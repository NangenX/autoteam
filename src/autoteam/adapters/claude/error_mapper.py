"""Map Claude CLI errors to structured ErrorInfo.

Categorizes errors for better decision-making by the Judge.
"""

import re
from enum import Enum

from autoteam.contracts import ErrorInfo, ErrorCategory
from autoteam.adapters.claude.runner import ClaudeRunResult


class ClaudeErrorCode(Enum):
    """Claude-specific error codes."""
    # Process errors
    TIMEOUT = "CLAUDE_TIMEOUT"
    PROCESS_FAILED = "CLAUDE_PROCESS_FAILED"
    NOT_FOUND = "CLAUDE_NOT_FOUND"
    
    # API errors
    RATE_LIMITED = "CLAUDE_RATE_LIMITED"
    AUTH_FAILED = "CLAUDE_AUTH_FAILED"
    QUOTA_EXCEEDED = "CLAUDE_QUOTA_EXCEEDED"
    API_ERROR = "CLAUDE_API_ERROR"
    
    # Content errors
    CONTEXT_TOO_LONG = "CLAUDE_CONTEXT_TOO_LONG"
    INVALID_REQUEST = "CLAUDE_INVALID_REQUEST"
    CONTENT_FILTERED = "CLAUDE_CONTENT_FILTERED"
    
    # Output errors
    PARSE_ERROR = "CLAUDE_PARSE_ERROR"
    EMPTY_OUTPUT = "CLAUDE_EMPTY_OUTPUT"
    
    # Unknown
    UNKNOWN = "CLAUDE_UNKNOWN"


# Patterns for detecting specific errors in stderr/stdout
ERROR_PATTERNS = [
    (re.compile(r"rate.?limit|429|too many requests", re.I), 
     ClaudeErrorCode.RATE_LIMITED, ErrorCategory.TRANSIENT),
    
    (re.compile(r"auth|unauthorized|401|api.?key|token", re.I),
     ClaudeErrorCode.AUTH_FAILED, ErrorCategory.CONFIG),
    
    (re.compile(r"quota|billing|payment|402", re.I),
     ClaudeErrorCode.QUOTA_EXCEEDED, ErrorCategory.RESOURCE),
    
    (re.compile(r"context.*(long|limit|exceed)|too.*(long|large)", re.I),
     ClaudeErrorCode.CONTEXT_TOO_LONG, ErrorCategory.INPUT),
    
    (re.compile(r"invalid.*(request|input|param)|400", re.I),
     ClaudeErrorCode.INVALID_REQUEST, ErrorCategory.INPUT),
    
    (re.compile(r"content.*(filter|policy|block)|unsafe", re.I),
     ClaudeErrorCode.CONTENT_FILTERED, ErrorCategory.INPUT),
    
    (re.compile(r"not.?found|command.?not|enoent", re.I),
     ClaudeErrorCode.NOT_FOUND, ErrorCategory.CONFIG),
    
    (re.compile(r"timeout|timed?.?out", re.I),
     ClaudeErrorCode.TIMEOUT, ErrorCategory.TRANSIENT),
    
    (re.compile(r"5\d{2}|server.?error|internal.?error", re.I),
     ClaudeErrorCode.API_ERROR, ErrorCategory.TRANSIENT),
]


