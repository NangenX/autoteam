"""CLI Adapters package.

Provides adapters for different CLI tools (Claude, Copilot, etc.).
"""

from autoteam.adapters.base import BaseAdapter, AdapterCapability, AdapterConfig
from autoteam.adapters.claude import ClaudeAdapter, create_claude_adapter

__all__ = [
    # Base
    "BaseAdapter",
    "AdapterCapability",
    "AdapterConfig",
    # Claude
    "ClaudeAdapter",
    "create_claude_adapter",
]
