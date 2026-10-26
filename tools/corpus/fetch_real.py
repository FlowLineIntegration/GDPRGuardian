"""Télécharge et convertit les corpus réels annotés (outil de dev, jamais livré).

Downloads and converts the real annotated corpora to the unified JSONL of real_common (dev tooling only):
ParlaMint-FR, Europeana Newspapers FR, HIPE-2022 NewsEye FR, MAPA (fr, de, es, it, nl, pt), MEDDOCAN (es),
German LER (de), TAB (en) and a Judilibre sample (negative control). BODACC and BOAMP have their own builders
(build_bodacc.py, build_boamp.py). Every source is pinned (revision, handle or DOI) in real_registry.py.

Everything lands in the cache folder OUTSIDE the repository (--cache); nothing is redistributed.

Usage:
    python tools/corpus/fetch_real.py --cache DIR                       # every corpus below
    python tools/corpus/fetch_real.py --cache DIR --only mapa_de meddocan_es
    python tools/corpus/fetch_real.py --cache DIR --only german_ler_de judilibre_fr --pyarrow-path DIR
"""

from __future__ import annotations

import argparse
import functools
import json
import random
import re
import sys
import tarfile
import zipfile
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.corpus.real_common import (  # noqa: E402
    bio_spans,
    check_outside_repo,
    corpus_path,
    default_cache,
    detokenize,
    download,
    log,
    raw_dir,
    record,
    update_manifest,
    write_jsonl,
)
from tools.corpus.real_registry import CORPORA  # noqa: E402

MAPA_REV = "bbb2a0157b760465002fd12a61af81b475cd387a"
LER_REV = "405b6923dfd2299da3d76a68220ee15a95bc1eab"
JUD_REV = "8019db1080cf6dc8a34d73ee44d704a8e90b558e"
HIPE_REV = "147f5bc3c7fb7e5c6b024a9ffd6503cd019fb9ea"
ENP_REV = "6bf838d23112c255fd81431b1187ab30ef6c2d90"
TAB_REV = "558e09e26d6b36f5f78440074e6a233946d98bd9"
PARLAMINT_URL = ("https://www.clarin.si/repository/xmlui/bitstream/handle/11356/2004/ParlaMint-FR.tgz"
                 "?sequence=13&isAllowed=y")
MEDDOCAN_URL = "https://zenodo.org/records/4279323/files/meddocan.zip?download=1"

# --- tables de correspondance / label maps ------------------------------------------------------------------

MAPA_OTHER_FINE = {"AGE", "ETHNIC CATEGORY", "MARITAL STATUS", "PROFESSION", "ROLE", "NATIONALITY", "TITLE"}
MAPA_LOCATION_FINE = {"CITY", "COUNTRY", "PLACE", "TERRITORY"}

MEDDOCAN_MAP = {
    "NOMBRE_SUJETO_ASISTENCIA": "PERSON", "NOMBRE_PERSONAL_SANITARIO": "PERSON", "CALLE": "ADDRESS",
    "CORREO_ELECTRONICO": "EMAIL", "NUMERO_TELEFONO": "PHONE", "NUMERO_FAX": "PHONE",
    "ID_SUJETO_ASISTENCIA": "ID", "ID_TITULACION_PERSONAL_SANITARIO": "ID", "ID_ASEGURAMIENTO": "NATIONAL_ID",
    "ID_CONTACTO_ASISTENCIAL": "ID", "ID_EMPLEO_PERSONAL_SANITARIO": "ID", "NUMERO_IDENTIF": "NATIONAL_ID",
    "URL_WEB": "URL", "DIREC_PROT_INTERNET": "IP", "IDENTIF_VEHICULOS_NRSERIE_PLACAS": "ID",
    "IDENTIF_DISPOSITIVOS_NRSERIE": "ID", "IDENTIF_BIOMETRICOS": "ID",
    "TERRITORIO": "LOCATION", "PAIS": "LOCATION", "FECHAS": "DATE", "HOSPITAL": "ORG", "INSTITUCION": "ORG",
    "CENTRO_SALUD": "ORG",
}  # EDAD, SEXO, FAMILIARES, PROFESION, OTROS -> OTHER

