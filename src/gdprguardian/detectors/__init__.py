"""Détecteurs Python branchables, déclarés par les packs / pluggable Python detectors declared by packs.

Contrat : `__init__(self, pack)` et `detect(self, ctx) -> list[Span]` (positions du texte normalisé).
Contract: `__init__(self, pack)` and `detect(self, ctx) -> list[Span]` (normalised-text offsets).
"""
