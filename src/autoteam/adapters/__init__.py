"""CLI Adapters package.

Provides adapters for different CLI tools (Claude, Copilot, etc.).
"""

from autoteam.adapters.base import BaseAdapter, AdapterCapability, AdapterConfig
from autoteam.adapters.claude import ClaudeAdapter, create_claude_adapter
from autoteam.adapters.copilot import CopilotAdapter, create_copilot_adapter

__all__ = [
    # Base
    "BaseAdapter",
    "AdapterCapability",
    "AdapterConfig",
    # Claude
    "ClaudeAdapter",
    "create_claude_adapter",
    # Copilot
    "CopilotAdapter",
    "create_copilot_adapter",
]
