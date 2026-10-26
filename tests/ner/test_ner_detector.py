"""Détecteur NER avec une fausse session ONNX (toujours exécutés) / NER detector with a fake ONNX session."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

pytest.importorskip("numpy")
pytest.importorskip("tokenizers")

from _ner_fakes import BIO_LABELS, IO_LABELS, LEXICON, LOC, ORG, PER, FakeSession, make_classifier, make_ctx

import gdprguardian.ner as ner_module
from gdprguardian import Anonymizer, Settings
from gdprguardian.ner import ModelIntegrityError, ModelSpec, NerDetector, load_detector
from gdprguardian.ner.detector import _outside, _surname_form
from gdprguardian.ner.registry import INT8_RECIPE, MANIFEST_NAME, DerivedFile, ModelFile
from gdprguardian.types import PRIORITY_NER


def found(detector: NerDetector, text: str, **settings_: object) -> list[tuple[str, str]]:
    ctx = make_ctx(text, **settings_)
    return [(s.entity, ctx.text[s.start:s.end]) for s in sorted(detector.detect(ctx), key=lambda s: s.start)]


def test_spans_follow_the_detector_contract(make_detector):
    detector = make_detector()
    ctx = make_ctx("Bonjour Jean Dupont, Martin travaille chez Renault à Lyon.")
    spans = sorted(detector.detect(ctx), key=lambda s: s.start)
    assert [(s.entity, ctx.text[s.start:s.end]) for s in spans] == [
        ("PERSON", "Jean Dupont"), ("PERSON", "Martin"), ("ORG", "Renault"), ("LOCATION", "Lyon")]
    for span in spans:
        assert span.label == span.entity and span.source == "ner" and span.priority == PRIORITY_NER
        assert span.propagate is (span.entity == "PERSON") and span.personal and span.value is None
        assert 0.5 <= span.score <= 1.0
    assert spans[0].forms == ("Dupont",) and spans[1].forms == ()


def test_honorifics_and_greetings_stay_outside(make_detector):
    session = FakeSession({**LEXICON, "Mme": (PER, 0.9), "Bonjour": (PER, 0.9)})
    assert found(make_detector(session), "Bonjour Mme Claire Vasseur") == [("PERSON", "Claire Vasseur")]


def test_placeholders_already_in_the_input_are_never_tagged(make_detector):
    # Mesuré sur le vrai modèle : « [ORG_2] » devenait « [[ORG_1]] » / measured on the real model.
    session = FakeSession({**LEXICON, "ORG_2": (ORG, 0.9), "PERSONNE_3": (PER, 0.9)})
    detector = make_detector(session)
    assert found(detector, "M. [PERSONNE_3] travaille chez [ORG_2] et Renault.") == [("ORG", "Renault")]
    anonymizer = Anonymizer(Settings(detectors=[detector], countries="INTL"))
    text = "M. [PERSONNE_3] travaille chez [ORG_2]."
    assert anonymizer.anonymize(text).text == text


def test_pieces_outside_placeholders():
    starts, ends = [5, 20], [10, 30]
    assert list(_outside(0, 40, starts, ends)) == [(0, 5), (10, 20), (30, 40)]
    assert list(_outside(6, 9, starts, ends)) == []
    assert list(_outside(8, 22, starts, ends)) == [(10, 20)]
    assert list(_outside(0, 4, [], [])) == [(0, 4)]


@given(st.lists(st.integers(1, 6), min_size=0, max_size=12), st.integers(0, 60), st.integers(0, 60))
def test_pieces_outside_placeholders_match_brute_force(gaps, a, b):
    starts, ends, cursor = [], [], 0
    for i, gap in enumerate(gaps):
        cursor += gap
        if i % 2 == 0:
            starts.append(cursor)
        else:
            ends.append(cursor)
    starts = starts[:len(ends)]
    start, end = min(a, b), max(a, b)
    covered = {i for lo, hi in _outside(start, end, starts, ends) for i in range(lo, hi)}
    blocked = {i for lo, hi in zip(starts, ends, strict=True) for i in range(lo, hi)}
    assert covered == set(range(start, end)) - blocked


def test_file_nouns_stay_outside_so_one_person_keeps_one_placeholder(make_detector):
    # Le vrai modèle rend « Dossier Lemoine » et « Famille Dupont » en entier (mesuré) / the real model does.
    session = FakeSession({**LEXICON, "Dossier": (PER, 0.9), "Famille": (PER, 0.9)})
    detector = make_detector(session)
    assert found(detector, "Famille Dupont") == [("PERSON", "Dupont")]
    anonymizer = Anonymizer(Settings(detectors=[detector], countries="INTL"))
    result = anonymizer.anonymize("Dossier Dupont.\n\nJean Dupont a signé. Dupont vient.")
    assert result.text == "Dossier [PERSONNE_1].\n\n[PERSONNE_1] a signé. [PERSONNE_1] vient."


def test_pronouns_and_common_nouns_are_dropped(make_detector):
    assert found(make_detector(), "Jean dit que il vient.") == [("PERSON", "Jean")]


def test_sub_words_and_hyphenated_names_are_masked_whole(make_detector):
    session = FakeSession({**LEXICON, "Pierre": (0, 0.99)})
    assert found(make_detector(session), "Jean-Pierre Dupont vient.") == [("PERSON", "Jean-Pierre Dupont")]


def test_runs_join_across_apostrophe_and_particles_are_trimmed(make_detector):
    joined = FakeSession({**LEXICON, "d": (PER, 0.9)})
    text = "Fabienne Ollivier d'Orléans vient."
    assert found(make_detector(joined), text) == [("PERSON", "Fabienne Ollivier d'Orléans")]
    dangling = FakeSession({**LEXICON, "d": (PER, 0.9), "Orléans": (0, 0.99)})
    assert found(make_detector(dangling), text) == [("PERSON", "Fabienne Ollivier")]


def test_elision_and_leading_common_words_left_outside_places(make_detector):
    text = "Rendez-vous à l'hôpital Necker."
    assert found(make_detector(), text) == [("LOCATION", "Necker")]
    session = FakeSession({**LEXICON, "l": (LOC, 0.9)})
    assert found(make_detector(session), text) == [("LOCATION", "Necker")]


def test_lowercase_person_is_kept_whole(make_detector):
    session = FakeSession({**LEXICON, "marie": (PER, 0.9), "curie": (PER, 0.9)})
    assert found(make_detector(session), "j'ai vu madame marie curie hier") == [("PERSON", "marie curie")]


def test_spans_cross_soft_wraps_but_never_paragraphs_or_cells(make_detector):
    session = FakeSession({**LEXICON, "marie": (PER, 0.9)})
    detector = make_detector(session)
    # Retour à la ligne souple (même phrase) : une seule personne / soft wrap within a sentence: one person.
    assert found(detector, "Le dossier de Jean\nmarie est prêt.") == [("PERSON", "Jean\nmarie")]
    paragraphs = "Le dossier de Jean\n\nmarie est prêt."
    assert found(make_detector(session, gating=False), paragraphs) == [("PERSON", "Jean"), ("PERSON", "marie")]
    assert found(detector, "| Jean | Dupont | Lyon |") == [
        ("PERSON", "Jean"), ("PERSON", "Dupont"), ("LOCATION", "Lyon")]


def test_segments_are_respected(make_detector):
    ctx = make_ctx(["Jean", "Dupont habite à Lyon", "le contrat"])
    spans = make_detector().detect(ctx)
    assert sorted(ctx.text[s.start:s.end] for s in spans) == ["Dupont", "Jean", "Lyon"]
    for span in spans:
        assert span.end <= ctx.segment(span.start)[2]


def test_gating_sends_only_sentences_with_cues(make_detector, fake_session):
    text = "Le contrat est signé. Jean vient. Il habite rue du Monde."
    assert found(make_detector(), text) == [("PERSON", "Jean")]
    assert fake_session.sequences == 2
    fake_session.calls.clear()
    make_detector(gating=False).detect(make_ctx(text))
    assert fake_session.sequences == 3


def test_identical_units_are_inferred_once(make_detector, fake_session):
    ctx = make_ctx(["Jean Dupont"] * 5)
    spans = make_detector().detect(ctx)
    assert fake_session.sequences == 1
    assert sorted(s.start for s in spans) == list(ctx.seg_starts)
    assert all(ctx.text[s.start:s.end] == "Jean Dupont" for s in spans)


_WORDS = ["Jean", "Pierre", "Dupont", "Martin", "Lyon", "Renault", "Transports", "Rivière", "le", "de", "et",
          "contrat", "signé", "vient", "Coupe", "Monde", "inconnu"]


@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(st.lists(st.sampled_from(_WORDS), min_size=1, max_size=120), st.integers(0, 3), st.integers(1, 600))
def test_windowing_is_invisible_to_a_context_free_model(make_detector, words, overlap, budget):
    text = "Jean " + " ".join(words)
    small = make_detector(max_tokens=16, overlap=overlap, batch_tokens=budget)
    large = make_detector(max_tokens=512, batch_tokens=budget)
    assert found(small, text) == found(large, text)


def test_batches_follow_the_padded_token_budget(make_detector, fake_session):
    # Cellules courtes : beaucoup par appel ; jamais plus de jetons que le budget, sauf une séquence seule.
    # Short cells: many per call; never more padded tokens than the budget, except a lone sequence.
    cells = [f"Jean {word}" for word in ("Dupont", "Martin", "Lyon", "Paris", "Renault", "Pierre")] * 3
    make_detector(batch_tokens=16).detect(make_ctx([*cells, "Jean " * 40]))
    # Distinctes : 42 jetons (seule), 5, puis cinq de 4 / distinct: 42 tokens (alone), 5, then five of 4.
    assert fake_session.calls == [(1, 42), (3, 5), (3, 4)]
    assert all(rows * width <= 16 or rows == 1 for rows, width in fake_session.calls)


def test_fast_profile_and_entity_filters(make_detector, fake_session):
    detector = make_detector()
    text = "Jean travaille chez Renault à Lyon."
    assert found(detector, text, profile="fast") == []
    assert found(detector, text, entities=frozenset({"EMAIL"})) == []
    assert fake_session.calls == []
    assert found(detector, text, entities=frozenset({"ORG"})) == [("ORG", "Renault")]
    assert found(detector, text, exclude_entities=frozenset({"PERSON"})) == [("ORG", "Renault"),
                                                                             ("LOCATION", "Lyon")]
    assert found(make_detector(entities=("PERSON",)), text) == [("PERSON", "Jean")]


def test_strict_profile_lowers_thresholds(make_detector):
    detector = make_detector()
    assert found(detector, "Bonjour Léa.") == []
    assert found(detector, "Bonjour Léa.", profile="strict") == [("PERSON", "Léa")]
    assert found(make_detector(thresholds={"PERSON": 0.35}), "Bonjour Léa.") == [("PERSON", "Léa")]


def test_hysteresis_keeps_multi_token_entities_whole(make_detector):
    ctx = make_ctx("Signé : Transports Rivière.")
    (span,) = make_detector().detect(ctx)
    assert ctx.text[span.start:span.end] == "Transports Rivière"
    assert span.score == pytest.approx(0.8, abs=1e-3)


def test_bio_models_split_on_begin_tags(make_detector):
    session = FakeSession({"Jean": (1, 0.9), "Pierre": (2, 0.9), "Martin": (1, 0.9), "Renault": (3, 0.9)},
                          classes=9)
    detector = make_detector(session, labels=BIO_LABELS)
    assert found(detector, "Jean Pierre Martin chez Renault.") == [
        ("PERSON", "Jean Pierre"), ("PERSON", "Martin"), ("ORG", "Renault")]


def test_config_and_model_must_agree_on_classes():
    with pytest.raises(ValueError, match="classes"):
        make_classifier(FakeSession(classes=9), IO_LABELS)


def test_token_type_ids_are_fed_when_the_model_expects_them(make_detector):
    session = FakeSession(extra_inputs=("token_type_ids",))
    assert found(make_detector(session), "Jean vient.") == [("PERSON", "Jean")]
    assert not session.feeds[0]["token_type_ids"].any()


def test_concurrent_detection_is_consistent(make_detector):
    detector = make_detector()
    texts = [f"Jean {'et Martin ' * (i % 7)}travaille chez Renault à Lyon {i}." for i in range(64)]
    expected = [found(detector, t) for t in texts]
    with ThreadPoolExecutor(8) as pool:
        assert list(pool.map(lambda t: found(detector, t), texts)) == expected


def test_engine_integration_keeps_one_placeholder_per_person(make_detector):
    # Pack INTL seul : on teste le NER, pas les heuristiques françaises / INTL only: tests NER, not FR heuristics.
    anonymizer = Anonymizer(Settings(detectors=[make_detector()], countries="INTL"))
    result = anonymizer.anonymize("Bonjour Jean Dupont. M. Dupont travaille à Lyon chez Renault.")
    assert result.text == "Bonjour [PERSONNE_1]. M. [PERSONNE_1] travaille à [LIEU_1] chez [ORG_1]."
    assert "detector:NER" in result.report["timings_ms"]


def test_surname_form():
    assert _surname_form("Jean Dupont") == ("Dupont",)
    assert _surname_form("DUPONT Jean") == ("DUPONT",)
    assert _surname_form("Martin") == ()
    assert _surname_form("Jean Le") == ()
    # Minuscules : « blanc » propagé masquerait chaque « vin blanc » / lowercase surnames are not propagated.
    assert _surname_form("jean blanc") == ()


def test_names_next_to_e_mails_links_and_in_data_lines_are_found(make_detector):
    detector = make_detector()
    text = ("De : Jean Dupont <jean.dupont@entreprise-exemple.fr>\n"
            "[Claire Vasseur](https://www.linkedin.com/in/claire-vasseur-a1b2c3d4)\n"
            "{\"nom\": \"Martin\", \"ville\": \"Lyon\"}\n"
            "```\n// relu par Pierre\n")
    assert found(detector, text) == [("PERSON", "Jean Dupont"), ("PERSON", "Claire Vasseur"), ("PERSON", "Martin"),
                                     ("LOCATION", "Lyon"), ("PERSON", "Pierre")]


def test_short_context_models_keep_a_linear_number_of_windows(fake_session):
    from _ner_fakes import make_tokenizer

    from gdprguardian.ner import TokenClassifier

    narrow = TokenClassifier(fake_session, make_tokenizer(), IO_LABELS, pad_id=0, max_length=16)
    detector = NerDetector(classifier=narrow, spec=None, max_tokens=512, overlap=127, gating=False)
    text = "Jean " * 300
    spans = detector.detect(make_ctx(text))
    # 300 jetons, fenêtres de 14 : sans borne du chevauchement, ~290 séquences / without the bound, ~290 sequences.
    assert fake_session.sequences <= 300 // 7 + 1
    assert sum(span.end - span.start for span in spans) >= len(text.strip()) - 300


def test_tokenizer_word_cache_is_disabled(fake_session):
    # Le cache de mots de tokenizers garderait les noms des documents passés / it would keep past names.
    from _ner_fakes import make_tokenizer

    from gdprguardian.ner import TokenClassifier

    resized: list[int] = []

    class Tracked:
        def __init__(self) -> None:
            self.inner = make_tokenizer()
            self.model = SimpleNamespace(_resize_cache=resized.append)

        def encode(self, text: str, add_special_tokens: bool = True) -> Any:
            return self.inner.encode(text, add_special_tokens=add_special_tokens)

    TokenClassifier(fake_session, Tracked(), IO_LABELS, pad_id=0)
    assert resized == [0]


def test_tokenizers_without_locatable_special_tokens_are_rejected(fake_session):
    from gdprguardian.ner import TokenClassifier

    class Opaque:
        def encode(self, text: str, add_special_tokens: bool = True) -> SimpleNamespace:
            return SimpleNamespace(ids=[7, 8] if add_special_tokens else [9])

    with pytest.raises(ValueError, match="special"):
        TokenClassifier(fake_session, Opaque(), IO_LABELS, pad_id=0)


def test_options_are_validated():
    for options in ({"max_tokens": 8}, {"max_tokens": 1024}, {"overlap": 200}, {"batch_tokens": 0},
                    {"entities": ("EMAIL",)}, {"thresholds": {"PERSON": 0.0}}, {"strict_thresholds": {"ORG": 1.5}},
                    {"thresholds": {"PERSONS": 0.4}}):
        with pytest.raises(ValueError):
            NerDetector("unused", **options)
    with pytest.raises(FileNotFoundError):
        NerDetector(spec=ModelSpec("absent-model", (), "MIT"))


def _fake_spec(tmp_path, *, corrupt: bool) -> ModelSpec:
    files = []
    for name, content in (("model.onnx", b"onnx"), ("tokenizer.json", b"{}"), ("config.json", b"{}")):
        (tmp_path / name).write_bytes(content + (b"!" if corrupt and name == "model.onnx" else b""))
        files.append(ModelFile(name, "x/y", "0" * 40, name, len(content), hashlib.sha256(content).hexdigest()))
    return ModelSpec("fake-model", tuple(files), "MIT")


def test_model_is_verified_lazily_on_first_use(tmp_path):
    detector = NerDetector(tmp_path, spec=_fake_spec(tmp_path, corrupt=True))
    assert not detector.loaded
    with pytest.raises(ModelIntegrityError):
        detector.detect(make_ctx("Jean Dupont vient."))
    assert not detector.loaded


def test_replace_shares_the_session_and_validates(make_detector, fake_session):
    detector = make_detector(thresholds={"ORG": 0.9})
    lenient = detector.replace(thresholds={"PERSON": 0.35}, gating=False)
    assert lenient.thresholds == {"PERSON": 0.35, "ORG": 0.9, "LOCATION": 0.5}
    assert detector.thresholds["PERSON"] == 0.5 and detector.gating and not lenient.gating
    assert found(lenient, "Bonjour Léa.") == [("PERSON", "Léa")] and found(detector, "Bonjour Léa.") == []
    assert lenient._model is detector._model
    with pytest.raises(ValueError):
        detector.replace(threads=2)
    with pytest.raises(ValueError):
        detector.replace(overlap=500)


def test_load_detector_returns_none_when_unavailable(tmp_path, monkeypatch):
    assert load_detector(tmp_path) is None
    spec = _fake_spec(tmp_path, corrupt=False)
    assert isinstance(load_detector(tmp_path, spec=spec), NerDetector)
    monkeypatch.setattr(ner_module, "runtime_available", lambda: False)
    assert load_detector(tmp_path, spec=spec) is None


def test_load_detector_prefers_only_a_recorded_derived_build(tmp_path):
    base = _fake_spec(tmp_path, corrupt=False)
    spec = ModelSpec(base.name, base.files, "MIT", (DerivedFile("model_int8.onnx", "model.onnx", INT8_RECIPE),))
    (tmp_path / "model_int8.onnx").write_bytes(b"int8")
    unrecorded = load_detector(tmp_path, spec=spec)
    assert unrecorded is not None and unrecorded.files[0] == "model.onnx"
    record = {"source_sha256": spec.file("model.onnx").sha256, "recipe": INT8_RECIPE, "size": 4,
              "sha256": hashlib.sha256(b"int8").hexdigest()}
    (tmp_path / MANIFEST_NAME).write_text(json.dumps({"derived": {"model_int8.onnx": record}}), encoding="utf-8")
    recorded = load_detector(tmp_path, spec=spec)
    assert recorded is not None and recorded.files[0] == "model_int8.onnx"
    explicit = load_detector(tmp_path, spec=spec, model_file="model.onnx")
    assert explicit is not None and explicit.files[0] == "model.onnx"


def test_load_detector_honours_folder_order_before_the_int8_preference(tmp_path, monkeypatch):
    # $GDPRGUARDIAN_MODELS_DIR (fp32 seul) passe avant un autre cache qui a un INT8 inscrit.
    # $GDPRGUARDIAN_MODELS_DIR (fp32 only) wins over another cache holding a recorded INT8.
    first, second = tmp_path / "env", tmp_path / "cache"
    first.mkdir()
    second.mkdir()
    base = _fake_spec(first, corrupt=False)
    _fake_spec(second, corrupt=False)
    spec = ModelSpec(base.name, base.files, "MIT", (DerivedFile("model_int8.onnx", "model.onnx", INT8_RECIPE),))
    (second / "model_int8.onnx").write_bytes(b"int8")
    record = {"source_sha256": spec.file("model.onnx").sha256, "recipe": INT8_RECIPE, "size": 4,
              "sha256": hashlib.sha256(b"int8").hexdigest()}
    (second / MANIFEST_NAME).write_text(json.dumps({"derived": {"model_int8.onnx": record}}), encoding="utf-8")
    monkeypatch.setattr(ner_module, "candidate_dirs", lambda name: [first, second])
    detector = load_detector(spec=spec)
    assert detector is not None and (detector.model_dir, detector.files[0]) == (first, "model.onnx")
    monkeypatch.setattr(ner_module, "candidate_dirs", lambda name: [tmp_path / "missing", second])
    detector = load_detector(spec=spec)
    assert detector is not None and (detector.model_dir, detector.files[0]) == (second, "model_int8.onnx")


def test_repr_reveals_no_content(make_detector):
    detector = make_detector()
    detector.detect(make_ctx("Jean Dupont vient."))
    assert "Jean" not in repr(detector) and "Dupont" not in repr(detector)


def test_importing_the_package_loads_no_heavy_dependency():
    code = "import sys, gdprguardian.ner; print(sorted({'numpy', 'onnxruntime', 'tokenizers'} & set(sys.modules)))"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout
    assert out.strip() == "[]"
