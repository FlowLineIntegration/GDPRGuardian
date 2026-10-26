"""Télécharge des jeux publics annotés et les convertit en JSONL unifié (outil de dev uniquement).

Downloads public annotated datasets and converts them to a unified JSONL (dev tooling only).
Nothing is vendored: files land in datasets/public/cache/ (git-ignored) and are pinned by revision.

Record: {"id", "source", "language", "text", "spans": [{"start", "end", "label", "text"}]}
Labels are GDPR Guardian families: PERSON, ORG, ADDRESS, LOCATION, EMAIL, PHONE, NATIONAL_ID, TAX_ID, IBAN,
BANK_ACCOUNT, CARD, BIRTH_DATE, DATE, ID, URL, IP, OTHER.

Usage:
    python tools/corpus/fetch_public.py                 # all permissive French sets
    python tools/corpus/fetch_public.py --only fr_pii_bench mapa_fr
    python tools/corpus/fetch_public.py --tab           # + TAB (English, MIT), optional
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PUBLIC_DIR = ROOT / "datasets" / "public"
CACHE_DIR = PUBLIC_DIR / "cache"
RAW_DIR = CACHE_DIR / "raw"
META_PATH = CACHE_DIR / "meta.json"
SOURCES_MD = PUBLIC_DIR / "SOURCES.md"

FAMILIES = ("PERSON", "ORG", "ADDRESS", "LOCATION", "EMAIL", "PHONE", "NATIONAL_ID", "TAX_ID", "IBAN",
            "BANK_ACCOUNT", "CARD", "BIRTH_DATE", "DATE", "ID", "URL", "IP", "OTHER")


@dataclass(frozen=True)
class Source:
    name: str
    title: str
    url: str
    repo: str            # HF dataset id or GitHub "owner/repo"
    revision: str        # commit sha (pinned)
    licence: str
    attribution: str
    notes: str
    kind: str = "hf"     # "hf" or "github"


SOURCES: dict[str, Source] = {s.name: s for s in (
    Source(
        "fr_pii_bench", "FR-PII-Bench v0", "https://huggingface.co/datasets/JaqueBill/fr-pii-bench",
        "JaqueBill/fr-pii-bench", "5476b0a489249047a478083ac856a328d0e4d2c3", "CC-BY-4.0",
        "Xiao, H. (2026). FR-PII-Bench v0, 300 synthetic French documents. CC-BY-4.0. "
        "https://huggingface.co/datasets/JaqueBill/fr-pii-bench",
        "Synthetic (Faker fr_FR), exact offsets. Author used it to tune its own stop-list; not held-out for them."),
    Source(
        "mapa_fr", "MAPA EUR-Lex (French split)", "https://huggingface.co/datasets/joelniklaus/mapa",
        "joelniklaus/mapa", "bbb2a0157b760465002fd12a61af81b475cd387a", "CC-BY-4.0",
        "de Gibert Bonet, O., Garcia Pablos, A., Cuadros, M., Melero, M. (2022). Spanish Datasets for Sensitive "
        "Entity Detection in the Legal Domain, LREC 2022; MAPA project; HF mirror by J. Niklaus. CC-BY-4.0.",
        "Manual annotations, legal text (EUR-Lex), tokenised: text rebuilt by joining tokens with spaces, "
        "one record per source document. Few direct identifiers (mostly legal-entity names, places, dates)."),
    Source(
        "gretel_fr", "gretelai/synthetic_pii_finance_multilingual (French)",
        "https://huggingface.co/datasets/gretelai/synthetic_pii_finance_multilingual",
        "gretelai/synthetic_pii_finance_multilingual", "7b844d16738527a04264f50214cb426a4cea0897", "Apache-2.0",
        "Gretel.ai (2024). synthetic_pii_finance_multilingual. Apache-2.0. "
        "https://huggingface.co/datasets/gretelai/synthetic_pii_finance_multilingual",
        "SILVER labels (LLM-generated text, GLiNER-assisted spans): false positives and negatives in gold. "
        "Read from the pinned data/France_{train,test} parquet files (requires pyarrow)."),
    Source(
        "openpii_fr", "ai4privacy pii-masking-openpii-1m (French, validation split sample)",
        "https://huggingface.co/datasets/ai4privacy/pii-masking-openpii-1m",
        "ai4privacy/pii-masking-openpii-1m", "ecfdc547f4a0955600cfe6ab98ba2a162207fcc0", "CC-BY-4.0",
        "Ai4Privacy / Ai Suisse SA (2026). OpenPII 1M. CC-BY-4.0 (c) 2026 Ai Suisse SA. "
        "https://huggingface.co/datasets/ai4privacy/pii-masking-openpii-1m",
        "Synthetic, generic labels (SOCIALNUM, TAXNUM, IDCARDNUM...). Card header says 'license: other' with "
        "license_name cc-by-4.0, and the card body states CC-BY-4.0 with commercial use allowed. Generator model "
        "undisclosed. Streamed (the file is 0.9 GB): first records with language=fr and region=FR only (fr-BE/CA/CH "
        "use non-French formats; --openpii-region any to keep them). GIVENNAME+SURNAME and "
        "STREET+BUILDINGNUM+ZIPCODE are merged into single PERSON / ADDRESS spans."),
    Source(
        "tab_en", "TAB, Text Anonymization Benchmark (English, ECHR)",
        "https://github.com/NorskRegnesentral/text-anonymization-benchmark",
        "NorskRegnesentral/text-anonymization-benchmark", "558e09e26d6b36f5f78440074e6a233946d98bd9", "MIT",
        "Pilan, I., Lison, P., Ovrelid, L., Papadopoulou, A., Sanchez, D., Batet, M. (2022). The Text "
        "Anonymization Benchmark (TAB). Copyright Norsk Regnesentral. MIT.",
        "English (optional, --tab). DIRECT and QUASI identifier mentions of the first annotator; "
        "NO_MASK mentions are dropped.", kind="github"),
)}

# --- label maps / tables de correspondance ---

FR_PII_BENCH_MAP = {
    "PERSON": "PERSON", "ADDRESS": "ADDRESS", "COMPANY": "ORG", "EMAIL": "EMAIL", "PHONE": "PHONE",
    "DOB": "BIRTH_DATE", "NIR": "NATIONAL_ID", "SIREN": "ID", "SIRET": "ID", "IBAN": "IBAN",
    "FISCAL": "TAX_ID", "PLAQUE": "ID", "PASSEPORT": "NATIONAL_ID",
}

GRETEL_MAP = {
    "name": "PERSON", "first_name": "PERSON", "last_name": "PERSON", "company": "ORG", "date": "DATE",
    "date_of_birth": "BIRTH_DATE", "date_time": "DATE", "email": "EMAIL", "phone_number": "PHONE",
    "street_address": "ADDRESS", "iban": "IBAN", "bban": "BANK_ACCOUNT", "bank_routing_number": "BANK_ACCOUNT",
    "credit_card_number": "CARD", "ssn": "NATIONAL_ID", "passport_number": "NATIONAL_ID",
    "driver_license_number": "ID", "customer_id": "ID", "employee_id": "ID", "user_name": "ID",
    "ipv4": "IP", "ipv6": "IP", "local_latlng": "LOCATION",
}  # others (time, password, api_key, pin, cvv, swift_bic_code...) -> OTHER

OPENPII_MAP = {
    "GIVENNAME": "PERSON", "SURNAME": "PERSON", "STREET": "ADDRESS", "BUILDINGNUM": "ADDRESS",
    "ZIPCODE": "ADDRESS", "CITY": "LOCATION", "EMAIL": "EMAIL", "TELEPHONENUM": "PHONE", "DATE": "DATE",
    "TAXNUM": "TAX_ID", "SOCIALNUM": "NATIONAL_ID", "IDCARDNUM": "NATIONAL_ID", "PASSPORTNUM": "NATIONAL_ID",
    "DRIVERLICENSENUM": "ID", "CREDITCARDNUMBER": "CARD",
}  # TITLE, AGE, GENDER, SEX -> OTHER

MAPA_OTHER_FINE = {"AGE", "ETHNIC CATEGORY", "MARITAL STATUS", "PROFESSION", "ROLE", "NATIONALITY", "TITLE"}
MAPA_LOCATION_FINE = {"CITY", "COUNTRY", "PLACE", "TERRITORY"}

TAB_MAP = {"PERSON": "PERSON", "ORG": "ORG", "LOC": "LOCATION", "DATETIME": "DATE"}
# CODE (court case numbers), DEMO, QUANTITY, MISC -> OTHER


# --- helpers ---

def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def clean_spans(text: str, raw: Iterable[tuple[int, int, str]]) -> list[dict[str, Any]]:
    """Valide les bornes, retire les chevauchements (garde le plus long) / validate and de-overlap."""
    items = sorted(((s, e, lab) for s, e, lab in raw if 0 <= s < e <= len(text)), key=lambda t: (t[0], -(t[1] - t[0])))
    kept: list[tuple[int, int, str]] = []
    for s, e, lab in items:
        if kept and s < kept[-1][1]:
            if e - s > kept[-1][1] - kept[-1][0] and s <= kept[-1][0]:
                kept[-1] = (s, e, lab)
            continue
        kept.append((s, e, lab))
    return [{"start": s, "end": e, "label": lab, "text": text[s:e]} for s, e, lab in kept]


def merge_runs(text: str, spans: list[tuple[int, int, str]], parts: set[str], merged: str,
               gap_ok: Callable[[str], bool]) -> list[tuple[int, int, str]]:
    """Fusionne les composants contigus (ex. nom+prénom) / merge contiguous components into one span."""
    out: list[tuple[int, int, str]] = []
    for s, e, lab in sorted(spans):
        if out and lab in parts and out[-1][2] == merged and gap_ok(text[out[-1][1]:s]):
            out[-1] = (out[-1][0], e, merged)
        else:
            out.append((s, e, merged if lab in parts else lab))
    return out


def write_jsonl(name: str, records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{name}.jsonl"
    count = 0
    spans = 0
    by_label: dict[str, int] = {}
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            count += 1
            spans += len(rec["spans"])
            for sp in rec["spans"]:
                by_label[sp["label"]] = by_label.get(sp["label"], 0) + 1
    return {"records": count, "spans": spans, "labels": dict(sorted(by_label.items())), "file": path.name}


def http_json(url: str) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "gdprguardian-eval/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_json_retry(url: str, tries: int = 8) -> Any:
    """GET JSON with backoff; honours Retry-After on HTTP 429 / retry avec attente."""
    for attempt in range(tries):
        try:
            return http_json(url)
        except urllib.error.HTTPError as exc:
            if attempt == tries - 1:
                raise
            wait = float(exc.headers.get("Retry-After") or 0) if exc.code == 429 else 0.0
            time.sleep(max(wait, 3.0 * (attempt + 1)))
        except OSError:
            if attempt == tries - 1:
                raise
            time.sleep(3.0 * (attempt + 1))
    return None


def hf_file(repo: str, filename: str, revision: str) -> Path:
    from huggingface_hub import hf_hub_download
    local = RAW_DIR / repo.replace("/", "__")
    return Path(hf_hub_download(repo, filename, repo_type="dataset", revision=revision, local_dir=local))


# --- converters / convertisseurs ---

def convert_fr_pii_bench(src: Source, _args: argparse.Namespace) -> dict[str, Any]:
    path = hf_file(src.repo, "fr_pii_bench_v0.jsonl", src.revision)

    def gen() -> Iterator[dict[str, Any]]:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            doc = json.loads(line)
            text = doc["text"]
            raw = [(e["start"], e["end"], FR_PII_BENCH_MAP.get(e["label"], "OTHER")) for e in doc["entities"]]
            yield {"id": f"fr_pii_bench:{doc['id']}", "source": src.name, "language": "fr", "text": text,
                   "spans": clean_spans(text, raw)}

    return write_jsonl(src.name, gen())


def _bio_spans(coarse: list[str], fine: list[str]) -> list[tuple[int, int, str, str]]:
    """(token_start, token_end_excl, coarse, fine_of_first_token)."""
    spans: list[tuple[int, int, str, str]] = []
    start = -1
    cur = ""
    for i, tag in enumerate([*coarse, "O"]):
        if start >= 0 and (tag == "O" or tag.startswith("B-") or tag[2:] != cur):
            spans.append((start, i, cur, fine[start].split("-", 1)[-1] if fine[start] != "O" else ""))
            start = -1
        if tag != "O" and start < 0:
            start, cur = i, tag[2:]
    return spans


def convert_mapa_fr(src: Source, _args: argparse.Namespace) -> dict[str, Any]:
    docs: dict[str, list[dict[str, Any]]] = {}
    for split in ("train", "validation", "test"):
        path = hf_file(src.repo, f"{split}.jsonl", src.revision)
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                row = json.loads(line)
                if row.get("language") == "fr":
                    docs.setdefault(f"{split}/{row['file_name']}", []).append(row)

    def gen() -> Iterator[dict[str, Any]]:
        for doc_id, rows in docs.items():
            rows.sort(key=lambda r: r["sentence_number"])
            text = ""
            raw: list[tuple[int, int, str]] = []
            for row in rows:
                tokens = row["tokens"]
                offsets: list[tuple[int, int]] = []
                pos = len(text)
                for tok in tokens:
                    offsets.append((pos, pos + len(tok)))
                    pos += len(tok) + 1
                for ts, te, coarse, fine in _bio_spans(row["coarse_grained"], row["fine_grained"]):
                    label = _mapa_label(coarse, fine)
                    if label:
                        raw.append((offsets[ts][0], offsets[te - 1][1], label))
                text += " ".join(tokens) + "\n"
            yield {"id": f"mapa_fr:{doc_id}", "source": src.name, "language": "fr", "text": text,
                   "spans": clean_spans(text, raw)}

    return write_jsonl(src.name, gen())


def _mapa_label(coarse: str, fine: str) -> str | None:
    coarse = coarse.upper()
    fine = fine.upper()
    if coarse == "PERSON":
        return "OTHER" if fine in MAPA_OTHER_FINE else ("URL" if fine == "URL" else "PERSON")
    if coarse == "ORGANISATION":
        return "ORG"
    if coarse == "ADDRESS":
        return "LOCATION" if fine in MAPA_LOCATION_FINE else "ADDRESS"
    if coarse == "DATE":
        return "DATE"
    return None  # AMOUNT, TIME: not personal data


def _gretel_rows(src: Source, args: argparse.Namespace) -> list[dict[str, Any]]:
    """French rows from the pinned parquet files (needs pyarrow, an optional dev dependency)."""
    if args.pyarrow_path:
        sys.path.insert(0, args.pyarrow_path)
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise RuntimeError("gretel_fr needs pyarrow: pip install pyarrow (or pass --pyarrow-path DIR)") from exc
    rows: list[dict[str, Any]] = []
    for split in ("train", "test"):
        path = hf_file(src.repo, f"data/France_{split}-00000-of-00001.parquet", src.revision)
        table = pq.read_table(path).to_pylist()
        rows.extend({**r, "_split": split} for r in table if r.get("language") in ("France", "French"))
        log(f"gretel_fr {split}: {len(table)} rows in the France file")
    return rows


def convert_gretel_fr(src: Source, args: argparse.Namespace) -> dict[str, Any]:
    rows = _gretel_rows(src, args)

    def gen() -> Iterator[dict[str, Any]]:
        for i, row in enumerate(rows):
            text = row["generated_text"]
            spans = row["pii_spans"]
            if isinstance(spans, str):
                spans = json.loads(spans)
            raw = [(int(s["start"]), int(s["end"]), GRETEL_MAP.get(s["label"], "OTHER")) for s in spans]
            yield {"id": f"gretel_fr:{row['_split']}:{i}", "source": src.name, "language": "fr", "text": text,
                   "spans": clean_spans(text, raw)}

    return write_jsonl(src.name, gen())


def convert_openpii_fr(src: Source, args: argparse.Namespace) -> dict[str, Any]:
    from huggingface_hub import HfFileSystem
    path = f"datasets/{src.repo}@{src.revision}/data/validation.jsonl"
    limit = args.openpii_limit
    max_bytes = args.openpii_scan_mb * 1024 * 1024
    gap_ok = re.compile(r"^[ ,]{0,2}$").match
    records: list[dict[str, Any]] = []
    scanned = 0
    with HfFileSystem().open(path, "rb") as fh:
        for line in fh:
            scanned += len(line)
            if scanned > max_bytes or len(records) >= limit:
                break
            if b'"language": "fr"' not in line and b'"language":"fr"' not in line:
                continue
            row = json.loads(line)
            if row.get("language") != "fr":
                continue
            if args.openpii_region != "any" and row.get("region") != args.openpii_region:
                continue  # fr-BE, fr-CA, fr-CH use non-French formats: keep France by default
            text = row["source_text"]
            raw = [(m["start"], m["end"], m["label"]) for m in row["privacy_mask"]]
            raw = merge_runs(text, raw, {"GIVENNAME", "SURNAME"}, "PERSON", lambda g: g == " ")
            raw = merge_runs(text, raw, {"STREET", "BUILDINGNUM", "ZIPCODE"}, "ADDRESS", lambda g: bool(gap_ok(g)))
            mapped = [(s, e, OPENPII_MAP.get(lab, "OTHER") if lab not in FAMILIES else lab) for s, e, lab in raw]
            records.append({"id": f"openpii_fr:{row.get('uid', len(records))}", "source": src.name, "language": "fr",
                            "text": text, "spans": clean_spans(text, mapped)})
    log(f"openpii_fr: {len(records)} French records after scanning {scanned / 1e6:.0f} MB")
    return write_jsonl(src.name, records)


def convert_tab_en(src: Source, args: argparse.Namespace) -> dict[str, Any]:
    url = f"https://raw.githubusercontent.com/NorskRegnesentral/text-anonymization-benchmark/{src.revision}/echr_test.json"
    dest = RAW_DIR / "tab" / "echr_test.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        req = urllib.request.Request(url, headers={"User-Agent": "gdprguardian-eval/1.0"})
        with urllib.request.urlopen(req, timeout=300) as resp, dest.open("wb") as out:
            out.write(resp.read())
    docs = json.loads(dest.read_text(encoding="utf-8"))

    def gen() -> Iterator[dict[str, Any]]:
        for doc in docs[: args.tab_limit]:
            text = doc["text"]
            annotations = doc.get("annotations", {})
            first = next(iter(annotations.values()), {})
            raw = []
            for m in first.get("entity_mentions", []):
                if m.get("identifier_type") not in ("DIRECT", "QUASI"):
                    continue
                raw.append((m["start_offset"], m["end_offset"], TAB_MAP.get(m.get("entity_type", ""), "OTHER")))
            yield {"id": f"tab_en:{doc.get('doc_id', '')}", "source": src.name, "language": "en", "text": text,
                   "spans": clean_spans(text, raw)}

    return write_jsonl(src.name, gen())


CONVERTERS: dict[str, Callable[[Source, argparse.Namespace], dict[str, Any]]] = {
    "fr_pii_bench": convert_fr_pii_bench,
    "mapa_fr": convert_mapa_fr,
    "gretel_fr": convert_gretel_fr,
    "openpii_fr": convert_openpii_fr,
    "tab_en": convert_tab_en,
}


def write_sources_md(meta: dict[str, Any]) -> None:
    lines = [
        "# Public evaluation datasets / Jeux publics d'évaluation",
        "",
        "Downloaded at evaluation time by `tools/corpus/fetch_public.py` into `datasets/public/cache/` "
        "(git-ignored, never redistributed). Dev tooling only.",
        "",
        "| name | dataset | revision | licence | records | gold spans |",
        "|---|---|---|---|---:|---:|",
    ]
    for name, src in SOURCES.items():
        info = meta.get(name)
        if not info:
            continue
        lines.append(f"| {name} | [{src.title}]({src.url}) | `{src.revision[:12]}` | {src.licence} | "
                     f"{info['records']} | {info['spans']} |")
    lines += ["", "## Details and attribution", ""]
    for name, src in SOURCES.items():
        info = meta.get(name)
        if not info:
            continue
        labels = ", ".join(f"{k}: {v}" for k, v in info["labels"].items())
        lines += [f"### {name}", "", f"- URL: {src.url}", f"- Revision (full): `{src.revision}`",
                  f"- Licence: {src.licence}", f"- Attribution: {src.attribution}", f"- Notes: {src.notes}",
                  f"- Fetched: {info.get('fetched', '')}", f"- Spans per family: {labels}", ""]
    lines += ["## Rejected (licence)", "",
              "ai4privacy pii-masking-200k/300k/400k/500k (non-commercial or Llama licence), WikiNEuRal and "
              "MultiNERD (CC-BY-NC-SA), CATIE-AQ frenchNER (inherits NC sets), piimb (CC-BY-NC), E3C, Meddies.", ""]
    SOURCES_MD.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main() -> int:
    from datetime import UTC, datetime
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", nargs="*", choices=sorted(CONVERTERS), help="datasets to fetch (default: all French)")
    parser.add_argument("--tab", action="store_true", help="also fetch TAB (English, optional)")
    parser.add_argument("--openpii-limit", type=int, default=3000, help="max French OpenPII records")
    parser.add_argument("--openpii-scan-mb", type=int, default=1000, help="max MB streamed from OpenPII")
    parser.add_argument("--openpii-region", default="FR", help='OpenPII region of French records, or "any"')
    parser.add_argument("--pyarrow-path", default=None, help="extra sys.path entry providing pyarrow")
    parser.add_argument("--tab-limit", type=int, default=150, help="max TAB documents (test split)")
    args = parser.parse_args()

    names = args.only or [n for n in CONVERTERS if n != "tab_en"]
    if args.tab and "tab_en" not in names:
        names.append("tab_en")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    meta: dict[str, Any] = json.loads(META_PATH.read_text(encoding="utf-8")) if META_PATH.exists() else {}
    failures = 0
    for name in names:
        log(f"== {name}")
        try:
            info = CONVERTERS[name](SOURCES[name], args)
        except Exception as exc:  # report and continue with the other datasets
            log(f"FAILED {name}: {type(exc).__name__}: {exc}")
            failures += 1
            continue
        info["fetched"] = datetime.now(UTC).strftime("%Y-%m-%d")
        meta[name] = info
        log(f"   {info['records']} records, {info['spans']} spans")
        META_PATH.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    write_sources_md(meta)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
