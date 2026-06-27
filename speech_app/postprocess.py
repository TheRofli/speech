from __future__ import annotations

import re
import time
from dataclasses import dataclass

from .api_corrector import ApiCorrector
from .local_corrector import LocalCorrector
from .settings import AppSettings


@dataclass(frozen=True, slots=True)
class CorrectionResult:
    original_text: str
    text: str
    mode: str
    status: str
    elapsed_ms: int
    error: str = ""

    def history_metadata(self) -> dict[str, object]:
        return {
            "original_text": self.original_text,
            "processing_mode": self.mode,
            "processing_status": self.status,
            "processing_ms": self.elapsed_ms,
        }


class TranscriptPostProcessor:
    def __init__(self, local_corrector=None, api_corrector=None) -> None:
        self.local_corrector = local_corrector or LocalCorrector()
        self.api_corrector = api_corrector or ApiCorrector()

    def load(self, settings: AppSettings) -> None:
        if settings.ai_mode.lower() == "local":
            self.local_corrector.load(settings)

    def unload(self) -> None:
        for corrector in (self.local_corrector, self.api_corrector):
            unload = getattr(corrector, "unload", None)
            if unload is not None:
                unload()

    def process(self, text: str, settings: AppSettings) -> CorrectionResult:
        original = text.strip()
        mode = settings.ai_mode.strip().lower()
        started = time.perf_counter()
        if not original or mode == "off":
            return CorrectionResult(original, original, "off", "skipped", 0)
        if mode == "local" and not re.search(r"[А-Яа-яЁё]", original):
            return CorrectionResult(original, original, mode, "skipped", 0)

        try:
            if mode == "local":
                corrected = self.local_corrector.correct(original, settings).strip()
            elif mode == "api":
                corrected = self.api_corrector.correct(original, settings).strip()
            else:
                raise RuntimeError(f"Unsupported AI mode: {settings.ai_mode}")
        except Exception as exc:
            return CorrectionResult(
                original,
                original,
                mode,
                "fallback",
                _elapsed_ms(started),
                str(exc),
            )

        if not _is_safe_correction(original, corrected):
            return CorrectionResult(
                original,
                original,
                mode,
                "rejected",
                _elapsed_ms(started),
                "Correction failed safety validation",
            )
        return CorrectionResult(
            original,
            corrected,
            mode,
            "applied" if corrected != original else "unchanged",
            _elapsed_ms(started),
        )


def _elapsed_ms(started: float) -> int:
    return max(0, round((time.perf_counter() - started) * 1000))


def _is_safe_correction(original: str, corrected: str) -> bool:
    if not corrected:
        return False
    ratio = len(corrected) / max(1, len(original))
    if ratio < 0.55 or ratio > 1.65:
        return False
    for pattern in (
        r"https?://[^\s]+",
        r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b",
        r"\b\d+(?::\d+|[.,]\d+)?\b",
        r"\b[A-Z][A-Z0-9_-]{1,}\b",
    ):
        source_tokens = re.findall(pattern, original)
        if any(token not in corrected for token in source_tokens):
            return False
    return True
