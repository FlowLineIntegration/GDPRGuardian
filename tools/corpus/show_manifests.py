"""Affiche les manifestes demandés / prints the requested manifests.

Usage : python tools/corpus/show_manifests.py --ids fr-00000 fr-00001
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MANIFESTS = Path(__file__).resolve().parents[2] / "datasets" / "fr" / "manifests.jsonl"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ids", nargs="+", required=True)
    args = parser.parse_args()
    wanted = set(args.ids)
    sys.stdout.reconfigure(encoding="utf-8")
    with MANIFESTS.open(encoding="utf-8") as handle:
        selected = [m for m in map(json.loads, handle) if m["id"] in wanted]
    print(json.dumps(selected, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
