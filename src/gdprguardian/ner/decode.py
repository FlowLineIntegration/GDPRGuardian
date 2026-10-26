"""Logits -> décisions par jeton -> suites d'entités, vectorisé avec numpy.

Logits -> per-token decisions -> entity runs, vectorised with numpy.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np

# Étiquette du modèle (sans préfixe B-/I-) -> entité Gardien RGPD / model tag (no B-/I- prefix) -> entity.
ENTITY_TAGS: Mapping[str, str] = {
    "PER": "PERSON", "PERSON": "PERSON", "ORG": "ORG", "ORGANIZATION": "ORG",
    "LOC": "LOCATION", "LOCATION": "LOCATION", "GPE": "LOCATION",
}
_PREFIXES = ("B-", "I-", "E-", "S-", "L-", "U-")


@dataclass(frozen=True, slots=True)
class LabelScheme:
    """Projection des classes du modèle sur les entités / projection of model classes onto entities.

    `type_matrix` (C, K) additionne B-x et I-x ; `begin_matrix` (C, K) ne garde que les débuts (B-, S-, U-).
    `type_matrix` (C, K) sums B-x and I-x; `begin_matrix` (C, K) keeps only begin classes.
    """

    entities: tuple[str, ...]
    type_matrix: np.ndarray
    begin_matrix: np.ndarray
    has_begin: bool

    @property
    def classes(self) -> int:
        return self.type_matrix.shape[0]

    @classmethod
    def from_labels(cls, id2label: Mapping[int, str], tags: Mapping[str, str] = ENTITY_TAGS) -> LabelScheme:
        size = max(id2label) + 1
        parsed: list[tuple[int, str, bool]] = []
        for index, label in id2label.items():
            upper = label.upper()
            prefix = next((p for p in _PREFIXES if upper.startswith(p)), "")
            entity = tags.get(upper[len(prefix):])
            if entity is not None:
                parsed.append((index, entity, prefix in ("B-", "S-", "U-")))
        entities = tuple(dict.fromkeys(entity for _, entity, _ in sorted(parsed)))
        if not entities:
            raise ValueError("aucune étiquette PER/ORG/LOC / no PER/ORG/LOC label in the model")
        type_matrix = np.zeros((size, len(entities)), np.float32)
        begin_matrix = np.zeros((size, len(entities)), np.float32)
        for index, entity, begin in parsed:
            column = entities.index(entity)
            type_matrix[index, column] = 1.0
            if begin:
                begin_matrix[index, column] = 1.0
        return cls(entities, type_matrix, begin_matrix, bool(begin_matrix.any()))


def softmax(logits: np.ndarray) -> np.ndarray:
    """Softmax stable en float32, en place / stable float32 softmax, in place."""
    probs = np.asarray(logits, dtype=np.float32)
    probs -= probs.max(axis=-1, keepdims=True)
    np.exp(probs, out=probs)
    probs /= probs.sum(axis=-1, keepdims=True)
    return probs


def token_decisions(logits: np.ndarray, scheme: LabelScheme, thresholds: np.ndarray,
                    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(entité ou -1, masse d'entité, début forcé) par jeton / (entity or -1, entity mass, forced begin).

    La masse est la somme des probabilités des types voulus (seuil fini), hors O et MISC ; le type est le plus
    probable d'entre eux. Un jeton partagé entre deux types (« Malletier » : lieu 0,48, organisation 0,42) reste
    une entité, même sous O : le rappel prime. Mass = summed probability of the wanted types (finite threshold),
    excluding O and MISC; type = the most likely of them. A token split between two types stays an entity.
    """
    probs = softmax(logits)
    by_type = probs @ scheme.type_matrix
    wanted = np.isfinite(thresholds)
    if not wanted.all():
        by_type[..., ~wanted] = 0.0
    best = by_type.argmax(axis=-1)
    mass = by_type.sum(axis=-1)
    entity = np.where(mass >= thresholds[best], best, -1).astype(np.int8)
    if scheme.has_begin:
        take = best[..., None]
        begin_prob = np.take_along_axis(probs @ scheme.begin_matrix, take, axis=-1)[..., 0]
        begin = begin_prob * 2.0 > np.take_along_axis(by_type, take, axis=-1)[..., 0]
    else:
        begin = np.zeros(entity.shape, dtype=bool)
    return entity, mass, begin


@dataclass(frozen=True, slots=True)
class Runs:
    """Suites de jetons de même entité et leur masse maximale / same-entity token runs and peak score."""

    first: np.ndarray
    stop: np.ndarray
    entity: np.ndarray
    score: np.ndarray

    def select(self, keep: np.ndarray) -> Runs:
        return Runs(self.first[keep], self.stop[keep], self.entity[keep], self.score[keep])


def _bounds(first: np.ndarray, stop: np.ndarray) -> np.ndarray:
    """Indices entrelacés pour `reduceat` sur [first, stop) / interleaved indices for `reduceat`."""
    bounds = np.empty(first.size * 2, np.intp)
    bounds[0::2] = first
    bounds[1::2] = stop
    return bounds


def group_runs(entity: np.ndarray, score: np.ndarray, begin: np.ndarray, breaks: np.ndarray) -> Runs:
    """Regroupe les jetons consécutifs de même entité ; `breaks` force une coupure (début d'unité).

    Groups consecutive same-entity tokens; `breaks` forces a cut (unit start). Score = maximum de la suite.
    """
    n = entity.shape[0]
    positive = entity >= 0
    new_run = positive.copy()
    if n > 1:
        new_run[1:] &= (entity[1:] != entity[:-1]) | begin[1:] | breaks[1:]
    first = np.flatnonzero(new_run)
    if first.size == 0:
        empty = np.zeros(0, np.intp)
        return Runs(empty, empty, np.zeros(0, np.int8), np.zeros(0, np.float32))
    cuts = np.append(np.flatnonzero(~(positive & ~new_run)), n)
    stop = cuts[np.searchsorted(cuts, first, side="right")]
    padded = np.append(score.astype(np.float32, copy=False), np.float32(0))
    peak = np.maximum.reduceat(padded, _bounds(first, stop))[0::2]
    return Runs(first, stop, entity[first], peak)


def run_extents(starts: np.ndarray, ends: np.ndarray, runs: Runs) -> tuple[np.ndarray, np.ndarray]:
    """Étendue en caractères de chaque suite (min des débuts, max des fins) / character extent of each run."""
    if runs.first.size == 0:
        empty = np.zeros(0, np.int64)
        return empty, empty
    bounds = _bounds(runs.first, runs.stop)
    lo = np.minimum.reduceat(np.append(starts, 0), bounds)[0::2]
    hi = np.maximum.reduceat(np.append(ends, 0), bounds)[0::2]
    return lo, hi
