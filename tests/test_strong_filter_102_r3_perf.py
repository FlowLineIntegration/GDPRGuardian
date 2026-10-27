"""Voie perf (1.0.2, troisième tour) : fragments de téléphone coupés avec les téléphones, détection fusionnée hors du
mode fort, fenêtre du libellé bornée (entrée hostile en mode essentiel).

Perf lane: phone fragments switched off with the phones, fused detection outside mode fort, bounded label window
(hostile input in mode essentiel). Chaque cas tourne sur le noyau Rust (s'il est installé) et sur la référence
Python, qui doivent rendre le même texte. Every case runs on both engines, which must agree. Données fictives /
fictitious data.
"""

from __future__ import annotations

import time

import pytest

from gdprguardian import Anonymizer, _native
from gdprguardian.categories import Gate, business_label_before, personal_label_before

_ENGINES = [pytest.param(True, id="rust", marks=pytest.mark.skipif(not _native.available(),
                                                                    reason="noyau Rust absent / no Rust core")),
            pytest.param(False, id="python")]

_FRAGMENT = "Appelez le 06 12 34 56 78, le numéro finissant par 56 78 est celui de Mme Durand."
_FRAGMENT_ALONE = "Son portable se terminant par 45 67 ; ligne en 24 71."


@pytest.mark.parametrize("native", _ENGINES)
def test_phone_fragment_off_with_phones(native: bool) -> None:
    """`disable=["telephones"]` : la fin d'un numéro reste en clair comme le numéro / the fragment stays in clear."""
    an = Anonymizer(countries=("FR",), native=native, disable=["telephones"])
    for text in (_FRAGMENT, _FRAGMENT_ALONE):
        out = an.anonymize(text)
        assert "[TEL_" not in out.text, out.text
        assert out.report["left_in_clear_by_mode"].get("fragments", 0) >= 1
    assert "[PERSONNE_1]" in an.anonymize(_FRAGMENT).text


@pytest.mark.parametrize("native", _ENGINES)
def test_phone_fragment_still_masked_in_fort_and_with_other_disables(native: bool) -> None:
    for kw in ({"mode": "fort"}, {"disable": ["codes"]}):
        out = Anonymizer(countries=("FR",), native=native, **kw).anonymize(_FRAGMENT).text
        assert "56 78" not in out and out.count("[TEL_") == 2, out


def test_gate_off_adds_fragments_only_with_phones() -> None:
    assert "fragments" in Gate("personnalise", ("telephones",)).off
    assert "fragments" not in Gate("personnalise", ("codes",)).off
    assert "fragments" in Gate("essentiel").off  # essentiel : déjà coupés / already off
    assert not Gate("fort").off


@pytest.mark.parametrize("kw", [{"mode": "essentiel"}, {"disable": ["codes", "boites_fonctionnelles"]},
                                {"disable": ["telephones"]}, {"disable": ["iban", "cartes"]}])
def test_gated_modes_use_fused_detection_with_same_output(kw: dict) -> None:
    """Hors du mode fort, la détection fusionnée (un appel) rend le texte, les zones et le rapport de la référence.

    Outside mode fort, the one-call fused detection gives the reference's text, spans and report.
    """
    if not _native.available():
        pytest.skip("noyau Rust absent / no Rust core")
    nat = Anonymizer(countries=("FR",), explain=True, **kw)
    pure = Anonymizer(countries=("FR",), explain=True, native=False, **kw)
    assert nat._fused is not None
    texts = [_FRAGMENT, "Facture 123456 du client CLT-204518, support@exemple.fr, @jdupont, Kevin Lambert "
             "https://kevinlambert.fr", "client 98765432 ; commande AB12345 ; facture du client 123456",
             "Tél. 06 12 34 56 78\r\nIBAN FR76 3000 6000 0112 3456 7890 189 et carte 4970 1012 3456 7899"]
    for text in texts:
        a, b = nat.anonymize(text), pure.anonymize(text)
        assert a.text == b.text
        assert [(s.start, s.end, s.source) for s in a.analysis.spans] == \
               [(s.start, s.end, s.source) for s in b.analysis.spans]
        assert {k: v for k, v in a.report.items() if k not in ("timings_ms", "native")} == \
               {k: v for k, v in b.report.items() if k not in ("timings_ms", "native")}
        assert [(s.start, s.end) for s in nat.analyze(text).spans] == [(s.start, s.end) for s in a.analysis.spans]


