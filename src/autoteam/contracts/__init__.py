"""Data contracts for AutoTeam."""

from autoteam.contracts.worker_result import (
    Artifact,
    ArtifactType,
    ErrorCategory,
    ErrorInfo,
    Metrics,
    NextActionHint,
    ResultStatus,
    WorkerResult,
)
from autoteam.contracts.decision_schema import JudgeDecision, JUDGE_DECISION_SCHEMA
from autoteam.contracts.run_state import RunState

__all__ = [
    # Worker result
    "Artifact",
    "ArtifactType",
    "ErrorCategory",
    "ErrorInfo",
    "Metrics",
    "NextActionHint",
    "ResultStatus",
    "WorkerResult",
    # Decision
    "JudgeDecision",
    "JUDGE_DECISION_SCHEMA",
    # Run state
    "RunState",
]
