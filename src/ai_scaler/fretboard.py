"""Guitar fretboard model: tunings and fret-to-note mapping."""

from __future__ import annotations

from typing import Dict, List, NamedTuple

from . import theory

# Open-string MIDI note numbers, ordered low string -> high string.
# (Standard guitar: E2 A2 D3 G3 B3 E4)
TUNINGS: Dict[str, List[int]] = {
    "Standard (E A D G B E)": [40, 45, 50, 55, 59, 64],
    "Drop D (D A D G B E)": [38, 45, 50, 55, 59, 64],
    "Half Step Down (Eb Ab Db Gb Bb Eb)": [39, 44, 49, 54, 58, 63],
    "Open G (D G D G B D)": [38, 43, 50, 55, 59, 62],
    "DADGAD": [38, 45, 50, 55, 57, 62],
}

DEFAULT_TUNING = "Standard (E A D G B E)"


class FretPosition(NamedTuple):
    """A single position on the fretboard."""

    string_index: int   # 0 == lowest string (top of screen when drawn high->low)
    fret: int           # 0 == open string
    note: str           # note name, e.g. "C#"
    midi: int           # MIDI note number for audio
    in_scale: bool
    is_root: bool


class Fretboard:
    """Models a fretted string instrument for a given tuning and fret count."""

    def __init__(self, tuning: str = DEFAULT_TUNING, num_frets: int = 15):
        if tuning not in TUNINGS:
            raise ValueError(f"Unknown tuning: {tuning!r}")
        self.tuning_name = tuning
        self.open_midi = TUNINGS[tuning]
        self.num_strings = len(self.open_midi)
        self.num_frets = num_frets

    def midi_at(self, string_index: int, fret: int) -> int:
        """MIDI note number for a string/fret combination."""
        return self.open_midi[string_index] + fret

    def note_at(self, string_index: int, fret: int) -> str:
        """Note name for a string/fret combination."""
        return theory.note_name(self.midi_at(string_index, fret) % 12)

    def scale_positions(self, root: str, scale_name: str) -> List[List[FretPosition]]:
        """Return a grid [string][fret] of FretPosition entries.

        Each entry records whether that position belongs to the scale and
        whether it is the root note.
        """
        scale_pcs = set(theory.scale_pitch_classes(root, scale_name))
        root_pc = theory.note_index(root)

        grid: List[List[FretPosition]] = []
        for s in range(self.num_strings):
            row: List[FretPosition] = []
            for fret in range(self.num_frets + 1):
                midi = self.midi_at(s, fret)
                pc = midi % 12
                row.append(
                    FretPosition(
                        string_index=s,
                        fret=fret,
                        note=theory.note_name(pc),
                        midi=midi,
                        in_scale=pc in scale_pcs,
                        is_root=pc == root_pc,
                    )
                )
            grid.append(row)
        return grid
