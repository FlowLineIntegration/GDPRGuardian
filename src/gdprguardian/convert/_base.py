"""Socle commun des convertisseurs / shared converter foundation.

Messages d'erreur sûrs (jamais de contenu ni de nom de fichier) et rapport des éléments écartés.
Safe error messages (never content nor file names) and the dropped-content report.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, TypeVar

from ..documents import (
    ConvertedDocument,
    DocumentError,
    DocumentOptions,
    DocumentTooLargeError,
    EncryptedDocumentError,
    MaliciousDocumentError,
    UnsupportedFormatError,
)

if TYPE_CHECKING:
    from ._archive import SafeArchive

T = TypeVar("T")

CRASH_MESSAGE = ("Le convertisseur s'est arrêté brutalement (document probablement malformé) / the converter "
                 "process crashed (document probably malformed)")
START_MESSAGE = "Impossible de démarrer le bac à sable de conversion / could not start the conversion sandbox"
FAILURE_MESSAGE = ("Échec de la conversion (document malformé ou non pris en charge) / conversion failed "
                   "(malformed or unsupported document)")
MEMORY_MESSAGE = "Mémoire insuffisante pour convertir ce document / conversion exceeded the memory limit"
NESTING_MESSAGE = "Structure du document trop imbriquée / document structure nested too deeply"

# Libellés lisibles des formats, pour les messages / readable format names, for messages.
FORMAT_NAMES = {
    "pdf": "PDF", "docx": "DOCX", "pptx": "PPTX", "odt": "ODT", "odp": "ODP", "odg": "ODG", "rtf": "RTF",
    "html": "HTML", "eml": "EML", "msg": "MSG", "txt": "texte", "md": "Markdown", "zip": "ZIP", "ole": "OLE",
}


@dataclass(slots=True)
class Source:
    """Document à convertir, format déjà identifié / document to convert, format already identified."""

    data: bytes
    kind: str
    archive: SafeArchive | None = None


@dataclass(slots=True)
class Report:
    """Avertissements et comptes d'éléments écartés (aucun contenu) / warnings and dropped counts (no content)."""

    warnings: list[str] = field(default_factory=list)
    dropped: dict[str, int] = field(default_factory=dict)

    def drop(self, key: str, count: int = 1) -> None:
        if count > 0:
            self.dropped[key] = self.dropped.get(key, 0) + count

    def warn(self, message: str) -> None:
        if message not in self.warnings:
            self.warnings.append(message)

    def document(self, markdown: str, kind: str, pages: int | None = None) -> ConvertedDocument:
        return ConvertedDocument(markdown, kind, pages, self.warnings, dict(sorted(self.dropped.items())))


def corrupt(kind: str) -> DocumentError:
    name = FORMAT_NAMES.get(kind, kind)
    return DocumentError(f"Document {name} illisible ou endommagé / unreadable or damaged {name} document")


def encrypted() -> EncryptedDocumentError:
    return EncryptedDocumentError("Document protégé par mot de passe ou chiffré / password-protected or encrypted "
                                  "document")


def malicious(reason_fr: str, reason_en: str) -> MaliciousDocumentError:
    return MaliciousDocumentError(f"Document refusé : {reason_fr} / document rejected: {reason_en}")


def too_large(what_fr: str, what_en: str, limit: int) -> DocumentTooLargeError:
    return DocumentTooLargeError(f"Document trop volumineux : {what_fr} > {limit} / document too large: "
                                 f"{what_en} > {limit}")


def unsupported(reason_fr: str, reason_en: str) -> UnsupportedFormatError:
    return UnsupportedFormatError(f"Format non pris en charge : {reason_fr} / unsupported format: {reason_en}")


def output_limit(options: DocumentOptions) -> int:
    """Plafond de caractères produits (bombe de décompression) / cap on produced characters (expansion bomb)."""
    return max(16 << 20, 4 * options.max_bytes)


def _failure(cls: type[DocumentError], message: str) -> DocumentError:
    error = cls(message)
    error.recycle = True  # type: ignore[attr-defined]  # état de l'analyseur incertain / parser state uncertain
    return error


def guarded(function: Callable[..., T], *args: Any) -> T:
    """Toute erreur imprévue devient une `DocumentError` sans contenu (le message d'origine peut en contenir).

    Any unexpected error becomes a content-free `DocumentError` (the original message may carry content).
    The original exception is not even kept as `__context__`: `from None` only hides it from tracebacks,
    while error reporters walking the chain could still read it.
    """
    try:
        return function(*args)
    except DocumentError as error:
        failure = error
    except MemoryError:
        failure = _failure(DocumentTooLargeError, MEMORY_MESSAGE)
    except RecursionError:
        failure = _failure(DocumentError, NESTING_MESSAGE)
    except Exception:
        failure = _failure(DocumentError, FAILURE_MESSAGE)
    # Hors du bloc except, chaîne coupée / outside the except block, chain cut.
    failure.__context__ = None
    raise failure from None


__all__ = ["CRASH_MESSAGE", "FAILURE_MESSAGE", "FORMAT_NAMES", "MEMORY_MESSAGE", "NESTING_MESSAGE", "START_MESSAGE",
           "Report", "Source", "corrupt", "encrypted", "guarded", "malicious", "output_limit", "too_large",
           "unsupported"]
