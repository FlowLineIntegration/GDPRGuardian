"""Schéma du corpus annoté, inspiré de TAB / annotated corpus schema, TAB-inspired.

Positions en points de code du texte ORIGINAL ; une mention = une zone, plusieurs mentions = une entité.
Offsets are code points of the ORIGINAL text; one mention = one span, several mentions = one entity.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DIRECT = "DIRECT"
QUASI = "QUASI"
NO_MASK = "NO_MASK"
IDENTIFIER_TYPES = (DIRECT, QUASI, NO_MASK)

# Libellés de référence ; mêmes clés que les libellés de Gardien RGPD quand ils existent.
# Gold labels; same keys as GDPR Guardian labels where they exist (typed comparison is then a plain equality).
GOLD_LABELS: dict[str, str] = {
    "PERSON": DIRECT,
    "EMAIL": DIRECT,
    "PHONE": DIRECT,
    "ADDRESS": DIRECT,
    "NIR": DIRECT,
    "IBAN": DIRECT,
    "RIB": DIRECT,
    "RIB_SPLIT": DIRECT,       # RIB éclaté en champs (banque, guichet, compte, clé) / RIB split into fields
    "CARD": DIRECT,
    "SIRET": DIRECT,           # entrepreneur individuel uniquement / sole traders only
    "SIREN": DIRECT,
    "VAT": DIRECT,
    "TAX_ID": DIRECT,
    "PASSPORT": DIRECT,
    "ID_CARD": DIRECT,
    "PLATE": DIRECT,
    "RPPS": DIRECT,
    "CAF": DIRECT,
    "FRANCE_TRAVAIL": DIRECT,
    "IP": DIRECT,
    "BIRTH_DATE": QUASI,
    "LOCATION": QUASI,
    "ORG": QUASI,
    "ID": QUASI,               # n° client, n° IPP, matricule / customer, patient, staff numbers
    # Leurres : ne doivent PAS être masqués / decoys: must NOT be masked.
    "AMOUNT": NO_MASK,
    "ORDER_NUMBER": NO_MASK,
    "INVOICE_NUMBER": NO_MASK,
    "LEGAL_REF": NO_MASK,
    "EVENT_DATE": NO_MASK,
    "PRODUCT_REF": NO_MASK,
    "CASE_NUMBER": NO_MASK,
    "COMPANY_ID": NO_MASK,     # SIREN/SIRET/TVA d'une personne morale / legal-entity identifiers
    "FACILITY_ID": NO_MASK,    # FINESS d'un établissement / facility identifier
    "BIC": NO_MASK,
    "VERSION": NO_MASK,
    "TICKET": NO_MASK,
}

# Identifiants à clé ou structurels visés par le test de fumée / checksum or structural ids of the smoke test.
CHECKSUM_LABELS = frozenset({"NIR", "IBAN", "RIB", "SIRET", "CARD", "EMAIL"})


@dataclass(frozen=True, slots=True)
class GoldSpan:
    """Mention annotée / annotated mention."""

    start: int
    end: int
    label: str
    entity_id: str
    identifier_type: str
    mutation: str | None = None


@dataclass(slots=True)
class Document:
    """Document annoté / annotated document."""

    doc_id: str
    kind: str
    text: str
    spans: tuple[GoldSpan, ...]
    language: str = "fr"
    mutation: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    def check(self) -> None:
        """Vérifie les invariants (bornes, ordre, disjonction, rognage) / checks invariants."""
        previous_end = 0
        for span in self.spans:
            if not 0 <= span.start < span.end <= len(self.text):
                raise ValueError(f"{self.doc_id}: zone hors bornes / span out of bounds {span}")
            if span.start < previous_end:
                raise ValueError(f"{self.doc_id}: zones non triées ou chevauchantes / overlapping spans")
            value = self.text[span.start:span.end]
            if value != value.strip():
                raise ValueError(f"{self.doc_id}: zone non rognée / untrimmed span {span}")
            if span.label not in GOLD_LABELS or span.identifier_type not in IDENTIFIER_TYPES:
                raise ValueError(f"{self.doc_id}: libellé inconnu / unknown label {span.label}")
            previous_end = span.end

    def to_json(self) -> dict[str, Any]:
        """Forme JSONL ; `span_text` permet de vérifier les positions à la relecture / `span_text` checks offsets."""
        return {
            "doc_id": self.doc_id,
            "kind": self.kind,
            "language": self.language,
            "mutation": self.mutation,
            "meta": self.meta,
            "text": self.text,
            "spans": [
                {
                    "start": s.start,
                    "end": s.end,
                    "label": s.label,
                    "entity_id": s.entity_id,
                    "identifier_type": s.identifier_type,
                    "mutation": s.mutation,
                    "span_text": self.text[s.start:s.end],
                }
                for s in self.spans
            ],
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Document:
        text = data["text"]
        spans = []
        for raw in data["spans"]:
            span = GoldSpan(raw["start"], raw["end"], raw["label"], raw["entity_id"], raw["identifier_type"],
                            raw.get("mutation"))
            if "span_text" in raw and text[span.start:span.end] != raw["span_text"]:
                raise ValueError(f"{data['doc_id']}: span_text incohérent / span_text mismatch")
            spans.append(span)
        doc = cls(data["doc_id"], data["kind"], text, tuple(spans), data.get("language", "fr"),
                  data.get("mutation"), data.get("meta", {}))
        doc.check()
        return doc


def write_jsonl(documents: Iterable[Document], path: str | Path) -> int:
    """Écrit un document JSON par ligne (UTF-8, ordre stable) / writes one JSON document per line."""
    count = 0
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        for doc in documents:
            handle.write(json.dumps(doc.to_json(), ensure_ascii=False, sort_keys=True))
            handle.write("\n")
            count += 1
    return count


def read_jsonl(path: str | Path) -> Iterator[Document]:
    """Relit et vérifie chaque document (positions, `span_text`) / reads back and checks every document."""
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield Document.from_json(json.loads(line))
