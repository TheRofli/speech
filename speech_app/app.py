from __future__ import annotations

import argparse
import importlib.util
import os
import queue
import sys
import threading
import traceback
import tkinter as tk
from collections.abc import Callable
from pathlib import Path

from .audio import AudioRecorder
from .history import TranscriptHistory
from .hotkeys import GlobalHotkeyListener
from .model_status import ModelStatus, find_model_status
from .output import TranscriptPublisher
from .overlay import VoiceOverlay
from .parakeet_engine import EngineUnavailable, ParakeetEngine
from .portable import build_portable_env
from .resources import ProcessResourceMonitor, ResourceSnapshot
from .settings import AppSettings, SettingsStore
from .settings import default_data_dir
from .single_instance import SingleInstanceLock
from .system import SystemActions
from .tray import TrayController
from .visuals import create_icon_photo, enable_dpi_awareness, set_windows_app_id
from .window import SpeechWindow


class SpeechApp:
    def __init__(self) -> None:
        set_windows_app_id()
        enable_dpi_awareness()
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("Speech")
        self.icon_photo = create_icon_photo()
        if self.icon_photo is not None:
            self.root.iconphoto(True, self.icon_photo)
        self.ui_queue: queue.Queue[Callable[[], None]] = queue.Queue()

        self.settings_store = SettingsStore()
        self.settings = self.settings_store.load()
        self.history = TranscriptHistory(max_entries=self.settings.history_limit)
        self.system = SystemActions()
        self.publisher = TranscriptPublisher(
            history=self.history,
            set_clipboard=self.system.copy_to_clipboard,
            paste_active_input=self.system.paste_into_active_input,
        )
        self.engine = ParakeetEngine()
        self.resource_monitor = ProcessResourceMonitor()
        self.overlay = VoiceOverlay(self.root)
        self.window = SpeechWindow(self.root, self)
        self.tray = TrayController(self)
        self.recorder = AudioRecorder(
            sample_rate=self.settings.sample_rate,
            level_callback=lambda level: self.post_ui(
                lambda: self.overlay.set_level(level)
            ),
        )
        self.hotkey_listener: GlobalHotkeyListener | None = None
        self.transcribing = False
        self.last_error = ""

    def run(self, show_window: bool = False) -> None:
        self.root.after(30, self._pump_ui_queue)
        tray_started = self.tray.start()
        self._start_hotkeys()
        if not tray_started:
            self.last_error = "pystray is not installed; tray mode is unavailable."
            self.window.show()
        elif show_window:
            self._show_primary_window()
        if self.settings.preload_model and self.settings.engine_enabled:
            self.load_model_background()
        self.root.mainloop()

    def post_ui(self, callback: Callable[[], None]) -> None:
        self.ui_queue.put(callback)

    def show_window(self) -> None:
        self.post_ui(self._show_primary_window)

    def show_history(self) -> None:
        self.post_ui(self._show_primary_window)

    def copy_last_transcript(self) -> None:
        entries = self.history.list()
        if not entries:
            self.post_ui(lambda: self.overlay.show_notice("No transcript yet"))
            return
        self.system.copy_to_clipboard(entries[0].text)
        self.post_ui(lambda: self.overlay.show_notice("Copied"))

    def _show_primary_window(self) -> None:
        speech_home = Path(__file__).resolve().parents[1]
        if self.system.open_tauri_ui(speech_home):
            self.overlay.show_notice("Opening Speech")
            return
        self.window.show()

    def toggle_engine(self) -> None:
        self.settings.engine_enabled = not self.settings.engine_enabled
        self.settings_store.save(self.settings)
        if not self.settings.engine_enabled:
            self.unload_model()
            self.post_ui(lambda: self.overlay.show_notice("Engine off"))
        else:
            self.post_ui(lambda: self.overlay.show_notice("Engine on"))

    def load_model_background(self) -> None:
        if self.engine.is_loaded:
            self.post_ui(lambda: self._model_state_changed("Parakeet loaded"))
            return
        self.post_ui(lambda: self.overlay.show_transcribing())
        threading.Thread(target=self._load_model_worker, daemon=True).start()

    def unload_model(self) -> None:
        self.engine.unload()
        self.post_ui(lambda: self._model_state_changed("Parakeet unloaded"))

    def set_device(self, device: str) -> None:
        self.settings.device = device
        self.settings_store.save(self.settings)
        self.unload_model()

    def set_backend(self, backend: str) -> None:
        self.settings.backend = backend
        self.settings_store.save(self.settings)
        self.unload_model()

    def engine_enabled(self) -> bool:
        return self.settings.engine_enabled

    def current_device(self) -> str:
        return self.settings.device

    def current_backend(self) -> str:
        return self.settings.backend

    def model_loaded(self) -> bool:
        return self.engine.is_loaded

    def status_text(self) -> str:
        engine = "on" if self.settings.engine_enabled else "off"
        loaded = "loaded" if self.engine.is_loaded else "unloaded"
        return f"Engine {engine} | Parakeet {loaded} | {self.settings.device}"

    def get_settings_values(self) -> dict[str, object]:
        return {
            "engine_enabled": self.settings.engine_enabled,
            "copy_to_clipboard": self.settings.copy_to_clipboard,
            "paste_to_active_input": self.settings.paste_to_active_input,
            "preload_model": self.settings.preload_model,
            "device": self.settings.device,
            "backend": self.settings.backend,
            "hotkey": self.settings.hotkey,
        }

    def save_settings_values(self, values: dict[str, object]) -> None:
        previous_hotkey = self.settings.hotkey
        self.settings.engine_enabled = bool(values["engine_enabled"])
        self.settings.copy_to_clipboard = bool(values["copy_to_clipboard"])
        self.settings.paste_to_active_input = bool(values["paste_to_active_input"])
        self.settings.preload_model = bool(values["preload_model"])
        self.settings.device = str(values["device"])
        self.settings.backend = str(values["backend"])
        self.settings.hotkey = str(values["hotkey"])
        self.settings_store.save(self.settings)
        if self.settings.hotkey != previous_hotkey:
            self._restart_hotkeys()

    def history_rows(self) -> list[tuple[str, str]]:
        return [(entry.id, entry.text) for entry in self.history.list()]

    def copy_history_entry(self, entry_id: str) -> None:
        for entry in self.history.list():
            if entry.id == entry_id:
                self.system.copy_to_clipboard(entry.text)
                self.overlay.show_notice("Copied")
                return

    def quit(self) -> None:
        self.post_ui(self._quit_ui)

    def _quit_ui(self) -> None:
        if self.hotkey_listener is not None:
            self.hotkey_listener.stop()
        self.tray.stop()
        self.root.quit()
        self.root.destroy()

    def _start_hotkeys(self) -> None:
        try:
            self.hotkey_listener = GlobalHotkeyListener(
                hotkey=self.settings.hotkey,
                on_start=lambda: self.post_ui(self._begin_recording),
                on_stop=lambda: self.post_ui(self._finish_recording),
                suppress=self.settings.suppress_hotkey,
            )
            self.hotkey_listener.start()
        except Exception as exc:
            self.last_error = str(exc)
            self.window.show()
            self.overlay.show_notice("Hotkey unavailable", timeout_ms=2200)

    def _restart_hotkeys(self) -> None:
        if self.hotkey_listener is not None:
            self.hotkey_listener.stop()
            self.hotkey_listener = None
        self._start_hotkeys()

    def _begin_recording(self) -> None:
        if not self.settings.engine_enabled:
            self.overlay.show_notice("Engine off")
            return
        if self.recorder.is_recording or self.transcribing:
            return
        try:
            self.recorder.start()
            if self.hotkey_listener is not None:
                self.hotkey_listener.ignore_releases_for(0.2)
            self.system.release_hotkey_modifiers()
            self.overlay.show_recording()
        except Exception as exc:
            self.last_error = str(exc)
            self.overlay.show_notice("Microphone error", timeout_ms=2200)
            self.tray.notify("Speech", str(exc))

    def _finish_recording(self) -> None:
        if not self.recorder.is_recording:
            return
        samples = self.recorder.stop()
        self.overlay.show_transcribing()
        self.transcribing = True
        threading.Thread(
            target=self._transcribe_worker,
            args=(samples, self.settings.sample_rate, self.settings),
            daemon=True,
        ).start()

    def _load_model_worker(self) -> None:
        try:
            self.engine.load(self.settings)
        except Exception as exc:
            self.last_error = str(exc)
            self.post_ui(lambda: self._show_error("Parakeet load failed", exc))
            return
        self.post_ui(lambda: self._model_state_changed("Parakeet loaded"))

    def _model_state_changed(self, notice: str) -> None:
        self.window.refresh()
        self.tray.refresh_menu()
        self.overlay.show_notice(notice)

    def _transcribe_worker(
        self, samples, sample_rate: int, settings_snapshot: AppSettings
    ) -> None:
        try:
            text = self.engine.transcribe(samples, sample_rate, settings_snapshot)
        except EngineUnavailable as exc:
            self.last_error = str(exc)
            self.post_ui(lambda: self._show_error("Parakeet unavailable", exc))
            return
        except Exception as exc:
            self.last_error = traceback.format_exc()
            self.post_ui(lambda: self._show_error("Transcription failed", exc))
            return
        finally:
            self.post_ui(lambda: setattr(self, "transcribing", False))

        self.post_ui(lambda: self._publish_transcript(text, settings_snapshot))

    def _publish_transcript(
        self, text: str, settings_snapshot: AppSettings
    ) -> None:
        self.overlay.hide()
        self.root.after(140, lambda: self._publish_transcript_after_focus(text, settings_snapshot))

    def _publish_transcript_after_focus(
        self, text: str, settings_snapshot: AppSettings
    ) -> None:
        entry = self.publisher.publish(text, settings_snapshot)
        if entry is None:
            self.overlay.show_notice("No speech detected")
        else:
            self.overlay.show_notice("Inserted")

    def _show_error(self, title: str, exc: Exception) -> None:
        message = str(exc)
        self.overlay.show_notice(title, timeout_ms=2400)
        self.tray.notify(title, message)
        self.window.show()

    def _pump_ui_queue(self) -> None:
        while True:
            try:
                callback = self.ui_queue.get_nowait()
            except queue.Empty:
                break
            callback()
        self.root.after(30, self._pump_ui_queue)

    def resource_snapshot(self) -> ResourceSnapshot:
        return self.resource_monitor.snapshot()

    def model_status(self) -> ModelStatus:
        fallback = Path(__file__).resolve().parents[1] / "models" / "huggingface"
        hf_home = Path(os.environ.get("HF_HOME", str(fallback)))
        return find_model_status(hf_home, self.settings.model_id)


