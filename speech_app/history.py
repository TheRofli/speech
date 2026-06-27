from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .settings import default_data_dir


@dataclass(frozen=True, slots=True)
class TranscriptEntry:
    id: str
    created_at: str
    text: str
    original_text: str = ""
    processing_mode: str = "off"
    processing_status: str = "skipped"
    processing_ms: int = 0


class TranscriptHistory:
    def __init__(self, path: Path | None = None, max_entries: int = 100) -> None:
        self.path = path or default_data_dir() / "history.jsonl"
        self.max_entries = max_entries

    def add(
        self,
        text: str,
        *,
        original_text: str | None = None,
        processing_mode: str = "off",
        processing_status: str = "skipped",
        processing_ms: int = 0,
    ) -> TranscriptEntry:
        entry = TranscriptEntry(
            id=str(uuid4()),
            created_at=datetime.now(timezone.utc).isoformat(),
            text=text,
            original_text=original_text if original_text is not None else text,
            processing_mode=processing_mode,
            processing_status=processing_status,
            processing_ms=processing_ms,
        )
        entries = [entry, *self.list()]
        self._write(entries[: self.max_entries])
        return entry

    def list(self) -> list[TranscriptEntry]:
        if not self.path.exists():
            return []

        entries: list[TranscriptEntry] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
                text = str(payload.get("text", ""))
                entries.append(
                    TranscriptEntry(
                        id=str(payload["id"]),
                        created_at=str(payload["created_at"]),
                        text=text,
                        original_text=str(payload.get("original_text") or text),
                        processing_mode=str(payload.get("processing_mode", "off")),
                        processing_status=str(
                            payload.get("processing_status", "skipped")
                        ),
                        processing_ms=int(payload.get("processing_ms", 0)),
                    )
                )
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                continue
        return entries[: self.max_entries]

    def _write(self, entries: list[TranscriptEntry]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = "\n".join(
            json.dumps(asdict(entry), ensure_ascii=False) for entry in entries
        )
        self.path.write_text(data + ("\n" if data else ""), encoding="utf-8")
