#!/usr/bin/env python3
"""Build a ~10 minute explainer video for the ai_scaler guitar app."""

from __future__ import annotations

import math
import os
import subprocess
import sys
import wave
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_scaler import audio, theory  # noqa: E402
from ai_scaler.fretboard import DEFAULT_TUNING, Fretboard  # noqa: E402

W, H = 1920, 1080
BUILD = Path(__file__).resolve().parent / "_build"
FINAL = Path(__file__).resolve().parent / "ai_scaler_explainer.mp4"

BG = (30, 34, 48)
PANEL_BG = (38, 43, 61)
BOARD_BG = (58, 44, 34)
FRET_COLOR = (201, 201, 201)
NUT_COLOR = (242, 242, 242)
STRING_COLOR = (216, 216, 216)
INLAY_COLOR = (90, 70, 54)
SCALE_COLOR = (61, 127, 214)
ROOT_COLOR = (232, 84, 63)
NOTE_TEXT = (255, 255, 255)
LABEL_FG = (232, 232, 232)
MUTED_FG = (154, 163, 184)
CHORD_BG = (255, 255, 255)
WHITE = (255, 255, 255)
ACCENT = (61, 127, 214)

INLAY_FRETS = {3, 5, 7, 9, 15, 17, 19, 21}
DOUBLE_INLAY_FRETS = {12, 24}

SAY_VOICE = "Samantha"
SAY_RATE = 154  # words/min — speech plus pauses/music lands near 10:00


def hex_to_rgb(h: str) -> Tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def load_font(size: int, mono: bool = False, bold: bool = False) -> ImageFont.FreeTypeFont:
    if mono:
        candidates = [
            ("/System/Library/Fonts/Supplemental/Courier New.ttf", 0),
            ("/System/Library/Fonts/Menlo.ttc", 0),
            ("/Library/Fonts/Courier New.ttf", 0),
        ]
    elif bold:
        candidates = [
            ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 0),
            ("/Library/Fonts/Arial Bold.ttf", 0),
            ("/System/Library/Fonts/Supplemental/Arial.ttf", 0),
            ("/System/Library/Fonts/Helvetica.ttc", 1),
        ]
    else:
        candidates = [
            ("/System/Library/Fonts/Supplemental/Arial.ttf", 0),
            ("/Library/Fonts/Arial.ttf", 0),
            ("/System/Library/Fonts/Helvetica.ttc", 0),
            ("/System/Library/Fonts/Supplemental/Georgia.ttf", 0),
        ]
    for path, index in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size, index=index)
            except OSError:
                continue
    return ImageFont.load_default()


def text_size(draw: ImageDraw.ImageDraw, text: str, font) -> Tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0], box[3] - box[1]


