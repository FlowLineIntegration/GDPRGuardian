"""Indice de confiance et bootstrap stratifié / confidence index and stratified bootstrap.

Indice = moyenne, à poids ÉGAL par famille, de la part des documents (ayant au moins une mention directe) dont
aucune mention directe ne reste lisible. IC à 95 % : bootstrap stratifié sur les DOCUMENTS (on rééchantillonne,
avec remise, autant de documents qu'en compte chaque famille), 2 000 tirages, graine fixe, percentiles 2,5 et 97,5.

Rééchantillonner n documents avec remise ne dépend que de l'histogramme de leurs issues (mentions, masquées) : le
nombre de documents tirés dans chaque case suit EXACTEMENT une loi multinomiale (n ; fréquences), tirée ici par
binomiales successives. Même loi que le tirage document par document, sans tableau d'un million d'entrées.
Resampling n documents with replacement only depends on the histogram of their outcomes: the count drawn in each
cell follows EXACTLY a multinomial law (n; frequencies), drawn by successive binomials. Same law as drawing document
by document, without a million-entry array. Python 3.12+ (`random.binomialvariate`).
"""

from __future__ import annotations

import math
import random
from collections.abc import Mapping, Sequence

Histogram = Mapping[tuple[int, int], int]   # (mentions directes, entièrement masquées) -> documents


def family_rates(hist: Histogram) -> tuple[float | None, float | None]:
    """(part des documents sans fuite, rappel des mentions) d'une famille / (no-leak share, mention recall)."""
    docs = sum(hist.values())
    if not docs:
        return None, None
    passed = sum(n for (m, k), n in hist.items() if k == m)
    mentions = sum(m * n for (m, _), n in hist.items())
    masked = sum(k * n for (_, k), n in hist.items())
    return passed / docs, (masked / mentions if mentions else None)


def equal_weight(values: Sequence[float | None]) -> float | None:
    """Moyenne à poids égal ; None si une famille manque (jamais d'indice partiel) / None if a family is missing."""
    if not values or any(v is None for v in values):
        return None
    return sum(values) / len(values)  # type: ignore[arg-type]


def index_point(hists: Sequence[Histogram]) -> tuple[float | None, float | None]:
    """(indice, rappel des mentions), familles à poids égal / (index, mention recall), equal family weights."""
    rates = [family_rates(h) for h in hists]
    return equal_weight([r[0] for r in rates]), equal_weight([r[1] for r in rates])


def multinomial(rng: random.Random, n: int, weights: Sequence[int]) -> list[int]:
    """Tirage multinomial exact (n ; poids entiers) par binomiales conditionnelles / exact multinomial draw."""
    total = sum(weights)
    counts = []
    left = n
    for weight in weights:
        if left == 0 or total <= 0:
            counts.append(0)
            continue
        p = weight / total
        draw = left if p >= 1.0 else (rng.binomialvariate(left, p) if p > 0 else 0)
        counts.append(draw)
        left -= draw
        total -= weight
    return counts


def bootstrap_index(hists: Sequence[Histogram], resamples: int, seed: int,
                    level: float = 0.95) -> dict[str, tuple[float, float] | None]:
    """IC percentile de l'indice et du rappel des mentions, strates = familles / percentile CIs, strata = families."""
    if any(not sum(h.values()) for h in hists):
        return {"index": None, "mention_recall": None}
    rng = random.Random(seed)
    cells = [sorted(h.items()) for h in hists]
    index_draws: list[float] = []
    recall_draws: list[float] = []
    for _ in range(resamples):
        rates: list[float] = []
        recalls: list[float] = []
        for items in cells:
            n = sum(c for _, c in items)
            counts = multinomial(rng, n, [c for _, c in items])
            passed = sum(c for ((m, k), _), c in zip(items, counts, strict=True) if k == m)
            mentions = sum(m * c for ((m, _), _), c in zip(items, counts, strict=True))
            masked = sum(k * c for ((_, k), _), c in zip(items, counts, strict=True))
            rates.append(passed / n)
            recalls.append(masked / mentions if mentions else 0.0)
        index_draws.append(sum(rates) / len(rates))
        recall_draws.append(sum(recalls) / len(recalls))
    tail = (1 - level) / 2 * 100
    return {"index": (percentile(index_draws, tail), percentile(index_draws, 100 - tail)),
            "mention_recall": (percentile(recall_draws, tail), percentile(recall_draws, 100 - tail))}


def pooled_point(hists: Sequence[Histogram]) -> tuple[float | None, float | None]:
    """(part sans fuite, rappel des mentions) des documents mis en commun : chaque document compte une fois (indice
    « documents difficiles », 1.1) / pooled (no-leak share, mention recall): every document counts once."""
    pooled: dict[tuple[int, int], int] = {}
    for hist in hists:
        for cell, n in hist.items():
            pooled[cell] = pooled.get(cell, 0) + n
    return family_rates(pooled)


def bootstrap_pooled(hists: Sequence[Histogram], resamples: int, seed: int,
                     level: float = 0.95) -> dict[str, tuple[float, float] | None]:
    """IC percentile de la part mise en commun, bootstrap stratifié par groupe (chaque groupe garde son nombre de
    documents, donc son poids) / percentile CI of the pooled share, bootstrap stratified by group (each group keeps its
    document count, hence its weight). Un groupe vide est ignoré ; aucun document : None / empty group skipped."""
    cells = [sorted(h.items()) for h in hists if sum(h.values())]
    if not cells:
        return {"index": None, "mention_recall": None}
    rng = random.Random(seed)
    index_draws: list[float] = []
    recall_draws: list[float] = []
    for _ in range(resamples):
        docs = passed = mentions = masked = 0
        for items in cells:
            n = sum(c for _, c in items)
            counts = multinomial(rng, n, [c for _, c in items])
            docs += n
            passed += sum(c for ((m, k), _), c in zip(items, counts, strict=True) if k == m)
            mentions += sum(m * c for ((m, _), _), c in zip(items, counts, strict=True))
            masked += sum(k * c for ((_, k), _), c in zip(items, counts, strict=True))
        index_draws.append(passed / docs)
        recall_draws.append(masked / mentions if mentions else 0.0)
    tail = (1 - level) / 2 * 100
    return {"index": (percentile(index_draws, tail), percentile(index_draws, 100 - tail)),
            "mention_recall": (percentile(recall_draws, tail), percentile(recall_draws, 100 - tail))}


def bootstrap_ratio(pairs: Sequence[tuple[int, int]], resamples: int, seed: int,
                    level: float = 0.95) -> tuple[float, float] | None:
    """IC percentile de Σnum/Σden par documents (corpus réels : précision…) / ratio CI over documents."""
    if not pairs or not sum(d for _, d in pairs):
        return None
    rng = random.Random(seed)
    n = len(pairs)
    draws = []
    for _ in range(resamples):
        num = den = 0
        for i in rng.choices(range(n), k=n):
            num += pairs[i][0]
            den += pairs[i][1]
        if den:
            draws.append(num / den)
    tail = (1 - level) / 2 * 100
    return (percentile(draws, tail), percentile(draws, 100 - tail)) if draws else None


def percentile(values: Sequence[float], q: float) -> float:
    """Interpolation linéaire, comme tools.eval.metrics / linear interpolation, as tools.eval.metrics."""
    ordered = sorted(values)
    position = (len(ordered) - 1) * q / 100
    low = math.floor(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def wilson(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float, float] | None:
    if total == 0:
        return None
    p = successes / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return (0.0 if successes == 0 else max(0.0, centre - half), 1.0 if successes == total else min(1.0, centre + half))
