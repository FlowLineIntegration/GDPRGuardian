"""Détecteur NER ONNX (personnes, organisations, lieux), local, sans torch ni réseau.

Local ONNX NER detector (persons, organisations, locations), no torch, no network.
"""

from __future__ import annotations

import copy
import logging
import math
import os
import re
import threading
from bisect import bisect_right
from collections.abc import Collection, Iterator, Mapping
from itertools import groupby
from operator import itemgetter
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np

from .._text import fold
from ..scope import PLACEHOLDER_RE, split_person_name
from ..types import PRIORITY_NER, Span
from .chunking import CAPITAL_RE, has_signal, split_units
from .lexicon import COMMON_STARTERS, LEADING_PERSON_WORDS, STOP_SPANS
from .registry import DISTILCAMEMBERT_NER, ModelSpec, find_model_dir, model_files, verify_files
from .runtime import TokenClassifier

logger = logging.getLogger(__name__)

ENTITIES = ("PERSON", "ORG", "LOCATION")
# Seuils par type sur la masse d'entité (decode.token_decisions), égaux ou supérieurs au `min_score` du profil,
# sinon le moteur écarterait la zone ; strict : rappel maximal. Per-type thresholds on the entity mass, at least
# the profile's `min_score` (else the engine drops the zone); strict: maximal recall.
DEFAULT_THRESHOLDS: Mapping[str, float] = {"PERSON": 0.5, "ORG": 0.5, "LOCATION": 0.5}
STRICT_THRESHOLDS: Mapping[str, float] = {"PERSON": 0.3, "ORG": 0.35, "LOCATION": 0.35}

# Mise en forme Markdown et sauts de ligne -> espaces, longueur conservée / markup -> spaces, same length.
_MODEL_INPUT = str.maketrans(dict.fromkeys("\n\r\t\v\f*#`>", " "))
# Élision minuscule devant le nom (« d'Orléans ») ; « L'Oréal », « N'Diaye » restent / lowercase elision only.
_ELISION_RE = re.compile(r"(?:[cdjlmnst]|qu|jusqu|lorsqu|puisqu)['’](?=[^\W\d_])")
_LEADING_WORD_RE = re.compile(r"([^\W\d_]{1,40})\.?[\s,]{1,8}")
# Particule orpheline en fin de zone (« Ollivier d ») / dangling particle at the end of a zone.
_TRAILING_PARTICLE_RE = re.compile(r"\s(?:d|de|du|des|la|le|les|von|van|der|den|di|da|del|dos|das)$")
_SPACES_RE = re.compile(r"\s{1,64}")
# Séparateurs qui joignent deux suites d'une même entité : « d'Orléans », « Saint-Malo » / run joiners.
_JOINERS = frozenset("'’-")


def _joins(text: str, i: int, lo: int, hi: int) -> bool:
    """Le caractère i prolonge-t-il le mot (lettre, chiffre, trait d'union interne) / part of the word?"""
    ch = text[i]
    if ch.isalnum():
        return True
    return ch == "-" and lo < i < hi - 1 and text[i - 1].isalnum() and text[i + 1].isalnum()


