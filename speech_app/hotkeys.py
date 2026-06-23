from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class HotkeyState:
    required_keys: set[str]
    on_start: Callable[[], None]
    on_stop: Callable[[], None]
    pressed_keys: set[str] = field(default_factory=set)
    active: bool = False

    def press(self, key: str) -> None:
        self.pressed_keys.add(key)
        if not self.active and self.required_keys.issubset(self.pressed_keys):
            self.active = True
            self.on_start()

    def release(self, key: str) -> None:
        self.pressed_keys.discard(key)
        if self.active and not self.required_keys.issubset(self.pressed_keys):
            self.active = False
            self.on_stop()


def parse_hotkey(value: str) -> set[str]:
    aliases = {
        "control": "ctrl",
        "cmd": "win",
        "windows": "win",
        "super": "win",
    }
    keys = set()
    for part in value.lower().replace(" ", "").split("+"):
        if not part:
            continue
        keys.add(aliases.get(part, part))
    return keys


class GlobalHotkeyListener:
    def __init__(
        self,
        hotkey: str,
        on_start: Callable[[], None],
        on_stop: Callable[[], None],
        suppress: bool = False,
    ) -> None:
        self.state = HotkeyState(
            required_keys=parse_hotkey(hotkey),
            on_start=on_start,
            on_stop=on_stop,
        )
        self.suppress = suppress
        self.listener = None

    def start(self) -> None:
        if self.listener is not None:
            return
        try:
            from pynput import keyboard
        except ImportError as exc:
            raise RuntimeError(
                "pynput is not installed, so global hotkeys are unavailable."
            ) from exc

        self.listener = keyboard.Listener(
            on_press=lambda key: self.state.press(_normalize_key(key)),
            on_release=lambda key: self.state.release(_normalize_key(key)),
            suppress=self.suppress,
        )
        self.listener.start()

    def stop(self) -> None:
        if self.listener is not None:
            self.listener.stop()
            self.listener = None


def _normalize_key(key) -> str:
    name = getattr(key, "name", None)
    char = getattr(key, "char", None)
    value = name or char or str(key)
    value = str(value).lower().replace("key.", "")
    if value in {"ctrl_l", "ctrl_r", "ctrl"}:
        return "ctrl"
    if value in {"cmd", "cmd_l", "cmd_r", "win", "win_l", "win_r"}:
        return "win"
    if value in {"shift_l", "shift_r"}:
        return "shift"
    if value in {"alt_l", "alt_r", "alt_gr"}:
        return "alt"
    return value
