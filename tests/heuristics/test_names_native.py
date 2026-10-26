"""Détecteur de noms natif (Rust) : sorties identiques à la référence Python.

Native (Rust) name detector: outputs identical to the Python reference. Preuve différentielle sur les 1 000
documents du corpus, les corpus d'heuristiques, le moteur complet (texte anonymisé et rapport), et par fuzzing
(Unicode piégeux, tableaux, minuscules, accents décomposés, jetons démesurés). Differential proof on the
corpora, the full engine and by fuzzing. Zones comparées champ par champ (`Span.__eq__`), score compris.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time
import unicodedata
from dataclasses import replace
from pathlib import Path

import pytest
from heuristics_corpus import NEGATIVES, POSITIVES, parse
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from gdprguardian import Anonymizer, _native
from gdprguardian._text import FOLD_TABLE, fold, normalize
from gdprguardian.engine import DetectionContext
from gdprguardian.heuristics import _lexicon
from gdprguardian.heuristics import _vocab as V
from gdprguardian.heuristics.fr_names import FrenchNameDetector, _native_data, _native_detector
from gdprguardian.packs import parse_pack

core = pytest.importorskip("gdprguardian_core")
if not hasattr(core, "NameDetector"):
    pytest.skip("noyau sans détecteur de noms / core without the name detector", allow_module_level=True)

ROOT = Path(__file__).resolve().parents[2]
DOCS = sorted((ROOT / "datasets" / "fr" / "docs").glob("*.md"))
SETTINGS = Anonymizer(countries="FR").settings
PURE = replace(SETTINGS, native=False)
DETECTOR = FrenchNameDetector(None)


def _context(text: str, *, normalized: bool = True, pure: bool = False) -> DetectionContext:
    """Contexte comme le construit le moteur (ou brut) / context as the engine builds it (or raw)."""
    norm = normalize(text)[0] if normalized else text
    return DetectionContext(norm, fold(norm), None, ("FR",), "fr", PURE if pure else SETTINGS)


def _mismatch(text: str, *, normalized: bool = True, detector: FrenchNameDetector = DETECTOR) -> str | None:
    """Écart entre Rust et Python, ou None / Rust-Python difference, or None."""
    ctx = _context(text, normalized=normalized)
    expected = detector._detect_python(ctx)
    got = detector._detect_native(ctx)
    if got != expected:
        return f"_detect_native: {got!r} != {expected!r}"
    # Par `detect` : vue composée (texte décomposé) et filtre de segments compris / composed view included.
    native, python = detector.detect(ctx), detector.detect(_context(text, normalized=normalized, pure=True))
    return None if native == python else f"detect: {native!r} != {python!r}"


def test_native_core_is_used():
    assert _native_detector() is not None and _native_detector() is _native_detector()  # une fois / built once
    ctx = _context("Bonjour Pierre, M. Jean Dupont et Mme Rose Petit vous saluent.")
    assert DETECTOR._detect_native(ctx)  # le chemin Rust répond / the Rust path answers


def test_corpus_documents_agree():
    assert len(DOCS) >= 1000
    failures = [path.name for path in DOCS if _mismatch(path.read_text(encoding="utf-8"))]
    assert not failures, failures[:20]


def test_heuristics_corpora_agree():
    texts = [parse(document)[0] for document in POSITIVES + NEGATIVES]
    for name in ("fr_sentences.txt", "fr_heldout.txt"):
        path = ROOT / "tests" / "ner" / "data" / name
        if path.exists():
            texts += [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(texts) > 100
    failures = [text for text in texts if _mismatch(text)]
    assert not failures, failures[:10]


def test_anonymised_text_and_report_are_identical(monkeypatch):
    # Même moteur, seul le détecteur change de chemin / same engine, only the detector's path changes.
    anonymizer = Anonymizer(countries="FR", explain=True)
    texts = [path.read_text(encoding="utf-8") for path in DOCS[::4]]
    native = [anonymizer.anonymize(text) for text in texts]
    monkeypatch.setattr(FrenchNameDetector, "_detect_native", lambda self, ctx: None)
    python = [anonymizer.anonymize(text) for text in texts]

    def stable(report: dict) -> dict:
        return {k: v for k, v in report.items() if k != "timings_ms"}

    for a, b in zip(native, python, strict=True):
        assert a.text == b.text
        assert stable(a.report) == stable(b.report)
        assert a.analysis.spans == b.analysis.spans


def test_pure_python_engine_gives_the_same_text():
    texts = [path.read_text(encoding="utf-8") for path in DOCS[::10]]
    native, pure = Anonymizer(countries="FR"), Anonymizer(countries="FR", native=False)
    for text in texts:
        assert native.anonymize(text).text == pure.anonymize(text).text


def test_pure_python_mode_never_builds_the_core():
    # Construit au premier usage seulement : `native=False` ne paie rien / built on first use only.
    code = ("from gdprguardian import Anonymizer\nfrom gdprguardian.heuristics import fr_names\n"
            "Anonymizer(countries='FR', native=False).anonymize('Bonjour Jean Dupont, M. Martin.')\n"
            "assert fr_names._NATIVE == {}, fr_names._NATIVE\n")
    subprocess.run([sys.executable, "-c", code], check=True, env=os.environ, timeout=120)


def test_person_columns_and_segments_agree():
    pack = parse_pack({"pack": {"id": "XX"}, "context": {"person": {"fr": ["prénom"]}}})
    detector = FrenchNameDetector(pack)
    cells = ["Rose", "Marine", "comptabilité", "Jean Dupont (DRH)", "  Zoé  ", "M.", "Durand"]
    joined = "\n\n".join(cells)
    starts, ends, cursor = [], [], 0
    for cell in cells:
        starts.append(cursor)
        cursor += len(cell)
        ends.append(cursor)
        cursor += 2
    forced = [frozenset({"XX:person"}) if i % 2 == 0 else frozenset() for i in range(len(cells))]
    contexts = []
    for pure in (False, True):
        ctx = _context(joined, normalized=False, pure=pure)
        ctx.seg_starts, ctx.seg_ends, ctx.forced = starts, ends, forced
        contexts.append(ctx)
    assert detector._detect_native(contexts[0]) == detector._detect_python(contexts[0])
    assert detector.detect(contexts[0]) == detector.detect(contexts[1])


@pytest.mark.parametrize("text", [
    "A" * 50_000, "Jean " * 10_000, "M. " * 10_000, "Anne-\n" * 10_000, "| a |" * 5_000, "de " * 10_000,
    "Nom : " * 10_000, "jean.dupont@ex.fr " * 3_000, "<" + "a" * 100 + "@x.fr>", "Dupont-" * 5_000,
    " " * 50_000 + "x\n|---|---|", "|---|---" + " " * 50_000 + "x", "| a | b |\n" + "|" + " :---- |" * 2_000 + "x",
    "Rue " * 10_000, "Cordialement,\n" * 5_000, "e" + chr(0x301) * 20_000, ("e" + chr(0x301)) * 20_000,
    "Jean-" * 20 + "Pierre", "A'" * 20_000, "Nom : " + "jean " * 10_000,
], ids=lambda text: repr(text[:12]))
def test_pathological_inputs_agree_in_linear_time(text):
    ctx = _context(text)
    start = time.perf_counter()
    got = DETECTOR._detect_native(ctx)
    elapsed = time.perf_counter() - start
    assert got == DETECTOR._detect_python(ctx)
    assert elapsed < 0.5, f"{elapsed:.2f} s"


@pytest.mark.parametrize("text", [
    # Élision à plusieurs apostrophes : seule la première est remplacée (`partition`) / only the first apostrophe.
    "NÉE A'Z'A ÉÉ", "A'Z'A ÉÉ'’-ZAÉA", "PATIENT :)A'Z'A AÉ'Z'A",
])
def test_regressions_found_by_fuzzing(text):
    assert _mismatch(text) is None


def test_line_break_chain_after_an_elision_agrees():
    # « O'Brien-⏎Anne-⏎Anne… » (texte brut) : l'élision garde la chaîne ouverte. Le noyau prolonge la clé sur place
    # au lieu de recopier chaque étape : mémoire linéaire (60 Ko demandaient 2,8 Go). Raw text: the elision keeps
    # the chain open; the core extends the key in place instead of copying each step (linear memory).
    ctx = _context("Bonjour O'Brien-\n" + "Anne-\n" * 1500 + "Marie", normalized=False)
    found = DETECTOR._detect_native(ctx)
    assert found == DETECTOR._detect_python(ctx)
    assert found and found[0].value.startswith("O'Brien-Anne-Anne-")


def test_core_of_another_version_falls_back_to_python():
    # Signature ou contrat différents (noyau d'une autre version) : la référence Python sert, sans erreur à chaque
    # document. Other signature or contract (core from another version): the Python reference serves, no error.
    data = _native_data()
    assert _native.name_detector(lambda: {**data, "constants": {**data["constants"], "MAX_RUN": 99}}) is None
    assert _native.name_detector(lambda: {**data, "unknown": 1}) is None
    assert _native.name_detector(lambda: data) is not None


def test_lone_surrogates_fall_back_to_python():
    # Non encodable en UTF-8 : le chemin Python reprend la main et se comporte comme la référence (même erreur).
    # Not encodable as UTF-8: the Python path takes over and behaves as the reference (same error).
    ctx = _context("Mme Dupont \ud800 et Jean Martin", normalized=False)
    assert DETECTOR._detect_native(ctx) is None
    with pytest.raises(UnicodeEncodeError):
        DETECTOR._detect_python(ctx)
    with pytest.raises(UnicodeEncodeError):
        DETECTOR.detect(ctx)


def test_inconsistent_folded_text_falls_back_to_python():
    ctx = DetectionContext("Jean Dupont", "jean", None, ("FR",), "fr", SETTINGS)
    assert _native_detector().detect(ctx.text, ctx.folded, []) is None


def test_constants_and_data_are_checked_at_construction():
    data = _native_data()
    with pytest.raises(ValueError, match="GIVEN_ALONE_MIN"):
        core.NameDetector(**{**data, "constants": {**data["constants"], "GIVEN_ALONE_MIN": 99}})
    vocabulary = {k: v for k, v in data["vocabulary"].items() if k != "stop"}
    with pytest.raises(ValueError, match="stop"):
        core.NameDetector(**{**data, "vocabulary": vocabulary})
    with pytest.raises(ValueError, match="empty"):
        core.NameDetector(**{**data, "triggers": [*data["triggers"], ("", 1, True, True)]})


# --- tables Unicode / Unicode tables ------------------------------------------------------------------------


def test_name_detector_reads_the_shared_unicode_table():
    """Le détecteur reçoit la table unique du noyau ; ses classes, sur chaque point des plans 0 à 3, sont celles
    de cet interpréteur (`re` et `str`). The detector gets the core's single table; its classes, on every point
    of planes 0-3, are this interpreter's (`re` and `str`)."""
    tables = _native.unicode_tables()
    assert _native_data()["unicode"] is tables
    every = _native.code_points(0, 0x40000)
    chars = every[:0xD800] + every[0xE000:]
    flags = tables.flags_of(chars)
    T = core.UnicodeTables

    def bits(bit: int) -> bytes:
        return bytes(bool(f & bit) for f in flags)

    def regex(pattern: str) -> bytes:
        found = bytearray(len(chars))
        for m in re.finditer(pattern + "+", chars):
            found[m.start():m.end()] = b"\x01" * (m.end() - m.start())
        return bytes(found)

    assert bits(T.ALPHA) == bytes(map(str.isalpha, chars))
    assert bits(T.WORD) == regex(r"\w")
    assert bits(T.LETTER) == regex(r"[^\W\d_]")
    assert bits(T.SPACE) == bytes(map(str.isspace, chars))
    assert bits(T.CAPITAL) == regex(f"[{_lexicon.UPPER}]")
    assert bits(T.UPPER) == bytes(map(str.isupper, chars))
    assert bits(T.LOWER) == bytes(map(str.islower, chars))
    assert bits(T.TITLE) == bytes(unicodedata.category(c) == "Lt" for c in chars)
    assert tables.lower(chars) == "".join(map(str.lower, chars))
    assert tables.fold(chars) == "".join(chr(FOLD_TABLE.get(ord(c), ord(c))) for c in chars)


