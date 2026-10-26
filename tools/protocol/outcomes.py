"""Note d'un document rendu par le service, et agrégats additifs / scoring one service output, additive aggregates.

Deux notations, côte à côte, jamais de texte conservé :
- l'issue PROTOCOLE (indice de confiance, rappel des mentions) : mentions d'identifiants directs du gold ayant au
  moins un caractère alphanumérique, et combien n'ont AUCUN caractère peut-être visible (borne prudente de
  l'alignement) ; un document fuit dès qu'une mention n'est pas entièrement masquée ;
- les mesures de tools.eval (corpus synthétiques, `score_document`) et de tools.corpus (corpus réels,
  `doc_stats`), appliquées aux zones masquées reconstruites, pour les autres chiffres publiés et le contrôle croisé.

Two scorings side by side, no text ever kept: the PROTOCOL outcome (confidence index, mention recall) and the
tools.eval / tools.corpus measures applied to the rebuilt masked zones (other published figures, cross-check).
"""

from __future__ import annotations

import base64
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, fields
from typing import Any

from tools.corpus.evaluate_real import BASE_FIELDS, doc_stats
from tools.corpus.real_common import PERSONAL
from tools.eval.metrics import Masked, Tally, score_document, significant_mask
from tools.eval.schema import DIRECT, Document
from tools.protocol.align import Alignment

REAL_FIELDS: tuple[str, ...] = tuple(BASE_FIELDS) + tuple(f"{p}_{f}" for f in PERSONAL for p in ("g", "f"))
_SEP = "|"


@dataclass(frozen=True, slots=True)
class Outcome:
    """Issue protocole d'un document / protocol outcome of one document."""

    mentions: int                 # mentions directes notées / scored direct mentions
    masked: int                   # dont entièrement masquées / of which fully masked
    labels: tuple[tuple[str, bool], ...]   # (libellé gold, entièrement masquée) par mention / per mention
    ambiguous: bool = False       # l'issue prudente diffère du placement représentatif / outcome depends on placement

    @property
    def leak(self) -> bool:
        return self.masked < self.mentions


def direct_outcome(text: str, gold: Iterable[tuple[int, int, str]], visible: bytearray,
                   representative: bytearray | None = None) -> Outcome:
    """Issue protocole : `gold` = (début, fin, libellé) des mentions directes ; `visible` = 1 si peut-être lisible.

    Protocol outcome: `gold` = (start, end, label) of the direct mentions; `visible` = 1 where possibly readable.
    `representative` (facultatif) : visibilité du placement représentatif, pour compter les documents dont l'issue
    dépend du placement / optional visibility of the representative placement, to count placement-dependent docs.
    """
    sig = significant_mask(text)
    size = len(text)
    sig_i = int.from_bytes(sig, "big")
    seen = (sig_i & int.from_bytes(visible, "big")).to_bytes(size, "big") if size else b""
    rep = ((sig_i & int.from_bytes(representative, "big")).to_bytes(size, "big")
           if representative is not None and size else None)
    mentions = masked = 0
    rows: list[tuple[str, bool]] = []
    differs = False
    for start, end, label in gold:
        if not sig[start:end].count(1):
            continue  # aucun caractère alphanumérique : rien à masquer / nothing alphanumeric to mask
        fully = not seen[start:end].count(1)
        mentions += 1
        masked += fully
        rows.append((label, fully))
        if rep is not None and fully != (not rep[start:end].count(1)):
            differs = True
    return Outcome(mentions, masked, tuple(rows), differs)


def representative_visible(text: str, alignment: Alignment) -> bytearray:
    """Visibilité du seul placement représentatif (complément des zones masquées) / representative visibility."""
    visible = bytearray(b"\x01") * len(text)
    for start, end, _ in alignment.masked:
        visible[start:end] = b"\x00" * (end - start)
    return visible


# --- Cellules d'agrégats / aggregate cells ---------------------------------------------------------------------------


def _tally_to_json(tally: Tally) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for f in fields(tally):
        value = getattr(tally, f.name)
        if isinstance(value, list):
            continue  # exemples avec valeurs : jamais conservés / examples with values: never kept
        if isinstance(value, Counter):
            out[f.name] = {(_SEP.join(k) if isinstance(k, tuple) else k): v for k, v in sorted(value.items(), key=str)}
        else:
            out[f.name] = value
    return out


def _tally_from_json(data: Mapping[str, Any]) -> Tally:
    tally = Tally()
    for f in fields(tally):
        if f.name not in data:
            continue
        current = getattr(tally, f.name)
        if isinstance(current, Counter):
            items = data[f.name].items()
            pairs = f.name.startswith("mutation_") or f.name == "confusion"
            current.update({(tuple(k.split(_SEP)) if pairs else k): v for k, v in items})
        else:
            setattr(tally, f.name, data[f.name])
    return tally


