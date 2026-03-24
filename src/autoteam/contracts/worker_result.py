"""Worker result data structure for normalized CLI outputs."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal


@dataclass
class Artifact:
    """An artifact produced by a worker."""

    path: Path
    kind: str


@dataclass
class Metrics:
    """Execution metrics for a worker run."""

    duration_ms: int
    tokens_in: int | None = None
    tokens_out: int | None = None
    cost_usd: float | None = None


@dataclass
class ErrorInfo:
    """Error information when a worker fails."""

    category: Literal[
        "timeout", "parse_error", "permission_denied", "tool_failure", "vendor_error", "unknown"
    ]
    message: str
    retryable: bool


@dataclass
class NextActionHint:
    """Hint for what should happen next after this worker completes."""

    type: Literal["continue", "review", "stop", "escalate"]
    target_role: str | None = None
    suggested_vendor: str | None = None


@dataclass
class WorkerResult:
    """Normalized result from any CLI worker (Claude, Copilot, etc.)."""

    worker_id: str
    vendor: Literal["claude", "copilot"]
    role: str
    run_id: str
    status: Literal["succeeded", "failed", "timeout", "cancelled"]
    summary: str
    raw_output_path: Path
    artifacts: list[Artifact] = field(default_factory=list)
    confidence: Literal["high", "medium", "low", "unknown"] = "unknown"
    next_action_hint: NextActionHint | None = None
    metrics: Metrics | None = None
    error: ErrorInfo | None = None
    created_at: datetime = field(default_factory=datetime.now)

    def is_success(self) -> bool:
        """Check if the worker completed successfully."""
        return self.status == "succeeded"

    def is_retryable(self) -> bool:
        """Check if this result can be retried."""
        if self.error is None:
            return False
        return self.error.retryable