def test_lowercased_word_lists_hold_no_sigma():
    # Le noyau ignore le sigma final de `str.lower()` : sans effet sur ces listes / final sigma is irrelevant here.
    assert not any(ch in word for word in V.DETERMINERS | V.LOCATIVES for ch in "σςΣ")


# --- fuzzing ------------------------------------------------------------------------------------------------

NAMES = ["Jean", "Dupont", "DUPONT", "Rose", "Pierre", "Blanc", "Marie-Claire", "Le Goff", "N'Diaye", "O'Brien",
         "Zélie", "Lefèvre", "Anne-", "Sophie", "Ferhati", "Nath", "VALLÉE", "Paris", "Noël", "Saint-Martin",
         "Louis", "XIV", "Ier", "Da Silva", "van der Berg", "jean", "dupont", "guillaume", "martin", "Marine",
         "Petit", "Thomas", "Moreau", "Zelensky", "Doignies", "Levallois-Perret", "D'Amico", "Johnson's", "A.",
         "J.-P.", "S.A.", "S.p.A.", "GmbH", "Curie", "Eiffel", "Albert", "Claire", "Durand", "Kowalczyk", "Gwendal",
         "A'Z'A", "O'B'Rien", "D'Ar'Cy", "L'Union", "C'est",
         # Règles « rules2 » : particules, saints, lettres de série, organisations, codes postaux.
         "Le", "Verger", "Le Verger", "LE VERGER", "Saint", "SAINT", "Saint Quentin", "St", "Bodacc", "B",
         "Bodacc B", "Van", "De", "Ville", "Syndicat", "SAS", "S.A.R.L.", "EI", "ESPACES", "INDUSTRIES", "30600",
         "75017", "VAUVERT", "Maison", "MAISON"]
