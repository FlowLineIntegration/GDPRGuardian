"""`python -m tools.protocol …` : voir `tools/protocol/cli.py` / see `tools/protocol/cli.py`."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):  # lancé comme script / run as a script
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.protocol.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
