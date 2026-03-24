"""Worker result data structure for normalized CLI outputs."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Literal


class ResultStatus(Enum):
    """Status of a worker result."""
    SUCCESS = "succeeded"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    PARTIAL = "partial"


class ErrorCategory(Enum):
    """Category of error for better handling decisions."""
    TRANSIENT = "transient"      # Can retry (network, rate limit)
    CONFIG = "config"            # Configuration issue (bad API key)
    INPUT = "input"              # Invalid input (prompt too long)
    RESOURCE = "resource"        # Resource issue (quota exceeded)
    UNKNOWN = "unknown"          # Unknown error


class ArtifactType(Enum):
    """Type of artifact produced."""
    ANALYSIS = "analysis"
    CODE_SNIPPET = "code_snippet"
    FILE_LIST = "file_list"
    SUGGESTIONS = "suggestions"
    DIFF = "diff"
    REPORT = "report"
    OTHER = "other"


@dataclass
class Artifact:
    """An artifact produced by a worker."""
    type: ArtifactType
    content: str
    name: str = ""
    path: Path | None = None
    metadata: dict | None = None


@dataclass
class Metrics:
    """Execution metrics for a worker run."""
    duration_seconds: float = 0.0
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None
    api_calls: int = 1


@dataclass
class ErrorInfo:
    """Error information when a worker fails."""
    category: ErrorCategory
    code: str
    message: str
    recoverable: bool = True
    suggestion: str | None = None
    raw_error: str | None = None


@dataclass
class NextActionHint:
    """Hint for what should happen next after this worker completes."""
    action: Literal["continue", "review", "stop", "escalate", "retry"]
    reason: str = ""
    suggested_target: str | None = None


@dataclass
class WorkerResult:
    """Normalized result from any CLI worker (Claude, Copilot, etc.)."""
    worker_id: str
    status: ResultStatus
    summary: str
    raw_output: str = ""
    artifacts: list[Artifact] = field(default_factory=list)
    confidence: float = 0.0  # 0.0 - 1.0
    metrics: Metrics | None = None
    next_action_hint: NextActionHint | None = None
    error_info: ErrorInfo | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Optional context
    vendor: Literal["claude", "copilot"] | None = None
    role: str | None = None
    run_id: str | None = None

    def is_success(self) -> bool:
        """Check if the worker completed successfully."""
        return self.status == ResultStatus.SUCCESS

    def is_retryable(self) -> bool:
        """Check if this result can be retried."""
        if self.error_info is None:
            return False
        return self.error_info.recoverable
    
    @property
    def status_str(self) -> str:
        """Get status as string for compatibility."""
        return self.status.value
