"""Tests des convertisseurs de corpus réels (entrées inventées) / tests of the real-corpus converters (made up)."""

from __future__ import annotations

import re

from tools.corpus.fetch_real import (
    _mapa_label,
    name_pattern,
    parlamint_documents,
    parlamint_persons,
    parse_brat,
    parse_hipe,
    tokens_record,
)
from tools.corpus.real_registry import CORPORA


def test_parse_brat_joins_discontinuous_fragments() -> None:
    ann = "T1\tNOMBRE_SUJETO_ASISTENCIA 10 20\tJuan Pérez\nT2\tCALLE 30 35;40 45\tCalle Mayor\n#1\tAnnotatorNotes T1\tx"
    assert parse_brat(ann) == [(10, 20, "NOMBRE_SUJETO_ASISTENCIA"), (30, 45, "CALLE")]


def test_parse_hipe_reads_documents_and_spacing() -> None:
    tsv = "\n".join([
        "TOKEN\tNE-COARSE-LIT\tNE-COARSE-METO\tMISC",
        "# hipe2022:document_id = doc_a",
        "M\tB-PER\t_\tNoSpaceAfter",
        ".\tI-PER\t_\t_",
        "Dupont\tI-PER\t_\tEndOfLine",
        "parle\tO\t_\t_",
        "# hipe2022:document_id = doc_b",
        "Paris\tB-LOC\t_\t_",
    ])
    docs = list(parse_hipe(tsv))
    assert [d[0] for d in docs] == ["doc_a", "doc_b"]
    _doc_id, tokens, tags, nospace, eol = docs[0]
    assert tokens == ["M", ".", "Dupont", "parle"] and nospace == [True, False, False, False]
    assert eol == [False, False, True, False] and tags[0] == "B-PER"


def test_tokens_record_maps_labels_and_trims_titles() -> None:
    rec = tokens_record("x:1", "src", "fr", ["M", ".", "Dupont", "à", "Lyon"], ["B-PER", "I-PER", "I-PER", "O",
                        "B-LOC"], {"PER": "PERSON", "LOC": "LOCATION"}.get, [True, False, False, False, False])
    assert rec["text"] == "M. Dupont à Lyon"
    assert [(s["text"], s["label"]) for s in rec["spans"]] == [("Dupont", "PERSON"), ("Lyon", "LOCATION")]


def test_mapa_label_policy() -> None:
    assert _mapa_label("PERSON", "family name") == "PERSON"
    assert _mapa_label("PERSON", "profession") == "OTHER"
    assert _mapa_label("ADDRESS", "city") == "LOCATION"
    assert _mapa_label("ADDRESS", "building") == "ADDRESS"
    assert _mapa_label("AMOUNT", "") is None


TEI_PERSONS = b"""<listPerson xmlns="http://www.tei-c.org/ns/1.0">
<person xml:id="P1"><persName><forename>Anne</forename><surname>Exemple</surname></persName><sex value="F"/></person>
<person xml:id="P2"><persName><forename>Paul</forename><surname>de Test</surname></persName><sex value="M"/></person>
</listPerson>"""

TEI_SITTING = b"""<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body><div>
<u who="#P2" ana="#chair"><seg>La parole est \xc3\xa0 Mme Exemple.</seg></u>
<u who="#P1" ana="#regular"><seg>Je remercie M. de Test et Paul de Test.</seg><seg>Merci.</seg></u>
</div></body></text></TEI>"""


def test_parlamint_speakers_and_mentions() -> None:
    persons = parlamint_persons(TEI_PERSONS)
    assert persons["P1"] == ("Anne", "Exemple", "F")
    pattern = name_pattern(persons)
    assert isinstance(pattern, re.Pattern)
    docs = list(parlamint_documents(TEI_SITTING, persons, pattern, "S1", 4000))
    assert len(docs) == 1
    text = docs[0]["text"]
    assert text.startswith("M. le président. La parole est à Mme Exemple.")
    got = [(s["text"], s["origin"]) for s in docs[0]["spans"]]
    assert ("Exemple", "mention") in got            # civility + surname, civility left out
    assert ("Anne Exemple", "speaker") in got        # rendered speaker label
    assert ("de Test", "mention") in got and ("Paul de Test", "mention") in got
    assert all(s["label"] == "PERSON" for s in docs[0]["spans"])


def test_registry_is_complete() -> None:
    for name, corpus in CORPORA.items():
        assert corpus.name == name and corpus.licence and corpus.build and corpus.countries
        assert "NC" not in corpus.licence  # no non-commercial licence for published scores
