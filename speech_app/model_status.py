from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ModelStatus:
    installed: bool
    snapshot: str
    path: Path | None
    size_mb: float

    @property
    def label(self) -> str:
        if not self.installed:
            return "Not installed"
        return f"Installed - {self.size_label}"

    @property
    def size_label(self) -> str:
        if self.size_mb >= 1024:
            return f"{self.size_mb / 1024:.2f} GB"
        return f"{self.size_mb:.1f} MB"


def find_model_status(hf_home: Path, model_id: str) -> ModelStatus:
    cache_name = "models--" + model_id.replace("/", "--")
    snapshots_dir = hf_home / "hub" / cache_name / "snapshots"
    if not snapshots_dir.exists():
        return ModelStatus(False, "", None, 0.0)

    snapshots = sorted(
        [path for path in snapshots_dir.iterdir() if path.is_dir()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not snapshots:
        return ModelStatus(False, "", None, 0.0)

    snapshot = snapshots[0]
    size = sum(path.stat().st_size for path in snapshot.rglob("*") if path.is_file())
    return ModelStatus(
        installed=True,
        snapshot=snapshot.name,
        path=snapshot,
        size_mb=round(size / (1024 * 1024), 3),
    )
