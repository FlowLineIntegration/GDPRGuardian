"""Client HTTP du service par son socket Unix, jeton local compris / HTTP client over the service's Unix socket.

Une requête arrivée sur le socket SANS en-tête d'adresse (`X-GG-Client`) et AVEC le jeton local (`X-GG-Local`, lu
dans /etc/gdprguardian/local-header, fichier root 0600) est le principal LOCAL : hors budgets par client, deux
traitements à la fois au plus, jamais la place réservée aux petites requêtes, comptée « protocol » dans les
statistiques publiques. Le jeton n'est jamais affiché, journalisé ni écrit ; il ne vit qu'en mémoire.
A request reaching the socket WITHOUT the address header and WITH the local token is the LOCAL principal: outside
per-client budgets, two jobs at most, never the small-request slot, counted as "protocol" in the public statistics.
The token is never printed, logged or written; it lives in memory only.

Reprises : 429 et 503 attendent `Retry-After` (+ 0 à 20 % de gigue) ; au-delà de `max_doc_wait_s` d'attente pour un
même document, `ServiceSaturated` met la campagne en pause (une surcharge n'est jamais comptée comme une fuite) ;
408 et 5xx sont retentés trois fois ; un service injoignable est réessayé jusqu'à `down_s` secondes, puis
`ServiceDown` met la campagne en pause. Chaque panne de connexion appelle `on_connection_error` : la campagne
revérifie alors le moteur (redémarrage possible). Retries: 429/503 wait `Retry-After` (+0-20% jitter); past
`max_doc_wait_s` of waiting for one document, `ServiceSaturated` pauses the campaign (an overload never counts as a
leak); 408 and 5xx are retried three times; an unreachable service is retried for up to `down_s` seconds, then
`ServiceDown` pauses the campaign. Every connection failure calls `on_connection_error`: the campaign then checks the
engine again (the service may have restarted).
"""

from __future__ import annotations

import http.client
import json
import random
import re
import socket
import threading
import time
from collections import Counter
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, BinaryIO, Protocol

LOCAL_HEADER_NAME = "X-GG-Local"
_HEADER_LINE_RE = re.compile(r"^\s*([A-Za-z0-9-]+)\s*:\s*([\x21-\x7e]{16,256})\s*$")


class ServiceDown(RuntimeError):
    """Service injoignable trop longtemps : la campagne se met en pause / service unreachable for too long."""


class ServiceSaturated(ServiceDown):
    """429/503 plus longtemps que `max_doc_wait_s` pour un document : pause, jamais une fuite / pause, never a leak."""


class DocumentRefused(RuntimeError):
    """Le service n'a pas rendu ce document (code HTTP seulement) / the service did not return this document."""

    def __init__(self, kind: str) -> None:
        super().__init__(kind)
        self.kind = kind


def parse_local_header(raw: bytes | str) -> tuple[str, str]:
    """« X-GG-Local: <jeton> » -> (nom, jeton) ; message d'erreur sans le jeton / error message never shows it."""
    text = raw.decode("ascii", "replace") if isinstance(raw, bytes) else raw
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) != 1:
        raise ValueError("fichier d'en-tête local : une ligne attendue / local header file: one line expected")
    m = _HEADER_LINE_RE.match(lines[0])
    if m is None or m.group(1).lower() != LOCAL_HEADER_NAME.lower():
        raise ValueError("fichier d'en-tête local illisible / unreadable local header file (X-GG-Local: <token>)")
    return LOCAL_HEADER_NAME, m.group(2)


def read_local_header(stream: BinaryIO) -> tuple[str, str]:
    return parse_local_header(stream.read(4096))


class Transport(Protocol):
    def request(self, method: str, path: str, body: bytes | None = None) -> tuple[int, Mapping[str, str], bytes]:
        ...

    def close(self) -> None:
        ...


class _UnixConnection(http.client.HTTPConnection):
    def __init__(self, path: str, timeout: float) -> None:
        super().__init__("localhost", timeout=timeout)
        self._path = path

    def connect(self) -> None:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        try:
            sock.connect(self._path)
        except OSError:
            sock.close()
            raise
        self.sock = sock