LER_NAMES = ["B-AN", "B-EUN", "B-GRT", "B-GS", "B-INN", "B-LD", "B-LDS", "B-LIT", "B-MRK", "B-ORG", "B-PER", "B-RR",
             "B-RS", "B-ST", "B-STR", "B-UN", "B-VO", "B-VS", "B-VT", "I-AN", "I-EUN", "I-GRT", "I-GS", "I-INN", "I-LD",
             "I-LDS", "I-LIT", "I-MRK", "I-ORG", "I-PER", "I-RR", "I-RS", "I-ST", "I-STR", "I-UN", "I-VO", "I-VS",
             "I-VT", "O"]
LER_MAP = {"PER": "PERSON", "RR": "PERSON", "AN": "PERSON", "STR": "ADDRESS", "ST": "LOCATION", "LD": "LOCATION",
           "LDS": "LOCATION", "ORG": "ORG", "UN": "ORG", "INN": "ORG", "GRT": "ORG", "MRK": "ORG"}
# GS, VO, EUN, VS, VT, RS, LIT (laws, regulations, case law, literature) -> OTHER

HIPE_MAP = {"pers": "PERSON", "per": "PERSON", "loc": "LOCATION", "org": "ORG", "time": "DATE", "prod": "OTHER",
            "humanprod": "OTHER"}
ENP_MAP = {"PER": "PERSON", "LOC": "LOCATION", "ORG": "ORG"}
TAB_MAP = {"PERSON": "PERSON", "ORG": "ORG", "LOC": "LOCATION", "DATETIME": "DATE"}


def hf_file(cache: Path, source: str, repo: str, filename: str, revision: str) -> Path:
    from huggingface_hub import hf_hub_download
    return Path(hf_hub_download(repo, filename, repo_type="dataset", revision=revision,
                                local_dir=raw_dir(cache, source)))


def _pyarrow(args: argparse.Namespace) -> Any:
    if args.pyarrow_path and args.pyarrow_path not in sys.path:
        sys.path.insert(0, args.pyarrow_path)
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise RuntimeError("needs pyarrow: pip install pyarrow (or pass --pyarrow-path DIR)") from exc
    return pq


def tokens_record(rec_id: str, source: str, lang: str, tokens: list[str], tags: list[str],
                  label_of: Callable[[str], str | None], no_space_after: list[bool] | None = None,
                  meta: dict[str, Any] | None = None) -> dict[str, Any]:
    text, offsets = detokenize(tokens, no_space_after)
    raw = []
    for ts, te, kind in bio_spans(tags):
        label = label_of(kind)
        if label:
            raw.append((offsets[ts][0], offsets[te - 1][1], label, "manual"))
    return record(rec_id, source, lang, text, raw, (), meta)


# --- MAPA ---------------------------------------------------------------------------------------------------

def _mapa_label(coarse: str, fine: str) -> str | None:
    coarse, fine = coarse.upper(), fine.upper()
    if coarse == "PERSON":
        return "OTHER" if fine in MAPA_OTHER_FINE else ("URL" if fine == "URL" else "PERSON")
    if coarse == "ORGANISATION":
        return "ORG"
    if coarse == "ADDRESS":
        return "LOCATION" if fine in MAPA_LOCATION_FINE else "ADDRESS"
    if coarse == "DATE":
        return "DATE"
    return None  # AMOUNT, TIME


def convert_mapa(cache: Path, lang: str, _args: argparse.Namespace) -> Iterator[dict[str, Any]]:
    docs: dict[str, list[dict[str, Any]]] = {}
    for split in ("train", "validation", "test"):
        path = hf_file(cache, "mapa", "joelniklaus/mapa", f"{split}.jsonl", MAPA_REV)
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                row = json.loads(line)
                if row.get("language") == lang:
                    docs.setdefault(f"{split}/{row['file_name']}", []).append(row)
    for doc_id, rows in docs.items():
        rows.sort(key=lambda r: r["sentence_number"])
        text = ""
        raw: list[tuple[int, int, str, str]] = []
        for row in rows:
            sent, offsets = detokenize(row["tokens"])
            base = len(text)
            coarse, fine = row["coarse_grained"], row["fine_grained"]
            for ts, te, kind in bio_spans(coarse):
                fine_tag = fine[ts].split("-", 1)[-1] if fine[ts] != "O" else ""
                label = _mapa_label(kind, fine_tag)
                if label:
                    raw.append((base + offsets[ts][0], base + offsets[te - 1][1], label, "manual"))
            text += sent + "\n"
        yield record(f"mapa_{lang}:{doc_id}", f"mapa_{lang}", lang, text, raw, (), {"split": doc_id.split("/")[0]})


