from __future__ import annotations

from typing import Protocol


class TrayApp(Protocol):
    def show_window(self) -> None: ...
    def show_history(self) -> None: ...
    def copy_last_transcript(self) -> None: ...
    def toggle_engine(self) -> None: ...
    def load_model_background(self) -> None: ...
    def unload_model(self) -> None: ...
    def set_device(self, device: str) -> None: ...
    def set_backend(self, backend: str) -> None: ...
    def set_ai_mode(self, mode: str) -> None: ...
    def set_ai_profile(self, profile: str) -> None: ...
    def quit(self) -> None: ...
    def engine_enabled(self) -> bool: ...
    def current_device(self) -> str: ...
    def current_backend(self) -> str: ...
    def current_ai_mode(self) -> str: ...
    def current_ai_profile(self) -> str: ...
    def model_loaded(self) -> bool: ...
    def model_is_loading(self) -> bool: ...


class TrayController:
    def __init__(self, app: TrayApp) -> None:
        self.app = app
        self.icon = None

    def start(self) -> bool:
        try:
            import pystray
        except ImportError:
            return False

        def item(label, action, **kwargs):
            return pystray.MenuItem(label, lambda icon, menu_item: action(), **kwargs)

        image = create_tray_image()

        menu = pystray.Menu(
            item("Open Speech", self.app.show_window, default=True),
            item("Open History", self.app.show_history),
            item("Copy Last Transcript", self.app.copy_last_transcript),
            pystray.Menu.SEPARATOR,
            item(
                "Engine On",
                self.app.toggle_engine,
                checked=lambda _: self.app.engine_enabled(),
            ),
            item(
                "Load Parakeet",
                self.app.load_model_background,
                enabled=lambda _: not self.app.model_loaded()
                and not self.app.model_is_loading(),
            ),
            item(
                "Loading Parakeet...",
                lambda: None,
                enabled=False,
                visible=lambda _: self.app.model_is_loading(),
            ),
            item(
                "Unload Parakeet",
                self.app.unload_model,
                enabled=lambda _: self.app.model_loaded()
                and not self.app.model_is_loading(),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Device",
                pystray.Menu(
                    item(
                        "CPU",
                        lambda: self.app.set_device("cpu"),
                        checked=lambda _: self.app.current_device() == "cpu",
                        radio=True,
                    ),
                    item(
                        "GPU / CUDA",
                        lambda: self.app.set_device("cuda"),
                        checked=lambda _: self.app.current_device() == "cuda",
                        radio=True,
                    ),
                    item(
                        "Auto",
                        lambda: self.app.set_device("auto"),
                        checked=lambda _: self.app.current_device() == "auto",
                        radio=True,
                    ),
                ),
            ),
            pystray.MenuItem(
                "Backend",
                pystray.Menu(
                    item(
                        "Auto",
                        lambda: self.app.set_backend("auto"),
                        checked=lambda _: self.app.current_backend() == "auto",
                        radio=True,
                    ),
                    item(
                        "Transformers",
                        lambda: self.app.set_backend("transformers"),
                        checked=lambda _: self.app.current_backend()
                        == "transformers",
                        radio=True,
                    ),
                    item(
                        "NeMo",
                        lambda: self.app.set_backend("nemo"),
                        checked=lambda _: self.app.current_backend() == "nemo",
                        radio=True,
                    ),
                ),
            ),
            pystray.MenuItem(
                "Transcript polish",
                pystray.Menu(
                    item(
                        "Off",
                        lambda: self.app.set_ai_mode("off"),
                        checked=lambda _: self.app.current_ai_mode() == "off",
                        radio=True,
                    ),
                    item(
                        "Local",
                        lambda: self.app.set_ai_mode("local"),
                        checked=lambda _: self.app.current_ai_mode() == "local",
                        radio=True,
                    ),
                    item(
                        "API",
                        lambda: self.app.set_ai_mode("api"),
                        checked=lambda _: self.app.current_ai_mode() == "api",
                        radio=True,
                    ),
                ),
            ),
            pystray.MenuItem(
                "Polish style",
                pystray.Menu(
                    item(
                        "Clean",
                        lambda: self.app.set_ai_profile("clean"),
                        checked=lambda _: self.app.current_ai_profile() == "clean",
                        radio=True,
                    ),
                    item(
                        "Refine",
                        lambda: self.app.set_ai_profile("refine"),
                        checked=lambda _: self.app.current_ai_profile() == "refine",
                        enabled=lambda _: self.app.current_ai_mode() == "api",
                        radio=True,
                    ),
                ),
            ),
            pystray.Menu.SEPARATOR,
            item("Quit", self.app.quit),
        )
        self.icon = pystray.Icon("Speech", image, "Speech", menu)
        self.icon.run_detached()
        return True

    def stop(self) -> None:
        if self.icon is not None:
            self.icon.stop()
            self.icon = None

    def refresh_menu(self) -> None:
        if self.icon is not None:
            try:
                self.icon.update_menu()
            except Exception:
                pass

    def notify(self, title: str, message: str) -> None:
        if self.icon is not None:
            try:
                self.icon.notify(message, title)
            except Exception:
                pass


def create_tray_image():
    from PIL import Image, ImageDraw

    scale = 4
    size = 64
    image = Image.new("RGBA", (size * scale, size * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    def px(value: int) -> int:
        return value * scale

    draw.rounded_rectangle(
        (px(7), px(11), px(57), px(53)),
        radius=px(17),
        fill="#f7f1ff",
        outline="#ded2ef",
        width=px(2),
    )
    draw.rounded_rectangle(
        (px(18), px(19), px(46), px(45)),
        radius=px(12),
        fill="#111111",
    )
    bars = [7, 13, 19, 25, 19, 13, 7]
    x = 23
    for height in bars:
        y0 = 32 - height // 2
        y1 = 32 + height // 2
        draw.rounded_rectangle(
            (px(x), px(y0), px(x + 2), px(y1)),
            radius=px(1),
            fill="#ffffff",
        )
        x += 4

    return image.resize((size, size), Image.Resampling.LANCZOS)
