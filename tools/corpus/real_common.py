"""Outils communs aux corpus réels (outil de dev, jamais livré) / shared helpers for the real corpora (dev only).

Règle de confidentialité / privacy rule: the documents built here come from open sources and may contain personal
data of real people (BODACC, BOAMP, debates, court decisions). They are written to a cache folder OUTSIDE the
repository (``--cache``, default ``$GDPRG_CORPORA_CACHE`` or ``~/.cache/gdprguardian-corpora``), used locally for
evaluation only, and never committed or republished. Only aggregate scores leave the machine.

Format of one record (JSONL, one per line):

    {"id", "source", "language", "text",
     "spans": [{"start", "end", "label", "text", "origin"}],   # gold, code-point offsets in "text"
     "ignore": [[start, end], ...],                            # zones left out of precision (unannotated free text)
     "meta": {...}}                                            # non-personal metadata only (family, year, split)

Labels are GDPR Guardian families. PERSONAL ones are expected to be masked; KEPT ones are kept by policy
(organisations, company identifiers, places, generic dates, other quasi-identifiers) and are reported apart.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "benchmarks" / "results"
USER_AGENT = "gdprguardian-eval/1.0 (+https://github.com/FlowLineIntegration/GDPRGuardian)"

PERSONAL = ("PERSON", "ADDRESS", "EMAIL", "PHONE", "NATIONAL_ID", "TAX_ID", "IBAN", "BANK_ACCOUNT", "CARD",
            "BIRTH_DATE", "ID", "URL", "IP")
KEPT = ("ORG", "ORG_ID", "LOCATION", "DATE", "OTHER")
FAMILIES = PERSONAL + KEPT


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


# --- dossiers / folders -------------------------------------------------------------------------------------

def default_cache() -> Path:
    env = os.environ.get("GDPRG_CORPORA_CACHE")
    return Path(env) if env else Path.home() / ".cache" / "gdprguardian-corpora"


def check_outside_repo(cache: Path) -> Path:
    """Refuse un cache dans le dépôt : les données personnelles n'y entrent jamais / never inside the repository."""
    cache = cache.resolve()
    try:
        cache.relative_to(ROOT.resolve())
    except ValueError:
        return cache
    raise SystemExit(f"--cache must be outside the repository ({ROOT}): personal data are never stored in it")


def raw_dir(cache: Path, source: str) -> Path:
    path = cache / "raw" / source
    path.mkdir(parents=True, exist_ok=True)
    return path


def corpus_path(cache: Path, name: str) -> Path:
    path = cache / "corpora"
    path.mkdir(parents=True, exist_ok=True)
    return path / f"{name}.jsonl"


# --- réseau / network ---------------------------------------------------------------------------------------

def http_get(url: str, *, tries: int = 6, timeout: int = 120, headers: dict[str, str] | None = None) -> bytes:
    """GET avec reprises (429 : Retry-After) ; décompresse le gzip / GET with retries, gzip-aware."""
    hdrs = {"User-Agent": USER_AGENT, **(headers or {})}
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=hdrs)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
            return gzip.decompress(data) if data[:2] == b"\x1f\x8b" else data
        except urllib.error.HTTPError as exc:
            if attempt == tries - 1 or exc.code in (400, 401, 403, 404):
                raise
            wait = float(exc.headers.get("Retry-After") or 0) if exc.code == 429 else 0.0
            time.sleep(max(wait, 2.0 * (attempt + 1)))
        except OSError:
            if attempt == tries - 1:
                raise
            time.sleep(2.0 * (attempt + 1))
    raise RuntimeError("unreachable")


def http_json(url: str, params: dict[str, Any] | None = None) -> Any:
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    return json.loads(http_get(url).decode("utf-8"))


def download(url: str, dest: Path, *, timeout: int = 600) -> Path:
    """Télécharge une fois (fichier .part puis renommage) / download once (.part then rename)."""
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp, part.open("wb") as out:
        while chunk := resp.read(1 << 20):
            out.write(chunk)
    part.replace(dest)
    return dest


# --- construction du texte et des zones / text and span building --------------------------------------------