@dataclass(slots=True)
class Cell:
    """Agrégats additifs d'un sous-ensemble (famille, graine, opérateur, corpus × moitié) / additive aggregates."""

    docs: int = 0                  # documents envoyés / documents sent
    chars: int = 0
    no_direct: int = 0             # documents sans mention directe (hors indice) / without direct mention
    errors: Counter[str] = field(default_factory=Counter)
    hist: Counter[tuple[int, int]] = field(default_factory=Counter)   # (mentions, masquées) -> documents
    label_mentions: Counter[str] = field(default_factory=Counter)
    label_masked: Counter[str] = field(default_factory=Counter)
    ambiguous_docs: int = 0        # issue dépendant du placement (comptée prudente) / placement-dependent outcome
    ambiguous_segments: int = 0
    placeholders: int = 0
    tally: Tally | None = None     # tools.eval (synthétiques) / tools.eval (synthetic)
    real: Counter[str] = field(default_factory=Counter)               # tools.corpus doc_stats, sommes / sums
    vectors: list[list[int]] = field(default_factory=list)            # doc_stats par document (corpus réels)

    def add_outcome(self, outcome: Outcome) -> None:
        if outcome.mentions == 0:
            self.no_direct += 1
            return
        self.hist[(outcome.mentions, outcome.masked)] += 1
        for label, fully in outcome.labels:
            self.label_mentions[label] += 1
            self.label_masked[label] += fully
        self.ambiguous_docs += outcome.ambiguous

    def add_failure(self, kind: str, mentions: int, labels: Sequence[str]) -> None:
        """Document sans sortie exploitable : compté comme fuite, toutes mentions non masquées (prudent).

        A document without a usable output counts as a leak with every mention unmasked (conservative).
        """
        self.errors[kind] += 1
        if mentions == 0:
            self.no_direct += 1
            return
        self.hist[(mentions, 0)] += 1
        for label in labels:
            self.label_mentions[label] += 1

    def merge(self, other: Cell) -> Cell:
        self.docs += other.docs
        self.chars += other.chars
        self.no_direct += other.no_direct
        self.errors.update(other.errors)
        self.hist.update(other.hist)
        self.label_mentions.update(other.label_mentions)
        self.label_masked.update(other.label_masked)
        self.ambiguous_docs += other.ambiguous_docs
        self.ambiguous_segments += other.ambiguous_segments
        self.placeholders += other.placeholders
        if other.tally is not None:
            if self.tally is None:
                self.tally = Tally()
            self.tally.merge(other.tally)
        self.real.update(other.real)
        self.vectors.extend(other.vectors)
        return self

    # Index et rappel / index and recall
    @property
    def scored(self) -> int:
        return sum(self.hist.values())

    @property
    def passed(self) -> int:
        return sum(n for (m, k), n in self.hist.items() if k == m)

    @property
    def mention_total(self) -> int:
        return sum(m * n for (m, _), n in self.hist.items())

    @property
    def mention_masked(self) -> int:
        return sum(k * n for (_, k), n in self.hist.items())

    def to_json(self) -> dict[str, Any]:
        return {
            "docs": self.docs, "chars": self.chars, "no_direct": self.no_direct, "errors": dict(self.errors),
            "hist": [[m, k, n] for (m, k), n in sorted(self.hist.items())],
            "label_mentions": dict(sorted(self.label_mentions.items())),
            "label_masked": dict(sorted(self.label_masked.items())),
            "ambiguous_docs": self.ambiguous_docs, "ambiguous_segments": self.ambiguous_segments,
            "placeholders": self.placeholders,
            "tally": _tally_to_json(self.tally) if self.tally is not None else None,
            "real": dict(sorted(self.real.items())), "vectors": self.vectors,
        }

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> Cell:
        return cls(
            docs=data["docs"], chars=data["chars"], no_direct=data["no_direct"], errors=Counter(data["errors"]),
            hist=Counter({(m, k): n for m, k, n in data["hist"]}), label_mentions=Counter(data["label_mentions"]),
            label_masked=Counter(data["label_masked"]), ambiguous_docs=data["ambiguous_docs"],
            ambiguous_segments=data["ambiguous_segments"], placeholders=data["placeholders"],
            tally=_tally_from_json(data["tally"]) if data.get("tally") is not None else None,
            real=Counter(data["real"]), vectors=[list(v) for v in data["vectors"]])