def rounded(draw: ImageDraw.ImageDraw, xy, radius: int, fill, outline=None, width: int = 1):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def draw_legend(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    font = load_font(18)
    r = 11
    draw.ellipse((x, y, x + 2 * r, y + 2 * r), fill=ROOT_COLOR, outline=WHITE, width=2)
    draw.text((x + 2 * r + 8, y + 2), "Root", fill=LABEL_FG, font=font)
    x2 = x + 110
    draw.ellipse((x2, y, x2 + 2 * r, y + 2 * r), fill=SCALE_COLOR, outline=(27, 58, 99), width=2)
    draw.text((x2 + 2 * r + 8, y + 2), "Scale tone", fill=LABEL_FG, font=font)


def render_title(title: str, subtitle: str, footer: str = "") -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    # Decorative nut + strings
    for i, thick in enumerate((6, 5, 4, 3, 2, 2)):
        y = 220 + i * 28
        draw.line((160, y, 1760, y), fill=STRING_COLOR, width=thick)
    draw.rectangle((240, 200, 252, 400), fill=NUT_COLOR)
    for cx in (520, 780, 1040, 1300):
        draw.ellipse((cx - 7, 292, cx + 7, 306), fill=INLAY_COLOR)

    title_font = load_font(92, bold=True)
    sub_font = load_font(36)
    foot_font = load_font(26)
    tw, th = text_size(draw, title, title_font)
    draw.text(((W - tw) / 2, 470), title, fill=WHITE, font=title_font)
    sw, sh = text_size(draw, subtitle, sub_font)
    draw.text(((W - sw) / 2, 470 + th + 24), subtitle, fill=ACCENT, font=sub_font)
    if footer:
        fw, _ = text_size(draw, footer, foot_font)
        draw.text(((W - fw) / 2, 920), footer, fill=MUTED_FG, font=foot_font)
    # Accent dots
    draw.ellipse((900, 820, 934, 854), fill=ROOT_COLOR, outline=WHITE, width=2)
    draw.ellipse((980, 820, 1014, 854), fill=SCALE_COLOR, outline=(27, 58, 99), width=2)
    return img


def render_end_card() -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    title_font = load_font(84, bold=True)
    body = load_font(34)
    small = load_font(26)
    lines = [
        (title_font, WHITE, "ai_scaler"),
        (body, ACCENT, "See the scale. Hear the scale. Play it."),
        (small, MUTED_FG, "python main.py"),
        (small, MUTED_FG, "Root  ·  Scale  ·  Fretboard  ·  Chords  ·  Sound"),
    ]
    y = 360
    for font, color, text in lines:
        tw, th = text_size(draw, text, font)
        draw.text(((W - tw) / 2, y), text, fill=color, font=font)
        y += th + 36
    return img


def render_app_frame(
    root: str,
    scale: str,
    tuning: str = DEFAULT_TUNING,
    caption: str = "",
    highlight: Optional[str] = None,
    chapter: str = "",
) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    top_h = 86
    status_h = 42
    caption_h = 70 if caption else 0
    board_top = top_h
    board_bottom = H - status_h - caption_h
    panel_w = 400
    panel_x = W - panel_w - 28

    # --- top bar ---
    draw.rectangle((0, 0, W, top_h), fill=PANEL_BG)
    ui = load_font(22)
    ui_b = load_font(22, bold=True)
    small = load_font(18)

    def combo(x, label, value, width):
        draw.text((x, 30), label, fill=LABEL_FG, font=small)
        lx = x + text_size(draw, label, small)[0] + 12
        rounded(draw, (lx, 22, lx + width, 64), 8, fill=(24, 28, 42), outline=(90, 98, 120), width=1)
        draw.text((lx + 12, 32), value, fill=WHITE, font=ui)
        return lx + width + 28

    x = 36
    x = combo(x, "Root", root, 90)
    x = combo(x, "Scale", scale, 340)
    x = combo(x, "Tuning", tuning.split(" (")[0], 220)

    # Play scale button
    bx1, by1, bx2, by2 = x + 8, 20, x + 188, 66
    play_fill = (90, 160, 240) if highlight == "play" else SCALE_COLOR
    rounded(draw, (bx1, by1, bx2, by2), 8, fill=play_fill)
    pw, ph = text_size(draw, "Play scale", ui_b)
    draw.text((bx1 + (bx2 - bx1 - pw) / 2, by1 + (by2 - by1 - ph) / 2 - 2),
              "Play scale", fill=WHITE, font=ui_b)
    if highlight == "play":
        rounded(draw, (bx1 - 6, by1 - 6, bx2 + 6, by2 + 6), 12, fill=None,
                outline=(255, 214, 102), width=3)

    if chapter:
        cw, _ = text_size(draw, chapter, small)
        draw.text((W - cw - 36, 32), chapter, fill=MUTED_FG, font=small)

    # --- fretboard canvas ---
    canvas_x0, canvas_y0 = 24, board_top + 16
    canvas_x1, canvas_y1 = panel_x - 20, board_bottom - 16
    draw.rectangle((canvas_x0, canvas_y0, canvas_x1, canvas_y1), fill=BG)

    fb = Fretboard(tuning, 15)
    grid = fb.scale_positions(root, scale)
    num_strings = fb.num_strings
    num_frets = 15

    margin_left = 100
    margin_right = 36
    margin_top = 48
    margin_bottom = 36
    origin_x = canvas_x0 + margin_left
    origin_y = canvas_y0 + margin_top
    board_w = (canvas_x1 - canvas_x0) - margin_left - margin_right
    board_h = (canvas_y1 - canvas_y0) - margin_top - margin_bottom
    fret_w = board_w / (num_frets + 1)
    string_gap = board_h / (num_strings - 1)
    nut_x = origin_x + fret_w
    radius = max(12, min(22, min(fret_w, string_gap) * 0.36))

    def string_y(display_row: int) -> float:
        return origin_y + display_row * string_gap

    def fret_center_x(fret: int) -> float:
        if fret == 0:
            return origin_x + fret_w * 0.5
        return nut_x + (fret - 0.5) * fret_w

    board_top_y = string_y(0)
    board_bot_y = string_y(num_strings - 1)
    board_mid = (board_top_y + board_bot_y) / 2

    # inlays
    for fret in range(1, num_frets + 1):
        cx = fret_center_x(fret)
        if fret in DOUBLE_INLAY_FRETS:
            for yy in (board_top_y + string_gap, board_bot_y - string_gap):
                draw.ellipse((cx - 6, yy - 6, cx + 6, yy + 6), fill=INLAY_COLOR)
        elif fret in INLAY_FRETS:
            draw.ellipse((cx - 6, board_mid - 6, cx + 6, board_mid + 6), fill=INLAY_COLOR)

    draw.rectangle((nut_x, board_top_y, nut_x + num_frets * fret_w, board_bot_y), fill=BOARD_BG)

    for fret in range(0, num_frets + 1):
        xline = nut_x + fret * fret_w
        color = NUT_COLOR if fret == 0 else FRET_COLOR
        width = 6 if fret == 0 else 2
        draw.line((xline, board_top_y, xline, board_bot_y), fill=color, width=width)

    fret_font = load_font(16)
    for fret in range(1, num_frets + 1):
        t = str(fret)
        tw, _ = text_size(draw, t, fret_font)
        draw.text((fret_center_x(fret) - tw / 2, canvas_y0 + 14), t, fill=MUTED_FG, font=fret_font)
    tw, _ = text_size(draw, "open", fret_font)
    draw.text((fret_center_x(0) - tw / 2, canvas_y0 + 14), "open", fill=MUTED_FG, font=fret_font)

    label_font = load_font(22, bold=True)
    note_font = load_font(int(radius * 0.95), bold=True)
    for display_row in range(num_strings):
        s = num_strings - 1 - display_row
        y = string_y(display_row)
        thickness = 1 + int((num_strings - 1 - s) * 0.7)
        draw.line((nut_x, y, nut_x + num_frets * fret_w, y), fill=STRING_COLOR, width=max(2, thickness))
        open_note = fb.note_at(s, 0)
        tw, th = text_size(draw, open_note, label_font)
        draw.text((origin_x - 50 - tw / 2, y - th / 2), open_note, fill=LABEL_FG, font=label_font)

    for display_row in range(num_strings):
        s = num_strings - 1 - display_row
        y = string_y(display_row)
        for pos in grid[s]:
            if not pos.in_scale:
                continue
            cx = fret_center_x(pos.fret)
            fill = ROOT_COLOR if pos.is_root else SCALE_COLOR
            outline = WHITE if pos.is_root else (27, 58, 99)
            draw.ellipse((cx - radius, y - radius, cx + radius, y + radius),
                         fill=fill, outline=outline, width=3)
            tw, th = text_size(draw, pos.note, note_font)
            draw.text((cx - tw / 2, y - th / 2 - 1), pos.note, fill=NOTE_TEXT, font=note_font)

    draw_legend(draw, int(canvas_x0 + 24), int(canvas_y1 - 40))

    # --- right panel ---
    py0, py1 = board_top + 16, board_bottom - 16
    draw.rectangle((panel_x, py0, panel_x + panel_w, py1), fill=PANEL_BG)
    if highlight == "notes":
        rounded(draw, (panel_x + 6, py0 + 6, panel_x + panel_w - 6, py0 + 150), 10,
                fill=None, outline=(255, 214, 102), width=3)
    if highlight == "chords":
        rounded(draw, (panel_x + 6, py0 + 150, panel_x + panel_w - 6, py1 - 6), 10,
                fill=None, outline=(255, 214, 102), width=3)

    head = load_font(24, bold=True)
    notes_font = load_font(26)
    muted = load_font(16)
    draw.text((panel_x + 22, py0 + 18), "Scale notes", fill=LABEL_FG, font=head)
    notes = theory.scale_notes(root, scale)
    display = "  ".join(f"[{n}]" if i == 0 else n for i, n in enumerate(notes))
    # wrap notes
    max_w = panel_w - 44
    words = display.split("  ")
    line, ly = "", py0 + 56
    for w_ in words:
        trial = (line + "  " + w_).strip()
        if text_size(draw, trial, notes_font)[0] <= max_w:
            line = trial
        else:
            draw.text((panel_x + 22, ly), line, fill=SCALE_COLOR, font=notes_font)
            ly += 34
            line = w_
    if line:
        draw.text((panel_x + 22, ly), line, fill=SCALE_COLOR, font=notes_font)

    draw.text((panel_x + 22, py0 + 160), "Related chords", fill=LABEL_FG, font=head)
    draw.text((panel_x + 22, py0 + 192), "(click a chord to hear it)", fill=MUTED_FG, font=muted)

    card_x0 = panel_x + 16
    card_y0 = py0 + 220
    card_x1 = panel_x + panel_w - 16
    card_y1 = py1 - 16
    draw.rectangle((card_x0, card_y0, card_x1, card_y1), fill=CHORD_BG)

    mono = load_font(18, mono=True)
    chords = theory.related_chords(root, scale)
    row_h = 34
    max_rows = max(1, int((card_y1 - card_y0 - 16) / row_h))
    for i, chord in enumerate(chords[:max_rows]):
        yy = card_y0 + 10 + i * row_h
        text = f"{chord.name:<8}  {' '.join(chord.notes)}"
        rounded(draw, (card_x0 + 8, yy, card_x1 - 8, yy + 28), 4,
                fill=(255, 255, 255), outline=(200, 200, 200), width=1)
        draw.text((card_x0 + 16, yy + 5), text, fill=(0, 0, 0), font=mono)

    # --- status ---
    status_y = H - status_h - caption_h
    draw.rectangle((0, status_y, W, status_y + status_h), fill=PANEL_BG)
    draw.text((24, status_y + 10), "Ready. Click a note or chord to play.",
              fill=MUTED_FG, font=load_font(18))

    if caption:
        draw.rectangle((0, H - caption_h, W, H), fill=(18, 21, 32))
        cap_font = load_font(28, bold=True)
        tw, th = text_size(draw, caption, cap_font)
        draw.text(((W - tw) / 2, H - caption_h + (caption_h - th) / 2 - 2),
                  caption, fill=WHITE, font=cap_font)
    return img


def render_bullets(title: str, bullets: Sequence[str], footer: str = "") -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    title_font = load_font(56, bold=True)
    body = load_font(32)
    draw.text((140, 120), title, fill=WHITE, font=title_font)
    y = 240
    for b in bullets:
        draw.ellipse((150, y + 14, 168, y + 32), fill=ACCENT)
        # wrap
        words = b.split()
        line = ""
        x = 200
        max_w = 1600
        for w_ in words:
            trial = (line + " " + w_).strip()
            if text_size(draw, trial, body)[0] <= max_w:
                line = trial
            else:
                draw.text((x, y), line, fill=LABEL_FG, font=body)
                y += 46
                line = w_
        draw.text((x, y), line, fill=LABEL_FG, font=body)
        y += 70
    if footer:
        draw.text((140, 960), footer, fill=MUTED_FG, font=load_font(24))
    return img


# ---------------------------------------------------------------------------
# Audio helpers
# ---------------------------------------------------------------------------

def write_wav(path: Path, samples: np.ndarray, sr: int = audio.SAMPLE_RATE) -> None:
    samples = np.clip(samples, -1.0, 1.0)
    pcm = (samples * 32767).astype(np.int16)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())


