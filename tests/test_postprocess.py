from __future__ import annotations

import unittest

from speech_app.postprocess import CorrectionResult, TranscriptPostProcessor
from speech_app.settings import AppSettings


class FakeCorrector:
    def __init__(self, output: str = "", error: Exception | None = None) -> None:
        self.output = output
        self.error = error
        self.calls: list[str] = []

    def correct(self, text: str, settings: AppSettings) -> str:
        self.calls.append(text)
        if self.error is not None:
            raise self.error
        return self.output


class TranscriptPostProcessorTests(unittest.TestCase):
    def test_off_mode_returns_original_without_loading_a_corrector(self):
        local = FakeCorrector(output="changed")
        api = FakeCorrector(output="changed")
        processor = TranscriptPostProcessor(local_corrector=local, api_corrector=api)

        result = processor.process("  Original text  ", AppSettings(ai_mode="off"))

        self.assertEqual(result.text, "Original text")
        self.assertEqual(result.original_text, "Original text")
        self.assertEqual(result.status, "skipped")
        self.assertEqual(local.calls, [])
        self.assertEqual(api.calls, [])

    def test_local_mode_returns_safe_correction(self):
        local = FakeCorrector(output="Я хочу, чтобы ты исправил ошибки.")
        processor = TranscriptPostProcessor(local_corrector=local)

        result = processor.process(
            "Я хачу штоб ты исправел ашипки.", AppSettings(ai_mode="local")
        )

        self.assertEqual(result.text, "Я хочу, чтобы ты исправил ошибки.")
        self.assertEqual(result.mode, "local")
        self.assertEqual(result.status, "applied")

    def test_local_mode_skips_text_without_cyrillic(self):
        local = FakeCorrector(output="Changed English text")
        processor = TranscriptPostProcessor(local_corrector=local)

        result = processor.process(
            "Keep this English transcript unchanged.",
            AppSettings(ai_mode="local"),
        )

        self.assertEqual(result.text, "Keep this English transcript unchanged.")
        self.assertEqual(result.status, "skipped")
        self.assertEqual(local.calls, [])

    def test_corrector_error_falls_back_to_original(self):
        local = FakeCorrector(error=RuntimeError("model unavailable"))
        processor = TranscriptPostProcessor(local_corrector=local)

        result = processor.process("Сохрани этот текст", AppSettings(ai_mode="local"))

        self.assertEqual(result.text, "Сохрани этот текст")
        self.assertEqual(result.status, "fallback")
        self.assertIn("model unavailable", result.error)

    def test_rejects_correction_that_drops_numbers_or_urls(self):
        local = FakeCorrector(output="Позвони мне завтра и открой сайт.")
        processor = TranscriptPostProcessor(local_corrector=local)
        original = "Позвони мне в 18:30 и открой https://example.com."

        result = processor.process(original, AppSettings(ai_mode="local"))

        self.assertEqual(result.text, original)
        self.assertEqual(result.status, "rejected")

    def test_rejects_empty_or_extreme_length_drift(self):
        local = FakeCorrector(output="Совсем коротко.")
        processor = TranscriptPostProcessor(local_corrector=local)
        original = "Это достаточно длинная исходная фраза, смысл которой нельзя терять."

        result = processor.process(original, AppSettings(ai_mode="local"))

        self.assertEqual(result.text, original)
        self.assertEqual(result.status, "rejected")


class CorrectionResultTests(unittest.TestCase):
    def test_result_exposes_history_metadata(self):
        result = CorrectionResult(
            original_text="сырой текст",
            text="Исправленный текст.",
            mode="local",
            status="applied",
            elapsed_ms=123,
        )

        self.assertEqual(result.history_metadata()["original_text"], "сырой текст")
        self.assertEqual(result.history_metadata()["processing_ms"], 123)


if __name__ == "__main__":
    unittest.main()
