"""Transcript storage for raw CLI outputs."""

import json
from datetime import datetime
from pathlib import Path


class TranscriptStore:
    """Store raw CLI output transcripts."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_transcript(
        self,
        run_id: str,
        worker_id: str,
        content: str,
        metadata: dict | None = None,
    ) -> Path:
        """Save a transcript for a worker."""
        run_dir = self.base_dir / run_id / "raw"
        run_dir.mkdir(parents=True, exist_ok=True)

        transcript_path = run_dir / f"{worker_id}.log"
        transcript_path.write_text(content, encoding="utf-8")

        if metadata:
            meta_path = run_dir / f"{worker_id}.meta.json"
            meta_path.write_text(
                json.dumps(
                    {
                        **metadata,
                        "saved_at": datetime.now().isoformat(),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

        return transcript_path

    def load_transcript(self, run_id: str, worker_id: str) -> str | None:
        """Load a transcript for a worker."""
        transcript_path = self.base_dir / run_id / "raw" / f"{worker_id}.log"
        if transcript_path.exists():
            return transcript_path.read_text(encoding="utf-8")
        return None

    def load_metadata(self, run_id: str, worker_id: str) -> dict | None:
        """Load metadata for a worker transcript."""
        meta_path = self.base_dir / run_id / "raw" / f"{worker_id}.meta.json"
        if meta_path.exists():
            return json.loads(meta_path.read_text(encoding="utf-8"))
        return None

    def list_transcripts(self, run_id: str) -> list[str]:
        """List all worker IDs with transcripts for a run."""
        run_dir = self.base_dir / run_id / "raw"
        if not run_dir.exists():
            return []

        return [
            f.stem
            for f in run_dir.glob("*.log")
        ]

    def delete_run(self, run_id: str) -> None:
        """Delete all transcripts for a run."""
        import shutil

        run_dir = self.base_dir / run_id
        if run_dir.exists():
            shutil.rmtree(run_dir)