def _trim(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and not text[start].isalnum():
        start += 1
    while end > start and not text[end - 1].isalnum():
        end -= 1
    return start, end


def _cells(text: str, start: int, end: int) -> Iterator[tuple[int, int]]:
    """Morceaux entre barres de tableau : une zone ne traverse jamais une cellule ; un saut de ligne interne
    à une unité est un retour souple (chunking.split_units). Pieces between table bars: a zone never crosses
    a cell; a newline inside a unit is a soft wrap.
    """
    while start < end:
        bar = text.find("|", start, end)
        stop = end if bar < 0 else bar
        yield start, stop
        start = stop + 1


def _outside(start: int, end: int, starts: list[int], ends: list[int]) -> Iterator[tuple[int, int]]:
    """Morceaux de [start, end) hors des balises déjà présentes (triées, disjointes) : sinon « [ORG_2] »
    deviendrait « [[ORG_1]] ». Pieces outside placeholders already in the input, else they get rewritten.
    """
    i = bisect_right(ends, start)
    while i < len(starts) and starts[i] < end:
        if starts[i] > start:
            yield start, starts[i]
        start = max(start, ends[i])
        i += 1
    if start < end:
        yield start, end


class _SharedModel:
    """Modèle vérifié puis chargé une seule fois, au premier usage, et partagé / verified, loaded once, shared.

    Double verrouillage : la session ONNX et le tokenizer ne sont créés qu'une fois, même sous concurrence.
    Double-checked locking: the ONNX session and tokenizer are created once, even under concurrency.
    """

    def __init__(self, directory: Path | None, spec: ModelSpec | None, files: tuple[str, str, str], *,
                 threads: int, verify: bool, classifier: TokenClassifier | None = None) -> None:
        if directory is None and classifier is None:
            raise ValueError("dossier ou classifieur requis / directory or classifier required")
        self.directory = directory
        self.spec = spec
        self.files = files
        self.threads = threads
        self.verify = verify and spec is not None
        self._classifier = classifier
        self._lock = threading.Lock()

    @property
    def loaded(self) -> bool:
        return self._classifier is not None

    def get(self) -> TokenClassifier:
        classifier = self._classifier
        if classifier is None:
            with self._lock:
                classifier = self._classifier
                if classifier is None:
                    classifier = self._classifier = self._load()
        return classifier

    def _load(self) -> TokenClassifier:
        if self.directory is None:  # impossible, exigé par __init__ / unreachable, required by __init__
            raise RuntimeError("dossier du modèle manquant / missing model directory")
        if self.verify and self.spec is not None:
            verify_files(self.directory, self.spec, self.files)
        t0 = perf_counter()
        model, tokenizer, config = (self.directory / name for name in self.files)
        classifier = TokenClassifier.load(model, tokenizer, config, threads=self.threads)
        logger.info("NER chargé / loaded in %.0f ms", (perf_counter() - t0) * 1000)
        return classifier


class NerDetector:
    """NER par classification de jetons ONNX (distilcamembert-base-ner par défaut).

    ONNX token-classification NER (distilcamembert-base-ner by default). La session est vérifiée (SHA-256) et
    chargée au premier appel, partagée et sûre entre threads ; seules les phrases portant un signal (majuscule
    hors mot d'attaque courant, civilité) passent par le modèle. The session is verified and loaded on first use,
    shared and thread-safe; only sentences with a cue reach the model. Inactif en profil `fast` / off in `fast`.
    """

    id = "NER"

    def __init__(self, model_dir: str | os.PathLike[str] | None = None, *,
                 spec: ModelSpec | None = DISTILCAMEMBERT_NER, model_file: str | None = None,
                 threads: int | None = None, max_tokens: int = 256, overlap: int = 32, batch_tokens: int = 512,
                 thresholds: Mapping[str, float] | None = None, strict_thresholds: Mapping[str, float] | None = None,
                 entities: Collection[str] = ENTITIES, gating: bool = True, verify: bool = True,
                 classifier: TokenClassifier | None = None) -> None:
        self._configure(max_tokens=max_tokens, overlap=overlap, batch_tokens=batch_tokens,
                        thresholds={**DEFAULT_THRESHOLDS, **(thresholds or {})},
                        strict_thresholds={**STRICT_THRESHOLDS, **(strict_thresholds or {})},
                        entities=entities, gating=gating)
        files = model_files(spec, model_file)
        if classifier is None and model_dir is None:
            if spec is None:
                raise ValueError("model_dir requis sans spec / model_dir required without spec")
            model_dir = find_model_dir(spec, files[0])
            if model_dir is None:
                raise FileNotFoundError(f"modèle NER absent / NER model not found: {spec.name} "
                                        "(python tools/download_models.py)")
        self._model = _SharedModel(Path(model_dir) if model_dir is not None else None, spec, files,
                                  threads=threads or min(4, os.cpu_count() or 1), verify=verify,
                                  classifier=classifier)

    def _configure(self, *, max_tokens: int, overlap: int, batch_tokens: int, thresholds: Mapping[str, float],
                   strict_thresholds: Mapping[str, float], entities: Collection[str], gating: bool) -> None:
        if not 16 <= max_tokens <= 512:
            raise ValueError("max_tokens ∈ [16, 512]")
        if not 0 <= overlap <= (max_tokens - 2) // 4:
            raise ValueError("overlap ∈ [0, (max_tokens - 2) / 4]")
        if batch_tokens < 1:
            raise ValueError("batch_tokens >= 1")
        unknown = (set(entities) | set(thresholds) | set(strict_thresholds)) - set(ENTITIES)
        if unknown:
            raise ValueError(f"entités inconnues / unknown entities: {sorted(unknown)}")
        if not all(0.0 < v <= 1.0 for v in (*thresholds.values(), *strict_thresholds.values())):
            raise ValueError("seuils ∈ ]0, 1] / thresholds in (0, 1]")
        self.max_tokens = max_tokens
        self.overlap = overlap
        self.batch_tokens = batch_tokens
        self.thresholds = dict(thresholds)
        self.strict_thresholds = dict(strict_thresholds)
        self.entities = frozenset(entities)
        self.gating = gating

    def replace(self, **changes: Any) -> NerDetector:
        """Autres réglages, même modèle et même session (chargée une fois) / other settings, same shared session.

        Modifiables / changeable: max_tokens, overlap, batch_tokens, thresholds, strict_thresholds, entities, gating.
        """
        current = {"max_tokens": self.max_tokens, "overlap": self.overlap, "batch_tokens": self.batch_tokens,
                   "thresholds": self.thresholds, "strict_thresholds": self.strict_thresholds,
                   "entities": self.entities, "gating": self.gating}
        unknown = changes.keys() - current.keys()
        if unknown:
            raise ValueError(f"réglages non modifiables / not replaceable: {sorted(unknown)}")
        for key in ("thresholds", "strict_thresholds"):
            if key in changes:
                changes[key] = {**current[key], **changes[key]}
        clone = copy.copy(self)
        clone._configure(**{**current, **changes})
        return clone

    def __repr__(self) -> str:
        name = self.spec.name if self.spec is not None else "custom"
        return f"NerDetector(model={name!r}, file={self.files[0]!r}, loaded={self.loaded})"

    # --- modèle / model ---

    @property
    def spec(self) -> ModelSpec | None:
        return self._model.spec

    @property
    def model_dir(self) -> Path | None:
        return self._model.directory

    @property
    def files(self) -> tuple[str, str, str]:
        """(modèle ONNX, tokenizer, configuration) / (ONNX model, tokenizer, config) file names."""
        return self._model.files

    @property
    def loaded(self) -> bool:
        return self._model.loaded

    def warmup(self) -> None:
        """Vérifie, charge et exécute une fois (sonde de disponibilité) / verify, load, run once (readiness)."""
        classifier = self._model.get()
        classifier.predict(["Jean Dupont habite à Lyon."], self._threshold_vector(classifier, self.entities, False),
                           max_tokens=self.max_tokens, overlap=self.overlap, batch_tokens=self.batch_tokens)

    # --- détection / detection ---

    def _wanted(self, settings: Any) -> frozenset[str]:
        allowed = self.entities - frozenset(settings.exclude_entities)
        return allowed if settings.entities is None else allowed & frozenset(settings.entities)

    def _threshold_vector(self, classifier: TokenClassifier, wanted: Collection[str], strict: bool) -> np.ndarray:
        table = self.strict_thresholds if strict else self.thresholds
        return np.array([table[e] if e in wanted else math.inf for e in classifier.entities], np.float32)

    def detect(self, ctx: Any) -> list[Span]:
        settings = ctx.settings
        if settings.profile == "fast":
            return []
        wanted = self._wanted(settings)
        if not wanted:
            return []
        t0 = perf_counter()
        text = ctx.text
        segments = list(zip(ctx.seg_starts, ctx.seg_ends, strict=True)) if ctx.seg_starts is not None \
            else [(0, len(text))]
        units = split_units(text, segments)
        candidates = len(units)
        if self.gating:
            folded = ctx.folded
            units = [u for u in units if has_signal(text, folded, u[0], u[1])]
        if not units:
            return []
        # Phrases identiques (cellules, signatures) : une seule inférence / identical units inferred once.
        occurrences: dict[str, list[int]] = {}
        for start, end in units:
            occurrences.setdefault(text[start:end], []).append(start)
        distinct = list(occurrences)
        classifier = self._model.get()
        prediction = classifier.predict(
            [unit.translate(_MODEL_INPUT) for unit in distinct],
            self._threshold_vector(classifier, wanted, ctx.strict),
            max_tokens=self.max_tokens, overlap=self.overlap, batch_tokens=self.batch_tokens)
        spans: list[Span] = []
        names = classifier.entities
        placeholders = [m.span() for m in PLACEHOLDER_RE.finditer(text)] if "[" in text else []
        starts = [s for s, _ in placeholders]
        ends = [e for _, e in placeholders]
        rows = zip(prediction.text_index.tolist(), prediction.start.tolist(), prediction.end.tolist(),
                   prediction.entity.tolist(), prediction.score.tolist(), strict=True)
        for index, unit_rows in groupby(rows, key=itemgetter(0)):
            unit = distinct[index]
            zones = _whole_words(unit, [row[1:] for row in unit_rows], not classifier.scheme.has_begin)
            for start, end, entity, score in zones:
                for base in occurrences[unit]:
                    for lo, hi in _outside(base + start, base + end, starts, ends):
                        _emit(text, lo, hi, names[entity], score, spans)
        logger.debug("ner: %d/%d unités, %d distinctes, %d séquences, %d jetons, %d zones, %.1f ms",
                     len(units), candidates, len(distinct), prediction.sequences, prediction.tokens, len(spans),
                     (perf_counter() - t0) * 1000)
        return spans


def _whole_words(unit: str, runs: list[tuple[int, int, int, float]], join_spaces: bool,
                 ) -> list[tuple[int, int, int, float]]:
    """Étend chaque suite au mot entier puis joint les voisines de même entité.

    Extends each run to whole words, then joins same-entity neighbours that touch or are separated by one
    apostrophe or hyphen (« d'Orléans »), or by spaces when the label scheme cannot mark entity starts (IO).
    """
    zones: list[list[Any]] = []
    size = len(unit)
    for start, end, entity, score in runs:
        while start > 0 and _joins(unit, start - 1, 0, size):
            start -= 1
        while end < size and _joins(unit, end, 0, size):
            end += 1
        if zones and zones[-1][2] == entity:
            previous = zones[-1]
            gap = unit[previous[1]:start]
            if start <= previous[1] or gap in _JOINERS or (join_spaces and not gap.strip(" \t")):
                previous[1] = max(previous[1], end)
                previous[3] = max(previous[3], score)
                continue
        zones.append([start, end, entity, score])
    return [(start, end, entity, score) for start, end, entity, score in zones]


def _emit(text: str, start: int, end: int, entity: str, score: float, out: list[Span]) -> None:
    """Nettoie une zone : sans cellule, élision, civilité ni particule / cleans a zone."""
    person = entity == "PERSON"
    for piece in _cells(text, start, end):
        s, e = _trim(text, *piece)
        elision = _ELISION_RE.match(text, s, e)
        if elision is not None:
            s = elision.end()
        if person:
            while (lead := _LEADING_WORD_RE.match(text, s, e)) is not None \
                    and fold(lead.group(1)) in LEADING_PERSON_WORDS:
                s = lead.end()
        elif s < e and text[s].islower():
            # « hôpital Necker » -> « Necker » ; jamais pour une personne écrite en minuscules.
            # Leading common words dropped for ORG/LOC only (lowercase person names stay whole).
            capital = CAPITAL_RE.search(text, s, e)
            if capital is not None:
                s = capital.start()
        particle = _TRAILING_PARTICLE_RE.search(text, max(s, e - 6), e)
        if particle is not None and particle.start() > s:
            e = particle.start()
        if e - s < 2 or not any(c.isalpha() for c in text[s:e]):
            continue
        value = text[s:e]
        if _SPACES_RE.sub(" ", fold(value)) in STOP_SPANS:
            continue
        out.append(Span(s, e, entity, entity, "ner", score, PRIORITY_NER,
                        forms=_surname_form(value) if person else (), propagate=person))


def _surname_form(value: str) -> tuple[str, ...]:
    """Nom de famille seul, à propager s'il commence par une majuscule et n'est pas un mot courant.

    Lone surname, propagated when capitalised and not a common word: « jean blanc » écrit en minuscules ne doit
    pas masquer chaque « blanc » du document / a lowercase "jean blanc" must not mask every "blanc".
    """
    parsed = split_person_name(value)
    if parsed is None or parsed[0] is None:
        return ()
    surname = parsed[1]
    key = fold(surname)
    if len(surname) < 3 or not surname[0].isupper() or key in COMMON_STARTERS or key in STOP_SPANS \
            or surname not in value:
        return ()
    return (surname,)
