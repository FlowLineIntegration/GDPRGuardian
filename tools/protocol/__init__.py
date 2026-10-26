"""Protocole public d'auto-évaluation de Gardien RGPD (outil de dev, jamais livré dans le paquet).

GDPR Guardian public self-rating protocol (development tooling, never shipped in the package). The campaign sends
every document through the REAL service (its Unix socket, local token, counted as "protocol" in the public
statistics), rebuilds what the service masked from its output alone, scores it against the gold annotations with
the metric definitions of `tools.eval` and `tools.corpus`, and writes aggregate scores only.

Pre-registered definitions: `tools/protocol/spec.py` and `docs/PROTOCOLE.md`. Entry point:
`python -m tools.protocol --help` (or the self-contained bundle built by `python -m tools.protocol bundle`).
Standard library only, plus Faker for the synthetic generator (vendored in the bundle).
"""
