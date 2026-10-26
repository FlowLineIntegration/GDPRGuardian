"""Clés d'API, jetons d'envoi et capacités de résultat / API keys, upload tokens and result capabilities.

Les clés ne sont conservées que sous forme d'empreintes SHA-256, comparées en temps constant ; le principal est une
empreinte dérivée, stable et non réversible. Jeton d'envoi et identifiant de résultat sont des capacités de 256 bits,
remises au seul demandeur et gardées en empreinte. Keys are kept only as SHA-256 digests, compared in constant time;
the principal is a derived, stable, non-reversible digest. Upload tokens and result ids are 256-bit capabilities,
handed to the requester alone and stored as digests.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
from collections.abc import Iterable
from typing import Protocol

DEV_PRINCIPAL = "dev"
TOKEN_BYTES = 32        # 256 bits : jeton d'envoi à usage unique / single-use upload token
_MAX_HEADER_CHARS = 1024
_TOKEN_RE = re.compile(r"[A-Za-z0-9_-]{43}")
UPLOAD_ID_RE = re.compile(r"up_[A-Za-z0-9_-]{43}")
_RESULT_DERIVATION = b"gdprguardian/result-capability\0"
# Clé de dérivation de la capacité de lecture, tirée au démarrage du processus, jamais écrite : qui voit l'URL d'envoi
# (historique du shell, ligne de commande de curl) ne peut pas en déduire l'identifiant du résultat. Derivation key of
# the read capability, drawn when the process starts, never written: whoever sees the upload URL cannot derive the
# result id from it.
_RESULT_KEY = secrets.token_bytes(32)


class Authenticator(Protocol):
    def authenticate(self, authorization: str | None) -> str | None:
        """Principal authentifié, ou None / authenticated principal, or None."""


class ApiKeyAuthenticator:
    """Clés statiques en `Authorization: Bearer`, gardées en empreintes / static bearer keys, kept as digests.

    `keys` : clés en clair (intégration en code) ; `digests` : empreintes SHA-256 hexadécimales
    (`GDPRGUARDIAN_API_KEY_SHA256`). `keys`: plaintext keys (in-code embedding); `digests`: hex SHA-256 digests.
    """

    __slots__ = ("_entries",)

    def __init__(self, keys: Iterable[str] = (), digests: Iterable[str] = ()) -> None:
        raw = [hashlib.sha256(key.encode()).digest() for key in keys] + [bytes.fromhex(item) for item in digests]
        self._entries = tuple((digest, _principal_of(digest)) for digest in dict.fromkeys(raw))
        if not self._entries:
            raise ValueError("au moins une clé / at least one key")

    def authenticate(self, authorization: str | None) -> str | None:
        key = bearer_token(authorization)
        if key is None:
            return None
        digest = hashlib.sha256(key.encode()).digest()
        principal = None
        # Parcours complet, sans sortie anticipée / full scan, no early exit.
        for candidate, candidate_principal in self._entries:
            if hmac.compare_digest(digest, candidate):
                principal = candidate_principal
        return principal


class DevAuthenticator:
    """Mode local sans authentification (GDPRGUARDIAN_DEV_NO_AUTH=1) / local no-auth mode."""

    __slots__ = ()

    def authenticate(self, authorization: str | None) -> str | None:
        return DEV_PRINCIPAL


def bearer_token(authorization: str | None) -> str | None:
    if not authorization or len(authorization) > _MAX_HEADER_CHARS:
        return None
    scheme, _, token = authorization.partition(" ")
    token = token.strip()
    if scheme.lower() != "bearer" or not token or not token.isascii() or not token.isprintable():
        return None
    return token


def _principal_of(key_digest: bytes) -> str:
    # `person` : 16 octets au plus, sinon ValueError / BLAKE2b personalisation is at most 16 bytes.
    return "k_" + hashlib.blake2b(key_digest, digest_size=12, person=b"gdprguardian/pri").hexdigest()


# --- Jetons d'envoi / upload tokens -----------------------------------------------------------------


def issue_upload_token() -> tuple[str, bytes]:
    """(jeton en clair, empreinte à conserver) / (plain token, digest to keep)."""
    token = secrets.token_urlsafe(TOKEN_BYTES)
    return token, hashlib.sha256(token.encode("ascii")).digest()


def token_digest(token: str) -> bytes | None:
    """Empreinte d'un jeton bien formé, None sinon / digest of a well-formed token, else None."""
    if not _TOKEN_RE.fullmatch(token):
        return None
    return hashlib.sha256(token.encode("ascii")).digest()


def result_id(token: str) -> str:
    """Capacité de lecture du résultat, dérivée du jeton d'envoi par HMAC-SHA256 sous une clé en mémoire (256 bits).

    Result read capability, derived from the upload token by HMAC-SHA256 under an in-memory key (256 bits). Sans la
    clé, l'URL d'envoi ne donne pas le résultat. Le dépôt ne garde ni l'un ni l'autre, seulement leurs empreintes : la
    capacité est recalculée du jeton présenté pour le reçu du PUT, que seul le détenteur du jeton reçoit. Without the
    key, the upload URL does not give the result away. The store keeps neither, only their digests: the capability is
    recomputed from the presented token for the PUT receipt, which only the token holder receives.
    """
    digest = hmac.new(_RESULT_KEY, _RESULT_DERIVATION + token.encode("ascii"), hashlib.sha256).digest()
    return "up_" + base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def result_digest(upload_id: str) -> bytes | None:
    """Empreinte d'un identifiant de résultat bien formé, None sinon / digest of a well-formed result id, else None."""
    if not UPLOAD_ID_RE.fullmatch(upload_id):
        return None
    return hashlib.sha256(upload_id.encode("ascii")).digest()


def valid_upload_id(upload_id: str) -> bool:
    return UPLOAD_ID_RE.fullmatch(upload_id) is not None


def same_digest(a: bytes, b: bytes) -> bool:
    """Comparaison en temps constant / constant-time comparison."""
    return hmac.compare_digest(a, b)
