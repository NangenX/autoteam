"""Run lifecycle management."""

from pathlib import Path
from typing import Callable

from autoteam.contracts import JudgeDecision, RunState, WorkerResult


class RunManager:
    """Manages the lifecycle of orchestration runs."""

    def __init__(
        self,
        runs_dir: Path,
        max_rounds: int = 5,
        on_step: Callable[[RunState, int], None] | None = None,
    ):
        self.runs_dir = runs_dir
        self.max_rounds = max_rounds
        self.on_step = on_step
        self._current_run: RunState | None = None

    def create_run(self, requirement: str) -> RunState:
        """Create a new run."""
        run = RunState.create(requirement)
        self._current_run = run

        run_dir = self.runs_dir / run.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "raw").mkdir(exist_ok=True)

        return run

    @property
    def current_run(self) -> RunState | None:
        """Get the current active run."""
        return self._current_run

    def start_run(self, run: RunState) -> None:
        """Start a run."""
        run.start()
        self._current_run = run

    def add_worker_result(self, run: RunState, result: WorkerResult) -> None:
        """Add a worker result to the run."""
        run.add_worker_result(result)

        if self.on_step:
            self.on_step(run, run.current_step)

    def add_decision(self, run: RunState, decision: JudgeDecision) -> None:
        """Add a judge decision to the run."""
        run.add_decision(decision)

    def should_continue(self, run: RunState) -> bool:
        """Check if the run should continue."""
        if run.is_terminal():
            return False

        if run.loop_count >= self.max_rounds:
            run.block("Max rounds exceeded")
            return False

        last_decision = run.last_decision()
        if last_decision and last_decision.should_stop():
            return False

        return True

    def next_loop(self, run: RunState) -> bool:
        """Advance to the next loop iteration."""
        if not self.should_continue(run):
            return False

        run.increment_loop()
        run.advance_step()
        return True

    def complete_run(self, run: RunState) -> None:
        """Mark the run as complete."""
        run.complete()
        self._current_run = None

    def fail_run(self, run: RunState, reason: str) -> None:
        """Mark the run as failed."""
        run.fail(reason)
        self._current_run = None

    def get_run_dir(self, run: RunState) -> Path:
        """Get the directory for a run."""
        return self.runs_dir / run.run_id

    def get_raw_output_path(self, run: RunState, worker_id: str) -> Path:
        """Get the path for raw worker output."""
        return self.get_run_dir(run) / "raw" / f"{worker_id}.log"
