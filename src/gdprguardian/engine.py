"""Moteur de détection et d'anonymisation / detection and anonymisation engine.

Cascade, du moins cher au plus cher / cascade, cheapest first:
normalisation -> mots-clés (1 passage) -> motifs + validateurs -> détecteurs -> fusion -> propagation.

Avec le noyau Rust, un document traverse toute la cascade en Rust (« moteur fusionné ») : Python n'exécute que
le code sans jumeau natif, et, sur un texte décomposé (NFD), les trois détecteurs à vue NFC. Sans lui, ou hors de
son domaine, le chemin par étapes ci-dessous, la référence, donne les mêmes résultats. With the Rust core, a
document goes through the whole cascade in Rust (the "fused engine"): Python only runs code without a native twin,
and, on a decomposed (NFD) text, the three NFC-view detectors. Without it, or outside its domain, the staged path
below, the reference, gives the same results.
"""

from __future__ import annotations

import re
from array import array
from bisect import bisect_left, bisect_right
from collections import Counter
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field, replace
from functools import cache, partial
from itertools import pairwise
from pathlib import PurePath
from time import perf_counter
from typing import Any

from . import _native
from ._text import _native_preparer, fold, normalize, prepare
from .custom import CUSTOM_PACK, KEEP_ENTITY, RuleError, RuleSet, load_rules, parse_rules
from .heuristics._compose import _COMMON_MARKS
from .keywords import MAX_KEYWORD_LEN, KeywordHits, KeywordIndex, longest_matches
from .labels import LABELS
from .locale import _native_detector as _native_language
from .locale import detect_language, evidence, select_countries
from .operators import FORCED_REPLACE, NATIVE_NAMES, get_operator
from .packs import Pack, PatternRecognizer, available_packs, load_pack
from .sanitize import sanitize_output
from .scope import HONORIFICS, Scope, native_rules
from .types import (
    MERGEABLE_ENTITIES,
    PRIORITY_CONTEXT_ONLY,
    PRIORITY_HEURISTIC,
    PRIORITY_PROPAGATED,
    PRIORITY_VALIDATED,
    Analysis,
    AnonymizedText,
    Span,
)

PROFILES = ("fast", "standard", "strict")
COUNTRY_MODES = ("all", "auto")
_MIN_SCORE = {"fast": 0.5, "standard": 0.5, "strict": 0.3}
_SEGMENT_SEPARATOR = "\n\n"
# Fenêtre [avant, après] où l'état civil d'une personne rend personnel un identifiant d'entreprise (« n° RCS :
# … ⏎ Nom : … ⏎ Prénom : … »). Window where a natural person's civil status makes a company number personal.
NATURAL_PERSON_WINDOW = (120, 120)
# Une personne morale dans cette fenêtre l'emporte (« la société X SAS, SIRET … ») / a legal entity there wins.
LEGAL_ENTITY_WINDOW = (80, 40)
_DIGIT_RE = re.compile(r"[0-9]")
# Avertissement du rapport quand le pays FR n'est pas demandé / report warning when FR is not requested.
NAMES_FRENCH_ONLY = ("Noms et adresses : détectés par les lexiques français seulement ; sans le pays FR, ils ne "
                     "sont pas masqués / Names and addresses are detected by the French lexicons only; without "
                     "country FR they are not masked")
_DENY_LABEL = "DENY"
# Cellule de tableau (début, fin) et groupes de contexte de son en-tête / table cell and its header's groups.
Zone = tuple[int, int, frozenset[str]]
NOTICE_FR = ("Anonymisation irréversible des identifiants détectés : aucune table de correspondance n'est "
             "conservée. Des éléments de contexte non détectés peuvent subsister.")
NOTICE_EN = ("Irreversible anonymisation of detected identifiers: no mapping table is kept. Undetected "
             "contextual details may remain.")


@dataclass(slots=True, frozen=True)
class Settings:
    """Réglages d'anonymisation / anonymisation settings."""

    # Pays explicites (recommandé), "all" (tous les packs, contexte requis pour les identifiants faibles)
    # ou "auto" (EXPÉRIMENTAL : pays deviné). Explicit countries (recommended), "all" (every pack, weak
    # identifiers need context) or "auto" (EXPERIMENTAL: inferred country).
    countries: str | tuple[str, ...] = ("FR",)
    default_countries: tuple[str, ...] = ("FR",)
    profile: str = "standard"
    label_language: str = "fr"
    neutral_labels: bool = False
    company_ids: str = "auto"
    facility_ids: str = "keep"
    entities: frozenset[str] | None = None
    exclude_entities: frozenset[str] = frozenset()
    operators: Mapping[str, str] = field(default_factory=dict)
    deny_list: Mapping[str, Sequence[str]] = field(default_factory=dict)
    allow_list: Sequence[str] = ()
    min_score: float | None = None
    sanitize: bool = True
    detectors: Sequence[Any] = ()
    # Noyau Rust si installé (résultats identiques) / Rust core when installed (identical results).
    native: bool = True
    # Jeu de règles de l'organisation (custom.parse_rules / load_rules) / the organisation's rule set.
    rules: Any = None
    # Rapport détaillé : pour chaque balise, la règle et la raison (jamais la valeur) / per-tag rule and reason.
    explain: bool = False

    def validate(self) -> None:
        if isinstance(self.countries, str):
            if self.countries not in COUNTRY_MODES:
                raise ValueError(f"countries : liste de codes pays ou / list of country codes or {COUNTRY_MODES}")
        else:
            unknown = sorted(set(self.countries) - set(available_packs()))
            if unknown or not self.countries:
                raise ValueError(f"Pays sans pack / countries without pack: {unknown or '[]'} "
                                 f"(disponibles / available: {available_packs()})")
        if self.profile not in PROFILES:
            raise ValueError(f"profile ∈ {PROFILES}")
        if self.company_ids not in ("auto", "keep", "mask") or self.facility_ids not in ("keep", "mask"):
            raise ValueError("company_ids ∈ auto|keep|mask, facility_ids ∈ keep|mask")
        if self.label_language not in ("fr", "en", "auto"):
            raise ValueError("label_language ∈ fr|en|auto")
        if self.rules is not None and not isinstance(self.rules, RuleSet):
            raise ValueError("rules : RuleSet, dict ou chemin de fichier / RuleSet, dict or file path")


class DetectionContext:
    """Vue partagée par les recognizers et détecteurs / view shared by recognizers and detectors."""

    __slots__ = ("_composed", "_features", "_zone_groups", "_zone_starts", "countries", "counts", "folded", "forced",
                 "found", "hits", "language", "seg_ends", "seg_starts", "settings", "strict", "text", "zones")

    def __init__(self, text: str, folded: str, hits: Any, countries: tuple[str, ...], language: str,
                 settings: Settings, seg_starts: list[int] | None = None, seg_ends: list[int] | None = None,
                 forced: Sequence[frozenset[str]] | None = None,
                 zones: Sequence[Zone] = ()) -> None:
        self.text = text
        self.folded = folded
        # Sans index de mots-clés (tests de détecteurs isolés) : aucun mot-clé / no keyword index: no keyword.
        self.hits = hits if hits is not None else KeywordHits()
        self.counts: dict[str, int] = self.hits.counts
        self.countries = countries
        self.language = language
        self.settings = settings
        self.strict = settings.profile == "strict"
        self.seg_starts = seg_starts
        self.seg_ends = seg_ends
        self.forced = forced
        # Cellules de tableau Markdown et groupes de contexte de leur en-tête de colonne (triées, disjointes).
        # Markdown table cells and the context groups of their column header (sorted, disjoint).
        self.zones = list(zones)
        self._zone_starts = [z[0] for z in self.zones]
        self._zone_groups = frozenset().union(*(z[2] for z in self.zones)) if self.zones else frozenset()
        # Zones déjà trouvées dans ce passage (motifs avant détecteurs), en lecture seule pour les détecteurs.
        # Spans already found in this pass (patterns before detectors), read-only for detectors.
        self.found: list[Span] = []
        self._features: dict[str, bool] = {}
        # Vue NFC d'un texte décomposé, faite une fois pour les détecteurs qui la lisent (`_compose`).
        # NFC view of a decomposed text, built once for the detectors that read it.
        self._composed: Any = None

    def has(self, feature: str | tuple[str, ...]) -> bool:
        """Préfiltre bon marché : 'digit' ou sous-chaînes cherchées dans le texte replié.

        Cheap prefilter: 'digit' or substrings searched in the folded text (any of them).
        """
        if isinstance(feature, tuple):
            return any(self.has(f) for f in feature)
        cached = self._features.get(feature)
        if cached is None:
            cached = (_DIGIT_RE.search(self.text) is not None) if feature == "digit" else feature in self.folded
            self._features[feature] = cached
        return cached

    def segment(self, pos: int) -> tuple[int, int, int]:
        if self.seg_starts is None:
            return -1, 0, len(self.text)
        index = bisect_right(self.seg_starts, pos) - 1
        return index, self.seg_starts[index], self.seg_ends[index]

    def any_context(self, groups: Sequence[str]) -> bool:
        counts = self.counts
        if any(g in counts for g in groups):
            return True
        if any(g in self._zone_groups for g in groups):
            return True
        return bool(self.forced) and any(any(g in f for g in groups) for f in self.forced)

    def _header_context(self, groups: Sequence[str], index: int, start: int, end: int) -> bool:
        """Contexte imposé par un en-tête de colonne (classeur ou tableau Markdown) / column-header context."""
        if self.forced is not None and index >= 0 and any(g in self.forced[index] for g in groups):
            return True
        if not self.zones:
            return False
        i = bisect_right(self._zone_starts, start) - 1
        return i >= 0 and end <= self.zones[i][1] and any(g in self.zones[i][2] for g in groups)

    def near(self, groups: Sequence[str], start: int, end: int, before: int, after: int, lo: int = 0,
             hi: int = 1 << 62) -> bool:
        """`lo`/`hi` bornent en plus la recherche (ligne, paragraphe) / further bound the search (line, block)."""
        index, seg_lo, seg_hi = self.segment(start)
        lo, hi = max(lo, seg_lo), min(hi, seg_hi)
        return (self._header_context(groups, index, start, end)
                or any(self.hits.near(g, start, end, before, after, lo, hi) for g in groups))

    def vetoed(self, groups: Sequence[str], vetoes: Sequence[str], start: int, end: int, after: int) -> bool:
        """Un mot-veto placé entre le dernier mot-clé et la valeur annule le contexte : l'indice le plus proche
        l'emporte (« né le 3 mai 1953. … la réunion du 12/02/2026 »). En-têtes et mots-clés après la valeur
        ne sont jamais annulés.

        A veto word between the last keyword and the value cancels the context: the nearest cue wins. Column
        headers and keywords after the value are never vetoed.
        """
        index, lo, hi = self.segment(start)
        if self._header_context(groups, index, start, end):
            return False
        if any(self.hits.near(g, start, end, 0, after, lo, hi) for g in groups):
            return False
        keyword = max(self.hits.last_end(g, start, lo) for g in groups)
        veto = max(self.hits.last_end(g, start, lo) for g in vetoes)
        return veto >= 0 and veto > keyword


