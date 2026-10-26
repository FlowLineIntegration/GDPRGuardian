"""Compteur d'usage de la page publique : un datagramme par anonymisation, métadonnées seulement.

Usage counter for the public page: one datagram per anonymisation, metadata only.

Le processus d'accueil envoie, à la fin de chaque anonymisation réussie ou non, un datagramme JSON d'au plus
256 octets sur le socket Unix local nommé par `GDPRGUARDIAN_USAGE_SOCKET` :
``{"v":1,"kind":K,"fmt":F,"bytes":N,"ms":M,"ok":B,"src":S}``. K, F et S viennent d'ensembles fermés (S : « public »
pour le trafic normal, « protocol » pour les requêtes du serveur lui-même, sans en-tête d'adresse), N et M sont des
entiers bornés, B un booléen : aucun contenu, nom de fichier, adresse IP, clé, principal ni identifiant (d'envoi
ou autre) ne peut y figurer. Envoi sans attente : socket non bloquant, toute erreur (démon absent, file pleine,
droits) est ignorée, sans rien journaliser. Sans socket Unix en datagrammes (Windows), le compteur ne fait rien.

Seul le processus d'accueil compte, et le démon le vérifie. Sous Linux, son socket prend à la construction, avant
tout travailleur, le nom abstrait `gdprguardian-usage:<chemin du socket>` (`sender_name`) et le garde ; le démon
du site ignore tout datagramme venu d'un autre nom. Les travailleurs partagent l'utilisateur et le dossier du
socket, mais le noyau refuse un second détenteur du nom : un travailleur, même compromis par un document piégé,
ne peut ni compter de faux documents ni faire passer quoi que ce soit par les chiffres publiés.

The front process sends, at the end of each anonymisation, successful or not, a JSON datagram of at most
256 bytes to the local Unix socket named by `GDPRGUARDIAN_USAGE_SOCKET`. K and F come from closed sets, N and M
are bounded integers, B a boolean: no content, file name, IP address, key, principal nor identifier (upload or
other) can appear in it. Fire and forget: non-blocking socket, every error (daemon gone, full buffer,
permissions) is ignored and nothing is logged. Without Unix datagram sockets (Windows), a no-op.

Only the front process counts, and the daemon checks it. On Linux its socket takes, at construction and before
any worker exists, the abstract name `gdprguardian-usage:<socket path>` and keeps it; the site daemon ignores any
datagram from another name. Workers share the user and the socket's folder, but the kernel refuses a second
holder of the name: a worker, even one compromised by a booby-trapped document, can neither count fake
documents nor pass anything through the published figures.
"""

from __future__ import annotations

import json
import os
import socket
import sys
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from time import perf_counter

USAGE_VERSION = 1
MAX_DATAGRAM_BYTES = 256
# Chemin d'un socket Unix : 108 octets, zéro final compris / Unix socket path: 108 bytes, final NUL included.
MAX_SOCKET_PATH_BYTES = 107
# Bornes du démon (au-delà, datagramme refusé) : 256 Mio, une heure / the daemon's bounds: 256 MiB, one hour.
MAX_REPORTED_BYTES = 1 << 28
MAX_REPORTED_MS = 3_600_000
# Nom abstrait de l'expéditeur (Linux), comme `usage_sender_name` du démon / sender's abstract name (Linux).
SENDER_PREFIX = b"gdprguardian-usage:"
MAX_ABSTRACT_NAME_BYTES = 107

# Origine d'une anonymisation / where an anonymisation comes from.
TEXT = "text"            # POST /v1/anonymize/text et /v1/detect
FILE = "file"            # POST /v1/anonymize/file
UPLOAD = "upload"        # envoi hors bande REST / REST out-of-band upload (PUT /v1/uploads/{token})
MCP_TEXT = "mcp_text"    # outil MCP anonymize_text / MCP tool
MCP_FILE = "mcp_file"    # document reçu par MCP (create_upload puis PUT, ou anonymize_file en local)
KINDS = frozenset({TEXT, FILE, UPLOAD, MCP_TEXT, MCP_FILE})
# Provenance : trafic public, ou requêtes du serveur lui-même (protocole de mesure) / public or the server's own.
PUBLIC = "public"
PROTOCOL = "protocol"
SOURCES = frozenset({PUBLIC, PROTOCOL})

OTHER = "other"
FORMATS = frozenset({"text", "pdf", "docx", "doc", "xlsx", "xls", "pptx", "odt", "ods", "odp", "rtf", "eml", "msg",
                     "html", "csv", "tsv", "md", OTHER})
# Format détecté (convertisseurs, tableur) ou extension déclarée -> liste fermée ; inconnu : « other ».
# Detected kind (converters, spreadsheets) or declared extension -> closed list; unknown: "other".
_FORMAT_OF = {
    **{name: name for name in FORMATS},
    "txt": "text", "odf-xml": "odt", "xlsm": "xlsx", "xlsb": "xlsx",
    "htm": "html", "xhtml": "html", "shtml": "html", "mht": "eml", "mhtml": "eml",
    "markdown": "md", "mdown": "md", "mkd": "md",
}


def usage_format(name: str | None) -> str:
    """Format de la liste fermée pour un format détecté ou une extension / closed-list format of a kind or suffix."""
    if not name:
        return OTHER
    return _FORMAT_OF.get(name.lower().lstrip("."), OTHER)


