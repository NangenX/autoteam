"""TTY Runner for Copilot CLI.

Copilot CLI requires an interactive terminal (TTY) for execution.
This module provides PTY-based session management for Windows and Unix.
"""

import asyncio
import os
import signal
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable

# Platform-specific imports
if sys.platform == "win32":
    import subprocess
    # Windows uses ConPTY via winpty or similar
    HAS_PTY = False
else:
    import pty
    import termios
    import fcntl
    HAS_PTY = True


class SessionState(Enum):
    """State of a TTY session."""
    CREATED = "created"
    STARTING = "starting"
    READY = "ready"
    BUSY = "busy"
    WAITING_INPUT = "waiting_input"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class TTYConfig:
    """Configuration for TTY runner."""
    executable: str = "copilot"
    args: list[str] = field(default_factory=list)
    working_dir: str | None = None
    env_vars: dict[str, str] | None = None
    timeout_seconds: int = 120
    read_timeout_seconds: float = 0.5
    buffer_size: int = 4096
    # Patterns to detect state
    ready_pattern: str = "❯"  # Copilot prompt indicator
    thinking_pattern: str = "Thinking"
    permission_pattern: str = "Allow"


@dataclass
class TTYOutput:
    """Output captured from TTY session."""
    text: str
    timestamp: float
    is_complete: bool = False
    detected_state: SessionState = SessionState.BUSY


