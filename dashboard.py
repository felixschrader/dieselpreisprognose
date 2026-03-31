"""Compatibility entrypoint for Streamlit Cloud.

Keeps old `dashboard.py` main-file paths working after moving scripts.
"""

from pathlib import Path
import runpy


if __name__ == "__main__":
    target = Path(__file__).resolve().parent / "scripts" / "dashboard.py"
    runpy.run_path(str(target), run_name="__main__")
