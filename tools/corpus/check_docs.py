"""Contrôle d'un document généré contre son manifeste / checks a generated document against its manifest.

Signale : valeurs obligatoires absentes (à l'identique), leurres absents, formes de noms utilisées, et mots
capitalisés suspects hors manifeste (possibles données personnelles ajoutées).
Reports: missing mandatory values (verbatim), missing decoys, name forms used, and suspicious capitalised
words outside the manifest (possible extra personal data).

Usage : python tools/corpus/check_docs.py --ids fr-00000 fr-00001   (ou --all)
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFESTS = ROOT / "datasets" / "fr" / "manifests.jsonl"
DOCS = ROOT / "datasets" / "fr" / "docs"
_CAPITALISED = re.compile(r"\b[A-ZÀ-Ý][a-zà-ÿ]{2,}(?:[- ][A-ZÀ-Ý][a-zà-ÿ]{2,})*\b")
_DIGIT_RUN = re.compile(r"\+?\d[\d .\-/]{7,}\d")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


def load_manifests() -> dict[str, dict]:
    with MANIFESTS.open(encoding="utf-8") as handle:
        return {m["id"]: m for m in map(json.loads, handle)}


def mandatory_values(manifest: dict) -> list[tuple[str, str]]:
    values: list[tuple[str, str]] = []
    for person in manifest["persons"]:
        values.append(("full_name", f"{person['given']} {person['surname']}"))
        values.extend((key, person[key]) for key in ("email", "phone", "nir", "birth_date", "address", "iban",
                                                      "card", "passport", "plate") if person.get(key))
    company = manifest["company"]
    values += [("company_name", company["name"]), ("siren_or_siret", company["siret"]), ("tva", company["tva"])]
    return values


def check(manifest: dict, text: str) -> dict:
    missing = [{"type": kind, "value": value} for kind, value in mandatory_values(manifest) if value not in text]
    decoys_missing = [d for d in manifest["decoys"] if d not in text]
    forms_used = {
        f"{p['given']} {p['surname']}": [form for form in p["allowed_forms"] if form in text]
        for p in manifest["persons"]
    }
    known_tokens = set()
    for person in manifest["persons"]:
        for form in person["allowed_forms"]:
            known_tokens.update(re.findall(r"[^\W\d_]+", form))
    known_tokens.update(re.findall(r"[^\W\d_]+", manifest["company"]["name"]))
    known_tokens.update(re.findall(r"[^\W\d_]+", " ".join(p["address"] for p in manifest["persons"])))
    suspicious = sorted({m.group() for m in _CAPITALISED.finditer(text)} - known_tokens)
    planted = " ".join(v for _, v in mandatory_values(manifest)) + " " + " ".join(manifest["decoys"])
    extra_numbers = sorted({m.group().strip() for m in _DIGIT_RUN.finditer(text)
                            if m.group().strip() not in planted and len(re.sub(r"\D", "", m.group())) >= 8})
    extra_emails = sorted({m.group() for m in _EMAIL.finditer(text)} - {p["email"] for p in manifest["persons"]})
    return {
        "id": manifest["id"],
        "ok": not missing and not decoys_missing and not extra_emails,
        "missing": missing,
        "decoys_missing": decoys_missing,
        "forms_used": forms_used,
        "extra_emails": extra_emails,
        "extra_long_numbers": extra_numbers,
        "capitalised_words_outside_manifest": suspicious,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ids", nargs="*", default=[])
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    manifests = load_manifests()
    ids = sorted(manifests) if args.all else args.ids
    reports = []
    for doc_id in ids:
        path = DOCS / f"{doc_id}.md"
        if not path.exists():
            reports.append({"id": doc_id, "ok": False, "error": "document absent / missing"})
            continue
        reports.append(check(manifests[doc_id], path.read_text(encoding="utf-8")))
    print(json.dumps(reports, ensure_ascii=False, indent=1))
    bad = [r["id"] for r in reports if not r["ok"]]
    print(f"# {len(reports) - len(bad)}/{len(reports)} OK ; à corriger / to fix: {bad}")


if __name__ == "__main__":
    main()
