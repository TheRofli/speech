import unittest
from unittest.mock import Mock, patch

from speech_app.app import SpeechApp
from speech_app.postprocess import CorrectionResult
from speech_app.settings import AppSettings


class FakeWindow:
    def __init__(self) -> None:
        self.refresh_count = 0
        self.show_count = 0

    def refresh(self) -> None:
        self.refresh_count += 1

    def show(self) -> None:
        self.show_count += 1


class FakeTray:
    def __init__(self) -> None:
        self.refresh_count = 0
        self.stop_count = 0

    def refresh_menu(self) -> None:
        self.refresh_count += 1

    def start(self) -> bool:
        return True

    def stop(self) -> None:
        self.stop_count += 1


class FakeOverlay:
    def __init__(self) -> None:
        self.notices = []
        self.recording_count = 0
        self.cleaning_count = 0

    def show_notice(self, message: str) -> None:
        self.notices.append(message)

    def show_recording(self) -> None:
        self.recording_count += 1

    def show_cleaning(self) -> None:
        self.cleaning_count += 1


class FakeSystem:
    def __init__(self) -> None:
        self.remember_count = 0
        self.release_count = 0

    def remember_active_window(self) -> None:
        self.remember_count += 1

    def release_hotkey_modifiers(self) -> None:
        self.release_count += 1


class FakeRecorder:
    def __init__(self) -> None:
        self.is_recording = False
        self.start_count = 0

    def start(self) -> None:
        self.start_count += 1
        self.is_recording = True


class FakeHotkeyListener:
    def __init__(self) -> None:
        self.ignore_windows = []
        self.stop_count = 0

    def ignore_releases_for(self, seconds: float) -> None:
        self.ignore_windows.append(seconds)

    def stop(self) -> None:
        self.stop_count += 1


class FakeRoot:
    def __init__(self) -> None:
        self.quit_count = 0
        self.destroy_count = 0
        self.after_calls = []
        self.mainloop_count = 0

    def after(self, delay, callback) -> None:
        self.after_calls.append((delay, callback))

    def mainloop(self) -> None:
        self.mainloop_count += 1

    def quit(self) -> None:
        self.quit_count += 1

    def destroy(self) -> None:
        self.destroy_count += 1


class FakeEngine:
    def __init__(self, is_loaded: bool = False) -> None:
        self.is_loaded = is_loaded
        self.unload_count = 0

    def unload(self) -> None:
        self.unload_count += 1

    def transcribe(self, samples, sample_rate, settings) -> str:
        return "raw transcript"


class FakePostProcessor:
    def __init__(self) -> None:
        self.local_corrector = self
        self.is_loaded = False
        self.unload_count = 0
        self.process_calls = []
        self.load_calls = []

    def unload(self) -> None:
        self.unload_count += 1

    def process(self, text, settings) -> CorrectionResult:
        self.process_calls.append((text, settings))
        return CorrectionResult(text, "corrected transcript", "local", "applied", 42)

    def load(self, settings) -> None:
        self.load_calls.append(settings.ai_mode)


class FakeSettingsStore:
    def __init__(self) -> None:
        self.saved = []

    def save(self, settings) -> None:
        self.saved.append((settings.ai_mode, settings.ai_profile))


class FakeThread:
    def __init__(self, target, daemon: bool = False, args=()) -> None:
        self.target = target
        self.daemon = daemon
        self.args = args
        self.started = False

    def start(self) -> None:
        self.started = True


