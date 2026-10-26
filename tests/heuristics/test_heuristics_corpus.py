"""Précision et rappel sur un corpus annoté et sur des noms jamais vus / precision and recall on corpora."""

from __future__ import annotations

import random
import re

import pytest
from heuristics_corpus import NEGATIVES, POSITIVES, parse

from gdprguardian import Anonymizer


def _score(fr: Anonymizer, documents: list[str]) -> tuple[int, int, int]:
    tp = fp = fn = 0
    for document in documents:
        text, expected = parse(document)
        predicted = {(s.entity, s.start, s.end) for s in fr.analyze(text).spans if s.entity in ("PERSON", "ADDRESS")}
        tp += len(predicted & set(expected))
        fp += len(predicted - set(expected))
        fn += len(set(expected) - predicted)
    return tp, fp, fn


def test_annotated_corpus_precision_and_recall(fr):
    # Correspondance exacte des zones, civilités exclues / exact span match, honorifics excluded.
    tp, fp, fn = _score(fr, POSITIVES + NEGATIVES)
    assert tp + fn >= 60
    assert tp / (tp + fp) >= 0.97
    assert tp / (tp + fn) >= 0.97


@pytest.mark.parametrize("document", NEGATIVES)
def test_negative_documents_stay_almost_untouched(fr, document):
    text, _ = parse(document)
    assert len([s for s in fr.analyze(text).spans if s.entity in ("PERSON", "ADDRESS")]) <= 1


def test_anonymized_corpus_keeps_no_annotated_value(fr):
    for document in POSITIVES:
        text, expected = parse(document)
        out = fr.anonymize(text).text
        for _, start, end in expected:
            value = text[start:end]
            assert not re.search(rf"(?<!\w){re.escape(value)}(?!\w)", out), value


TEMPLATES = [
    "Le dossier de {full} a été transmis hier au service juridique.",
    "Bonjour {first}, merci pour ton retour sur le projet.",
    "M. {last} a signé le contrat ce matin.",
    "Mme {first} {last} est convoquée le 3 mars.",
    "Étaient présents : {full}, {full2} et {full3}.",
    "{LAST} {first}, né le 12 mai 1980, demeurant à Lyon.",
    "Cordialement,\n{full}\nResponsable des achats",
    "Selon {full}, le budget est insuffisant.",
    "Contact : {first_l}.{last_l}@exemple.fr. {full} vous répondra.",
    "Le patient {full} présente une toux persistante.",
]


def test_recall_on_unseen_names():
    """Noms tirés de Faker (jamais vus pendant la mise au point), plusieurs pays / unseen Faker names."""
    faker = pytest.importorskip("faker")
    fr = Anonymizer(countries="FR")
    rng = random.Random(7)
    total = masked = 0
    for locale in ("fr_FR", "fr_FR", "de_DE", "it_IT", "es_ES", "nl_NL"):
        fake = faker.Faker(locale)
        fake.seed_instance(42)
        for _ in range(40):
            first, last = fake.first_name(), fake.last_name()
            others = [f"{fake.first_name()} {fake.last_name()}" for _ in range(2)]
            values = {"first": first, "last": last, "full": f"{first} {last}", "LAST": last.upper(),
                      "full2": others[0], "full3": others[1], "first_l": first.lower().replace(" ", ""),
                      "last_l": last.lower().replace(" ", "")}
            template = rng.choice(TEMPLATES)
            out = fr.anonymize(template.format(**values)).text
            parts = {p for key in ("first", "last", "full", "LAST", "full2", "full3") if f"{{{key}}}" in template
                     for p in values[key].split()}
            for part in parts:
                total += 1
                masked += part not in out and part.upper() not in out
    assert total > 300
    assert masked / total >= 0.93
