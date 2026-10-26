"""Mots-clés de contexte : noyau Rust contre référence Python, à l'identique.

Context keywords: Rust core against the Python reference, identically. Tout ce qu'un détecteur ajouté peut lire
(`ctx.hits`, `ctx.counts`) : comptes, ordre des groupes et des clés (par nom), occurrences. Un groupe ne compte
qu'une fois par mot replié, même si plusieurs listes de langues le répètent (« iban » dans sept listes de
INTL:iban). Everything a plugged-in detector can read: counts, group and key order (by name), occurrences. A
group counts once per folded word, even when several language lists repeat it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from gdprguardian import Anonymizer, _native
from gdprguardian._text import fold
from gdprguardian.keywords import KeywordIndex

pytestmark = pytest.mark.skipif(not _native.available(), reason="noyau Rust absent / no Rust core")

_DOCS = sorted((Path(__file__).resolve().parents[1] / "datasets" / "fr" / "docs").glob("*.md"))


def _view(hits: Any) -> tuple:
    """Ce qu'un détecteur lit : (groupe, compte) dans l'ordre, groupes, occurrences / what a detector reads."""
    groups = hits.groups()
    return list(hits.counts.items()), groups, {group: hits.occurrences(group) for group in groups}


@pytest.mark.parametrize("countries", ["FR", "all"])
def test_corpus_keywords_identical(countries):
    native, python = Anonymizer(countries=countries), Anonymizer(countries=countries, native=False)
    assert native.native and not python.native
    for path in _DOCS:
        folded = fold(path.read_text(encoding="utf-8"))
        assert _view(native._scan_keywords(folded)) == _view(python._scan_keywords(folded)), path.name


def test_a_group_counts_once_per_occurrence():
    """Mot répété dans les listes d'un même groupe : une occurrence, un compte ; groupes et clés triés.

    Word repeated in the lists of one group: one occurrence, one count; groups and keys sorted.
    """
    folded = fold("IBAN : FR76 3000 6000 0112 3456 7890 189, téléphone 06 12 34 56 78, Tél. 01 02 03 04 05")
    for anonymizer in (Anonymizer(), Anonymizer(native=False)):
        hits = anonymizer._scan_keywords(folded)
        assert hits.counts["INTL:iban"] == 1 and hits.occurrences("INTL:iban") == [(0, 4)]
        assert hits.groups() == sorted(hits.groups()) == list(hits.counts)


_WORDS = ["iban", "IBAN", "Iban", "tél", "tel", "TEL", "téléphone", "né le", "nee le", "date de naissance", "nir",
          "n° sécu", "e-mail", "mail", "courriel", "rib", "ré", "a", "ab", "x.y", "l'adresse", "Ǆ", "ß", "ﬁ", "İ",
          "naïve", "co-gérant", "S.A.S.", "#", "1er", "Ⅻ", "²"]
_GROUPS = st.dictionaries(
    st.sampled_from(["FR:x", "FR:y", "BE:x", "INTL:iban", "INTL:tel", "Z:z"]),
    st.lists(st.sampled_from(_WORDS) | st.text(alphabet="abcé -", min_size=1, max_size=5), min_size=1, max_size=8),
    min_size=1, max_size=6)
_TEXTS = st.lists(st.sampled_from(_WORDS) | st.sampled_from([" ", ", ", "\n", "x", "é", "1", "-"]),
                  max_size=40).map("".join)


@settings(max_examples=400, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(groups=_GROUPS, text=_TEXTS)
def test_random_keyword_compositions_identical(groups, text):
    """Groupes au hasard, mots répétés ou de même repli, dans un groupe ou entre groupes / random compositions."""
    native = _native.build([], groups, fold)
    folded = fold(text)
    assert _view(native.keywords(folded)) == _view(KeywordIndex(groups).scan(folded))


class _Probe:
    """Détecteur ajouté qui relève ce qu'il lit des mots-clés / plugged-in detector recording the keywords."""

    id = "PROBE"

    def __init__(self) -> None:
        self.seen: list[tuple] = []

    def detect(self, ctx: Any) -> list[Any]:
        self.seen.append((*_view(ctx.hits), list(ctx.counts.items())))
        return []


@pytest.mark.parametrize("countries", ["FR", "all"])
def test_plugged_in_detector_sees_the_same_keywords(countries):
    """Moteur fusionné (occurrences de Rust) et référence : même `ctx.hits`, même `ctx.counts`.

    Fused engine (Rust hits) and reference: the same `ctx.hits` and `ctx.counts`.
    """
    probe = _Probe()
    native = Anonymizer(countries=countries, detectors=(probe,))
    python = Anonymizer(countries=countries, detectors=(probe,), native=False)
    assert native._fused is not None
    for path in _DOCS[::4]:
        text = path.read_text(encoding="utf-8")
        probe.seen = []
        native.anonymize(text)
        python.anonymize(text)
        assert probe.seen[0] == probe.seen[1], path.name
