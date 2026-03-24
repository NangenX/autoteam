"""Session registry for tracking CLI sessions."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass
class SessionInfo:
    """Information about an active CLI session."""

    session_id: str
    vendor: Literal["claude", "copilot"]
    role: str
    run_id: str
    status: Literal["active", "completed", "failed", "terminated"] = "active"
    created_at: datetime = field(default_factory=datetime.now)
    finished_at: datetime | None = None
    pid: int | None = None

    def is_active(self) -> bool:
        """Check if the session is still active."""
        return self.status == "active"

    def complete(self) -> None:
        """Mark the session as completed."""
        self.status = "completed"
        self.finished_at = datetime.now()

    def fail(self) -> None:
        """Mark the session as failed."""
        self.status = "failed"
        self.finished_at = datetime.now()

    def terminate(self) -> None:
        """Mark the session as terminated."""
        self.status = "terminated"
        self.finished_at = datetime.now()


class SessionRegistry:
    """Registry for tracking CLI sessions across runs."""

    def __init__(self):
        self._sessions: dict[str, SessionInfo] = {}
        self._counter: int = 0

    def create_session(
        self,
        vendor: Literal["claude", "copilot"],
        role: str,
        run_id: str,
        pid: int | None = None,
    ) -> SessionInfo:
        """Create and register a new session."""
        self._counter += 1
        session_id = f"{vendor}-{role}-{self._counter}"

        session = SessionInfo(
            session_id=session_id,
            vendor=vendor,
            role=role,
            run_id=run_id,
            pid=pid,
        )

        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> SessionInfo | None:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    def get_active_sessions(self) -> list[SessionInfo]:
        """Get all active sessions."""
        return [s for s in self._sessions.values() if s.is_active()]

    def get_sessions_for_run(self, run_id: str) -> list[SessionInfo]:
        """Get all sessions for a specific run."""
        return [s for s in self._sessions.values() if s.run_id == run_id]

    def complete_session(self, session_id: str) -> None:
        """Mark a session as completed."""
        if session := self._sessions.get(session_id):
            session.complete()

    def fail_session(self, session_id: str) -> None:
        """Mark a session as failed."""
        if session := self._sessions.get(session_id):
            session.fail()

    def terminate_session(self, session_id: str) -> None:
        """Mark a session as terminated."""
        if session := self._sessions.get(session_id):
            session.terminate()

    def cleanup_run(self, run_id: str) -> None:
        """Cleanup all sessions for a run."""
        for session in self.get_sessions_for_run(run_id):
            if session.is_active():
                session.terminate()

    def clear(self) -> None:
        """Clear all sessions."""
        self._sessions.clear()
        self._counter = 0