def sender_name(path: str) -> bytes:
    """Nom abstrait que le démon attend de l'expéditeur : préfixe et chemin, 107 octets au plus.

    Abstract name the daemon expects from the sender: prefix and path, 107 bytes at most. Le service et le démon
    doivent voir le socket au même chemin / service and daemon must see the socket at the same path.
    """
    return (SENDER_PREFIX + os.fsencode(path))[:MAX_ABSTRACT_NAME_BYTES]


def encode_usage(kind: str, fmt: str, size: int, ms: float, ok: bool, src: str = PUBLIC) -> bytes | None:
    """Datagramme du contrat, construit de valeurs fermées et bornées ; None pour une origine inconnue.

    The contract's datagram, built from closed, bounded values only; None for an unknown origin. Provenance hors
    liste : « public » / unknown provenance: "public".
    """
    if kind not in KINDS:
        return None
    datagram = json.dumps({"v": USAGE_VERSION, "kind": kind, "fmt": fmt if fmt in FORMATS else OTHER,
                           "bytes": min(max(0, int(size)), MAX_REPORTED_BYTES),
                           "ms": min(max(0, round(ms)), MAX_REPORTED_MS), "ok": ok is True,
                           "src": src if src in SOURCES else PUBLIC},
                          separators=(",", ":")).encode("ascii")
    return datagram if len(datagram) <= MAX_DATAGRAM_BYTES else None


class Measure:
    """Une anonymisation en cours : son format et son issue, posés par l'appelant / one anonymisation in flight."""

    __slots__ = ("fmt", "ok")

    def __init__(self, fmt: str) -> None:
        self.fmt = fmt
        self.ok = False


class UsageReporter:
    """Envoie les datagrammes d'usage ; sans chemin, ou sans socket Unix en datagrammes, ne fait rien.

    Sends the usage datagrams; without a path, or without Unix datagram sockets, does nothing. Le socket est
    ouvert, et sous Linux lié à son nom abstrait, dès la construction (dans le processus d'accueil, avant tout
    travailleur) ; jamais hérité (non héritable, et le zygote naît d'un interpréteur neuf), il ne vit que dans ce
    processus. The socket is opened, and on Linux bound to its abstract name, at construction (in the front
    process, before any worker); never inherited, it lives in this process only.
    """

    __slots__ = ("_address", "_sender", "_socket")

    def __init__(self, path: str | None) -> None:
        # Windows : pas de AF_UNIX dans le module socket, donc rien à envoyer / no AF_UNIX, nothing to send.
        self._address = path if path and hasattr(socket, "AF_UNIX") else None
        # Espace de noms abstrait : Linux seulement / abstract namespace: Linux only.
        self._sender = (b"\0" + sender_name(path) if self._address is not None and path
                        and sys.platform.startswith("linux") else None)
        self._socket: socket.socket | None = None
        if self._address is not None:
            with suppress(OSError):  # nom déjà pris ou socket refusé : réessayé au premier envoi / retried
                self._open()

    @property
    def enabled(self) -> bool:
        return self._address is not None

    @property
    def sender(self) -> bytes | None:
        """Adresse abstraite tenue (octet nul compris), None si aucune / abstract address held, if any."""
        return self._sender if self._socket is not None else None

    def report(self, kind: str, fmt: str, size: int, ms: float, ok: bool, src: str = PUBLIC) -> None:
        """Un datagramme, sans attendre ni lever / one datagram, never waits nor raises."""
        if self._address is None:
            return
        datagram = encode_usage(kind, fmt, size, ms, ok, src)
        if datagram is None:
            return
        try:
            sock = self._socket or self._open()
            sock.sendto(datagram, self._address)
        except OSError:
            pass  # démon absent, file pleine, droits, nom pris : statistique perdue / stat lost

    @contextmanager
    def measure(self, kind: str, size: int, fmt: str, src: str = PUBLIC) -> Iterator[Measure]:
        """Mesure le bloc et signale son issue, exception ou annulation comprise (ok false).

        Times the block and reports its outcome, exception or cancellation included (ok false).
        """
        started = perf_counter()
        record = Measure(fmt)
        try:
            yield record
        finally:
            self.report(kind, record.fmt, size, (perf_counter() - started) * 1000, record.ok, src)

    def close(self) -> None:
        """Ferme le socket et rend son nom (à l'arrêt, travailleurs déjà arrêtés) ; le prochain envoi en rouvre un.

        Closes the socket and releases its name (at shutdown, workers already stopped); the next send reopens one.
        """
        sock, self._socket = self._socket, None
        if sock is not None:
            sock.close()

    def _open(self) -> socket.socket:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        try:
            if self._sender is not None:
                sock.bind(self._sender)
            sock.setblocking(False)
        except OSError:
            sock.close()
            raise
        self._socket = sock
        return sock


__all__ = ["FILE", "FORMATS", "KINDS", "MAX_DATAGRAM_BYTES", "MAX_REPORTED_BYTES", "MAX_REPORTED_MS",
           "MAX_SOCKET_PATH_BYTES", "MCP_FILE", "MCP_TEXT", "PROTOCOL", "PUBLIC", "SOURCES", "TEXT", "UPLOAD",
           "Measure", "UsageReporter", "encode_usage", "sender_name", "usage_format"]
