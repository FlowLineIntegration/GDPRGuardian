"""De bout en bout : aucun identifiant planté ne survit, quel que soit son canal.

End to end: no planted identifier survives, whatever channel it hides in (body, header, footer,
comment, note, form field, hidden slide, e-mail subject, file name...).
"""

from __future__ import annotations

import pytest
from convert_samples import (
    AUTHOR,
    HTML,
    IBAN,
    NIR,
    RTF,
    SECRETS,
    contract_pdf,
    make_docx,
    make_eml,
    make_msg,
    make_odp,
    make_odt,
    make_pptx,
)

from gdprguardian.documents import DocumentOptions, anonymize_document

# Tous les canaux ouverts : le pire cas pour une fuite / every channel open: worst case for a leak.
EVERYTHING = DocumentOptions(sandbox=False, include_comments=True, include_hidden=True, include_speaker_notes=True)
CASES = [
    ("pdf", contract_pdf), ("docx", make_docx), ("pptx", make_pptx), ("odt", make_odt), ("odp", make_odp),
    ("rtf", lambda: RTF.encode("latin-1")), ("html", lambda: HTML.encode()), ("eml", lambda: make_eml(html=True)),
    ("msg", lambda: make_msg(body=f"Corps : IBAN {IBAN}, NIR {NIR}")),
]


def leaks(markdown: str) -> list[str]:
    variants = {secret for secret in SECRETS} | {secret.replace(" ", "") for secret in SECRETS} | {AUTHOR}
    return sorted(variant for variant in variants if variant in markdown)


@pytest.mark.parametrize(("extension", "builder"), CASES, ids=[case[0] for case in CASES])
def test_planted_identifiers_never_reach_the_output(extension: str, builder, anonymizer_fr) -> None:
    filename = f"Classeurtemoin NIR {NIR}.{extension}"
    result = anonymize_document(builder(), filename, anonymizer_fr, EVERYTHING)
    assert leaks(result.markdown) == []
    # Le nom de fichier n'est jamais écrit, pas même réduit à son extension / the file name is never written.
    assert "Classeurtemoin" not in result.markdown and f"document.{extension}" not in result.markdown
    assert result.kind == extension
    assert result.report["irreversible"] is True
    assert result.report["total_replaced"] >= 3


@pytest.mark.parametrize(("extension", "builder"), CASES[:3], ids=[case[0] for case in CASES[:3]])
def test_default_options_through_the_sandbox(extension: str, builder, anonymizer_fr) -> None:
    result = anonymize_document(builder(), f"document.{extension}", anonymizer_fr, DocumentOptions(timeout_s=120))
    assert leaks(result.markdown) == []
    assert result.dropped == result.report["dropped"]


def test_same_identifier_keeps_its_placeholder_across_channels(anonymizer_fr) -> None:
    result = anonymize_document(make_docx(), "contrat.docx", anonymizer_fr, EVERYTHING)
    markdown = result.markdown
    # Le courriel de l'en-tête de la première page et de l'en-tête courant : une seule balise.
    # The e-mail of the first-page header and of the running header: one single placeholder.
    assert "Confidentiel - contact [EMAIL_1]" in markdown and "Première page - courriel [EMAIL_1]" in markdown


def test_default_anonymizer() -> None:
    result = anonymize_document(contract_pdf(), "contrat.pdf", options=DocumentOptions(sandbox=False))
    assert leaks(result.markdown) == []
