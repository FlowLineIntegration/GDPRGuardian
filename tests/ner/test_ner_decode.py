"""Décodage vectorisé : schéma d'étiquettes, softmax, décisions, suites / vectorised decoding."""

from __future__ import annotations

import math

import pytest

np = pytest.importorskip("numpy")

from gdprguardian.ner.decode import LabelScheme, group_runs, run_extents, softmax, token_decisions  # noqa: E402

IO = {0: "O", 1: "I-LOC", 2: "I-PER", 3: "I-MISC", 4: "I-ORG"}
BIO = {0: "O", 1: "B-PER", 2: "I-PER", 3: "B-ORG", 4: "I-ORG", 5: "B-LOC", 6: "I-LOC", 7: "B-MISC", 8: "I-MISC"}


def logits_for(rows: list[dict[int, float]], classes: int) -> np.ndarray:
    """Une ligne par jeton : {classe: probabilité}, le reste à parts égales / one row per token."""
    out = np.zeros((1, len(rows), classes), np.float32)
    for i, row in enumerate(rows):
        rest = (1.0 - sum(row.values())) / (classes - len(row))
        probs = [row.get(c, rest) for c in range(classes)]
        out[0, i] = np.log(np.maximum(probs, 1e-9))
    return out


def test_scheme_from_io_labels():
    scheme = LabelScheme.from_labels(IO)
    assert scheme.entities == ("LOCATION", "PERSON", "ORG")
    assert not scheme.has_begin
    assert scheme.type_matrix[3].sum() == 0  # MISC ignorée / MISC ignored
    assert scheme.type_matrix[2, scheme.entities.index("PERSON")] == 1


def test_scheme_from_bio_labels_sums_begin_and_inside():
    scheme = LabelScheme.from_labels(BIO)
    assert scheme.entities == ("PERSON", "ORG", "LOCATION")
    assert scheme.has_begin
    person = scheme.entities.index("PERSON")
    assert scheme.type_matrix[[1, 2], person].tolist() == [1, 1]
    assert scheme.begin_matrix[[1, 2], person].tolist() == [1, 0]


def test_scheme_without_entities_is_rejected():
    with pytest.raises(ValueError):
        LabelScheme.from_labels({0: "O", 1: "I-MISC"})


def test_softmax_is_stable_and_normalised():
    probs = softmax(np.array([[1000.0, 1000.0, -1000.0]], np.float32))
    assert np.allclose(probs.sum(-1), 1.0)
    assert np.allclose(probs[0, :2], 0.5)


def test_token_decision_accepts_entity_below_o_when_threshold_allows():
    scheme = LabelScheme.from_labels(IO)
    logits = logits_for([{0: 0.55, 2: 0.4, 3: 0.05}, {0: 0.95, 2: 0.01, 3: 0.04}], 5)
    person = scheme.entities.index("PERSON")
    loose = np.array([0.3, 0.3, 0.3], np.float32)
    entity, score, begin = token_decisions(logits.copy(), scheme, loose)
    assert entity[0].tolist() == [person, -1]
    assert math.isclose(float(score[0, 0]), 0.4, rel_tol=1e-4)
    assert not begin.any()
    blocked = np.array([math.inf, math.inf, math.inf], np.float32)
    entity, _, _ = token_decisions(logits.copy(), scheme, blocked)
    assert (entity == -1).all()


def test_entity_mass_keeps_a_token_split_between_two_types():
    # « Malletier » (mesuré) : lieu 0,48, organisation 0,42 ; aucun type seul n'atteint 0,5.
    # "Malletier" (measured): location 0.48, organisation 0.42; no single type reaches 0.5.
    scheme = LabelScheme.from_labels(IO)
    logits = logits_for([{0: 0.08, 1: 0.48, 4: 0.42, 3: 0.01}], 5)  # personne : le reste, 0,01 / person: 0.01
    entity, mass, _ = token_decisions(logits, scheme, np.full(3, 0.5, np.float32))
    assert entity[0, 0] == scheme.entities.index("LOCATION")
    assert math.isclose(float(mass[0, 0]), 0.91, rel_tol=1e-4)


def test_unwanted_types_neither_win_the_argmax_nor_count_in_the_mass():
    scheme = LabelScheme.from_labels(IO)
    logits = logits_for([{0: 0.05, 1: 0.55, 2: 0.4}], 5)  # lieu devant personne / location ahead of person
    only_person = np.array([math.inf if e != "PERSON" else 0.3 for e in scheme.entities], np.float32)
    entity, mass, _ = token_decisions(logits, scheme, only_person)
    assert entity[0, 0] == scheme.entities.index("PERSON")
    assert math.isclose(float(mass[0, 0]), 0.4, rel_tol=1e-4)


def test_misc_is_not_an_entity():
    scheme = LabelScheme.from_labels(IO)
    entity, mass, _ = token_decisions(logits_for([{3: 0.95, 0: 0.05}], 5), scheme, np.full(3, 0.1, np.float32))
    assert entity[0, 0] == -1 and float(mass[0, 0]) < 1e-6


def test_bio_begin_flag_marks_new_entity():
    scheme = LabelScheme.from_labels(BIO)
    logits = logits_for([{1: 0.9}, {2: 0.9}, {1: 0.9}], 9)
    entity, _, begin = token_decisions(logits, scheme, np.full(3, 0.5, np.float32))
    assert entity[0].tolist() == [0, 0, 0]
    assert begin[0].tolist() == [True, False, True]
    runs = group_runs(entity[0], np.ones(3, np.float32), begin[0], np.zeros(3, bool))
    assert list(zip(runs.first.tolist(), runs.stop.tolist(), strict=True)) == [(0, 2), (2, 3)]


def test_group_runs_by_entity_and_breaks():
    entity = np.array([1, 1, -1, 1, 2, 2, 2, 0], np.int8)
    score = np.array([0.9, 0.7, 0.0, 0.6, 0.8, 0.5, 0.95, 0.4], np.float32)
    breaks = np.zeros(8, bool)
    breaks[5] = True  # début d'une autre unité / another unit starts here
    runs = group_runs(entity, score, np.zeros(8, bool), breaks)
    assert list(zip(runs.first.tolist(), runs.stop.tolist(), strict=True)) == [(0, 2), (3, 4), (4, 5), (5, 7),
                                                                                (7, 8)]
    assert runs.entity.tolist() == [1, 1, 2, 2, 0]
    assert np.allclose(runs.score, [0.9, 0.6, 0.8, 0.95, 0.4])
    kept = runs.select(runs.score >= 0.7)
    assert kept.first.tolist() == [0, 4, 5]


def test_group_runs_empty():
    runs = group_runs(np.full(3, -1, np.int8), np.zeros(3, np.float32), np.zeros(3, bool), np.zeros(3, bool))
    assert runs.first.size == 0
    starts, ends = run_extents(np.zeros(3, np.int64), np.ones(3, np.int64), runs)
    assert starts.size == ends.size == 0


def test_run_extents_cover_overlapping_tokens():
    # « ▁ » isolé chevauche le jeton suivant (CamemBERT) / a lone "▁" overlaps the next token.
    starts = np.array([0, 5, 5, 8], np.int64)
    ends = np.array([4, 6, 8, 12], np.int64)
    runs = group_runs(np.array([0, 0, 0, -1], np.int8), np.ones(4, np.float32), np.zeros(4, bool),
                      np.zeros(4, bool))
    lo, hi = run_extents(starts, ends, runs)
    assert (lo.tolist(), hi.tolist()) == ([0], [8])
