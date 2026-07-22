"""Music theory core: notes, scales (common + exotic) and chord harmonization.

Pitch classes are integers 0-11 where 0 == C. Scales are stored as interval
patterns (semitone offsets from the root, always starting at 0).
"""

from __future__ import annotations

from typing import Dict, List, NamedTuple

# Chromatic notes using sharp spelling (kept simple, consistent).
NOTES: List[str] = [
    "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B",
]

# Accepts both sharps and flats (and a couple of enharmonics) as input.
_NOTE_TO_INDEX: Dict[str, int] = {
    "C": 0, "B#": 0,
    "C#": 1, "DB": 1,
    "D": 2,
    "D#": 3, "EB": 3,
    "E": 4, "FB": 4,
    "F": 5, "E#": 5,
    "F#": 6, "GB": 6,
    "G": 7,
    "G#": 8, "AB": 8,
    "A": 9,
    "A#": 10, "BB": 10,
    "B": 11, "CB": 11,
}

# Scale interval patterns (semitones from the root).
SCALES: Dict[str, List[int]] = {
    # --- Common ---
    "Major (Ionian)": [0, 2, 4, 5, 7, 9, 11],
    "Natural Minor (Aeolian)": [0, 2, 3, 5, 7, 8, 10],
    "Harmonic Minor": [0, 2, 3, 5, 7, 8, 11],
    "Melodic Minor": [0, 2, 3, 5, 7, 9, 11],
    "Dorian": [0, 2, 3, 5, 7, 9, 10],
    "Phrygian": [0, 1, 3, 5, 7, 8, 10],
    "Lydian": [0, 2, 4, 6, 7, 9, 11],
    "Mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "Locrian": [0, 1, 3, 5, 6, 8, 10],
    "Major Pentatonic": [0, 2, 4, 7, 9],
    "Minor Pentatonic": [0, 3, 5, 7, 10],
    "Blues": [0, 3, 5, 6, 7, 10],
    # --- Exotic ---
    "Whole Tone": [0, 2, 4, 6, 8, 10],
    "Diminished (Half-Whole)": [0, 1, 3, 4, 6, 7, 9, 10],
    "Diminished (Whole-Half)": [0, 2, 3, 5, 6, 8, 9, 11],
    "Phrygian Dominant": [0, 1, 4, 5, 7, 8, 10],
    "Hungarian Minor": [0, 2, 3, 6, 7, 8, 11],
    "Double Harmonic (Byzantine)": [0, 1, 4, 5, 7, 8, 11],
    "Neapolitan Major": [0, 1, 3, 5, 7, 9, 11],
    "Neapolitan Minor": [0, 1, 3, 5, 7, 8, 11],
    "Enigmatic": [0, 1, 4, 6, 8, 10, 11],
    "Japanese Hirajoshi": [0, 2, 3, 7, 8],
    "In Sen": [0, 1, 5, 7, 10],
    "Prometheus": [0, 2, 4, 6, 9, 10],
    "Augmented": [0, 3, 4, 7, 8, 11],
}


def note_index(note: str) -> int:
    """Return the pitch class (0-11) for a note name like 'C#', 'Db', 'A'."""
    key = note.strip().capitalize()
    if key not in _NOTE_TO_INDEX:
        raise ValueError(f"Unknown note: {note!r}")
    return _NOTE_TO_INDEX[key]


def note_name(pitch_class: int) -> str:
    """Return the sharp-spelled name for a pitch class."""
    return NOTES[pitch_class % 12]


def scale_pitch_classes(root: str, scale_name: str) -> List[int]:
    """Return absolute pitch classes (0-11) for a scale, in ascending order."""
    if scale_name not in SCALES:
        raise ValueError(f"Unknown scale: {scale_name!r}")
    root_pc = note_index(root)
    return [(root_pc + step) % 12 for step in SCALES[scale_name]]


def scale_notes(root: str, scale_name: str) -> List[str]:
    """Return the note names of a scale, e.g. C Major -> C D E F G A B."""
    return [note_name(pc) for pc in scale_pitch_classes(root, scale_name)]


class Chord(NamedTuple):
    """A harmonized chord: its display name, quality suffix and member notes."""

    name: str          # e.g. "Dm7"
    root: str          # e.g. "D"
    quality: str       # e.g. "m7"
    notes: List[str]   # member note names


# Triad quality from the (third, fifth) interval pair (semitones from root).
_TRIAD_QUALITY = {
    (4, 7): "",       # major
    (3, 7): "m",      # minor
    (3, 6): "dim",    # diminished
    (4, 8): "aug",    # augmented
    (2, 7): "sus2",
    (5, 7): "sus4",
    (4, 6): "(b5)",   # major flat-five
    (3, 8): "m(#5)",
}

