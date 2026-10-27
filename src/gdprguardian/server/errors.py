"""Erreurs du service : codes stables, messages fixes, sans contenu / service errors: stable codes, fixed messages.

Les messages viennent de cette table, jamais d'une exception tierce (qui pourrait citer le document).
Messages come from this table, never from a third-party exception (which could quote the document).
"""

from __future__ import annotations

import re

from ..convert._base import MEMORY_MESSAGE
from ..documents import (
    ConversionTimeoutError,
    DocumentError,
    DocumentTooLargeError,
    EncryptedDocumentError,
    MaliciousDocumentError,
    UnsupportedFormatError,
)

# Plafond de sortie dépassé, dans le travailleur (texte converti ou résultat) : message fixe, reconnu ici.
# Output cap exceeded, in the worker (converted text or result): fixed message, recognised here.
OUTPUT_TOO_LARGE = "Résultat trop volumineux / result too large"


class ServiceError(Exception):
    """Erreur affichable telle quelle au client / error safe to show to the client as is."""

    status = 500
    code = "internal_error"
    message = "Erreur interne / internal error"

    def __init__(self, message: str | None = None, *, code: str | None = None, retry_after: int | None = None) -> None:
        if message is not None:
            self.message = message
        if code is not None:
            self.code = code
        self.retry_after = retry_after
        super().__init__(self.code)

    def to_dict(self) -> dict[str, dict[str, str | int]]:
        # Attente en secondes dans le corps aussi (en plus de Retry-After), pour qui ne lit pas les en-têtes.
        # Wait in seconds in the body too (besides Retry-After), for clients that do not read headers.
        if self.retry_after:
            return {"error": {"code": self.code, "message": self.message, "retry_after_s": self.retry_after}}
        return {"error": {"code": self.code, "message": self.message}}


class InvalidRequest(ServiceError):
    status = 422
    code = "invalid_request"
    message = "Requête invalide / invalid request"


class Unauthorized(ServiceError):
    status = 401
    code = "unauthorized"
    message = "Clé d'API absente ou invalide / missing or invalid API key"


class CrossSiteRefused(ServiceError):
    """Requête envoyée par le navigateur depuis une autre page (Sec-Fetch-Site) : le service n'est pas une ressource
    que d'autres sites peuvent faire consommer à leurs visiteurs. A request a browser sent from another page: other
    sites may not make their visitors use the service."""

    status = 403
    code = "cross_site_request"
    message = "Requête inter-sites refusée / cross-site request refused"


class NotFound(ServiceError):
    """Faux, expiré, déjà utilisé ou lu, d'une autre clé : toujours cette réponse / always this same answer."""

    status = 404
    code = "not_found"
    message = "Introuvable ou expiré / not found or expired"


class UploadTimeout(ServiceError):
    status = 408
    code = "upload_timeout"
    message = ("Envoi trop lent, interrompu : renvoyez-le ; avec une URL d'envoi, demandez-en une nouvelle "
               "(create_upload ou POST /v1/uploads), elle ne sert qu'une fois / upload too slow, aborted: send it "
               "again; with an upload URL, request a new one (create_upload or POST /v1/uploads), it works only once")


# Envoi perdu en route (client parti) / upload lost on the way (client gone).
UPLOAD_INTERRUPTED_MESSAGE = ("Envoi interrompu : demandez une nouvelle URL d'envoi (create_upload ou POST "
                              "/v1/uploads), elle ne sert qu'une fois / upload interrupted: request a new upload URL "
                              "(create_upload or POST /v1/uploads), it works only once")


class PayloadTooLarge(ServiceError):
    status = 413
    code = "payload_too_large"
    message = "Contenu trop volumineux / payload too large"


class UnsupportedFormat(ServiceError):
    status = 415
    code = "unsupported_format"
    message = "Format de document non pris en charge / unsupported document format"


class RateLimited(ServiceError):
    status = 429
    code = "rate_limited"
    message = "Trop de requêtes, réessayez après Retry-After / too many requests, retry after Retry-After"


class QuotaExceeded(ServiceError):
    status = 429
    code = "too_many_active_uploads"
    message = "Trop d'envois en cours : lisez ou laissez expirer les résultats / too many active uploads"


