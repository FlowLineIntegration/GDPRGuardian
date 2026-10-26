"""Tirage d'un échantillon à relire à la main / draws a sample for manual gold review (dev tooling).

Writes, INSIDE THE CACHE FOLDER (never the repository), a text file where each gold span is shown as
``[[LABEL|value]]`` and each ignored free-text zone as ``{{ignore: ...}}``. A reviewer reads it and fills a
small JSON verdict file (also in the cache) with, per document: spans that are wrong (not personal data, wrong
boundaries, wrong label) and personal data present in the scored zone but missing from the gold. The counts, and
only the counts, are reported in benchmarks/results and docs/CORPUS_REELS.md.

With ``--detections``, the sample shows the engine's masked spans instead (``<<LABEL|value>>``): this is how
the negative control (Judilibre) is reviewed.

Usage:
    python tools/corpus/spotcheck_real.py --cache DIR --corpus bodacc_fr [--n 50] [--seed 20261025]
    python tools/corpus/spotcheck_real.py --cache DIR --corpus judilibre_fr --detections --countries FR
"""

from __future__ import annotations

import argparse
import random
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.corpus.real_common import check_outside_repo, corpus_path, default_cache, read_jsonl  # noqa: E402


def sample(records: list[dict[str, Any]], n: int, seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    picks = sorted(rng.sample(range(len(records)), min(n, len(records))))
    return [records[i] for i in picks]


def annotate(text: str, spans: list[tuple[int, int, str]], ignore: list[list[int]], open_: str = "[[",
             close: str = "]]", preview: int | None = None) -> str:
    """Texte avec marques en ligne / text with inline marks.

    Order at one position: closing marks first (span, then zone), then opening marks (zone, then span).
    With `preview`, unannotated text inside an ignored zone is cut to that many characters per segment.
    """
    events: list[tuple[int, int, str]] = []
    for start, end in ignore:
        events.append((start, 2, "{{ignore: "))
        events.append((end, 1, "}}"))
    for start, end, label in spans:
        events.append((start, 3, f"{open_}{label}|"))
        events.append((end, 0, close))
    out: list[str] = []
    pos = 0
    inside = False
    for at, _order, mark in sorted(events):
        segment = text[pos:at]
        if inside and preview is not None and len(segment) > preview:
            segment = segment[:preview] + " [...] "
        out.append(segment)
        out.append(mark)
        inside = True if mark == "{{ignore: " else (False if mark == "}}" else inside)
        pos = at
    out.append(text[pos:])
    return "".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cache", type=Path, default=default_cache())
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--n", type=int, default=50)
    parser.add_argument("--seed", type=int, default=20261025)
    parser.add_argument("--detections", action="store_true", help="show the engine's masked spans, not the gold")
    parser.add_argument("--countries", default="FR")
    parser.add_argument("--detection-contexts", type=int, default=0,
                        help="with --detections: draw this many masked spans over the WHOLE corpus, with context")
    parser.add_argument("--max-chars", type=int, default=6000, help="cut each shown document to this length")
    parser.add_argument("--skip-lines", default=None,
                        help="regex: hide shown lines that match it and carry no annotation (codes, amounts...)")
    parser.add_argument("--ignore-preview", type=int, default=None,
                        help="cut unannotated text inside ignored zones to this many characters per segment")
    args = parser.parse_args()
    cache = check_outside_repo(args.cache)
    records = list(read_jsonl(corpus_path(cache, args.corpus)))
    picked = sample(records, args.n, args.seed)
    out_dir = cache / "spotcheck"
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = "detections" if args.detections else "gold"
    path = out_dir / f"{args.corpus}-{suffix}-{args.seed}.txt"
    anonymizer = None
    if args.detections:
        from gdprguardian import Anonymizer
        anonymizer = Anonymizer(countries=args.countries, profile="standard")
    if args.detection_contexts:
        # Un échantillon de zones masquées, chacune avec son contexte / a sample of masked spans with context
        assert anonymizer is not None, "--detection-contexts needs --detections"
        found: list[tuple[str, int, int, str, str]] = []
        for rec in records:
            found.extend((rec["id"], s.start, s.end, s.label, rec["text"])
                         for s in anonymizer.anonymize(rec["text"]).analysis.spans if s.personal)
        rng = random.Random(args.seed)
        chosen = sorted(rng.sample(range(len(found)), min(args.detection_contexts, len(found))))
        path = out_dir / f"{args.corpus}-detection-contexts-{args.seed}.txt"
        with path.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(f"{len(found)} masked spans in {len(records)} documents; {len(chosen)} drawn\n\n")
            for i, k in enumerate(chosen, 1):
                rec_id, start, end, label, text = found[k]
                left = " ".join(text[max(0, start - 70):start].split())
                right = " ".join(text[end:end + 70].split())
                fh.write(f"{i:3d} {label:<14} {left} <<{text[start:end]}>> {right}   [{rec_id}]\n")
        print(path)
        return 0
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for i, rec in enumerate(picked, 1):
            text = rec["text"]
            if anonymizer is not None:
                result = anonymizer.anonymize(text)
                spans = [(s.start, s.end, s.label) for s in result.analysis.spans if s.personal]
                shown = annotate(text, spans, [], "<<", ">>")
            else:
                spans = [(g["start"], g["end"], g["label"]) for g in rec["spans"]]
                shown = annotate(text, spans, rec.get("ignore", []), preview=args.ignore_preview)
            if args.skip_lines:
                skip = re.compile(args.skip_lines)
                shown = "\n".join(line for line in shown.split("\n")
                                  if "[[" in line or "<<" in line or not skip.search(line))
            if len(shown) > args.max_chars:
                shown = shown[: args.max_chars] + " [...]"
            fh.write(f"===== {i}/{len(picked)} {rec['id']} =====\n{shown}\n\n")
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
