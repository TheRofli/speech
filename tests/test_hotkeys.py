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

    def test_can_ignore_synthetic_required_key_release_briefly(self):
        events = []
        current_time = [10.0]
        state = HotkeyState(
            required_keys={"ctrl", "win"},
            on_start=lambda: events.append("start"),
            on_stop=lambda: events.append("stop"),
            now=lambda: current_time[0],
        )

        state.press("ctrl")
        state.press("win")
        state.ignore_releases_for(0.2)
        state.release("ctrl")
        current_time[0] += 0.3
        state.release("ctrl")

        self.assertEqual(events, ["start", "stop"])


if __name__ == "__main__":
    unittest.main()