CUES = ["M.", "Mme", "Mlle", "Dr", "Me", "MM.", "Bonjour", "Cher", "Chère", "Merci,", "Cordialement,\n",
        "Bien à vous,\n", "le juge", "mon fils", "chez", "rue", "avenue", "tour", "rue du Docteur", "Nom :",
        "Prénom :", "Nom : ", "De :", "Signé par", "Patient :", "Étaient présents :", "Le médecin traitant :",
        "Notre-Dame", "à", "en", "le", "la", "de", "d'", "l'", "du", "selon", "Appelle", "née", "Fils", "& Fils",
        "Nom complet : ", "Nom commercial : ", "Nom de la société : ", "Nom du gérant : ", "Adresse : "]
GLUE = [" ", "  ", "   ", "\t", "\n", "\n\n", "\r\n", ", ", " et ", "; ", " & ", ".", ". ", "-", "-\n", "'", "’",
        "|", " | ", "\n|---|---|\n", "| Nom | Prénom |\n|---|---|\n", ":", "(", ")", "<", ">", "@", "\"",
        "jean.dupont@ex.fr", "<a.b@c.fr>", "j.martin@x.org", "*", "**", "#", "  - ", "2024", " 5", " IV", "!"]
# Pièges Unicode ; les invisibles et les diacritiques seuls par leur point de code, pour rester lisibles.
# Unicode traps; invisible characters and lone marks by code point, for legibility.
ACUTE = chr(0x301)
UNICODE = ["é", ACUTE, "e" + ACUTE, "Œ", "œ", "æ", "ß", "İ", "Σ", "ς", "ǅ", "ǈ", "Ǆ", "Ⅻ", "ⓐ", "Ⓐ", "²", "½",
           "日本", "Ωμέγα", "Жанна", "😀", "𝐀", "𐐀", "ﬁ", "ꭰ",
           *map(chr, (0x212A, 0x212B, 0x200B, 0xA0, 0x202F, 0x2060, 0x1C, 0x2028, 0x345, 0xFEFF, 0xAD))]
