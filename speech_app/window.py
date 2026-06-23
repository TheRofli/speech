from __future__ import annotations

import tkinter as tk
from tkinter import ttk
import importlib.util
from typing import Protocol

from .model_status import ModelStatus
from .resources import ResourceSnapshot


BG = "#f7f7f5"
PANEL = "#ffffff"
PANEL_ALT = "#f0f0ed"
INK = "#151515"
MUTED = "#6c696f"
LINE = "#dfdfdb"
ACCENT = "#16131b"
SUCCESS = "#1d7a4d"
SOFT_ACCENT = "#ece7f6"


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
        self.history_list: tk.Listbox | None = None
        self.history_ids: list[str] = []
        self.vars: dict[str, tk.Variable] = {}
        self.status_var = tk.StringVar(value="")
        self.model_var = tk.StringVar(value="")
        self.model_path_var = tk.StringVar(value="")
        self.ram_var = tk.StringVar(value="")
        self.cpu_var = tk.StringVar(value="")
        self.threads_var = tk.StringVar(value="")
        self.mode_var = tk.StringVar(value="")
        self.output_var = tk.StringVar(value="")
        self._history_signature: tuple[tuple[str, str], ...] = ()

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

    def refresh(self) -> None:
        self._refresh()

    def _build(self) -> None:
        self.window = tk.Toplevel(self.root)
        self.window.title("Speech")
        self.window.geometry("780x640")
        self.window.minsize(420, 360)
        self.window.configure(bg=BG)
        icon = getattr(self.app, "icon_photo", None)
        if icon is not None:
            self.window.iconphoto(False, icon)
        self.window.protocol("WM_DELETE_WINDOW", self.window.withdraw)

        style = ttk.Style(self.window)
        style.theme_use("clam")
        style.configure(".", background=BG, foreground=INK, font=("Segoe UI", 10))
        style.configure(
            "TButton",
            padding=(14, 8),
            font=("Segoe UI", 10),
            borderwidth=0,
            focusthickness=0,
        )
        style.configure("Primary.TButton", background=ACCENT, foreground="#ffffff")
        style.map("Primary.TButton", background=[("active", "#302a37")])
        style.configure("Soft.TButton", background=PANEL_ALT, foreground=INK)
        style.map("Soft.TButton", background=[("active", "#e4e4df")])
        style.configure(
            "TMenubutton",
            background=PANEL_ALT,
            foreground=INK,
            padding=(10, 6),
            relief="flat",
        )
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            padding=(16, 8),
            font=("Segoe UI", 10, "bold"),
            background=PANEL_ALT,
            foreground=MUTED,
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", PANEL)],
            foreground=[("selected", INK)],
        )

        shell = tk.Frame(self.window, bg=BG)
        shell.pack(fill="both", expand=True, padx=24, pady=20)

        self._build_header(shell)

        notebook = ttk.Notebook(shell)
        notebook.pack(fill="both", expand=True, pady=(16, 0))

        overview_outer, overview = self._scroll_tab(notebook)
        controls_outer, controls = self._scroll_tab(notebook)
        history = tk.Frame(notebook, bg=BG)

        notebook.add(overview_outer, text="Overview")
        notebook.add(controls_outer, text="Controls")
        notebook.add(history, text="History")

        self._build_parakeet_panel(overview)
        self._build_resources_panel(overview)
        self._build_parakeet_modes_panel(overview)

        self._build_runtime_panel(controls)
        self._build_output_panel(controls)

        self._build_history_panel(history)

        self._schedule_refresh()

    def _scroll_tab(self, parent: ttk.Notebook) -> tuple[tk.Frame, tk.Frame]:
        outer = tk.Frame(parent, bg=BG)
        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        content = tk.Frame(canvas, bg=BG)
        content_id = canvas.create_window((0, 0), window=content, anchor="nw")

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

    def _build_header(self, parent: tk.Frame) -> None:
        header = tk.Frame(parent, bg=BG)
        header.pack(fill="x")
        mark = tk.Canvas(header, width=52, height=52, bg=BG, highlightthickness=0)
        mark.pack(side="left")
        mark.create_oval(3, 3, 49, 49, fill=ACCENT, outline=ACCENT)
        for index, height in enumerate([8, 16, 24, 16, 8]):
            x = 17 + index * 5
            mark.create_line(
                x,
                26 - height / 2,
                x,
                26 + height / 2,
                fill="#ffffff",
                width=3,
                capstyle=tk.ROUND,
            )

        title = tk.Frame(header, bg=BG)
        title.pack(side="left", padx=(12, 0))
        tk.Label(
            title,
            text="Speech",
            bg=BG,
            fg=INK,
            font=("Segoe UI", 23, "bold"),
        ).pack(anchor="w")
        tk.Label(
            title,
            textvariable=self.status_var,
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w")

        actions = tk.Frame(header, bg=BG)
        actions.pack(side="right")
        ttk.Button(
            actions,
            text="Load",
            command=self.app.load_model_background,
            style="Primary.TButton",
        ).pack(side="left", padx=(0, 8))
        ttk.Button(
            actions,
            text="Unload",
            command=self.app.unload_model,
            style="Soft.TButton",
        ).pack(side="left")

    def _build_parakeet_panel(self, parent: tk.Frame) -> None:
        panel = self._panel(parent)
        panel.pack(fill="x", pady=(0, 12))
        self._panel_title(panel, "Parakeet")
        self._big_value(panel, self.model_var)
        tk.Label(
            panel,
            textvariable=self.model_path_var,
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 9),
            wraplength=285,
            justify="left",
        ).pack(anchor="w", pady=(6, 0))

    def _build_runtime_panel(self, parent: tk.Frame) -> None:
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

        panel = self._panel(parent)
        panel.pack(fill="x", pady=(0, 12))
        self._panel_title(panel, "Runtime")
        self._field(panel, "Device", self.vars["device"], ("cpu", "cuda", "auto"))
        self._field(
            panel,
            "Backend",
            self.vars["backend"],
            ("auto", "transformers", "nemo"),
        )
        self._entry(panel, "Hotkey", self.vars["hotkey"])

        tk.Label(
            panel,
            textvariable=self.mode_var,
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 9),
            wraplength=285,
            justify="left",
        ).pack(anchor="w", pady=(8, 0))

        checks = tk.Frame(panel, bg=PANEL)
        checks.pack(fill="x", pady=(10, 0))
        for key, label in [
            ("engine_enabled", "Engine enabled"),
            ("preload_model", "Preload on launch"),
        ]:
            tk.Checkbutton(
                checks,
                text=label,
                variable=self.vars[key],
                bg=PANEL,
                fg=INK,
                activebackground=PANEL,
                selectcolor=PANEL_ALT,
                font=("Segoe UI", 9),
            ).pack(anchor="w")

        row = tk.Frame(panel, bg=PANEL)
        row.pack(fill="x", pady=(10, 0))
        ttk.Button(
            row,
            text="Save",
            command=self._save_settings,
            style="Primary.TButton",
        ).pack(side="left", padx=(0, 8))
        ttk.Button(row, text="Engine", command=self._toggle_engine, style="Soft.TButton").pack(side="left")

    def _build_resources_panel(self, parent: tk.Frame) -> None:
        panel = self._panel(parent)
        panel.pack(fill="x", pady=(0, 12))
        self._panel_title(panel, "Resources")
        row = tk.Frame(panel, bg=PANEL)
        row.pack(fill="x")
        self._metric(row, "RAM", self.ram_var).pack(side="left", expand=True, fill="x")
        self._metric(row, "CPU", self.cpu_var).pack(side="left", expand=True, fill="x", padx=8)
        self._metric(row, "Threads", self.threads_var).pack(side="left", expand=True, fill="x")

    def _build_parakeet_modes_panel(self, parent: tk.Frame) -> None:
        panel = self._panel(parent)
        panel.pack(fill="x", pady=(0, 12))
        self._panel_title(panel, "Parakeet Modes")

        grid = tk.Frame(panel, bg=PANEL)
        grid.pack(fill="x")
        nemo_status = "Ready" if importlib.util.find_spec("nemo") else "Requires NeMo"
        features = [
            ("Model size", "0.6B only", ACCENT),
            ("Dictation", "Active", SUCCESS),
            ("Auto language", "Active", SUCCESS),
            ("Punctuation", "Active", SUCCESS),
            ("Timestamps", "Supported", "#5f35b1"),
            ("Long-form", nemo_status, "#6c557e"),
            ("Streaming", nemo_status, "#6c557e"),
            ("Medium/Large", "Not in v3", MUTED),
        ]
        for index, (name, status, color) in enumerate(features):
            chip = tk.Frame(grid, bg=PANEL_ALT, padx=12, pady=9)
            chip.grid(row=index // 2, column=index % 2, sticky="ew", padx=4, pady=4)
            tk.Label(
                chip,
                text=name,
                bg=PANEL_ALT,
                fg=INK,
                font=("Segoe UI", 10, "bold"),
            ).pack(anchor="w")
            tk.Label(
                chip,
                text=status,
                bg=PANEL_ALT,
                fg=color,
                font=("Segoe UI", 8, "bold"),
            ).pack(anchor="w", pady=(2, 0))
        for column in range(2):
            grid.columnconfigure(column, weight=1)

    def _build_output_panel(self, parent: tk.Frame) -> None:
        panel = self._panel(parent)
        panel.pack(fill="x", pady=(0, 12))
        self._panel_title(panel, "Output")
        tk.Label(
            panel,
            textvariable=self.output_var,
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 10),
        ).pack(anchor="w")
        for key, label in [
            ("paste_to_active_input", "Insert into active input"),
            ("copy_to_clipboard", "Copy to clipboard"),
        ]:
            tk.Checkbutton(
                panel,
                text=label,
                variable=self.vars[key],
                bg=PANEL,
                fg=INK,
                activebackground=PANEL,
                selectcolor=PANEL_ALT,
                font=("Segoe UI", 9),
                command=self._save_settings,
            ).pack(anchor="w", pady=(8, 0))

    def _build_history_panel(self, parent: tk.Frame) -> None:
        panel = self._panel(parent)
        panel.pack(fill="both", expand=True)
        panel.rowconfigure(1, weight=1)
        self._panel_title(panel, "History")

        list_frame = tk.Frame(panel, bg=PANEL)
        list_frame.pack(fill="both", expand=True, pady=(4, 10))
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical")
        scrollbar.pack(side="right", fill="y")
        self.history_list = tk.Listbox(
            list_frame,
            bg="#ffffff",
            fg=INK,
            selectbackground=ACCENT,
            selectforeground="#ffffff",
            activestyle="none",
            font=("Segoe UI", 10),
            relief="flat",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=LINE,
            yscrollcommand=scrollbar.set,
        )
        self.history_list.pack(side="left", fill="both", expand=True)
        scrollbar.configure(command=self.history_list.yview)
        row = tk.Frame(panel, bg=PANEL)
        row.pack(fill="x")
        ttk.Button(row, text="Copy Selected", command=self._copy_selected, style="Primary.TButton").pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(row, text="Refresh", command=self._refresh_history, style="Soft.TButton").pack(
            side="left"
        )

    def _panel(self, parent: tk.Frame) -> tk.Frame:
        frame = tk.Frame(parent, bg=PANEL, highlightbackground=LINE, highlightthickness=1)
        frame.configure(padx=16, pady=14)
        return frame

    def _panel_title(self, parent: tk.Frame, title: str) -> None:
        tk.Label(
            parent,
            text=title,
            bg=PANEL,
            fg=INK,
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", pady=(0, 8))

    def _big_value(self, parent: tk.Frame, variable: tk.StringVar) -> None:
        tk.Label(
            parent,
            textvariable=variable,
            bg=PANEL,
            fg=INK,
            font=("Segoe UI", 18, "bold"),
        ).pack(anchor="w")

    def _metric(self, parent: tk.Frame, label: str, variable: tk.StringVar) -> tk.Frame:
        box = tk.Frame(parent, bg=PANEL_ALT, padx=10, pady=8)
        tk.Label(box, text=label, bg=PANEL_ALT, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w")
        tk.Label(box, textvariable=variable, bg=PANEL_ALT, fg=INK, font=("Segoe UI", 12, "bold")).pack(anchor="w")
        return box

    def _field(
        self,
        parent: tk.Frame,
        label: str,
        variable: tk.StringVar,
        options: tuple[str, ...],
    ) -> None:
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x", pady=4)
        tk.Label(row, text=label, bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(side="left")
        ttk.OptionMenu(row, variable, variable.get(), *options).pack(side="right")

    def _entry(self, parent: tk.Frame, label: str, variable: tk.StringVar) -> None:
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x", pady=4)
        tk.Label(row, text=label, bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(side="left")
        tk.Entry(
            row,
            textvariable=variable,
            bg="#ffffff",
            fg=INK,
            relief="flat",
            highlightthickness=1,
            highlightbackground=LINE,
            width=14,
        ).pack(side="right")

    def _toggle_engine(self) -> None:
        self.app.toggle_engine()
        current = bool(self.vars["engine_enabled"].get())
        self.vars["engine_enabled"].set(not current)
        self._refresh()

    def _save_settings(self) -> None:
        self.app.save_settings_values({key: var.get() for key, var in self.vars.items()})
        self._refresh()

    def _copy_selected(self) -> None:
        if self.history_list is None:
            return
        selected = self.history_list.curselection()
        if not selected:
            return
        self.app.copy_history_entry(self.history_ids[selected[0]])

    def _refresh(self) -> None:
        self.status_var.set(self.app.status_text())
        model = self.app.model_status()
        self.model_var.set(model.label)
        if model.path is None:
            self.model_path_var.set("Run speech parakeet install to download the model.")
        else:
            self.model_path_var.set(f"{model.snapshot[:10]}... - {model.path}")

        resources = self.app.resource_snapshot()
        self.ram_var.set(resources.ram_label)
        self.cpu_var.set(resources.cpu_label)
        self.threads_var.set(resources.threads_label)

        values = self.app.get_settings_values()
        self.mode_var.set(
            "Push-to-talk dictation - "
            f"{values['device']} - {values['backend']} backend"
        )
        output = []
        if values["paste_to_active_input"]:
            output.append("active input (paste)")
        if values["copy_to_clipboard"]:
            output.append("clipboard")
        output.append("history")
        self.output_var.set("Transcript goes to " + " + ".join(output))
        self._refresh_history()

    def _refresh_history(self) -> None:
        if self.history_list is None:
            return
        rows = self.app.history_rows()
        signature = tuple(rows)
        if signature == self._history_signature:
            return
        self._history_signature = signature

        self.history_list.delete(0, tk.END)
        self.history_ids = []
        for entry_id, text in rows:
            self.history_ids.append(entry_id)
            preview = text.replace("\n", " ")
            if len(preview) > 140:
                preview = preview[:137] + "..."
            self.history_list.insert(tk.END, preview)

    def _schedule_refresh(self) -> None:
        if self.window is None or not self.window.winfo_exists():
            return
        self._refresh()
        self.window.after(1200, self._schedule_refresh)
