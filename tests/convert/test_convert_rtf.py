"""Analyseur RTF maison / in-house RTF parser."""

from __future__ import annotations

import dataclasses
import time

import pytest
from convert_samples import AUTHOR, EMAIL, IBAN, NIR, PHONE_INTL, RTF, rtf_unicode

from gdprguardian.convert import to_markdown
from gdprguardian.convert._base import Report
from gdprguardian.convert._rtf import rtf_to_markdown
from gdprguardian.documents import DocumentError, DocumentOptions

LOCAL = DocumentOptions(sandbox=False)


def convert(rtf: str | bytes, **options: object):
    data = rtf.encode("latin-1") if isinstance(rtf, str) else rtf
    return to_markdown(data, "doc.rtf", dataclasses.replace(LOCAL, **options))


def body(rtf: str) -> str:
    return convert(r"{\rtf1\ansi " + rtf + "}").markdown


def test_sample_document() -> None:
    result = convert(RTF)
    markdown = result.markdown
    assert "# Contrat de travail" in markdown
    assert f"Salarié : Jean Dupont, NIR {NIR}" in markdown
    assert "Entête : " + EMAIL in markdown  # en-tête conservé / header kept
    assert "Café € crème łódź" in markdown  # \'hh cp1252, \uN, \fcharset238 (cp1250)
    assert f"| Nom\\|Prénom | IBAN |\n| --- | --- |\n| Dupont | {IBAN} |" in markdown
    assert "- Premier point" in markdown
    assert "Fin courriel" in markdown and "mailto" not in markdown  # résultat de champ, pas l'instruction


def test_dropped_channels_are_counted_never_output() -> None:
    result = convert(RTF)
    assert AUTHOR not in result.markdown and "Dossier secret" not in result.markdown
    assert "SUPPRIME-SECRET" not in result.markdown and "TEXTE-MASQUE" not in result.markdown
    assert PHONE_INTL not in result.markdown
    assert result.dropped == {"comments": 1, "hidden_text": 1, "images": 1, "metadata": 3, "tracked_deletions": 1}


def test_options_reveal_hidden_text_and_comments() -> None:
    result = convert(RTF, include_hidden=True, include_comments=True)
    assert "TEXTE-MASQUE" in result.markdown
    assert "[commentaire : Rappeler au " + PHONE_INTL in result.markdown
    assert AUTHOR not in result.markdown  # \atnauthor jamais émis / never output
    assert "SUPPRIME-SECRET" not in result.markdown


def test_unicode_escapes() -> None:
    smile = rtf_unicode(-10179) + "?" + rtf_unicode(-8704) + "?"
    assert body(smile + r"\par") == "\N{GRINNING FACE}"
    assert body(r"\uc0" + rtf_unicode(233) + r"t" + rtf_unicode(233)) == "été"
    assert body(r"\uc2" + rtf_unicode(8364) + r"EU suite") == "€ suite"
    assert body(rtf_unicode(61623) + "?") == "\N{MIDDLE DOT}"  # zone privée Symbol / Symbol PUA (0xF0B7)


def test_multibyte_code_page() -> None:
    assert convert(r"{\rtf1\ansi\ansicpg932 \'93\'fa\'96\'7b}").markdown == "日本"
    # Une fin de ligne brute (sans effet en RTF) ne coupe pas un caractère double octet.
    # A raw line end (meaningless in RTF) does not split a double-byte character.
    assert convert("{\\rtf1\\ansi\\ansicpg932 \\'93\r\n\\'fa\\'96\n\\'7b}").markdown == "日本"


@pytest.mark.parametrize("value", [-99999, -32769, 1114112, 9999999999])
def test_out_of_range_unicode_escape_becomes_a_replacement_character(value: int) -> None:
    # \u-99999 levait ValueError dans chr() : tout le document était perdu / used to fail the whole document.
    assert body("a" + rtf_unicode(value) + "?b") == "a\N{REPLACEMENT CHARACTER}b"


def test_binary_data_is_skipped_unparsed() -> None:
    # Les 8 octets bruts « }{\}\\{x » contiennent des accolades : jamais analysés / raw bytes with braces.
    assert body(r"{\pict\bin8 }{\}\\{x}apr\'e8s") == "après"


def test_symbols_and_specials() -> None:
    expected = "a\xa0b-cd {x} \\ \N{LEFT SINGLE QUOTATION MARK}q\N{RIGHT SINGLE QUOTATION MARK}\t\N{EM DASH}"
    assert body(r"a\~b\_c\-d \{x\} \\ \lquote q\rquote\tab\emdash") == expected


def test_footnotes_stay_inline() -> None:
    assert body(r"Texte{\super\chftn}{\footnote\pard Note IBAN\par} suite\par") == "Texte [note : Note IBAN] suite"


def test_paragraph_state_is_group_scoped() -> None:
    # Le \pard de la note ne sort pas de son groupe : la cellule reste dans le tableau.
    # The note's \pard stays inside its group: the cell stays in the table.
    rtf = r"\pard\intbl A{\super\chftn}{\footnote\pard Note\par}\cell B\cell\row\pard Fin\par"
    assert body(rtf) == "| A [note : Note] | B |\n| --- | --- |\n\nFin"


@pytest.mark.parametrize("rtf", [
    r"{\rtf1 abc}}}}}} reste",
    r"{\rtf1 " + "{" * 5000 + "texte",
    r"{\rtf1 tronqué \u",
    r"{\rtf1 tronqué \'",
    r"{\rtf1 \bin-5 x}",
    r"{\rtf1 \bin99999999999 x}",
    r"{\rtf1\ansicpg99999 \'e9}",
    r"{\rtf1 " + rtf_unicode(99999999) + r"? \uc99 x}",
    "{\\rtf1 fin \\",
])
def test_malformed_input_never_crashes(rtf: str) -> None:
    convert(rtf)


def test_nesting_limit() -> None:
    with pytest.raises(DocumentError, match="RTF"):
        convert(r"{\rtf1 " + "{" * 20_000)


def test_not_rtf() -> None:
    # L'extension seule ne suffit pas : pris pour du texte / extension alone is not enough: plain text.
    assert to_markdown(b"{\\rtX}", "a.rtf", LOCAL).kind == "txt"
    with pytest.raises(DocumentError, match="RTF"):
        rtf_to_markdown(b"pas du RTF", LOCAL, Report())


def test_large_document_is_linear() -> None:
    paragraph = r"\pard\plain Salari\'e9 Jean Dupont, NIR " + NIR + r" {\b gras} " + rtf_unicode(8364) + r"? fin\par"
    rtf = r"{\rtf1\ansi " + paragraph * 40_000 + "}"
    started = time.perf_counter()
    result = convert(rtf)
    elapsed = time.perf_counter() - started
    assert result.markdown.count(NIR) == 40_000
    assert elapsed < 10, f"{len(rtf) / elapsed / 1e6:.1f} Mo/s"