def merge_cells(cells: Iterable[Cell]) -> Cell:
    total = Cell()
    for cell in cells:
        total.merge(cell)
    return total


# --- Notation d'un document / scoring one document -------------------------------------------------------------------


def score_synthetic(cell: Cell, doc: Document, output: str, alignment: Alignment, label_keys: Mapping[str, str],
                    baseline: Sequence[bool] | None = None) -> tuple[list[bool], int]:
    """Document synthétique : issue protocole + `score_document` de tools.eval ; rend (drapeaux par zone, fuite).

    Synthetic document: protocol outcome + tools.eval `score_document`; returns (per-span flags, the baseline of the
    red-team survival; leak bit). Les listes d'exemples (valeurs) sont vidées : jamais conservées / examples dropped.
    """
    gold = [(s.start, s.end, s.label) for s in doc.spans if s.identifier_type == DIRECT]
    outcome = direct_outcome(doc.text, gold, alignment.maybe_visible, representative_visible(doc.text, alignment))
    masked = [Masked(start, end, label_keys.get(label, label), "service") for start, end, label in alignment.masked]
    score = score_document(doc, masked, output, baseline)
    score.tally.misses.clear()
    score.tally.false_masks.clear()
    # Tout est calculé : la cellule ne change qu'à partir d'ici (une exception plus haut ne laisse rien à moitié
    # compté). Everything is computed: the cell only changes from here (an exception above leaves nothing half-counted).
    cell.add_outcome(outcome)
    cell.ambiguous_segments += alignment.ambiguous_segments
    cell.placeholders += alignment.placeholders
    if cell.tally is None:
        cell.tally = Tally()
    cell.tally.merge(score.tally)
    return score.masked, int(outcome.leak)


def score_real(cell: Cell, record: Mapping[str, Any], output: str, alignment: Alignment,
               direct_labels: frozenset[str]) -> int:
    """Document réel : issue protocole + `doc_stats` de tools.corpus (sommes et vecteur) ; rend le bit de fuite.

    Real document: protocol outcome + tools.corpus `doc_stats` (sums and per-document vector of integers); returns
    the leak bit.
    """
    text = record["text"]
    gold = [(g["start"], g["end"], g["label"]) for g in record["spans"] if g["label"] in direct_labels]
    outcome = direct_outcome(text, gold, alignment.maybe_visible, representative_visible(text, alignment))
    stats = doc_stats(record, [(start, end) for start, end, _ in alignment.masked], output, PERSONAL)
    vector = [stats[name] for name in REAL_FIELDS]
    # La cellule ne change qu'une fois tout calculé / the cell changes only once everything is computed.
    cell.add_outcome(outcome)
    cell.ambiguous_segments += alignment.ambiguous_segments
    cell.placeholders += alignment.placeholders
    cell.real.update(stats)
    cell.vectors.append(vector)
    return int(outcome.leak)


def real_failure(cell: Cell, record: Mapping[str, Any], kind: str, direct_labels: frozenset[str]) -> int:
    """Échec d'un document réel, compté comme fuite ; rend le bit de fuite / failure counted as a leak; leak bit."""
    labels = [g["label"] for g in record["spans"] if g["label"] in direct_labels and _has_alnum(record["text"], g)]
    cell.add_failure(kind, len(labels), labels)
    return int(bool(labels))


def synthetic_failure(cell: Cell, doc: Document, kind: str) -> int:
    """Échec d'un document synthétique, compté comme fuite ; rend le bit de fuite / failure as a leak; leak bit."""
    sig = significant_mask(doc.text)
    labels = [s.label for s in doc.spans if s.identifier_type == DIRECT and sig[s.start:s.end].count(1)]
    cell.add_failure(kind, len(labels), labels)
    return int(bool(labels))


def _has_alnum(text: str, span: Mapping[str, Any]) -> bool:
    return any(ch.isalnum() for ch in text[span["start"]:span["end"]])


# --- Bits par document (audit) / per-document bits (audit) -----------------------------------------------------------


def pack_bits(bits: Sequence[int]) -> str:
    """Bits 0/1 -> base64 (1 bit par document, ordre du plan) / 0-1 bits -> base64, one bit per document."""
    raw = bytearray((len(bits) + 7) // 8)
    for i, bit in enumerate(bits):
        if bit:
            raw[i >> 3] |= 0x80 >> (i & 7)
    return base64.b64encode(bytes(raw)).decode("ascii")


def unpack_bits(data: str, count: int) -> list[int]:
    raw = base64.b64decode(data)
    return [(raw[i >> 3] >> (7 - (i & 7))) & 1 for i in range(count)]