# --- MEDDOCAN -----------------------------------------------------------------------------------------------

def parse_brat(ann: str) -> list[tuple[int, int, str]]:
    """Entités « T » d'un fichier .ann (fragments discontinus réunis) / brat T entities."""
    out = []
    for line in ann.splitlines():
        if not line.startswith("T") or "\t" not in line:
            continue
        _tid, info, *_rest = line.split("\t")
        kind, _, locs = info.partition(" ")
        bounds = [tuple(int(x) for x in frag.split()) for frag in locs.split(";") if frag.strip()]
        if bounds:
            out.append((min(b[0] for b in bounds), max(b[1] for b in bounds), kind))
    return out


def convert_meddocan(cache: Path, _args: argparse.Namespace) -> Iterator[dict[str, Any]]:
    path = download(MEDDOCAN_URL, raw_dir(cache, "meddocan") / "meddocan.zip")
    with zipfile.ZipFile(path) as zf:
        names = sorted(n for n in zf.namelist() if n.endswith(".ann") and "/brat/" in n)
        for name in names:
            split = name.split("/")[1]
            text = zf.read(name[:-4] + ".txt").decode("utf-8")
            raw = [(s, e, MEDDOCAN_MAP.get(kind, "OTHER"), "manual") for s, e, kind in parse_brat(
                zf.read(name).decode("utf-8"))]
            doc = name.rsplit("/", 1)[-1][:-4]
            yield record(f"meddocan:{split}/{doc}", "meddocan_es", "es", text, raw, (), {"split": split})


# --- German LER ---------------------------------------------------------------------------------------------

def convert_german_ler(cache: Path, args: argparse.Namespace) -> Iterator[dict[str, Any]]:
    pq = _pyarrow(args)
    path = hf_file(cache, "german_ler", "elenanereiss/german-ler", "data/test-00000-of-00001.parquet", LER_REV)
    table = pq.read_table(path)
    tag_column = "ner" if "ner" in table.column_names else "ner_tags"
    rows = table.select(["tokens", tag_column]).to_pylist()
    size = args.ler_sentences_per_doc
    for i in range(0, len(rows), size):
        chunk = rows[i: i + size]
        text = ""
        raw: list[tuple[int, int, str, str]] = []
        for row in chunk:
            tags = [LER_NAMES[t] if isinstance(t, int) else str(t) for t in row[tag_column]]
            sent, offsets = detokenize(list(row["tokens"]))
            base = len(text)
            for ts, te, kind in bio_spans(tags):
                raw.append((base + offsets[ts][0], base + offsets[te - 1][1], LER_MAP.get(kind, "OTHER"), "manual"))
            text += sent + "\n"
        yield record(f"german_ler:test/{i // size}", "german_ler_de", "de", text, raw, (), {"split": "test"})


# --- Europeana Newspapers FR --------------------------------------------------------------------------------

def convert_europeana(cache: Path, args: argparse.Namespace) -> Iterator[dict[str, Any]]:
    url = (f"https://raw.githubusercontent.com/EuropeanaNewspapers/ner-corpora/{ENP_REV}/"
           "enp_FR.bnf.bio/enp_FR.bnf.bio")
    path = download(url, raw_dir(cache, "europeana_fr") / "enp_FR.bnf.bio")
    tokens: list[str] = []
    tags: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.rsplit(" ", 1)
        if len(parts) == 2 and parts[0]:
            tokens.append(parts[0])
            tags.append(parts[1])
    size = args.enp_tokens_per_doc
    for i in range(0, len(tokens), size):
        yield tokens_record(f"europeana_fr:{i // size}", "europeana_fr", "fr", tokens[i: i + size],
                            tags[i: i + size], lambda k: ENP_MAP.get(k))


# --- HIPE-2022 NewsEye FR -----------------------------------------------------------------------------------

def parse_hipe(tsv: str) -> Iterator[tuple[str, list[str], list[str], list[bool], list[bool]]]:
    """(document_id, jetons, étiquettes, pas d'espace après, fin de ligne) par document / per document."""
    doc_id = ""
    tokens: list[str] = []
    tags: list[str] = []
    nospace: list[bool] = []
    eol: list[bool] = []
    for line in tsv.splitlines():
        if line.startswith("# hipe2022:document_id"):
            if tokens:
                yield doc_id, tokens, tags, nospace, eol
            doc_id = line.split("=", 1)[1].strip()
            tokens, tags, nospace, eol = [], [], [], []
            continue
        if not line.strip() or line.startswith("#") or line.startswith("TOKEN\t"):
            continue
        cols = line.split("\t")
        misc = cols[-1] if len(cols) > 1 else ""
        tokens.append(cols[0])
        tags.append(cols[1] if len(cols) > 1 else "O")
        nospace.append("NoSpaceAfter" in misc)
        eol.append("EndOfLine" in misc)
    if tokens:
        yield doc_id, tokens, tags, nospace, eol


