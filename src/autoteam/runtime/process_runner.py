"""Subprocess execution with timeout and output capture."""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass
class ProcessResult:
    """Result of a subprocess execution."""

    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool
    duration_ms: int

    def is_success(self) -> bool:
        """Check if the process completed successfully."""
        return self.exit_code == 0 and not self.timed_out


class ProcessRunner:
    """Execute subprocesses with timeout and output capture."""

    def __init__(self, default_timeout: int = 120, working_dir: Path | None = None):
        self.default_timeout = default_timeout
        self.working_dir = working_dir

    def run(
        self,
        command: list[str],
        timeout: int | None = None,
        env: dict[str, str] | None = None,
        input_text: str | None = None,
    ) -> ProcessResult:
        """Run a command and capture output."""
        import time

        effective_timeout = timeout or self.default_timeout
        start_time = time.monotonic()

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=effective_timeout,
                cwd=self.working_dir,
                env=env,
                input=input_text,
            )
            duration_ms = int((time.monotonic() - start_time) * 1000)

            return ProcessResult(
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                timed_out=False,
                duration_ms=duration_ms,
            )

        except subprocess.TimeoutExpired as e:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            return ProcessResult(
                exit_code=-1,
                stdout=e.stdout or "" if isinstance(e.stdout, str) else "",
                stderr=e.stderr or "" if isinstance(e.stderr, str) else "",
                timed_out=True,
                duration_ms=duration_ms,
            )

    def run_interactive(
        self,
        command: list[str],
        timeout: int | None = None,
    ) -> "InteractiveSession":
        """Start an interactive subprocess session."""
        return InteractiveSession(
            command=command,
            timeout=timeout or self.default_timeout,
            working_dir=self.working_dir,
        )


class InteractiveSession:
    """Interactive subprocess session with stdin/stdout control."""

    def __init__(
        self,
        command: list[str],
        timeout: int,
        working_dir: Path | None = None,
    ):
        self.command = command
        self.timeout = timeout
        self.working_dir = working_dir
        self._process: subprocess.Popen | None = None
        self._output_buffer: list[str] = []

    def start(self) -> None:
        """Start the interactive session."""
        self._process = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=self.working_dir,
        )

    def send(self, text: str) -> None:
        """Send text to stdin."""
        if self._process and self._process.stdin:
            self._process.stdin.write(text)
            self._process.stdin.flush()

    def send_line(self, text: str) -> None:
        """Send a line of text to stdin."""
        self.send(text + "\n")

    def read_available(self) -> str:
        """Read available output without blocking."""
        if not self._process or not self._process.stdout:
            return ""

        import select

        output = []
        while True:
            if select.select([self._process.stdout], [], [], 0.1)[0]:
                line = self._process.stdout.readline()
                if line:
                    output.append(line)
                    self._output_buffer.append(line)
                else:
                    break
            else:
                break

        return "".join(output)

    def wait(self, timeout: int | None = None) -> ProcessResult:
        """Wait for the process to complete."""
        import time

        if not self._process:
            return ProcessResult(
                exit_code=-1,
                stdout="",
                stderr="Process not started",
                timed_out=False,
                duration_ms=0,
            )

        effective_timeout = timeout or self.timeout
        start_time = time.monotonic()

        try:
            stdout, stderr = self._process.communicate(timeout=effective_timeout)
            duration_ms = int((time.monotonic() - start_time) * 1000)

            full_output = "".join(self._output_buffer) + (stdout or "")

            return ProcessResult(
                exit_code=self._process.returncode or 0,
                stdout=full_output,
                stderr=stderr or "",
                timed_out=False,
                duration_ms=duration_ms,
            )

        except subprocess.TimeoutExpired:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            self._process.kill()

            return ProcessResult(
                exit_code=-1,
                stdout="".join(self._output_buffer),
                stderr="",
                timed_out=True,
                duration_ms=duration_ms,
            )

    def stop(self) -> None:
        """Stop the interactive session."""
        if self._process:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()

    @property
    def is_running(self) -> bool:
        """Check if the process is still running."""
        if not self._process:
            return False
        return self._process.poll() is None
