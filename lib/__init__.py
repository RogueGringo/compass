"""Compass lib package.

Bootstraps jtech-substrate-core onto sys.path so trigger.py and the lib
modules can import the shared substrate without `pip install`. Looks
for the substrate at a sibling directory of compass/.
"""
import sys
from pathlib import Path

_COMPASS_ROOT = Path(__file__).resolve().parents[1]
_SUBSTRATE_PARENT = _COMPASS_ROOT.parent / "core"
if _SUBSTRATE_PARENT.exists() and str(_SUBSTRATE_PARENT) not in sys.path:
    sys.path.insert(0, str(_SUBSTRATE_PARENT))
