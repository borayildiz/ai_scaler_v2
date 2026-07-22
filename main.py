"""Entry point for the ai_scaler guitar scale visualizer."""

import os
import sys

# Make the src/ layout importable when running `python main.py` directly.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from ai_scaler.gui import run  # noqa: E402


if __name__ == "__main__":
    run()
