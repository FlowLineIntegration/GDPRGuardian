"""Métriques : cas construits à la main (fuite partielle, décalage de borne, mentions éclatées).

Metrics: hand-built cases (partial leak, boundary shift, split mentions, decoys, over-masking).
"""

from __future__ import annotations

import math
import sys

import pytest
from tools.eval.metrics import (
    STAT_FIELDS,
    Masked,
    Tally,
    _percentile,
    bootstrap,
    canonical,
    f_beta,
    headline,
    score_document,
    significant_mask,
    wilson,
)
from tools.eval.schema import DIRECT, NO_MASK, QUASI, Document, GoldSpan

NIR = "1 85 05 78 006 084 36"


def _doc(text: str, *spans: tuple[str, str, str, str]) -> Document:
    """Zones données par (valeur, libellé, entité, type), cherchées dans l'ordre / spans by value."""
    gold, cursor = [], 0
    for value, label, entity, kind in spans:
        start = text.index(value, cursor)
        gold.append(GoldSpan(start, start + len(value), label, f"d:{entity}", kind))
        cursor = start + len(value)
    doc = Document("d", "test", text, tuple(gold))
    doc.check()
    return doc


def _mask(text: str, value: str, label: str = "X", occurrence: int = 0) -> Masked:
    start = -1
    for _ in range(occurrence + 1):
        start = text.index(value, start + 1)
    return Masked(start, start + len(value), label)


def _stats(stats: list[int]) -> dict[str, int]:
    return dict(zip(STAT_FIELDS, stats, strict=True))


def _score(doc: Document, masked: list[Masked], output: str | None = None) -> tuple[Tally, list[int]]:
    score = score_document(doc, masked, output)
    return score.tally, score.stats


def test_perfect_masking():
    text = f"NIR {NIR} fin"
    doc = _doc(text, (NIR, "NIR", "nir", DIRECT))
    tally, stats = _score(doc, [_mask(text, NIR, "NIR")], "NIR [NIR_1] fin")
    assert tally.mentions_masked["NIR"] == 1 and tally.mentions_strict["NIR"] == 1
    assert tally.mentions_typed["NIR"] == 1 and tally.mentions_iou["NIR"] == 1
    assert tally.docs_leak_strict == tally.docs_leak_verbatim == 0
    assert _stats(stats)["pred"] == _stats(stats)["pred_ok"] == 15


def test_partial_leak_is_a_leak():
    text = f"NIR {NIR} fin"
    doc = _doc(text, (NIR, "NIR", "nir", DIRECT))
    tally, stats = _score(doc, [_mask(text, NIR[:-3])])  # « 36 » reste visible / stays visible
    assert _stats(stats)["leak_structured"] == 1
    assert tally.mentions_masked["NIR"] == 0
    assert tally.hit_chars["NIR"] == 13 and tally.gold_chars["NIR"] == 15
    assert tally.docs_leak_strict == 1 and tally.docs_leak_structured == 1
    assert tally.mentions_leak_lenient["NIR"] == 0  # 2 caractères < 4 / 2 chars < 4
    assert tally.misses[0]["visible"] == 2


def test_lenient_leak_counts_significant_chars_across_separators():
    text = f"NIR {NIR} fin"
    doc = _doc(text, (NIR, "NIR", "nir", DIRECT))
    tally, _ = _score(doc, [_mask(text, NIR[:-6])])  # « 084 36 » visible : 5 chiffres / 5 digits
    assert tally.mentions_leak_lenient["NIR"] == 1 and tally.docs_leak_lenient == 1


def test_boundary_shift_lowers_iou_not_privacy_of_masked_chars():
    text = "Contact jean.dupont@exemple.fr merci"
    doc = _doc(text, ("jean.dupont@exemple.fr", "EMAIL", "email", DIRECT))
    shifted = _mask(text, "ean.dupont@exemple.fr", "EMAIL")
    tally, _ = _score(doc, [shifted])
    assert tally.mentions_masked["EMAIL"] == 0 and tally.mentions_iou["EMAIL"] == 1  # IoU 21/22 ≥ 0.9
    assert tally.hit_chars["EMAIL"] == tally.gold_chars["EMAIL"] - 1


def test_whitespace_is_ignored_but_strict_requires_full_cover():
    text = "Signé Jean Dupont."
    doc = _doc(text, ("Jean Dupont", "PERSON", "p1", DIRECT))
    tally, _ = _score(doc, [_mask(text, "Jean", "PERSON"), _mask(text, "Dupont", "PERSON")])
    assert tally.mentions_masked["PERSON"] == 1  # l'espace ne compte pas (TAB) / space ignored
    assert tally.mentions_strict["PERSON"] == 0  # mais il reste visible / but it stays visible


