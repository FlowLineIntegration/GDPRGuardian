"""Mutations équipe rouge : positions recalculées, déterminisme, couverture des opérateurs.

Red-team mutations: recomputed offsets, determinism, operator coverage.
"""

from __future__ import annotations

import unicodedata
from pathlib import Path
from random import Random

import pytest
from tools.eval import mutate as mutate_module
from tools.eval.generate import generate_corpus
from tools.eval.generate import main as generate_main
from tools.eval.mutate import MUTATIONS, MUTATIONS_BY_NAME, mutate_corpus, mutate_document, select
from tools.eval.mutate import main as mutate_main
from tools.eval.schema import Document, read_jsonl


@pytest.fixture(scope="module")
def base() -> list[Document]:
    return generate_corpus(54, seed=21)


def _outside(doc: Document) -> list[str]:
    """Texte hors zones / text outside spans."""
    pieces, cursor = [], 0
    for span in doc.spans:
        pieces.append(doc.text[cursor:span.start])
        cursor = span.end
    pieces.append(doc.text[cursor:])
    return pieces


def test_operator_names_are_unique():
    assert len(MUTATIONS_BY_NAME) == len(MUTATIONS)


@pytest.mark.parametrize("mutation", MUTATIONS, ids=lambda m: m.name)
def test_mutation_preserves_structure(base, mutation):
    produced = 0
    for doc in base:
        mutated = mutate_document(doc, mutation, Random(f"t/{doc.doc_id}"))
        if mutated is None:
            continue
        produced += 1
        mutated.check()
        assert mutated.mutation == mutation.name and mutated.meta["base"] == doc.doc_id
        assert _outside(mutated) == _outside(doc)
        assert len(mutated.spans) == len(doc.spans)
        for old, new in zip(doc.spans, mutated.spans, strict=True):
            assert (old.label, old.entity_id, old.identifier_type) == (new.label, new.entity_id, new.identifier_type)
            old_value, new_value = doc.text[old.start:old.end], mutated.text[new.start:new.end]
            if new.mutation is None:
                assert new_value == old_value
            else:
                assert new_value != old_value and new.label in mutation.labels
    assert produced > 0, f"{mutation.name} ne s'applique à aucun document / never applies"


def test_mutations_are_deterministic(base):
    first = [d.to_json() for d in mutate_corpus(base[:9], MUTATIONS[:12], seed=5)]
    again = [d.to_json() for d in mutate_corpus(base[:9], MUTATIONS[:12], seed=5)]
    assert first == again


@pytest.mark.parametrize(("name", "value", "expected"), [
    ("nbsp", "06 12 34 56 78", "06\u00a012\u00a034\u00a056\u00a078"),
    ("compact", "FR76 3000 6000 0112", "FR76300060000112"),
    ("dots", "06 12 34 56 78", "06.12.34.56.78"),
    ("at_brackets", "jean.dupont@exemple.fr", "jean.dupont [at] exemple.fr"),
    ("dot_point", "jean.dupont@exemple.fr", "jean.dupont@exemple(point)fr"),
    ("superscript", "1 85", "¹ ⁸⁵"),
    ("surname_first", "Jean Dupont", "DUPONT Jean"),
    ("upper", "Éloïse Le Goff", "ÉLOÏSE LE GOFF"),
    ("strip_accents", "Éloïse", "Eloise"),
    ("letter_spacing", "06 12", "0 6   1 2"),
    ("markdown_bold", "Jean Dupont", "**Jean Dupont**"),
    ("nb_hyphen", "Jean-Pierre", "Jean\u2011Pierre"),
])
def test_known_rewrites(name, value, expected):
    assert MUTATIONS_BY_NAME[name](value, Random(0)) == expected


@pytest.mark.parametrize(("name", "value"), [
    ("surname_first", "DUPONT Jean"), ("surname_first", "J. Dupont"), ("nbsp", "0612345678"),
    ("strip_accents", "Dupont"), ("ocr", "ABCD"), ("pdf_hyphenation", "Rey 12"), ("letter_spacing", "X"),
])
def test_not_applicable_returns_none(name, value):
    assert MUTATIONS_BY_NAME[name](value, Random(0)) is None


def test_pdf_hyphenation_cuts_inside_a_word():
    for seed in range(50):
        value = MUTATIONS_BY_NAME["pdf_hyphenation"]("Jean Dupont", Random(seed))
        assert value is not None and value.replace("-\n", "") == "Jean Dupont"
        before, after = value.split("-\n")
        assert before[-2:].isalpha() and after[:2].isalpha()  # au moins 2 lettres de chaque côté / 2 letters


def test_hangul_filler_is_inserted_inside_the_value():
    value = MUTATIONS_BY_NAME["hangul_filler"]("Jean Dupont", Random(3))
    assert value is not None and value.count("\u3164") == 3 and value.replace("\u3164", "") == "Jean Dupont"


def test_operators_never_use_raw_invisible_characters():
    # Les caractères invisibles s'écrivent en échappements dans le source (revue) / escapes in the source.
    source = Path(mutate_module.__file__).read_text(encoding="utf-8")
    raw = {f"U+{ord(c):04X}" for c in source if unicodedata.category(c) in ("Cf", "Mn", "Zs") and c != " "}
    assert not raw, raw


def test_cli_round_trip(tmp_path, capsys):
    corpus, mutated = tmp_path / "corpus.jsonl", tmp_path / "mutated.jsonl"
    assert generate_main(["--docs", "9", "--seed", "4", "--out", str(corpus)]) == 0
    assert mutate_main(["--in", str(corpus), "--out", str(mutated), "--only", "nbsp,upper"]) == 0
    docs = list(read_jsonl(mutated))
    assert docs and {d.mutation for d in docs} == {"nbsp", "upper"}
    assert mutate_main(["--list"]) == 0 and "hangul_filler" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        mutate_main(["--in", str(corpus), "--out", str(mutated), "--only", "nope"])


def test_invisible_insertions_stay_inside_span():
    mutation = MUTATIONS_BY_NAME["zero_width_space"]
    value = mutation("1 85 05 78 006 084 36", Random(1))
    assert value is not None and value.count("\u200b") == 3
    assert value[0] != "\u200b" and value[-1] != "\u200b"


def test_select():
    assert select(None) == MUTATIONS
    assert [m.name for m in select("nbsp, ocr")] == ["nbsp", "ocr"]
    with pytest.raises(ValueError, match=r"inconnus|unknown"):
        select("nope")