def diagnose() -> int:
    modules = [
        "tkinter",
        "numpy",
        "sounddevice",
        "pystray",
        "PIL",
        "pynput",
        "pyperclip",
        "torch",
        "transformers",
        "librosa",
        "nemo",
    ]
    print(f"Python: {sys.version}")
    for module in modules:
        print(f"{module}: {'ok' if importlib.util.find_spec(module) else 'missing'}")
    try:
        import torch

        print(f"torch cuda available: {torch.cuda.is_available()}")
    except ImportError:
        pass
    return 0


def install_parakeet_model(model_id: str | None = None) -> int:
    model_id = model_id or AppSettings().model_id
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("huggingface_hub is not installed. Run: speech install")
        return 1

    print(f"Downloading {model_id} into the configured Hugging Face cache...")
    path = snapshot_download(repo_id=model_id)
    print(f"Parakeet is ready at: {path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="speech")
    parser.add_argument(
        "--diagnose",
        action="store_true",
        help="Compatibility alias for: speech diagnose",
    )
    subparsers = parser.add_subparsers(dest="command")
    run_parser = subparsers.add_parser("run", help="Start the Speech tray app.")
    run_parser.add_argument(
        "--show-window",
        action="store_true",
        help="Open the Speech window immediately after starting the tray app.",
    )
    subparsers.add_parser("diagnose", help="Check Python and dependency state.")

    parakeet = subparsers.add_parser("parakeet", help="Manage the Parakeet model.")
    parakeet_sub = parakeet.add_subparsers(dest="parakeet_command")
    parakeet_sub.add_parser(
        "install",
        help="Download Parakeet into the configured local model cache.",
    )
    return parser


def apply_portable_env_if_present() -> None:
    speech_home = Path(__file__).resolve().parents[1]
    env = build_portable_env(speech_home)
    for key, value in env.items():
        if key not in sys.modules.get("os").environ:
            sys.modules.get("os").environ[key] = value


def main(argv: list[str] | None = None) -> int:
    import os

    speech_home = Path(__file__).resolve().parents[1]
    for key, value in build_portable_env(speech_home).items():
        os.environ.setdefault(key, value)

    parser = build_parser()
    args = parser.parse_args(argv)
    if args.diagnose or args.command == "diagnose":
        return diagnose()
    if args.command == "parakeet" and args.parakeet_command == "install":
        return install_parakeet_model()
    if args.command == "parakeet":
        parser.error("Choose a Parakeet command, for example: speech parakeet install")

    lock = SingleInstanceLock(default_data_dir() / "speech.lock")
    if not lock.acquire():
        print("Speech is already running.")
        return 0
    try:
        app = SpeechApp()
        app.run(show_window=bool(getattr(args, "show_window", False)))
        return 0
    finally:
        lock.release()
