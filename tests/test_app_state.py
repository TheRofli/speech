import unittest

from speech_app.app import SpeechApp
from speech_app.settings import AppSettings


class FakeWindow:
    def __init__(self) -> None:
        self.refresh_count = 0

    def refresh(self) -> None:
        self.refresh_count += 1


class FakeTray:
    def __init__(self) -> None:
        self.refresh_count = 0

    def refresh_menu(self) -> None:
        self.refresh_count += 1


class FakeOverlay:
    def __init__(self) -> None:
        self.notices = []
        self.recording_count = 0

    def show_notice(self, message: str) -> None:
        self.notices.append(message)

    def show_recording(self) -> None:
        self.recording_count += 1


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

    def ignore_releases_for(self, seconds: float) -> None:
        self.ignore_windows.append(seconds)


class AppStateTests(unittest.TestCase):
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
        self.assertEqual(app.hotkey_listener.ignore_windows, [0.2])
        self.assertEqual(app.recorder.start_count, 1)
        self.assertEqual(app.overlay.recording_count, 1)


if __name__ == "__main__":
    unittest.main()
