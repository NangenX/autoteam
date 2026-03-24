"""Copilot CLI Adapter - Main adapter class.

Combines TTY runner, prompt sender, permission controller, and normalizer.
"""

from pathlib import Path
from typing import Any

from autoteam.adapters.base import BaseAdapter, AdapterCapability, AdapterConfig
from autoteam.adapters.copilot.tty_runner import TTYRunner, TTYConfig, TTYSession
from autoteam.adapters.copilot.prompt_sender import PromptSender, PromptMode, PromptResult
from autoteam.adapters.copilot.permission_controller import (
    PermissionController,
    PermissionPolicy,
    create_review_only_policy,
)
from autoteam.adapters.copilot.timeline_parser import TimelineParser
from autoteam.adapters.copilot.normalizer import CopilotNormalizer
from autoteam.contracts import WorkerResult, ResultStatus, Metrics, NextActionHint, ErrorInfo, ErrorCategory


class CopilotAdapter(BaseAdapter):
    """Copilot CLI adapter for interactive TTY execution.
    
    Unlike Claude CLI, Copilot requires an interactive terminal.
    This adapter manages:
    - TTY session lifecycle
    - Prompt sending and response capture
    - Permission handling
    - Output normalization
    
    Example:
        config = AdapterConfig(executable="copilot", timeout_seconds=120)
        adapter = CopilotAdapter(config)
        
        await adapter.start_session()
        result = await adapter.execute("Review this code: ...")
        await adapter.stop_session()
    """

    def __init__(
        self,
        config: AdapterConfig | None = None,
        worker_id: str = "copilot",
        permission_policy: PermissionPolicy | None = None,
    ):
        if config is None:
            config = AdapterConfig(executable="copilot")
        super().__init__(config)

        self.worker_id = worker_id
        self._tty_config = TTYConfig(
            executable=config.executable,
            args=config.extra_args or [],
            working_dir=config.working_dir,
            env_vars=config.env_vars,
            timeout_seconds=config.timeout_seconds,
        )
        self._runner = TTYRunner(self._tty_config)
        self._session: TTYSession | None = None
        self._prompt_sender: PromptSender | None = None
        self._permission_controller = PermissionController(
            policy=permission_policy or create_review_only_policy()
        )
        self._normalizer = CopilotNormalizer(worker_id)

    @property
    def name(self) -> str:
        return "Copilot CLI"

    @property
    def capabilities(self) -> set[AdapterCapability]:
        return {
            AdapterCapability.INTERACTIVE,
            AdapterCapability.SESSION_PERSISTENCE,
        }

    async def start_session(self) -> bool:
        """Start a new Copilot TTY session.
        
        Returns:
            True if session started successfully
        """
        if self._session and self._session.is_running:
            return True

        try:
            self._session = await self._runner.create_session()
            self._prompt_sender = PromptSender(
                session=self._session,
                timeout_seconds=self.config.timeout_seconds,
            )
            return True
        except Exception:
            return False

    async def stop_session(self) -> None:
        """Stop the current TTY session."""
        await self._runner.destroy_session()
        self._session = None
        self._prompt_sender = None

    async def execute(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
    ) -> WorkerResult:
        """Execute a prompt using Copilot CLI.
        
        If no session exists, one will be created automatically.
        
        Args:
            prompt: The task/prompt to send
            context: Optional context with:
                - mode: PromptMode - Execution mode
                - working_dir: str - Working directory
                - auto_approve: bool - Auto-approve all permissions
                
        Returns:
            Normalized WorkerResult
        """
        context = context or {}

        # Ensure session exists
        if not self._session or not self._session.is_running:
            started = await self.start_session()
            if not started:
                return self._build_error_result(
                    "Failed to start Copilot session",
                    ErrorCategory.CONFIG,
                )

        try:
            # Configure permission handling
            if context.get("auto_approve"):
                # Temporarily allow all
                old_policy = self._permission_controller.policy
                self._permission_controller.policy = PermissionPolicy(
                    default_action=PermissionPolicy.APPROVE
                )

            # Send prompt
            mode = context.get("mode", PromptMode.SIMPLE)
            prompt_result = await self._prompt_sender.send_prompt(
                prompt=prompt,
                mode=mode,
                context=context,
            )

            # Restore policy if changed
            if context.get("auto_approve"):
                self._permission_controller.policy = old_policy

            # Normalize result
            return self._normalizer.normalize(prompt_result, context)

        except Exception as e:
            return self._build_error_result(
                str(e),
                ErrorCategory.UNKNOWN,
            )

    async def health_check(self) -> bool:
        """Check if Copilot CLI is available."""
        healthy, _ = await self._runner.health_check()
        return healthy

    def _build_error_result(
        self,
        message: str,
        category: ErrorCategory,
    ) -> WorkerResult:
        """Build WorkerResult for error case."""
        from datetime import datetime, timezone

        return WorkerResult(
            worker_id=self.worker_id,
            status=ResultStatus.FAILED,
            summary=f"Error: {message}",
            raw_output="",
            artifacts=[],
            confidence=0.0,
            metrics=Metrics(duration_seconds=0),
            next_action_hint=NextActionHint(
                action="escalate",
                reason=message,
            ),
            timestamp=datetime.now(timezone.utc),
            error_info=ErrorInfo(
                category=category,
                code="COPILOT_ERROR",
                message=message,
                recoverable=category == ErrorCategory.TRANSIENT,
            ),
            vendor="copilot",
        )

    @property
    def session(self) -> TTYSession | None:
        """Get current session."""
        return self._session

    @property
    def permission_history(self) -> list:
        """Get permission handling history."""
        return self._permission_controller.get_history()


def create_copilot_adapter(
    executable: str = "copilot",
    timeout_seconds: int = 120,
    working_dir: str | None = None,
    worker_id: str = "copilot",
    review_only: bool = True,
) -> CopilotAdapter:
    """Factory function to create Copilot adapter.
    
    Args:
        executable: Path to Copilot CLI executable
        timeout_seconds: Execution timeout
        working_dir: Default working directory
        worker_id: Worker identifier
        review_only: Use review-only permission policy
        
    Returns:
        Configured CopilotAdapter instance
    """
    config = AdapterConfig(
        executable=executable,
        timeout_seconds=timeout_seconds,
        working_dir=working_dir,
    )

    policy = create_review_only_policy() if review_only else PermissionPolicy()

    return CopilotAdapter(config, worker_id, policy)
