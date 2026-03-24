"""Run metadata storage."""

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from autoteam.contracts import RunState


class RunStore:
    """Store and retrieve run metadata."""

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or Path("runs")
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _run_path(self, run_id: str) -> Path:
        """Get the path for a run's metadata file."""
        return self.base_dir / run_id / "run.json"

    def save_run(self, run_id: str, data: dict[str, Any]) -> None:
        """Save run metadata to disk."""
        run_dir = self.base_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        run_path = self._run_path(run_id)
        run_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def load_run(self, run_id: str) -> dict[str, Any] | None:
        """Load run metadata from disk."""
        run_path = self._run_path(run_id)
        if not run_path.exists():
            return None

        return json.loads(run_path.read_text(encoding="utf-8"))

    def list_runs(self, limit: int = 50) -> list[str]:
        """List recent run IDs."""
        runs = []
        if not self.base_dir.exists():
            return []
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
