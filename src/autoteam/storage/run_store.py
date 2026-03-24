"""Run metadata storage."""

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from autoteam.contracts import RunState


class RunStore:
    """Store and retrieve run metadata."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _run_path(self, run_id: str) -> Path:
        """Get the path for a run's metadata file."""
        return self.base_dir / run_id / "run.json"

    def save_run(self, run: RunState) -> None:
        """Save run metadata to disk."""
        run_dir = self.base_dir / run.run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        run_path = self._run_path(run.run_id)
        data = self._serialize_run(run)
        run_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def load_run(self, run_id: str) -> RunState | None:
        """Load run metadata from disk."""
        run_path = self._run_path(run_id)
        if not run_path.exists():
            return None

        data = json.loads(run_path.read_text(encoding="utf-8"))
        return self._deserialize_run(data)

    def list_runs(self, limit: int = 50) -> list[str]:
        """List recent run IDs."""
        runs = []
        for d in self.base_dir.iterdir():
            if d.is_dir() and (d / "run.json").exists():
                runs.append(d.name)

        runs.sort(reverse=True)
        return runs[:limit]

    def delete_run(self, run_id: str) -> None:
        """Delete a run and all its data."""
        import shutil

        run_dir = self.base_dir / run_id
        if run_dir.exists():
            shutil.rmtree(run_dir)

    def _serialize_run(self, run: RunState) -> dict:
        """Serialize a RunState to a dictionary."""
        return {
            "run_id": run.run_id,
            "requirement": run.requirement,
            "status": run.status,
            "current_step": run.current_step,
            "loop_count": run.loop_count,
            "workers": [self._serialize_worker(w) for w in run.workers],
            "decisions": [d.to_dict() for d in run.decisions],
            "started_at": run.started_at.isoformat(),
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        }

    def _serialize_worker(self, worker) -> dict:
        """Serialize a WorkerResult to a dictionary."""
        return {
            "worker_id": worker.worker_id,
            "vendor": worker.vendor,
            "role": worker.role,
            "run_id": worker.run_id,
            "status": worker.status,
            "summary": worker.summary,
            "raw_output_path": str(worker.raw_output_path),
            "artifacts": [{"path": str(a.path), "kind": a.kind} for a in worker.artifacts],
            "confidence": worker.confidence,
            "created_at": worker.created_at.isoformat(),
        }

    def _deserialize_run(self, data: dict) -> RunState:
        """Deserialize a dictionary to a RunState."""
        from autoteam.contracts import JudgeDecision

        run = RunState(
            run_id=data["run_id"],
            requirement=data["requirement"],
            status=data["status"],
            current_step=data["current_step"],
            loop_count=data["loop_count"],
            started_at=datetime.fromisoformat(data["started_at"]),
            finished_at=(
                datetime.fromisoformat(data["finished_at"])
                if data["finished_at"]
                else None
            ),
        )

        for d in data.get("decisions", []):
            run.decisions.append(JudgeDecision.from_dict(d))

        return run
