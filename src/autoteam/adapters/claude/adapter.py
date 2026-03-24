"""Claude CLI Adapter - Main adapter class.

Combines runner, parser, normalizer, and error mapper into a complete adapter.
"""

from pathlib import Path
from typing import Any

from autoteam.adapters.base import BaseAdapter, AdapterCapability, AdapterConfig
from autoteam.adapters.claude.runner import ClaudeRunner, ClaudeRunResult
from autoteam.adapters.claude.parser import ClaudeOutputParser, ParsedOutput
from autoteam.adapters.claude.normalizer import ClaudeNormalizer
from autoteam.adapters.claude.error_mapper import ClaudeErrorMapper
from autoteam.contracts import WorkerResult, ResultStatus, ErrorInfo


class ClaudeAdapter(BaseAdapter):
    """Claude CLI adapter for non-interactive execution.
    
    Uses `claude -p` for prompt-based execution. Supports:
    - Plain text output
    - JSON structured output
    - System prompts
    - Tool restrictions
    - Timeout handling
    
    Example:
        config = AdapterConfig(executable="claude", timeout_seconds=120)
        adapter = ClaudeAdapter(config)
        result = await adapter.execute("Analyze this code: ...")
    """

    def __init__(
        self,
        config: AdapterConfig | None = None,
        worker_id: str = "claude",
    ):
        if config is None:
            config = AdapterConfig(executable="claude")
        super().__init__(config)
        
        self.worker_id = worker_id
        self._runner = ClaudeRunner(config)
        self._parser = ClaudeOutputParser()
        self._normalizer = ClaudeNormalizer(worker_id)
        self._error_mapper = ClaudeErrorMapper()

    @property
    def name(self) -> str:
        return "Claude CLI"

    @property
    def capabilities(self) -> set[AdapterCapability]:
        return {
            AdapterCapability.NON_INTERACTIVE,
            AdapterCapability.JSON_OUTPUT,
        }

    async def execute(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
    ) -> WorkerResult:
        """Execute a prompt using Claude CLI.
        
        Args:
            prompt: The task/prompt to send
            context: Optional context with:
                - system_prompt: str - System prompt for Claude
                - json_output: bool - Request JSON output
                - working_dir: str - Working directory
                - allowed_tools: list[str] - Tools to allow
                - disallowed_tools: list[str] - Tools to disallow
                - max_turns: int - Max agentic turns
                
        Returns:
            Normalized WorkerResult
        """
        context = context or {}
        exception: Exception | None = None
        run_result: ClaudeRunResult | None = None
        parsed: ParsedOutput | None = None

        try:
            # Execute Claude CLI
            run_result = await self._runner.run(
                prompt=prompt,
                json_output=context.get("json_output", False),
                system_prompt=context.get("system_prompt"),
                allowed_tools=context.get("allowed_tools"),
                disallowed_tools=context.get("disallowed_tools"),
                max_turns=context.get("max_turns"),
                working_dir=Path(context["working_dir"]) if context.get("working_dir") else None,
            )

            # Parse output
            parsed = self._parser.parse(run_result.stdout)

        except Exception as e:
            exception = e
            if run_result is None:
                # Create a failed result
                run_result = ClaudeRunResult(
                    stdout="",
                    stderr=str(e),
                    exit_code=-1,
                    elapsed_seconds=0,
                )
            if parsed is None:
                parsed = ParsedOutput(
                    format=None,  # type: ignore
                    raw_text="",
                )

        # Check for errors
        error_info = self._error_mapper.map_error(run_result, exception)

        if error_info:
            return self._build_error_result(error_info, run_result, prompt)

        # Normalize to WorkerResult
        return self._normalizer.normalize(
            run_result=run_result,
            parsed=parsed,
            prompt=prompt,
            context=context,
        )

    async def health_check(self) -> bool:
        """Check if Claude CLI is available."""
        healthy, _ = await self._runner.health_check()
        return healthy

    async def get_version(self) -> str | None:
        """Get Claude CLI version."""
        healthy, message = await self._runner.health_check()
        if healthy:
            # Extract version from message
            return message.split(":")[-1].strip() if ":" in message else message
        return None

    def _build_error_result(
        self,
        error_info: ErrorInfo,
        run_result: ClaudeRunResult,
        prompt: str,
    ) -> WorkerResult:
        """Build WorkerResult for error case."""
        from datetime import datetime, timezone
        from autoteam.contracts import Metrics, NextActionHint

        return WorkerResult(
            worker_id=self.worker_id,
            status=ResultStatus.FAILED,
            summary=f"Error: {error_info.message}",
            raw_output=run_result.stdout if run_result else "",
            artifacts=[],
            confidence=0.0,
            metrics=Metrics(
                duration_seconds=run_result.elapsed_seconds if run_result else 0,
            ),
            next_action_hint=NextActionHint(
                action="retry" if error_info.recoverable else "escalate",
                reason=error_info.suggestion or error_info.message,
                suggested_target=None,
            ),
            timestamp=datetime.now(timezone.utc),
            error_info=error_info,
        )


def create_claude_adapter(
    executable: str = "claude",
    timeout_seconds: int = 120,
    max_retries: int = 2,
    working_dir: str | None = None,
    worker_id: str = "claude",
) -> ClaudeAdapter:
    """Factory function to create Claude adapter.
    
    Args:
        executable: Path to Claude CLI executable
        timeout_seconds: Execution timeout
        max_retries: Max retry attempts
        working_dir: Default working directory
        worker_id: Worker identifier for tracking
        
    Returns:
        Configured ClaudeAdapter instance
    """
    config = AdapterConfig(
        executable=executable,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        working_dir=working_dir,
    )
    return ClaudeAdapter(config, worker_id)