PIECES = st.sampled_from(NAMES + CUES + GLUE + UNICODE)
TEXTS = st.lists(st.one_of(PIECES, PIECES, PIECES, st.text(max_size=6)), max_size=60).map("".join)
LONG_TOKENS = st.text(alphabet="Aaéz-'’ " + ACUTE, min_size=30, max_size=400)


@st.composite
def tables(draw: st.DrawFn) -> str:
    """Tableau Markdown à en-têtes de personnes et cellules variées / Markdown table with person headers."""
    headers = draw(st.lists(st.sampled_from(["Nom", "Prénom", "Nom complet", "Service", "**Patient**", "Ville",
                                             "nom de famille", "Salarié", "Date"]), min_size=1, max_size=4))
    rows = draw(st.lists(st.lists(TEXTS.map(lambda s: s.replace("|", "/").replace("\n", " ")),
                                  min_size=len(headers), max_size=len(headers)), max_size=4))
    sep = draw(st.sampled_from(["|---|", "| :--- |", "|---:|", "|:---:|"]))
    eol = draw(st.sampled_from(["\n", "\r\n"]))
    lines = ["| " + " | ".join(headers) + " |", "|" + sep.strip("|") * len(headers) + "|"]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return draw(TEXTS) + eol + eol.join(lines) + eol + draw(TEXTS)