class ClaudeErrorMapper:
    """Maps Claude CLI errors to structured ErrorInfo."""

    def map_error(
        self,
        run_result: ClaudeRunResult,
        exception: Exception | None = None,
    ) -> ErrorInfo | None:
        """Map execution result to ErrorInfo if there's an error.
        
        Args:
            run_result: The raw execution result
            exception: Any exception that occurred
            
        Returns:
            ErrorInfo if error detected, None otherwise
        """
        # No error if exit code is 0 and no exception
        if run_result.exit_code == 0 and exception is None:
            return None

        # Check for timeout
        if run_result.truncated:
            return ErrorInfo(
                category=ErrorCategory.TRANSIENT,
                code=ClaudeErrorCode.TIMEOUT.value,
                message=f"Execution timed out after {run_result.elapsed_seconds:.1f}s",
                recoverable=True,
                suggestion="Reduce prompt complexity or increase timeout",
            )

        # Combine stdout and stderr for pattern matching
        combined_output = f"{run_result.stdout}\n{run_result.stderr}"

        # Check exception first
        if exception:
            return self._map_exception(exception, combined_output)

        # Match against known patterns
        for pattern, error_code, category in ERROR_PATTERNS:
            if pattern.search(combined_output):
                return ErrorInfo(
                    category=category,
                    code=error_code.value,
                    message=self._extract_error_message(combined_output, error_code),
                    recoverable=self._is_recoverable(category),
                    suggestion=self._get_suggestion(error_code),
                )

        # Empty output
        if not run_result.stdout.strip() and not run_result.stderr.strip():
            return ErrorInfo(
                category=ErrorCategory.UNKNOWN,
                code=ClaudeErrorCode.EMPTY_OUTPUT.value,
                message=f"No output received (exit code: {run_result.exit_code})",
                recoverable=True,
                suggestion="Check Claude CLI installation and authentication",
            )

        # Generic process failure
        if run_result.exit_code != 0:
            return ErrorInfo(
                category=ErrorCategory.UNKNOWN,
                code=ClaudeErrorCode.PROCESS_FAILED.value,
                message=f"Process exited with code {run_result.exit_code}",
                recoverable=True,
                suggestion="Check stderr for details",
                raw_error=run_result.stderr[:500] if run_result.stderr else None,
            )

        return None

    def _map_exception(self, exc: Exception, output: str) -> ErrorInfo:
        """Map Python exception to ErrorInfo."""
        exc_name = type(exc).__name__
        exc_msg = str(exc)

        if isinstance(exc, FileNotFoundError):
            return ErrorInfo(
                category=ErrorCategory.CONFIG,
                code=ClaudeErrorCode.NOT_FOUND.value,
                message="Claude CLI not found",
                recoverable=False,
                suggestion="Install Claude CLI: npm install -g @anthropic-ai/claude-code",
            )

        if "timeout" in exc_name.lower() or "timeout" in exc_msg.lower():
            return ErrorInfo(
                category=ErrorCategory.TRANSIENT,
                code=ClaudeErrorCode.TIMEOUT.value,
                message=f"Operation timed out: {exc_msg}",
                recoverable=True,
                suggestion="Increase timeout or simplify request",
            )

        return ErrorInfo(
            category=ErrorCategory.UNKNOWN,
            code=ClaudeErrorCode.UNKNOWN.value,
            message=f"{exc_name}: {exc_msg}",
            recoverable=True,
            suggestion="Check logs for details",
            raw_error=output[:500] if output else None,
        )

    def _extract_error_message(self, output: str, code: ClaudeErrorCode) -> str:
        """Extract a meaningful error message from output."""
        # Try to find a specific error line
        for line in output.split("\n"):
            line = line.strip()
            if line and any(word in line.lower() for word in ["error", "failed", "unable"]):
                return line[:200]

        # Fall back to code description
        return f"Claude CLI error: {code.name}"

    def _is_recoverable(self, category: ErrorCategory) -> bool:
        """Determine if error is recoverable."""
        return category in (
            ErrorCategory.TRANSIENT,
            ErrorCategory.RESOURCE,
        )

    def _get_suggestion(self, code: ClaudeErrorCode) -> str:
        """Get suggestion for specific error code."""
        suggestions = {
            ClaudeErrorCode.RATE_LIMITED: "Wait and retry, or reduce request frequency",
            ClaudeErrorCode.AUTH_FAILED: "Check ANTHROPIC_API_KEY or run 'claude login'",
            ClaudeErrorCode.QUOTA_EXCEEDED: "Check billing status or upgrade plan",
            ClaudeErrorCode.CONTEXT_TOO_LONG: "Reduce prompt length or context size",
            ClaudeErrorCode.INVALID_REQUEST: "Review and fix request parameters",
            ClaudeErrorCode.CONTENT_FILTERED: "Modify content to comply with usage policies",
            ClaudeErrorCode.NOT_FOUND: "Install Claude CLI: npm install -g @anthropic-ai/claude-code",
            ClaudeErrorCode.TIMEOUT: "Increase timeout or simplify request",
            ClaudeErrorCode.API_ERROR: "Retry after a short delay",
            ClaudeErrorCode.EMPTY_OUTPUT: "Check CLI installation and network connectivity",
        }
        return suggestions.get(code, "Check logs for details")