class _FoundView(Sequence[Span]):
    """`ctx.found` des détecteurs Python du moteur fusionné : les zones du passage, lues dans Rust au premier
    usage, relues seulement si le passage a changé (aucun objet créé sans lecture). The fused engine's
    `ctx.found`: the pass's spans, read from Rust on first use, read again only once the pass has changed (no
    object built unless read). Lecture seule, comme `ctx.found` / read-only, as `ctx.found`. Chaque zone garde
    son objet, et un objet modifié est vu, comme dans la liste de Python / each span keeps its object, and a
    changed object is seen, as in Python's list.
    """

    __slots__ = ("_document", "_key", "_spans")

    def __init__(self, document: Any) -> None:
        self._document = document
        self._key: tuple[int, int] | None = None
        self._spans: list[Span] = []

    def _current(self) -> list[Span]:
        key = self._document.found_key
        if key != self._key:
            self._spans, self._key = self._document.found(True), key
        return self._spans

    def __getitem__(self, index: Any) -> Any:
        return self._current()[index]

    def __len__(self) -> int:
        return len(self._current())

    def __iter__(self) -> Iterator[Span]:
        return iter(self._current())


class _Host:
    """Code Python que le moteur fusionné appelle : `calls[i](ctx)` rend les zones d'un détecteur ou de
    recognizers sans jumeau, `context(document)` construit leur `DetectionContext`, `select(document)` choisit les
    pays du mode auto. Python code the fused engine calls: detectors and recognizers without a twin, their context,
    and the auto-mode country choice.
    """

    __slots__ = ("calls", "context", "select")

    def __init__(self, calls: Sequence[Callable[[DetectionContext], list[Span]]],
                 context: Callable[[Any], DetectionContext],
                 select: Callable[[Any], tuple[tuple[str, ...], dict[str, list[str]]]]) -> None:
        self.calls = tuple(calls)
        self.context = context
        self.select = select


# Ligne de délimitation GFM (au moins deux colonnes) / GFM delimiter row (two columns or more).
_TABLE_DELIMITER_RE = re.compile(r"^[ \t]*\|?[ \t]*:?-+:?[ \t]*(?:\|[ \t]*:?-+:?[ \t]*)+\|?[ \t\r]*$", re.MULTILINE)
_PIPE_RE = re.compile(r"(?<!\\)\|")


def _cells(line: str, offset: int) -> list[tuple[int, int]]:
    """Cellules d'une ligne GFM (barres échappées ignorées), positions absolues rognées.

    GFM row cells (escaped pipes ignored), trimmed absolute offsets.
    """
    edges = [-1, *(m.start() for m in _PIPE_RE.finditer(line)), len(line)]
    cells: list[tuple[int, int]] = []
    for left, right in pairwise(edges):
        start, end = left + 1, right
        while start < end and line[start].isspace():
            start += 1
        while end > start and line[end - 1].isspace():
            end -= 1
        cells.append((offset + start, offset + end))
    # Barres de bord : pas de cellule avant la première ni après la dernière / edge pipes open no cell.
    if len(edges) > 2 and not line[:edges[1]].strip():
        cells.pop(0)
    if len(edges) > 2 and cells and not line[edges[-2] + 1:].strip():
        cells.pop()
    return cells


def markdown_table_zones(text: str, groups_of: Callable[[str], frozenset[str]]) -> list[Zone]:
    """Cellules dont l'en-tête de colonne porte un contexte (« Date de naissance », « Passeport »…).

    Cells whose column header carries context ("Date de naissance", "Passeport"…): the header then acts as
    context for every cell below it, however far. Zones triées et disjointes / sorted, disjoint zones.
    """
    if "|" not in text:
        return []
    zones: list[Zone] = []
    consumed = 0
    for delimiter in _TABLE_DELIMITER_RE.finditer(text):
        # Une délimitation dans un tableau déjà lu est une simple ligne (GFM) / inside a table, just a row.
        if delimiter.start() < consumed or delimiter.start() == 0:
            continue
        header_start = text.rfind("\n", 0, delimiter.start() - 1) + 1
        header = text[header_start:delimiter.start() - 1]
        if "|" not in header:
            continue
        columns = [groups_of(text[s:e]) for s, e in _cells(header, header_start)]
        pos = delimiter.end() + 1
        while pos < len(text):
            end = text.find("\n", pos)
            end = len(text) if end < 0 else end
            line = text[pos:end]
            if "|" not in line:
                break
            if any(columns):
                for column, (start, stop) in enumerate(_cells(line, pos)):
                    if column < len(columns) and columns[column] and stop > start:
                        zones.append((start, stop, columns[column]))
            pos = end + 1
        consumed = pos
    return zones


# --- Contrôles de bornes / boundary checks ---------------------------------------------------------


def _not_alnum(ch: str) -> bool:
    return not ch.isalnum()


def _boundary_checks() -> dict[str, tuple[Callable[[str, int], bool], Callable[[str, int], bool]]]:
    def left(pred: Callable[[str], bool]) -> Callable[[str, int], bool]:
        return lambda text, pos: pos == 0 or pred(text[pos - 1])

    def right(pred: Callable[[str], bool]) -> Callable[[str, int], bool]:
        return lambda text, pos: pos >= len(text) or pred(text[pos])

    def ip_right(text: str, pos: int) -> bool:
        if pos >= len(text):
            return True
        ch = text[pos]
        if ch.isalnum():
            return False
        return not (ch == "." and pos + 1 < len(text) and text[pos + 1].isdigit())

    always = lambda text, pos: True  # noqa: E731
    return {
        "alnum": (left(_not_alnum), right(_not_alnum)),
        "word": (left(lambda c: not (c.isalnum() or c in "_.%+-")), right(lambda c: not (c.isalnum() or c == "_"))),
        "ip": (left(lambda c: not (c.isalnum() or c == ".")), ip_right),
        "hex": (left(lambda c: not (c.isalnum() or c == ":")), right(lambda c: not (c.isalnum() or c == ":"))),
        "phone": (left(lambda c: not (c.isalnum() or c == "+")), right(_not_alnum)),
        "digit": (left(lambda c: not c.isdigit()), right(lambda c: not c.isdigit())),
        "none": (always, always),
    }


_BOUNDARIES = _boundary_checks()

# Après un échec, chaque position suivante du même mot a un prédécesseur alphanumérique (ou chiffre) et
# échouerait à la borne gauche : on saute le mot entier, résultat identique. After a failure, every later
# position in the same run has an alnum (or digit) predecessor and would fail the left check: skip the run.
_SKIP_RUN = {"alnum": re.compile(r"[^\W_]+"), "digit": re.compile(r"\d+")}


def _next_start(skip: re.Pattern[str] | None, text: str, start: int) -> int:
    run = skip.match(text, start) if skip is not None else None
    return max(run.end(), start + 1) if run is not None else start + 1


# --- Résolution des chevauchements / overlap resolution ----------------------------------------------


