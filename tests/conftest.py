"""Puts the repo's shared test support on the path, the same way each package's own suite does, so
the migration is proved against the source a printer runs at the strictness a printer applies."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests_support"))
