# ai_scaler_v2

A Python desktop app that visualizes guitar **scales** and **exotic scales** on
an interactive fretboard and as a list of notes. It highlights the root note in
a distinct color, shows the related (harmonized) chords, and lets you **play the
notes** with synthesized audio by clicking the fretboard.

## Features

- Displays common scales (major, natural/harmonic/melodic minor, all modes,
  pentatonics, blues) and exotic scales (whole tone, diminished, Phrygian
  dominant, Hungarian minor, double harmonic / Byzantine, Neapolitan, enigmatic,
  Japanese Hirajoshi / In Sen, Prometheus, augmented).
- Interactive guitar fretboard with the scale notes marked; the **root note is
  shown in a different color**.
- Scale notes listed as text.
- Related chords derived by harmonizing the scale.
- Click any note on the fretboard (or a chord) to hear it, or use **Play scale**.

## Requirements

- Python 3.9+
- `numpy` and `sounddevice` (see `requirements.txt`)
- Tkinter (bundled with most Python installs; on some Linux distros install
  `python3-tk`)

`sounddevice` relies on PortAudio, which ships inside its wheel on macOS and
Windows. If audio cannot be initialized the app still runs; note playback is
simply disabled with a warning.

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

## Troubleshooting

- **`macOS 12 (1207) or later required, have instead 12 (1206)!`** — the Tk that
  ships with Apple's Command Line Tools Python is incompatible with some macOS
  builds. Fix by installing a Python from [python.org](https://www.python.org/downloads/macos/)
  (which bundles a working Tk) or via Homebrew with `brew install python-tk`, then
  recreate the virtualenv with that interpreter.
- **No sound** — `sounddevice` could not open an output device. The app still
  runs; the status bar shows the reason. Ensure an audio output device is
  available.

## Project layout

```
main.py                    entry point
src/ai_scaler/
  theory.py                notes, scales (incl. exotic), chord harmonization
  fretboard.py             tuning and fret-to-note mapping
  audio.py                 frequency + tone synthesis / playback
  gui.py                   Tkinter UI and fretboard rendering
```