def _trim(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and not text[start].isalnum():
        start += 1
    while end > start and not text[end - 1].isalnum():
        end -= 1
    return start, end


def merge_same_entity(spans: list[Span]) -> list[Span]:
    """Fusionne les chevauchements d'un même type composite (personne, adresse…) / merge same-type overlaps."""
    merged: list[Span] = []
    by_entity: dict[str, list[Span]] = {}
    for span in spans:
        if span.entity in MERGEABLE_ENTITIES:
            by_entity.setdefault(span.entity, []).append(span)
        else:
            merged.append(span)
    for group in by_entity.values():
        group.sort(key=lambda s: (s.start, -s.end, -s.priority, s.source))
        current = group[0]
        for span in group[1:]:
            if span.start < current.end:
                if span.end > current.end or span.priority > current.priority:
                    current = replace(
                        current,
                        end=max(current.end, span.end),
                        priority=max(current.priority, span.priority),
                        score=max(current.score, span.score),
                        forms=current.forms + span.forms,
                        propagate=current.propagate or span.propagate,
                        value=None,
                        source=current.source if current.source == span.source else f"{current.source}+{span.source}",
                    )
                else:
                    current.propagate = current.propagate or span.propagate
            else:
                merged.append(current)
                current = span
        merged.append(current)
    return merged


def resolve(spans: list[Span], text: str) -> list[Span]:
    """Priorité, puis longueur, puis score ; les zones composites perdantes sont rognées, pas perdues.

    Priority, then length, then score; losing composite zones are trimmed, not dropped.
    """
    # Ordre total (source en dernier) : résultat indépendant de l'ordre de détection.
    # Total order (source last): result independent of detection order.
    order = sorted(spans, key=lambda s: (-s.priority, -(s.end - s.start), -s.score, s.start, s.source))
    starts: list[int] = []
    accepted: list[Span] = []
    for span in order:
        i = bisect_left(starts, span.end)
        j = i - 1
        overlaps: list[Span] = []
        while j >= 0 and accepted[j].end > span.start:
            overlaps.append(accepted[j])
            j -= 1
        if not overlaps:
            starts.insert(i, span.start)
            accepted.insert(i, span)
            continue
        if span.entity not in MERGEABLE_ENTITIES:
            continue
        cursor = span.start
        pieces: list[tuple[int, int]] = []
        for other in sorted(overlaps, key=lambda s: s.start):
            if other.start > cursor:
                pieces.append((cursor, other.start))
            cursor = max(cursor, other.end)
        if cursor < span.end:
            pieces.append((cursor, span.end))
        for piece_start, piece_end in pieces:
            piece_start, piece_end = _trim(text, piece_start, piece_end)
            if piece_end - piece_start >= 3:
                piece = replace(span, start=piece_start, end=piece_end, value=None)
                k = bisect_left(starts, piece_start)
                starts.insert(k, piece_start)
                accepted.insert(k, piece)
    return accepted


def _priority(rec: PatternRecognizer, value: str | None) -> int:
    """Clé fausse gardée sur contexte : priorité « contexte seul » / wrong key kept on context: context-only."""
    return PRIORITY_CONTEXT_ONLY if value is None and rec.fallback else rec.priority


def _line_bounds(text: str, start: int, end: int, before: int, after: int) -> tuple[int, int]:
    """Ligne de [start, end), bornée aux fenêtres (`KeywordHits.near` ne lit rien au-delà) : coût constant.

    The line of [start, end), bounded by the windows (`KeywordHits.near` reads nothing beyond): constant cost.
    """
    lo = text.rfind("\n", max(0, start - before - MAX_KEYWORD_LEN), start) + 1
    hi = text.find("\n", end, end + after)
    return lo, end + after if hi < 0 else hi


def _block_bounds(text: str, start: int, end: int, before: int, after: int) -> tuple[int, int]:
    """Paragraphe de [start, end) : entre deux lignes vides (blancs seuls), borné aux fenêtres.

    The paragraph of [start, end): between two blank lines (blanks only), bounded by the windows.
    """
    floor = max(0, start - before - MAX_KEYWORD_LEN)
    lo, newline, blank = floor, -1, True
    for i in range(start - 1, floor - 1, -1):
        c = text[i]
        if c == "\n":
            if newline >= 0 and blank:
                lo = newline + 1
                break
            newline, blank = i, True
        elif c not in " \t\r":
            blank = False
    ceiling = min(len(text), end + after)
    hi, newline, blank = ceiling, -1, True
    for i in range(end, ceiling):
        c = text[i]
        if c == "\n":
            if newline >= 0 and blank:
                hi = newline
                break
            newline, blank = i, True
        elif c not in " \t\r":
            blank = False
    return lo, hi


@cache
def _packs_for(countries: tuple[str, ...] | str) -> tuple[Pack, ...]:
    ids = available_packs() if countries in COUNTRY_MODES else tuple(dict.fromkeys(("INTL", *countries)))
    return tuple(load_pack(pack_id) for pack_id in ids)


@cache
def _keyword_groups(pack_ids: tuple[str, ...]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for pack_id in pack_ids:
        for group, words in load_pack(pack_id).context.items():
            groups.setdefault(group, []).extend(words)
    return groups


@cache
def _keyword_index(pack_ids: tuple[str, ...]) -> KeywordIndex:
    return KeywordIndex(_keyword_groups(pack_ids))


@cache
def _native_scanner(pack_ids: tuple[str, ...], keys: tuple[tuple[str, str], ...]) -> _native.NativeScanner | None:
    """Analyseur Rust compilé une fois par ensemble de packs / Rust scanner compiled once per pack set."""
    by_key = {(r.pack, r.id): r for pack_id in pack_ids for r in load_pack(pack_id).recognizers}
    return _native.build([by_key[k] for k in keys], _keyword_groups(pack_ids), fold)


class Anonymizer:
    """Point d'entrée principal ; réutilisable et sûr entre threads (état par appel).

    Main entry point; reusable and thread-safe (per-call state only).
    """

    def __init__(self, settings: Settings | None = None, **overrides: Any) -> None:
        settings = replace(settings or Settings(), **overrides) if overrides else (settings or Settings())
        if isinstance(settings.countries, str) and settings.countries.lower() in COUNTRY_MODES:
            settings = replace(settings, countries=settings.countries.lower())
        elif isinstance(settings.countries, str):
            settings = replace(settings, countries=tuple(c.strip() for c in settings.countries.split(",") if c.strip()))
        if isinstance(settings.countries, list):
            settings = replace(settings, countries=tuple(settings.countries))
        if isinstance(settings.countries, tuple):
            settings = replace(settings, countries=tuple(c.upper() for c in settings.countries))
        # Règles : objet validé, dict (JSON) ou fichier TOML/JSON (de confiance) / rules: object, dict or file path.
        if isinstance(settings.rules, Mapping):
            settings = replace(settings, rules=parse_rules(settings.rules))
        elif isinstance(settings.rules, (str, PurePath)):
            settings = replace(settings, rules=load_rules(settings.rules))
        settings.validate()
        self.settings = settings
        self._packs = _packs_for(settings.countries)
        self._keywords = _keyword_index(tuple(p.id for p in self._packs))
        self._recognizers: dict[str, list[PatternRecognizer]] = {}
        self._detectors: dict[str, list[Any]] = {}
        for pack in self._packs:
            allowed = [r for r in pack.recognizers if self._entity_allowed(r.entity)]
            self._recognizers[pack.id] = allowed
            self._detectors[pack.id] = pack.build_detectors()
        # Rust prend les recognizers qu'il sait traiter, Python garde les autres.
        # Rust takes the recognizers it supports, Python keeps the others.
        self._native: _native.NativeScanner | None = None
        self._python_recognizers = self._recognizers
        if settings.native and _native.available():
            keys = tuple((r.pack, r.id) for p in self._packs for r in self._recognizers[p.id])
            scanner = _native_scanner(tuple(p.id for p in self._packs), keys)
            if scanner is not None and scanner.supported:
                self._native = scanner
                self._python_recognizers = {
                    pack_id: [r for r in recs if (r.pack, r.id) not in scanner.supported]
                    for pack_id, recs in self._recognizers.items()
                }
        self._extra_detectors = list(settings.detectors)
        self._ei_groups = tuple(g for p in self._packs for g in p.context if g.endswith(":ei"))
        self._person_groups = tuple(g for p in self._packs for g in p.context if g.endswith(":natural_person"))
        self._entity_groups = tuple(g for p in self._packs for g in p.context if g.endswith(":legal_entity"))
        self._min_score = settings.min_score if settings.min_score is not None else _MIN_SCORE[settings.profile]
        rules: RuleSet | None = settings.rules
        allow, deny = tuple(settings.allow_list), dict(settings.deny_list)
        if rules is not None:
            allow += rules.allow
            for label, terms in rules.deny.items():
                deny[label] = (*deny.get(label, ()), *terms)
        self._allow = frozenset(fold(term).strip() for term in allow)
        self._deny = self._build_deny(deny)
        # Règles personnalisées : compilées pour cette instance seulement, jamais en cache partagé.
        # Custom rules: compiled for this instance only, never in a shared cache.
        self._custom: list[PatternRecognizer] = rules.recognizers() if rules is not None else []
        self._custom_native: _native.NativeScanner | None = None
        self._custom_keywords: KeywordIndex | None = None
        if self._custom:
            groups = rules.keyword_groups()
            if settings.native and _native.available():
                # Règles non sûres : compilation bornée (un fil, budget mémoire commun) / bounded compile.
                self._custom_native = _native.build(self._custom, groups, fold, untrusted=not rules.trusted)
            unsupported = [] if self._custom_native is None else [
                (i, error) for i, (ok, error) in enumerate(zip(self._custom_native.flags, self._custom_native.errors,
                                                                strict=True), 1) if not ok]
            if not rules.trusted and (self._custom_native is None or unsupported):
                # Règles non sûres : moteur linéaire obligatoire (aucun retour arrière exponentiel possible).
                # Untrusted rules: linear-time engine required (no catastrophic backtracking possible).
                if self._custom_native is None:
                    raise RuleError("Règles personnalisées indisponibles : noyau Rust requis / Rust core required")
                index, error = unsupported[0]
                raise RuleError(f"Règle n°{index} ({rules.rules[index - 1].label}) : construction refusée par le "
                                f"moteur linéaire / refused by the linear-time engine: {(error or '')[:200]}")
            if unsupported:
                self._custom_native = None  # de confiance : repli sur Python / trusted: Python fallback
            if self._custom_native is None:
                self._custom_keywords = KeywordIndex(groups) if groups else None
        self._operators = {k: get_operator(v) for k, v in settings.operators.items()}
        self._default_operator = get_operator("replace")
        # Après la détection, tout en Rust si possible : mêmes zones, même texte, même rapport.
        # After detection, everything in Rust when possible: same spans, same text, same report.
        self._finalizer = self._native_finalizer() if settings.native else None
        # Moteur fusionné : la détection aussi, en un appel par document, puis la finalisation avec ce finaliseur-là.
        # Fused engine: detection too, one call per document, then finalisation with this very finalizer.
        self._host: _Host | None = None
        self._fused = self._fused_engine() if self._finalizer is not None else None
        self._fused_finalizer = self._finalizer

    def _fused_engine(self) -> Any:
        """Moteur Rust fusionné, composé des composants natifs déjà construits, ou None.

        Fused Rust engine, composed of the native components already built, or None: detection in one call,
        finalisation in a second / détection en un appel, finalisation en un second. Chaque détecteur décrit son
        jumeau (`native_plan`) ; un détecteur sans plan propre (classe dérivée comprise), les recognizers sans
        jumeau, la liste de refus et les règles en Python deviennent des appels Python. Each detector describes its
        twin; one without its own plan (subclasses included), recognizers without a twin, the deny list and Python
        rules become Python calls.
        """
        preparer, language = _native_preparer(), _native_language()
        if self._native is None or preparer is None or language is None:
            return None
        calls: list[Callable[[DetectionContext], list[Span]]] = []

        def python(function: Callable[[DetectionContext], list[Span]]) -> int:
            calls.append(function)
            return len(calls) - 1

        packs = []
        for pack in self._packs:
            slots = []
            for detector in self._detectors[pack.id]:
                own = "native_plan" in vars(type(detector))  # une classe dérivée peut changer `detect`
                plan = detector.native_plan() if own else None
                fallback = python(partial(self._detector_spans, detector))
                slots.append({"kind": "python", "call": fallback} if plan is None else {**plan, "fallback": fallback})
            left = self._python_recognizers[pack.id]  # sans équivalent natif / without a native equivalent
            packs.append({"id": pack.id, "country": pack.country, "always_on": pack.always_on, "slots": slots,
                          "recognizers": python(partial(self._recognizer_spans, pack.id)) if left else None})
        index = {pack.id: i for i, pack in enumerate(self._packs)}
        # Prototype de zone de chaque motif natif, priorité d'une clé fausse, pack / prototype, wrong-key priority.
        recognizers = [(Span(0, 0, r.entity, r.label, r.id, 0.0, r.priority), _priority(r, None), index[r.pack])
                       for r in self._native.recognizers]
        extras = [(python(partial(self._detector_spans, d)), f"detector:{getattr(d, 'id', type(d).__name__)}")
                  for d in self._extra_detectors]
        deny = python(self._deny_spans) if self._deny is not None else None
        custom: dict[str, Any] | None = None
        if self._custom and self._custom_native is not None:
            custom = {"scanner": self._custom_native._scanner,
                      "rules": [Span(0, 0, r.entity, r.label, r.id, 0.0, r.priority) for r in self._custom]}
        elif self._custom:
            custom = {"call": python(self._custom_spans)}
        # Packs actifs et `ctx.countries`, comme `_detect_all` / active packs and `ctx.countries`, as there.
        mode = self.settings.countries
        if mode == "auto":
            active, countries = [], ()
        elif mode == "all":
            active, countries = [True] * len(self._packs), tuple(p.country for p in self._packs if p.country)
        else:
            countries = tuple(c for c in mode if c != "INTL")
            chosen = set(countries)
            active = [p.always_on or p.country in chosen or p.id in chosen for p in self._packs]
        self._host = _Host(calls, self._fused_context, self._fused_select)
        return _native.engine(
            preparer=preparer, language=language, scanner=self._native._scanner, table=_native.unicode_table(),
            span_type=Span, recognizers=recognizers, packs=packs, auto=mode == "auto", active=active,
            countries=countries, strict=self.settings.profile == "strict", company_ids=self.settings.company_ids,
            facility_mask=self.settings.facility_ids == "mask", ei_groups=list(self._ei_groups),
            person_groups=list(self._person_groups), entity_groups=list(self._entity_groups),
            entities=None if self.settings.entities is None else set(self.settings.entities),
            excluded=set(self.settings.exclude_entities), extras=extras, deny=deny, custom=custom,
            marks=list(_COMMON_MARKS))

    def _native_finalizer(self) -> Any:
        """Finaliseur Rust, avec les données mêmes du chemin Python / Rust finalizer, fed the Python path's data."""
        rules = native_rules()
        if rules is None:
            return None
        operators = [(key, NATIVE_NAMES.get(operator)) for key, operator in self._operators.items()]
        native_operators = all(name for _, name in operators) and NATIVE_NAMES.get(self._default_operator) == "replace"
        try:
            return _native.finalizer(
                rules, Span, min_score=self._min_score, allow=sorted(self._allow),
                mergeable=sorted(MERGEABLE_ENTITIES), keep_entity=KEEP_ENTITY if self._custom else None,
                unmaskable=sorted(_UNMASKABLE), priority_validated=PRIORITY_VALIDATED,
                priority_propagated=PRIORITY_PROPAGATED, operators=operators if native_operators else None,
                forced_replace=sorted(FORCED_REPLACE), detector_reasons=sorted(_DETECTOR_REASONS.items()),
                recognizers=[(r.id, r.tier, r.validator is not None) for r in self._recognizer_index().values()])
        except (TypeError, ValueError, OverflowError):
            # Réglage hors du domaine natif (terme avec substitut isolé, seuil géant…) : la référence Python
            # le traite. Setting outside the native domain (lone surrogate, huge threshold…): Python handles it.
            return None

    # --- configuration ---

    def _entity_allowed(self, entity: str) -> bool:
        if entity in self.settings.exclude_entities:
            return False
        return self.settings.entities is None or entity in self.settings.entities

    @staticmethod
    def _build_deny(deny: Mapping[str, Sequence[str]]) -> KeywordIndex | None:
        groups: dict[str, list[str]] = {}
        for label, terms in deny.items():
            key = re.sub(r"[^A-Z0-9]+", "_", fold(label).upper()).strip("_") or "CUSTOM"
            if not key[0].isalpha():
                key = "X_" + key
            if terms:
                groups.setdefault(f"{_DENY_LABEL}:{key}", []).extend(terms)
        return KeywordIndex(groups) if groups else None

    @property
    def packs(self) -> tuple[Pack, ...]:
        return self._packs

    @property
    def native(self) -> bool:
        """Le noyau Rust est-il utilisé ? / is the Rust core in use?"""
        return self._native is not None

    def _scan_keywords(self, folded: str) -> Any:
        return self._native.keywords(folded) if self._native is not None else self._keywords.scan(folded)

    def context_groups(self, text: str) -> frozenset[str]:
        """Groupes de contexte présents dans un court texte (en-tête) / context groups in a short text."""
        return frozenset(self._keywords.groups_in(text))

    # --- moteur fusionné / fused engine ---

    def _fused_document(self, text: str) -> Any:
        """Texte détecté par le moteur fusionné (document Rust), ou None : chemin par étapes (pas de moteur,
        finaliseur remplacé, texte hors du domaine natif). Text detected by the fused engine, or None: staged path.
        """
        if self._fused is None or self._finalizer is not self._fused_finalizer:
            return None
        return self._fused.detect(text, self._host)

    def _fused_cells(self, texts: Sequence[str], forced: Sequence[frozenset[str]] | None) -> Any:
        """Cellules détectées par le moteur fusionné, ou None / cells detected by the fused engine, or None."""
        if self._fused is None or self._finalizer is not self._fused_finalizer:
            return None
        return self._fused.detect_cells(texts, forced, self._host)

    def _fused_context(self, document: Any) -> DetectionContext:
        """`DetectionContext` sur le texte, les mots-clés et les zones d'un document Rust, pour le code Python.

        `DetectionContext` over a Rust document's text, keywords and zones, for Python code.
        """
        segments = document.segments
        starts, ends = segments if segments is not None else (None, None)
        forced = document.forced
        zones = [(start, end, frozenset(groups)) for start, end, groups in document.zones]
        ctx = DetectionContext(document.text, document.folded, document.hits, document.countries, document.language,
                               self.settings, starts, ends, list(forced) if forced is not None else None, zones)
        ctx.found = _FoundView(document)  # type: ignore[assignment]
        return ctx

    def _fused_select(self, document: Any) -> tuple[tuple[str, ...], dict[str, list[str]]]:
        """Mode auto : pays tirés des preuves du premier passage, comme `_detect_all` / auto-mode countries.

        Preuves lues en Rust sans objet par zone ; une valeur non ASCII (casse de Python) passe par `evidence`.
        Evidence read in Rust without one object per span; a non-ASCII value (Python's case rules) uses `evidence`.
        """
        found = document.evidence()
        ibans, phones, tlds = found if found is not None else evidence(document.found())
        return select_countries(document.hits, self._packs, self.settings.default_countries, document.language,
                                ibans, phones, tlds)

    def _fused_countries(self, document: Any) -> tuple[tuple[str, ...], dict[str, list[str]]]:
        """Pays d'un document et leurs raisons, comme `_detect_all` / a document's countries and reasons."""
        mode = self.settings.countries
        if mode == "auto":
            return document.countries, document.reasons
        countries = document.countries
        return countries, {c: ["all" if mode == "all" else "explicit"] for c in countries}

    def _fused_fallback(self, document: Any) -> tuple[DetectionContext, list[Span], dict[str, list[str]], Any,
                                                      dict[str, float]] | None:
        """Entrées du chemin par étapes tirées d'un document que Rust ne finalise pas (zone Python hors du domaine
        natif, opérateur Python) ; None s'il n'y a pas de document ou si ses zones ont déjà été remises à Rust.
        Staged-path inputs from a document Rust does not finalise; None without a document or once its spans
        were handed over to Rust (the staged path then starts again).
        """
        detected = None if document is None else document.detected()
        if detected is None:
            return None
        ctx = self._fused_context(document)
        ctx.countries, reasons = self._fused_countries(document)
        return ctx, detected, reasons, _offset_array(document.offsets), dict(document.timings)

    def _fused_cells_fallback(self, document: Any) -> tuple[DetectionContext, list[Span], dict[str, list[str]],
                                                            list[tuple[str | None, Any]], dict[str, float]] | None:
        """`_fused_fallback` pour des cellules / for cells."""
        staged = self._fused_fallback(document)
        if staged is None:
            return None
        ctx, detected, reasons, _, timings = staged
        return ctx, detected, reasons, [(None, _offset_array(raw)) for raw in document.cell_offsets], timings

    # --- détection / detection ---

    def analyze(self, text: str) -> Analysis:
        t0 = perf_counter()
        document = self._fused_document(text)
        if document is not None:
            t1 = perf_counter()
            spans = document.analyze(self._finalizer)
            if spans is not None:
                timings = dict(document.timings)
                timings["resolve"] = (perf_counter() - t1) * 1000
                timings["total"] = (perf_counter() - t0) * 1000
                countries, reasons = self._fused_countries(document)
                return Analysis(text, spans, countries, reasons, document.language, timings)
        ctx, detected, reasons, offsets, timings = self._fused_fallback(document) or self._detect_text(text)
        t1 = perf_counter()
        spans = self._final_spans(ctx, detected, offsets)
        timings["resolve"] = (perf_counter() - t1) * 1000
        timings["total"] = (perf_counter() - t0) * 1000
        return Analysis(text, spans, ctx.countries, reasons, ctx.language, timings)

    def _detect_text(self, text: str) -> tuple[DetectionContext, list[Span], dict[str, list[str]], Any,
                                               dict[str, float]]:
        """Normalisation, contexte et détection d'un texte / normalisation, context and detection of a text."""
        timings: dict[str, float] = {}
        t0 = perf_counter()
        native = self.settings.native
        norm, folded, offsets = prepare(text, native=native)
        hits = self._scan_keywords(folded)
        language = detect_language(folded, native=native)
        zones = markdown_table_zones(norm, self.context_groups)
        timings["prepare"] = (perf_counter() - t0) * 1000
        ctx = DetectionContext(norm, folded, hits, (), language, self.settings, zones=zones)
        spans, reasons = self._detect_all(ctx, timings)
        return ctx, spans, reasons, offsets, timings

    def _final_spans(self, ctx: DetectionContext, detected: list[Span], offsets: Any) -> list[Span]:
        """Zones finales en positions d'origine (Rust si possible) / final spans in original offsets."""
        if self._finalizer is not None:
            spans = self._finalizer.analyze(detected, ctx.text, _offset_bytes(offsets))
            if spans is not None:
                return spans
        spans = self._finalize(ctx, detected)
        if offsets is not None:
            for span in spans:
                span.start = offsets[span.start]
                span.end = offsets[span.end - 1] + 1
        return spans

    def analyze_segments(self, texts: Sequence[str], forced: Sequence[frozenset[str]] | None = None,
                         ) -> tuple[list[list[Span]], Analysis]:
        """Détecte sur plusieurs segments en un seul passage (cellules, lignes…).

        Detects over many segments in one pass (cells, lines…). Le contexte ne traverse pas les
        segments, sauf les groupes `forced` (en-têtes de colonnes), un ensemble par segment / context never
        crosses segments, except `forced` groups (column headers), one set per segment.
        """
        _check_forced(texts, forced)
        document = self._fused_cells(texts, forced)
        if document is not None:
            found = document.analyze_cells(self._finalizer)
            if found is not None:
                per_segment, spans = found
                countries, reasons = self._fused_countries(document)
                return per_segment, Analysis(document.text, spans, countries, reasons, document.language,
                                             dict(document.timings))
        staged = self._fused_cells_fallback(document) or self._detect_segments(texts, forced)
        ctx, detected, reasons, normalized, timings = staged
        per_segment, spans = self._segment_spans(ctx, detected, normalized)
        return per_segment, Analysis(ctx.text, spans, ctx.countries, reasons, ctx.language, timings)

    def _detect_segments(self, texts: Sequence[str], forced: Sequence[frozenset[str]] | None,
                         ) -> tuple[DetectionContext, list[Span], dict[str, list[str]], list[tuple[str, Any]],
                                    dict[str, float]]:
        normalized = [normalize(t) for t in texts]
        seg_starts: list[int] = []
        seg_ends: list[int] = []
        pieces: list[str] = []
        cursor = 0
        for norm, _ in normalized:
            seg_starts.append(cursor)
            pieces.append(norm)
            cursor += len(norm)
            seg_ends.append(cursor)
            cursor += len(_SEGMENT_SEPARATOR)
        joined = _SEGMENT_SEPARATOR.join(pieces)
        folded = fold(joined)
        hits = self._scan_keywords(folded)
        language = detect_language(folded, native=self.settings.native)
        ctx = DetectionContext(joined, folded, hits, (), language, self.settings,
                               seg_starts, seg_ends, list(forced) if forced is not None else None)
        timings: dict[str, float] = {}
        detected, reasons = self._detect_all(ctx, timings)
        return ctx, detected, reasons, normalized, timings

    def _segment_spans(self, ctx: DetectionContext, detected: list[Span], normalized: list[tuple[str, Any]],
                       ) -> tuple[list[list[Span]], list[Span]]:
        """Zones par segment, en positions locales d'origine (Rust si possible) / per-segment spans."""
        if self._finalizer is not None:
            native = self._finalizer.analyze_segments(detected, ctx.text, ctx.seg_starts, ctx.seg_ends,
                                                      [_offset_bytes(offsets) for _, offsets in normalized])
            if native is not None:
                return native
        spans = self._finalize(ctx, detected)
        per_segment: list[list[Span]] = [[] for _ in normalized]
        for span in spans:
            index, lo, hi = ctx.segment(span.start)
            if span.end > hi:
                continue
            offsets = normalized[index][1]
            span.start -= lo
            span.end -= lo
            if offsets is not None:
                span.start = offsets[span.start]
                span.end = offsets[span.end - 1] + 1
            per_segment[index].append(span)
        return per_segment, spans

    def _detect_all(self, ctx: DetectionContext, timings: dict[str, float]) -> tuple[list[Span], dict[str, list[str]]]:
        """Pays explicites : un passage. Mode auto : packs toujours actifs, puis pays déduits des preuves validées.

        Explicit countries: one pass. Auto mode: always-on packs first, then countries inferred from the
        validated evidence they produced (IBAN, E.164 phones, e-mail domains) plus context keywords.
        """
        mode = self.settings.countries
        if mode == "all":
            ctx.countries = tuple(p.country for p in self._packs if p.country)
            packs = frozenset(p.id for p in self._packs)
            return self._detect(ctx, timings, packs, extras=True), {c: ["all"] for c in ctx.countries}
        if mode != "auto":
            ctx.countries = tuple(c for c in mode if c != "INTL")
            active = set(ctx.countries)
            packs = frozenset(p.id for p in self._packs if p.always_on or p.country in active or p.id in active)
            return self._detect(ctx, timings, packs, extras=True), {c: ["explicit"] for c in ctx.countries}
        spans = self._detect(ctx, timings, frozenset(p.id for p in self._packs if p.always_on), extras=False)
        ibans, phones, tlds = evidence(spans)
        ctx.countries, reasons = select_countries(ctx.hits, self._packs, self.settings.default_countries,
                                                  ctx.language, ibans, phones, tlds)
        active = set(ctx.countries)
        country_packs = frozenset(p.id for p in self._packs
                                  if not p.always_on and (p.country in active or p.id in active))
        spans.extend(self._detect(ctx, timings, country_packs, extras=True))
        return spans, reasons

    def _detect(self, ctx: DetectionContext, timings: dict[str, float], active_packs: frozenset[str],
                extras: bool) -> list[Span]:
        spans: list[Span] = []
        ctx.found = spans
        if self._native is not None and active_packs:
            t0 = perf_counter()
            segments = list(zip(ctx.seg_starts, ctx.seg_ends, strict=True)) if ctx.seg_starts is not None else None
            found = self._native.scan(ctx.hits, ctx.text, ctx.folded, active_packs, ctx.strict,
                                      self.settings.company_ids, self.settings.facility_ids == "mask",
                                      self._ei_groups, segments, ctx.forced, ctx.zones,
                                      person_groups=self._person_groups, entity_groups=self._entity_groups)
            recognizers = self._native.recognizers
            for start, end, index, value, score, personal, reason in found:
                rec = recognizers[index]
                spans.append(Span(start, end, rec.entity, rec.label, rec.id, score, _priority(rec, value), value,
                                  personal, reason=reason))
            timings["native"] = timings.get("native", 0.0) + (perf_counter() - t0) * 1000
        for pack in self._packs:
            if pack.id not in active_packs:
                continue
            t0 = perf_counter()
            spans.extend(self._recognizer_spans(pack.id, ctx))
            for detector in self._detectors[pack.id]:
                spans.extend(self._detector_spans(detector, ctx))
            timings[f"pack:{pack.id}"] = (perf_counter() - t0) * 1000
        if not extras:
            return spans
        for detector in self._extra_detectors:
            t0 = perf_counter()
            spans.extend(self._detector_spans(detector, ctx))
            timings[f"detector:{getattr(detector, 'id', type(detector).__name__)}"] = (perf_counter() - t0) * 1000
        if self._deny is not None:
            spans.extend(self._deny_spans(ctx))
        if self._custom:
            t0 = perf_counter()
            spans.extend(self._custom_spans(ctx))
            timings["custom"] = (perf_counter() - t0) * 1000
        return spans

    def _recognizer_spans(self, pack_id: str, ctx: DetectionContext) -> list[Span]:
        """Recognizers d'un pack laissés à Python (motif ou validateur sans équivalent natif).

        A pack's recognizers left to Python (pattern or validator without a native equivalent).
        """
        spans: list[Span] = []
        for recognizer in self._python_recognizers[pack_id]:
            if recognizer.prefilter and not ctx.has(recognizer.prefilter):
                continue
            # Sans aucun mot-clé dans le texte, inutile de lancer la regex / no keyword, skip the regex.
            needs_context = recognizer.tier == "C" or (recognizer.tier == "B" and not ctx.strict)
            if needs_context and not ctx.any_context(recognizer.contexts):
                continue
            self._run(recognizer, ctx, spans)
        return spans

    def _detector_spans(self, detector: Any, ctx: DetectionContext) -> list[Span]:
        """Zones d'un détecteur, entités choisies seulement / a detector's spans, chosen entities only."""
        return [s for s in detector.detect(ctx) if self._entity_allowed(s.entity)]

    def _custom_spans(self, ctx: DetectionContext) -> list[Span]:
        """Règles de l'organisation, avec leurs propres mots-clés / the organisation's rules, own keywords."""
        spans: list[Span] = []
        if self._custom_native is not None:
            hits = self._custom_native.keywords(ctx.folded)
            segments = list(zip(ctx.seg_starts, ctx.seg_ends, strict=True)) if ctx.seg_starts is not None else None
            found = self._custom_native.scan(hits, ctx.text, ctx.folded, frozenset({CUSTOM_PACK}), ctx.strict,
                                             "keep", False, (), segments)
            for start, end, index, value, score, _personal, _reason in found:
                rec = self._custom[index]
                spans.append(Span(start, end, rec.entity, rec.label, rec.id, score, rec.priority, value, True))
            return spans
        hits = self._custom_keywords.scan(ctx.folded) if self._custom_keywords is not None else KeywordHits()
        own = DetectionContext(ctx.text, ctx.folded, hits, ctx.countries, ctx.language, self.settings,
                               ctx.seg_starts, ctx.seg_ends)
        for rec in self._custom:
            self._run(rec, own, spans)
        return spans

    def _run(self, rec: PatternRecognizer, ctx: DetectionContext, out: list[Span]) -> None:
        text = ctx.text
        search = rec.regex.search
        check_left, check_right = _BOUNDARIES[rec.boundary]
        skip = _SKIP_RUN.get(rec.boundary)
        validator = rec.validator
        needs_context = rec.tier in ("B", "C")
        pos = 0
        # `search` ramène une position au-delà du texte à sa fin : sans ce test, une règle qui peut correspondre
        # à vide bouclerait à la fin. `search` clamps a position past the end back to it: without this check, a
        # rule that can match empty would loop forever at the end.
        while pos <= len(text):
            m = search(text, pos)
            if m is None:
                return
            full_start, full_end = m.span()
            # Échec : on relance plus loin, sans avaler de candidat / retry further on, swallowing no candidate.
            if not (check_left(text, full_start) and check_right(text, full_end)):
                pos = _next_start(skip, text, full_start)
                continue
            start, end = m.span(rec.group)
            if start < 0:
                pos = full_start + 1
                continue
            candidate = text[start:end]
            value: str | None = candidate
            score = rec.score
            if validator is not None:
                value = validator(candidate)
                if value is None:
                    # Clé fausse : gardé en niveau L, ou si un mot-clé explicite l'accompagne (faute de frappe, OCR).
                    # Wrong key: kept for tier L, or when an explicit keyword comes with it (typo, OCR error).
                    if not (rec.tier == "L" or (rec.fallback and ctx.near(rec.contexts, start, end, rec.before,
                                                                          rec.after))):
                        pos = _next_start(skip, text, full_start)
                        continue
                    score *= 0.6
            has_context = (bool(rec.contexts) and ctx.near(rec.contexts, start, end, rec.before, rec.after)
                           and not (rec.vetoes and ctx.vetoed(rec.contexts, rec.vetoes, start, end, rec.after)))
            if needs_context and not has_context:
                if rec.tier == "C" or not ctx.strict:
                    pos = _next_start(skip, text, full_start)
                    continue
                score = 0.6
            elif has_context:
                score = min(1.0, score + 0.04)
            personal, reason = self._personal(rec, ctx, start, end)
            out.append(Span(start, end, rec.entity, rec.label, rec.id, score, _priority(rec, value), value,
                            personal, reason=reason))
            pos = full_end if full_end > full_start else full_start + 1

    def _personal(self, rec: PatternRecognizer, ctx: DetectionContext, start: int, end: int,
                  ) -> tuple[bool, str | None]:
        """Politique des identifiants de personnes morales : (personnel ?, raison propre ou None).

        Legal-entity identifier policy: (personal?, specific reason or None).
        """
        if rec.policy is None:
            return True, None
        if rec.policy == "facility":
            return self.settings.facility_ids == "mask" or ctx.strict, None
        mode = self.settings.company_ids
        if mode != "auto":
            return mode == "mask", None
        if ctx.strict:
            return True, None
        # « Entrepreneur individuel » n'importe où dans le document suffit : rappel d'abord. L'état civil d'une
        # personne physique (prénom, date de naissance) à côté du numéro désigne aussi son titulaire.
        # "Sole trader" anywhere in the document is enough: recall first. A natural person's civil status (given
        # name, birth date) next to the number also names its holder.
        if self._ei_groups and ctx.any_context(self._ei_groups):
            return True, "sole_trader"
        if self._person_groups and self._civil_status(ctx, start, end):
            return True, "civil_status_nearby"
        return False, None

    def _civil_status(self, ctx: DetectionContext, start: int, end: int) -> bool:
        """État civil d'une personne physique à côté du numéro, sans personne morale plus près.

        Sur la ligne du numéro : une personne morale l'emporte (« Employeur : TESTIVO, … SIRET … »), sinon l'état
        civil suffit (« M. Jean Dupont, né le …, RM … »). Ligne muette : le paragraphe, sans personne morale proche
        (« n° RCS : … ⏎ Nom : … ⏎ Prénom : … »). Jamais au-delà d'une ligne vide. On the number's line, a legal entity
        wins, otherwise the civil status is enough; on a silent line, the paragraph, with no nearby legal entity.
        Never past a blank line.
        """
        text = ctx.text
        line_lo, line_hi = _line_bounds(text, start, end, *NATURAL_PERSON_WINDOW)
        if self._entity_groups and ctx.near(self._entity_groups, start, end, *LEGAL_ENTITY_WINDOW, line_lo, line_hi):
            return False
        if ctx.near(self._person_groups, start, end, *NATURAL_PERSON_WINDOW, line_lo, line_hi):
            return True
        lo, hi = _block_bounds(text, start, end, *NATURAL_PERSON_WINDOW)
        return ctx.near(self._person_groups, start, end, *NATURAL_PERSON_WINDOW, lo, hi) and not (
            self._entity_groups and ctx.near(self._entity_groups, start, end, *LEGAL_ENTITY_WINDOW, lo, hi))

    def _deny_spans(self, ctx: DetectionContext) -> list[Span]:
        hits = self._deny.scan(ctx.folded) if self._deny else None
        spans: list[Span] = []
        if hits is None:
            return spans
        for group in hits.groups():
            label = group.split(":", 1)[1]
            for start, end in hits.occurrences(group):
                spans.append(Span(start, end, "CUSTOM", label, "deny_list", 1.0, 99, ctx.folded[start:end]))
        return spans

    def _finalize(self, ctx: DetectionContext, spans: list[Span]) -> list[Span]:
        if self._custom:
            spans = _apply_keep(spans)
        text = ctx.text
        minimum = self._min_score
        allow = self._allow
        kept = []
        for span in spans:
            if span.score < minimum or span.end <= span.start:
                continue
            if allow and fold(text[span.start:span.end]).strip() in allow:
                continue
            if span.entity == "PERSON":
                _trim_honorific(span, text)
                if span.end <= span.start:
                    continue
            if span.value is None and span.entity in MERGEABLE_ENTITIES:
                span.value = text[span.start:span.end]
            kept.append(span)
        if not kept:
            return []
        resolved = resolve(merge_same_entity(kept), text)
        resolved = self._propagate(ctx, resolved)
        for span in resolved:
            if span.value is None:
                span.value = text[span.start:span.end]
        resolved.sort(key=lambda s: s.start)
        return resolved

    def _propagate(self, ctx: DetectionContext, spans: list[Span]) -> list[Span]:
        """Masque toutes les autres occurrences des noms trouvés / masks every other occurrence of found names."""
        text = ctx.text
        sources: dict[str, Span] = {}
        for span in spans:
            if not span.propagate or not span.personal:
                continue
            for form in (text[span.start:span.end], *span.forms):
                form = form.strip()
                if len(form) >= 3 and any(c.isalpha() for c in form):
                    sources.setdefault(form, span)
                    upper = form.upper()
                    if upper != form:
                        sources.setdefault(upper, span)
        if not sources:
            return spans
        forms = list(sources)
        ordered = sorted(spans, key=lambda s: s.start)
        starts = [s.start for s in ordered]
        added = False
        for index, start, end in longest_matches(forms, text):
            if (start > 0 and text[start - 1].isalnum()) or (end < len(text) and text[end].isalnum()):
                continue
            i = bisect_right(starts, start) - 1
            if i >= 0 and ordered[i].end > start:
                continue
            if i + 1 < len(ordered) and ordered[i + 1].start < end:
                continue
            source = sources[forms[index]]
            seg = ctx.segment(start)
            if end > seg[2]:
                continue
            span = Span(start, end, source.entity, source.label, f"propagated:{source.source}",
                        source.score * 0.95, PRIORITY_PROPAGATED, None, True)
            k = bisect_left(starts, start)
            starts.insert(k, start)
            ordered.insert(k, span)
            added = True
        return ordered if added else spans

    # --- anonymisation ---

    def anonymize(self, text: str, scope: Scope | None = None) -> AnonymizedText:
        """Remplace chaque zone détectée ; la portée locale est détruite à la fin.

        Replaces every detected zone; a locally-created scope is destroyed at the end. Avec le moteur fusionné,
        un document ne quitte pas Rust de la détection au rendu, et aucun objet `Span` n'est créé tant qu'on ne
        lit pas `analysis.spans` ; une portée locale y naît et y meurt. With the fused engine, a document stays in
        Rust from detection to rendering, and no `Span` object is built unless `analysis.spans` is read; a local
        scope lives only there.
        """
        t0 = perf_counter()
        native_scope = _native_scope(scope)
        document = self._fused_document(text) if scope is None or native_scope is not None else None
        if document is not None:
            t1 = perf_counter()
            language = document.language
            # `explain` vrai au sens de Python (1, "oui"…), comme `_render_text` ; `sanitize_output` en Rust (jumeau
            # exact). Python truthiness, as there; `sanitize_output` in Rust (exact twin).
            done = document.anonymize(self._finalizer, native_scope, self._labels(scope, language, _display_all),
                                      bool(self.settings.explain), bool(self.settings.sanitize))
            if done is not None:
                output, replaced, kept, explain, spans = done
                timings = dict(document.timings)
                timings["resolve"] = (perf_counter() - t1) * 1000
                timings["total"] = (perf_counter() - t0) * 1000
                countries, reasons = self._fused_countries(document)
                analysis = Analysis.deferred(text, spans.objects, countries, reasons, language, timings)
                return AnonymizedText(output, analysis,
                                      self._report(language, countries, reasons, timings, replaced, kept, explain))
        ctx, detected, reasons, offsets, timings = self._fused_fallback(document) or self._detect_text(text)
        t1 = perf_counter()
        native = None
        if self._finalizer is not None and (scope is None or native_scope is not None):
            native = self._finalizer.anonymize(detected, ctx.text, _offset_bytes(offsets), text, native_scope,
                                               self._labels(scope, ctx.language), bool(self.settings.explain))
        if native is not None:
            output, spans, replaced, kept, explain = native
        else:
            spans = self._final_spans(ctx, detected, offsets)
            output, replaced, kept, explain = self._render_text(text, spans, scope, ctx.language)
        # Tout l'après-détection : résolution, propagation et rendu / all post-detection work.
        timings["resolve"] = (perf_counter() - t1) * 1000
        if self.settings.sanitize:
            output = sanitize_output(output)
        timings["total"] = (perf_counter() - t0) * 1000
        analysis = Analysis(text, spans, ctx.countries, reasons, ctx.language, timings)
        return AnonymizedText(output, analysis,
                              self._report(ctx.language, ctx.countries, reasons, timings, replaced, kept, explain))

    def _labels(self, scope: Scope | None, language: str, display: Callable[..., Any] = LABELS.display,
                ) -> tuple[Callable[..., Any], str, bool]:
        """Libellés affichés comme `Scope.label_text` : (fonction, langue, neutre) / displayed labels."""
        if scope is not None:
            return display, scope.label_language, scope.neutral
        return display, self._label_language(language), self.settings.neutral_labels

    def _render_text(self, text: str, spans: list[Span], scope: Scope | None, language: str,
                     ) -> tuple[str, Mapping[str, int], Mapping[str, int], list[dict[str, Any]] | None]:
        """Rendu Python d'un texte ; une portée locale est détruite à la fin / Python rendering of one text."""
        own_scope = scope is None
        if scope is None:
            scope = self.new_scope(language)
        explain: list[dict[str, Any]] | None = [] if self.settings.explain else None
        try:
            scope.reserve(text)
            output, replaced, kept = self._render(text, spans, scope, explain)
        finally:
            if own_scope:
                scope.close()
        return output, replaced, kept, _aggregate(explain) if explain is not None else None

    def anonymize_segments(self, texts: Sequence[str], scope: Scope,
                           forced: Sequence[frozenset[str]] | None = None) -> tuple[list[str], dict[str, Any]]:
        """Anonymise des segments (cellules) avec une portée partagée / segments with a shared scope.

        Avec le moteur fusionné : détection et rendu en Rust, aucun objet Python par zone / with the fused
        engine: detection and rendering in Rust, no Python object per span.
        """
        _check_forced(texts, forced)
        native_scope = _native_scope(scope)
        document = self._fused_cells(texts, forced) if native_scope is not None else None
        if document is not None:
            done = document.anonymize_cells(self._finalizer, native_scope,
                                            self._labels(scope, document.language, _display_all),
                                            bool(self.settings.explain), bool(self.settings.sanitize))
            if done is not None:
                outputs, replaced, kept, explain = done
                countries, reasons = self._fused_countries(document)
                return outputs, self._report(document.language, countries, reasons, dict(document.timings),
                                             replaced, kept, explain)
        staged = self._fused_cells_fallback(document) or self._detect_segments(texts, forced)
        ctx, detected, reasons, normalized, timings = staged
        native = None
        if self._finalizer is not None and native_scope is not None:
            native = self._finalizer.anonymize_segments(
                detected, ctx.text, ctx.seg_starts, ctx.seg_ends, [_offset_bytes(o) for _, o in normalized],
                list(texts), native_scope, self._labels(scope, ctx.language), bool(self.settings.explain))
        if native is not None:
            outputs, replaced, kept, explain = native
            if self.settings.sanitize:
                outputs = [sanitize_output(out) for out in outputs]
        else:
            per_segment, _ = self._segment_spans(ctx, detected, normalized)
            outputs = []
            replaced, kept = Counter(), Counter()
            entries: list[dict[str, Any]] | None = [] if self.settings.explain else None
            for text, segment_spans in zip(texts, per_segment, strict=True):
                out, rep, kep = self._render(text, segment_spans, scope, entries)
                outputs.append(sanitize_output(out) if self.settings.sanitize else out)
                replaced.update(rep)
                kept.update(kep)
            explain = _aggregate(entries) if entries is not None else None
        return outputs, self._report(ctx.language, ctx.countries, reasons, timings, replaced, kept, explain)

    def new_scope(self, language: str = "und") -> Scope:
        return Scope(self._label_language(language), self.settings.neutral_labels, native=self.settings.native)

    def _label_language(self, detected: str) -> str:
        if self.settings.label_language != "auto":
            return self.settings.label_language
        return "fr" if detected in ("fr", "und") else "en"

    def _render(self, text: str, spans: Sequence[Span], scope: Scope, explain: list[dict[str, Any]] | None = None,
                ) -> tuple[str, Counter[str], Counter[str]]:
        parts: list[str] = []
        replaced: Counter[str] = Counter()
        kept: Counter[str] = Counter()
        last = 0
        for span in spans:
            if not span.personal:
                kept[span.label] += 1
                if explain is not None:
                    explain.append({"kept": scope.label_text(span.label), "rule": _rule_of(span),
                                    "reason": "keep_rule" if span.source.startswith("keep:") else "company_policy"})
                continue
            original = text[span.start:span.end]
            operator = self._operators.get(span.entity) or self._operators.get(span.label) or self._default_operator
            if span.entity in FORCED_REPLACE:
                operator = self._default_operator
            parts.append(text[last:span.start])
            output = operator(span, original, scope)
            parts.append(output)
            last = span.end
            replaced[scope.label_text(span.label)] += 1
            if explain is not None:
                # La balise produite, jamais la valeur d'origine / the produced tag, never the original value.
                explain.append({"tag": output, "rule": _rule_of(span), "reason": self._reason(span)})
        parts.append(text[last:])
        return "".join(parts), replaced, kept

    def _reason(self, span: Span) -> str:
        """Raison stable et documentée d'une détection (docs/EXPLAIN.md) / stable, documented reason code."""
        source = span.source.split("+", 1)[0]
        if source.startswith("propagated:"):
            return "propagation"
        if source == "deny_list":
            return "deny_list"
        if source.startswith("CUSTOM_"):
            return "custom_rule"
        if span.reason is not None:
            return span.reason  # raison propre à la règle (« civil_status_nearby ») / the rule's own reason
        if source == "INTL_IBAN":
            return "validated" if span.value is not None else "iban_layout_despite_invalid_key"
        reason = _DETECTOR_REASONS.get(source) or ("ner_model" if source.lower().startswith("ner") else None)
        if reason is not None:
            return reason
        rec = self._recognizer_index().get(source)
        if rec is None:
            return "detector"
        # « validated » : clé de contrôle ou règles officielles vérifiées (plan de numérotation, calendrier…).
        # "validated": checksum or official rules checked (numbering plan, calendar…).
        if rec.tier == "L":
            return "validated" if span.value is not None else "printed_layout"
        if rec.validator is not None and span.value is None:
            return "keyword_despite_invalid_key"  # clé fausse, mot-clé explicite / wrong key, explicit keyword
        if rec.validator is not None:
            return "validated" if rec.tier == "A" else "validated_and_keyword"
        return "format" if rec.tier == "A" else "keyword"

    def _recognizer_index(self) -> dict[str, PatternRecognizer]:
        return _recognizers_by_id(tuple(p.id for p in self._packs))

    def _report(self, language: str, countries: Sequence[str], reasons: dict[str, list[str]],
                timings: Mapping[str, float], replaced: Mapping[str, int], kept: Mapping[str, int],
                explain: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        """Rapport ; `explain` : lignes déjà agrégées (`_aggregate`) / report; `explain`: aggregated lines."""
        mode = self.settings.countries if isinstance(self.settings.countries, str) else "explicit"
        report: dict[str, Any] = {
            "entities": dict(sorted(replaced.items())),
            "kept_by_policy": dict(sorted(kept.items())),
            "total_replaced": sum(replaced.values()),
            "country_mode": mode,
            "countries": list(countries),
            "country_reasons": reasons,
            "language": language,
            "profile": self.settings.profile,
            "native": self.native,
            "timings_ms": {k: round(v, 3) for k, v in timings.items()},
            "irreversible": True,
            "notice": NOTICE_FR if self._label_language(language) == "fr" else NOTICE_EN,
        }
        warnings = ["country_mode=auto est expérimental / is experimental"] if mode == "auto" else []
        if "FR" not in countries:
            warnings.append(NAMES_FRENCH_ONLY)
        if warnings:
            report["warnings"] = warnings
        if self.settings.rules is not None:
            report["rules"] = self.settings.rules.name
        if explain is not None:
            report["explain"] = explain
        return report


# Raisons des détecteurs (docs/EXPLAIN.md) / detector reason codes.
_DETECTOR_REASONS = {
    "EMAIL": "format", "INTL_MRZ": "format", "INTL_PHONE": "phone_numbering_plan", "FR_NAMES": "name_lexicon",
    "FR_ADDRESS": "postcode_and_town", "ORGANIZATIONS": "legal_form", "FR_NIR_BIRTH_DATE": "matches_nir",
    "NER": "ner_model",
}


def _check_forced(texts: Sequence[str], forced: Sequence[frozenset[str]] | None) -> None:
    """Groupes imposés : un ensemble par segment, sur les deux chemins / forced groups: one set per segment."""
    if forced is not None and len(forced) != len(texts):
        raise ValueError("forced : un ensemble par segment / one forced set per segment")


def _native_scope(scope: Scope | None) -> Any:
    """Portée Rust d'une `Scope` exacte (pas d'une sous-classe), sinon None / Rust scope of an exact `Scope`."""
    return scope._native_scope if type(scope) is Scope else None


def _offset_bytes(offsets: Any) -> bytes | None:
    """Table de positions de `normalize` (`array('q')`) pour le noyau / `normalize`'s offset map for the core."""
    return offsets.tobytes() if offsets is not None else None


def _display_all(keys: Sequence[str], language: str, neutral: bool) -> list[str]:
    """`LABELS.display` de plusieurs clés, en un seul appel du moteur fusionné / in one fused-engine call."""
    display = LABELS.display
    return [display(key, language, neutral) for key in keys]


def _offset_array(raw: bytes | None) -> array | None:
    """Table de positions rendue par le noyau, en `array('q')` comme `normalize` / the core's offset map."""
    if raw is None:
        return None
    offsets = array("q")
    offsets.frombytes(raw)
    return offsets


def _rule_of(span: Span) -> str:
    """Règle à l'origine d'une zone, préfixes retirés / rule behind a span, prefixes removed."""
    source = span.source.split("+", 1)[0]
    for prefix in ("keep:", "propagated:"):
        if source.startswith(prefix):
            source = source[len(prefix):]
    return source


@cache
def _recognizers_by_id(pack_ids: tuple[str, ...]) -> dict[str, PatternRecognizer]:
    return {r.id: r for pack_id in pack_ids for r in load_pack(pack_id).recognizers}


def _aggregate(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Une ligne par (balise, règle, raison), avec le nombre d'occurrences / one line per tag, rule, reason."""
    lines: dict[tuple[Any, ...], dict[str, Any]] = {}
    for entry in entries:
        key = tuple(entry.items())
        line = lines.get(key)
        if line is None:
            lines[key] = {**entry, "count": 1}
        else:
            line["count"] += 1
    return list(lines.values())


# Identifiants officiels qu'une règle « keep » ne démasque jamais une fois leur clé validée.
# Official identifiers that a keep rule never unmasks once their checksum is validated.
_UNMASKABLE = frozenset({"NATIONAL_ID", "TAX_ID", "SOCIAL_ID", "IBAN", "BANK_ACCOUNT", "CARD", "PASSPORT", "ID_CARD",
                         "DRIVER_LICENSE", "MRZ", "SECRET", "CRYPTO"})


def _apply_keep(spans: list[Span]) -> list[Span]:
    """Zones « keep » d'une règle : les détections entièrement comprises dans une zone restent en clair, sauf un
    identifiant officiel validé par sa clé (NIR, IBAN, carte…), que rien ne démasque. Une détection qui déborde
    reste masquée (rappel d'abord). Keep zones leave detections fully inside them in clear, except a validated
    official identifier; a detection that sticks out stays masked (recall first).
    """
    keep = sorted((s.start, s.end, s.source) for s in spans if s.entity == KEEP_ENTITY)
    if not keep:
        return spans
    starts = [k[0] for k in keep]
    reach: list[int] = []  # fin la plus lointaine parmi les zones 0..i / furthest end among zones 0..i
    owner: list[str] = []
    for _start, end, source in keep:
        if not reach or end > reach[-1]:
            reach.append(end)
            owner.append(source)
        else:
            reach.append(reach[-1])
            owner.append(owner[-1])
    kept = []
    for span in spans:
        if span.entity == KEEP_ENTITY:
            continue
        # Zones commençant avant la détection : la plus lointaine la contient-elle ? / does the furthest one contain it?
        i = bisect_right(starts, span.start) - 1
        protected = span.priority >= PRIORITY_VALIDATED and span.entity in _UNMASKABLE
        if not protected and i >= 0 and reach[i] >= span.end:
            span.personal = False
            span.source = f"keep:{owner[i]}"
        kept.append(span)
    return kept


def _trim_honorific(span: Span, text: str) -> None:
    """Laisse « M. », « Mme »… hors de la zone (accords grammaticaux) / keeps honorifics outside the span."""
    while True:
        segment = text[span.start:span.end]
        token_end = 0
        while token_end < len(segment) and (segment[token_end].isalpha()):
            token_end += 1
        if token_end == 0 or fold(segment[:token_end]) not in HONORIFICS:
            return
        rest = token_end
        while rest < len(segment) and segment[rest] in ".  ":
            rest += 1
        if rest >= len(segment):
            return
        span.start += rest


@cache
def default_anonymizer() -> Anonymizer:
    return Anonymizer()


def anonymize(text: str, **settings: Any) -> AnonymizedText:
    """Raccourci / shortcut: `anonymize("Jean Dupont, NIR 1 85 05 78 006 084 91")`."""
    anonymizer = Anonymizer(**settings) if settings else default_anonymizer()
    return anonymizer.anonymize(text)


__all__ = ["PRIORITY_HEURISTIC", "Anonymizer", "DetectionContext", "Settings", "anonymize", "resolve"]
