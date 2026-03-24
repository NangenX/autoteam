"""Claude CLI runner for non-interactive execution.

Uses `claude -p` for prompt-based execution with optional JSON output.
"""

import asyncio
import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from autoteam.adapters.base import AdapterConfig


@dataclass
class ClaudeRunResult:
    """Raw result from Claude CLI execution."""
    stdout: str
    stderr: str
    exit_code: int
    elapsed_seconds: float
    truncated: bool = False


class ClaudeRunner:
    """Executes Claude CLI in non-interactive mode.
    
    Claude Code CLI supports:
    - `claude -p "prompt"` - Send prompt, get response, exit
    - `claude -p "prompt" --output-format json` - Get JSON structured output
    - `claude --print` - Print without interactivity
    
    This runner focuses on the `-p` (prompt) mode.
    """

    def __init__(self, config: AdapterConfig):
        self.config = config
        self._executable = config.executable or self._find_executable()

    def _find_executable(self) -> str:
        """Locate Claude CLI executable."""
        # Try common locations
        candidates = [
            "claude",
            "claude.exe",
            shutil.which("claude"),
        ]
        for candidate in candidates:
            if candidate and shutil.which(candidate):
                return candidate
        raise FileNotFoundError("Claude CLI not found. Install with: npm install -g @anthropic-ai/claude-code")

    def _build_command(
        self,
        prompt: str,
        json_output: bool = False,
        system_prompt: str | None = None,
        allowed_tools: list[str] | None = None,
        disallowed_tools: list[str] | None = None,
        max_turns: int | None = None,
    ) -> list[str]:
        """Build the claude CLI command."""
        cmd = [self._executable, "-p", prompt]

        if json_output:
            cmd.extend(["--output-format", "json"])

        if system_prompt:
            cmd.extend(["--system-prompt", system_prompt])

        if allowed_tools:
            for tool in allowed_tools:
                cmd.extend(["--allowedTools", tool])

        if disallowed_tools:
            for tool in disallowed_tools:
                cmd.extend(["--disallowedTools", tool])

        if max_turns is not None:
            cmd.extend(["--max-turns", str(max_turns)])

        # Add extra args from config
        if self.config.extra_args:
            cmd.extend(self.config.extra_args)

        return cmd

    async def run(
        self,
        prompt: str,
        json_output: bool = False,
        system_prompt: str | None = None,
        allowed_tools: list[str] | None = None,
        disallowed_tools: list[str] | None = None,
        max_turns: int | None = None,
        working_dir: Path | None = None,
    ) -> ClaudeRunResult:
        """Execute Claude CLI with the given prompt.
        
        Args:
            prompt: The prompt to send
            json_output: Request JSON structured output
            system_prompt: Optional system prompt
            allowed_tools: List of tools to allow
            disallowed_tools: List of tools to disallow
            max_turns: Maximum agentic turns
            working_dir: Working directory for execution
            
        Returns:
            ClaudeRunResult with stdout, stderr, exit_code
        """
        cmd = self._build_command(
            prompt=prompt,
            json_output=json_output,
            system_prompt=system_prompt,
            allowed_tools=allowed_tools,
            disallowed_tools=disallowed_tools,
            max_turns=max_turns,
        )

        env = None
        if self.config.env_vars:
            import os
            env = os.environ.copy()
            env.update(self.config.env_vars)

        cwd = working_dir or (Path(self.config.working_dir) if self.config.working_dir else None)

        import time
        start = time.monotonic()

        try:
            proc = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd,
                    env=env,
                ),
                timeout=5,  # Timeout for starting process
            )

            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=self.config.timeout_seconds,
            )

            elapsed = time.monotonic() - start

            return ClaudeRunResult(
                stdout=stdout_bytes.decode("utf-8", errors="replace"),
                stderr=stderr_bytes.decode("utf-8", errors="replace"),
                exit_code=proc.returncode or 0,
                elapsed_seconds=elapsed,
            )

        except asyncio.TimeoutError:
            elapsed = time.monotonic() - start
            return ClaudeRunResult(
                stdout="",
                stderr=f"Timeout after {self.config.timeout_seconds}s",
                exit_code=-1,
                elapsed_seconds=elapsed,
                truncated=True,
            )

    async def health_check(self) -> tuple[bool, str]:
        """Check if Claude CLI is available.
        
        Returns:
            Tuple of (is_healthy, message)
        """
        try:
            cmd = [self._executable, "--version"]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            version = stdout.decode().strip()
            return True, f"Claude CLI available: {version}"
        except FileNotFoundError:
            return False, "Claude CLI not found"
        except Exception as e:
            return False, f"Health check failed: {e}"


class ClaudeJsonRunner(ClaudeRunner):
    """Convenience runner that always requests JSON output."""

    async def run_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
        working_dir: Path | None = None,
    ) -> tuple[ClaudeRunResult, dict[str, Any] | None]:
        """Run Claude CLI and parse JSON output.
        
        Returns:
            Tuple of (raw_result, parsed_json or None)
        """
        result = await self.run(
            prompt=prompt,
            json_output=True,
            system_prompt=system_prompt,
            working_dir=working_dir,
        )

        parsed = None
        if result.exit_code == 0 and result.stdout:
            try:
                parsed = json.loads(result.stdout)
            except json.JSONDecodeError:
                pass

        return result, parsed