def test_entity_recall_requires_every_mention():
    text = "Jean Dupont écrit. Plus tard, M. Dupont rappelle."
    doc = _doc(text, ("Jean Dupont", "PERSON", "p1", DIRECT), ("Dupont", "PERSON", "p1", DIRECT))
    tally, stats = _score(doc, [_mask(text, "Jean Dupont", "PERSON")])
    assert tally.mentions["PERSON"] == 2 and tally.mentions_masked["PERSON"] == 1
    assert tally.entities[DIRECT] == 1 and tally.entities_masked[DIRECT] == 0
    assert _stats(stats)["entities_direct_masked"] == 0
    assert tally.docs_leak_structured == 0 and tally.docs_leak_strict == 1  # nom = textuel / name = textual


def test_decoys_and_over_masking():
    text = "Montant 1 250,00 € selon l'article L. 1234-5, réunion lundi."
    doc = _doc(text, ("1 250,00 €", "AMOUNT", "d1", NO_MASK), ("L. 1234-5", "LEGAL_REF", "d2", NO_MASK))
    tally, stats = _score(doc, [_mask(text, "L. 1234-5", "ID"), _mask(text, "lundi", "DATE")])
    values = _stats(stats)
    assert values["decoys"] == 2 and values["decoys_hit"] == 1
    assert tally.neutral_masked == 5 and values["pred_ok"] == 0
    assert tally.pred_on_decoys == 6  # « L », « 1234 », « 5 »
    assert headline(stats, 1)["precision"] == 0.0
    assert {row["value"] for row in tally.false_masks} == {"L. 1234-5", "lundi"}


def test_quasi_identifiers_count_as_correct_masks():
    text = "Née le 12/03/1985 à Lyon."
    doc = _doc(text, ("12/03/1985", "BIRTH_DATE", "b", QUASI), ("Lyon", "LOCATION", "l", QUASI))
    tally, stats = _score(doc, [_mask(text, "12/03/1985", "BIRTH_DATE")])
    values = _stats(stats)
    assert values["pred"] == values["pred_ok"] == 8
    assert values["direct_gold"] == 0 and values["gold"] == 12
    assert tally.entities[QUASI] == 2 and tally.entities_masked[QUASI] == 1
    assert tally.docs_leak_strict == 0  # les quasi-identifiants ne sont pas des fuites directes


def test_verbatim_leak_survives_output_sanitizing():
    value = "1 85\u200b05 78 006 084 36"
    text = f"NIR {value}."
    doc = _doc(text, (value, "NIR", "nir", DIRECT))
    tally, _ = _score(doc, [], output=f"NIR {value.replace(chr(0x200B), '')}.")
    assert tally.docs_leak_verbatim == 1


def test_mutation_bookkeeping_and_survival():
    text = "Tél. 06 12 34 56 78, Jean Dupont."
    spans = (GoldSpan(5, 19, "PHONE", "d:t", DIRECT, "nbsp"), GoldSpan(21, 32, "PERSON", "d:p", DIRECT, "nbsp"))
    doc = Document("d", "test", text, spans)
    score = score_document(doc, [Masked(5, 19, "PHONE")], baseline=[True, False])
    tally = score.tally
    assert score.masked == [True, False]
    assert tally.mutation_masked[("nbsp", "PHONE")] == 1 and tally.mutation_masked[("nbsp", "PERSON")] == 0
    # Survie : seules les mentions masquées avant mutation comptent / only mentions caught before count.
    assert tally.mutation_baseline[("nbsp", "PHONE")] == 1 and tally.mutation_survived[("nbsp", "PHONE")] == 1
    assert tally.mutation_baseline[("nbsp", "PERSON")] == 0
    lost = score_document(doc, [], baseline=[True, False]).tally
    assert lost.mutation_baseline[("nbsp", "PHONE")] == 1 and lost.mutation_survived[("nbsp", "PHONE")] == 0


def test_nested_masked_zones_are_found():
    # Une grande zone qui en englobe une petite : la mention reste attribuée à la grande (confusion, IoU).
    # A large zone enclosing a small one: the mention is still attributed to the large one.
    text = "Signé Jean Dupont, Paris."
    doc = _doc(text, ("Jean Dupont", "PERSON", "p1", DIRECT))
    tally, _ = _score(doc, [Masked(0, len(text) - 1, "ORG"), Masked(1, 3, "X")])
    assert tally.mentions_masked["PERSON"] == 1
    assert tally.confusion[("PERSON", "ORG")] == 1 and tally.mentions_iou["PERSON"] == 0


