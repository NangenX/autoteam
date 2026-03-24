"""Prompt sender for Copilot CLI.

Handles sending prompts to an active Copilot TTY session and
capturing responses with proper timing.
"""

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

from autoteam.adapters.copilot.tty_runner import TTYSession, TTYOutput, SessionState


class PromptMode(Enum):
    """Mode for sending prompts."""
    SIMPLE = "simple"           # Just send and wait
    MULTI_TURN = "multi_turn"   # Multiple exchanges
    WITH_CONTEXT = "with_context"  # Include file context


@dataclass
class PromptResult:
    """Result from sending a prompt."""
    success: bool
    response_text: str
    elapsed_seconds: float
    turn_count: int = 1
    permission_requests: list[str] | None = None
    final_state: SessionState = SessionState.READY
    error: str | None = None


class PromptSender:
    """Sends prompts to Copilot TTY session and captures responses.
    
    Handles:
    - Sending the initial prompt
    - Waiting for and detecting completion
    - Handling permission dialogs
    - Multi-turn conversations
    """

    def __init__(
        self,
        session: TTYSession,
        timeout_seconds: float = 120.0,
        completion_patterns: list[str] | None = None,
    ):
        self.session = session
        self.timeout_seconds = timeout_seconds
        self.completion_patterns = completion_patterns or [
            "❯",           # Copilot ready prompt
            "Completed",   # Task completed
            "Done",        # Alternative completion
        ]
        self._permission_handler: "PermissionHandler | None" = None

    def set_permission_handler(self, handler: "PermissionHandler") -> None:
        """Set handler for permission requests."""
        self._permission_handler = handler

    async def send_prompt(
        self,
        prompt: str,
        mode: PromptMode = PromptMode.SIMPLE,
        context: dict[str, Any] | None = None,
    ) -> PromptResult:
        """Send a prompt and wait for response.
        
        Args:
            prompt: The prompt text to send
            mode: Prompt mode (simple, multi_turn, with_context)
            context: Optional context for the prompt
            
        Returns:
            PromptResult with response and metadata
        """
        start_time = time.monotonic()
        collected_output: list[str] = []
        permission_requests: list[str] = []
        turn_count = 0

        try:
            # Ensure session is ready
            if self.session.state != SessionState.READY:
                await self._wait_for_ready()

            # Send the prompt
            await self.session.send(prompt)
            turn_count = 1

            # Wait for response
            while time.monotonic() - start_time < self.timeout_seconds:
                output = await self.session.read_until(
                    pattern=self._get_completion_pattern(),
                    timeout=min(5.0, self.timeout_seconds - (time.monotonic() - start_time)),
                )

                if output.text:
                    collected_output.append(output.text)

                # Check for permission request
                if self.session.state == SessionState.WAITING_INPUT:
                    if self._permission_handler:
                        permission_text = self._extract_permission_text(output.text)
                        permission_requests.append(permission_text)
                        decision = await self._permission_handler.handle(permission_text)
                        await self.session.send_control(decision)
                    else:
                        # Default: deny permissions
                        await self.session.send_control("n")

                # Check for completion
                if output.is_complete or self._is_response_complete(output.text):
                    break

                # Check if back to ready state
                if self.session.state == SessionState.READY and collected_output:
                    break

            elapsed = time.monotonic() - start_time
            response_text = "".join(collected_output)

            return PromptResult(
                success=True,
                response_text=self._clean_response(response_text),
                elapsed_seconds=elapsed,
                turn_count=turn_count,
                permission_requests=permission_requests if permission_requests else None,
                final_state=self.session.state,
            )

        except Exception as e:
            return PromptResult(
                success=False,
                response_text="".join(collected_output),
                elapsed_seconds=time.monotonic() - start_time,
                turn_count=turn_count,
                final_state=self.session.state,
                error=str(e),
            )

    async def send_multi_turn(
        self,
        prompts: list[str],
        max_turns: int = 5,
    ) -> list[PromptResult]:
        """Send multiple prompts in sequence.
        
        Args:
            prompts: List of prompts to send
            max_turns: Maximum turns per prompt
            
        Returns:
            List of PromptResult for each prompt
        """
        results = []
        for prompt in prompts[:max_turns]:
            result = await self.send_prompt(prompt)
            results.append(result)
            if not result.success:
                break
        return results

    async def _wait_for_ready(self, timeout: float = 10.0) -> bool:
        """Wait for session to become ready."""
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            if self.session.state == SessionState.READY:
                return True
            await asyncio.sleep(0.1)
        return False

    def _get_completion_pattern(self) -> str:
        """Get pattern that indicates response is complete."""
        return self.completion_patterns[0]

    def _is_response_complete(self, text: str) -> bool:
        """Check if response text indicates completion."""
        return any(pattern in text for pattern in self.completion_patterns)

    def _extract_permission_text(self, text: str) -> str:
        """Extract permission request text from output."""
        # Look for common permission patterns
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if "Allow" in line or "Permission" in line or "approve" in line.lower():
                # Return this line and context
                start = max(0, i - 2)
                end = min(len(lines), i + 3)
                return "\n".join(lines[start:end])
        return text[-500:]  # Last 500 chars as fallback

    def _clean_response(self, text: str) -> str:
        """Clean response text by removing ANSI codes and noise."""
        import re
        # Remove ANSI escape sequences
        ansi_pattern = re.compile(r'\x1b\[[0-9;]*m')
        text = ansi_pattern.sub('', text)
        
        # Remove spinner characters
        spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        for char in spinner_chars:
            text = text.replace(char, '')
        
        # Clean up excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()


class PermissionHandler:
    """Handles permission requests from Copilot CLI.
    
    Can be configured to:
    - Auto-approve certain operations
    - Auto-deny certain operations
    - Ask the user
    - Use policy rules
    """

    def __init__(
        self,
        default_action: str = "n",  # Default: deny
        auto_approve_patterns: list[str] | None = None,
        auto_deny_patterns: list[str] | None = None,
    ):
        self.default_action = default_action
        self.auto_approve_patterns = auto_approve_patterns or []
        self.auto_deny_patterns = auto_deny_patterns or [
            "delete",
            "remove",
            "overwrite",
            "execute",
            "install",
        ]

    async def handle(self, permission_text: str) -> str:
        """Handle a permission request.
        
        Args:
            permission_text: Text describing the permission request
            
        Returns:
            "y" to approve, "n" to deny
        """
        text_lower = permission_text.lower()

        # Check deny patterns first (safety)
        for pattern in self.auto_deny_patterns:
            if pattern in text_lower:
                return "n"

        # Check approve patterns
        for pattern in self.auto_approve_patterns:
            if pattern in text_lower:
                return "y"

        return self.default_action
