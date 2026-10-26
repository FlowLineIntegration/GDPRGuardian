"""Convertisseur PDF (pypdfium2 + pypdf) / PDF converter."""

from __future__ import annotations

import dataclasses

import pytest
from convert_samples import (
    AUTHOR,
    EMAIL,
    IBAN,
    NIR,
    PHONE_INTL,
    contract_pdf,
    encrypt_pdf,
    line,
    make_pdf,
)

from gdprguardian.convert import to_markdown
from gdprguardian.convert._pdf import SCANNED_PLACEHOLDER
from gdprguardian.documents import DocumentError, DocumentOptions, DocumentTooLargeError, EncryptedDocumentError

LOCAL = DocumentOptions(sandbox=False)


@pytest.fixture(scope="module")
def contract() -> str:
    return to_markdown(contract_pdf(), "contrat.pdf", LOCAL).markdown


def test_headings_come_from_glyph_size(contract: str) -> None:
    assert "# Contrat de travail" in contract.splitlines()
    assert "## Article 1 - Parties" in contract.splitlines()
    assert "## Article 2 - Contact" in contract.splitlines()


def test_wrapped_lines_are_rejoined_so_identifiers_stay_whole(contract: str) -> None:
    assert IBAN in contract  # coupé entre deux lignes dans le PDF / split across two lines in the PDF
    assert NIR in contract
    assert "et la société ACME" in contract


def test_short_lines_keep_their_line_breaks(contract: str) -> None:
    assert "Adresse : 12 rue de la Paix\n75002 Paris" in contract


def test_matrix_scaled_text_is_body_text(contract: str) -> None:
    # `/F1 1 Tf` avec une matrice x10 : taille réelle 10 pt, pas un titre / real size 10 pt, not a heading.
    assert "\nTexte à l'échelle via une matrice de texte." in contract
    assert "# Texte à l'échelle" not in contract


def test_page_markers_and_scanned_page() -> None:
    result = to_markdown(contract_pdf(), "c.pdf", LOCAL)
    assert result.pages == 2
    assert result.markdown.startswith("<!-- page 1 -->")
    assert f"<!-- page 2 -->\n\n{SCANNED_PLACEHOLDER}" in result.markdown
    assert result.dropped["scanned_pages"] == 1
    assert any("numérisée" in warning for warning in result.warnings)
    assert not any("OCR demandé" in warning for warning in result.warnings)
    with_ocr = to_markdown(contract_pdf(), "c.pdf", dataclasses.replace(LOCAL, ocr=True))
    assert any("OCR demandé" in warning for warning in with_ocr.warnings)


def test_form_fields_are_listed(contract: str) -> None:
    assert "## Champs de formulaire\n\n- Nom : Jean Dupont\n- NIR : " + NIR in contract


def test_free_text_annotations_are_content_and_notes_are_comments() -> None:
    hidden = to_markdown(contract_pdf(), "c.pdf", LOCAL)
    assert "Signé : Jean Dupont" in hidden.markdown  # texte visible ajouté / visible added text
    assert PHONE_INTL not in hidden.markdown
    assert hidden.dropped["comments"] == 1
    shown = to_markdown(contract_pdf(), "c.pdf", dataclasses.replace(LOCAL, include_comments=True))
    assert "## Commentaires\n\n- page 1 : Rappeler au " + PHONE_INTL in shown.markdown
    assert "comments" not in shown.dropped


def test_metadata_and_annotation_authors_never_output() -> None:
    result = to_markdown(contract_pdf(), "c.pdf", dataclasses.replace(LOCAL, include_comments=True))
    assert AUTHOR not in result.markdown
    assert result.dropped["metadata"] == 2


def test_attachments_are_listed_by_number_and_extension_only() -> None:
    result = to_markdown(contract_pdf(), "c.pdf", LOCAL)
    assert "## Pièces jointes\n\n- Pièce jointe 1 (pdf)" in result.markdown
    assert "bulletin-dupont" not in result.markdown and "fake" not in result.markdown
    assert result.dropped["attachments"] == 1


def test_dehyphenation_and_bullets() -> None:
    lines = [line("Le texte est anony-", 700), line("misation complète et Jean-", 688),
             line("Pierre signe ensuite le document en bas de la page.", 676),
             line("\N{BULLET} Premier point", 640), line("\N{BULLET} Second point", 628)]
    markdown = to_markdown(make_pdf([lines]), "a.pdf", LOCAL).markdown
    assert "anonymisation complète" in markdown
    assert "Jean-Pierre" in markdown
    assert "- Premier point\n\n- Second point" in markdown


def test_scaled_heading_is_detected() -> None:
    pages = [[line("Titre par matrice", 700, scale=24), line("Corps de texte ordinaire.", 660),
              line("Encore du corps de texte ordinaire.", 648)]]
    assert "# Titre par matrice" in to_markdown(make_pdf(pages), "a.pdf", LOCAL).markdown


def test_unicode_text_is_preserved() -> None:
    pages = [[line("Élodie Gérard, née à Saint-Étienne, œuvre à 100 €.", 700)]]
    markdown = to_markdown(make_pdf(pages), "a.pdf", LOCAL).markdown
    assert "Élodie Gérard, née à Saint-Étienne, œuvre à 100 €." in markdown


def test_user_password_pdf_is_rejected_as_encrypted() -> None:
    with pytest.raises(EncryptedDocumentError):
        to_markdown(encrypt_pdf(contract_pdf(), "secret"), "c.pdf", LOCAL)


def test_owner_only_encryption_still_converts() -> None:
    result = to_markdown(encrypt_pdf(contract_pdf(), ""), "c.pdf", LOCAL)
    assert EMAIL in result.markdown
    assert "- Nom : Jean Dupont" in result.markdown  # champs lus après déchiffrement vide / fields after empty pw


def test_page_limit() -> None:
    with pytest.raises(DocumentTooLargeError, match="pages"):
        to_markdown(contract_pdf(), "c.pdf", dataclasses.replace(LOCAL, max_pages=1))


@pytest.mark.parametrize("data", [b"%PDF-1.7\n1 0 obj garbage", b"%PDF-", contract_pdf()[:300]])
def test_damaged_pdf_is_a_safe_document_error(data: bytes) -> None:
    with pytest.raises(DocumentError) as error:
        to_markdown(data, "c.pdf", LOCAL)
    assert "PDF" in str(error.value)


def test_empty_pdf_page_has_no_text_warning() -> None:
    result = to_markdown(make_pdf([[]]), "vide.pdf", LOCAL)
    assert result.markdown == "<!-- page 1 -->"
    assert "scanned_pages" not in result.dropped
