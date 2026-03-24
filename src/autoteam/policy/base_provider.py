"""Base Judge Provider interface.

Supports multiple AI providers for the Judge role.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from autoteam.contracts import JudgeDecision


class JudgeProviderType(Enum):
    """Supported Judge provider types."""
    DEEPSEEK = "deepseek"
    CLAUDE = "claude"
    OPENAI = "openai"
    OLLAMA = "ollama"  # For local models


@dataclass
class JudgeProviderConfig:
    """Configuration for a Judge provider."""
    provider_type: JudgeProviderType
    api_key: str | None = None
    api_base: str | None = None
    model: str | None = None
    timeout_seconds: int = 60
    max_tokens: int = 1024
    temperature: float = 0.1  # Low temperature for consistent decisions
    extra_params: dict[str, Any] = field(default_factory=dict)


@dataclass
class JudgeRequest:
    """Request to the Judge."""
    evidence: str  # Formatted evidence from workers
    context: dict[str, Any] | None = None
    run_id: str | None = None
    round_number: int = 0


@dataclass
class JudgeResponse:
    """Response from the Judge provider."""
    decision: JudgeDecision | None
    raw_response: str
    success: bool
    error: str | None = None
    usage: dict[str, int] | None = None  # tokens, cost, etc.
    latency_seconds: float = 0.0


class BaseJudgeProvider(ABC):
    """Abstract base class for Judge providers.
    
    Each provider implements the Judge role using a different AI backend.
    The Judge evaluates worker outputs and decides next actions.
    """

    def __init__(self, config: JudgeProviderConfig):
        self.config = config

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging."""
        ...

    @abstractmethod
    async def judge(self, request: JudgeRequest) -> JudgeResponse:
        """Evaluate evidence and return a decision.
        
        Args:
            request: JudgeRequest with evidence and context
            
        Returns:
            JudgeResponse with decision or error
        """
        ...

    @abstractmethod
    async def health_check(self) -> tuple[bool, str]:
        """Check if the provider is available.
        
        Returns:
            Tuple of (is_healthy, message)
        """
        ...

    def _build_system_prompt(self) -> str:
        """Build the system prompt for the Judge."""
        return """You are an AI Judge in a multi-agent orchestration system.

Your role is to evaluate the output from AI workers (Claude CLI, Copilot CLI) and decide what should happen next.

You MUST respond with a JSON object matching this schema:
{
    "action": "continue" | "stop" | "retry" | "escalate",
    "target_worker": "claude" | "copilot" | null,
    "reason": "Brief explanation of your decision",
    "confidence": "high" | "medium" | "low",
    "stop_flag": true | false
}

Decision guidelines:
- "continue": The work should proceed to the next worker
- "stop": The task is complete or no further action needed
- "retry": The current worker should try again (errors, incomplete output)
- "escalate": Human intervention needed (conflicts, unclear requirements)

Set stop_flag=true when:
- Task is fully complete
- Maximum rounds reached
- Unrecoverable error occurred
- Human escalation needed

Be concise and decisive. Focus on whether the output meets the task requirements."""

    def _build_user_prompt(self, request: JudgeRequest) -> str:
        """Build the user prompt with evidence."""
        parts = [
            f"## Round {request.round_number}",
            "",
            "## Evidence from Workers",
            request.evidence,
            "",
            "## Your Task",
            "Evaluate the above evidence and decide the next action.",
            "Respond with a JSON object only, no markdown formatting.",
        ]
        return "\n".join(parts)
