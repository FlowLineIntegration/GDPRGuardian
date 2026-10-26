"""Indice de confiance et bootstrap stratifié / confidence index and stratified bootstrap."""

from __future__ import annotations

import random
import statistics
from collections import Counter

from tools.protocol.stats import (
    bootstrap_index,
    bootstrap_ratio,
    family_rates,
    index_point,
    multinomial,
    percentile,
)


def test_family_rates() -> None:
    hist = Counter({(3, 3): 8, (2, 1): 2})
    rate, recall = family_rates(hist)
    assert rate == 0.8
    assert recall == (3 * 8 + 1 * 2) / (3 * 8 + 2 * 2)


def test_volume_never_buys_weight() -> None:
    """Un million de documents parfaits et dix documents ratés : 50 %, pas 99,999 % / equal weights."""
    huge = Counter({(2, 2): 1_000_000})
    tiny = Counter({(1, 0): 10})
    index, recall = index_point([huge, tiny])
    assert index == 0.5
    assert recall == 0.5


def test_missing_family_gives_no_index() -> None:
    assert index_point([Counter({(1, 1): 3}), Counter()]) == (None, None)
    assert bootstrap_index([Counter({(1, 1): 3}), Counter()], 50, 1) == {"index": None, "mention_recall": None}


def test_multinomial_is_exact_in_total_and_mean() -> None:
    rng = random.Random(7)
    weights = [70, 20, 10]
    draws = [multinomial(rng, 100, weights) for _ in range(4000)]
    assert all(sum(d) == 100 for d in draws)
    means = [statistics.fmean(d[i] for d in draws) for i in range(3)]
    for mean, expected in zip(means, (70, 20, 10), strict=True):
        assert abs(mean - expected) < 0.6


def test_bootstrap_matches_naive_document_resampling() -> None:
    """Même loi que le tirage document par document (moyenne et écart-type) / same law as naive resampling."""
    hist_a = Counter({(2, 2): 140, (2, 1): 40, (1, 0): 20})
    hist_b = Counter({(5, 5): 300, (5, 3): 100})
    point, _ = index_point([hist_a, hist_b])

    def naive(seed: int, resamples: int) -> list[float]:
        rng = random.Random(seed)
        docs_a = [k == m for (m, k), n in hist_a.items() for _ in range(n)]
        docs_b = [k == m for (m, k), n in hist_b.items() for _ in range(n)]
        out = []
        for _ in range(resamples):
            a = sum(rng.choices(docs_a, k=len(docs_a))) / len(docs_a)
            b = sum(rng.choices(docs_b, k=len(docs_b))) / len(docs_b)
            out.append((a + b) / 2)
        return out

    reference = naive(3, 3000)
    ours = bootstrap_index([hist_a, hist_b], 3000, 5)["index"]
    assert ours is not None
    low, high = ours
    assert low < point < high
    assert abs(low - percentile(reference, 2.5)) < 0.01
    assert abs(high - percentile(reference, 97.5)) < 0.01
    assert abs(statistics.fmean(reference) - point) < 0.005


def test_bootstrap_is_deterministic() -> None:
    hists = [Counter({(1, 1): 50, (1, 0): 5}), Counter({(3, 2): 4, (3, 3): 9})]
    assert bootstrap_index(hists, 200, 11) == bootstrap_index(hists, 200, 11)


def test_ratio_interval() -> None:
    pairs = [(9, 10)] * 50 + [(5, 10)] * 50
    low, high = bootstrap_ratio(pairs, 500, 1)
    assert low < 0.7 < high
    assert bootstrap_ratio([], 10, 1) is None
