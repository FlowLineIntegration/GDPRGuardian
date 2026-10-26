"""Texte brut, décodage et aides Markdown / plain text, decoding and Markdown helpers."""

from __future__ import annotations

import codecs
import unicodedata

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from gdprguardian.convert import to_markdown
from gdprguardian.convert._encoding import decode_text, latin_codec
from gdprguardian.convert._markdown import _TAG_OPEN_RE, clean_text, clip, escape_cell, finalize, gfm_table, inline
from gdprguardian.documents import DocumentOptions, DocumentTooLargeError, UnsupportedFormatError

LOCAL = DocumentOptions(sandbox=False)
FRENCH = "Le salarié Jérôme Dupont réside à Évry ; café crème, déjà vu à l'été."


@pytest.mark.parametrize(("text", "encoding"), [
    (FRENCH, "utf-8"),
    (FRENCH, "cp1252"),
    ("Café crème, déjà vu à l'été.", "cp1252"),  # court : charset-normalizer seul dirait cp1257
    ("Größe, Übermäßig, Straße, Jürgen Müller wohnt in Köln.", "cp1252"),
    ("Zażółć gęślą jaźń. Paweł Łukasiewicz mieszka w Łodzi.", "cp1250"),
    ("Příliš žluťoučký kůň úpěl ďábelské ódy. Jiří Novák.", "cp1250"),
    ("Привет, как дела? Иван Петров живет в Москве. " * 3, "cp1251"),
    ("Иван Петров, Москва.", "cp1251"),  # court : charset-normalizer seul dirait CJK / alone it would say CJK
    ("Γιώργος Παπαδόπουλος, Αθήνα.", "cp1253"),
    ("日本語のテキストです。東京都千代田区に住んでいます。" * 3, "shift_jis"),
    (FRENCH, "utf-16"),
])
def test_legacy_encodings_are_decoded(text: str, encoding: str) -> None:
    assert decode_text(text.encode(encoding)) == text


def test_boms_and_declared_charsets() -> None:
    assert decode_text(codecs.BOM_UTF8 + FRENCH.encode()) == FRENCH
    assert decode_text(FRENCH.encode("utf-32")) == FRENCH
    assert decode_text("Élodie – 50 €".encode("cp1252"), "iso-8859-1") == "Élodie – 50 €"  # WHATWG
    assert decode_text(FRENCH.encode("cp1252"), "utf-8") == FRENCH  # étiquette fausse / wrong label
    assert decode_text(b"plain", "no-such-charset") == "plain"


@pytest.mark.parametrize("label", ["base64", "rot13", "hex", "zlib", "uu"])
def test_non_text_codecs_are_ignored(label: str) -> None:
    # « charset=base64 » faisait échouer toute la conversion / used to make the whole conversion fail.
    assert decode_text(FRENCH.encode(), label) == FRENCH
    eml = f"From: a@b.fr\r\nContent-Type: text/plain; charset={label}\r\n\r\n{FRENCH}\r\n".encode()
    assert FRENCH in to_markdown(eml, "m.eml", LOCAL).markdown


@pytest.mark.parametrize("stray", [b"\xff", b"\x92", b"\xe2\x82", b"\x80\x81"])
def test_stray_bytes_do_not_turn_utf8_into_mojibake(stray: bytes) -> None:
    # Un seul octet parasite rendait tout le texte illisible (« JĆ©rĆ´me ») : nom manqué, mais lisible par un LLM.
    # A single stray byte turned the whole text into mojibake: a name detection misses but an LLM reads.
    data = FRENCH.encode() + stray + FRENCH.encode()
    decoded = decode_text(data)
    assert decoded.startswith(FRENCH) and decoded.endswith(FRENCH)
    assert decode_text(data, "utf-8") == decoded


def test_latin_codec_votes_on_letters() -> None:
    assert latin_codec("à è é".encode("cp1252")) == "cp1252"
    assert latin_codec("łódź ą ę".encode("cp1250")) == "cp1250"
    assert latin_codec(b"ascii only") == "cp1252"


def test_clean_text() -> None:
    assert clean_text("a\r\nb\rc") == "a\nb\nc"
    assert clean_text("x\x00y\x07z\x9f\ud800\U0000fffe") == "xyz"
    assert clean_text("\N{LATIN SMALL LIGATURE FI}n \N{LATIN SMALL LIGATURE FFL}") == "fin ffl"
    assert clean_text("Jose\N{COMBINING ACUTE ACCENT}") == "Jos\N{LATIN SMALL LETTER E WITH ACUTE}"
    assert clean_text("tab\tok") == "tab\tok"


