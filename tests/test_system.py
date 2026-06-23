import unittest

from speech_app.system import SystemActions


class FakeUser32:
    def __init__(self) -> None:
        self.foreground = 1234
        self.restored = []
        self.key_events = []

    def GetForegroundWindow(self):
        return self.foreground

    def IsWindow(self, hwnd):
        return hwnd == self.foreground

    def SetForegroundWindow(self, hwnd):
        self.restored.append(hwnd)
        return 1

    def keybd_event(self, vk, scan, flags, extra):
        self.key_events.append((vk, scan, flags, extra))


class SystemActionsTests(unittest.TestCase):
    def test_remembers_and_restores_foreground_window(self):
        user32 = FakeUser32()
        actions = SystemActions(user32=user32)

        actions.remember_active_window()
        actions.restore_active_window()

        self.assertEqual(user32.restored, [1234])

    def test_paste_restores_window_then_invokes_sender(self):
        user32 = FakeUser32()
        calls = []
        actions = SystemActions(
            user32=user32,
            paste_sender=lambda text: calls.append(text),
            sleep=lambda seconds: None,
        )

        actions.remember_active_window()
        actions.paste_into_active_input("typed text")

        self.assertEqual(user32.restored, [1234])
        self.assertEqual(calls, ["typed text"])

    def test_paste_copies_text_then_sends_ctrl_v_when_sender_is_not_injected(self):
        user32 = FakeUser32()
        clipboard = []
        actions = SystemActions(
            user32=user32,
            clipboard_writer=clipboard.append,
            sleep=lambda seconds: None,
        )

        actions.paste_into_active_input("hello")

        self.assertEqual(clipboard, ["hello"])
        self.assertEqual(
            user32.key_events,
            [
                (0x5B, 0, 0x0002, 0),
                (0x5C, 0, 0x0002, 0),
                (0xA2, 0, 0x0002, 0),
                (0xA3, 0, 0x0002, 0),
                (0x11, 0, 0x0002, 0),
                (0x11, 0, 0, 0),
                (0x56, 0, 0, 0),
                (0x56, 0, 0x0002, 0),
                (0x11, 0, 0x0002, 0),
            ],
        )


if __name__ == "__main__":
    unittest.main()