@dataclass
class TextBuilder:
    """Assemble un texte en gardant les positions exactes des valeurs / builds text with exact value offsets."""

    parts: list[str] = field(default_factory=list)
    length: int = 0
    spans: list[tuple[int, int, str, str]] = field(default_factory=list)
    ignore: list[tuple[int, int]] = field(default_factory=list)

    def add(self, text: str, label: str | None = None, origin: str = "field", *,
            ignore: bool = False) -> tuple[int, int]:
        start = self.length
        self.parts.append(text)
        self.length += len(text)
        if label and text.strip():
            lead = len(text) - len(text.lstrip())
            trail = len(text) - len(text.rstrip())
            self.spans.append((start + lead, self.length - trail, label, origin))
        if ignore and text:
            self.ignore.append((start, self.length))
        return start, self.length

    def line(self, prefix: str, value: str | None, label: str | None = None, *, ignore: bool = False) -> None:
        """« Préfixe : valeur » puis fin de ligne ; rien si la valeur est vide / "Prefix: value" + newline."""
        if value is None or not str(value).strip():
            return
        self.add(prefix)
        self.add(str(value).strip(), label, ignore=ignore)
        self.add("\n")

    @property
    def text(self) -> str:
        return "".join(self.parts)


def find_all(text: str, value: str, *, word: bool = True, ignore_case: bool = False) -> list[tuple[int, int]]:
    """Toutes les occurrences exactes de `value`, bornées par des non-alphanumériques / exact occurrences."""
    value = value.strip()
    if not value:
        return []
    flags = re.IGNORECASE if ignore_case else 0
    body = re.escape(value)
    pattern = rf"(?<![^\W_]){body}(?![^\W_])" if word else body
    return [(m.start(), m.end()) for m in re.finditer(pattern, text, flags)]


# Civilités et titres retirés du début d'une zone PERSON (contrat des détecteurs : la civilité reste hors zone)
# Honorifics removed from the start of a PERSON span (detector contract: the title stays outside the span).
HONORIFIC = re.compile(  # utilisé avec .match(text, pos) : pas de « ^ » / used with .match(text, pos): no "^"
    r"(?:(?:M|MM|Mme|Mmes|Mlle|Mlles|Me|Mgr|Dr|Pr|Mr|Mrs|Ms|Sr|Sra|Srta|Dña|Dra|Sig|Sig\.ra|Dott|Dhr|Mevr|Prof)"
    r"\s*\.?|Monsieur|Madame|Mademoiselle|Maître|Docteur|Professeur|Miss|Sir|Lord|Lady|Herr|Frau|Doña|"
    r"Signor|Signora|Senhor|Senhora|monsieur|madame)\s+(?=\S)")


def trim_person(text: str, start: int, end: int) -> int:
    """Nouveau début d'une zone PERSON sans civilité (au moins un mot gardé) / start without honorific."""
    while True:
        m = HONORIFIC.match(text, start, end)
        if not m or m.end() >= end:
            return start
        start = m.end()


def resolve_spans(text: str, raw: Iterable[tuple[int, int, str, str]]) -> list[dict[str, Any]]:
    """Valide, dédoublonne et retire les chevauchements / validate, dedupe, remove overlaps.

    Priority on overlap: personal families first, then the longer span. Spans are trimmed of surrounding spaces,
    and PERSON spans of a leading honorific ("M.", "Mme", "Mr", "Dr"...).
    """
    items: list[tuple[int, int, str, str]] = []
    seen: set[tuple[int, int]] = set()
    for start, end, label, origin in raw:
        if not (0 <= start < end <= len(text)):
            continue
        while start < end and text[start].isspace():
            start += 1
        while end > start and text[end - 1].isspace():
            end -= 1
        if label == "PERSON":
            start = trim_person(text, start, end)
        if start < end and (start, end) not in seen:
            seen.add((start, end))
            items.append((start, end, label, origin))
    items.sort(key=lambda t: (t[2] not in PERSONAL, -(t[1] - t[0]), t[0]))
    taken = bytearray(len(text))
    kept: list[tuple[int, int, str, str]] = []
    for start, end, label, origin in items:
        if any(taken[start:end]):
            continue
        taken[start:end] = b"\x01" * (end - start)
        kept.append((start, end, label, origin))
    kept.sort()
    return [{"start": s, "end": e, "label": lab, "text": text[s:e], "origin": o} for s, e, lab, o in kept]


def merge_zones(zones: Iterable[tuple[int, int]]) -> list[list[int]]:
    out: list[list[int]] = []
    for start, end in sorted(zones):
        if out and start <= out[-1][1]:
            out[-1][1] = max(out[-1][1], end)
        elif start < end:
            out.append([start, end])
    return out


def record(rec_id: str, source: str, language: str, text: str, raw_spans: Iterable[tuple[int, int, str, str]],
           ignore: Iterable[tuple[int, int]] = (), meta: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"id": rec_id, "source": source, "language": language, "text": text,
            "spans": resolve_spans(text, raw_spans), "ignore": merge_zones(ignore), "meta": meta or {}}


