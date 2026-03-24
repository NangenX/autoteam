"""Run state management for orchestration."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import uuid4

from autoteam.contracts.decision_schema import JudgeDecision
from autoteam.contracts.worker_result import WorkerResult


@dataclass
class RunState:
    """State of a single orchestration run."""

    run_id: str
    requirement: str
    status: Literal["ready", "running", "done", "blocked", "failed"] = "ready"
    current_step: int = 0
    loop_count: int = 0
    workers: list[WorkerResult] = field(default_factory=list)
    decisions: list[JudgeDecision] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    finished_at: datetime | None = None

    @classmethod
    def create(cls, requirement: str) -> "RunState":
        """Create a new run with a unique ID."""
        run_id = f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:6]}"
        return cls(run_id=run_id, requirement=requirement)

    def is_active(self) -> bool:
        """Check if the run is still active."""
        return self.status in ("ready", "running")

    def is_terminal(self) -> bool:
        """Check if the run has reached a terminal state."""
        return self.status in ("done", "blocked", "failed")

    def add_worker_result(self, result: WorkerResult) -> None:
        """Add a worker result to this run."""
        self.workers.append(result)

    def add_decision(self, decision: JudgeDecision) -> None:
        """Add a judge decision to this run."""
        self.decisions.append(decision)
        if decision.should_stop():
            self.status = "done"
            self.finished_at = datetime.now()
        elif decision.should_escalate():
            self.status = "blocked"
            self.finished_at = datetime.now()

    def increment_loop(self) -> None:
        """Increment the loop counter."""
        self.loop_count += 1

    def advance_step(self) -> None:
        """Advance to the next step."""
        self.current_step += 1

    def start(self) -> None:
        """Mark the run as started."""
        self.status = "running"
        self.started_at = datetime.now()

    def complete(self) -> None:
        """Mark the run as completed successfully."""
        self.status = "done"
        self.finished_at = datetime.now()

    def fail(self, reason: str | None = None) -> None:
        """Mark the run as failed."""
        self.status = "failed"
        self.finished_at = datetime.now()

    def block(self, reason: str | None = None) -> None:
        """Mark the run as blocked (needs human intervention)."""
        self.status = "blocked"
        self.finished_at = datetime.now()

    def last_worker_result(self) -> WorkerResult | None:
        """Get the most recent worker result."""
        return self.workers[-1] if self.workers else None

    def last_decision(self) -> JudgeDecision | None:
        """Get the most recent judge decision."""
        return self.decisions[-1] if self.decisions else None

    def total_duration_ms(self) -> int | None:
        """Calculate total run duration in milliseconds."""
        if self.finished_at is None:
            return None
        delta = self.finished_at - self.started_at
        return int(delta.total_seconds() * 1000)
