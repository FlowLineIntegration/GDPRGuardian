"""Générateur de corpus : déterminisme, positions exactes, validité des valeurs annotées.

Corpus generator: determinism, exact offsets, validity of annotated values.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import date
from random import Random

import pytest
from faker import Faker
from tools.eval.generate import CorpusGenerator, Person, dept_of, generate_corpus
from tools.eval.schema import DIRECT, GOLD_LABELS, NO_MASK, Document, read_jsonl, write_jsonl
from tools.eval.templates import ENGLISH_TEMPLATES, KINDS, TEMPLATES

from gdprguardian.validators import fr as fr_validators
from gdprguardian.validators import intl as intl_validators

PER_KIND = 24


@pytest.fixture(scope="module")
def corpus() -> list[Document]:
    return generate_corpus(PER_KIND * len(KINDS), seed=11)


def test_deterministic_and_prefix_stable():
    first = [d.to_json() for d in generate_corpus(20, seed=3)]
    again = [d.to_json() for d in generate_corpus(20, seed=3)]
    assert first == again
    assert generate_corpus(5, seed=3)[4].to_json() == first[4]  # indépendant de la taille / size-independent
    assert [d.text for d in generate_corpus(5, seed=4)] != [d["text"] for d in first[:5]]


def test_every_template_is_rendered(corpus):
    seen = Counter((d.kind, d.meta["template"]) for d in corpus)
    for kind, templates in TEMPLATES.items():
        for index in range(len(templates)):
            assert seen[(kind, index)] > 0, (kind, index)


def test_offsets_and_invariants(corpus):
    for doc in corpus:
        doc.check()
        assert doc.spans, doc.doc_id
        for span in doc.spans:
            assert span.entity_id.startswith(doc.doc_id + ":")
            assert GOLD_LABELS[span.label] == span.identifier_type


def test_honorifics_stay_outside_person_spans(corpus):
    for doc in corpus:
        for span in doc.spans:
            if span.label == "PERSON":
                value = doc.text[span.start:span.end]
                assert not value.startswith(("M. ", "Mme ", "Dr ", "Monsieur ", "Madame ")), value


def test_annotated_identifiers_are_valid(corpus):
    validators = {"NIR": fr_validators.nir, "IBAN": intl_validators.iban, "RIB": fr_validators.rib,
                  "SIRET": fr_validators.siret, "SIREN": fr_validators.siren, "VAT": fr_validators.tva,
                  "CARD": intl_validators.card, "TAX_ID": fr_validators.spi, "RPPS": fr_validators.luhn_digits,
                  "PLATE": lambda v: v if " " in v and not v[0].isalpha() else fr_validators.siv_plate(v)}
    checked = Counter()
    for doc in corpus:
        for span in doc.spans:
            check = validators.get(span.label)
            value = doc.text[span.start:span.end]
            if check is None or (span.label == "NIR" and len(value.replace(" ", "")) == 13):
                continue
            assert check(value) is not None, (span.label, value)
            checked[span.label] += 1
    assert set(checked) == set(validators)


def test_policy_split_between_people_and_companies(corpus):
    labels = Counter((s.label, s.identifier_type) for d in corpus for s in d.spans)
    assert labels[("SIRET", DIRECT)] > 0 and labels[("COMPANY_ID", NO_MASK)] > 0
    assert labels[("RIB_SPLIT", DIRECT)] > 0
    decoys = {label for (label, kind) in labels if kind == NO_MASK}
    assert {"AMOUNT", "LEGAL_REF", "EVENT_DATE", "ORDER_NUMBER", "INVOICE_NUMBER", "PRODUCT_REF"} <= decoys


def test_repeated_mentions_share_entity(corpus):
    entities = Counter(s.entity_id for d in corpus for s in d.spans if s.label == "PERSON")
    assert max(entities.values()) >= 3  # même personne citée sous plusieurs formes / several forms


def test_jsonl_round_trip(tmp_path, corpus):
    path = tmp_path / "corpus.jsonl"
    assert write_jsonl(corpus[:30], path) == 30
    loaded = list(read_jsonl(path))
    assert [d.to_json() for d in loaded] == [d.to_json() for d in corpus[:30]]
    line = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert all(s["span_text"] for s in line["spans"])


def test_document_check_rejects_overlap():
    doc = generate_corpus(1, seed=1)[0]
    first, second = doc.spans[0], doc.spans[1]
    broken = Document(doc.doc_id, doc.kind, doc.text, (first, type(second)(first.start, second.end, second.label,
                                                                             second.entity_id,
                                                                             second.identifier_type)))
    with pytest.raises(ValueError, match=r"chevauchantes|overlapping"):
        broken.check()


def test_department_of_postcode():
    assert dept_of("20000") == "2A" and dept_of("20200") == "2B"
    assert dept_of("97400") == "974" and dept_of("75011") == "75"


def test_generator_kind_override():
    doc = CorpusGenerator(5).document(0, "medical")
    assert doc.kind == "medical" and doc.doc_id == "medical-00000"


@pytest.mark.parametrize(("year", "dept", "expected"), [
    (1960, "2A", "20"), (1975, "2B", "20"), (1976, "2A", "2A"), (1990, "2B", "2B"), (1960, "75", "75"),
])
def test_corsica_nir_department_follows_the_1976_split(year, dept, expected):
    # Natifs de Corse avant 1976 : « 20 » dans le NIR ; le validateur doit l'accepter (rappel d'abord).
    # Born in Corsica before 1976: "20" in the NIR; the validator must accept it (recall first).
    person = Person("p1", Random(year), Faker("fr_FR"))
    person.__dict__.update(female=False, birth_date=date(year, 6, 15), birth_country=None,
                           _birth_place=("Ajaccio", dept))
    value = person.nir_value
    assert value[5:7] == expected and fr_validators.nir(value) == value


def test_english_templates_are_tagged_english(corpus):
    languages = {(d.kind, d.meta["template"]): d.language for d in corpus}
    assert {key for key, language in languages.items() if language == "en"} == set(ENGLISH_TEMPLATES)
    assert languages[("letter", 0)] == "fr"


def test_schema_rejects_inconsistent_span_text():
    data = generate_corpus(1, seed=1)[0].to_json()
    data["spans"][0]["span_text"] = "falsifié"
    with pytest.raises(ValueError, match="span_text"):
        Document.from_json(data)
