"""Reporte les clés du protocole dans site/data/quality.json / merges the protocol keys into the site quality file.

    python tools/protocol/merge_quality.py benchmarks/results/protocol-<version>-<date>.json site/data/quality.json

Clés : indice « documents normalisés » (confidence_*, mention_recall_pct, protocol_*, real_*) et, depuis la 1.1,
indice « documents difficiles » (hard_*). Keys: normalised index, and from 1.1 the difficult index (hard_*).
Ne touche qu'aux clés du protocole ; les autres clés et leur ordre restent. Refuse une campagne incomplète, un plan
réduit (essai), un plan dont les empreintes diffèrent de celles enregistrées, une campagne passée sans le jeton
local, une surcharge du service comptée en échecs (429/503), une campagne répétée qui ne liste pas celle déjà
publiée, des garde-fous en échec (sauf `--force-guards`, à déclarer publiquement), ou un site et un README qui
montrent encore le texte d'une version précédente (sauf `--site-text-checked`) ; rappelle les écarts déclarés.
Bibliothèque standard. Only touches the protocol keys; other keys and their order stay. Refuses an incomplete
campaign, a scaled (test) plan, a plan whose fingerprints differ from the registered ones, a campaign run without the
local token, service overload counted as failures (429/503), a repeat campaign that does not list the published one,
failed guards (unless `--force-guards`, to be disclosed publicly), or a site and README still showing an earlier
version's text (unless `--site-text-checked`); recalls the disclosed departures. Standard library only.
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
# Indice « documents normalisés » (l'indice de confiance principal) : clés historiques du site.
# "Normalised documents" index (the headline confidence index): the site's historical keys.
HEADLINE_KEYS = ("confidence_index", "confidence_ci_low", "confidence_ci_high", "mention_recall_pct", "protocol_docs",
                 "protocol_families", "real_corpora", "real_docs", "protocol_date", "protocol_engine")
# Indice « documents difficiles » (protocole 1.1) : équipe rouge entière / "difficult documents" index (protocol 1.1).
HARD_KEYS = ("hard_index", "hard_ci_low", "hard_ci_high", "hard_docs", "hard_mention_recall_pct")
PROTOCOL_KEYS = HEADLINE_KEYS + HARD_KEYS
_PERCENT = ("confidence_index", "confidence_ci_low", "confidence_ci_high", "mention_recall_pct", "hard_index",
            "hard_ci_low", "hard_ci_high", "hard_mention_recall_pct")
_INTEGER = ("protocol_docs", "protocol_families", "real_corpora", "real_docs", "hard_docs")
# Versions du protocole qui publient l'indice « documents difficiles » / protocol versions with the difficult index.
_HARD_FROM = (1, 1)
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
    # Indice « documents difficiles » exigé à partir de la 1.1 ; un résultat plus ancien n'en a pas (les clés hard_*
    # restent alors telles quelles). Difficult index required from 1.1; an older result has none (hard_* left as is).
    match = re.fullmatch(r"(\d+)\.(\d+)", str(results.get("protocol", {}).get("version") or ""))
    hard_required = match is not None and (int(match[1]), int(match[2])) >= _HARD_FROM
    hard_given = hard_required or any(keys.get(k) is not None for k in HARD_KEYS)
    out: dict[str, Any] = {}
    for key in PROTOCOL_KEYS:
        value = keys.get(key)
        if value is None and key in HARD_KEYS and not hard_given:
            continue
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
    if hard_given and not out["hard_ci_low"] <= out["hard_index"] <= out["hard_ci_high"]:
        raise ValueError("indice « documents difficiles » hors de son intervalle / difficult index outside its "
                         "interval")
    # Protocole 1.1 : familles de l'indice (documents normalisés) = celles du résultat, jamais celles de l'indice
    # « documents difficiles » ni celles publiées à part. Protocol 1.1: index (normalised) families = the result's,
    # never the difficult index's nor those published apart.
    families = results.get("confidence_index", {}).get("families")
    if families is not None and out["protocol_families"] != len(families):
        raise ValueError("nombre de familles différent de celles de l'indice / family count differs from the index's")
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


# Texte écrit en dur pour une version précédente, sur le site et dans le README : un report refuse de mettre l'indice
# d'une version sous le texte d'une autre. Une ligne qui nomme la version précédente (« Protocole 1.0 : 61,8 %, 7
# familles ») reste permise. Hard-coded text of an earlier version on the site and in the README: the merge refuses to
# put one version's index under another version's text; a line naming the earlier version stays allowed.
# 1.1 : texte 1.0 (sept familles, 51 « déguisements »), et premier jet 1.1 jamais enregistré (cinq familles, équipe
# rouge du quotidien dans l'indice). « 51 façons » / « 51 opérateurs » sont permis : l'indice « documents difficiles »
# couvre les 51 opérateurs. En minuscules (comparées à la ligne en minuscules). 1.1: 1.0 text and the unregistered first
# 1.1 draft (five families, everyday red team in the index); "51 ways" / "51 operators" allowed (the difficult index
# covers all 51 operators). Lower case (matched against the lower-cased line).
STALE_SITE_TEXT: dict[str, tuple[str, ...]] = {
    "1.1": ("7 familles", "7 families", "sept familles", "seven families", "51 déguisements", "51 disguises",
            "21 minutes avant le lancement", "21 minutes before the launch", "mesurées 7 fois", "measured 7 times",
            "moyenne à poids égal de la colonne", "equal-weight mean of the column",
            "cinq familles", "five families", "5 familles", "5 families", "1/5 chacune", "1/5 each",
            "restreinte aux 25", "restricted to 25 everyday"),
}
SITE_TEXT_FILES = ("site/templates/index.fr.html", "site/templates/index.en.html", "README.md")


def check_site_text(results: dict[str, Any], quality_path: Path) -> None:
    """Refuse si le site ou le README montrent encore le texte d'une version précédente / stale site text refused."""
    protocol = results.get("protocol", {})
    markers = STALE_SITE_TEXT.get(str(protocol.get("version")), ())
    quality_path = quality_path.resolve()
    if not markers or quality_path.parent.name != "data" or quality_path.parent.parent.name != "site":
        return  # pas un dépôt / not a repository layout (tests, copies)
    earlier = [str(item.get("version")) for item in protocol.get("previous_versions") or []]
    root = quality_path.parents[2]
    stale = []
    for rel in SITE_TEXT_FILES:
        path = root / rel
        if not path.is_file():
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if any(re.search(rf"(?i)(protocole|protocol|campagne|campaign|version) {re.escape(v)}(?![.\d])", line)
                   for v in earlier):
                continue  # rappel de la version précédente / the earlier version's reminder
            stale += [f"{rel}:{number}: « {m} »" for m in markers if m in line.lower()]
    if stale:
        raise ValueError("texte d'une version précédente sur le site ou dans le README, à mettre à jour avant le "
                         "report (ou --site-text-checked après relecture) / earlier-version text on the site or in "
                         f"the README, update it first: {'; '.join(stale)}")


def merge(results_path: Path, quality_path: Path, *, force_guards: bool = False, allow_scaled: bool = False,
          site_text_checked: bool = False) -> int:
    results = json.loads(results_path.read_text(encoding="utf-8"))
    quality = json.loads(quality_path.read_text(encoding="utf-8")) if quality_path.exists() else {}
    try:
        values = quality_values(results, force_guards=force_guards, allow_scaled=allow_scaled)
        check_repeat(values, results, quality)
        if not site_text_checked:
            check_site_text(results, quality_path)
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
    protocol = results.get("protocol", {})
    for item in protocol.get("previous_versions") or []:
        print(f"RAPPEL : résultat de la version {item.get('version')} gardé publié, à citer à côté / REMINDER: version "
              f"{item.get('version')} result kept published, to cite next to it: {item.get('confidence_index')} "
              f"({item.get('results')})", file=sys.stderr)
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
    parser.add_argument("--site-text-checked", action="store_true",
                        help="texte du site et du README relu pour cette version / site and README text reviewed")
    args = parser.parse_args(argv)
    return merge(args.results, args.quality, force_guards=args.force_guards, allow_scaled=args.allow_scaled,
                 site_text_checked=args.site_text_checked)


if __name__ == "__main__":
    raise SystemExit(main())