def convert_hipe(cache: Path, _args: argparse.Namespace) -> Iterator[dict[str, Any]]:
    seen: set[str] = set()
    for split in ("train", "dev", "dev2", "test"):
        url = (f"https://raw.githubusercontent.com/hipe-eval/HIPE-2022-data/{HIPE_REV}/data/v2.1/newseye/fr/"
               f"HIPE-2022-v2.1-newseye-{split}-fr.tsv")
        path = download(url, raw_dir(cache, "hipe_newseye_fr") / f"newseye-{split}-fr.tsv")
        for doc_id, tokens, tags, nospace, eol in parse_hipe(path.read_text(encoding="utf-8")):
            key = f"{split}/{doc_id}"
            if key in seen:
                continue
            seen.add(key)
            text, offsets = detokenize(tokens, nospace)
            # fin de ligne sans césure : saut de ligne au lieu d'une espace / end of line: newline, not a space
            chars = list(text)
            for i, (end_of_line, glued) in enumerate(zip(eol, nospace, strict=True)):
                if end_of_line and not glued and i + 1 < len(offsets):
                    chars[offsets[i][1]] = "\n"
            text = "".join(chars)
            raw = [(offsets[ts][0], offsets[te - 1][1], HIPE_MAP.get(kind.split(".")[0].lower(), "OTHER"), "manual")
                   for ts, te, kind in bio_spans(tags)]
            yield record(f"hipe_newseye_fr:{key}", "hipe_newseye_fr", "fr", text, raw, (), {"split": split})


# --- TAB ----------------------------------------------------------------------------------------------------

def convert_tab(cache: Path, args: argparse.Namespace) -> Iterator[dict[str, Any]]:
    url = f"https://raw.githubusercontent.com/NorskRegnesentral/text-anonymization-benchmark/{TAB_REV}/echr_test.json"
    path = download(url, raw_dir(cache, "tab") / "echr_test.json")
    docs = json.loads(path.read_text(encoding="utf-8"))
    for doc in docs[: args.tab_limit]:
        text = doc["text"]
        first = next(iter(doc.get("annotations", {}).values()), {})
        raw = [(m["start_offset"], m["end_offset"], TAB_MAP.get(m.get("entity_type", ""), "OTHER"), "manual")
               for m in first.get("entity_mentions", []) if m.get("identifier_type") in ("DIRECT", "QUASI")]
        yield record(f"tab_en:{doc.get('doc_id', '')}", "tab_en", "en", text, raw, (), {"split": "test"})


# --- ParlaMint-FR -------------------------------------------------------------------------------------------

TEI = "{http://www.tei-c.org/ns/1.0}"
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"


def parlamint_persons(xml: bytes) -> dict[str, tuple[str, str, str]]:
    """xml:id -> (prénom, nom, sexe) depuis listPerson / person list."""
    from xml.etree import ElementTree as ET
    root = ET.fromstring(xml)
    out: dict[str, tuple[str, str, str]] = {}
    for person in root.iter(f"{TEI}person"):
        pid = person.get(XML_ID)
        name = person.find(f"{TEI}persName")
        if not pid or name is None:
            continue
        fore = " ".join((f.text or "").strip() for f in name.findall(f"{TEI}forename")).strip()
        sur = " ".join((s.text or "").strip() for s in name.findall(f"{TEI}surname")).strip()
        sex = person.find(f"{TEI}sex")
        out[pid] = (fore, sur, sex.get("value", "") if sex is not None else "")
    return out


