"""Claude CLI Adapter package.

Provides integration with Claude Code CLI for non-interactive execution.
"""

from autoteam.adapters.claude.adapter import ClaudeAdapter, create_claude_adapter
from autoteam.adapters.claude.runner import ClaudeRunner, ClaudeRunResult, ClaudeJsonRunner
from autoteam.adapters.claude.parser import ClaudeOutputParser, ParsedOutput, OutputFormat, CodeBlock
from autoteam.adapters.claude.normalizer import ClaudeNormalizer
from autoteam.adapters.claude.error_mapper import ClaudeErrorMapper, ClaudeErrorCode

__all__ = [
    # Main adapter
    "ClaudeAdapter",
    "create_claude_adapter",
    # Runner
    "ClaudeRunner",
    "ClaudeRunResult",
    "ClaudeJsonRunner",
    # Parser
    "ClaudeOutputParser",
    "ParsedOutput",
    "OutputFormat",
    "CodeBlock",
    # Normalizer
    "ClaudeNormalizer",
    # Error handling
    "ClaudeErrorMapper",
    "ClaudeErrorCode",
]