class ResultsQuotaExceeded(QuotaExceeded):
    """Résultats non lus d'un client (ou de son préfixe réseau) au-delà de sa part du dépôt / unread results of a
    client (or its network prefix) beyond its share of the store."""

    code = "too_many_unread_results"
    message = ("Résultats non lus trop volumineux : lisez-les, supprimez-les ou laissez-les expirer / unread results "
               "too large: read, delete or let them expire")


class ConverterUnavailable(ServiceError):
    status = 501
    code = "converter_unavailable"
    message = "Convertisseur indisponible pour ce format / converter unavailable for this format"


class ServiceBusy(ServiceError):
    status = 503
    code = "service_busy"
    message = "Capacité temporairement atteinte, réessayez / capacity temporarily reached, retry"


class DocumentRejected(ServiceError):
    status = 422
    code = "document_error"
    message = "Document illisible ou refusé / unreadable or rejected document"


class ProcessingTimeout(ServiceError):
    """Texte dont l'anonymisation dépasse l'échéance de la requête (pendant de `conversion_timeout`).

    Text whose anonymisation exceeds the request deadline (counterpart of `conversion_timeout`). Le résultat
    serait le même en réessayant : 422, pas 5xx / retrying would give the same outcome: 422, not 5xx.
    """

    status = 422
    code = "processing_timeout"
    message = "Anonymisation trop longue, texte refusé : le découper / anonymisation timed out, split the text"


class RulesTooCostly(ServiceError):
    """Travailleur arrêté pendant un texte traité avec des règles de l'organisation : sans convertisseur, la
    cause probable est le coût de ces règles (filet de sécurité derrière le budget de compilation).

    Worker stopped while processing a text with organisation rules: with no converter involved, the likely cause
    is the cost of those rules (safety net behind the compile budget). Même résultat en réessayant : 422, pas
    5xx / same outcome on retry: 422, not 5xx.
    """

    status = 422
    code = "rules_too_costly"
    message = ("Traitement interrompu : règles de l'organisation trop coûteuses, à simplifier / processing stopped: "
               "organisation rules too costly, simplify them")


# Messages fixes par code de `DocumentError` / fixed messages per `DocumentError` code.
_DOCUMENT_ERRORS: tuple[tuple[type[DocumentError], type[ServiceError], str, str], ...] = (
    (DocumentTooLargeError, PayloadTooLarge, "document_too_large",
     "Document trop volumineux / document too large"),
    (UnsupportedFormatError, UnsupportedFormat, "unsupported_format", UnsupportedFormat.message),
    (EncryptedDocumentError, DocumentRejected, "encrypted_document",
     "Document chiffré ou protégé par mot de passe / encrypted or password-protected document"),
    (MaliciousDocumentError, DocumentRejected, "malicious_document",
     "Document refusé par les contrôles de sécurité / document rejected by safety checks"),
    (ConversionTimeoutError, DocumentRejected, "conversion_timeout",
     "Conversion trop longue, document refusé / conversion timed out"),
)

# Limites nommées dans un refus « trop volumineux » : chaque message vient de cette table, le travailleur ne donne que
# la nature (ensemble fermé) et le nombre. Limits named in a "too large" refusal: every message comes from this
# table; the worker only gives the kind (closed set) and the number.
_TOO_LARGE_KINDS = {
    "pages": ("Document trop long : {fr} pages au plus", "document too long: {en} pages at most"),
    "slides": ("Présentation trop longue : {fr} diapositives au plus", "presentation too long: {en} slides at most"),
    "table cells": ("Tableau trop grand : {fr} cellules au plus", "table too large: {en} cells at most"),
    "HTML tags": ("HTML trop complexe : {fr} balises au plus, ouvrantes et fermantes",
                  "HTML too complex: {en} tags at most, opening and closing"),
    "HTML nesting levels": ("HTML trop imbriqué : {fr} niveaux au plus", "HTML nested too deeply: {en} levels at most"),
    "Word paragraphs": ("Document Word trop long : {fr} paragraphes au plus, cellules de tableau comprises",
                        "Word document too long: {en} paragraphs at most, table cells included"),
    "Word elements": ("Document Word trop complexe : {fr} éléments au plus",
                      "Word document too complex: {en} elements at most"),
    "extracted text (characters)": ("Texte extrait trop long : {fr} caractères au plus",
                                    "extracted text too long: {en} characters at most"),
    "RTF body (bytes)": ("Corps RTF trop volumineux : {fr} octets au plus", "RTF body too large: {en} bytes at most"),
}
_TOO_LARGE_RE = re.compile(r"Document trop volumineux : [^/]{1,60} > (?P<n>\d{1,12}) / document too large: "
                           r"(?P<kind>[A-Za-z ()]{1,60}) > (?P=n)")
