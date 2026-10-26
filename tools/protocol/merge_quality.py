"""Reporte les clés du protocole dans site/data/quality.json / merges the protocol keys into the site quality file.

    python tools/protocol/merge_quality.py benchmarks/results/protocol-<date>.json site/data/quality.json

Ne touche qu'aux clés du protocole ; les autres clés et leur ordre restent. Refuse une campagne incomplète, un plan
réduit (essai), un plan dont les empreintes diffèrent de celles enregistrées, une campagne passée sans le jeton
local, une surcharge du service comptée en échecs (429/503), une campagne répétée qui ne liste pas celle déjà
publiée, ou des garde-fous en échec (sauf `--force-guards`, à déclarer publiquement) ; rappelle les écarts déclarés.
Bibliothèque standard. Only touches the protocol keys; other keys and their order stay. Refuses an incomplete
campaign, a scaled (test) plan, a plan whose fingerprints differ from the registered ones, a campaign run without the
local token, service overload counted as failures (429/503), a repeat campaign that does not list the published one,
or failed guards (unless `--force-guards`, to be disclosed publicly); recalls the disclosed departures. Standard
library only.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import re
import sys
from pathlib import Path
from typing import Any

PENDING = "—"
PROTOCOL_KEYS = ("confidence_index", "confidence_ci_low", "confidence_ci_high", "mention_recall_pct", "protocol_docs",
                 "protocol_families", "real_corpora", "real_docs", "protocol_date", "protocol_engine")
_PERCENT = ("confidence_index", "confidence_ci_low", "confidence_ci_high", "mention_recall_pct")
_INTEGER = ("protocol_docs", "protocol_families", "real_corpora", "real_docs")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+([.+-][0-9A-Za-z.+-]+)?$")


def quality_values(results: dict[str, Any], *, force_guards: bool = False,
                   allow_scaled: bool = False) -> dict[str, Any]:
    """Valeurs du contrat, vérifiées ; ValueError avec la raison sinon / contract values, checked."""
    campaign = results.get("campaign", {})
    if not campaign.get("complete"):
        raise ValueError("campagne incomplète / incomplete campaign")
    if not campaign.get("standard_plan") and not allow_scaled:
        raise ValueError("plan réduit (essai) : jamais publié / scaled (test) plan: never published")
    if campaign.get("standard_plan"):
        if results.get("registration", {}).get("fingerprints_match_registration") is not True:
            raise ValueError("empreintes du plan différentes de celles enregistrées (spec.REGISTERED_PLAN) / plan "
                             "fingerprints differ from the registered ones")
        if campaign.get("local_principal") is not True:
            raise ValueError("campagne sans jeton local : comptée comme trafic public / campaign without the local "
                             "token: counted as public traffic")
    overload = sorted(k for k in campaign.get("errors", {}) if k in ("http_429", "http_503"))
    if overload:
        raise ValueError(f"surcharge du service comptée comme fuites / service overload counted as leaks: "
                         f"{', '.join(overload)}")
    if not results.get("guards", {}).get("passed") and not force_guards:
        failed = [k for k, v in results.get("guards", {}).get("checks", {}).items() if not v.get("passed")]
        raise ValueError(f"garde-fous en échec / failed guards: {', '.join(failed) or '?'}")
    keys = results["quality_keys"]
    out: dict[str, Any] = {}
    for key in PROTOCOL_KEYS:
        value = keys.get(key)
        if value is None:
            raise ValueError(f"valeur manquante / missing value: {key}")
        if key in _PERCENT:
            if not isinstance(value, (int, float)) or not 0 <= value <= 100:
                raise ValueError(f"pourcentage invalide / invalid percent: {key}")
            value = round(float(value), 1)
        elif key in _INTEGER:
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"entier invalide / invalid integer: {key}")
        elif key == "protocol_date":
            if not isinstance(value, str) or not _DATE_RE.match(value):
                raise ValueError("date ISO attendue / ISO date expected")
        elif key == "protocol_engine" and (not isinstance(value, str) or not _VERSION_RE.match(value)):
            raise ValueError("version attendue / version expected")
        out[key] = value
    if not out["confidence_ci_low"] <= out["confidence_index"] <= out["confidence_ci_high"]:
        raise ValueError("indice hors de son intervalle / index outside its interval")
    return out


def check_repeat(values: dict[str, Any], results: dict[str, Any], quality: dict[str, Any]) -> None:
    """Campagne répétée : elle doit lister celle déjà publiée (spec.EARLIER_CAMPAIGNS) / a repeat campaign lists it.

    Après une première campagne publiée, les moitiés test ne sont plus aveugles (docs/PROTOCOLE.md, section 3) : la
    suivante le déclare en listant la précédente, recopiée dans ses résultats. Le même résultat reporté deux fois
    passe. After a first published campaign the test halves are no longer blind: the next one says so by listing the
    previous one, copied into its results. Merging the same result twice is fine.
    """
    date, engine = quality.get("protocol_date"), quality.get("protocol_engine")
    if not isinstance(date, str) or not _DATE_RE.match(date):
        return  # aucune campagne publiée / no campaign published yet
    if (date, engine) == (values["protocol_date"], values["protocol_engine"]):
        return
    earlier = results.get("registration", {}).get("earlier_campaigns") or []
    if not any(item.get("date") == date and item.get("engine") == engine for item in earlier):
        raise ValueError(f"campagne répétée : la campagne publiée du {date} (moteur {engine}) doit figurer dans "
                         "spec.EARLIER_CAMPAIGNS (nouvelle version datée du protocole, docs/PROTOCOLE.md section 3) / "
                         "repeat campaign: the published one must be listed in spec.EARLIER_CAMPAIGNS")


def merge(results_path: Path, quality_path: Path, *, force_guards: bool = False, allow_scaled: bool = False) -> int:
    results = json.loads(results_path.read_text(encoding="utf-8"))
    quality = json.loads(quality_path.read_text(encoding="utf-8")) if quality_path.exists() else {}
    try:
        values = quality_values(results, force_guards=force_guards, allow_scaled=allow_scaled)
        check_repeat(values, results, quality)
    except ValueError as exc:
        print(f"refus / refused: {exc}", file=sys.stderr)
        return 2
    for key, value in values.items():
        quality[key] = value  # clé existante : même place ; nouvelle : à la fin / existing key keeps its place
    quality_path.write_text(json.dumps(quality, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(values, ensure_ascii=False, indent=2))
    if force_guards:
        print("ATTENTION : garde-fous forcés, à déclarer publiquement / guards forced, disclose it publicly",
              file=sys.stderr)
    for item in results.get("campaign", {}).get("disclosures") or []:
        print(f"ÉCART DÉCLARÉ, à publier avec l'indice / DISCLOSED DEPARTURE, to publish with the index: "
              f"{item.get('fr')} / {item.get('en')} {item.get('detail') or ''}".rstrip(), file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    # Sorties en UTF-8, console Windows comprise (pas de mojibake) / UTF-8 output, Windows console included.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            with contextlib.suppress(OSError, ValueError):
                reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("results", type=Path)
    parser.add_argument("quality", type=Path)
    parser.add_argument("--force-guards", action="store_true")
    parser.add_argument("--allow-scaled", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    return merge(args.results, args.quality, force_guards=args.force_guards, allow_scaled=args.allow_scaled)


if __name__ == "__main__":
    raise SystemExit(main())
