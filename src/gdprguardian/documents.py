"""Façade documents : fichier -> Markdown anonymisé / documents facade: file -> anonymised Markdown.

Les convertisseurs (`gdprguardian.convert`) et le pipeline tableur (`gdprguardian.tabular`) implémentent
les fonctions déclarées ici ; ce module ne contient que les types partagés et l'aiguillage.
Converters and the spreadsheet pipeline implement the functions declared here; this module only
holds shared types and dispatch.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePath
from typing import Any

from .engine import Anonymizer, default_anonymizer

SPREADSHEET_EXTENSIONS = frozenset({".xlsx", ".xlsm", ".xls", ".xlsb", ".ods", ".csv", ".tsv"})


class DocumentError(Exception):
    """Erreur de document, message sûr à afficher (aucune donnée du document) / safe-to-display error."""

    code = "document_error"


class UnsupportedFormatError(DocumentError):
    code = "unsupported_format"


class DocumentTooLargeError(DocumentError):
    code = "document_too_large"


class EncryptedDocumentError(DocumentError):
    code = "encrypted_document"


class MaliciousDocumentError(DocumentError):
    code = "malicious_document"


class ConversionTimeoutError(DocumentError):
    code = "conversion_timeout"


@dataclass(slots=True, frozen=True)
class DocumentOptions:
    """Options de conversion ; les valeurs par défaut minimisent les données / defaults minimise data."""

    include_hidden: bool = False
    include_comments: bool = False
    include_speaker_notes: bool = True
    ocr: bool = False
    max_bytes: int = 50 * 1024 * 1024
    max_pages: int = 500
    max_cells: int = 2_000_000
    max_rows_per_sheet: int | None = None
    table_format: str = "markdown"
    timeout_s: float = 60.0
    sandbox: bool = True


@dataclass(slots=True)
class ConvertedDocument:
    """Sortie d'un convertisseur, AVANT anonymisation / converter output, BEFORE anonymisation."""

    markdown: str
    kind: str
    pages: int | None = None
    warnings: list[str] = field(default_factory=list)
    dropped: dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class DocumentResult:
    """Markdown anonymisé et rapport / anonymised Markdown and report."""

    markdown: str
    kind: str
    report: dict[str, Any]
    warnings: list[str] = field(default_factory=list)
    dropped: dict[str, int] = field(default_factory=dict)
    pages: int | None = None


def anonymize_document(
    data: bytes,
    filename: str,
    anonymizer: Anonymizer | None = None,
    options: DocumentOptions | None = None,
) -> DocumentResult:
    """Convertit puis anonymise un document ; le nom de fichier ne sert qu'à choisir le format.

    Converts then anonymises a document; the file name only selects the format and never reaches the output.
    """
    anonymizer = anonymizer or default_anonymizer()
    options = options or DocumentOptions()
    if len(data) > options.max_bytes:
        raise DocumentTooLargeError(f"Fichier trop volumineux / file too large (> {options.max_bytes} octets/bytes)")
    suffix = PurePath(filename).suffix.lower()
    if suffix in SPREADSHEET_EXTENSIONS:
        from .tabular import anonymize_workbook

        return anonymize_workbook(data, filename, anonymizer, options)
    from .convert import to_markdown

    converted = to_markdown(data, filename, options)
    # Le nom de fichier porte souvent des données personnelles (« CV_Jean_Dupont.pdf ») : il n'est jamais écrit
    # dans la sortie, pas même réduit à son extension. File names often carry personal data: never written to
    # the output, not even reduced to their extension.
    result = anonymizer.anonymize(converted.markdown)
    report = dict(result.report)
    report["dropped"] = converted.dropped
    return DocumentResult(result.text, converted.kind, report, converted.warnings, converted.dropped,
                          converted.pages)
