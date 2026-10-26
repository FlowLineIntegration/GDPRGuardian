"""Types publics du moteur / public engine types."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

# Priorités de résolution des chevauchements / overlap-resolution priorities.
PRIORITY_VALIDATED = 100   # clé de contrôle forte / strong checksum (tier A)
PRIORITY_STRUCTURAL = 95   # e-mail, IP, URL… / structural formats
PRIORITY_LENIENT = 85      # tier L
PRIORITY_CONTEXT = 80      # clé faible + contexte / weak checksum + context (tier B)
PRIORITY_CONTEXT_ONLY = 70 # contexte seul / context only (tier C)
PRIORITY_HEURISTIC = 60    # listes de noms, adresses / gazetteers, addresses
PRIORITY_NER = 55          # modèle NER / NER model
PRIORITY_PROPAGATED = 50   # occurrences propagées / propagated occurrences

TIERS = ("A", "B", "C", "L")

# Entités dont les chevauchements de même type fusionnent / entities merged when overlapping.
MERGEABLE_ENTITIES = frozenset({"PERSON", "ORG", "ADDRESS", "LOCATION"})


@dataclass(slots=True)
class Span:
    """Zone détectée, en positions de caractères / detected zone, character offsets."""

    start: int
    end: int
    entity: str
    label: str
    source: str
    score: float = 1.0
    priority: int = PRIORITY_HEURISTIC
    value: str | None = None
    personal: bool = True
    forms: tuple[str, ...] = ()
    propagate: bool = False
    # Raison propre à la règle, si elle précise celle du détecteur (`explain`) : « civil_status_nearby »,
    # « street_and_number »… ; jamais la valeur. Rule-specific reason refining the detector's one, never the value.
    reason: str | None = None

    @property
    def length(self) -> int:
        return self.end - self.start

    def to_dict(self, text: str | None = None) -> dict[str, Any]:
        data = {
            "start": self.start,
            "end": self.end,
            "entity": self.entity,
            "label": self.label,
            "source": self.source,
            "score": round(self.score, 3),
            "personal": self.personal,
        }
        if text is not None:
            data["text"] = text[self.start:self.end]
        return data


class _DeferredSpans:
    """Champ `spans` d'`Analysis` : une liste, ou construite par le moteur natif à la première lecture.

    `Analysis.spans`: a list, or built by the native engine on first read. Champ-descripteur de dataclass :
    `fields`, `asdict`, `replace`, l'égalité et la représentation le lisent comme un attribut ordinaire / a
    dataclass descriptor field, read like a plain attribute by `fields`, `asdict`, `replace`, eq and repr.
    """

    __slots__ = ()

    def __get__(self, analysis: Analysis | None, owner: type | None = None) -> list[Span]:
        if analysis is None:
            raise AttributeError("spans")  # champ obligatoire, sans défaut / required field, no default
        pending = analysis._pending
        if pending is not None:
            analysis._spans, analysis._pending = pending(), None
        return analysis._spans

    def __set__(self, analysis: Analysis, spans: list[Span]) -> None:
        analysis._spans, analysis._pending = spans, None


@dataclass
class Analysis:
    """Résultat de détection / detection result.

    `spans` peut être différé : le moteur natif n'en crée les objets qu'à la première lecture (`anonymize` n'en
    crée aucun si on ne les lit pas). `spans` may be deferred: the native engine only builds the objects on
    first read (`anonymize` builds none unless they are read). Toujours une dataclass : champs, `asdict`,
    `replace`, égalité, copie et `pickle` lisent les zones / still a dataclass: fields, `asdict`, `replace`,
    equality, copy and `pickle` read the spans.
    """

    text: str
    spans: list[Span] = _DeferredSpans()  # type: ignore[assignment]
    countries: tuple[str, ...]
    country_reasons: dict[str, list[str]]
    language: str
    timings_ms: dict[str, float] = field(default_factory=dict)
    # Construction différée des zones (hors champs) / deferred span construction (not a field).
    _pending = None

    @classmethod
    def deferred(cls, text: str, spans: Callable[[], list[Span]], countries: tuple[str, ...],
                 country_reasons: dict[str, list[str]], language: str, timings_ms: dict[str, float]) -> Analysis:
        """Analyse dont les zones sont construites par `spans()` à la première lecture / spans built on first read."""
        analysis = cls(text, [], countries, country_reasons, language, timings_ms)
        analysis._pending = spans
        return analysis

    def __getstate__(self) -> dict[str, Any]:
        """Copie et `pickle` : zones construites d'abord / copy and pickling: spans built first."""
        _ = self.spans
        return self.__dict__


@dataclass(slots=True)
class AnonymizedText:
    """Résultat d'anonymisation / anonymisation result."""

    text: str
    analysis: Analysis
    report: dict[str, Any]


@runtime_checkable
class Detector(Protocol):
    """Détecteur Python branchable (IBAN, MRZ, noms, NER…) / pluggable Python detector."""

    id: str

    def detect(self, ctx: Any) -> list[Span]: ...
