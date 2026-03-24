"""Pytest configuration and fixtures for autoteam tests."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from autoteam.contracts import (
    WorkerResult,
    ResultStatus,
    Metrics,
    Artifact,
    ArtifactType,
    ErrorInfo,
    ErrorCategory,
    NextActionHint,
    JudgeDecision,
)
from autoteam.adapters.base import AdapterConfig


@pytest.fixture
def sample_worker_result() -> WorkerResult:
    """Create a sample successful WorkerResult."""
    return WorkerResult(
        worker_id="claude",
        status=ResultStatus.SUCCESS,
        summary="Code review completed successfully",
        raw_output="The code looks good. Found 2 minor issues...",
        artifacts=[
            Artifact(
                type=ArtifactType.ANALYSIS,
                name="review_findings",
                content="1. Consider using type hints\n2. Add docstring",
            )
        ],
        confidence=0.85,
        metrics=Metrics(
            duration_seconds=5.2,
            api_calls=1,
        ),
        next_action_hint=NextActionHint(
            action="continue",
            reason="Review complete, ready for fixes",
            suggested_target="copilot",
        ),
        timestamp=datetime.now(timezone.utc),
        error_info=None,
    )


@pytest.fixture
def sample_error_result() -> WorkerResult:
    """Create a sample error WorkerResult."""
    return WorkerResult(
        worker_id="claude",
        status=ResultStatus.FAILED,
        summary="Execution failed: timeout",
        raw_output="",
        artifacts=[],
        confidence=0.0,
        metrics=Metrics(duration_seconds=120.0),
        next_action_hint=NextActionHint(
            action="retry",
            reason="Timeout - may need more time",
        ),
        timestamp=datetime.now(timezone.utc),
        error_info=ErrorInfo(
            category=ErrorCategory.TRANSIENT,
            code="TIMEOUT",
            message="Process timed out after 120s",
            recoverable=True,
            suggestion="Increase timeout or simplify task",
        ),
    )


@pytest.fixture
def sample_judge_decision() -> JudgeDecision:
    """Create a sample JudgeDecision."""
    return JudgeDecision(
        action="continue",
        target_worker="copilot",
        reason="Claude completed review, Copilot should apply fixes",
        confidence="high",
        stop_flag=False,
    )


@pytest.fixture
def adapter_config() -> AdapterConfig:
    """Create a sample AdapterConfig."""
    return AdapterConfig(
        executable="claude",
        timeout_seconds=60,
        max_retries=2,
    )


@pytest.fixture
def mock_subprocess_result():
    """Create a mock subprocess result."""
    mock = MagicMock()
    mock.stdout = "Mock output from CLI"
    mock.stderr = ""
    mock.returncode = 0
    return mock


@pytest.fixture
def mock_async_runner():
    """Create an AsyncMock for CLI runners."""
    runner = AsyncMock()
    runner.run = AsyncMock()
    runner.health_check = AsyncMock(return_value=(True, "OK"))
    return runner