def test_dominant_zone_is_the_largest_overlap():
    text = "Signé Jean Dupont."
    doc = _doc(text, ("Jean Dupont", "PERSON", "p1", DIRECT))
    tally, _ = _score(doc, [_mask(text, "Jean", "PERSON"), _mask(text, "Dupont", "ADDRESS")])
    assert tally.confusion[("PERSON", "ADDRESS")] == 1 and tally.mentions_typed["PERSON"] == 0


@pytest.mark.parametrize("zone", [(5, 40), (-1, 3), (6, 4)])
def test_out_of_bounds_masked_zone_is_rejected(zone):
    # Une zone hors bornes agrandirait le masque et décalerait silencieusement toutes les mesures.
    # An out-of-bounds zone would grow the mask and silently shift every measurement.
    text = f"NIR {NIR}"
    doc = _doc(text, (NIR, "NIR", "nir", DIRECT))
    with pytest.raises(ValueError, match=r"hors bornes|out of bounds"):
        score_document(doc, [Masked(*zone, "X")])


def test_baseline_length_mismatch_is_rejected():
    text = f"NIR {NIR}"
    doc = _doc(text, (NIR, "NIR", "nir", DIRECT))
    with pytest.raises(ValueError, match="baseline"):
        score_document(doc, [], baseline=[True, True])


def test_empty_document_scores_without_error():
    score = score_document(Document("d", "test", "", ()), [])
    assert score.masked == [] and score.tally.pred_total == 0


def test_canonical_drops_default_ignorables():
    # U+FE0F et U+034F (Mn), U+3164 (Lo) : invisibles mais hors de la catégorie Cf / invisible, not Cf.
    assert canonical("1\ufe0f2\u034f3\u31644\U000e01005") == "12345"
    assert canonical("Jean\u00a0Dupont") == "Jean Dupont"  # NFKC


def test_verbatim_leak_found_when_output_drops_a_variation_selector():
    value = "1 85\ufe0f05 78 006 084 36"
    text = f"NIR {value}."
    doc = _doc(text, (value, "NIR", "nir", DIRECT))
    tally, _ = _score(doc, [], output=f"NIR {value.replace(chr(0xFE0F), '')}.")
    assert tally.docs_leak_verbatim == 1


def test_tally_merge_adds_everything():
    text = f"NIR {NIR}"
    doc = _doc(text, (NIR, "NIR", "nir", DIRECT))
    total = Tally()
    for _ in range(3):
        total.merge(score_document(doc, []).tally)
    assert total.docs == 3 and total.mentions["NIR"] == 3 and len(total.misses) == 3


def test_significant_mask_and_canonical():
    assert list(significant_mask("a-b c_d")) == [1, 0, 1, 0, 1, 0, 1]
    assert canonical("１\u200b２") == "12"
    assert canonical("plain") == "plain"


def _row(**values: int) -> list[int]:
    return [values.get(name, 0) for name in STAT_FIELDS]


# 20 documents masqués, 5 qui fuient : rappel direct 0,8 / 20 masked documents, 5 leaking: recall 0.8.
_BOOTSTRAP_STATS = [_row(direct_gold=1, direct_hit=1, gold=1, hit=1, pred=1, pred_ok=1, entities_direct=1,
                         entities_direct_masked=1, neutral=1)] * 20 \
    + [_row(direct_gold=1, gold=1, entities_direct=1, leak_strict=1, leak_structured=1, neutral=1)] * 5


def test_f_beta_and_wilson():
    assert f_beta(0.5, 1.0) == pytest.approx(5 * 0.5 / (4 * 0.5 + 1))
    assert f_beta(None, 1.0) is None and f_beta(0.0, 0.0) == 0.0
    assert wilson(0, 0) == (None, None)
    low, high = wilson(10, 10)
    assert high == 1.0 and 0.6 < low < 0.8


def test_bootstrap_is_deterministic_and_brackets_the_estimate():
    ci = bootstrap(_BOOTSTRAP_STATS, headline, resamples=300, seed=1)
    assert ci == bootstrap(_BOOTSTRAP_STATS, headline, resamples=300, seed=1)
    low, high = ci["recall_direct"]
    assert low <= 0.8 <= high and not math.isnan(low)


def test_bootstrap_without_numpy(monkeypatch):
    monkeypatch.setitem(sys.modules, "numpy", None)  # import numpy -> ImportError
    ci = bootstrap(_BOOTSTRAP_STATS, headline, resamples=300, seed=1)
    low, high = ci["recall_direct"]
    assert 0.5 < low <= 0.8 <= high <= 1.0


def test_percentile_matches_numpy():
    np = pytest.importorskip("numpy")
    values = [((i * 7919) % 101) / 7 for i in range(57)]
    for q in (0, 2.5, 50, 97.5, 100):
        assert _percentile(values, q) == pytest.approx(float(np.percentile(values, q)))
