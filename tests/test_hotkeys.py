import unittest

from speech_app.hotkeys import HotkeyState


class HotkeyStateTests(unittest.TestCase):
    def test_ctrl_win_starts_once_and_stops_on_release(self):
        events = []
        state = HotkeyState(
            required_keys={"ctrl", "win"},
            on_start=lambda: events.append("start"),
            on_stop=lambda: events.append("stop"),
        )

        state.press("ctrl")
        state.press("win")
        state.press("win")
        state.release("ctrl")

        self.assertEqual(events, ["start", "stop"])

    def test_release_without_active_recording_does_not_stop(self):
        events = []
        state = HotkeyState(
            required_keys={"ctrl", "win"},
            on_start=lambda: events.append("start"),
            on_stop=lambda: events.append("stop"),
        )

        state.press("ctrl")
        state.release("ctrl")

        self.assertEqual(events, [])


if __name__ == "__main__":
    unittest.main()