# Seventh label from (triad_suffix, seventh_interval).
_SEVENTH_QUALITY = {
    ("", 11): "maj7",
    ("", 10): "7",
    ("m", 10): "m7",
    ("m", 11): "mMaj7",
    ("dim", 10): "m7b5",   # half-diminished
    ("dim", 9): "dim7",
    ("aug", 11): "augMaj7",
    ("aug", 10): "aug7",
}


def _quality_from_intervals(intervals: List[int]) -> str:
    """Derive a chord-quality suffix from intervals (semitones from chord root).

    ``intervals`` includes 0 (the root). Handles triads and, when a seventh is
    present, common seventh chords. Falls back to listing the intervals.
    """
    interval_set = set(intervals)
    third = next((i for i in (3, 4, 2, 5) if i in interval_set), None)
    fifth = next((i for i in (7, 6, 8) if i in interval_set), None)
    seventh = next((i for i in (11, 10, 9) if i in interval_set), None)

    if third is None or fifth is None:
        return "(" + ",".join(str(i) for i in sorted(interval_set)) + ")"

    triad = _TRIAD_QUALITY.get((third, fifth))
    if triad is None:
        return "(" + ",".join(str(i) for i in sorted(interval_set)) + ")"

    if seventh is not None:
        return _SEVENTH_QUALITY.get((triad, seventh), triad + "add7")
    return triad


# Common chord formulas (intervals from the chord root) with display suffixes,
# ordered so that richer chords are preferred when several match on one root.
_CHORD_FORMULAS = [
    ("maj7", [0, 4, 7, 11]),
    ("7", [0, 4, 7, 10]),
    ("6", [0, 4, 7, 9]),
    ("m7", [0, 3, 7, 10]),
    ("m6", [0, 3, 7, 9]),
    ("mMaj7", [0, 3, 7, 11]),
    ("m7b5", [0, 3, 6, 10]),
    ("dim7", [0, 3, 6, 9]),
    ("", [0, 4, 7]),       # major triad
    ("m", [0, 3, 7]),      # minor triad
    ("dim", [0, 3, 6]),
    ("aug", [0, 4, 8]),
    ("sus2", [0, 2, 7]),
    ("sus4", [0, 5, 7]),
]


def _harmonize_by_thirds(pcs: List[int], sevenths: bool) -> List[Chord]:
    """Build one chord per degree by stacking scale thirds (best for 7-note scales)."""
    n = len(pcs)
    chords: List[Chord] = []
    for i in range(n):
        member_pcs = [pcs[(i + step) % n] for step in (0, 2, 4)]
        if sevenths:
            member_pcs.append(pcs[(i + 6) % n])
        chord_root_pc = member_pcs[0]
        intervals = sorted({(pc - chord_root_pc) % 12 for pc in member_pcs})
        quality = _quality_from_intervals(intervals)
        root_note = note_name(chord_root_pc)
        chords.append(
            Chord(
                name=f"{root_note}{quality}",
                root=root_note,
                quality=quality,
                notes=[note_name(pc) for pc in member_pcs],
            )
        )
    return chords


def _match_chords(pcs: List[int]) -> List[Chord]:
    """Find standard chords whose notes all fit within the scale's pitch classes.

    Used for non-heptatonic scales (pentatonics, blues, symmetric scales) where
    stacking scale thirds does not yield conventional tertian chords. For each
    scale note, the richest matching formula (a subset of the scale) is kept.
    """
    pc_set = set(pcs)
    chords: List[Chord] = []
    for chord_root_pc in pcs:
        for quality, formula in _CHORD_FORMULAS:
            members = [(chord_root_pc + iv) % 12 for iv in formula]
            if all(m in pc_set for m in members):
                root_note = note_name(chord_root_pc)
                chords.append(
                    Chord(
                        name=f"{root_note}{quality}",
                        root=root_note,
                        quality=quality,
                        notes=[note_name(m) for m in members],
                    )
                )
                break  # richest match on this root wins
    return chords


def related_chords(root: str, scale_name: str, sevenths: bool = True) -> List[Chord]:
    """Return the chords related to a scale.

    Seven-note scales are harmonized by stacking thirds on each degree (the
    classic diatonic triads / seventh chords). Other scales return the standard
    chords whose notes fit entirely within the scale.
    """
    pcs = scale_pitch_classes(root, scale_name)
    n = len(pcs)
    if n < 3:
        return []
    if n == 7:
        return _harmonize_by_thirds(pcs, sevenths)
    return _match_chords(pcs)
