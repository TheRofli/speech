import json
import tempfile
import unittest
from pathlib import Path

from speech_app.history import TranscriptHistory
from speech_app.output import TranscriptPublisher
from speech_app.runtime_state import write_runtime_state
from speech_app.settings import AppSettings, SettingsStore
from speech_app.app import build_parser


class SettingsStoreTests(unittest.TestCase):
    def test_loads_defaults_when_file_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SettingsStore(Path(tmp) / "settings.json")

            settings = store.load()

            self.assertEqual(settings.model_id, "nvidia/parakeet-tdt-0.6b-v3")
            self.assertEqual(settings.device, "cpu")
            self.assertEqual(settings.hotkey, "ctrl+win")
            self.assertTrue(settings.copy_to_clipboard)
            self.assertTrue(settings.paste_to_active_input)
            self.assertTrue(settings.preload_model)
            self.assertEqual(settings.ai_mode, "off")
            self.assertEqual(
                settings.ai_local_model_id,
                "ai-forever/sage-fredt5-distilled-95m",
            )

    def test_round_trips_known_settings_and_ignores_unknown_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            path.write_text(
                json.dumps(
                    {
                        "device": "cuda",
                        "backend": "nemo",
                        "engine_enabled": False,
                        "unknown_future_field": "kept out",
                    }
                ),
                encoding="utf-8",
            )
            store = SettingsStore(path)

            settings = store.load()
            store.save(settings)
            reloaded = json.loads(path.read_text(encoding="utf-8"))

            self.assertEqual(settings.device, "cuda")
            self.assertEqual(settings.backend, "nemo")
            self.assertFalse(settings.engine_enabled)
            self.assertNotIn("unknown_future_field", reloaded)


class TranscriptHistoryTests(unittest.TestCase):
    def test_add_records_newest_entries_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            history = TranscriptHistory(Path(tmp) / "history.jsonl", max_entries=3)

            first = history.add("first")
            second = history.add("second")

            entries = history.list()
            self.assertEqual([entry.text for entry in entries], ["second", "first"])
            self.assertNotEqual(first.id, second.id)

    def test_history_is_trimmed_to_max_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            history = TranscriptHistory(Path(tmp) / "history.jsonl", max_entries=2)

            history.add("one")
            history.add("two")
            history.add("three")

            self.assertEqual([entry.text for entry in history.list()], ["three", "two"])

    def test_history_reads_legacy_rows_and_persists_correction_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "history.jsonl"
            path.write_text(
                json.dumps(
                    {
                        "id": "legacy",
                        "created_at": "2026-01-01T00:00:00+00:00",
                        "text": "legacy text",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            history = TranscriptHistory(path)

            legacy = history.list()[0]
            corrected = history.add(
                "Corrected text",
                original_text="raw text",
                processing_mode="local",
                processing_status="applied",
                processing_ms=240,
            )

            self.assertEqual(legacy.original_text, "legacy text")
            self.assertEqual(legacy.processing_mode, "off")
            self.assertEqual(corrected.original_text, "raw text")
            self.assertEqual(corrected.processing_status, "applied")
            self.assertEqual(corrected.processing_ms, 240)


class TranscriptPublisherTests(unittest.TestCase):
    def test_publish_saves_to_clipboard_history_and_pastes_when_enabled(self):
        clipboard = []
        pasted = []
        with tempfile.TemporaryDirectory() as tmp:
            history = TranscriptHistory(Path(tmp) / "history.jsonl")
            publisher = TranscriptPublisher(
                history=history,
                set_clipboard=clipboard.append,
                paste_active_input=lambda text: pasted.append(text),
            )

            entry = publisher.publish(" hello world ", AppSettings())

            self.assertEqual(entry.text, "hello world")
            self.assertEqual(clipboard, ["hello world"])
            self.assertEqual(pasted, ["hello world"])
            self.assertEqual(history.list()[0].text, "hello world")

    def test_publish_records_original_and_processing_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            history = TranscriptHistory(Path(tmp) / "history.jsonl")
            publisher = TranscriptPublisher(
                history=history,
                set_clipboard=lambda _text: None,
                paste_active_input=lambda _text: None,
            )

            entry = publisher.publish(
                "Corrected text",
                AppSettings(),
                original_text="raw text",
                processing_mode="local",
                processing_status="applied",
                processing_ms=180,
            )

            self.assertEqual(entry.original_text, "raw text")
            self.assertEqual(entry.processing_mode, "local")
            self.assertEqual(entry.processing_ms, 180)

    def test_publish_skips_empty_transcripts(self):
        clipboard = []
        with tempfile.TemporaryDirectory() as tmp:
            history = TranscriptHistory(Path(tmp) / "history.jsonl")
            publisher = TranscriptPublisher(
                history=history,
                set_clipboard=clipboard.append,
                paste_active_input=lambda text: None,
            )

            entry = publisher.publish("   ", AppSettings())

            self.assertIsNone(entry)
            self.assertEqual(clipboard, [])
            self.assertEqual(history.list(), [])


class RuntimeStateTests(unittest.TestCase):
    def test_runtime_state_records_model_loading_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runtime_state.json"

            write_runtime_state(
                "loading",
                AppSettings(device="cpu", backend="auto"),
                path=path,
            )

            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertTrue(payload["running"])
            self.assertEqual(payload["model_state"], "loading")
            self.assertEqual(payload["device"], "cpu")
            self.assertEqual(payload["backend"], "auto")


class CliTests(unittest.TestCase):
    def test_ai_install_command_is_available(self):
        args = build_parser().parse_args(["ai", "install"])

        self.assertEqual(args.command, "ai")
        self.assertEqual(args.ai_command, "install")


if __name__ == "__main__":
    unittest.main()
