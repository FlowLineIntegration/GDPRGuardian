"""Identité des clients du service public, pseudonyme en mémoire seulement / client identity, in-memory pseudonym.

Le service public n'a pas de clé : un client est reconnu à son adresse réseau, que Nginx pose dans un en-tête de
confiance (`GDPRGUARDIAN_CLIENT_IP_HEADER`, production : `X-GG-Client`, écrasé par Nginx quelle que soit la valeur
reçue). L'adresse devient aussitôt un pseudonyme : 8 premiers octets de HMAC-SHA256(secret, préfixe), secret de
32 octets tiré au démarrage, renouvelé toutes les 24 h (la génération précédente reste reconnue 10 min), jamais
écrit ni journalisé. Deux niveaux : IPv4 /32 et /24, IPv6 /64 et /48 (une IPv4 mappée compte comme IPv4). L'adresse
brute n'est ni gardée, ni journalisée, ni mise dans un datagramme, un message d'erreur ou une réponse ; l'en-tête est
retiré de la requête dès sa lecture. Une requête sans cet en-tête, l'en-tête étant configuré, vient du serveur
lui-même (sonde, protocole de mesure) : principal LOCAL. Si un jeton local est configuré
(`GDPRGUARDIAN_LOCAL_TOKEN_SHA256`, son empreinte seulement), elle doit en plus présenter ce jeton dans `X-GG-Local`
(fichier réservé à root sur l'hôte) : un travailleur compromis, qui joint le même socket, retombe sinon dans le seau
commun des adresses illisibles. L'en-tête `X-GG-Local` est lui aussi retiré dès sa lecture.

The public service has no key: a client is known by its network address, which Nginx puts in a trusted header
(production: `X-GG-Client`, overwritten by Nginx whatever the client sent). The address becomes a pseudonym at once:
the first 8 bytes of HMAC-SHA256(secret, prefix), with a 32-byte secret drawn at start-up, renewed every 24 h (the
previous generation is still recognised for 10 min), never written nor logged. Two tiers: IPv4 /32 and /24, IPv6 /64
and /48 (an IPv4-mapped address counts as IPv4). The raw address is never kept, logged, put in a datagram, an error
message or a response; the header is removed from the request as soon as it is read. A request without the header,
when the header is configured, comes from the server itself (probe, measurement protocol): the LOCAL principal. When
a local token is configured (its SHA-256 digest only), it must also present that token in `X-GG-Local` (a root-only
file on the host): a compromised worker, which reaches the same socket, otherwise lands in the shared bucket of
unreadable addresses. `X-GG-Local` is removed as soon as it is read, too.
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import os
import threading
import time
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .usage import PROTOCOL, PUBLIC

if TYPE_CHECKING:
    from .admission import Reservation
    from .limiter import Ticket

# Principal des requêtes du serveur lui-même (sans en-tête client) / requests from the server itself.
LOCAL = "local"
PSEUDONYM_BYTES = 8
SECRET_BYTES = 32
# Jeton des requêtes du serveur lui-même, si configuré / token of the server's own requests, when configured.
LOCAL_TOKEN_HEADER = b"x-gg-local"
_MAX_LOCAL_TOKEN_CHARS = 256
_MAX_ADDRESS_CHARS = 64          # forme textuelle la plus longue d'une IPv6 avec zone, largement / with margin
_CLIENT_PREFIX = "c_"            # principal d'un client réseau / network client principal
_NETWORK_PREFIX = "p_"           # clé de quota d'un préfixe réseau / quota key of a network prefix
_TIER_CLIENT = b"client\0"
_TIER_PREFIX = b"prefix\0"
_TIER_PRINCIPAL = b"principal\0"
_UNKNOWN = b"unknown"            # adresse illisible : un seau commun / unreadable address: one shared bucket


@dataclass(frozen=True, slots=True)
class Client:
    """Qui envoie la requête, sans jamais l'adresse / who sends the request, never the address.

    `principal` : clé d'équité et de quota (« c_<16 hex> » pour un client réseau, « k_… » pour une clé d'API,
    LOCAL, « dev »…). `key`, `prefix` : clés du limiteur (niveau client et niveau préfixe), pseudonymes de 64 bits ;
    `previous_*` : les mêmes sous la génération précédente du secret, pendant le délai de grâce. `owner` : principal
    à clé auquel lier un envoi hors bande (None : la capacité seule donne accès). `local` : requête du serveur
    lui-même. `principal`: fairness and quota key. `key`, `prefix`: limiter keys (client and prefix tiers), 64-bit
    pseudonyms; `previous_*`: the same under the previous secret generation, during the grace period. `owner`: keyed
    principal an out-of-band upload is bound to (None: the capability alone grants access). `local`: a request from
    the server itself.
    """

    principal: str
    key: int | None = field(default=None, repr=False)
    prefix: int | None = field(default=None, repr=False)
    previous_key: int | None = field(default=None, repr=False)
    previous_prefix: int | None = field(default=None, repr=False)
    owner: str | None = None
    local: bool = False

    @property
    def src(self) -> str:
        """Provenance pour le compteur d'usage / provenance for the usage counter."""
        return PROTOCOL if self.local else PUBLIC

    @property
    def prefix_key(self) -> str | None:
        """Clé de quota du préfixe réseau (/24, /48), None hors réseau / quota key of the network prefix."""
        return None if self.prefix is None else f"{_NETWORK_PREFIX}{self.prefix:016x}"

    @property
    def budget_key(self) -> str:
        """Clé d'équité du budget mémoire : le préfixe s'il existe (une rotation de /64 n'y change rien), sinon le
        principal. Fairness key of the memory budget: the prefix when there is one (rotating /64s changes nothing),
        else the principal."""
        return self.prefix_key or self.principal


