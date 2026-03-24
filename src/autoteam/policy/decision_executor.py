"""Decision executor for applying Judge decisions.

Translates Judge decisions into concrete actions for the orchestrator.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Awaitable

from autoteam.contracts import JudgeDecision, WorkerResult


class ExecutionAction(Enum):
    """Concrete action to execute."""
    INVOKE_WORKER = "invoke_worker"
    RETRY_WORKER = "retry_worker"
    STOP_RUN = "stop_run"
    ESCALATE_HUMAN = "escalate_human"
    WAIT = "wait"


@dataclass
class ExecutionPlan:
    """Plan for executing a decision."""
    action: ExecutionAction
    target_worker: str | None = None
    prompt: str | None = None
    context: dict[str, Any] | None = None
    reason: str = ""
    priority: int = 0


class DecisionExecutor:
    """Executes Judge decisions by creating execution plans.
    
    Maps abstract decisions (continue, stop, retry, escalate)
    to concrete actions with proper context.
    """

    def __init__(
        self,
        default_next_worker: str = "copilot",
        worker_sequence: list[str] | None = None,
    ):
        self.default_next_worker = default_next_worker
        self.worker_sequence = worker_sequence or ["claude", "copilot"]
        self._current_worker_index = 0

    def create_plan(
        self,
        decision: JudgeDecision,
        last_result: WorkerResult | None = None,
        original_task: str | None = None,
    ) -> ExecutionPlan:
        """Create an execution plan from a Judge decision.
        
        Args:
            decision: The Judge's decision
            last_result: The most recent worker result
            original_task: The original task/prompt
            
        Returns:
            ExecutionPlan with concrete action
        """
        if decision.should_stop():
            return ExecutionPlan(
                action=ExecutionAction.STOP_RUN,
                reason=decision.reason,
            )

        if decision.should_escalate():
            return ExecutionPlan(
                action=ExecutionAction.ESCALATE_HUMAN,
                reason=decision.reason,
                context={
                    "decision": decision.to_dict(),
                    "last_result": self._serialize_result(last_result) if last_result else None,
                },
            )

        if decision.should_retry():
            target = decision.target_worker or (last_result.worker_id if last_result else None)
            return ExecutionPlan(
                action=ExecutionAction.RETRY_WORKER,
                target_worker=target,
                prompt=self._build_retry_prompt(decision, last_result, original_task),
                reason=decision.reason,
            )

        # Continue to next worker
        target = decision.target_worker or self._get_next_worker(last_result)
        return ExecutionPlan(
            action=ExecutionAction.INVOKE_WORKER,
            target_worker=target,
            prompt=self._build_continuation_prompt(decision, last_result, original_task),
            reason=decision.reason,
        )

    def _get_next_worker(self, last_result: WorkerResult | None) -> str:
        """Determine the next worker in sequence."""
        if not last_result:
            return self.worker_sequence[0]

        try:
            current_idx = self.worker_sequence.index(last_result.worker_id)
            next_idx = (current_idx + 1) % len(self.worker_sequence)
            return self.worker_sequence[next_idx]
        except ValueError:
            return self.default_next_worker

    def _build_retry_prompt(
        self,
        decision: JudgeDecision,
        last_result: WorkerResult | None,
        original_task: str | None,
    ) -> str:
        """Build a prompt for retry action."""
        parts = []

        if original_task:
            parts.append(f"Original task: {original_task}")
            parts.append("")

        parts.append("Your previous attempt had issues:")
        parts.append(f"- {decision.reason}")
        parts.append("")
        parts.append("Please try again, addressing the issues mentioned above.")

        if last_result and last_result.error_info:
            parts.append("")
            parts.append(f"Previous error: {last_result.error_info.message}")
            if last_result.error_info.suggestion:
                parts.append(f"Suggestion: {last_result.error_info.suggestion}")

        return "\n".join(parts)

    def _build_continuation_prompt(
        self,
        decision: JudgeDecision,
        last_result: WorkerResult | None,
        original_task: str | None,
    ) -> str:
        """Build a prompt for continuing to next worker."""
        parts = []

        if original_task:
            parts.append(f"Task: {original_task}")
            parts.append("")

        if last_result:
            parts.append("Previous worker's output:")
            parts.append(f"- Worker: {last_result.worker_id}")
            parts.append(f"- Summary: {last_result.summary[:500]}")
            parts.append("")
            parts.append("Your role:")
            parts.append(f"- Review and {decision.reason}")

        return "\n".join(parts)

    def _serialize_result(self, result: WorkerResult) -> dict[str, Any]:
        """Serialize a WorkerResult for context."""
        return {
            "worker_id": result.worker_id,
            "status": result.status.value,
            "summary": result.summary[:500],
            "confidence": result.confidence,
        }


class AsyncDecisionExecutor(DecisionExecutor):
    """Async version of DecisionExecutor with callback support."""

    def __init__(
        self,
        worker_invoker: Callable[[str, str], Awaitable[WorkerResult]] | None = None,
        escalation_handler: Callable[[dict], Awaitable[None]] | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._worker_invoker = worker_invoker
        self._escalation_handler = escalation_handler

    async def execute(
        self,
        plan: ExecutionPlan,
    ) -> WorkerResult | None:
        """Execute a plan and return result if applicable.
        
        Args:
            plan: The execution plan
            
        Returns:
            WorkerResult if a worker was invoked, None otherwise
        """
        if plan.action == ExecutionAction.STOP_RUN:
            return None

        if plan.action == ExecutionAction.ESCALATE_HUMAN:
            if self._escalation_handler:
                await self._escalation_handler(plan.context or {})
            return None

        if plan.action in (ExecutionAction.INVOKE_WORKER, ExecutionAction.RETRY_WORKER):
            if self._worker_invoker and plan.target_worker and plan.prompt:
                return await self._worker_invoker(plan.target_worker, plan.prompt)
            return None

        return None
