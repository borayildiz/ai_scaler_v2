"""Audio: equal-temperament frequencies and simple tone synthesis.

Notes are synthesized with numpy (a few harmonics plus a plucked-style
amplitude envelope) and played back through sounddevice. If the audio backend
is unavailable the module degrades gracefully: playback becomes a no-op and
``available()`` reports False, so the GUI can keep working silently.
"""

from __future__ import annotations

import threading
from typing import Optional, Sequence

import numpy as np

from . import theory

SAMPLE_RATE = 44_100
A4_FREQ = 440.0
A4_MIDI = 69

_sd = None            # lazily imported sounddevice module
_audio_error: Optional[str] = None


def _get_sd():
    """Import sounddevice lazily; cache failure so we only try once."""
    global _sd, _audio_error
    if _sd is not None or _audio_error is not None:
        return _sd
    try:
        import sounddevice as sd  # type: ignore

        _sd = sd
    except Exception as exc:  # pragma: no cover - depends on environment
        _audio_error = f"Audio unavailable: {exc}"
    return _sd


def available() -> bool:
    """Return True if audio playback is usable."""
    return _get_sd() is not None


def audio_error() -> Optional[str]:
    """Return the reason audio is unavailable, if any."""
    _get_sd()
    return _audio_error


def midi_to_freq(midi: int) -> float:
    """Convert a MIDI note number to a frequency in Hz (A4 = 440)."""
    return A4_FREQ * (2.0 ** ((midi - A4_MIDI) / 12.0))


def note_to_freq(note: str, octave: int = 4) -> float:
    """Convert a note name + octave to a frequency in Hz.

    Octaves follow the scientific pitch convention where C4 is middle C, so
    MIDI = (octave + 1) * 12 + pitch_class.
    """
    midi = (octave + 1) * 12 + theory.note_index(note)
    return midi_to_freq(midi)


def _tone(freq: float, duration: float, amplitude: float = 0.5) -> np.ndarray:
    """Generate a single plucked-style tone as a float32 mono waveform."""
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0.0, duration, n, endpoint=False)

    # A few harmonics give the tone a little body without sounding harsh.
    wave = (
        1.00 * np.sin(2 * np.pi * freq * t)
        + 0.35 * np.sin(2 * np.pi * 2 * freq * t)
        + 0.15 * np.sin(2 * np.pi * 3 * freq * t)
    )

    # Plucked-style envelope: fast attack, exponential-ish decay.
    attack = max(1, int(0.005 * SAMPLE_RATE))
    env = np.ones(n)
    env[:attack] = np.linspace(0.0, 1.0, attack)
    decay = np.linspace(1.0, 0.0, n) ** 1.6
    env *= decay

    return (amplitude * wave * env).astype(np.float32)


def _mix(waveforms: Sequence[np.ndarray]) -> np.ndarray:
    """Sum waveforms of possibly different lengths into one buffer."""
    if not waveforms:
        return np.zeros(0, dtype=np.float32)
    length = max(len(w) for w in waveforms)
    buffer = np.zeros(length, dtype=np.float32)
    for w in waveforms:
        buffer[: len(w)] += w
    # Guard against clipping when many notes overlap.
    peak = np.max(np.abs(buffer)) if buffer.size else 0.0
    if peak > 1.0:
        buffer /= peak
    return buffer


def _play_buffer(buffer: np.ndarray) -> None:
    sd = _get_sd()
    if sd is None or buffer.size == 0:
        return

    def worker():
        try:
            sd.play(buffer, SAMPLE_RATE)
        except Exception:  # pragma: no cover - device hiccups shouldn't crash UI
            pass

    threading.Thread(target=worker, daemon=True).start()


def play_note(midi: int, duration: float = 0.7) -> None:
    """Play a single note (by MIDI number), non-blocking."""
    _play_buffer(_tone(midi_to_freq(midi), duration))


def play_chord(midis: Sequence[int], duration: float = 1.1) -> None:
    """Play several notes simultaneously, non-blocking."""
    amp = 0.5 / max(1, len(midis)) ** 0.5
    waves = [_tone(midi_to_freq(m), duration, amplitude=amp) for m in midis]
    _play_buffer(_mix(waves))


def play_sequence(
    midis: Sequence[int],
    note_duration: float = 0.45,
    gap: float = 0.28,
) -> None:
    """Play notes one after another (as one pre-mixed, non-blocking buffer)."""
    offset_samples = int(gap * SAMPLE_RATE)
    total = offset_samples * max(0, len(midis) - 1) + int(note_duration * SAMPLE_RATE)
    buffer = np.zeros(total, dtype=np.float32)
    for i, m in enumerate(midis):
        tone = _tone(midi_to_freq(m), note_duration, amplitude=0.5)
        start = i * offset_samples
        buffer[start : start + len(tone)] += tone
    peak = np.max(np.abs(buffer)) if buffer.size else 0.0
    if peak > 1.0:
        buffer /= peak
    _play_buffer(buffer)