def read_wav(path: Path) -> Tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as wf:
        sr = wf.getframerate()
        n = wf.getnframes()
        raw = wf.readframes(n)
        ch = wf.getnchannels()
        sampwidth = wf.getsampwidth()
    if sampwidth == 2:
        data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    else:
        raise RuntimeError(f"Unsupported sample width {sampwidth} in {path}")
    if ch > 1:
        data = data.reshape(-1, ch).mean(axis=1)
    return data, sr


def silence(seconds: float, sr: int = audio.SAMPLE_RATE) -> np.ndarray:
    return np.zeros(int(seconds * sr), dtype=np.float32)


def concat_audio(chunks: Sequence[np.ndarray]) -> np.ndarray:
    if not chunks:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(list(chunks))


def render_scale_tone(root: str, scale_name: str) -> np.ndarray:
    root_midi = 48 + theory.note_index(root)
    midis = [root_midi + step for step in theory.SCALES[scale_name]]
    midis.append(root_midi + 12)
    note_duration, gap = 0.42, 0.32
    offset = int(gap * audio.SAMPLE_RATE)
    total = offset * (len(midis) - 1) + int(note_duration * audio.SAMPLE_RATE)
    buf = np.zeros(total, dtype=np.float32)
    for i, m in enumerate(midis):
        tone = audio._tone(audio.midi_to_freq(m), note_duration, amplitude=0.55)
        start = i * offset
        buf[start : start + len(tone)] += tone
    peak = np.max(np.abs(buf)) if buf.size else 0.0
    if peak > 1.0:
        buf /= peak
    return buf