def name_pattern(persons: dict[str, tuple[str, str, str]]) -> re.Pattern[str]:
    """Formes exactes cherchées dans le texte / exact forms searched in speeches.

    "Forename Surname", and civility + surname ("M. de Exemple", "Mme Essai", "monsieur Testeur").
    """
    forms: set[str] = set()
    for fore, sur, _sex in persons.values():
        if not sur or len(sur) < 3:
            continue
        if fore:
            forms.add(f"{fore} {sur}")
        for civ in ("M.", "Mme", "Monsieur", "Madame", "monsieur", "madame", "Mlle"):
            forms.add(f"{civ} {sur}")
    alternation = "|".join(re.escape(f) for f in sorted(forms, key=len, reverse=True))
    return re.compile(rf"(?<![^\W_])(?:{alternation})(?![^\W_])")


def _seg_text(elem: Any) -> str:
    return " ".join("".join(elem.itertext()).split())


def parlamint_documents(sitting: bytes, persons: dict[str, tuple[str, str, str]], pattern: re.Pattern[str],
                        sitting_id: str, max_chars: int) -> Iterator[dict[str, Any]]:
    """Comptes rendus découpés en documents de taille bornée / minutes cut into bounded documents."""
    from xml.etree import ElementTree as ET
    root = ET.fromstring(sitting)
    blocks: list[tuple[str, str, bool]] = []  # (speaker label, speech, label is a name)
    for u in root.iter(f"{TEI}u"):
        who = (u.get("who") or "").lstrip("#")
        segs = [_seg_text(s) for s in u.iter(f"{TEI}seg")]
        speech = " ".join(s for s in segs if s)
        if not speech:
            continue
        fore, sur, sex = persons.get(who, ("", "", ""))
        chair = "#chair" in (u.get("ana") or "")
        if chair:
            label, is_name = ("Mme la présidente" if sex == "F" else "M. le président"), False
        elif sur:
            label, is_name = f"{'Mme' if sex == 'F' else 'M.'} {fore} {sur}".replace("  ", " "), True
        else:
            label, is_name = "", False
        blocks.append((label, speech, is_name))
    part = 0
    text = ""
    raw: list[tuple[int, int, str, str]] = []

    def flush() -> Iterator[dict[str, Any]]:
        nonlocal text, raw, part
        if text:
            yield record(f"parlamint_fr:{sitting_id}/{part}", "parlamint_fr", "fr", text, raw, (),
                         {"sitting": sitting_id})
            part += 1
        text, raw = "", []

    for label, speech, is_name in blocks:
        if text and len(text) + len(speech) > max_chars:
            yield from flush()
        if label:
            start = len(text)
            civ = label.split(" ", 1)[0]
            if is_name:
                raw.append((start + len(civ) + 1, start + len(label), "PERSON", "speaker"))
            text += f"{label}. "
        base = len(text)
        for m in pattern.finditer(speech):
            match = m.group(0)
            civ = match.split(" ", 1)[0]
            offset = len(civ) + 1 if civ in ("M.", "Mme", "Monsieur", "Madame", "monsieur", "madame", "Mlle") else 0
            raw.append((base + m.start() + offset, base + m.end(), "PERSON", "mention"))
        text += speech + "\n\n"
    yield from flush()


def convert_parlamint(cache: Path, args: argparse.Namespace) -> Iterator[dict[str, Any]]:
    path = download(PARLAMINT_URL, raw_dir(cache, "parlamint_fr") / "ParlaMint-FR.tgz", timeout=3600)
    with tarfile.open(path, "r:gz") as tf:
        members = [m for m in tf.getmembers() if m.isfile()]
        persons_member = next(m for m in members if m.name.endswith("ParlaMint-FR-listPerson.xml"))
        persons = parlamint_persons(tf.extractfile(persons_member).read())
        pattern = name_pattern(persons)
        sittings = sorted(m.name for m in members
                          if re.search(r"/\d{4}/ParlaMint-FR_[^/]+\.xml$", m.name) and ".ana" not in m.name)
        rng = random.Random(args.seed)
        chosen = sorted(rng.sample(sittings, min(args.parlamint_sittings, len(sittings))))
        by_name = {m.name: m for m in members}
        for name in chosen:
            sitting_id = name.rsplit("/", 1)[-1][:-4]
            docs = list(parlamint_documents(tf.extractfile(by_name[name]).read(), persons, pattern, sitting_id,
                                            args.parlamint_chars))
            rng_s = random.Random(f"{args.seed}:{sitting_id}")
            yield from sorted(rng_s.sample(docs, min(args.parlamint_docs_per_sitting, len(docs))),
                              key=lambda d: d["id"])


# --- Judilibre (témoin négatif) / negative control ----------------------------------------------------------

