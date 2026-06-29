from __future__ import annotations

import re
import time
from collections import Counter
from dataclasses import dataclass
from difflib import SequenceMatcher

from .api_corrector import ApiCorrector
from .local_corrector import LocalCorrector
from .glossary import apply_glossary, parse_glossary
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

        corrected = apply_glossary(corrected, parse_glossary(settings.ai_glossary))
        profile = settings.ai_profile if mode == "api" else "clean"
        if not _is_safe_correction(original, corrected, profile):
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


def _is_safe_correction(original: str, corrected: str, profile: str = "clean") -> bool:
    if not corrected:
        return False
    ratio = len(corrected) / max(1, len(original))
    lower, upper, retention_floor = (
        (0.65, 1.45, 0.55) if profile == "refine" else (0.80, 1.25, 0.75)
    )
    if ratio < lower or ratio > upper:
        return False
    if _introduces_assistant_formatting(original, corrected):
        return False
    if _fuzzy_token_retention(original, corrected) < retention_floor:
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


def _introduces_assistant_formatting(original: str, corrected: str) -> bool:
    markdown_patterns = (
        r"(?m)^\s{0,3}#{1,6}\s+",
        r"(?m)^\s*(?:[-*+]\s+|\d+[.)]\s+)",
        r"\*\*[^*]+\*\*",
    )
    if any(re.search(pattern, corrected) and not re.search(pattern, original) for pattern in markdown_patterns):
        return True
    if _contains_emoji(corrected) and not _contains_emoji(original):
        return True
    opening = corrected[:220].casefold()
    source = original[:220].casefold()
    assistant_openings = (
        "спасибо за описание",
        "я не вижу",
        "что нужно сделать",
        "here is",
        "i can't",
        "i cannot",
        "thanks for the description",
    )
    return any(marker in opening and marker not in source for marker in assistant_openings)


def _contains_emoji(value: str) -> bool:
    return bool(
        re.search(
            "["
            "\U0001F300-\U0001FAFF"
            "\U00002600-\U000027BF"
            "]",
            value,
        )
    )


def _fuzzy_token_retention(original: str, corrected: str) -> float:
    source = re.findall(r"\w+", original.casefold(), flags=re.UNICODE)
    target = re.findall(r"\w+", corrected.casefold(), flags=re.UNICODE)
    if not source:
        return 1.0

    source_counts = Counter(source)
    target_counts = Counter(target)
    exact = sum(min(count, target_counts[token]) for token, count in source_counts.items())
    source_remaining: list[str] = []
    target_remaining: list[str] = []
    for token, count in source_counts.items():
        source_remaining.extend([token] * max(0, count - target_counts[token]))
    for token, count in target_counts.items():
        target_remaining.extend([token] * max(0, count - source_counts[token]))

    fuzzy = 0
    for token in source_remaining:
        best_index = -1
        best_score = 0.0
        for index, candidate in enumerate(target_remaining):
            score = SequenceMatcher(None, token, candidate).ratio()
            if score > best_score:
                best_score = score
                best_index = index
        if best_index >= 0 and best_score >= 0.65:
            fuzzy += 1
            target_remaining.pop(best_index)
    return (exact + fuzzy) / len(source)
