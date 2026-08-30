"""Puts the repo's shared test support on the path, so every package proves its fragments the same
way: against the source a printer runs, at the strictness a printer applies."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tests_support"))
