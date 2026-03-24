"""Judge Adapter - Main orchestration of Judge functionality.

Combines provider, evidence builder, guardrails, and executor.
"""

from dataclasses import dataclass
from typing import Any

from autoteam.contracts import JudgeDecision, WorkerResult
from autoteam.policy.base_provider import (
    BaseJudgeProvider,
    JudgeProviderConfig,
    JudgeProviderType,
    JudgeRequest,
    JudgeResponse,
)
from autoteam.policy.deepseek_provider import DeepSeekJudgeProvider, create_deepseek_judge
from autoteam.policy.evidence_builder import EvidenceBuilder, EvidencePackage
from autoteam.policy.rule_guardrails import RuleGuardrails, GuardrailConfig, GuardrailResult, GuardrailAction
from autoteam.policy.decision_executor import DecisionExecutor, ExecutionPlan


@dataclass
class JudgeResult:
    """Complete result from Judge evaluation."""
    decision: JudgeDecision | None
    guardrail_result: GuardrailResult
    execution_plan: ExecutionPlan | None
    provider_response: JudgeResponse | None
    final_action: str  # The actual action to take
    reason: str


class JudgeAdapter:
    """Main adapter for Judge functionality.
    
    Combines:
    - AI provider for decisions (DeepSeek, Claude, etc.)
    - Evidence builder for formatting input
    - Rule guardrails for safety
    - Decision executor for action planning
    
    Example:
        judge = JudgeAdapter.create_with_deepseek()
        result = await judge.evaluate(worker_results, context)
        if result.final_action == "continue":
            plan = result.execution_plan
            # Execute plan...
    """

    def __init__(
        self,
        provider: BaseJudgeProvider,
        evidence_builder: EvidenceBuilder | None = None,
        guardrails: RuleGuardrails | None = None,
        executor: DecisionExecutor | None = None,
    ):
        self.provider = provider
        self.evidence_builder = evidence_builder or EvidenceBuilder()
        self.guardrails = guardrails or RuleGuardrails()
        self.executor = executor or DecisionExecutor()

    @classmethod
    def create_with_deepseek(
        cls,
        api_key: str | None = None,
        model: str = "deepseek-chat",
        guardrail_config: GuardrailConfig | None = None,
    ) -> "JudgeAdapter":
        """Create JudgeAdapter with DeepSeek provider.
        
        Args:
            api_key: DeepSeek API key (or use env var)
            model: Model to use
            guardrail_config: Custom guardrail configuration
            
        Returns:
            Configured JudgeAdapter
        """
        provider = create_deepseek_judge(api_key=api_key, model=model)
        guardrails = RuleGuardrails(guardrail_config) if guardrail_config else RuleGuardrails()
        return cls(provider=provider, guardrails=guardrails)

    async def evaluate(
        self,
        results: list[WorkerResult],
        context: dict[str, Any] | None = None,
    ) -> JudgeResult:
        """Evaluate worker results and determine next action.
        
        Args:
            results: List of worker results to evaluate
            context: Additional context (task, round number, etc.)
            
        Returns:
            JudgeResult with decision, guardrail check, and execution plan
        """
        context = context or {}

        # Build evidence
        evidence = self.evidence_builder.build(results, context)

        # Create Judge request
        request = JudgeRequest(
            evidence=evidence.formatted_text,
            context=context,
            run_id=context.get("run_id"),
            round_number=context.get("round_number", 0),
        )

        # Get Judge decision from provider
        response = await self.provider.judge(request)

        if not response.success or not response.decision:
            # Provider failed - create fallback decision
            fallback = JudgeDecision(
                action="stop",
                target_worker=None,
                reason=f"Judge provider error: {response.error}",
                confidence="low",
                stop_flag=True,
            )
            return JudgeResult(
                decision=fallback,
                guardrail_result=GuardrailResult(action=GuardrailAction.ALLOW, triggered_rules=[]),
                execution_plan=self.executor.create_plan(fallback),
                provider_response=response,
                final_action="stop",
                reason=f"Judge provider failed: {response.error}",
            )

        decision = response.decision

        # Apply guardrails
        guardrail_result = self.guardrails.evaluate(
            decision=decision,
            results=results,
            context=context,
        )

        # Determine final decision
        if guardrail_result.action == GuardrailAction.OVERRIDE:
            final_decision = guardrail_result.modified_decision or decision
        elif guardrail_result.action == GuardrailAction.BLOCK:
            final_decision = JudgeDecision(
                action="stop",
                target_worker=None,
                reason=f"Blocked by guardrail: {guardrail_result.reason}",
                confidence="high",
                stop_flag=True,
            )
        else:
            final_decision = decision

        # Record round for tracking
        self.guardrails.record_round(final_decision)

        # Record API call
        if response.usage:
            cost = self._estimate_cost(response.usage)
            self.guardrails.record_api_call(cost)

        # Create execution plan
        last_result = results[-1] if results else None
        plan = self.executor.create_plan(
            decision=final_decision,
            last_result=last_result,
            original_task=context.get("original_task"),
        )

        return JudgeResult(
            decision=final_decision,
            guardrail_result=guardrail_result,
            execution_plan=plan,
            provider_response=response,
            final_action=final_decision.action,
            reason=final_decision.reason,
        )

    def _estimate_cost(self, usage: dict[str, int]) -> float:
        """Estimate cost from token usage."""
        # DeepSeek pricing (approximate)
        input_cost = usage.get("prompt_tokens", 0) * 0.00014 / 1000
        output_cost = usage.get("completion_tokens", 0) * 0.00028 / 1000
        return input_cost + output_cost

    async def health_check(self) -> tuple[bool, str]:
        """Check if Judge is operational."""
        return await self.provider.health_check()

    def reset(self) -> None:
        """Reset Judge state (guardrails, etc.)."""
        self.guardrails.reset()

    @property
    def stats(self) -> dict[str, Any]:
        """Get Judge statistics."""
        return {
            "provider": self.provider.name,
            **self.guardrails.stats,
        }
