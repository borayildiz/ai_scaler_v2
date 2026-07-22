"""Tkinter GUI: interactive guitar fretboard, scale notes and related chords."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import List, Tuple

from . import audio, theory
from .fretboard import DEFAULT_TUNING, TUNINGS, Fretboard

# --- Colors -----------------------------------------------------------------
BG = "#1e2230"
PANEL_BG = "#262b3d"
BOARD_BG = "#3a2c22"
FRET_COLOR = "#c9c9c9"
NUT_COLOR = "#f2f2f2"
STRING_COLOR = "#d8d8d8"
INLAY_COLOR = "#5a4636"
SCALE_COLOR = "#3d7fd6"      # in-scale note
ROOT_COLOR = "#e8543f"       # root note (distinct color)
NOTE_TEXT = "#ffffff"
LABEL_FG = "#e8e8e8"
MUTED_FG = "#9aa3b8"

INLAY_FRETS = {3, 5, 7, 9, 15, 17, 19, 21}
DOUBLE_INLAY_FRETS = {12, 24}


class GuitarScaleApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ai_scaler - Guitar Scale & Chord Visualizer")
        self.configure(bg=BG)
        self.geometry("1180x680")
        self.minsize(980, 560)

        self.num_frets = 15
        self.fretboard = Fretboard(DEFAULT_TUNING, self.num_frets)

        # Clickable-dot registry: (x, y, radius) -> midi note.
        self._dots: List[Tuple[float, float, float, int]] = []

        self._build_controls()
        self._build_body()
        self._build_statusbar()

        self.render()

    # ------------------------------------------------------------------ UI
    def _build_controls(self) -> None:
        bar = tk.Frame(self, bg=PANEL_BG)
        bar.pack(side=tk.TOP, fill=tk.X)

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TCombobox", padding=4)

        def label(text):
            return tk.Label(bar, text=text, bg=PANEL_BG, fg=LABEL_FG,
                            font=("Helvetica", 11))

        label("Root").pack(side=tk.LEFT, padx=(12, 4), pady=10)
        self.root_var = tk.StringVar(value="C")
        root_cb = ttk.Combobox(bar, textvariable=self.root_var, width=4,
                               state="readonly", values=theory.NOTES)
        root_cb.pack(side=tk.LEFT, padx=(0, 12))
        root_cb.bind("<<ComboboxSelected>>", lambda _e: self.render())

        label("Scale").pack(side=tk.LEFT, padx=(4, 4))
        self.scale_var = tk.StringVar(value="Major (Ionian)")
        scale_cb = ttk.Combobox(bar, textvariable=self.scale_var, width=26,
                                state="readonly", values=list(theory.SCALES))
        scale_cb.pack(side=tk.LEFT, padx=(0, 12))
        scale_cb.bind("<<ComboboxSelected>>", lambda _e: self.render())

        label("Tuning").pack(side=tk.LEFT, padx=(4, 4))
        self.tuning_var = tk.StringVar(value=DEFAULT_TUNING)
        tuning_cb = ttk.Combobox(bar, textvariable=self.tuning_var, width=28,
                                 state="readonly", values=list(TUNINGS))
        tuning_cb.pack(side=tk.LEFT, padx=(0, 12))
        tuning_cb.bind("<<ComboboxSelected>>", self._on_tuning_change)

        play_btn = tk.Button(bar, text="Play scale", command=self.play_scale,
                             bg=SCALE_COLOR, fg="white", relief=tk.FLAT,
                             activebackground="#2f6bb8", font=("Helvetica", 11, "bold"),
                             padx=12, pady=4, cursor="hand2")
        play_btn.pack(side=tk.LEFT, padx=8, pady=8)

    def _build_body(self) -> None:
        body = tk.Frame(self, bg=BG)
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Fretboard canvas (left, expands).
        self.canvas = tk.Canvas(body, bg=BG, highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 6), pady=10)
        self.canvas.bind("<Configure>", lambda _e: self.render())
        self.canvas.bind("<Button-1>", self._on_canvas_click)

        # Right info panel.
        panel = tk.Frame(body, bg=PANEL_BG, width=300)
        panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 10), pady=10)
        panel.pack_propagate(False)

        tk.Label(panel, text="Scale notes", bg=PANEL_BG, fg=LABEL_FG,
                 font=("Helvetica", 12, "bold")).pack(anchor="w", padx=12, pady=(12, 2))
        self.notes_label = tk.Label(panel, text="", bg=PANEL_BG, fg=SCALE_COLOR,
                                    font=("Helvetica", 14), justify="left",
                                    wraplength=270)
        self.notes_label.pack(anchor="w", padx=12, pady=(0, 8))

        tk.Label(panel, text="Related chords", bg=PANEL_BG, fg=LABEL_FG,
                 font=("Helvetica", 12, "bold")).pack(anchor="w", padx=12, pady=(6, 2))
        tk.Label(panel, text="(click a chord to hear it)", bg=PANEL_BG,
                 fg=MUTED_FG, font=("Helvetica", 9)).pack(anchor="w", padx=12)

        # Scrollable area for chord buttons.
        chord_wrap = tk.Frame(panel, bg=PANEL_BG)
        chord_wrap.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
        self.chord_frame = tk.Frame(chord_wrap, bg=PANEL_BG)
        self.chord_frame.pack(fill=tk.BOTH, expand=True)

    def _build_statusbar(self) -> None:
        self.status = tk.Label(self, text="", bg=PANEL_BG, fg=MUTED_FG,
                               anchor="w", font=("Helvetica", 9), padx=10)
        self.status.pack(side=tk.BOTTOM, fill=tk.X)
        if not audio.available():
            self.status.config(text=audio.audio_error() or "Audio unavailable "
                               "- visuals only.")
        else:
            self.status.config(text="Ready. Click a note or chord to play.")

    # -------------------------------------------------------------- events
    def _on_tuning_change(self, _event=None) -> None:
        self.fretboard = Fretboard(self.tuning_var.get(), self.num_frets)
        self.render()

    def _on_canvas_click(self, event) -> None:
        for x, y, r, midi in self._dots:
            if (event.x - x) ** 2 + (event.y - y) ** 2 <= r * r:
                audio.play_note(midi)
                return

    # ------------------------------------------------------------- rendering
    def render(self) -> None:
        self._draw_fretboard()
        self._update_panel()

    def _draw_fretboard(self) -> None:
        c = self.canvas
        c.delete("all")
        self._dots = []

        w = c.winfo_width()
        h = c.winfo_height()
        if w < 50 or h < 50:
            return

        root = self.root_var.get()
        scale = self.scale_var.get()
        grid = self.fretboard.scale_positions(root, scale)
        num_strings = self.fretboard.num_strings

        margin_left = 70
        margin_right = 30
        margin_top = 40
        margin_bottom = 30

        board_w = w - margin_left - margin_right
        board_h = h - margin_top - margin_bottom
        fret_w = board_w / (self.num_frets + 1)  # +1 leaves room for open column
        string_gap = board_h / (num_strings - 1)

        nut_x = margin_left + fret_w  # open notes sit left of the nut
        radius = min(fret_w, string_gap) * 0.36
        radius = max(9, min(radius, 20))

        def string_y(display_row: int) -> float:
            return margin_top + display_row * string_gap

        def fret_center_x(fret: int) -> float:
            if fret == 0:
                return margin_left + fret_w * 0.5
            return nut_x + (fret - 0.5) * fret_w

        # Inlay markers (behind everything).
        board_top = string_y(0)
        board_bottom = string_y(num_strings - 1)
        board_mid = (board_top + board_bottom) / 2
        for fret in range(1, self.num_frets + 1):
            cx = fret_center_x(fret)
            if fret in DOUBLE_INLAY_FRETS:
                c.create_oval(cx - 5, board_top + string_gap - 5,
                              cx + 5, board_top + string_gap + 5,
                              fill=INLAY_COLOR, outline="")
                c.create_oval(cx - 5, board_bottom - string_gap - 5,
                              cx + 5, board_bottom - string_gap + 5,
                              fill=INLAY_COLOR, outline="")
            elif fret in INLAY_FRETS:
                c.create_oval(cx - 5, board_mid - 5, cx + 5, board_mid + 5,
                              fill=INLAY_COLOR, outline="")

        # Board background.
        c.create_rectangle(nut_x, board_top, nut_x + self.num_frets * fret_w,
                           board_bottom, fill=BOARD_BG, outline="")

        # Fret lines.
        for fret in range(0, self.num_frets + 1):
            x = nut_x + fret * fret_w
            color = NUT_COLOR if fret == 0 else FRET_COLOR
            width = 5 if fret == 0 else 2
            c.create_line(x, board_top, x, board_bottom, fill=color, width=width)

        # Fret numbers.
        for fret in range(1, self.num_frets + 1):
            c.create_text(fret_center_x(fret), margin_top - 18,
                          text=str(fret), fill=MUTED_FG, font=("Helvetica", 9))
        c.create_text(fret_center_x(0), margin_top - 18, text="open",
                      fill=MUTED_FG, font=("Helvetica", 8))

        # Strings (draw thicker for lower strings) + open-string labels.
        for display_row in range(num_strings):
            s = num_strings - 1 - display_row  # low string index at bottom
            y = string_y(display_row)
            thickness = 1 + int((num_strings - 1 - s) * 0.6)
            c.create_line(nut_x, y, nut_x + self.num_frets * fret_w, y,
                          fill=STRING_COLOR, width=max(1, thickness))
            open_note = self.fretboard.note_at(s, 0)
            c.create_text(margin_left - 24, y, text=open_note, fill=LABEL_FG,
                          font=("Helvetica", 11, "bold"))

        # Scale note dots.
        for display_row in range(num_strings):
            s = num_strings - 1 - display_row
            y = string_y(display_row)
            for pos in grid[s]:
                if not pos.in_scale:
                    continue
                cx = fret_center_x(pos.fret)
                fill = ROOT_COLOR if pos.is_root else SCALE_COLOR
                outline = "#ffffff" if pos.is_root else "#1b3a63"
                c.create_oval(cx - radius, y - radius, cx + radius, y + radius,
                              fill=fill, outline=outline, width=2)
                c.create_text(cx, y, text=pos.note, fill=NOTE_TEXT,
                              font=("Helvetica", int(radius * 0.8), "bold"))
                self._dots.append((cx, y, radius, pos.midi))

    def _update_panel(self) -> None:
        root = self.root_var.get()
        scale = self.scale_var.get()

        notes = theory.scale_notes(root, scale)
        # Emphasize the root by marking it.
        display = "  ".join(f"[{n}]" if i == 0 else n for i, n in enumerate(notes))
        self.notes_label.config(text=display)

        for child in self.chord_frame.winfo_children():
            child.destroy()

        for chord in theory.related_chords(root, scale):
            midis = _voice_chord(chord.notes)
            text = f"{chord.name:<8}  {' '.join(chord.notes)}"
            btn = tk.Button(
                self.chord_frame, text=text, anchor="w",
                bg="#323a52", fg=LABEL_FG, relief=tk.FLAT,
                activebackground="#3d4766", activeforeground="white",
                font=("Courier", 11), padx=8, pady=3, cursor="hand2",
                command=lambda m=midis: audio.play_chord(m),
            )
            btn.pack(fill=tk.X, pady=2)

    # -------------------------------------------------------------- playback
    def play_scale(self) -> None:
        root = self.root_var.get()
        scale = self.scale_var.get()
        root_midi = 48 + theory.note_index(root)  # around C3-B3
        midis = [root_midi + step for step in theory.SCALES[scale]]
        midis.append(root_midi + 12)  # finish on the octave
        audio.play_sequence(midis)


def _voice_chord(note_names: List[str]) -> List[int]:
    """Turn chord note names into an ascending MIDI voicing near octave 3-4."""
    base = 48  # C3
    midis: List[int] = []
    prev = -1
    for name in note_names:
        m = base + theory.note_index(name)
        while m <= prev:
            m += 12
        midis.append(m)
        prev = m
    return midis


def run() -> None:
    app = GuitarScaleApp()
    app.mainloop()


if __name__ == "__main__":
    run()
