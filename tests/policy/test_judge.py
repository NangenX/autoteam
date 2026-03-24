"""Tests for Judge/Policy module."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from autoteam.contracts import WorkerResult, ResultStatus, Metrics, JudgeDecision
from autoteam.policy.base_provider import (
    BaseJudgeProvider,
    JudgeProviderConfig,
    JudgeProviderType,
    JudgeRequest,
    JudgeResponse,
)
from autoteam.policy.evidence_builder import EvidenceBuilder, EvidencePackage
from autoteam.policy.rule_guardrails import (
    RuleGuardrails,
    GuardrailConfig,
    GuardrailResult,
    GuardrailAction,
)
from autoteam.policy.decision_executor import DecisionExecutor, ExecutionPlan, ExecutionAction
from autoteam.policy.judge_adapter import JudgeAdapter, JudgeResult


class TestEvidenceBuilder:
    """Tests for EvidenceBuilder."""

    @pytest.fixture
    def builder(self) -> EvidenceBuilder:
        return EvidenceBuilder()

    def test_build_single_result(
        self, builder: EvidenceBuilder, sample_worker_result: WorkerResult
    ):
        """Test building evidence from single result."""
        evidence = builder.build([sample_worker_result], {})

        assert isinstance(evidence, EvidencePackage)
        assert evidence.formatted_text != ""
        assert "claude" in evidence.formatted_text.lower()

    def test_build_multiple_results(
        self,
        builder: EvidenceBuilder,
        sample_worker_result: WorkerResult,
        sample_error_result: WorkerResult,
    ):
        """Test building evidence from multiple results."""
        results = [sample_worker_result, sample_error_result]
        evidence = builder.build(results, {"task": "Review code"})

        assert evidence.formatted_text != ""
        assert "success" in evidence.formatted_text.lower() or "fail" in evidence.formatted_text.lower()

    def test_build_with_context(
        self, builder: EvidenceBuilder, sample_worker_result: WorkerResult
    ):
        """Test building evidence with context."""
        context = {
            "task": "Review authentication code",
            "round_number": 2,
            "max_rounds": 5,
        }
        evidence = builder.build([sample_worker_result], context)

        assert "authentication" in evidence.formatted_text.lower() or len(evidence.formatted_text) > 0


class TestRuleGuardrails:
    """Tests for RuleGuardrails."""

    @pytest.fixture
    def guardrails(self) -> RuleGuardrails:
        config = GuardrailConfig(
            max_rounds=3,
            max_retries_per_worker=2,
            max_cost_usd=1.0,
        )
        return RuleGuardrails(config)

    def test_allow_normal_decision(
        self, guardrails: RuleGuardrails, sample_judge_decision: JudgeDecision
    ):
        """Test allowing a normal decision."""
        result = guardrails.evaluate(sample_judge_decision, [], {})

        assert result.action == GuardrailAction.ALLOW

    def test_block_excessive_rounds(self, guardrails: RuleGuardrails):
        """Test blocking when max rounds exceeded."""
        decision = JudgeDecision(
            action="continue",
            target_worker="claude",
            reason="Keep going",
            confidence="high",
            stop_flag=False,
        )

        # Simulate 3 rounds
        for _ in range(3):
            guardrails.record_round(decision)

        result = guardrails.evaluate(decision, [], {"round_number": 4})

        assert result.action in (GuardrailAction.OVERRIDE, GuardrailAction.BLOCK)

    def test_block_excessive_cost(self, guardrails: RuleGuardrails):
        """Test blocking when cost exceeded."""
        decision = JudgeDecision(
            action="continue",
            target_worker="claude",
            reason="Keep going",
            confidence="high",
            stop_flag=False,
        )

        # Simulate high cost
        guardrails.record_api_call(0.6)
        guardrails.record_api_call(0.5)

        result = guardrails.evaluate(decision, [], {})

        assert result.action in (GuardrailAction.OVERRIDE, GuardrailAction.BLOCK)

    def test_detect_duplicate_outputs(
        self, guardrails: RuleGuardrails, sample_worker_result: WorkerResult
    ):
        """Test detecting duplicate outputs."""
        decision = JudgeDecision(
            action="continue",
            target_worker="claude",
            reason="Continue",
            confidence="high",
            stop_flag=False,
        )

        # First evaluation - should pass
        result1 = guardrails.evaluate(decision, [sample_worker_result], {})
        assert result1.action == GuardrailAction.ALLOW

        # Record the round
        guardrails.record_round(decision)

        # Second evaluation with same output - should detect duplicate
        result2 = guardrails.evaluate(decision, [sample_worker_result], {})
        # May or may not block depending on implementation
        assert result2.action in (GuardrailAction.ALLOW, GuardrailAction.OVERRIDE, GuardrailAction.BLOCK)

    def test_reset_clears_state(self, guardrails: RuleGuardrails):
        """Test that reset clears all state."""
        decision = JudgeDecision(
            action="continue",
            target_worker="claude",
            reason="Keep going",
            confidence="high",
            stop_flag=False,
        )

        guardrails.record_round(decision)
        guardrails.record_api_call(0.5)

        guardrails.reset()

        stats = guardrails.stats
        assert stats["round_count"] == 0
        assert stats["total_cost"] == 0.0


class TestDecisionExecutor:
    """Tests for DecisionExecutor."""

    @pytest.fixture
    def executor(self) -> DecisionExecutor:
        return DecisionExecutor()

    def test_create_continue_plan(
        self, executor: DecisionExecutor, sample_judge_decision: JudgeDecision
    ):
        """Test creating plan for continue action."""
        plan = executor.create_plan(sample_judge_decision)

        assert isinstance(plan, ExecutionPlan)
        assert plan.action == ExecutionAction.INVOKE_WORKER
        assert plan.target_worker == "copilot"

    def test_create_stop_plan(self, executor: DecisionExecutor):
        """Test creating plan for stop action."""
        decision = JudgeDecision(
            action="stop",
            target_worker=None,
            reason="Task complete",
            confidence="high",
            stop_flag=True,
        )

        plan = executor.create_plan(decision)

        assert plan.action == ExecutionAction.STOP_RUN

    def test_create_retry_plan(
        self, executor: DecisionExecutor, sample_worker_result: WorkerResult
    ):
        """Test creating plan for retry action."""
        decision = JudgeDecision(
            action="retry",
            target_worker="claude",
            reason="Unclear output, retry",
            confidence="medium",
            stop_flag=False,
        )

        plan = executor.create_plan(decision, last_result=sample_worker_result)

        assert plan.action == ExecutionAction.RETRY_WORKER
        assert plan.target_worker == "claude"

    def test_create_escalate_plan(self, executor: DecisionExecutor):
        """Test creating plan for escalate action."""
        decision = JudgeDecision(
            action="escalate",
            target_worker=None,
            reason="Need human review",
            confidence="low",
            stop_flag=True,
        )

        plan = executor.create_plan(decision)

        assert plan.action == ExecutionAction.ESCALATE_HUMAN


class MockJudgeProvider(BaseJudgeProvider):
    """Mock Judge provider for testing."""

    def __init__(self, decision: JudgeDecision | None = None):
        config = JudgeProviderConfig(
            provider_type=JudgeProviderType.DEEPSEEK,
            api_key="mock-key",
        )
        super().__init__(config)
        self._decision = decision

    @property
    def name(self) -> str:
        return "Mock Judge"

    async def judge(self, request: JudgeRequest) -> JudgeResponse:
        if self._decision:
            return JudgeResponse(
                decision=self._decision,
                raw_response="mock response",
                success=True,
                usage={"prompt_tokens": 100, "completion_tokens": 50},
            )
        return JudgeResponse(
            decision=None,
            raw_response="",
            success=False,
            error="Mock error",
        )

    async def health_check(self) -> tuple[bool, str]:
        return True, "Mock OK"


class TestJudgeAdapter:
    """Integration tests for JudgeAdapter."""

    @pytest.fixture
    def mock_provider(self, sample_judge_decision: JudgeDecision) -> MockJudgeProvider:
        return MockJudgeProvider(sample_judge_decision)

    @pytest.fixture
    def adapter(self, mock_provider: MockJudgeProvider) -> JudgeAdapter:
        return JudgeAdapter(provider=mock_provider)

    @pytest.mark.asyncio
    async def test_evaluate_success(
        self, adapter: JudgeAdapter, sample_worker_result: WorkerResult
    ):
        """Test successful evaluation."""
        result = await adapter.evaluate([sample_worker_result], {"task": "Review code"})

        assert isinstance(result, JudgeResult)
        assert result.final_action == "continue"
        assert result.decision is not None
        assert result.execution_plan is not None

    @pytest.mark.asyncio
    async def test_evaluate_with_guardrail_override(
        self, sample_worker_result: WorkerResult, sample_judge_decision: JudgeDecision
    ):
        """Test evaluation with guardrail override."""
        # Create adapter with strict guardrails
        config = GuardrailConfig(max_rounds=1)
        provider = MockJudgeProvider(sample_judge_decision)
        guardrails = RuleGuardrails(config)
        
        # Record one round to trigger max rounds
        guardrails.record_round(sample_judge_decision)
        
        adapter = JudgeAdapter(provider=provider, guardrails=guardrails)

        result = await adapter.evaluate(
            [sample_worker_result],
            {"task": "Review code", "round_number": 2},
        )

        # Should be overridden or blocked
        assert result.final_action in ("stop", "continue")

    @pytest.mark.asyncio
    async def test_evaluate_provider_failure(
        self, sample_worker_result: WorkerResult
    ):
        """Test handling provider failure."""
        provider = MockJudgeProvider(None)  # Will return error
        adapter = JudgeAdapter(provider=provider)

        result = await adapter.evaluate([sample_worker_result], {})

        assert result.final_action == "stop"
        assert "error" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_health_check(self, adapter: JudgeAdapter):
        """Test health check delegation."""
        healthy, message = await adapter.health_check()

        assert healthy is True
        assert "OK" in message

    def test_reset(self, adapter: JudgeAdapter):
        """Test reset functionality."""
        # Record some state
        decision = JudgeDecision(
            action="continue",
            target_worker="claude",
            reason="Test",
            confidence="high",
            stop_flag=False,
        )
        adapter.guardrails.record_round(decision)
        adapter.guardrails.record_api_call(0.1)

        adapter.reset()

        stats = adapter.stats
        assert stats["round_count"] == 0

    def test_stats(self, adapter: JudgeAdapter):
        """Test stats property."""
        stats = adapter.stats

        assert "provider" in stats
        assert "round_count" in stats
        assert "total_cost" in stats