# --- jetons BIO / BIO tokens --------------------------------------------------------------------------------

_NO_SPACE_BEFORE = set(",.;:!?)]}%»’”") | {"'s", "n't"}
_NO_SPACE_AFTER = set("([{«“‘")


def detokenize(tokens: list[str], no_space_after: list[bool] | None = None) -> tuple[str, list[tuple[int, int]]]:
    """Recolle des jetons en texte lisible et rend leurs positions / join tokens, return token offsets.

    With `no_space_after` (HIPE "NoSpaceAfter"), the original spacing is restored exactly; otherwise a light
    rule set avoids spaces before closing punctuation and after an apostrophe ("l'", "d'").
    """
    out: list[str] = []
    offsets: list[tuple[int, int]] = []
    pos = 0
    for i, tok in enumerate(tokens):
        if i:
            if no_space_after is not None:
                space = not no_space_after[i - 1]
            else:
                prev = tokens[i - 1]
                space = not (tok in _NO_SPACE_BEFORE or prev in _NO_SPACE_AFTER or prev.endswith(("'", "’")))
            if space:
                out.append(" ")
                pos += 1
        offsets.append((pos, pos + len(tok)))
        out.append(tok)
        pos += len(tok)
    return "".join(out), offsets


def bio_spans(tags: list[str]) -> list[tuple[int, int, str]]:
    """(premier jeton, dernier jeton exclu, type) depuis des étiquettes BIO / BIO tags to token spans.

    Accepts "B-X", "I-X", "E-X", "S-X" and bare "O"; an I- tag after O or another type starts a new span.
    """
    spans: list[tuple[int, int, str]] = []
    start = -1
    cur = ""
    for i, tag in enumerate([*tags, "O"]):
        tag = tag or "O"
        kind = tag[2:] if len(tag) > 2 and tag[1] in "-_" else ""
        prefix = tag[0] if kind else "O"
        if start >= 0 and (prefix in "OBS" or kind != cur):
            spans.append((start, i, cur))
            start = -1
        if prefix != "O" and start < 0:
            start, cur = i, kind
    return spans


# --- écriture / writing -------------------------------------------------------------------------------------

def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = spans = chars = 0
    by_label: dict[str, int] = {}
    tmp = path.with_name(path.name + ".part")
    with tmp.open("w", encoding="utf-8", newline="\n") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            count += 1
            chars += len(rec["text"])
            spans += len(rec["spans"])
            for sp in rec["spans"]:
                by_label[sp["label"]] = by_label.get(sp["label"], 0) + 1
    tmp.replace(path)
    return {"documents": count, "mentions": spans, "chars": chars, "labels": dict(sorted(by_label.items()))}


def read_jsonl(path: Path, limit: int | None = None) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            if limit is not None and i >= limit:
                return
            if line.strip():
                yield json.loads(line)


def update_manifest(cache: Path, name: str, info: dict[str, Any]) -> None:
    """Métadonnées non personnelles de chaque corpus construit / non-personal metadata of each built corpus."""
    path = cache / "corpora" / "manifest.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    data[name] = info
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")


def read_manifest(cache: Path) -> dict[str, Any]:
    path = cache / "corpora" / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


# --- normalisation pour la fuite littérale / normalisation for literal leaks --------------------------------

def canon(text: str) -> str:
    """NFKC, minuscules, espaces réduits, sans caractères de format / NFKC, casefold, collapsed spaces."""
    text = unicodedata.normalize("NFKC", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Cf")
    return re.sub(r"\s+", " ", text).strip().casefold()


def alnum_mask(text: str) -> bytearray:
    return bytearray(1 if ch.isalnum() else 0 for ch in text)


# --- partition dev / test / dev-test split ------------------------------------------------------------------

# Graine fixe, écrite avant toute modification des règles (25/10/2026) : les règles se conçoivent sur « dev »
# seulement, « test » ne sert qu'à la mesure. Fixed seed, written down before any rule change: rules are designed
# on "dev" only, "test" is for measurement only.
SPLIT_SEED = "gdprguardian-rules2-2026-10-25"
SPLITS = ("dev", "test")


def split_of(doc_id: str) -> str:
    """« dev » ou « test » : parité du premier mot de 32 bits de SHA-256(graine | id) / even -> dev, odd -> test."""
    digest = hashlib.sha256(f"{SPLIT_SEED}|{doc_id}".encode()).digest()
    return SPLITS[int.from_bytes(digest[:4], "big") & 1]
