"""Compass test bootstrap.

Adds the compass root and jtech-substrate-core to sys.path so tests can
import lib.* and jtech_substrate_core without a pip install.
"""
import sys
from pathlib import Path

_COMPASS_ROOT = Path(__file__).resolve().parents[1]
_SUBSTRATE = _COMPASS_ROOT.parent / "core"

for p in (_COMPASS_ROOT, _SUBSTRATE):
    if p.exists() and str(p) not in sys.path:
        sys.path.insert(0, str(p))
