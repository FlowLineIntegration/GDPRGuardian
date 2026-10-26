"""Tests des mesures de evaluate_real (cas construits à la main) / tests of evaluate_real metrics (hand-built)."""

from __future__ import annotations

from tools.corpus.evaluate_real import BASE_FIELDS, doc_stats, headline, literal_leak
from tools.eval.metrics import bootstrap


def rec(text: str, spans: list[tuple[int, int, str]], ignore: list[list[int]] | None = None) -> dict:
    return {"text": text, "spans": [{"start": s, "end": e, "label": lab, "text": text[s:e]} for s, e, lab in spans],
            "ignore": ignore or []}


TEXT = "Nom : Jeanne MARTIN, 12 rue Haute. Ville de Paris. Notes : Jeanne MARTIN encore."
#        0     6      13    20          31            44


def test_full_partial_and_missed_mentions() -> None:
    r = rec(TEXT, [(6, 19, "PERSON"), (21, 33, "ADDRESS"), (35, 49, "ORG")])
    # nom entièrement masqué, adresse masquée sauf « Haute » / name fully masked, address masked except "Haute"
    st = doc_stats(r, [(6, 19), (21, 28)], "Nom : [P], [A]Haute. Ville de Paris. Notes : Jeanne MARTIN encore.",
                   ["PERSON", "ADDRESS"])
    assert st["m_total"] == 2 and st["m_full"] == 1
    assert st["f_PERSON"] == 1 and st["f_ADDRESS"] == 0
    assert st["m_cov80"] == 1  # "12rue" = 5 of 10 alnum chars: below 80%
    assert st["d_leak"] == 1
    assert st["m_literal"] == 1 and st["d_leak_literal"] == 1  # "Jeanne MARTIN" still in the output
    assert st["k_total"] == 1 and st["k_touched"] == 0


def test_precision_ignores_unscored_zones() -> None:
    r = rec(TEXT, [(6, 19, "PERSON")], ignore=[[51, 80]])
    st = doc_stats(r, [(6, 19), (59, 72), (41, 49)], "x", ["PERSON"])
    # « Jeanne MARTIN » répété dans la zone ignorée ne compte pas ; « de Paris » est hors gold
    alnum = sum(ch.isalnum() for ch in TEXT[6:19])
    assert st["c_pred_tp"] == alnum
    assert st["c_pred"] == alnum + sum(ch.isalnum() for ch in TEXT[41:49])
    assert st["c_neutral_masked"] == sum(ch.isalnum() for ch in TEXT[41:49])
    m = headline({k: float(st.get(k, 0)) for k in [*BASE_FIELDS, "g_PERSON", "f_PERSON"]}, 1, ["PERSON"])
    assert m["mention_recall"] == 1.0 and m["recall_PERSON"] == 1.0
    assert 0 < m["precision"] < 1


def test_literal_leak_needs_a_word_boundary() -> None:
    assert literal_leak("Martin", "m. martin est venu")
    assert not literal_leak("Martin", "martinez est venu")
    assert literal_leak("ＭＡＲＴＩＮ", "le dossier martin")


def test_document_without_personal_gold_is_not_in_leak_denominator() -> None:
    st = doc_stats(rec("Rien ici.", []), [], "Rien ici.", [])
    assert st["d_has_gold"] == 0 and st["d_leak"] == 0 and st["detections"] == 0


def test_bootstrap_intervals_bracket_the_point_estimate() -> None:
    keys = [*BASE_FIELDS, "g_PERSON", "f_PERSON"]
    rows = []
    for i in range(40):
        st = dict.fromkeys(keys, 0)
        st.update(m_total=2, m_full=1 + (i % 2), d_has_gold=1, g_PERSON=2, f_PERSON=1 + (i % 2), chars=10)
        rows.append([st[k] for k in keys])
    ci = bootstrap(rows, lambda sums, n: headline(dict(zip(keys, sums, strict=True)), n, ["PERSON"]),
                   resamples=200, seed=0)
    low, high = ci["mention_recall"]
    assert low <= 0.75 <= high