class AppStateTests(unittest.TestCase):
    def test_run_starts_only_the_sequential_model_preload_pipeline(self):
        app = SpeechApp.__new__(SpeechApp)
        app.root = FakeRoot()
        app.tray = FakeTray()
        app.settings = AppSettings(ai_mode="local", preload_model=True)
        app.window = FakeWindow()
        app._start_hotkeys = Mock()
        app.load_model_background = Mock()
        app.load_corrector_background = Mock()

        app.run()

        app.load_model_background.assert_called_once_with()
        app.load_corrector_background.assert_not_called()
        self.assertEqual(app.root.mainloop_count, 1)

    def test_model_state_change_refreshes_window_tray_and_notice(self):
        app = SpeechApp.__new__(SpeechApp)
        app.window = FakeWindow()
        app.tray = FakeTray()
        app.overlay = FakeOverlay()

        app._model_state_changed("Parakeet loaded")

        self.assertEqual(app.window.refresh_count, 1)
        self.assertEqual(app.tray.refresh_count, 1)
        self.assertEqual(app.overlay.notices, ["Parakeet loaded"])

    def test_begin_recording_releases_hotkey_modifiers_without_remembering_window(self):
        app = SpeechApp.__new__(SpeechApp)
        app.settings = AppSettings()
        app.recorder = FakeRecorder()
        app.overlay = FakeOverlay()
        app.tray = None
        app.transcribing = False
        app.system = FakeSystem()
        app.hotkey_listener = FakeHotkeyListener()

        app._begin_recording()

        self.assertEqual(app.system.remember_count, 0)
        self.assertEqual(app.system.release_count, 1)
        self.assertEqual(app.hotkey_listener.ignore_windows, [])
        self.assertEqual(app.recorder.start_count, 1)
        self.assertEqual(app.overlay.recording_count, 1)

    def test_quit_unloads_model_before_destroying_root(self):
        app = SpeechApp.__new__(SpeechApp)
        app.hotkey_listener = FakeHotkeyListener()
        app.tray = FakeTray()
        app.root = FakeRoot()
        app.engine = FakeEngine()
        app.postprocessor = FakePostProcessor()
        app.model_loading = False

        app._quit_ui()

        self.assertEqual(app.engine.unload_count, 1)
        self.assertEqual(app.postprocessor.unload_count, 1)
        self.assertEqual(app.hotkey_listener.stop_count, 1)
        self.assertEqual(app.tray.stop_count, 1)
        self.assertEqual(app.root.quit_count, 1)
        self.assertEqual(app.root.destroy_count, 1)

    def test_status_text_reports_loading_while_model_loads(self):
        app = SpeechApp.__new__(SpeechApp)
        app.settings = AppSettings()
        app.engine = FakeEngine(is_loaded=False)
        app.model_loading = True

        self.assertIn("Parakeet loading", app.status_text())

    def test_load_model_background_marks_loading_before_worker_starts(self):
        app = SpeechApp.__new__(SpeechApp)
        app.settings = AppSettings()
        app.engine = FakeEngine(is_loaded=False)
        app.model_loading = False
        app.posted_callbacks = []
        app.post_ui = app.posted_callbacks.append
        app._write_runtime_state = lambda *_args, **_kwargs: None

        with patch("speech_app.app.threading.Thread", FakeThread):
            app.load_model_background()

        self.assertTrue(app.model_loading)
        self.assertIn("Parakeet loading", app.status_text())
        self.assertEqual(len(app.posted_callbacks), 1)

    def test_load_model_background_does_not_start_duplicate_worker_while_loading(self):
        app = SpeechApp.__new__(SpeechApp)
        app.settings = AppSettings()
        app.engine = FakeEngine(is_loaded=False)
        app.model_loading = True
        app.posted_callbacks = []
        app.post_ui = app.posted_callbacks.append

        with patch("speech_app.app.threading.Thread") as thread_cls:
            app.load_model_background()

        thread_cls.assert_not_called()

    def test_transcribe_worker_corrects_before_publishing(self):
        app = SpeechApp.__new__(SpeechApp)
        app.engine = FakeEngine()
        app.postprocessor = FakePostProcessor()
        app.model_loading = False
        app.overlay = FakeOverlay()
        app.transcribing = True
        app.posted_callbacks = []
        app.post_ui = app.posted_callbacks.append
        published = []
        app._publish_correction = lambda result, _settings: published.append(result)
        settings = AppSettings(ai_mode="local")

        app._transcribe_worker([], 16000, settings)
        for callback in app.posted_callbacks:
            callback()

        self.assertEqual(app.postprocessor.process_calls[0][0], "raw transcript")
        self.assertEqual(published[0].text, "corrected transcript")
        self.assertEqual(app.overlay.cleaning_count, 1)
        self.assertFalse(app.transcribing)

    def test_set_ai_mode_off_persists_and_unloads_corrector(self):
        app = SpeechApp.__new__(SpeechApp)
        app.settings = AppSettings(ai_mode="local")
        app.settings_store = FakeSettingsStore()
        app.postprocessor = FakePostProcessor()
        app.engine = FakeEngine()
        app.model_loading = False
        app.overlay = FakeOverlay()
        app.window = FakeWindow()
        app.tray = FakeTray()
        app._write_runtime_state = lambda *_args, **_kwargs: None

        app.set_ai_mode("off")

        self.assertEqual(app.current_ai_mode(), "off")
        self.assertEqual(app.settings_store.saved[-1], ("off", "clean"))
        self.assertEqual(app.postprocessor.unload_count, 1)
        self.assertEqual(app.window.refresh_count, 1)
        self.assertEqual(app.tray.refresh_count, 1)

    def test_set_ai_mode_local_starts_background_load(self):
        app = SpeechApp.__new__(SpeechApp)
        app.settings = AppSettings(ai_mode="off")
        app.settings_store = FakeSettingsStore()
        app.postprocessor = FakePostProcessor()
        app.engine = FakeEngine()
        app.model_loading = False
        app.overlay = FakeOverlay()
        app.window = FakeWindow()
        app.tray = FakeTray()
        app.ai_loading = False
        app.posted_callbacks = []
        app.post_ui = app.posted_callbacks.append
        app._write_runtime_state = lambda *_args, **_kwargs: None

        with patch("speech_app.app.threading.Thread", FakeThread):
            app.set_ai_mode("local")

        self.assertEqual(app.current_ai_mode(), "local")
        self.assertTrue(app.ai_loading)
        self.assertEqual(app.settings_store.saved[-1], ("local", "clean"))

    def test_refine_profile_requires_api_mode(self):
        app = SpeechApp.__new__(SpeechApp)
        app.settings = AppSettings(ai_mode="local")
        app.settings_store = FakeSettingsStore()

        with self.assertRaisesRegex(ValueError, "API"):
            app.set_ai_profile("refine")

        self.assertEqual(app.settings.ai_profile, "clean")

    def test_api_mode_accepts_refine_profile(self):
        app = SpeechApp.__new__(SpeechApp)
        app.settings = AppSettings(ai_mode="api")
        app.settings_store = FakeSettingsStore()
        app.window = FakeWindow()
        app.tray = FakeTray()

        app.set_ai_profile("refine")

        self.assertEqual(app.current_ai_profile(), "refine")
        self.assertEqual(app.settings_store.saved[-1], ("api", "refine"))


if __name__ == "__main__":
    unittest.main()
