"""Writes a protocol result into the site and the README, in one command. Standard library only.

    python site/tools/protocol_table.py benchmarks/results/protocol-1.1-<date>.json

1. Runs tools/protocol/merge_quality.py on the result first (headline keys: index, interval, mention recall, counts,
   date, engine), with every refusal it has; --force-guards and --site-text-checked are passed through. Nothing is
   written when it refuses.
2. Writes the per-family table keys into site/data/quality.json (f_<family>_docs, _nl, _mr, _pr; the Judilibre
   control; the guards) and protocol_version, "—" for a value the result does not have (the site shows "—").
3. Fills the values between <!--q:<key>:<fr|en>-->…<!--/q--> markers in README.md, formatted per language.
Nothing of steps 2 and 3 is written when a README marker names a key the site file does not have.

--table-only skips step 1 (a scaled trial, or a check on an older result); --pending writes "—" for every table key
and every README marker, no result needed (protocol_version is left as it is; --pending-index also resets the
headline keys and protocol_version, so the site says "not measured yet" rather than show an earlier version's index);
--quality and --readme pick other files (tests). The site build accepts "—" for every table key.
--modes-file F writes the per-mode keys of an internal measure (`python -m tools.protocol modes-dev`), refused for an
engine label older than 1.0.2; --only-fort leaves the essentiel keys at "—".
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
QUALITY = ROOT / "site" / "data" / "quality.json"
README = ROOT / "README.md"
PENDING = "—"

# Short code on the page -> family name in the result (tools/protocol/spec.py, FAMILIES then APART_FAMILIES).
FAMILIES = (("syn", "synthetic_fr"), ("red", "redteam_fr"), ("bod", "bodacc_fr"), ("boa", "boamp_fr"),
            ("par", "parlamint_fr"), ("obf", "redteam_obfuscation_fr"), ("ocr", "redteam_ocr_fr"),
            ("old", "old_press_fr"), ("mapa", "mapa_fr"), ("oth", None))
MEASURES = ("docs", "nl", "mr", "pr")
# Version of the protocol whose result the headline keys hold ("1.0" until the first 1.1 result is written).
VERSION_KEY = "protocol_version"
TABLE_KEYS: tuple[str, ...] = (
    *(f"f_{code}_{m}" for code, _ in FAMILIES for m in MEASURES),
    "f_jud_docs", "f_jud_spans", "g_overmask", "g_decoys",
)
SITE_KEYS = (VERSION_KEY, *TABLE_KEYS)  # every key this script writes (site/tools/preview.py checks them)
# Headline keys, written by tools/protocol/merge_quality.py (step 1); --pending-index resets them to "—".
HEADLINE_KEYS = ("confidence_index", "confidence_ci_low", "confidence_ci_high", "mention_recall_pct", "protocol_docs",
                 "protocol_families", "real_corpora", "real_docs", "protocol_date", "protocol_engine",
                 "hard_index", "hard_ci_low", "hard_ci_high", "hard_docs", "hard_mention_recall_pct")
PERCENT_DECIMALS = {"g_overmask": 2}
# Protocol 1.2: two numbers per filter mode (anonymisation: normalised index, its interval, difficult index; useful
# codes lost: decoys masked), and where they come from. Written from a 1.2 result (modes_source "protocole 1.2") or,
# until the 1.2 campaign, from `python -m tools.protocol modes-dev` with --modes-file (modes_source "mesure interne,
# moitié dev"). Not in SITE_KEYS: preview.py lists them itself; --pending leaves them as they are.
MODE_KEYS = ("fort_index", "fort_ci_low", "fort_ci_high", "fort_hard_index", "fort_code_loss",
             "ess_index", "ess_ci_low", "ess_ci_high", "ess_hard_index", "ess_code_loss",
             "modes_source", "modes_date", "modes_engine")
INTERNAL_SOURCE = "mesure interne, moitié dev"


def _pct(value: Any, decimals: int = 1) -> Any:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return PENDING
    value = round(100 * float(value), decimals)
    if not 0 <= value <= 100:
        raise ValueError(f"pourcentage hors de 0-100 / percentage out of range: {value}")
    return value


def _count(value: Any) -> Any:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else PENDING


def family_values(entry: dict[str, Any] | None) -> dict[str, Any]:
    """Scored documents, no-leak rate, mention recall, precision of one family (test half for real corpora)."""
    if not entry:
        return dict.fromkeys(MEASURES, PENDING)
    head = entry.get("headline") or {}
    measures = entry.get("measures") or {}
    precision = (measures.get("metrics") or {}).get("precision") if entry.get("kind") == "real" \
        else measures.get("precision")
    return {"docs": _count(head.get("scored")), "nl": _pct(head.get("no_leak_rate")),
            "mr": _pct(head.get("mention_recall")), "pr": _pct(precision)}


def other_languages(out_of_scope: dict[str, Any]) -> dict[str, Any]:
    """Other languages pooled (test half): documents, no leak and mentions summed; precision not pooled ("—")."""
    outcomes = [row.get("test", {}).get("outcome") or {} for row in out_of_scope.values()]
    if not outcomes:
        return dict.fromkeys(MEASURES, PENDING)
    scored = sum(o.get("scored", 0) for o in outcomes)
    passed = sum(o.get("passed", 0) for o in outcomes)
    mentions = sum(o.get("mentions", 0) for o in outcomes)
    masked = sum(o.get("mentions_masked", 0) for o in outcomes)
    return {"docs": scored, "nl": _pct(passed / scored) if scored else PENDING,
            "mr": _pct(masked / mentions) if mentions else PENDING, "pr": PENDING}


def table_values(results: dict[str, Any]) -> dict[str, Any]:
    version = (results.get("protocol") or {}).get("version")
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+", version):
        raise ValueError(f"version du protocole illisible / unreadable protocol version: {version!r}")
    out: dict[str, Any] = {VERSION_KEY: version}
    index, apart = results.get("families") or {}, results.get("families_apart") or {}
    for code, name in FAMILIES:
        values = other_languages(results.get("out_of_scope") or {}) if name is None \
            else family_values(index.get(name) or apart.get(name))
        out.update({f"f_{code}_{m}": values[m] for m in MEASURES})
    control = (results.get("negative_control") or {}).get("judilibre_fr") or {}
    spans = control.get("masked_spans_per_10k_chars")
    out["f_jud_docs"] = _count(control.get("docs"))
    out["f_jud_spans"] = round(float(spans), 1) if isinstance(spans, (int, float)) else PENDING
    checks = (results.get("guards") or {}).get("checks") or {}
    if "overmask_synthetic" in checks or "decoys_masked_synthetic" in checks:  # 1.0 and 1.1: one set of guards
        overmask = (checks.get("overmask_synthetic") or {}).get("value")
        decoys = (checks.get("decoys_masked_synthetic") or {}).get("value")
    else:
        # 1.2: guards per mode ("fort/overmask_synthetic"…). Over-masking: the higher of the modes (the guard that
        # matters); decoys: the mode(s) where the decoy guard applies (essentiel; fort shows its loss, no guard).
        values = [c.get("value") for k, c in checks.items() if k.endswith("/overmask_synthetic")]
        overmask = max((v for v in values if isinstance(v, (int, float))), default=None)
        decoys = next((c.get("value") for k, c in checks.items() if k.endswith("/decoys_masked_synthetic")), None)
    out["g_overmask"] = _pct(overmask, PERCENT_DECIMALS["g_overmask"])
    out["g_decoys"] = _pct(decoys)
    if tuple(int(x) for x in version.split(".")) >= (1, 2):
        out.update(_merge_module().mode_values(results.get("quality_keys") or {}, f"protocole {version}"))
    return out


def _merge_module() -> Any:
    """tools/protocol/merge_quality.py, loaded by path (standard library only, works under python -I)."""
    path = ROOT / "tools" / "protocol" / "merge_quality.py"
    spec = importlib.util.spec_from_file_location("merge_quality", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODES_FROM_ENGINE = (1, 0, 2)  # the first engine with modes; an earlier label means unfinished sources


def internal_mode_values(data: dict[str, Any], quality: dict[str, Any], *, only_fort: bool = False) -> dict[str, Any]:
    """Per-mode keys of a modes-dev file (internal measure, dev halves); never over a protocol 1.2 result.

    Refused when the engine label is older than 1.0.2 (modes did not exist: unfinished sources, not a release).
    only_fort: the essentiel keys are written "—" (a mode not yet fit to show; the site then shows nothing of it)."""
    if str(quality.get("modes_source", "")).startswith("protocole"):
        raise ValueError("the site already shows a protocol result per mode; an internal measure never replaces it")
    engine = str((data.get("keys") or {}).get("modes_engine", ""))
    base = re.match(r"(\d+)\.(\d+)\.(\d+)", engine)
    if not base or tuple(int(x) for x in base.groups()) < MODES_FROM_ENGINE:
        raise ValueError(f"engine {engine!r}: modes exist from 1.0.2; rerun modes-dev on the released engine")
    values = _merge_module().mode_values(data.get("keys") or {}, INTERNAL_SOURCE)
    if only_fort:
        values.update({k: PENDING for k in values if k.startswith("ess_")})
    return values


# ---------------------------------------------------------------------------------------------- README markers

MARKER = re.compile(r"<!--q:([a-z_]+):(fr|en)-->(.*?)<!--/q-->")
MONTHS = {"fr": ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
                 "novembre", "décembre"),
          "en": ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
                 "November", "December")}


def text_value(value: Any, lang: str) -> str:
    """Like the site: French "1 019 385" and "61,8", English "1,019,385" and "61.8"; an ISO date in words."""
    if isinstance(value, str):
        match = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", value)
        if not match:
            return value
        year, month, day = (int(part) for part in match.groups())
        return f"{'1er' if lang == 'fr' and day == 1 else day} {MONTHS[lang][month - 1]} {year}"
    raw = json.dumps(value)
    integer, _, fraction = raw.partition(".")
    grouped = f"{int(integer):,}"
    if lang == "fr":
        return grouped.replace(",", " ") + ("," + fraction if fraction else "")
    return grouped + ("." + fraction if fraction else "")


def fill_readme(text: str, quality: dict[str, Any] | None) -> str:
    """Values between the markers; every one "—" when quality is None (no result of this version yet)."""

    def sub(match: re.Match) -> str:
        key, lang = match.group(1), match.group(2)
        value = PENDING if quality is None else text_value(quality[key], lang)
        return f"<!--q:{key}:{lang}-->{value}<!--/q-->"

    return MARKER.sub(sub, text)


# ---------------------------------------------------------------------------------------------- main

def run_merge(results: Path, quality: Path, *, force_guards: bool, site_text_checked: bool) -> int:
    return _merge_module().merge(results, quality, force_guards=force_guards, site_text_checked=site_text_checked)


def write_modes_file(path: Path, quality_path: Path, *, only_fort: bool = False) -> int:
    """--modes-file: the per-mode keys of an internal measure into the site file, nothing else."""
    quality = json.loads(quality_path.read_text(encoding="utf-8"))
    try:
        values = internal_mode_values(json.loads(path.read_text(encoding="utf-8")), quality, only_fort=only_fort)
    except ValueError as exc:
        print(f"refus / refused: {exc}", file=sys.stderr)
        return 2
    quality.update(values)
    write_json(quality_path, quality)
    print(json.dumps(values, ensure_ascii=False, indent=2))
    print(f"modes: internal measure written ({INTERNAL_SOURCE}); the site must label it as such, never as the protocol",
          file=sys.stderr)
    return 0


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        with contextlib.suppress(AttributeError, OSError, ValueError):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("results", type=Path, nargs="?", help="benchmarks/results/protocol-<version>-<date>.json")
    parser.add_argument("--quality", type=Path, default=QUALITY)
    parser.add_argument("--readme", type=Path, default=README)
    parser.add_argument("--table-only", action="store_true", help="skip merge_quality.py (headline keys)")
    parser.add_argument("--pending", action="store_true", help="write '—' for every table key, no result needed")
    parser.add_argument("--pending-index", action="store_true",
                        help="with --pending: the headline keys and protocol_version too (site shows 'not measured "
                             "yet' instead of an earlier version's index)")
    parser.add_argument("--force-guards", action="store_true", help="passed to merge_quality.py")
    parser.add_argument("--site-text-checked", action="store_true", help="passed to merge_quality.py")
    parser.add_argument("--modes-file", type=Path,
                        help="per-mode keys of `python -m tools.protocol modes-dev` (internal measure, dev halves) "
                             "into the site file; nothing else is written")
    parser.add_argument("--only-fort", action="store_true",
                        help="with --modes-file: write the fort keys only, the essentiel keys stay '—'")
    args = parser.parse_args(argv)
    if args.only_fort and args.modes_file is None:
        parser.error("--only-fort goes with --modes-file")
    if args.modes_file is not None:
        if args.pending or args.results is not None:
            parser.error("--modes-file goes alone")
        return write_modes_file(args.modes_file, args.quality, only_fort=args.only_fort)
    if args.pending == (args.results is not None):
        parser.error("give a results file, or --pending")
    if args.pending_index and not args.pending:
        parser.error("--pending-index goes with --pending")
    if args.pending:
        values: dict[str, Any] = dict.fromkeys(TABLE_KEYS, PENDING)
        if args.pending_index:
            values.update(dict.fromkeys((*HEADLINE_KEYS, VERSION_KEY), PENDING))
    else:
        results = json.loads(args.results.read_text(encoding="utf-8"))
        try:
            values = table_values(results)
        except ValueError as exc:
            print(f"refus / refused: {exc}", file=sys.stderr)
            return 2
    readme = args.readme.read_text(encoding="utf-8") if args.readme.is_file() else None
    # Every README marker must name a key the site file has (or gets now): checked before anything is written.
    known = set(json.loads(args.quality.read_text(encoding="utf-8"))) | set(values) | {VERSION_KEY}
    unknown = sorted({key for key, _, _ in MARKER.findall(readme or "")} - known)
    if unknown:
        print(f"refus / refused: README markers name unknown keys: {', '.join(unknown)}", file=sys.stderr)
        return 2
    if not args.pending and not args.table_only:
        code = run_merge(args.results, args.quality, force_guards=args.force_guards,
                         site_text_checked=args.site_text_checked)
        if code:
            return code
    quality = json.loads(args.quality.read_text(encoding="utf-8"))
    quality.setdefault(VERSION_KEY, PENDING)
    quality.update(values)  # existing key keeps its place, a new one goes at the end
    write_json(args.quality, quality)
    print(json.dumps(values, ensure_ascii=False, indent=2))
    if readme is not None:
        text = fill_readme(readme, None if args.pending else quality)
        args.readme.write_text(text, encoding="utf-8", newline="\n")
        print(f"README: {len(MARKER.findall(text))} value(s) written ({args.readme})")
    pending = sorted(k for k, v in quality.items() if v == PENDING and k in TABLE_KEYS)
    if pending and not args.pending:
        print(f"shown as '—' (not in this result): {', '.join(pending)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