def convert_judilibre(cache: Path, args: argparse.Namespace) -> Iterator[dict[str, Any]]:
    """Échantillon des groupes de lignes les plus récents de chaque fichier parquet / latest row groups."""
    pq = _pyarrow(args)
    from huggingface_hub import HfFileSystem
    fs = HfFileSystem()
    rng = random.Random(args.seed)
    for fname in ("cour_de_cassation", "cour_d_appel", "tribunal_judiciaire"):
        local = raw_dir(cache, "judilibre") / f"{fname}_sample_{args.judilibre_per_court}.jsonl"
        if not local.exists():
            path = f"datasets/antoinejeannot/jurisprudence@{JUD_REV}/{fname}.parquet"
            with fs.open(path, "rb") as fh:
                pf = pq.ParquetFile(fh)
                cols = [c for c in ("id", "decision_date", "jurisdiction", "chamber", "type", "text")
                        if c in pf.schema_arrow.names]
                rows: list[dict[str, Any]] = []
                for group in range(pf.num_row_groups - 1, -1, -1):
                    table = pf.read_row_group(group, columns=cols).to_pylist()
                    rows.extend(r for r in table if r.get("text") and str(r.get("decision_date") or "") >= "2022")
                    if len(rows) >= args.judilibre_per_court * 4:
                        break
            rows.sort(key=lambda r: str(r.get("id")))
            picked = rng.sample(rows, min(args.judilibre_per_court, len(rows)))
            with local.open("w", encoding="utf-8", newline="\n") as out:
                for r in picked:
                    out.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
        with local.open(encoding="utf-8") as fh:
            for line in fh:
                r = json.loads(line)
                text = str(r["text"])[: args.judilibre_max_chars]
                yield record(f"judilibre:{fname}/{r.get('id')}", "judilibre_fr", "fr", text, [], (),
                             {"court": fname, "date": str(r.get("decision_date"))[:10]})


def convert_mapa_lang(lang: str, cache: Path, args: argparse.Namespace) -> Iterator[dict[str, Any]]:
    return convert_mapa(cache, lang, args)


CONVERTERS: dict[str, Callable[[Path, argparse.Namespace], Iterator[dict[str, Any]]]] = {
    "parlamint_fr": convert_parlamint,
    "europeana_fr": convert_europeana,
    "hipe_newseye_fr": convert_hipe,
    **{f"mapa_{lang}": functools.partial(convert_mapa_lang, lang) for lang in ("fr", "de", "es", "it", "nl", "pt")},
    "meddocan_es": convert_meddocan,
    "german_ler_de": convert_german_ler,
    "tab_en": convert_tab,
    "judilibre_fr": convert_judilibre,
}


def main() -> int:
    from datetime import UTC, datetime
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cache", type=Path, default=default_cache(), help="cache folder, outside the repository")
    parser.add_argument("--only", nargs="*", choices=sorted(CONVERTERS), help="corpora to build (default: all)")
    parser.add_argument("--pyarrow-path", default=None, help="extra sys.path entry providing pyarrow")
    parser.add_argument("--seed", type=int, default=20261025)
    parser.add_argument("--parlamint-sittings", type=int, default=60)
    parser.add_argument("--parlamint-docs-per-sitting", type=int, default=5)
    parser.add_argument("--parlamint-chars", type=int, default=4000)
    parser.add_argument("--enp-tokens-per-doc", type=int, default=400)
    parser.add_argument("--ler-sentences-per-doc", type=int, default=20)
    parser.add_argument("--tab-limit", type=int, default=1000)
    parser.add_argument("--judilibre-per-court", type=int, default=100)
    parser.add_argument("--judilibre-max-chars", type=int, default=60000)
    args = parser.parse_args()
    cache = check_outside_repo(args.cache)
    failures = 0
    for name in args.only or list(CONVERTERS):
        log(f"== {name}")
        try:
            info = write_jsonl(corpus_path(cache, name), CONVERTERS[name](cache, args))
        except Exception as exc:  # signalé, on continue / reported, continue with the others
            log(f"FAILED {name}: {type(exc).__name__}: {exc}")
            failures += 1
            continue
        meta = CORPORA[name]
        info.update({"source": meta.url, "revision": meta.revision, "licence": meta.licence,
                     "fetched": datetime.now(UTC).strftime("%Y-%m-%d")})
        update_manifest(cache, name, info)
        log(f"   {info['documents']} documents, {info['mentions']} gold spans {info['labels']}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
