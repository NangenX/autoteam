"""Base adapter interface for CLI workers.

All CLI adapters (Claude, Copilot, etc.) must implement this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

from autoteam.contracts import WorkerResult


class AdapterCapability(Enum):
    """Capabilities that an adapter may support."""
    NON_INTERACTIVE = "non_interactive"  # Can run without TTY
    INTERACTIVE = "interactive"          # Requires TTY interaction
    JSON_OUTPUT = "json_output"           # Supports structured JSON output
    STREAMING = "streaming"               # Supports streaming output
    SESSION_PERSISTENCE = "session_persistence"  # Can maintain session state


@dataclass
class AdapterConfig:
    """Configuration for a CLI adapter."""
    executable: str
    timeout_seconds: int = 120
    max_retries: int = 2
    working_dir: str | None = None
    env_vars: dict[str, str] | None = None
    extra_args: list[str] | None = None


class BaseAdapter(ABC):
    """Abstract base class for CLI adapters.
    
    Each adapter is responsible for:
    1. Running the CLI with appropriate arguments
    2. Parsing the output (text/JSON)
    3. Normalizing results to WorkerResult
    4. Mapping errors to structured error info
    """

    def __init__(self, config: AdapterConfig):
        self.config = config

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable adapter name."""
        ...

    @property
    @abstractmethod
    def capabilities(self) -> set[AdapterCapability]:
        """Set of capabilities this adapter supports."""
        ...

    @abstractmethod
    async def execute(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
    ) -> WorkerResult:
        """Execute a prompt and return normalized result.
        
        Args:
            prompt: The task/prompt to send to the CLI
            context: Optional context (previous results, files, etc.)
            
        Returns:
            WorkerResult with normalized output
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the CLI is available and responsive.
        
        Returns:
            True if the CLI can be executed, False otherwise
        """
        ...

    def supports(self, capability: AdapterCapability) -> bool:
        """Check if this adapter supports a specific capability."""
        return capability in self.capabilities