def test_label_window_same_bounds() -> None:
    """La fenêtre bornée donne les mêmes réponses que la recherche jusqu'au début / same answers as before."""
    texts = ["client 123456", "x" * 100 + " client 123456", "client\n123456", "facture du client 123456",
             "facture 123456", "a\nfacture n° 123456", "client " + "y" * 70 + " 123456"]
    for text in texts:
        start = text.rfind("1")  # dernier chiffre : borne au milieu d'un nombre, c'est voulu / any offset works
        for at in (start, text.find("123456")):
            assert personal_label_before(text, at) == _old_personal(text, at)
            assert business_label_before(text, at) == _old_business(text, at)


def _old_personal(text: str, start: int) -> bool:
    from gdprguardian import categories as c
    line = text.rfind("\n", 0, start) + 1
    return c._PERSONAL_LABEL_BEFORE.search(text, max(line, start - c._LABEL_WINDOW), start) is not None


def _old_business(text: str, start: int) -> bool:
    from gdprguardian import categories as c
    lo = max(text.rfind("\n", 0, start) + 1, start - c._LABEL_WINDOW)
    business = c._BUSINESS_LABEL_BEFORE.search(text, lo, start)
    if business is None:
        return False
    personal = c._PERSONAL_LABEL_BEFORE.search(text, lo, start)
    return personal is None or business.start() >= personal.start()


def test_personal_site_plan_needs_the_twin() -> None:
    """Plan natif seulement si le noyau porte le jumeau (`personal_site_twin`) / native plan only with the twin."""
    from gdprguardian.detectors.intl import PersonalSiteDetector, _fold_word

    detector = PersonalSiteDetector(None)
    plan = detector.native_plan()
    core = _native.core()
    if core is None or not getattr(core, "personal_site_twin", False):
        assert plan is None
    else:
        assert plan["kind"] == "personal_site" and plan["fold"] is _fold_word
        assert plan["prototype"].reason == "personal_site_name" and plan["prototype"].source == "URL_PERSONAL_NAME"


@pytest.mark.parametrize("native", _ENGINES)
@pytest.mark.parametrize("text, hosts", [
    ("Kevin Lambert publie sur https://kevinlambert.fr et kevin-lambert.fr/blog ; voir aussi klambert.fr.",
     ["kevinlambert", "kevinlambert", "klambert"]),
    ("LAMBERT Kevin : www.lambertkevin.com. Jean Dupont tient jdupont.blog", ["lambertkevin", "jdupont"]),
    ("Zoé Ñúñez : zoenunez.fr ; Élise Durand : elisedurand.page", ["zoenunez", "elisedurand"]),
    ("Élise Œuvray : eliseoeuvray.page", []),  # « œ » sans décomposition : aucune forme ASCII / no ASCII form
    ("Voir https://www.service-public.fr pour Jean Dupont.", []),
])
def test_personal_site_same_spans(native: bool, text: str, hosts: list[str]) -> None:
    """Même zones et mêmes valeurs, jumeau ou Python / same spans and values, twin or Python."""
    spans = Anonymizer(countries=("FR",), native=native).analyze(text).spans
    assert [s.value for s in spans if s.source == "URL_PERSONAL_NAME"] == hosts


@pytest.mark.parametrize("native", _ENGINES)
def test_essentiel_hostile_input_bounded(native: bool) -> None:
    """Essentiel sur 60 000 codes sans retour à la ligne : linéaire (voie perf) / linear on a hostile input."""
    text = " ".join(f"AB{i:06d}" for i in range(60000))
    an = Anonymizer(countries=("FR",), native=native, mode="essentiel")
    t0 = time.perf_counter()
    out = an.anonymize(text)
    assert time.perf_counter() - t0 < 30
    assert out.text.startswith("AB000000 AB000001")  # codes sans libellé : lisibles en essentiel / readable