def render_chord_tone(note_names: Sequence[str]) -> np.ndarray:
    base, prev = 48, -1
    midis = []
    for name in note_names:
        m = base + theory.note_index(name)
        while m <= prev:
            m += 12
        midis.append(m)
        prev = m
    amp = 0.5 / max(1, len(midis)) ** 0.5
    waves = [audio._tone(audio.midi_to_freq(m), 1.4, amplitude=amp) for m in midis]
    length = max(len(w) for w in waves)
    buf = np.zeros(length, dtype=np.float32)
    for w in waves:
        buf[: len(w)] += w
    peak = np.max(np.abs(buf)) if buf.size else 0.0
    if peak > 1.0:
        buf /= peak
    return buf


def say_to_wav(text: str, dest: Path) -> np.ndarray:
    """Speak `text` with macOS say and return 44100 Hz float32 audio."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    aiff = dest.with_suffix(".aiff")
    txt = dest.with_suffix(".txt")
    txt.write_text(text, encoding="utf-8")
    subprocess.check_call(
        ["say", "-v", SAY_VOICE, "-r", str(SAY_RATE), "-f", str(txt), "-o", str(aiff)]
    )
    wav = dest.with_suffix(".wav")
    subprocess.check_call(
        ["afconvert", "-f", "WAVE", "-d", "LEI16@44100", str(aiff), str(wav)]
    )
    data, sr = read_wav(wav)
    if sr != audio.SAMPLE_RATE:
        # Linear resample if afconvert used a different rate.
        n_out = int(len(data) * audio.SAMPLE_RATE / sr)
        x_old = np.linspace(0, 1, len(data), endpoint=False)
        x_new = np.linspace(0, 1, n_out, endpoint=False)
        data = np.interp(x_new, x_old, data).astype(np.float32)
    return data


# ---------------------------------------------------------------------------
# Script
# ---------------------------------------------------------------------------

def scenes() -> List[dict]:
    """Visual + narration beats. Speech is written for spoken English (no '#')."""
    return [
        {
            "id": "01_title",
            "kind": "title",
            "title": "ai_scaler",
            "subtitle": "Guitar Scale & Chord Visualizer",
            "footer": "A ten-minute tour of the app",
            "speech": (
                "Welcome to A.I. scaler — a desktop guitar companion that shows you any scale "
                "on a real fretboard, lists the notes, finds the related chords, and lets you "
                "hear everything. In the next ten minutes we will walk through the whole app: "
                "how to pick a root and a scale, how to read the board, how playback works, "
                "and how tunings and exotic scales fit in. You do not need to be a theory "
                "expert. If you can find the low E string, you can use this."
            ),
        },
        {
            "id": "02_promise",
            "kind": "bullets",
            "title": "What the app gives you",
            "bullets": [
                "Every in-scale note, marked on a 15-fret guitar neck",
                "The root painted red, so you never lose home base",
                "A spelled-out note list plus related, clickable chords",
                "Sound: click a note, a chord, or play the whole scale",
            ],
            "speech": (
                "Think of it as a flashlight for the neck of the guitar. Choose a key and a "
                "scale, and every matching note lights up. The root is painted a different "
                "color so you never lose home base. Click a dot to hear that pitch, click a "
                "chord to hear a voicing, or press Play scale to hear the whole thing "
                "ascending. Visuals always work, even if sound cannot start on your machine."
            ),
        },
        {
            "id": "03_overview",
            "kind": "app",
            "root": "C",
            "scale": "Major (Ionian)",
            "caption": "The main window — C major, standard tuning",
            "chapter": "1  ·  Layout",
            "speech": (
                "This is the main window. Across the top you pick the root note, the scale, "
                "and the tuning. On the left is a fifteen-fret guitar neck. On the right, a "
                "panel lists the scale tones and the related chords. Along the bottom, a "
                "status line tells you the app is ready — or warns you if audio could not "
                "start. Nothing is hidden in extra screens. One window is the whole tool."
            ),
        },
        {
            "id": "04_controls",
            "kind": "app",
            "root": "C",
            "scale": "Major (Ionian)",
            "caption": "Root, scale, and tuning menus — change any of them and the board redraws",
            "chapter": "1  ·  Layout",
            "speech": (
                "Start with the three menus. Root is the tonic — C, G, E, B flat, whatever "
                "you need. Scale is a long list: major, the three common minors, the church "
                "modes, pentatonics, blues, and a set of exotic scales. Tuning defaults to "
                "standard E A D G B E, and you can switch to drop D, half step down, open G, "
                "or dad-gad. Changing any menu redraws the board immediately."
            ),
        },
        {
            "id": "05_fretboard",
            "kind": "app",
            "root": "C",
            "scale": "Major (Ionian)",
            "caption": "High E at the top, low E at the bottom — open strings sit left of the nut",
            "chapter": "2  ·  Fretboard",
            "speech": (
                "The neck is drawn the way most players picture it: the high E string at the "
                "top of the screen, the low E at the bottom. Open strings sit to the left of "
                "the nut, labeled with their pitch. Fret numbers run along the top. Inlay "
                "dots mark frets three, five, seven, nine, twelve, and fifteen — the same "
                "landmarks you feel on a real guitar. Only notes that belong to the current "
                "scale appear as dots. Empty wood means: do not land there, for this scale."
            ),
        },
        {
            "id": "06_colors",
            "kind": "app",
            "root": "C",
            "scale": "Major (Ionian)",
            "caption": "Red is the root  ·  Blue is every other scale tone",
            "chapter": "2  ·  Fretboard",
            "speech": (
                "Color is doing real work here. Blue dots are scale tones. Red dots are the "
                "root. That split sounds small, but on a crowded neck it is how you keep your "
                "place. In C major, every C on the board is red, and the rest of the major "
                "scale is blue. If you change the root to A, the red jumps to every A — the "
                "map rotates, the guitar does not. Look for red first, then walk the blues "
                "around it."
            ),
        },
        {
            "id": "07_play",
            "kind": "app",
            "root": "C",
            "scale": "Major (Ionian)",
            "highlight": "play",
            "caption": "Play scale walks from the root up to the octave",
            "chapter": "3  ·  Sound",
            "music": ("scale", "C", "Major (Ionian)"),
            "speech": (
                "Now the fun part: sound. Click any lit note and a synthesized plucked tone "
                "plays that pitch. The synthesizer uses a few harmonics and a fast decay, so "
                "it feels more like a string than a beep. The Play scale button, highlighted "
                "here, walks the scale from the root up to the octave. Listen to C major."
            ),
        },
        {
            "id": "08_a_minor",
            "kind": "app",
            "root": "A",
            "scale": "Natural Minor (Aeolian)",
            "caption": "Same guitar, new map — A natural minor",
            "chapter": "3  ·  Sound",
            "speech": (
                "Change the root to A and the scale to natural minor, and the board becomes "
                "the A minor pattern you already know if you play rock or folk. Same guitar, "
                "different map. That is the whole idea: stop memorizing isolated shapes in "
                "isolation, and start seeing one scale everywhere it lives on the neck. Click "
                "through a few roots and watch the red tonic leap from string to string."
            ),
        },
        {
            "id": "09_notes",
            "kind": "app",
            "root": "C",
            "scale": "Major (Ionian)",
            "highlight": "notes",
            "caption": "Scale notes — the linear spelling of what the neck is showing",
            "chapter": "4  ·  Notes",
            "speech": (
                "The right-hand panel spells the scale as text, with the root in brackets. "
                "For C major you see C, D, E, F, G, A, and B. That list is the same "
                "information as the dots, just linear. It is handy when you want to sing the "
                "scale, check a spelling, or confirm a sharp, without hunting across strings. "
                "When you switch scales, this list updates with the board."
            ),
        },
        {
            "id": "10_chords",
            "kind": "app",
            "root": "C",
            "scale": "Major (Ionian)",
            "highlight": "chords",
            "caption": "Related chords — C major harmonized in sevenths",
            "chapter": "5  ·  Chords",
            "music": ("chord", "C", "E", "G", "B"),
            "speech": (
                "Under the notes, Related chords shows what you get when you harmonize the "
                "scale. For a seven-note scale, the app stacks thirds on each degree — the "
                "classic diatonic seventh chords. C major gives you C major seven, D minor "
                "seven, E minor seven, F major seven, G seven, A minor seven, and B minor "
                "seven flat five. Click any row to hear that chord voiced. Here is C major seven."
            ),
        },
        {
            "id": "11_pent_chords",
            "kind": "app",
            "root": "A",
            "scale": "Minor Pentatonic",
            "highlight": "chords",
            "caption": "Non-seven-note scales: richest chords that still fit the notes",
            "chapter": "5  ·  Chords",
            "speech": (
                "Pentatonics, blues, and symmetrical scales do not stack into neat seventh "
                "chords the same way. For those, the app searches for standard chord formulas "
                "whose notes all live inside the scale, and keeps the richest match on each "
                "root. So a minor pentatonic still shows useful guitar chords, instead of a "
                "blank panel. Theory stays practical: if you can play it on the guitar, it "
                "is worth listing."
            ),
        },
        {
            "id": "12_dorian",
            "kind": "app",
            "root": "A",
            "scale": "Dorian",
            "caption": "A Dorian — minor with a raised sixth",
            "chapter": "6  ·  Modes",
            "speech": (
                "The church modes are all here: Dorian, Phrygian, Lydian, Mixolydian, Locrian, "
                "plus Ionian and Aeolian under their everyday names, major and natural minor. "
                "Dorian is the minor scale with a raised sixth — a favorite for jazz, funk, "
                "and modal rock. Compare A Dorian with A natural minor and you will see one "
                "dot shift: F becomes F sharp. That single color change is the Dorian sound."
            ),
        },
        {
            "id": "12b_harmonic",
            "kind": "app",
            "root": "A",
            "scale": "Harmonic Minor",
            "caption": "A harmonic minor — the raised seventh that makes E seven possible",
            "chapter": "6  ·  Modes",
            "speech": (
                "Harmonic and melodic minor sit right under natural minor in the menu, and "
                "they are worth a look because so many guitar parts use them. Harmonic minor "
                "raises the seventh: in A, G becomes G sharp. That one extra red-adjacent "
                "dot is what lets you play an E seven chord in an A minor song, and it is "
                "the exotic-sounding leap you hear in classical and metal. Melodic minor "
                "also raises the sixth, smoothing the climb to the octave. Flip between the "
                "three minors on the same root and watch a single dot or two jump. That is "
                "ear training with your eyes."
            ),
        },
        {
            "id": "13_mixolydian",
            "kind": "app",
            "root": "G",
            "scale": "Mixolydian",
            "caption": "G Mixolydian — the sound of G seven, stretched across the neck",
            "chapter": "6  ·  Modes",
            "speech": (
                "Mixolydian is major with a flat seventh, which is the sound of dominant "
                "chords and a lot of rock riffs. Pick G Mixolydian and you are looking at "
                "the notes of a G seven chord, stretched across the neck. Lydian raises the "
                "fourth of major — bright and filmic. Phrygian flattens the second of minor "
                "— darker, Spanish, heavy. Locrian is the tense half-diminished mode, with a "
                "flat second and a flat fifth."
            ),
        },
        {
            "id": "14_blues",
            "kind": "app",
            "root": "E",
            "scale": "Blues",
            "caption": "E blues — minor pentatonic plus the blue note, B flat",
            "chapter": "6  ·  Modes",
            "music": ("scale", "E", "Blues"),
            "speech": (
                "Major and minor pentatonic cut the scale to five notes — the shapes most "
                "guitarists learn first. Blues adds the flat five, the blue note, between "
                "the four and the five of minor pentatonic. In E blues that extra tension "
                "is B flat, sitting between A and B. That is why a blues box feels different "
                "from a pentatonic box, even though they share so many dots. Listen to E blues."
            ),
        },
        {
            "id": "15_whole_dim",
            "kind": "app",
            "root": "C",
            "scale": "Whole Tone",
            "caption": "C whole tone — six equal steps, no single tonic gravity",
            "chapter": "7  ·  Exotic",
            "speech": (
                "The exotic list is where the app becomes a playground. Whole tone divides "
                "the octave into six equal steps — dreamy, unrooted, a classic film and "
                "impressionist color. The two diminished scales, half-whole and whole-half, "
                "are eight-note symmetric scales used in jazz for dominant chords and "
                "diminished harmony. Watch how regular the dots look. Symmetry on the neck "
                "is a clue that the scale repeats every minor third or every whole step."
            ),
        },
        {
            "id": "16_phrygian_dom",
            "kind": "app",
            "root": "E",
            "scale": "Phrygian Dominant",
            "caption": "E Phrygian dominant — flamenco, metal, and harmonic-minor color",
            "chapter": "7  ·  Exotic",
            "speech": (
                "Phrygian dominant is the fifth mode of harmonic minor: a flat second and a "
                "major third. It is the sound of flamenco, metal, and a lot of Middle "
                "Eastern-influenced riffs. Hungarian minor raises the fourth of harmonic "
                "minor, which gives an extra pull toward the fifth. Double harmonic, also "
                "called Byzantine, has two augmented seconds and a very vocal, ancient "
                "quality. Select any of them and the red tonic still tells you where home is."
            ),
        },
        {
            "id": "17_hirajoshi",
            "kind": "app",
            "root": "C",
            "scale": "Japanese Hirajoshi",
            "caption": "C Hirajoshi — a five-note Japanese scale on the same guitar",
            "chapter": "7  ·  Exotic",
            "speech": (
                "Japanese Hirajoshi and In Sen are five-note scales with a distinctly East "
                "Asian contour — great for melody that does not sound like a Western minor "
                "box. Prometheus is a six-note scale associated with Scriabin. Augmented, "
                "Neapolitan major and minor, and the Enigmatic scale round out the set. You "
                "do not have to know their history. Select one, and the neck shows you where "
                "to put your fingers. That is the point of a visualizer."
            ),
        },
        {
            "id": "18_drop_d",
            "kind": "app",
            "root": "D",
            "scale": "Minor Pentatonic",
            "tuning": "Drop D (D A D G B E)",
            "caption": "Drop D — the sixth string drops to D; open labels and dots all move",
            "chapter": "8  ·  Tunings",
            "speech": (
                "Five tunings ship with the app. Standard is E A D G B E. Drop D lowers the "
                "sixth string a whole step, so power chords sit on one finger. Here is D "
                "minor pentatonic in drop D — notice the open sixth string is now D, and "
                "it is red, because D is the root. Half step down is the classic E flat "
                "tuning, used by a lot of rock singers to ease the vocal range."
            ),
        },
        {
            "id": "19_dadgad",
            "kind": "app",
            "root": "D",
            "scale": "Mixolydian",
            "tuning": "DADGAD",
            "caption": "DADGAD — D Mixolydian over a folk drone",
            "chapter": "8  ·  Tunings",
            "speech": (
                "Open G is D G D G B D — a slide and Stones tuning, where a barred G chord "
                "falls naturally. Dad-gad is the folk and Celtic tuning: D A D G A D, with "
                "big suspended drones. Pair it with D Mixolydian and the open strings ring "
                "inside the scale. Switch tunings and the open-string labels and every dot "
                "recalculate. The theory engine does not assume standard tuning. The guitar "
                "on screen is the guitar in your hands."
            ),
        },
        {
            "id": "19b_practice",
            "kind": "bullets",
            "title": "A five-minute practice loop",
            "bullets": [
                "Set Root to the key of a song you already play",
                "Choose the scale the melody actually uses",
                "Find every red root, then connect nearby blue notes",
                "Click related chords and strum those shapes on the guitar",
                "Repeat tomorrow with a mode, an exotic scale, or a new tuning",
            ],
            "speech": (
                "Here is a simple way to use the app in a real practice session. Open a song "
                "you already play. Set the root to that key. Choose the scale the melody "
                "actually uses — minor pentatonic for a blues, Mixolydian for a dominant "
                "vamp, Dorian for a funk groove. Find every red root on the neck, then "
                "connect the nearest blue notes with short phrases. Click the related chords "
                "and strum them on the guitar, matching what you hear. Tomorrow, change one "
                "thing: a mode, an exotic color, or a different tuning. Small daily maps beat "
                "memorizing twenty box shapes you never use."
            ),
        },
        {
            "id": "20_recap",
            "kind": "bullets",
            "title": "How to use it, in one pass",
            "bullets": [
                "Pick a root and a scale — red is home, blue is the rest",
                "Read the neck, then confirm the spelling in Scale notes",
                "Click notes, click chords, or press Play scale",
                "Try a mode, an exotic scale, or a new tuning",
                "Run it with:  python main.py",
            ],
            "speech": (
                "To recap: pick a root, pick a scale, read the neck. Red is the tonic, blue "
                "is the rest of the scale. Click notes or chords to hear them, or play the "
                "scale. Related chords tell you what you can strum over that map. Exotic "
                "names are just more maps. The project is a small Python app. Install the "
                "requirements, then run python main.py. If audio fails, you still get the "
                "visualizer. That is the whole tour. Now open a scale you do not know, and "
                "learn it by seeing it."
            ),
        },
        {
            "id": "21_end",
            "kind": "end",
            "speech": (
                "A.I. scaler. See the scale. Hear the scale. Play it on the guitar. "
                "Thanks for watching — now pick a scale you do not know, and put it on the neck."
            ),
        },
    ]


def render_scene(scene: dict) -> Image.Image:
    kind = scene["kind"]
    if kind == "title":
        return render_title(scene["title"], scene["subtitle"], scene.get("footer", ""))
    if kind == "end":
        return render_end_card()
    if kind == "bullets":
        return render_bullets(scene["title"], scene["bullets"])
    return render_app_frame(
        root=scene["root"],
        scale=scene["scale"],
        tuning=scene.get("tuning", DEFAULT_TUNING),
        caption=scene.get("caption", ""),
        highlight=scene.get("highlight"),
        chapter=scene.get("chapter", ""),
    )


def ffmpeg_bin() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def word_count(text: str) -> int:
    return len(text.replace("—", " ").split())


def build() -> None:
    BUILD.mkdir(parents=True, exist_ok=True)
    frames_dir = BUILD / "frames"
    audio_dir = BUILD / "audio"
    frames_dir.mkdir(exist_ok=True)
    audio_dir.mkdir(exist_ok=True)

    scs = scenes()
    total_words = sum(word_count(s["speech"]) for s in scs)
    print(f"Scenes: {len(scs)}  |  spoken words: {total_words}  |  target ~10:00 at {SAY_RATE} wpm")

    timeline: List[Tuple[Path, float]] = []
    narration_chunks: List[np.ndarray] = []

    for i, scene in enumerate(scs):
        print(f"[{i+1:02d}/{len(scs)}] {scene['id']}")
        frame_path = frames_dir / f"{scene['id']}.png"
        if not frame_path.exists():
            render_scene(scene).save(frame_path, "PNG")

        speech = say_to_wav(scene["speech"], audio_dir / f"{scene['id']}_speech")
        parts = [silence(0.20 if i else 0.45), speech, silence(0.30)]
        music = scene.get("music")
        if music:
            if music[0] == "scale":
                parts.append(render_scale_tone(music[1], music[2]))
            elif music[0] == "chord":
                parts.append(render_chord_tone(music[1:]))
            parts.append(silence(0.35))
        clip = concat_audio(parts)
        narration_chunks.append(clip)
        duration = len(clip) / audio.SAMPLE_RATE
        timeline.append((frame_path, duration))
        print(f"    {duration:6.1f}s  ({word_count(scene['speech'])} words)")

    full = concat_audio(narration_chunks)
    total_s = len(full) / audio.SAMPLE_RATE
    print(f"Total narration: {total_s/60:.2f} min ({total_s:.1f}s)")

    # Land near 10:00 without a long silent tail.
    target = 600.0
    if total_s < target - 2:
        extra = min(target - total_s, 6.0)
        full = concat_audio([full, silence(extra)])
        last_path, last_d = timeline[-1]
        timeline[-1] = (last_path, last_d + extra)
        total_s = len(full) / audio.SAMPLE_RATE
        print(f"Padded end card by {extra:.1f}s")
    elif total_s > target + 25:
        print(f"Warning: {total_s/60:.2f} min is past the 10-minute target.")

    voice_wav = BUILD / "narration.wav"
    write_wav(voice_wav, full)

    # concat demuxer list (last file repeated per ffmpeg docs)
    list_path = BUILD / "concat.txt"
    lines = []
    for path, dur in timeline:
        lines.append(f"file '{path}'")
        lines.append(f"duration {dur:.3f}")
    lines.append(f"file '{timeline[-1][0]}'")
    list_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    ff = ffmpeg_bin()
    tmp_mp4 = BUILD / "video_noaudio.mp4"
    print("Encoding video…")
    subprocess.check_call(
        [
            ff, "-y",
            "-f", "concat", "-safe", "0", "-i", str(list_path),
            "-fps_mode", "vfr",
            "-pix_fmt", "yuv420p",
            "-vf", "fps=30,scale=1920:1080:flags=lanczos",
            "-c:v", "libx264", "-tune", "stillimage", "-preset", "medium", "-crf", "18",
            str(tmp_mp4),
        ]
    )
    print("Muxing audio…")
    subprocess.check_call(
        [
            ff, "-y",
            "-i", str(tmp_mp4),
            "-i", str(voice_wav),
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            "-movflags", "+faststart",
            str(FINAL),
        ]
    )
    size_mb = FINAL.stat().st_size / (1024 * 1024)
    print(f"Wrote {FINAL}  ({size_mb:.1f} MB, {total_s/60:.2f} min)")


if __name__ == "__main__":
    build()