LOCAL_CLIENT = Client(LOCAL, local=True)


def address_tiers(value: str) -> tuple[bytes, bytes] | None:
    """Préfixes /32 et /24 (IPv4) ou /64 et /48 (IPv6) d'une adresse, None si illisible.

    /32 and /24 (IPv4) or /64 and /48 (IPv6) prefixes of an address, None when unreadable. L'erreur d'analyse cite
    la valeur reçue : elle n'est ni gardée ni chaînée / the parse error quotes the input: neither kept nor chained.
    """
    if not value or len(value) > _MAX_ADDRESS_CHARS:
        return None
    try:
        address = ipaddress.ip_address(value.strip())
    except ValueError:
        return None
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        address = address.ipv4_mapped
    packed = address.packed
    if address.version == 4:
        return b"4/32:" + packed, b"4/24:" + packed[:3]
    return b"6/64:" + packed[:8], b"6/48:" + packed[:6]


class Pseudonymizer:
    """HMAC-SHA256 tronqué à 64 bits, secret en mémoire renouvelé / truncated HMAC-SHA256, rotating in-memory secret.

    Le secret n'est ni écrit, ni journalisé, ni transmis aux travailleurs (processus neufs, sans ce module chargé
    dans leur zygote d'origine) ; il est remplacé toutes les `rotate_s` secondes, l'ancien restant reconnu
    `grace_s` secondes pour que l'état d'un client survive à la bascule. The secret is never written, logged nor
    passed to workers; it is replaced every `rotate_s` seconds, the old one still recognised for `grace_s` seconds
    so a client's state survives the switch.
    """

    __slots__ = ("_clock", "_grace", "_lock", "_previous", "_previous_until", "_rotate", "_secret", "_since")

    def __init__(self, *, rotate_s: float = 86_400.0, grace_s: float = 600.0,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._rotate = rotate_s
        self._grace = grace_s
        self._lock = threading.Lock()
        self._secret = os.urandom(SECRET_BYTES)
        self._since = clock()
        self._previous: bytes | None = None
        self._previous_until = 0.0

    def _secrets(self) -> tuple[bytes, bytes | None]:
        now = self._clock()
        with self._lock:
            if now - self._since >= self._rotate:
                self._previous, self._previous_until = self._secret, now + self._grace
                self._secret, self._since = os.urandom(SECRET_BYTES), now
            if self._previous is not None and now >= self._previous_until:
                self._previous = None
            return self._secret, self._previous

    def derive(self, *materials: bytes) -> list[tuple[int, int | None]]:
        """Pseudonymes (génération actuelle, précédente ou None) de chaque matériau / pseudonyms of each material."""
        current, previous = self._secrets()
        return [(_mac(current, material), None if previous is None else _mac(previous, material))
                for material in materials]


def _mac(secret: bytes, material: bytes) -> int:
    digest = hmac.new(secret, material, hashlib.sha256).digest()
    return int.from_bytes(digest[:PSEUDONYM_BYTES], "big")


class ClientIdentifier:
    """Construit le `Client` d'une requête / builds a request's `Client`.

    `header` : nom de l'en-tête de confiance (minuscules), ou None : l'adresse du pair TCP sert alors (jamais un
    en-tête que le client pourrait écrire). `local_token_sha256` : empreinte du jeton exigé des requêtes du serveur
    lui-même (sans en-tête d'adresse), None : aucun jeton exigé. `header`: trusted header name, or None: the TCP peer
    address is used (never a header the client could write). `local_token_sha256`: digest of the token required from
    the server's own requests (without the address header), None: no token required.
    """

    __slots__ = ("_header", "_local_digest", "pseudonymizer")

    def __init__(self, header: str | None, pseudonymizer: Pseudonymizer, *,
                 local_token_sha256: str | None = None) -> None:
        self._header = header.lower().encode("latin-1") if header else None
        self._local_digest = bytes.fromhex(local_token_sha256) if local_token_sha256 else None
        self.pseudonymizer = pseudonymizer

    @property
    def header(self) -> bytes | None:
        return self._header

    def network(self, headers: list[tuple[bytes, bytes]], peer: object) -> tuple[Client, list[tuple[bytes, bytes]]]:
        """Client réseau et en-têtes sans l'en-tête d'adresse ni le jeton local / network client and headers
        without the address header nor the local token.

        En-tête configuré et absent : LOCAL (avec le jeton, s'il est exigé ; sinon seau commun). Plusieurs valeurs
        (impossible derrière Nginx) : illisible, seau commun. Header configured but absent: LOCAL (with the token,
        when required; else the shared bucket). Several values (impossible behind Nginx): unreadable, shared bucket.
        """
        tokens = [value for name, value in headers if name == LOCAL_TOKEN_HEADER]
        if tokens:
            headers = [item for item in headers if item[0] != LOCAL_TOKEN_HEADER]
        if self._header is not None:
            values = [value for name, value in headers if name == self._header]
            kept = [item for item in headers if item[0] != self._header]
            if not values:
                return (LOCAL_CLIENT if self._local(tokens) else self._from_address("")), kept
            raw = values[0].decode("latin-1") if len(values) == 1 else ""
            return self._from_address(raw), kept
        host = peer[0] if isinstance(peer, (tuple, list)) and peer else None
        return self._from_address(host if isinstance(host, str) else ""), headers

    def _local(self, tokens: list[bytes]) -> bool:
        """Requête sans en-tête d'adresse : du serveur lui-même ? / a request without the address header: local?"""
        if self._local_digest is None:
            return True
        if len(tokens) != 1 or len(tokens[0]) > _MAX_LOCAL_TOKEN_CHARS:
            return False
        return hmac.compare_digest(hashlib.sha256(tokens[0].strip()).digest(), self._local_digest)

    def _from_address(self, raw: str) -> Client:
        tiers = address_tiers(raw)
        if tiers is None:
            tiers = (b"x/" + _UNKNOWN, b"x/" + _UNKNOWN)
        (key, previous_key), (prefix, previous_prefix) = self.pseudonymizer.derive(_TIER_CLIENT + tiers[0],
                                                                                   _TIER_PREFIX + tiers[1])
        return Client(f"{_CLIENT_PREFIX}{key:016x}", key, prefix, previous_key, previous_prefix)

    def principal(self, principal: str, *, owner: str | None = None, local: bool = False) -> Client:
        """Client identifié par un principal (clé d'API, mode local) : un seul niveau / one tier only."""
        [(key, previous_key)] = self.pseudonymizer.derive(_TIER_PRINCIPAL + principal.encode())
        return Client(principal, key, None, previous_key, None, owner=owner, local=local)


@dataclass(slots=True)
class RequestContext:
    """Contexte d'une requête HTTP, posé par la porte d'entrée / HTTP request context, set by the gate.

    `ticket` : réservation du limiteur pour une requête à contenu (None sinon). `reservation` : octets du budget
    mémoire tenus par la requête (corps, puis sortie du travailleur), posée par l'admission. `ticket`: limiter
    reservation for a content request (None otherwise). `reservation`: memory-budget bytes held by the request (body,
    then the worker's output), set by the admission.
    """

    client: Client
    ticket: Ticket | None = None
    reservation: Reservation | None = None


# Contexte de la requête en cours, hérité par les tâches qu'elle lance (outils MCP compris).
# Current request context, inherited by the tasks it starts (MCP tools included).
REQUEST: ContextVar[RequestContext | None] = ContextVar("gdprguardian_request", default=None)


def current_client() -> Client | None:
    context = REQUEST.get()
    return None if context is None else context.client


__all__ = ["LOCAL", "LOCAL_CLIENT", "LOCAL_TOKEN_HEADER", "REQUEST", "Client", "ClientIdentifier", "Pseudonymizer",
           "RequestContext", "address_tiers", "current_client"]
