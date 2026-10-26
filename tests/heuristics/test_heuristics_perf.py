"""Performance : moins de 2 ms par 10 Ko de prose sur la machine de référence (marge large ici).

Performance smoke test: the target is below 2 ms per 10 KB of French prose for the three detectors on the
reference machine; the assertion keeps a wide margin for slow CI runners.
"""

from __future__ import annotations

import time

from heuristics_corpus import POSITIVES, parse

from gdprguardian.heuristics.fr_address import FrenchAddressDetector
from gdprguardian.heuristics.fr_names import FrenchNameDetector
from gdprguardian.heuristics.organizations import OrganizationDetector

PROSE = (
    "Compte rendu de la réunion du 12 mars 2025. Le directeur financier rappelle que les dépenses de "
    "fonctionnement ont augmenté de 4 % par rapport à l'année dernière, en raison de la hausse des coûts de "
    "l'énergie et des loyers. Il propose de reporter certains investissements au second semestre afin de "
    "préserver la trésorerie. La politique de protection des données décrit la manière dont l'entreprise "
    "collecte, utilise et conserve les informations relatives à ses clients et partenaires.\n"
)


def _ten_kilobytes() -> str:
    parts = []
    i = 0
    while sum(map(len, parts)) < 10_240:
        parts.append(parse(POSITIVES[i % len(POSITIVES)])[0] if i % 2 else PROSE)
        i += 1
    return "".join(parts)[:10_240]


def test_three_detectors_are_fast(context):
    ctx = context(_ten_kilobytes())
    detectors = (FrenchNameDetector(None), FrenchAddressDetector(None), OrganizationDetector(None))
    for detector in detectors:
        detector.detect(ctx)  # échauffement / warm-up
    best = float("inf")
    for _ in range(7):
        start = time.perf_counter()
        for detector in detectors:
            detector.detect(ctx)
        best = min(best, time.perf_counter() - start)
    assert best * 1000 < 15.0, f"{best * 1000:.2f} ms / 10 KB"
