"""Convertisseur OpenDocument (defusedxml) / OpenDocument converter."""

from __future__ import annotations

import dataclasses

import pytest
from convert_samples import (
    _ODF_NS,
    AUTHOR,
    EMAIL,
    IBAN,
    NIR,
    ODT_BODY,
    PHONE,
    PHONE_INTL,
    make_odf,
    make_odp,
    make_odt,
    odf_content,
)

from gdprguardian.convert import to_markdown
from gdprguardian.documents import (
    DocumentOptions,
    DocumentTooLargeError,
    EncryptedDocumentError,
    UnsupportedFormatError,
)

LOCAL = DocumentOptions(sandbox=False)


def convert(data: bytes, name: str = "doc.odt", **options: object):
    return to_markdown(data, name, dataclasses.replace(LOCAL, **options))


def test_text_structure() -> None:
    markdown = convert(make_odt()).markdown
    assert markdown.startswith("# Contrat de travail\n\nSalarié : Jean  Dupont, NIR " + NIR + "[^1].")
    assert "- Premier point\n  - Sous-point" in markdown
    assert "[IMAGE: Photo badge]" in markdown


def test_repeated_cells_are_never_expanded() -> None:
    result = convert(make_odt())
    assert f"| Nom\\|Prénom | Courriel |\n| --- | --- |\n| Dupont | {EMAIL} |" in result.markdown
    assert len(result.markdown) < 2000  # 16384 colonnes x 1 million de lignes déclarées / declared, not expanded


def test_footnotes_headers_and_footers() -> None:
    markdown = convert(make_odt()).markdown
    assert markdown.endswith(f"[^1]: Note : IBAN {IBAN}")
    assert f"## En-têtes et pieds de page\n\n- En-tête : {EMAIL}\n- Pied : tél. {PHONE}" in markdown


def test_tracked_deletions_and_comments() -> None:
    default = convert(make_odt())
    assert "SUPPRIME-SECRET" not in default.markdown and default.dropped["tracked_deletions"] == 1
    assert PHONE_INTL not in default.markdown and default.dropped["comments"] == 1
    shown = convert(make_odt(), include_comments=True)
    assert "## Commentaires\n\n- Rappeler au " + PHONE_INTL in shown.markdown
    assert AUTHOR not in shown.markdown  # dc:creator, meta.xml, nom de cadre / frame name
    assert shown.dropped["metadata"] == 3


def test_presentation_slides_notes_and_hidden_pages() -> None:
    result = convert(make_odp(), "deck.odp")
    assert result.kind == "odp" and result.pages == 2
    assert "## Diapositive 1 : Bilan annuel\n\n- Contact " + PHONE in result.markdown
    assert "### Notes\n\nNotes ODP " + NIR in result.markdown
    assert "ODP-CACHE" not in result.markdown and result.dropped["hidden_slides"] == 1
    assert "Pied ODP " + EMAIL in result.markdown
    shown = convert(make_odp(), "deck.odp", include_hidden=True, include_speaker_notes=False)
    assert "## Diapositive 2 (masquée)" in shown.markdown and IBAN in shown.markdown
    assert NIR not in shown.markdown and shown.dropped["speaker_notes"] == 1


def test_flat_xml_document() -> None:
    flat = (f'<?xml version="1.0"?><office:document {_ODF_NS}><office:meta><dc:creator>{AUTHOR}</dc:creator>'
            f"</office:meta><office:body><office:text>{ODT_BODY}</office:text></office:body></office:document>")
    result = convert(flat.encode(), "doc.fodt")
    assert result.kind == "odt"
    assert NIR in result.markdown and AUTHOR not in result.markdown
    assert result.dropped["metadata"] == 1


def test_encrypted_odf_is_rejected() -> None:
    manifest = (b'<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0">'
                b'<manifest:file-entry manifest:full-path="content.xml"><manifest:encryption-data/>'
                b"</manifest:file-entry></manifest:manifest>")
    with pytest.raises(EncryptedDocumentError):
        convert(make_odf(b"\x00garbage", manifest=manifest))


def test_spreadsheet_inside_content_is_rejected() -> None:
    data = make_odf(odf_content("<table:table/>", "spreadsheet"))
    with pytest.raises(UnsupportedFormatError, match="tableur"):
        convert(data)


HIDDEN_STYLES = ('<style:style style:name="T1" style:family="text"><style:text-properties text:display="none"/>'
                 '</style:style><style:style style:name="P9" style:family="paragraph"><style:text-properties '
                 'text:display="none"/></style:style>')
HIDDEN_BODY = ('<text:p>Visible <text:span text:style-name="T1">PASSAGE-CACHE</text:span> suite '
               '<text:a xlink:href="mailto:jean@exemple.fr">écrire</text:a></text:p>'
               '<text:p text:style-name="P9">PARAGRAPHE-CACHE</text:p>'
               '<text:p><text:hidden-paragraph text:condition="ooow:1" text:is-hidden="true"/>CONDITION-CACHE</text:p>'
               '<text:section text:name="S1" text:display="none"><text:p>SECTION-CACHEE</text:p></text:section>'
               '<text:list><text:list-item><text:p text:style-name="P9">PUCE-CACHEE</text:p></text:list-item>'
               '<text:list-item><text:p>Puce visible</text:p></text:list-item></text:list>')


def test_hidden_text_sections_and_paragraphs_follow_include_hidden() -> None:
    data = make_odf(odf_content(HIDDEN_BODY, styles=HIDDEN_STYLES))
    default = convert(data)
    assert "Visible  suite écrire" in default.markdown and "- Puce visible" in default.markdown
    assert "CACHE" not in default.markdown and "jean@exemple.fr" not in default.markdown
    assert default.dropped["hidden_text"] == 1 and default.dropped["hidden_content"] == 4
    assert default.dropped["links"] == 1
    shown = convert(data, include_hidden=True).markdown
    for text in ("PASSAGE-CACHE", "PARAGRAPHE-CACHE", "CONDITION-CACHE", "SECTION-CACHEE", "PUCE-CACHEE"):
        assert text in shown


def test_cell_budget() -> None:
    rows = "".join("<table:table-row><table:table-cell><text:p>x</text:p></table:table-cell></table:table-row>"
                   for _ in range(20))
    with pytest.raises(DocumentTooLargeError):
        convert(make_odf(odf_content(f"<table:table>{rows}</table:table>")), max_cells=10)
