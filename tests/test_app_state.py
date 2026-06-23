import unittest

from speech_app.app import SpeechApp


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

    def show_notice(self, message: str) -> None:
        self.notices.append(message)


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


if __name__ == "__main__":
    unittest.main()