class TTYSession:
    """Manages an interactive TTY session with Copilot CLI.
    
    On Unix: Uses PTY (pseudo-terminal)
    On Windows: Uses subprocess with ConPTY wrapper
    """

    def __init__(self, config: TTYConfig):
        self.config = config
        self.state = SessionState.CREATED
        self._process: asyncio.subprocess.Process | None = None
        self._master_fd: int | None = None
        self._output_buffer: list[str] = []
        self._callbacks: list[Callable[[str], None]] = []
        self._read_task: asyncio.Task | None = None

    async def start(self) -> bool:
        """Start the TTY session.
        
        Returns:
            True if session started successfully
        """
        self.state = SessionState.STARTING
        
        try:
            if HAS_PTY:
                return await self._start_pty()
            else:
                return await self._start_subprocess()
        except Exception as e:
            self.state = SessionState.ERROR
            raise RuntimeError(f"Failed to start TTY session: {e}")

    async def _start_pty(self) -> bool:
        """Start session using Unix PTY."""
        # Create pseudo-terminal
        master_fd, slave_fd = pty.openpty()
        self._master_fd = master_fd

        # Set non-blocking
        flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
        fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        # Build command
        cmd = [self.config.executable] + self.config.args

        # Environment
        env = os.environ.copy()
        if self.config.env_vars:
            env.update(self.config.env_vars)

        # Start process
        self._process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            cwd=self.config.working_dir,
            env=env,
            start_new_session=True,
        )

        os.close(slave_fd)

        # Start output reader
        self._read_task = asyncio.create_task(self._read_output_loop())
        
        # Wait for ready state
        ready = await self._wait_for_ready()
        if ready:
            self.state = SessionState.READY
        return ready

    async def _start_subprocess(self) -> bool:
        """Start session using Windows subprocess (limited TTY emulation)."""
        cmd = [self.config.executable] + self.config.args

        env = os.environ.copy()
        if self.config.env_vars:
            env.update(self.config.env_vars)

        # On Windows, we use PIPE and emulate interaction
        # Note: This is limited compared to real PTY
        self._process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=self.config.working_dir,
            env=env,
        )

        # Start output reader
        self._read_task = asyncio.create_task(self._read_subprocess_loop())

        # Wait for ready
        ready = await self._wait_for_ready()
        if ready:
            self.state = SessionState.READY
        return ready

    async def _read_output_loop(self) -> None:
        """Read output from PTY master fd."""
        loop = asyncio.get_event_loop()
        
        while self._master_fd is not None and self.state not in (SessionState.STOPPED, SessionState.ERROR):
            try:
                # Read with timeout
                data = await asyncio.wait_for(
                    loop.run_in_executor(None, self._read_master),
                    timeout=self.config.read_timeout_seconds,
                )
                if data:
                    self._handle_output(data)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                if self.state != SessionState.STOPPED:
                    self.state = SessionState.ERROR
                break

    def _read_master(self) -> str:
        """Blocking read from master fd."""
        try:
            data = os.read(self._master_fd, self.config.buffer_size)
            return data.decode("utf-8", errors="replace")
        except OSError:
            return ""

    async def _read_subprocess_loop(self) -> None:
        """Read output from subprocess stdout."""
        while self._process and self.state not in (SessionState.STOPPED, SessionState.ERROR):
            try:
                data = await asyncio.wait_for(
                    self._process.stdout.read(self.config.buffer_size),
                    timeout=self.config.read_timeout_seconds,
                )
                if data:
                    self._handle_output(data.decode("utf-8", errors="replace"))
                elif self._process.returncode is not None:
                    break
            except asyncio.TimeoutError:
                continue
            except Exception:
                break

    def _handle_output(self, text: str) -> None:
        """Process incoming output."""
        self._output_buffer.append(text)
        
        # Detect state from output
        if self.config.ready_pattern in text:
            self.state = SessionState.READY
        elif self.config.thinking_pattern in text:
            self.state = SessionState.BUSY
        elif self.config.permission_pattern in text:
            self.state = SessionState.WAITING_INPUT

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(text)
            except Exception:
                pass

    async def _wait_for_ready(self, timeout: float = 30.0) -> bool:
        """Wait for session to become ready."""
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            if self.state == SessionState.READY:
                return True
            if self.state == SessionState.ERROR:
                return False
            await asyncio.sleep(0.1)
        return False

    async def send(self, text: str) -> None:
        """Send text to the session.
        
        Args:
            text: Text to send (newline added automatically)
        """
        if self.state in (SessionState.STOPPED, SessionState.ERROR):
            raise RuntimeError("Session not running")

        data = (text + "\n").encode("utf-8")

        if HAS_PTY and self._master_fd:
            os.write(self._master_fd, data)
        elif self._process and self._process.stdin:
            self._process.stdin.write(data)
            await self._process.stdin.drain()

    async def send_control(self, key: str) -> None:
        """Send control character.
        
        Args:
            key: Control key name (e.g., 'c' for Ctrl+C)
        """
        ctrl_map = {
            "c": b"\x03",  # Ctrl+C
            "d": b"\x04",  # Ctrl+D (EOF)
            "z": b"\x1a",  # Ctrl+Z
            "enter": b"\n",
            "up": b"\x1b[A",
            "down": b"\x1b[B",
            "left": b"\x1b[D",
            "right": b"\x1b[C",
            "tab": b"\t",
            "y": b"y",
            "n": b"n",
        }

        data = ctrl_map.get(key.lower(), key.encode("utf-8"))

        if HAS_PTY and self._master_fd:
            os.write(self._master_fd, data)
        elif self._process and self._process.stdin:
            self._process.stdin.write(data)
            await self._process.stdin.drain()

    async def read_until(
        self,
        pattern: str,
        timeout: float | None = None,
    ) -> TTYOutput:
        """Read output until pattern is found or timeout.
        
        Args:
            pattern: Pattern to wait for
            timeout: Timeout in seconds
            
        Returns:
            TTYOutput with captured text
        """
        timeout = timeout or self.config.timeout_seconds
        start = time.monotonic()
        collected = []

        while time.monotonic() - start < timeout:
            if self._output_buffer:
                chunk = self._output_buffer.pop(0)
                collected.append(chunk)
                
                full_text = "".join(collected)
                if pattern in full_text:
                    return TTYOutput(
                        text=full_text,
                        timestamp=time.monotonic(),
                        is_complete=True,
                        detected_state=self.state,
                    )
            await asyncio.sleep(0.05)

        return TTYOutput(
            text="".join(collected),
            timestamp=time.monotonic(),
            is_complete=False,
            detected_state=self.state,
        )

    def get_buffer(self) -> str:
        """Get and clear current output buffer."""
        text = "".join(self._output_buffer)
        self._output_buffer.clear()
        return text

    def add_callback(self, callback: Callable[[str], None]) -> None:
        """Add output callback."""
        self._callbacks.append(callback)

    async def stop(self) -> None:
        """Stop the TTY session."""
        self.state = SessionState.STOPPED

        # Cancel read task
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass

        # Close master fd
        if self._master_fd:
            try:
                os.close(self._master_fd)
            except OSError:
                pass
            self._master_fd = None

        # Terminate process
        if self._process:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._process.kill()
            except Exception:
                pass
            self._process = None

    @property
    def is_running(self) -> bool:
        """Check if session is running."""
        return self.state not in (SessionState.STOPPED, SessionState.ERROR, SessionState.CREATED)


class TTYRunner:
    """High-level TTY runner for Copilot CLI."""

    def __init__(self, config: TTYConfig | None = None):
        self.config = config or TTYConfig()
        self._session: TTYSession | None = None

    async def create_session(self) -> TTYSession:
        """Create and start a new TTY session."""
        session = TTYSession(self.config)
        await session.start()
        self._session = session
        return session

    async def destroy_session(self) -> None:
        """Stop and destroy current session."""
        if self._session:
            await self._session.stop()
            self._session = None

    @property
    def session(self) -> TTYSession | None:
        """Get current session."""
        return self._session

    async def health_check(self) -> tuple[bool, str]:
        """Check if Copilot CLI is available."""
        import shutil
        
        exe = shutil.which(self.config.executable)
        if exe:
            return True, f"Copilot CLI found: {exe}"
        return False, "Copilot CLI not found"
