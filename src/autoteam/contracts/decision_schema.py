"""Judge decision schema for policy engine outputs."""

from dataclasses import dataclass
from typing import Literal

# JSON schema for Judge output validation
JUDGE_DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["continue", "stop", "retry", "escalate"],
        },
        "target_worker": {
            "type": ["string", "null"],
        },
        "reason": {
            "type": "string",
        },
        "confidence": {
            "type": "string",
            "enum": ["high", "medium", "low"],
        },
        "stop_flag": {
            "type": "boolean",
        },
    },
    "required": ["action", "reason", "confidence", "stop_flag"],
}


@dataclass
class NextActionHint:
    """Hint for what action to take next."""

    type: Literal["continue", "review", "stop", "escalate"]
    target_role: str | None = None
    suggested_vendor: str | None = None


@dataclass
class JudgeDecision:
    """Structured decision from the AI Judge."""

    action: Literal["continue", "stop", "retry", "escalate"]
    target_worker: str | None
    reason: str
    confidence: Literal["high", "medium", "low"]
    stop_flag: bool

    def should_stop(self) -> bool:
        """Check if this decision indicates the run should stop."""
        return self.stop_flag or self.action == "stop"

    def should_retry(self) -> bool:
        """Check if this decision indicates a retry is needed."""
        return self.action == "retry"

    def should_escalate(self) -> bool:
        """Check if this decision indicates human escalation is needed."""
        return self.action == "escalate"

    @classmethod
    def from_dict(cls, data: dict) -> "JudgeDecision":
        """Create a JudgeDecision from a dictionary."""
        return cls(
            action=data["action"],
            target_worker=data.get("target_worker"),
            reason=data["reason"],
            confidence=data["confidence"],
            stop_flag=data["stop_flag"],
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "action": self.action,
            "target_worker": self.target_worker,
            "reason": self.reason,
            "confidence": self.confidence,
            "stop_flag": self.stop_flag,
        }
