"""Modèle réel distilcamembert-base-ner, si téléchargé (marqueur `ner`) / real model, when downloaded."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest

pytest.importorskip("numpy")
pytest.importorskip("onnxruntime")

from _ner_corpus import HELDOUT_PATH, evaluate, load_corpus
from _ner_fakes import make_ctx

from gdprguardian import Anonymizer, Settings
from gdprguardian.ner import DISTILCAMEMBERT_NER, NerDetector, load_detector
from gdprguardian.ner.registry import verify_files

pytestmark = pytest.mark.ner


def detect_all(detector: NerDetector, texts: list[str], **settings: object) -> list[list]:
    return [detector.detect(make_ctx(text, **settings)) for text in texts]


def test_pinned_files_verify(real_detector):
    verify_files(real_detector.model_dir, DISTILCAMEMBERT_NER, real_detector.files)


def test_french_entities_are_masked_with_honorifics_kept(real_detector):
    # Pack INTL seul : on teste le NER, pas les heuristiques françaises / INTL only: tests NER, not FR heuristics.
    anonymizer = Anonymizer(Settings(detectors=[real_detector], countries="INTL"))
    result = anonymizer.anonymize(
        "Bonjour Jean-Baptiste Dupont, je vous écris au sujet de M. Martin, qui travaille chez Renault à Lyon. "
        "M. Dupont sera présent.")
    for secret in ("Jean-Baptiste", "Dupont", "Martin", "Renault", "Lyon"):
        assert secret not in result.text
    assert "M. [PERSONNE_2]" in result.text and "M. [PERSONNE_1] sera présent." in result.text
    assert "[ORG_1]" in result.text and "[LIEU_1]" in result.text


@pytest.mark.parametrize("text, secrets", [
    ("De : Jean Dupont <jean.dupont@entreprise-exemple.fr>", ("Jean", "Dupont")),
    ("Contact : Claire Vasseur - claire.vasseur@cabinet-vasseur-avocats.fr", ("Claire", "Vasseur")),
    ("[Jean Dupont](https://www.linkedin.com/in/jean-dupont-a1b2c3d4)", ("Jean", "Dupont")),
    ('{"name": "Jean Dupont", "city": "Lyon"}', ("Jean", "Dupont", "Lyon")),
    ("// Auteur : Jean Dupont", ("Jean", "Dupont")),
    ("SELECT * FROM clients WHERE nom = 'Dupont' AND ville = 'Lyon'", ("Dupont", "Lyon")),
    ("let me know if Jean Dupont can come to Paris.", ("Jean", "Dupont", "Paris")),
    ("Bonjour.\n```\nLe dossier de Jean Dupont est à Lyon.", ("Jean", "Dupont", "Lyon")),
    ("rdv avec m. dupont demain", ("dupont",)),
])
def test_names_in_headers_links_data_and_code_comments_are_masked(real_detector, text, secrets):
    # Lignes autrefois écartées comme « code » ou « opaques » / lines formerly skipped as "code" or "opaque".
    ctx = make_ctx(text)
    masked = {i for span in real_detector.detect(ctx) for i in range(span.start, span.end)}
    for secret in secrets:
        start = ctx.text.index(secret)
        assert set(range(start, start + len(secret))) <= masked, secret


def test_the_pinned_tokenizer_cache_can_be_disabled(real_detector):
    # Sinon des noms de documents passés resteraient dans le cache Unigram / else past names stay cached.
    assert callable(getattr(real_detector._model.get().tokenizer.model, "_resize_cache", None))


def test_int8_quality_gate_measures_agreement(tool, real_detector):
    directory = real_detector.model_dir
    assert tool.label_agreement(directory, DISTILCAMEMBERT_NER, directory / "model.onnx") == (1.0, 1.0)


def test_corpus_recall_standard_and_strict(real_detector, corpus):
    texts = [s.text for s in corpus]
    standard = evaluate(corpus, detect_all(real_detector, texts))
    strict = evaluate(corpus, detect_all(real_detector, texts, profile="strict"))
    # Mesuré le 2026-10-24 : standard 97,7 % (0 faux positif), strict 100 % (0) / measured.
    assert standard.recall() >= 0.95 and standard.recall("PERSON") >= 0.95, standard.summary()
    assert strict.recall() >= 0.99 and strict.false_positives <= 3, strict.summary()


def test_heldout_recall(real_detector):
    heldout = load_corpus(HELDOUT_PATH)
    report = evaluate(heldout, detect_all(real_detector, [s.text for s in heldout]))
    # Mesuré : 96,3 % (manqués : deux prénoms seuls dans un message familier) / measured: 96.3 %.
    assert report.recall() >= 0.93 and report.false_positives <= 2, report.summary()


def test_gating_loses_nothing_on_the_corpus(real_detector, corpus):
    texts = [s.text for s in corpus]
    ungated = real_detector.replace(gating=False)
    assert evaluate(corpus, detect_all(real_detector, texts)).recall() \
        >= evaluate(corpus, detect_all(ungated, texts)).recall()


def test_long_unit_is_windowed_without_losing_names(real_detector, corpus):
    samples = [s for s in corpus if s.gold and "\n" not in s.text][:40]
    # Une seule « phrase » de plus de 1 000 jetons / one "sentence" of more than 1,000 tokens.
    text = " ; ".join(s.text.rstrip(".") for s in samples)
    golds, cursor = [], 0
    for sample in samples:
        golds.extend((e, cursor + a, cursor + b) for e, a, b in sample.gold)
        cursor += len(sample.text.rstrip(".")) + 3
    merged = type(samples[0])(text, tuple(golds))
    for detector in (real_detector, real_detector.replace(max_tokens=64, overlap=12)):
        report = evaluate([merged], [detector.detect(make_ctx(text))])
        assert report.recall("PERSON") >= 0.9, report.summary()


def test_concurrent_calls_share_one_session(real_detector, corpus):
    texts = [s.text for s in corpus]
    expected = [[(s.start, s.end, s.entity) for s in spans] for spans in detect_all(real_detector, texts)]
    with ThreadPoolExecutor(4) as pool:
        got = list(pool.map(lambda t: [(s.start, s.end, s.entity) for s in real_detector.detect(make_ctx(t))],
                            texts))
    assert got == expected


def test_local_int8_build_keeps_fp32_recall(int8_detector, real_detector, corpus):
    verify_files(int8_detector.model_dir, DISTILCAMEMBERT_NER, int8_detector.files)
    samples = corpus + load_corpus(HELDOUT_PATH)
    texts = [s.text for s in samples]
    for profile in ("standard", "strict"):
        fp32 = evaluate(samples, detect_all(real_detector, texts, profile=profile))
        int8 = evaluate(samples, detect_all(int8_detector, texts, profile=profile))
        # Mesuré : 97,8 % contre 97,3 % (standard), 98,9 % des deux côtés (strict) / measured.
        assert int8.recall() >= fp32.recall() - 0.02, (int8.summary(), fp32.summary())
        assert int8.false_positives <= fp32.false_positives + 2


def test_load_detector_prefers_the_checked_int8_build(int8_detector):
    detector = load_detector()
    assert detector is not None and detector.files[0] == "model_int8.onnx"
    forced = load_detector(model_file="model.onnx")
    assert forced is not None and forced.files[0] == "model.onnx"
