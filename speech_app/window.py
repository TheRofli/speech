from __future__ import annotations

import importlib.util
import tkinter as tk
from typing import Protocol

from .model_status import ModelStatus
from .resources import ResourceSnapshot


BG = "#fff8fc"
SURFACE = "#fffdfd"
SURFACE_SOFT = "#fff1f7"
SURFACE_MUTED = "#f8edf4"
INK = "#2a2231"
MUTED = "#7b707f"
LINE = "#ead5df"
ACCENT = "#2a2231"
ACCENT_HOVER = "#3a3042"
PINK = "#f4cfe0"
SUCCESS = "#43825d"
WARN = "#a06a7d"


class WindowApp(Protocol):
    def status_text(self) -> str: ...
    def get_settings_values(self) -> dict[str, object]: ...
    def save_settings_values(self, values: dict[str, object]) -> None: ...
    def history_rows(self) -> list[tuple[str, str]]: ...
    def copy_history_entry(self, entry_id: str) -> None: ...
    def load_model_background(self) -> None: ...
    def unload_model(self) -> None: ...
    def toggle_engine(self) -> None: ...
    def model_status(self) -> ModelStatus: ...
    def resource_snapshot(self) -> ResourceSnapshot: ...


class SpeechWindow:
    def __init__(self, root: tk.Tk, app: WindowApp) -> None:
        self.root = root
        self.app = app
        self.window: tk.Toplevel | None = None
        self.content: tk.Frame | None = None
        self.content_canvas: tk.Canvas | None = None
        self.history_list: tk.Listbox | None = None
        self.history_preview: tk.Text | None = None
        self.latest_text: tk.Text | None = None
        self.nav_buttons: dict[str, tk.Button] = {}
        self.history_ids: list[str] = []
        self.selected_history_id = ""
        self.latest_history_id = ""
        self.vars: dict[str, tk.Variable] = {}
        self.status_var = tk.StringVar(value="")
        self.status_headline_var = tk.StringVar(value="")
        self.status_detail_var = tk.StringVar(value="")
        self.model_var = tk.StringVar(value="")
        self.model_path_var = tk.StringVar(value="")
        self.side_model_var = tk.StringVar(value="")
        self.history_count_var = tk.StringVar(value="0")
        self.device_var = tk.StringVar(value="CPU")
        self.ram_var = tk.StringVar(value="")
        self.cpu_var = tk.StringVar(value="")
        self.threads_var = tk.StringVar(value="")
        self.mode_var = tk.StringVar(value="")
        self.output_var = tk.StringVar(value="")
        self.active_tab = tk.StringVar(value="overview")
        self.history_search_var = tk.StringVar(value="")
        self._history_signature: tuple[tuple[str, str], str] = ((), "")

    def show(self) -> None:
        if self.window is None or not self.window.winfo_exists():
            self._build()
        assert self.window is not None
        self._refresh()
        self.window.deiconify()
        self.window.lift()
        self.window.focus_force()

    def show_history(self) -> None:
        self.show()
        self._select_tab("history")

    def refresh(self) -> None:
        self._refresh()

    def _build(self) -> None:
        self.window = tk.Toplevel(self.root)
        self.window.title("Speech")
        self.window.geometry("940x680")
        self.window.minsize(760, 520)
        self.window.configure(bg=BG)
        self._center_window(940, 680)
        icon = getattr(self.app, "icon_photo", None)
        if icon is not None:
            self.window.iconphoto(False, icon)
        self.window.protocol("WM_DELETE_WINDOW", self.window.withdraw)

        shell = tk.Frame(self.window, bg=BG)
        shell.pack(fill="both", expand=True, padx=18, pady=18)

        self._build_sidebar(shell)

        main = tk.Frame(shell, bg=BG)
        main.pack(side="left", fill="both", expand=True, padx=(18, 0))

        self._build_topbar(main)
        outer, content = self._scroll_area(main)
        outer.pack(fill="both", expand=True, pady=(16, 0))
        self.content = content

        self.history_search_var.trace_add("write", lambda *_args: self._refresh_history())
        self._render_tab()
        self._schedule_refresh()

    def _center_window(self, width: int, height: int) -> None:
        if self.window is None:
            return
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        width = min(width, max(760, screen_width - 80))
        height = min(height, max(520, screen_height - 100))
        x = max(20, (screen_width - width) // 2)
        y = max(20, (screen_height - height) // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")

    def _build_sidebar(self, parent: tk.Frame) -> None:
        sidebar = tk.Frame(
            parent,
            bg=SURFACE,
            highlightbackground=LINE,
            highlightthickness=1,
            width=230,
        )
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        brand = tk.Frame(sidebar, bg=SURFACE)
        brand.pack(fill="x", padx=18, pady=(18, 22))
        mark = tk.Canvas(brand, width=52, height=52, bg=SURFACE, highlightthickness=0)
        mark.pack(side="left")
        self._draw_mark(mark, 52, SURFACE)

        title = tk.Frame(brand, bg=SURFACE)
        title.pack(side="left", padx=(12, 0), fill="x", expand=True)
        tk.Label(
            title,
            text="Speech",
            bg=SURFACE,
            fg=INK,
            font=("Segoe UI", 20, "bold"),
        ).pack(anchor="w")
        tk.Label(
            title,
            text="local dictation",
            bg=SURFACE,
            fg=MUTED,
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w")

        nav = tk.Frame(sidebar, bg=SURFACE)
        nav.pack(fill="x", padx=18)
        for tab, label in [
            ("overview", "Overview"),
            ("controls", "Controls"),
            ("history", "History"),
            ("install", "Install"),
        ]:
            self.nav_buttons[tab] = self._nav_button(nav, tab, label)

        note = tk.Frame(sidebar, bg=SURFACE_SOFT, padx=14, pady=12)
        note.pack(side="bottom", fill="x", padx=18, pady=18)
        tk.Label(
            note,
            text="Parakeet",
            bg=SURFACE_SOFT,
            fg=MUTED,
            font=("Segoe UI", 8, "bold"),
        ).pack(anchor="w")
        tk.Label(
            note,
            textvariable=self.side_model_var,
            bg=SURFACE_SOFT,
            fg=INK,
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", pady=(3, 0))

    def _build_topbar(self, parent: tk.Frame) -> None:
        topbar = tk.Frame(
            parent,
            bg=SURFACE,
            highlightbackground=LINE,
            highlightthickness=1,
        )
        topbar.pack(fill="x")
        topbar.columnconfigure(0, weight=1)

        status = tk.Frame(topbar, bg=SURFACE)
        status.grid(row=0, column=0, sticky="w", padx=20, pady=16)
        tk.Label(
            status,
            text="Status",
            bg=SURFACE,
            fg=MUTED,
            font=("Segoe UI", 8, "bold"),
        ).pack(anchor="w")
        tk.Label(
            status,
            textvariable=self.status_headline_var,
            bg=SURFACE,
            fg=INK,
            font=("Segoe UI", 18, "bold"),
        ).pack(anchor="w")
        tk.Label(
            status,
            textvariable=self.status_detail_var,
            bg=SURFACE,
            fg=MUTED,
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", pady=(2, 0))

        actions = tk.Frame(topbar, bg=SURFACE)
        actions.grid(row=0, column=1, sticky="e", padx=20, pady=16)
        self._button(actions, "Refresh", self._refresh, variant="soft").pack(
            side="left", padx=(0, 8)
        )
        self._button(actions, "Load", self.app.load_model_background).pack(
            side="left", padx=(0, 8)
        )
        self._button(actions, "Unload", self.app.unload_model, variant="soft").pack(
            side="left"
        )

    def _render_tab(self) -> None:
        if self.content is None:
            return
        for child in self.content.winfo_children():
            child.destroy()
        self.history_list = None
        self.history_preview = None
        self.latest_text = None

        tab = self.active_tab.get()
        for key, button in self.nav_buttons.items():
            active = key == tab
            button.configure(
                bg=ACCENT if active else SURFACE,
                fg="#ffffff" if active else MUTED,
                activebackground=ACCENT_HOVER if active else SURFACE_SOFT,
                activeforeground="#ffffff" if active else INK,
            )

        if tab == "overview":
            self._build_overview(self.content)
        elif tab == "controls":
            self._build_controls(self.content)
        elif tab == "history":
            self._build_history(self.content)
        else:
            self._build_install(self.content)
        self._refresh()
        if self.content_canvas is not None:
            self.content_canvas.yview_moveto(0)

    def _build_overview(self, parent: tk.Frame) -> None:
        hero = self._panel(parent, padx=22, pady=22)
        hero.pack(fill="x", pady=(0, 14))
        hero.columnconfigure(0, weight=1)
        copy = tk.Frame(hero, bg=SURFACE)
        copy.grid(row=0, column=0, sticky="nsew")
        self._quiet_label(copy, "Push-to-talk").pack(anchor="w")
        tk.Label(
            copy,
            text="Hold, speak,\nrelease.",
            bg=SURFACE,
            fg=INK,
            justify="left",
            font=("Segoe UI", 31, "bold"),
        ).pack(anchor="w")
        tk.Label(
            copy,
            text="Speech keeps transcription local, then sends text to the active input, clipboard, and history.",
            bg=SURFACE,
            fg=MUTED,
            justify="left",
            wraplength=520,
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", pady=(10, 0))
        wave = tk.Canvas(hero, width=132, height=70, bg=SURFACE, highlightthickness=0)
        wave.grid(row=0, column=1, padx=(22, 0), sticky="e")
        self._draw_wave_pill(wave)

        metrics = tk.Frame(parent, bg=BG)
        metrics.pack(fill="x", pady=(0, 14))
        for index in range(2):
            metrics.columnconfigure(index, weight=1, uniform="metrics")
        self._metric_card(metrics, 0, "Runtime", self.status_headline_var, "tray app")
        self._metric_card(metrics, 1, "Model", self.model_var, "Parakeet")
        self._metric_card(metrics, 2, "History", self.history_count_var, "local rows")
        self._metric_card(metrics, 3, "Device", self.device_var, "stable default")

        latest = self._panel(parent, padx=18, pady=16)
        latest.pack(fill="both", expand=True)
        latest.columnconfigure(0, weight=1)
        head = tk.Frame(latest, bg=SURFACE)
        head.grid(row=0, column=0, sticky="ew")
        self._quiet_label(head, "Latest transcript").pack(side="left")
        self._button(
            head,
            "Copy",
            lambda: self._copy_history_id(self.latest_history_id),
            variant="soft",
        ).pack(side="right")
        self.latest_text = tk.Text(
            latest,
            height=6,
            bg=SURFACE,
            fg=INK,
            relief="flat",
            borderwidth=0,
            wrap="word",
            font=("Segoe UI", 12),
            padx=0,
            pady=10,
        )
        self.latest_text.grid(row=1, column=0, sticky="nsew")
        latest.rowconfigure(1, weight=1)

    def _build_controls(self, parent: tk.Frame) -> None:
        values = self.app.get_settings_values()
        self.vars = {
            "engine_enabled": tk.BooleanVar(value=bool(values["engine_enabled"])),
            "copy_to_clipboard": tk.BooleanVar(value=bool(values["copy_to_clipboard"])),
            "paste_to_active_input": tk.BooleanVar(
                value=bool(values["paste_to_active_input"])
            ),
            "preload_model": tk.BooleanVar(value=bool(values["preload_model"])),
            "device": tk.StringVar(value=str(values["device"])),
            "backend": tk.StringVar(value=str(values["backend"])),
            "hotkey": tk.StringVar(value=str(values["hotkey"])),
        }

        grid = tk.Frame(parent, bg=BG)
        grid.pack(fill="x")
        grid.columnconfigure(0, weight=1, uniform="controls")
        grid.columnconfigure(1, weight=1, uniform="controls")

        runtime = self._panel(grid)
        runtime.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 14))
        self._section_title(runtime, "Runtime")
        self._field(runtime, "Device", self.vars["device"], ("cpu", "cuda", "auto"))
        self._field(runtime, "Backend", self.vars["backend"], ("auto", "transformers", "nemo"))
        self._entry(runtime, "Hotkey", self.vars["hotkey"])
        tk.Label(
            runtime,
            textvariable=self.mode_var,
            bg=SURFACE,
            fg=MUTED,
            justify="left",
            wraplength=300,
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", pady=(10, 8))
        self._check(runtime, "Engine enabled", self.vars["engine_enabled"])
        self._check(runtime, "Preload on launch", self.vars["preload_model"])
        row = tk.Frame(runtime, bg=SURFACE)
        row.pack(fill="x", pady=(12, 0))
        self._button(row, "Save", self._save_settings).pack(side="left", padx=(0, 8))
        self._button(row, "Engine", self._toggle_engine, variant="soft").pack(side="left")

        output = self._panel(grid)
        output.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=(0, 14))
        self._section_title(output, "Output")
        tk.Label(
            output,
            textvariable=self.output_var,
            bg=SURFACE,
            fg=MUTED,
            justify="left",
            wraplength=300,
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(0, 8))
        self._check(
            output,
            "Paste into active input",
            self.vars["paste_to_active_input"],
            command=self._save_settings,
        )
        self._check(
            output,
            "Copy to clipboard",
            self.vars["copy_to_clipboard"],
            command=self._save_settings,
        )

        resources = self._panel(parent)
        resources.pack(fill="x", pady=(0, 14))
        self._section_title(resources, "Resources")
        row = tk.Frame(resources, bg=SURFACE)
        row.pack(fill="x")
        row.columnconfigure(0, weight=1, uniform="resources")
        row.columnconfigure(1, weight=1, uniform="resources")
        row.columnconfigure(2, weight=1, uniform="resources")
        self._mini_metric(row, 0, "RAM", self.ram_var)
        self._mini_metric(row, 1, "CPU", self.cpu_var)
        self._mini_metric(row, 2, "Threads", self.threads_var)

        self._build_modes(parent)

    def _build_modes(self, parent: tk.Frame) -> None:
        panel = self._panel(parent)
        panel.pack(fill="x", pady=(0, 14))
        self._section_title(panel, "Parakeet modes")
        tk.Label(
            panel,
            text="Parakeet v3 ships as a 0.6B model. Quality/speed changes here are runtime choices: CPU or CUDA, Transformers or NeMo, preload or unload.",
            bg=SURFACE,
            fg=MUTED,
            justify="left",
            wraplength=620,
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(0, 10))

        grid = tk.Frame(panel, bg=SURFACE)
        grid.pack(fill="x")
        for index in range(4):
            grid.columnconfigure(index, weight=1, uniform="modes")
        nemo_status = "Ready" if importlib.util.find_spec("nemo") else "Needs NeMo"
        features = [
            ("0.6B", "current model", ACCENT),
            ("CPU", "stable default", SUCCESS),
            ("CUDA", "optional", WARN),
            ("Auto language", "built in", SUCCESS),
            ("Punctuation", "built in", SUCCESS),
            ("Timestamps", "supported", "#6e4f8f"),
            ("Long-form", nemo_status, WARN),
            ("Medium/Large", "not in v3", MUTED),
        ]
        for index, (name, status, color) in enumerate(features):
            chip = tk.Frame(grid, bg=SURFACE_SOFT, padx=12, pady=10)
            chip.grid(row=index // 4, column=index % 4, sticky="ew", padx=4, pady=4)
            tk.Label(
                chip,
                text=name,
                bg=SURFACE_SOFT,
                fg=INK,
                font=("Segoe UI", 10, "bold"),
            ).pack(anchor="w")
            tk.Label(
                chip,
                text=status,
                bg=SURFACE_SOFT,
                fg=color,
                font=("Segoe UI", 8, "bold"),
            ).pack(anchor="w", pady=(2, 0))

    def _build_history(self, parent: tk.Frame) -> None:
        panel = self._panel(parent, padx=18, pady=16)
        panel.pack(fill="both", expand=True)
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(1, weight=1)

        toolbar = tk.Frame(panel, bg=SURFACE)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        toolbar.columnconfigure(0, weight=1)
        title = tk.Frame(toolbar, bg=SURFACE)
        title.grid(row=0, column=0, sticky="w")
        self._quiet_label(title, "History").pack(anchor="w")
        tk.Label(
            title,
            text="Recent transcripts",
            bg=SURFACE,
            fg=INK,
            font=("Segoe UI", 18, "bold"),
        ).pack(anchor="w")

        search = tk.Entry(
            toolbar,
            textvariable=self.history_search_var,
            bg=SURFACE_SOFT,
            fg=INK,
            insertbackground=INK,
            relief="flat",
            highlightthickness=1,
            highlightbackground=LINE,
            highlightcolor=PINK,
            width=28,
            font=("Segoe UI", 10),
        )
        search.grid(row=0, column=1, sticky="e")

        body = tk.Frame(panel, bg=SURFACE)
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        list_shell = tk.Frame(body, bg=SURFACE_SOFT, padx=10, pady=10)
        list_shell.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        list_shell.rowconfigure(0, weight=1)
        list_shell.columnconfigure(0, weight=1)
        scrollbar = tk.Scrollbar(list_shell, orient="vertical")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.history_list = tk.Listbox(
            list_shell,
            bg=SURFACE_SOFT,
            fg=INK,
            selectbackground=ACCENT,
            selectforeground="#ffffff",
            activestyle="none",
            font=("Segoe UI", 10),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            yscrollcommand=scrollbar.set,
        )
        self.history_list.grid(row=0, column=0, sticky="nsew")
        self.history_list.bind("<<ListboxSelect>>", lambda _event: self._select_history_row())
        scrollbar.configure(command=self.history_list.yview)

        preview = tk.Frame(body, bg=SURFACE, highlightbackground=LINE, highlightthickness=1)
        preview.grid(row=0, column=1, sticky="nsew")
        preview.rowconfigure(1, weight=1)
        preview.columnconfigure(0, weight=1)
        head = tk.Frame(preview, bg=SURFACE)
        head.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 0))
        self._quiet_label(head, "Selected").pack(side="left")
        self._button(head, "Copy", self._copy_selected, variant="soft").pack(side="right")
        self.history_preview = tk.Text(
            preview,
            bg=SURFACE,
            fg=INK,
            relief="flat",
            borderwidth=0,
            wrap="word",
            font=("Segoe UI", 11),
            padx=14,
            pady=12,
        )
        self.history_preview.grid(row=1, column=0, sticky="nsew")

        footer = tk.Frame(panel, bg=SURFACE)
        footer.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        self._button(footer, "Refresh", self._refresh_history, variant="soft").pack(side="right")

    def _build_install(self, parent: tk.Frame) -> None:
        intro = self._panel(parent, padx=22, pady=22)
        intro.pack(fill="x", pady=(0, 14))
        self._quiet_label(intro, "GitHub setup").pack(anchor="w")
        tk.Label(
            intro,
            text="Clean install, no heavy files in the repo.",
            bg=SURFACE,
            fg=INK,
            font=("Segoe UI", 22, "bold"),
        ).pack(anchor="w")
        tk.Label(
            intro,
            text="The repository keeps code and docs only. Models, virtualenvs, caches, and builds stay local on D:.",
            bg=SURFACE,
            fg=MUTED,
            justify="left",
            wraplength=650,
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", pady=(8, 0))

        self._command_card(
            parent,
            "Install from GitHub",
            'powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/TheRofli/speech/main/bootstrap.ps1 | iex"',
        )
        self._command_card(parent, "Download Parakeet", "speech parakeet install")
        requirements = self._panel(parent)
        requirements.pack(fill="x")
        self._section_title(requirements, "Requirements")
        tk.Label(
            requirements,
            text="Windows 11, Python 3.11, microphone, 8 GB RAM minimum, 16 GB+ recommended, 12-20 GB free on D:. CPU is the stable default; CUDA is optional.",
            bg=SURFACE,
            fg=MUTED,
            justify="left",
            wraplength=680,
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w")

    def _scroll_area(self, parent: tk.Frame) -> tuple[tk.Frame, tk.Frame]:
        outer = tk.Frame(parent, bg=BG)
        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        content = tk.Frame(canvas, bg=BG)
        content_id = canvas.create_window((0, 0), window=content, anchor="nw")
        self.content_canvas = canvas

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def on_content_configure(_event) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def on_canvas_configure(event) -> None:
            canvas.itemconfigure(content_id, width=event.width)

        def on_mousewheel(event) -> None:
            delta = -1 * int(event.delta / 120) if event.delta else 0
            if delta:
                canvas.yview_scroll(delta, "units")

        content.bind("<Configure>", on_content_configure)
        canvas.bind("<Configure>", on_canvas_configure)
        canvas.bind("<Enter>", lambda _event: canvas.bind_all("<MouseWheel>", on_mousewheel))
        canvas.bind("<Leave>", lambda _event: canvas.unbind_all("<MouseWheel>"))
        return outer, content

    def _panel(self, parent: tk.Frame, padx: int = 16, pady: int = 14) -> tk.Frame:
        frame = tk.Frame(
            parent,
            bg=SURFACE,
            highlightbackground=LINE,
            highlightthickness=1,
            padx=padx,
            pady=pady,
        )
        return frame

    def _nav_button(self, parent: tk.Frame, tab: str, label: str) -> tk.Button:
        button = tk.Button(
            parent,
            text=label,
            command=lambda: self._select_tab(tab),
            bg=SURFACE,
            fg=MUTED,
            activebackground=SURFACE_SOFT,
            activeforeground=INK,
            bd=0,
            relief="flat",
            anchor="w",
            cursor="hand2",
            padx=14,
            pady=10,
            font=("Segoe UI", 11, "bold"),
        )
        button.pack(fill="x", pady=3)
        return button

    def _button(
        self,
        parent: tk.Frame,
        text: str,
        command,
        variant: str = "primary",
    ) -> tk.Button:
        primary = variant == "primary"
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=ACCENT if primary else SURFACE_SOFT,
            fg="#ffffff" if primary else INK,
            activebackground=ACCENT_HOVER if primary else "#f5dfe9",
            activeforeground="#ffffff" if primary else INK,
            bd=0,
            relief="flat",
            cursor="hand2",
            padx=16,
            pady=9,
            font=("Segoe UI", 10, "bold"),
        )

    def _section_title(self, parent: tk.Frame, title: str) -> None:
        tk.Label(
            parent,
            text=title,
            bg=SURFACE,
            fg=INK,
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor="w", pady=(0, 10))

    def _quiet_label(self, parent: tk.Frame, text: str) -> tk.Label:
        return tk.Label(
            parent,
            text=text,
            bg=parent.cget("bg"),
            fg=MUTED,
            font=("Segoe UI", 8, "bold"),
        )

    def _metric_card(
        self,
        parent: tk.Frame,
        index: int,
        label: str,
        variable: tk.StringVar,
        detail: str,
    ) -> None:
        row = index // 2
        column = index % 2
        card = self._panel(parent, padx=14, pady=14)
        card.grid(
            row=row,
            column=column,
            sticky="nsew",
            padx=(0 if column == 0 else 8, 0),
            pady=(0 if row == 0 else 8, 0),
        )
        self._quiet_label(card, label).pack(anchor="w")
        tk.Label(
            card,
            textvariable=variable,
            bg=SURFACE,
            fg=INK,
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w", pady=(4, 0))
        tk.Label(
            card,
            text=detail,
            bg=SURFACE,
            fg=MUTED,
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", pady=(4, 0))

    def _mini_metric(
        self,
        parent: tk.Frame,
        column: int,
        label: str,
        variable: tk.StringVar,
    ) -> None:
        box = tk.Frame(parent, bg=SURFACE_SOFT, padx=12, pady=10)
        box.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 8, 0))
        tk.Label(box, text=label, bg=SURFACE_SOFT, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w")
        tk.Label(box, textvariable=variable, bg=SURFACE_SOFT, fg=INK, font=("Segoe UI", 13, "bold")).pack(anchor="w")

    def _field(
        self,
        parent: tk.Frame,
        label: str,
        variable: tk.StringVar,
        options: tuple[str, ...],
    ) -> None:
        row = tk.Frame(parent, bg=SURFACE)
        row.pack(fill="x", pady=5)
        tk.Label(row, text=label, bg=SURFACE, fg=MUTED, font=("Segoe UI", 9, "bold")).pack(side="left")
        menu = tk.OptionMenu(row, variable, *options)
        menu.configure(
            bg=SURFACE_SOFT,
            fg=INK,
            activebackground="#f5dfe9",
            activeforeground=INK,
            bd=0,
            highlightthickness=1,
            highlightbackground=LINE,
            font=("Segoe UI", 9, "bold"),
            width=12,
        )
        menu["menu"].configure(bg=SURFACE, fg=INK, activebackground=SURFACE_SOFT)
        menu.pack(side="right")

    def _entry(self, parent: tk.Frame, label: str, variable: tk.StringVar) -> None:
        row = tk.Frame(parent, bg=SURFACE)
        row.pack(fill="x", pady=5)
        tk.Label(row, text=label, bg=SURFACE, fg=MUTED, font=("Segoe UI", 9, "bold")).pack(side="left")
        tk.Entry(
            row,
            textvariable=variable,
            bg=SURFACE_SOFT,
            fg=INK,
            insertbackground=INK,
            relief="flat",
            highlightthickness=1,
            highlightbackground=LINE,
            highlightcolor=PINK,
            width=16,
            font=("Segoe UI", 9, "bold"),
        ).pack(side="right")

    def _check(
        self,
        parent: tk.Frame,
        label: str,
        variable: tk.Variable,
        command=None,
    ) -> None:
        tk.Checkbutton(
            parent,
            text=label,
            variable=variable,
            command=command,
            bg=SURFACE,
            fg=INK,
            activebackground=SURFACE,
            activeforeground=INK,
            selectcolor=SURFACE_SOFT,
            bd=0,
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", pady=4)

    def _command_card(self, parent: tk.Frame, title: str, command: str) -> None:
        card = self._panel(parent)
        card.pack(fill="x", pady=(0, 14))
        self._section_title(card, title)
        box = tk.Text(
            card,
            height=2,
            bg=SURFACE_SOFT,
            fg=INK,
            relief="flat",
            borderwidth=0,
            wrap="word",
            font=("Consolas", 9),
            padx=12,
            pady=10,
        )
        box.pack(fill="x")
        box.insert("1.0", command)
        box.configure(state="disabled")

    def _draw_mark(self, canvas: tk.Canvas, size: int, bg: str) -> None:
        canvas.configure(bg=bg, width=size, height=size)
        canvas.create_oval(4, 4, size - 4, size - 4, fill=ACCENT, outline=ACCENT)
        heights = [10, 18, 28, 18, 10]
        center = size // 2
        start = center - 13
        for index, height in enumerate(heights):
            x = start + index * 7
            canvas.create_line(
                x,
                center - height / 2,
                x,
                center + height / 2,
                fill="#ffffff",
                width=3,
                capstyle=tk.ROUND,
            )

    def _draw_wave_pill(self, canvas: tk.Canvas) -> None:
        canvas.create_oval(0, 9, 122, 61, fill=ACCENT, outline=ACCENT)
        heights = [11, 24, 34, 25, 13, 29, 18]
        for index, height in enumerate(heights):
            x = 28 + index * 11
            canvas.create_line(
                x,
                35 - height / 2,
                x,
                35 + height / 2,
                fill="#ffffff",
                width=4,
                capstyle=tk.ROUND,
            )

    def _select_tab(self, tab: str) -> None:
        self.active_tab.set(tab)
        self._render_tab()

    def _toggle_engine(self) -> None:
        self.app.toggle_engine()
        current = bool(self.vars["engine_enabled"].get())
        self.vars["engine_enabled"].set(not current)
        self._refresh()

    def _save_settings(self) -> None:
        if not self.vars:
            return
        self.app.save_settings_values({key: var.get() for key, var in self.vars.items()})
        self._refresh()

    def _copy_selected(self) -> None:
        if self.history_list is None:
            self._copy_history_id(self.selected_history_id)
            return
        selected = self.history_list.curselection()
        if selected:
            self._copy_history_id(self.history_ids[selected[0]])
        else:
            self._copy_history_id(self.selected_history_id)

    def _copy_history_id(self, entry_id: str) -> None:
        if entry_id:
            self.app.copy_history_entry(entry_id)

    def _select_history_row(self) -> None:
        if self.history_list is None:
            return
        selected = self.history_list.curselection()
        if not selected:
            return
        if selected[0] >= len(self.history_ids):
            return
        self.selected_history_id = self.history_ids[selected[0]]
        self._update_history_preview()

    def _refresh(self) -> None:
        status_text = self.app.status_text()
        status_lower = status_text.lower()
        loading = "parakeet loading" in status_lower
        loaded = "parakeet loaded" in status_lower and "unloaded" not in status_lower
        self.status_var.set(status_text)
        self.status_headline_var.set(
            "Loading" if loading else ("Ready" if loaded else "Stopped")
        )
        model = self.app.model_status()
        self.model_var.set("Loading..." if loading else model.label)
        self.side_model_var.set(
            "loading..." if loading else (model.size_label if model.installed else "missing")
        )
        if model.path is None:
            self.model_path_var.set("Run speech parakeet install to download the model.")
        else:
            self.model_path_var.set(f"{model.snapshot[:10]}... - {model.path}")

        resources = self.app.resource_snapshot()
        self.ram_var.set(resources.ram_label)
        self.cpu_var.set(resources.cpu_label)
        self.threads_var.set(resources.threads_label)

        values = self.app.get_settings_values()
        self.device_var.set(str(values["device"]).upper())
        engine = "on" if values["engine_enabled"] else "off"
        self.status_headline_var.set(
            "Off"
            if not values["engine_enabled"]
            else ("Loading" if loading else ("Ready" if loaded else "Stopped"))
        )
        self.status_detail_var.set(
            f"Engine {engine} - Parakeet {'loading' if loading else ('loaded' if loaded else 'unloaded')} - {values['device']}"
        )
        self.mode_var.set(
            "Push-to-talk dictation - "
            f"{values['device']} - {values['backend']} backend"
        )
        output = []
        if values["paste_to_active_input"]:
            output.append("active input")
        if values["copy_to_clipboard"]:
            output.append("clipboard")
        output.append("history")
        self.output_var.set("Transcript goes to " + " + ".join(output))

        rows = self.app.history_rows()
        self.history_count_var.set(str(len(rows)))
        if rows and not self.selected_history_id:
            self.selected_history_id = rows[0][0]
        self.latest_history_id = rows[0][0] if rows else ""
        self._update_latest(rows)
        self._refresh_history(rows)

    def _refresh_history(self, rows: list[tuple[str, str]] | None = None) -> None:
        if rows is None:
            rows = self.app.history_rows()
        query = self.history_search_var.get().strip().lower()
        signature = (tuple(rows), query)
        if signature == self._history_signature and self.history_list is not None:
            self._update_history_preview()
            return
        self._history_signature = signature

        filtered = [
            (entry_id, text)
            for entry_id, text in rows
            if not query or query in text.lower()
        ]
        if filtered and self.selected_history_id not in {entry_id for entry_id, _ in filtered}:
            self.selected_history_id = filtered[0][0]
        elif not filtered and query:
            self.selected_history_id = ""
        elif rows and not self.selected_history_id:
            self.selected_history_id = rows[0][0]

        if self.history_list is None:
            self._update_history_preview(rows)
            return

        self.history_list.delete(0, tk.END)
        self.history_ids = []
        for index, (entry_id, text) in enumerate(filtered):
            self.history_ids.append(entry_id)
            preview = text.replace("\n", " ")
            if len(preview) > 92:
                preview = preview[:89] + "..."
            self.history_list.insert(tk.END, preview)
            if entry_id == self.selected_history_id:
                self.history_list.selection_set(index)
                self.history_list.activate(index)
        if not filtered:
            self.history_list.insert(tk.END, "No matching transcripts")
        self._update_history_preview(rows)

    def _update_latest(self, rows: list[tuple[str, str]]) -> None:
        if self.latest_text is None:
            return
        text = rows[0][1] if rows else "No transcript yet."
        self._set_text(self.latest_text, text)

    def _update_history_preview(self, rows: list[tuple[str, str]] | None = None) -> None:
        if self.history_preview is None:
            return
        rows = rows if rows is not None else self.app.history_rows()
        selected = next(
            (text for entry_id, text in rows if entry_id == self.selected_history_id),
            "Select a transcript to preview it here.",
        )
        self._set_text(self.history_preview, selected)

    def _set_text(self, widget: tk.Text, text: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def _schedule_refresh(self) -> None:
        if self.window is None or not self.window.winfo_exists():
            return
        self._refresh()
        self.window.after(1200, self._schedule_refresh)