# Raisons fixes reprises mot pour mot (mémoire, classeurs) / fixed reasons passed on verbatim (memory, workbooks).
_FIXED_TOO_LARGE = frozenset({
    MEMORY_MESSAGE,
    "Partie de classeur trop volumineuse / workbook part too large",
    "Classeur trop volumineux une fois décompressé / workbook too large uncompressed",
    "Feuille trop étendue / sheet extent too large",
})


def _fr_number(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def _megabytes(size: int) -> tuple[str, str]:
    """Taille en Mo (Mio) si entière, sinon en octets / size in MB (MiB) when whole, else in bytes."""
    if size % 2**20 == 0:
        return f"{size >> 20} Mo", f"{size >> 20} MB"
    return f"{_fr_number(size)} octets", f"{size:,} bytes"


def file_too_large(max_bytes: int) -> PayloadTooLarge:
    """Fichier au-delà de la limite d'un envoi, limite nommée / file over the upload limit, the limit named."""
    fr, en = _megabytes(max_bytes)
    return PayloadTooLarge(f"Fichier trop volumineux : {fr} au plus / file too large: {en} at most")


def text_too_long(max_chars: int) -> PayloadTooLarge:
    """Texte au-delà de la limite d'un texte, limite nommée / text over the text limit, the limit named."""
    return PayloadTooLarge(f"Texte trop long : {_fr_number(max_chars)} caractères au plus / text too long: "
                           f"{max_chars:,} characters at most")


def result_too_long(max_chars: int) -> PayloadTooLarge:
    """Document dont le résultat (Markdown anonymisé) dépasse le plafond de sortie, ou dont le texte converti ne peut
    pas y tenir. Document whose result (anonymised Markdown) exceeds the output cap, or whose converted text cannot
    fit under it."""
    return PayloadTooLarge(f"Résultat trop long : {_fr_number(max_chars)} caractères au plus par document / result "
                           f"too long: {max_chars:,} characters at most per document", code="document_too_large")


def from_document_error(exc: DocumentError, *, max_output_chars: int | None = None) -> ServiceError:
    """Traduit une erreur de document en erreur de service, sans reprendre son message (tables fermées ci-dessus).

    Translates a document error into a service error without echoing its message (closed tables above). Un
    « trop volumineux » nomme la limite atteinte quand le travailleur en donne une connue / a "too large" names the
    limit reached when the worker reports a known one.
    """
    if isinstance(exc, DocumentTooLargeError):
        reason = str(exc)
        if reason == OUTPUT_TOO_LARGE and max_output_chars is not None:
            return result_too_long(max_output_chars)
        if reason in _FIXED_TOO_LARGE:
            return PayloadTooLarge(reason, code="document_too_large")
        match = _TOO_LARGE_RE.fullmatch(reason)
        if match is not None:
            limit, kind = int(match["n"]), match["kind"]
            if kind == "file (bytes)":
                return file_too_large(limit)
            if kind in _TOO_LARGE_KINDS:
                fr, en = _TOO_LARGE_KINDS[kind]
                message = f"{fr.format(fr=_fr_number(limit))} / {en.format(en=f'{limit:,}')}"
                return PayloadTooLarge(message, code="document_too_large")
    for exc_type, error_type, code, message in _DOCUMENT_ERRORS:
        if isinstance(exc, exc_type):
            return error_type(message, code=code)
    return DocumentRejected()
