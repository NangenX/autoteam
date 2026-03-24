"""End-to-end tests for ReviewWorkflow."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from autoteam.contracts import (
    WorkerResult,
    ResultStatus,
    Metrics,
    JudgeDecision,
)
from autoteam.workflows.review_flow import ReviewWorkflow, WorkflowState, WorkflowRun
from autoteam.policy.judge_adapter import JudgeResult
from autoteam.policy.rule_guardrails import GuardrailResult, GuardrailAction
from autoteam.policy.decision_executor import ExecutionPlan, ExecutionAction


class MockClaudeAdapter:
    """Mock Claude adapter for testing."""

    def __init__(self, responses: list[WorkerResult] | None = None):
        self._responses = responses or []
        self._call_count = 0

    async def execute(self, prompt: str, context: dict = None) -> WorkerResult:
        if self._call_count < len(self._responses):
            result = self._responses[self._call_count]
        else:
            result = WorkerResult(
                worker_id="claude",
                status=ResultStatus.SUCCESS,
                summary="Mock Claude response",
                raw_output="Mock analysis complete",
                artifacts=[],
                confidence=0.8,
                metrics=Metrics(duration_seconds=2.0),
                timestamp=datetime.now(timezone.utc),
            )
        self._call_count += 1
        return result

    async def health_check(self) -> bool:
        return True


class MockCopilotAdapter:
    """Mock Copilot adapter for testing."""

    def __init__(self, responses: list[WorkerResult] | None = None):
        self._responses = responses or []
        self._call_count = 0

    async def execute(self, prompt: str, context: dict = None) -> WorkerResult:
        if self._call_count < len(self._responses):
            result = self._responses[self._call_count]
        else:
            result = WorkerResult(
                worker_id="copilot",
                status=ResultStatus.SUCCESS,
                summary="Mock Copilot response",
                raw_output="Mock code review complete",
                artifacts=[],
                confidence=0.85,
                metrics=Metrics(duration_seconds=3.0),
                timestamp=datetime.now(timezone.utc),
            )
        self._call_count += 1
        return result

    async def start_session(self) -> str:
        return "mock-session-id"

    async def end_session(self) -> None:
        pass

    async def health_check(self) -> bool:
        return True


class MockJudgeAdapter:
    """Mock Judge adapter for testing."""

    def __init__(self, decisions: list[JudgeDecision] | None = None):
        self._decisions = decisions or []
        self._call_count = 0

    async def evaluate(self, results: list[WorkerResult], context: dict = None) -> JudgeResult:
        if self._call_count < len(self._decisions):
            decision = self._decisions[self._call_count]
        else:
            # Default to stop after exhausting decisions
            decision = JudgeDecision(
                action="stop",
                target_worker=None,
                reason="Complete",
                confidence="high",
                stop_flag=True,
            )
        self._call_count += 1

        return JudgeResult(
            decision=decision,
            guardrail_result=GuardrailResult(
                action=GuardrailAction.ALLOW,
                triggered_rules=[],
            ),
            execution_plan=ExecutionPlan(
                action=ExecutionAction.INVOKE_WORKER if decision.action == "continue" else ExecutionAction.STOP_RUN,
                target_worker=decision.target_worker,
                prompt=None,
                context=None,
                reason=decision.reason,
            ),
            provider_response=None,
            final_action=decision.action,
            reason=decision.reason,
        )

    async def health_check(self) -> tuple[bool, str]:
        return True, "Mock OK"

    def reset(self) -> None:
        self._call_count = 0


class TestReviewWorkflow:
    """Tests for ReviewWorkflow."""

    @pytest.fixture
    def workflow(self) -> ReviewWorkflow:
        """Create workflow with mock adapters."""
        claude = MockClaudeAdapter()
        copilot = MockCopilotAdapter()
        judge = MockJudgeAdapter([
            JudgeDecision(
                action="continue",
                target_worker="copilot",
                reason="Claude done, Copilot next",
                confidence="high",
                stop_flag=False,
            ),
            JudgeDecision(
                action="stop",
                target_worker=None,
                reason="Review complete",
                confidence="high",
                stop_flag=True,
            ),
        ])

        return ReviewWorkflow(
            claude_adapter=claude,
            copilot_adapter=copilot,
            judge=judge,
        )

    @pytest.mark.asyncio
    async def test_execute_simple_flow(self, workflow: ReviewWorkflow):
        """Test simple review flow: Claude -> Judge -> Copilot -> Judge -> Stop."""
        run = await workflow.execute("Review the authentication code")

        assert run.state == WorkflowState.COMPLETED
        assert len(run.steps) == 2  # Claude and Copilot
        assert run.current_round == 1

    @pytest.mark.asyncio
    async def test_execute_immediate_stop(self):
        """Test workflow that stops immediately after first worker."""
        claude = MockClaudeAdapter()
        copilot = MockCopilotAdapter()
        judge = MockJudgeAdapter([
            JudgeDecision(
                action="stop",
                target_worker=None,
                reason="Task complete",
                confidence="high",
                stop_flag=True,
            ),
        ])

        workflow = ReviewWorkflow(
            claude_adapter=claude,
            copilot_adapter=copilot,
            judge=judge,
        )

        run = await workflow.execute("Simple task")

        assert run.state == WorkflowState.COMPLETED
        assert len(run.steps) == 1  # Only Claude ran

    @pytest.mark.asyncio
    async def test_execute_escalate(self):
        """Test workflow that escalates to human."""
        claude = MockClaudeAdapter()
        copilot = MockCopilotAdapter()
        judge = MockJudgeAdapter([
            JudgeDecision(
                action="escalate",
                target_worker=None,
                reason="Need human review",
                confidence="low",
                stop_flag=True,
            ),
        ])

        workflow = ReviewWorkflow(
            claude_adapter=claude,
            copilot_adapter=copilot,
            judge=judge,
        )

        run = await workflow.execute("Sensitive task")

        assert run.state == WorkflowState.PAUSED
        assert len(run.steps) == 1
        assert "escalate" in run.error.lower() or "escalation" in run.error.lower()

    @pytest.mark.asyncio
    async def test_execute_worker_failure(self):
        """Test handling worker failure."""
        # Claude that fails
        claude = MockClaudeAdapter([
            WorkerResult(
                worker_id="claude",
                status=ResultStatus.FAILED,
                summary="Execution failed",
                raw_output="",
                artifacts=[],
                confidence=0.0,
                metrics=Metrics(duration_seconds=1.0),
                timestamp=datetime.now(timezone.utc),
            )
        ])
        copilot = MockCopilotAdapter()
        judge = MockJudgeAdapter()

        workflow = ReviewWorkflow(
            claude_adapter=claude,
            copilot_adapter=copilot,
            judge=judge,
        )

        run = await workflow.execute("Failing task")

        # Should fail
        assert run.state == WorkflowState.FAILED


class TestReviewWorkflowIntegration:
    """Integration tests for workflow with realistic scenarios."""

    @pytest.mark.asyncio
    async def test_code_review_scenario(self):
        """Test realistic code review scenario."""
        # Claude finds issues
        claude_responses = [
            WorkerResult(
                worker_id="claude",
                status=ResultStatus.SUCCESS,
                summary="Found 3 issues in authentication code",
                raw_output="""
                Code Review Findings:
                1. SQL injection vulnerability in login function
                2. Missing input validation for email
                3. Hardcoded credentials in config
                """,
                artifacts=[],
                confidence=0.9,
                metrics=Metrics(duration_seconds=5.0),
                timestamp=datetime.now(timezone.utc),
            ),
        ]

        # Copilot suggests fixes
        copilot_responses = [
            WorkerResult(
                worker_id="copilot",
                status=ResultStatus.SUCCESS,
                summary="Suggested fixes for 3 issues",
                raw_output="""
                Suggested Fixes:
                1. Use parameterized queries
                2. Add email validation regex
                3. Move credentials to environment variables
                """,
                artifacts=[],
                confidence=0.85,
                metrics=Metrics(duration_seconds=4.0),
                timestamp=datetime.now(timezone.utc),
            ),
        ]

        judge_decisions = [
            JudgeDecision(
                action="continue",
                target_worker="copilot",
                reason="Claude found issues, Copilot should review fixes",
                confidence="high",
                stop_flag=False,
            ),
            JudgeDecision(
                action="stop",
                target_worker=None,
                reason="Review complete with actionable fixes",
                confidence="high",
                stop_flag=True,
            ),
        ]

        workflow = ReviewWorkflow(
            claude_adapter=MockClaudeAdapter(claude_responses),
            copilot_adapter=MockCopilotAdapter(copilot_responses),
            judge=MockJudgeAdapter(judge_decisions),
        )

        run = await workflow.execute(
            "Review authentication code in src/auth.py for security issues"
        )

        assert run.state == WorkflowState.COMPLETED
        assert len(run.steps) == 2
        assert "SQL injection" in run.steps[0].result.raw_output
        assert "parameterized" in run.steps[1].result.raw_output
