"""Desktop theme and widgets."""

import tkinter as tk
from tkinter import ttk, scrolledtext
from src.voice.providers import PROVIDERS

BG, PANEL, FG, MUTED, MINT = "#101b22", "#192932", "#edf2ed", "#9bb0b8", "#a5dfbd"
MODES = ("Play Stockfish", "Local two-player", "Watch Stockfish")


class Layout:
    def build_layout(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", background=BG, foreground=FG, font=("DejaVu Sans", 10))
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG)
        style.configure("Muted.TLabel", foreground=MUTED)
        style.configure("Title.TLabel", font=("DejaVu Sans", 25, "bold"), foreground=MINT)
        style.configure("Value.TLabel", font=("DejaVu Sans", 17, "bold"), foreground=MINT)
        style.configure(
            "TButton", background="#2a424d", foreground=FG, padding=(10, 8), borderwidth=0
        )
        style.map("TButton", background=[("active", "#3b5b68")])
        style.configure("Accent.TButton", background="#3c705b")
        style.configure(
            "TCombobox",
            fieldbackground=PANEL,
            background="#2a424d",
            foreground=FG,
            arrowcolor=MINT,
            padding=4,
        )
        style.map("TCombobox", fieldbackground=[("readonly", PANEL)], foreground=[("readonly", FG)])
        style.configure("TEntry", fieldbackground=PANEL, foreground=FG, padding=4)
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=PANEL, foreground=MUTED, padding=(16, 10))
        style.map(
            "TNotebook.Tab", background=[("selected", "#2a424d")], foreground=[("selected", FG)]
        )
        style.configure(
            "Treeview",
            background=PANEL,
            fieldbackground=PANEL,
            foreground=FG,
            rowheight=26,
            borderwidth=0,
        )
        style.configure("Treeview.Heading", background="#2a424d", foreground=MUTED)
        self.root.option_add("*TCombobox*Listbox.background", PANEL)
        self.root.option_add("*TCombobox*Listbox.foreground", FG)
        outer = ttk.Frame(self.root, padding=20)
        outer.pack(fill="both", expand=True)
        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 16))
        ttk.Label(header, text="PESC-I", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="Good moves. Better questions.", style="Muted.TLabel").pack(
            side="left", padx=20
        )
        self.status = tk.StringVar()
        content = ttk.Frame(outer)
        content.pack(fill="both", expand=True)
        left = ttk.Frame(content)
        left.pack(side="left", fill="y", padx=(0, 18))
        controls = ttk.Frame(left)
        controls.pack(fill="x", pady=(0, 8))
        self.mode = tk.StringVar(value=MODES[0])
        combo = ttk.Combobox(
            controls, textvariable=self.mode, values=MODES, state="readonly", width=19
        )
        combo.pack(side="left")
        combo.bind("<<ComboboxSelected>>", self.new_game)
        self.side = tk.StringVar(value="White")
        combo = ttk.Combobox(
            controls, textvariable=self.side, values=("White", "Black"), state="readonly", width=9
        )
        combo.pack(side="left", padx=8)
        combo.bind("<<ComboboxSelected>>", self.side_changed)
        self.pause_button = ttk.Button(controls, text="Pause", command=self.toggle_pause)
        self.pause_button.pack(side="right")
        self.canvas = tk.Canvas(left, width=564, height=564, bg=BG, highlightthickness=0)
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.on_click)
        actions = ttk.Frame(left)
        actions.pack(fill="x", pady=(6, 12))
        for text, command in (
            ("New game", self.new_game),
            ("Undo", self.undo),
            ("Hint", self.analyze_position),
            ("Flip board", self.flip),
        ):
            ttk.Button(actions, text=text, command=command).pack(side="left", padx=(0, 8))
        ttk.Label(left, textvariable=self.status, wraplength=550, style="Muted.TLabel").pack(
            anchor="w", pady=(2, 8)
        )
        ttk.Label(
            left,
            text="Click to move · Last move in gold · Legal moves in mint",
            style="Muted.TLabel",
            font=("DejaVu Sans", 9),
        ).pack(anchor="w")
        right = ttk.Frame(content)
        right.pack(side="left", fill="both", expand=True)
        self.notebook = ttk.Notebook(right)
        self.notebook.pack(fill="both", expand=True)
        game = ttk.Frame(self.notebook, padding=(4, 12))
        settings = ttk.Frame(self.notebook, padding=(10, 12))
        self.notebook.add(game, text="At the board")
        self.notebook.add(settings, text="Commentary setup")
        self.turn_text = tk.StringVar(value="White to move")
        ttk.Label(game, textvariable=self.turn_text, style="Value.TLabel").pack(anchor="w")
        self.eval_text = tk.StringVar(value="Evaluation  —")
        ttk.Label(game, textvariable=self.eval_text).pack(anchor="w", pady=(10, 2))
        ttk.Label(
            game,
            text="Positive favors White; negative favors Black.",
            style="Muted.TLabel",
            font=("DejaVu Sans", 9),
        ).pack(anchor="w")
        self.pv_text = tk.StringVar(value="Play a move to see Stockfish's continuation.")
        ttk.Label(game, textvariable=self.pv_text, wraplength=430, style="Muted.TLabel").pack(
            anchor="w", pady=(8, 14)
        )
        self.note_status = tk.StringVar(value="ENGINE NOTES · No model needed")
        ttk.Label(game, textvariable=self.note_status, style="Muted.TLabel", wraplength=430).pack(
            anchor="w"
        )
        self.notes = scrolledtext.ScrolledText(
            game,
            height=10,
            width=43,
            wrap="word",
            bg=PANEL,
            fg=FG,
            font=("DejaVu Sans", 11),
            relief="flat",
            padx=14,
            pady=12,
            insertbackground=MINT,
            highlightthickness=0,
        )
        self.notes.pack(fill="both", expand=True, pady=(8, 6))
        self.notes.tag_configure("heading", foreground=MINT, font=("DejaVu Sans", 11, "bold"))
        self.notes.tag_configure("muted", foreground=MUTED, font=("DejaVu Sans", 9))
        self.notes.configure(state="disabled")
        self.skip_button = ttk.Button(
            game,
            text="Continue without explanation",
            command=self.skip_commentary,
            state="disabled",
        )
        self.skip_button.pack(anchor="w", pady=(0, 10))
        ttk.Label(game, text="MOVEBOOK", style="Muted.TLabel").pack(anchor="w", pady=(0, 6))
        self.history = ttk.Treeview(
            game, columns=("number", "white", "black"), show="headings", height=5
        )
        for name, label, width in (
            ("number", "#", 40),
            ("white", "White", 140),
            ("black", "Black", 140),
        ):
            self.history.heading(name, text=label)
            self.history.column(name, width=width, stretch=name != "number")
        self.history.pack(fill="x")
        self.provider = tk.StringVar(value="Engine notes (offline)")
        self.url, self.model, self.key = tk.StringVar(), tk.StringVar(), tk.StringVar()
        self.verbosity = tk.StringVar(value="Brief")
        self.timeout, self.think_time = tk.StringVar(value="45"), tk.StringVar(value="0.4")
        self.connection = tk.StringVar(value="Choose a provider. The board works offline, too.")
        self.active_text = tk.StringVar(value="Active: Engine notes (offline)")
        ttk.Label(settings, text="Give your board a voice", style="Value.TLabel").pack(anchor="w")
        ttk.Label(
            settings,
            text="Choose who explains. Stockfish checks the moves.",
            wraplength=420,
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(6, 8))
        self.field(settings, "Provider", self.provider, tuple(PROVIDERS), self.provider_changed)
        self.url_entry = self.field(settings, "Server base URL", self.url)
        self.key_entry = self.field(
            settings, "API key / token (optional for local)", self.key, secret=True
        )
        self.model_combo = self.field(
            settings, "Model · choose or type an exact ID", self.model, ()
        )
        ttk.Button(settings, text="Find available models", command=self.refresh_models).pack(
            anchor="w", pady=(8, 4)
        )
        ttk.Label(
            settings, textvariable=self.connection, wraplength=420, style="Muted.TLabel"
        ).pack(anchor="w", pady=(2, 4))
        self.field(settings, "Explanation length", self.verbosity, ("Brief", "Detailed"))
        self.field(settings, "Request timeout (seconds · 5–180)", self.timeout)
        self.field(
            settings, "Stockfish time per analysis / move (seconds · 0.1–5)", self.think_time
        )
        ttk.Button(
            settings,
            text="Apply commentary settings",
            command=self.apply_settings,
            style="Accent.TButton",
        ).pack(anchor="w", pady=(14, 8))
        ttk.Label(settings, textvariable=self.active_text, wraplength=420).pack(anchor="w")
        ttk.Label(
            settings,
            text=(
                "Keys stay in memory. Settings apply next move.\n"
                "Remote APIs receive move facts. LLM text can be wrong."
            ),
            wraplength=420,
            style="Muted.TLabel",
            font=("DejaVu Sans", 9),
        ).pack(anchor="w", pady=12)

    def field(self, parent, label, variable, values=None, command=None, secret=False):
        ttk.Label(parent, text=label, style="Muted.TLabel", font=("DejaVu Sans", 9)).pack(
            anchor="w", pady=(4, 2)
        )
        if values is None:
            widget = ttk.Entry(parent, textvariable=variable, show="•" if secret else "")
        else:
            widget = ttk.Combobox(
                parent,
                textvariable=variable,
                values=values,
                state="normal" if label.startswith("Model") else "readonly",
            )
        widget.pack(fill="x")
        if command:
            widget.bind("<<ComboboxSelected>>", command)
        return widget