def test_line_and_page_separators_keep_words_apart() -> None:
    # Saut de page de pdftotext, tabulation verticale de Word, NEL, U+2028 : jamais « JeanDupont ».
    # pdftotext form feed, Word vertical tab, NEL, U+2028: never "JeanDupont".
    assert clean_text("Jean\x0cDupont\x0bMarie\x85Curie\u2028Paul\u2029Durand\x1eFin") == (
        "Jean\nDupont\nMarie\nCurie\nPaul\nDurand\nFin")
    assert to_markdown(b"page 1 Jean\x0cDupont page 2", "a.txt", LOCAL).markdown == "page 1 Jean\nDupont page 2"


def test_clip_never_leaves_part_of_an_identifier() -> None:
    assert clip("court", 10) == "court"
    assert clip("Dossier NIR 1 85 05 78 006 084 91 de Jean", 25) == "Dossier NIR […]"
    assert clip("jean.dupont@exemple.fr marie.martin@exemple.fr", 30) == "jean.dupont@exemple.fr […]"
    assert clip("x" * 50, 10) == "x" * 10 + " […]"
    assert len(clip("mot " * 1000, 300)) <= 304


@settings(max_examples=300, deadline=None)
@given(st.text(), st.integers(min_value=1, max_value=60))
def test_clip_is_a_bounded_word_prefix(text: str, limit: int) -> None:
    clipped = clip(text, limit)
    if clipped.endswith(" […]"):
        head = clipped.removesuffix(" […]")
        assert len(head) <= limit and inline(text).startswith(head)
    else:
        assert clipped == inline(text) and len(clipped) <= limit


@settings(max_examples=300, deadline=None)
@given(st.text(alphabet=st.characters(codec="utf-8") | st.sampled_from("<>/\x00\x0b\x0c\x85\u2028\ufb01\r\n\t ")))
def test_finalize_output_is_clean_and_stable(text: str) -> None:
    markdown = finalize(text)
    assert finalize(markdown) == markdown
    assert _TAG_OPEN_RE.search(markdown) is None
    assert not any(unicodedata.category(char) in ("Cc", "Cs") and char not in "\n\t" for char in markdown)


def test_finalize_collapses_blank_lines_and_trailing_spaces() -> None:
    assert finalize("\n\n a  \n\n\n\nb\t\n\n") == " a\n\nb"
    assert finalize("") == ""


def test_raw_html_in_document_text_is_neutralised() -> None:
    text = 'Voir <img src="https://evil.example/x?d=1"> et </script> ; écrire à <jean@exemple.fr>, 3 < 4.'
    assert finalize(text) == ('Voir &lt;img src="https://evil.example/x?d=1"> et &lt;/script> ; écrire à '
                              "<jean@exemple.fr>, 3 < 4.")
    assert finalize("<!-- page 2 -->\n\ntexte") == "<!-- page 2 -->\n\ntexte"


def test_escaped_markup_in_html_stays_text() -> None:
    html = b"<p>Code : &lt;img src=https://evil.example/p.gif&gt; fin</p>"
    assert to_markdown(html, "a.html", LOCAL).markdown == "Code : &lt;img src=https://evil.example/p.gif> fin"


def test_gfm_table() -> None:
    assert gfm_table([["A|B", "C"], ["x\ny", "a\\|b"], ["seul"]]) == (
        "| A\\|B | C |\n| --- | --- |\n| x y | a\\|b |\n| seul |  |")
    assert gfm_table([["", ""], []]) == ""
    assert escape_cell("  a \n  b | c ") == "a b \\| c"


def test_plain_text_and_markdown_pass_through() -> None:
    text = "# Titre\n\nmail jean_dupont@exemple.fr, tél. 06-12-34-56-78\n"
    result = to_markdown(text.encode(), "notes.md", LOCAL)
    assert result.kind == "md" and result.markdown == text.strip()
    assert to_markdown(FRENCH.encode("cp1252"), "lettre.txt", LOCAL).markdown == FRENCH


def test_text_never_needs_the_sandbox() -> None:
    # Le texte brut est décodé sur place, même avec le bac à sable activé / decoded in place even with sandbox on.
    result = to_markdown(b"bonjour", "a.txt", DocumentOptions(timeout_s=0.001))
    assert result.markdown == "bonjour"


def test_empty_file_warns() -> None:
    result = to_markdown(b"", "vide.txt", LOCAL)
    assert result.markdown == "" and result.warnings == ["Aucun texte extrait / no text extracted"]


def test_size_limits() -> None:
    with pytest.raises(DocumentTooLargeError):
        to_markdown(b"x" * 101, "a.txt", DocumentOptions(sandbox=False, max_bytes=100))


def test_binary_is_rejected() -> None:
    with pytest.raises(UnsupportedFormatError):
        to_markdown(b"\x00\x01\x02binary\x00", "a.txt", LOCAL)
