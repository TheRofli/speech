from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import patch

from speech_app.tray import TrayController


class FakeMenu(tuple):
    SEPARATOR = object()

    def __new__(cls, *items):
        return super().__new__(cls, items)


class FakeMenuItem:
    def __init__(self, label, action, **kwargs) -> None:
        self.label = label
        self.action = action
        self.kwargs = kwargs


class FakeIcon:
    def __init__(self, _name, _image, _title, menu) -> None:
        self.menu = menu

    def run_detached(self) -> None:
        return None

    def stop(self) -> None:
        return None

    def update_menu(self) -> None:
        return None


class FakeTrayApp:
    def __init__(self) -> None:
        self.mode = "local"
        self.profile = "clean"
        self.mode_changes = []
        self.profile_changes = []

    def set_ai_mode(self, mode: str) -> None:
        self.mode_changes.append(mode)

    def set_ai_profile(self, profile: str) -> None:
        self.profile_changes.append(profile)

    def current_ai_mode(self) -> str:
        return self.mode

    def current_ai_profile(self) -> str:
        return self.profile

    def __getattr__(self, _name):
        return lambda *_args, **_kwargs: False


class TrayControllerTests(unittest.TestCase):
    def test_menu_exposes_polish_provider_and_profile_radios(self):
        fake_pystray = types.SimpleNamespace(
            Menu=FakeMenu,
            MenuItem=FakeMenuItem,
            Icon=FakeIcon,
        )
        app = FakeTrayApp()
        controller = TrayController(app)

        with patch.dict(sys.modules, {"pystray": fake_pystray}), patch(
            "speech_app.tray.create_tray_image", return_value=object()
        ):
            self.assertTrue(controller.start())

        top_level = {item.label: item for item in controller.icon.menu if isinstance(item, FakeMenuItem)}
        providers = top_level["Transcript polish"].action
        profiles = top_level["Polish style"].action
        self.assertEqual([item.label for item in providers], ["Off", "Local", "API"])
        self.assertEqual([item.label for item in profiles], ["Clean", "Refine"])

        providers[2].action(None, None)
        profiles[1].action(None, None)
        self.assertEqual(app.mode_changes, ["api"])
        self.assertEqual(app.profile_changes, ["refine"])
        self.assertTrue(providers[1].kwargs["checked"](None))
        self.assertFalse(profiles[1].kwargs["enabled"](None))


if __name__ == "__main__":
    unittest.main()
