"""Accès aux outils de corpus réels (hors paquet publié) / access to the real-corpus tooling (not shipped)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = str(Path(__file__).resolve().parents[2])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