FUZZ = settings(max_examples=600, deadline=None, suppress_health_check=[HealthCheck.too_slow])


@FUZZ
@given(TEXTS)
def test_fuzz_mixed_pieces(text):
    assert _mismatch(text) is None


@FUZZ
@given(TEXTS)
def test_fuzz_raw_text_without_normalisation(text):
    # Sans `normalize` : caractères invisibles, espaces exotiques et pleine chasse restent / raw text.
    assert _mismatch(text, normalized=False) is None


@FUZZ
@given(TEXTS.map(lambda s: unicodedata.normalize("NFD", s)))
def test_fuzz_decomposed_accents(text):
    assert _mismatch(text) is None


@FUZZ
@given(tables())
def test_fuzz_markdown_tables(text):
    assert _mismatch(text) is None


@FUZZ
@given(st.lists(st.one_of(LONG_TOKENS, PIECES), max_size=8).map("".join))
def test_fuzz_long_tokens(text):
    assert _mismatch(text) is None


@FUZZ
@given(st.text(max_size=80))
def test_fuzz_arbitrary_unicode(text):
    assert _mismatch(text) is None
    assert _mismatch(text, normalized=False) is None


@FUZZ
@given(TEXTS.map(str.lower))
def test_fuzz_lowercase(text):
    assert _mismatch(text) is None


@FUZZ
@given(TEXTS.map(str.upper))
def test_fuzz_uppercase(text):
    assert _mismatch(text) is None


@st.composite
def window_limits(draw: st.DrawFn) -> str:
    """Structures au bord des fenêtres (12, 20, 32, 61, 80, 300, 512) et des bornes des motifs (30, 40, 64, 512).

    Structures at the edges of the context windows and of the patterns' bounded quantifiers.
    """
    def size(*sizes: int) -> int:
        return draw(st.sampled_from(sizes))

    name = draw(st.sampled_from(NAMES))
    builders = [
        lambda: "x" * size(58, 59, 60, 61, 62) + draw(st.sampled_from(["  ", "\t", "|", "\n"])) + "Nom :"
        + " " * size(0, 1, 4, 5) + name,
        lambda: "Cordialement" + " " * size(0, 78, 79, 80, 81) + "\n" + "y" * size(0, 299, 300, 301) + "\n" + name,
        lambda: "\n" + " " * size(30, 31, 32, 33) + name,
        lambda: "a" * size(18, 19, 20, 21) + " " * size(1, 3, 4) + name,
        lambda: "... " + "*" * size(10, 11, 12) + name,
        lambda: "w" * size(510, 511, 512, 513) + " " + name + " " + "w" * size(510, 511, 512, 513),
        lambda: draw(st.sampled_from(["", "<", "< ", "\" <"])) + "a" + "b" * size(0, 62, 63, 64) + "@x",
        lambda: "A" + "b" * size(39, 40, 41) + "-Cc" * size(0, 4, 5),
        lambda: "Nom : z" + "é" * size(0, 29, 30, 31) + draw(st.sampled_from(["", " Jean", "\n", "  y"])),
        lambda: name + " " * size(1, 2, 3) + draw(st.sampled_from(["IVXLCD", "IVXLCDM", "1999", "20245"])),
        lambda: "| Nom | Prénom |\n|" + "-" * size(2, 3, 512, 513) + "|" + " " * size(0, 3, 4) + "---|\n| " + name
        + " | Jean |",
    ]
    picks = draw(st.lists(st.integers(0, len(builders) - 1), min_size=1, max_size=4))
    return draw(st.sampled_from(["\n", " ", ". ", "\r\n"])).join(builders[i]() for i in picks)


@FUZZ
@given(window_limits())
def test_fuzz_window_limits(text):
    assert _mismatch(text) is None
    assert _mismatch(text, normalized=False) is None