class UnixTransport:
    """Une connexion gardée ouverte par fil / one kept-alive connection per thread."""

    def __init__(self, path: str, header: tuple[str, str] | None, timeout: float = 600.0) -> None:
        self._path = path
        self._header = header
        self._timeout = timeout
        self._conn: _UnixConnection | None = None

    def request(self, method: str, path: str, body: bytes | None = None) -> tuple[int, Mapping[str, str], bytes]:
        headers = {"Host": "localhost", "Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if self._header is not None:
            headers[self._header[0]] = self._header[1]
        for attempt in (0, 1):
            if self._conn is None:
                self._conn = _UnixConnection(self._path, self._timeout)
            try:
                self._conn.request(method, path, body=body, headers=headers)
                response = self._conn.getresponse()
                data = response.read()
                status = response.status
                reply = {k.lower(): v for k, v in response.getheaders()}
                if response.will_close:
                    self.close()
                return status, reply, data
            except (http.client.RemoteDisconnected, BrokenPipeError, ConnectionResetError):
                # Connexion gardée fermée par le serveur entre deux requêtes : une seule nouvelle tentative.
                # Kept-alive connection closed by the server between requests: one fresh attempt.
                self.close()
                if attempt:
                    raise
        raise ConnectionError("unreachable")

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None


@dataclass(slots=True)
class RetryPolicy:
    max_doc_wait_s: float = 1_800.0
    down_s: float = 600.0
    retries_5xx: int = 3
    sleep: Callable[[float], None] = time.sleep
    rng: random.Random = field(default_factory=lambda: random.Random(0x6767))


class Gate:
    """Requêtes en vol de la campagne ; réduite à 1 quand des visiteurs attendent / in-flight cap, 1 for visitors.

    Une requête prioritaire (le contrôle du moteur) passe avant les fils de travail, qui reprendraient sinon la place
    aussitôt libérée. A priority request (the engine check) goes before the worker threads, which would otherwise
    take every freed slot at once.
    """

    def __init__(self, limit: int) -> None:
        self.normal = limit
        self.limit = limit
        self.inflight = 0
        self.throttled_s = 0.0
        self._since: float | None = None
        self._priority_waiting = 0
        self._cond = threading.Condition()

    @contextmanager
    def slot(self, priority: bool = False) -> Iterator[Gate]:
        with self._cond:
            if priority:
                self._priority_waiting += 1
            try:
                while self.inflight >= self.limit or (not priority and self._priority_waiting):
                    self._cond.wait(1.0)
            finally:
                if priority:
                    self._priority_waiting -= 1
            self.inflight += 1
        try:
            yield self
        finally:
            with self._cond:
                self.inflight -= 1
                self._cond.notify_all()

    def __enter__(self) -> Gate:
        with self._cond:
            while self.inflight >= self.limit or self._priority_waiting:
                self._cond.wait(1.0)
            self.inflight += 1
        return self

    def __exit__(self, *_exc: object) -> None:
        with self._cond:
            self.inflight -= 1
            self._cond.notify_all()

    def set_throttle(self, on: bool) -> None:
        with self._cond:
            now = time.monotonic()
            if on and self._since is None:
                self._since = now
                self.limit = 1
            elif not on and self._since is not None:
                self.throttled_s += now - self._since
                self._since = None
                self.limit = self.normal
            self._cond.notify_all()


class ServiceClient:
    """Anonymise un texte par le service, avec reprises ; aucun contenu dans les erreurs / no content in errors."""

    def __init__(self, transport: Transport, gate: Gate | None = None, policy: RetryPolicy | None = None) -> None:
        self.transport = transport
        self.gate = gate
        self.policy = policy or RetryPolicy()
        self.retries: Counter[str] = Counter()
        # Appelé à chaque panne de connexion (le service a pu redémarrer) / called on every connection failure.
        self.on_connection_error: Callable[[str], None] | None = None
        self.priority = False  # passe avant les fils de travail au portillon / goes first at the gate

    def _call(self, method: str, path: str, body: bytes | None) -> tuple[int, Mapping[str, str], bytes]:
        """Appel avec reprise des pannes de connexion / call with connection-failure retries."""
        down_since: float | None = None
        delay = 1.0
        while True:
            try:
                if self.gate is not None and body is not None:
                    with self.gate.slot(self.priority):
                        return self.transport.request(method, path, body)
                return self.transport.request(method, path, body)
            except (OSError, http.client.HTTPException) as exc:
                self.transport.close()
                now = time.monotonic()
                down_since = down_since or now
                self.retries[f"connection:{type(exc).__name__}"] += 1
                if self.on_connection_error is not None:
                    self.on_connection_error("connection")
                if now - down_since > self.policy.down_s:
                    raise ServiceDown(type(exc).__name__) from None
                self.policy.sleep(delay)
                delay = min(delay * 2, 30.0)

    def anonymize(self, text: str, options: Mapping[str, Any]) -> str:
        body = json.dumps({"text": text, **options}, ensure_ascii=False).encode("utf-8")
        waited = 0.0
        failures = 0
        while True:
            status, headers, data = self._call("POST", "/v1/anonymize/text", body)
            if status == 200:
                try:
                    out = json.loads(data)["text"]
                except (ValueError, KeyError, TypeError):
                    raise DocumentRefused("bad_reply") from None
                if not isinstance(out, str):
                    raise DocumentRefused("bad_reply")
                return out
            if status in (429, 503):
                self.retries[f"http_{status}"] += 1
                wait = _retry_after(headers.get("retry-after"))
                wait *= 1 + 0.2 * self.policy.rng.random()
                if waited + wait > self.policy.max_doc_wait_s:
                    # Surcharge durable : pause de la campagne, le document sera renvoyé à la reprise.
                    # Lasting overload: the campaign pauses, the document is sent again on resume.
                    raise ServiceSaturated(f"http_{status}")
                self.policy.sleep(wait)
                waited += wait
                continue
            if status == 408 or status >= 500:
                failures += 1
                self.retries[f"http_{status}"] += 1
                if failures > self.policy.retries_5xx:
                    raise DocumentRefused(f"http_{status}")
                self.policy.sleep(min(2.0 ** failures, 30.0))
                continue
            raise DocumentRefused(f"http_{status}")

    def get_json(self, path: str) -> Any:
        status, _, data = self._call("GET", path, None)
        if status != 200:
            raise DocumentRefused(f"http_{status}")
        return json.loads(data)

    def get_status(self, path: str) -> int:
        """Code HTTP seulement / HTTP status only."""
        status, _, _ = self._call("GET", path, None)
        return status


def local_principal(client: ServiceClient) -> bool:
    """Le service voit-il nos requêtes comme LOCALES (jeton accepté) ? / does the service see us as LOCAL?

    `/health/deep` n'existe que pour le principal LOCAL : 200 = jeton accepté, 404 = requêtes vues comme celles d'un
    visiteur public (jeton absent ou faux). Autre code : sonde en échec. `/health/deep` exists for the LOCAL
    principal only: 200 = token accepted, 404 = requests seen as a public visitor's (token missing or wrong).
    """
    status = client.get_status("/health/deep")
    if status == 200:
        return True
    if status == 404:
        return False
    raise DocumentRefused(f"http_{status}")


# Compteurs du limiteur croissants pendant toute la vie du service : s'ils baissent, il a redémarré.
# Limiter counters that only grow during the service's lifetime: if they drop, it restarted.
_MONOTONIC_COUNTERS = ("accepted", "limited", "shed", "dry_run_limited", "errors")


def counters_total(status: Mapping[str, Any]) -> int | None:
    """Somme des compteurs croissants de /status, None s'ils manquent / sum of the growing /status counters."""
    counters = status.get("counters")
    if not isinstance(counters, Mapping):
        return None
    try:
        values = [int(counters[name]) for name in _MONOTONIC_COUNTERS if name in counters]
    except (TypeError, ValueError):
        return None
    return sum(values) if values else None


def _retry_after(value: str | None) -> float:
    try:
        seconds = float(value) if value is not None else 1.0
    except ValueError:
        seconds = 1.0
    return min(max(seconds, 0.5), 60.0)


def visitors_active(status: Mapping[str, Any], own_inflight: int) -> bool:
    """D'après /status : d'autres requêtes que les nôtres occupent ou attendent une place / others busy or waiting."""
    workers = status.get("workers") or {}
    try:
        busy = int(workers.get("busy", 0))
        waiting = int(workers.get("waiting", 0))
    except (TypeError, ValueError):
        return False
    return busy + waiting > own_inflight
