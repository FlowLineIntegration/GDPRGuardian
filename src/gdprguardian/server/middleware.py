"""Intergiciels ASGI purs : journal d'erreurs, en-têtes de sécurité, hôte, porte d'entrée, taille et durée des corps.

Pure ASGI middleware: error log, security headers, Host check, entry gate (cross-site refusal, authentication,
client identity, abuse limiter), body size and duration limits. Aucun journal d'accès : une requête n'est notée
qu'en DEBUG, ou en WARNING si le service répond 5xx, et seulement par son gabarit de route (jamais le chemin réel,
qui porte des jetons). No access log: a request is only noted at DEBUG, or WARNING when the service answers 5xx,
and only by its route template (never the actual path, which carries tokens).
"""

from __future__ import annotations

import ipaddress
import json
import logging
import re
from collections.abc import Callable, Iterable, Sequence
from fnmatch import fnmatchcase
from time import perf_counter

import anyio
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .clients import REQUEST, Client, ClientIdentifier, RequestContext
from .errors import (
    CrossSiteRefused,
    PayloadTooLarge,
    RateLimited,
    ServiceBusy,
    ServiceError,
    Unauthorized,
    UploadTimeout,
)
from .limiter import FILE, TEXT, Limiter
from .logs import log_event

PRINCIPAL_STATE_KEY = "gdprguardian_principal"
# Clé d'équité du budget mémoire (préfixe réseau ou principal) / fairness key of the memory budget.
BUDGET_STATE_KEY = "gdprguardian_budget_key"
WWW_AUTHENTICATE = 'Bearer realm="gdprguardian"'
# Principal de repli de l'admission (requête sans principal posé) / admission's fallback principal.
ANONYMOUS = "anonymous"
DEEP_HEALTH = "/health/deep"
_JSON = (b"content-type", b"application/json")
_STATIC_ROUTES = frozenset({"/health", DEEP_HEALTH, "/status", "/v1/packs", "/v1/anonymize/text",
                            "/v1/anonymize/file", "/v1/detect", "/v1/uploads"})
# Nature des requêtes à contenu, par gabarit et méthode : seau de coût, requêtes en vol, délestage. La création d'un
# envoi porte un petit corps JSON (comptée en vol : un corps lent tient de la mémoire).
# Content requests, by template and method: cost bucket, in-flight count, shedding. Creating an upload carries a
# small JSON body (counted in flight: a slow body holds memory).
_CONTENT = {("POST", "/v1/anonymize/text"): TEXT, ("POST", "/v1/detect"): TEXT, ("POST", "/v1/anonymize/file"): FILE,
            ("PUT", "/v1/uploads/{token}"): FILE, ("POST", "/mcp"): TEXT, ("POST", "/v1/uploads"): TEXT}
# Requêtes à contenu qui comptent aussi dans le seau bon marché (sans travailleur la plupart du temps).
# Content requests also counted in the cheap bucket (mostly no worker).
_CHEAP_CONTENT = frozenset({"/mcp", "/v1/uploads"})
# Délestage sur l'attente estimée reporté à la prise d'un travailleur (`Service._process`).
# Wait-based shedding deferred until a worker is taken.
_DEFERRED_SHED = frozenset({"/mcp", "/v1/uploads"})
# Sec-Fetch-Site admis : même origine (cockpit) ou navigation directe ; absent : client hors navigateur.
# Allowed Sec-Fetch-Site: same origin (cockpit) or direct navigation; absent: a non-browser client.
_FETCH_SITES = frozenset({"same-origin", "none"})
_DRAIN_S = 10.0          # lecture à vide d'un corps refusé, au plus / draining a refused body, at most
_LOOPBACK_NAMES = frozenset({"localhost", "127.0.0.1", "::1"})
_SECURITY_HEADERS = (
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"no-referrer"),
    (b"cache-control", b"no-store"),
    (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'"),
    (b"permissions-policy", b"camera=(), geolocation=(), microphone=()"),
    (b"cross-origin-resource-policy", b"same-origin"),
)


def route_template(path: str) -> str:
    """Gabarit de route, sans jeton ni identifiant / route template, without token or identifier."""
    if path in _STATIC_ROUTES:
        return path
    if path.startswith("/v1/uploads/"):
        return "/v1/uploads/{token}"
    if path.startswith("/v1/results/"):
        return "/v1/results/{upload_id}"
    if path == "/mcp" or path.startswith("/mcp/"):
        return "/mcp"
    return "other"


def _header(scope: Scope, name: bytes) -> str | None:
    for key, value in scope.get("headers", ()):
        if key == name:
            return value.decode("latin-1")
    return None


async def send_json(send: Send, status: int, payload: dict[str, object],
                    extra: Sequence[tuple[bytes, bytes]] = ()) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode()
    headers = [_JSON, (b"content-length", str(len(body)).encode()), *extra]
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body})


def _expects_continue(scope: Scope) -> bool:
    return any(key == b"expect" and value.lower() == b"100-continue" for key, value in scope.get("headers", ()))


# Identifiant JSON-RPC d'un message MCP : clé « id » hors chaîne (dans une chaîne JSON, un guillemet est échappé).
# JSON-RPC id of an MCP message: an "id" key outside any string (inside a JSON string a quote is escaped).
_JSONRPC_ID_RE = re.compile(rb'(?<!\\)"id"\s*:\s*(-?\d{1,18}|"(?:[^"\\]|\\.){0,128}")')
_PROBE_HEAD = 8 * 1024   # début du corps gardé pour l'id (SDK Python : id en tête) / body head kept for the id
_PROBE_TAIL = 512        # fin du corps gardée (SDK TypeScript : id à la fin) / body tail kept (id at the end)
# Erreur JSON-RPC « serveur » pour un refus temporaire ou de transport / JSON-RPC server error for these refusals.
JSONRPC_SERVER_ERROR = -32000


class JsonRpcIdProbe:
    """Garde le début et la fin d'un corps MCP, jamais le reste, pour retrouver l'id de la requête.

    Keeps the head and tail of an MCP body, never the rest, to find the request id. Rien n'est journalisé ni renvoyé
    hormis l'id lui-même / nothing is logged or echoed but the id itself.
    """

    __slots__ = ("head", "tail")

    def __init__(self) -> None:
        self.head = b""
        self.tail = b""

    def feed(self, chunk: bytes) -> None:
        if len(self.head) < _PROBE_HEAD:
            room = _PROBE_HEAD - len(self.head)
            self.head += chunk[:room]
        self.tail = (self.tail + chunk)[-_PROBE_TAIL:]

    def request_id(self) -> int | str | None:
        """Premier id du début (SDK Python), sinon dernier de la fin / first id of the head, else last of the tail."""
        match = _JSONRPC_ID_RE.search(self.head)
        if match is None:
            found = list(_JSONRPC_ID_RE.finditer(self.tail))
            match = found[-1] if found else None
        if match is None:
            return None
        try:
            value = json.loads(match.group(1))
        except ValueError:
            return None
        return value if isinstance(value, int | str) else None


def is_mcp_post(scope: Scope) -> bool:
    return scope.get("method") == "POST" and route_template(scope.get("path", "")) == "/mcp"


def jsonrpc_error_body(error: ServiceError, request_id: int | str) -> dict[str, object]:
    """Erreur JSON-RPC lisible par l'agent : code stable, message FR/EN, retry_after_s et statut HTTP d'origine.

    JSON-RPC error an agent can read: stable code, FR/EN message, retry_after_s and the original HTTP status. Un
    client MCP ne lit jamais le corps d'une réponse HTTP 4xx/5xx (« Server returned an error response ») : sur /mcp,
    le refus part donc en HTTP 200 avec cette erreur. An MCP client never reads the body of an HTTP 4xx/5xx, so on
    /mcp the refusal goes out as HTTP 200 carrying this error.
    """
    retry = error.retry_after
    hint = (f" Réessayez dans {retry} s, une requête à la fois / retry in {retry} s, one request at a time "
            f"(retry_after_s={retry})." if retry else "")
    if error.code in ("upload_timeout", "payload_too_large"):
        hint += " Texte long : utilisez create_upload / long text: use create_upload."
    data: dict[str, object] = {"code": error.code, "http_status": error.status}
    if retry:
        data["retry_after_s"] = retry
    return {"jsonrpc": "2.0", "id": request_id,
            "error": {"code": JSONRPC_SERVER_ERROR, "message": f"{error.code}: {error.message}{hint}", "data": data}}


async def send_refusal(scope: Scope, send: Send, error: ServiceError, extra: Sequence[tuple[bytes, bytes]],
                       probe: JsonRpcIdProbe | None = None) -> None:
    """Refus HTTP (statut et en-têtes gardés), ou erreur JSON-RPC en HTTP 200 sur /mcp quand l'id est connu.

    HTTP refusal (status and headers kept), or a JSON-RPC error over HTTP 200 on /mcp when the id is known; the
    Retry-After header is kept either way.
    """
    request_id = probe.request_id() if probe is not None and is_mcp_post(scope) else None
    if request_id is None:
        await send_json(send, error.status, error.to_dict(), extra)
        return
    await send_json(send, 200, jsonrpc_error_body(error, request_id), extra)


_MCP_INVALID = ("Requête invalide : un seul objet JSON-RPC 2.0 avec \"jsonrpc\": \"2.0\", pas de lot / invalid "
                "request: send one JSON-RPC 2.0 object with \"jsonrpc\": \"2.0\"; batches are not supported")
_MCP_PARSE = "JSON illisible / parse error: the body is not valid JSON"
_ERROR_BODY_MAX = 64 * 1024


class McpProtocolGuard:
    """Réponses du SDK MCP corrigées, sans écho de l'entrée / the MCP SDK's answers fixed, never echoing the input.

    - Message invalide (lot, « jsonrpc » absent…) : le SDK répond 400 `-32602` avec l'erreur Pydantic, qui cite
      l'entrée (`input_value=…`, un texte personnel peut-être). Remplacé par un message fixe : `-32600` (requête
      invalide), ou `-32700` pour un JSON illisible. An invalid message (batch, missing "jsonrpc"…) gets a fixed
      message instead of the Pydantic error that quotes the input.
    - `Allow` d'un 405 : le SDK annonce DELETE alors que DELETE répond 405 (serveur sans session) ; seul POST est
      annoncé. A 405's `Allow` names POST only (DELETE answers 405 too on this stateless server).
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        held: Message | None = None
        chunks: list[bytes] = []
        size = 0

        async def guarded_send(message: Message) -> None:
            nonlocal held, size
            if message["type"] == "http.response.start":
                status = message["status"]
                if status == 405:
                    message["headers"] = [(name, b"POST" if name.lower() == b"allow" else value)
                                          for name, value in message.get("headers", ())]
                elif status == 400:
                    held = message  # corps remplacé à la fin / body replaced at the end
                    return
                await send(message)
                return
            if held is None:
                await send(message)
                return
            if size < _ERROR_BODY_MAX:
                chunk = message.get("body", b"")[:_ERROR_BODY_MAX - size]
                chunks.append(chunk)
                size += len(chunk)
            if not message.get("more_body", False):
                await self._replace(send, held, b"".join(chunks))

        await self.app(scope, receive, guarded_send)

    @staticmethod
    async def _replace(send: Send, start: Message, body: bytes) -> None:
        try:
            original = json.loads(body)
        except ValueError:
            original = None
        error = original.get("error") if isinstance(original, dict) else None
        if not isinstance(error, dict) or "jsonrpc" not in original:
            # Pas une erreur JSON-RPC du SDK : rendue telle quelle / not a JSON-RPC error of the SDK: as is.
            await send(start)
            await send({"type": "http.response.body", "body": body})
            return
        code = error.get("code")
        if code == -32700:
            fixed = {"code": -32700, "message": _MCP_PARSE}
        elif code in (-32600, -32602):
            fixed = {"code": -32600, "message": _MCP_INVALID}
        else:
            fixed = {"code": code if type(code) is int else -32600, "message": _MCP_INVALID}
        payload = json.dumps({"jsonrpc": "2.0", "id": None, "error": fixed}, ensure_ascii=False).encode()
        headers = [(name, value) for name, value in start.get("headers", ())
                   if name.lower() not in (b"content-length", b"content-type")]
        await send({"type": "http.response.start", "status": 400,
                    "headers": [*headers, _JSON, (b"content-length", str(len(payload)).encode())]})
        await send({"type": "http.response.body", "body": payload})


async def refuse(scope: Scope, receive: Receive, send: Send, error: ServiceError,
                 headers: Sequence[tuple[bytes, bytes]], limit: int) -> None:
    """Refus lisible par tout client : corps lu à vide (borné), sauf « Expect: 100-continue ».

    A refusal every client can read: the body is drained (bounded), except with "Expect: 100-continue" (the client
    has not sent it). Sans cela, un client qui envoie tout son corps avant de lire la réponse voit une connexion
    réinitialisée. Otherwise a client sending its whole body first sees a connection reset. Corps lu à vide : au plus
    `limit` octets et `_DRAIN_S` secondes, jamais gardé / drained: at most `limit` bytes and `_DRAIN_S`, never kept.
    """
    declared = content_length(scope)
    drained = declared == 0
    # MCP : début et fin du corps lu à vide gardés pour l'id JSON-RPC / MCP: drained body's ends kept for the id.
    probe = JsonRpcIdProbe() if is_mcp_post(scope) else None
    if declared != 0 and not _expects_continue(scope):
        received = 0
        with anyio.move_on_after(_DRAIN_S):
            while received <= limit:
                message = await receive()
                if probe is not None and message["type"] == "http.request":
                    probe.feed(message.get("body", b""))
                if message["type"] != "http.request" or not message.get("more_body", False):
                    drained = message["type"] == "http.request"
                    break
                received += len(message.get("body", b""))
    extra = [*headers]
    if error.retry_after:
        extra.append((b"retry-after", str(error.retry_after).encode()))
    if not drained:
        extra.append((b"connection", b"close"))
        if probe is not None:
            probe.tail = b""  # fin non reçue : seul le début compte / end not received: the head only
    await send_refusal(scope, send, error, extra, probe)


class AccessLogMiddleware:
    """Filet de sécurité (aucune trace d'exception ne sort) et journal des réponses 5xx / last-resort guard and 5xx log.

    Pas de journal d'accès : chaque requête n'est notée qu'en DEBUG (développement), une réponse 5xx en WARNING. No
    access log: each request is only noted at DEBUG (development), a 5xx answer at WARNING.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = perf_counter()
        status = 0
        received = 0

        async def counting_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
            return message

        async def tracking_send(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, counting_receive, tracking_send)
        except Exception as exc:
            # Pas de relance : le serveur ASGI journaliserait le message de l'exception / no re-raise.
            log_event("unhandled_error", logging.ERROR, error=type(exc).__name__.lower())
            if not status:
                status = 500
                await send_json(send, 500, {"error": {"code": "internal_error",
                                                      "message": "Erreur interne / internal error"}})
        log_event("request", logging.WARNING if status >= 500 else logging.DEBUG, method=scope.get("method"),
                  route=route_template(scope.get("path", "")), status=status, bytes_in=received,
                  ms=(perf_counter() - started) * 1000)


class SecurityHeadersMiddleware:
    """Ajoute les en-têtes de sécurité à toute réponse, erreurs comprises / adds security headers everywhere.

    `Cache-Control: no-store` est imposé, quoi que réponde l'application : aucune réponse n'est jamais mise en
    cache ni partagée. `Cache-Control: no-store` is forced whatever the application answers: no response is ever
    cached or shared. `csp_exempt` : chemins sans CSP stricte (page /docs, si activée) / paths without the strict CSP.
    """

    def __init__(self, app: ASGIApp, *, hsts: bool = False, csp_exempt: frozenset[str] = frozenset()) -> None:
        self.app = app
        self.headers = _SECURITY_HEADERS
        if hsts:
            self.headers += ((b"strict-transport-security", b"max-age=31536000"),)
        self.relaxed = tuple(h for h in self.headers if h[0] != b"content-security-policy")
        self.csp_exempt = csp_exempt

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = self.relaxed if scope.get("path") in self.csp_exempt else self.headers

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                own = [(name, value) for name, value in message.get("headers", ())
                       if name.lower() not in (b"cache-control", b"pragma", b"expires")]
                present = {name.lower() for name, _ in own}
                message["headers"] = [*own, *(h for h in headers if h[0] not in present)]
            await send(message)

        await self.app(scope, receive, send_with_headers)


class HostGuardMiddleware:
    """En-tête Host contrôlé contre le « DNS rebinding » / Host header checked against DNS rebinding.

    Contrôle actif si des hôtes sont configurés ou si le serveur écoute en local (cas du mode sans
    authentification) ; les noms locaux restent acceptés (sonde de santé). Active when hosts are configured
    or the server listens on loopback; loopback names stay accepted (health probe).
    """

    def __init__(self, app: ASGIApp, *, allowed_hosts: Iterable[str] = ()) -> None:
        self.app = app
        self.allowed = tuple(host.strip().lower() for host in allowed_hosts if host.strip())

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and self._enforced(scope) and not self._accepted(_header(scope, b"host")):
            await send_json(send, 421, {"error": {"code": "misdirected_request",
                                                  "message": "Hôte non autorisé / host not allowed"}})
            return
        await self.app(scope, receive, send)

    def _enforced(self, scope: Scope) -> bool:
        server = scope.get("server")
        return bool(self.allowed) or bool(server and is_loopback_host(str(server[0])))

    def _accepted(self, host_header: str | None) -> bool:
        host = host_name(host_header or "")
        return is_loopback_host(host) or any(fnmatchcase(host, pattern) for pattern in self.allowed)


def host_name(host_header: str) -> str:
    """Nom d'hôte sans port, en minuscules, IPv6 sans crochets / host name without port, lowercase, bare IPv6."""
    host = host_header.strip().lower()
    if host.startswith("["):
        return host[1:].split("]", 1)[0]
    return host.rsplit(":", 1)[0] if host.count(":") == 1 else host


def is_loopback_host(host: str) -> bool:
    if host in _LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class GateMiddleware:
    """Porte d'entrée : identité, refus inter-sites, authentification et limiteur, tout AVANT la lecture du corps.

    Entry gate: identity, cross-site refusal, authentication and abuse limiter, all BEFORE the body is read.

    - Identité réseau : l'en-tête de confiance (retiré de la requête aussitôt lu) ou le pair TCP, devenu pseudonyme
      (`clients`). Aucune adresse ne va plus loin : `scope["client"]` est effacé. Network identity: the trusted
      header (removed from the request once read) or the TCP peer, turned into a pseudonym; no address goes further.
    - Requête qu'un navigateur envoie depuis une autre page (`Sec-Fetch-Site` autre que same-origin ou none) : 403,
      sans rien compter ; une page tierce ne peut pas faire de ses visiteurs une source de charge (un formulaire
      multipart passe sans contrôle CORS préalable). A request a browser sends from another page: 403, nothing
      counted; a third-party page cannot turn its visitors into a load source (a multipart form needs no preflight).
    - Mode public : aucune authentification ; une clé valide, s'il en existe, donne son propre principal. Mode à
      clés : un client sans clé valide n'obtient qu'un 401, jamais l'analyse d'un corps ; `/mcp` (délégué) répond
      lui-même 401, sous les limites du client réseau. Public mode: no authentication; a valid key, if any, gets its
      own principal. Keyed mode: a client without a valid key only gets a 401; `/mcp` (delegated) answers its own
      401, under the network client's limits.
    - Limiteur (`limiter`) : 429 ou 503 avec Retry-After, RateLimit-Policy et RateLimit, corps JSON fermé.
      Limiter: 429 or 503 with Retry-After, RateLimit-Policy and RateLimit, closed JSON body.

    Le principal et la clé d'équité du budget sont déposés dans `scope["state"]`, le contexte de la requête (client,
    ticket du limiteur) dans `clients.REQUEST`, que les outils MCP et le service relisent. Une réponse 503 (refus de
    capacité) rend au client le coût pré-imputé, sauf si un travailleur a servi. The principal and the budget
    fairness key go into `scope["state"]`, the request context (client, limiter ticket) into `clients.REQUEST`, read
    back by the MCP tools and the service. A 503 answer (capacity refusal) refunds the pre-charged cost, unless a
    worker was used.
    """

    def __init__(self, app: ASGIApp, *, authenticate: Callable[[str | None], str | None] | None,
                 identifier: ClientIdentifier, limiter: Limiter, limit_for: Callable[[Scope], int],
                 open_paths: frozenset[str], delegated: frozenset[str], keyless: bool) -> None:
        self.app = app
        self.authenticate = authenticate
        self.identifier = identifier
        self.limiter = limiter
        self.limit_for = limit_for
        self.open_paths = open_paths
        self.delegated = delegated
        # Mode public ou développement : une requête sans clé passe / public or dev mode: no key needed.
        self.keyless = keyless

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        network, scope["headers"] = self.identifier.network(list(scope.get("headers", ())), scope.get("client"))
        scope["client"] = None  # plus aucune adresse dans la requête / no address left in the request
        fetch_site = _header(scope, b"sec-fetch-site")
        if fetch_site is not None and fetch_site.strip().lower() not in _FETCH_SITES:
            # Corps jamais lu : connexion fermée s'il y en a un / body never read: connection closed if there is one.
            declared = content_length(scope)
            pending = declared not in (None, 0) or _header(scope, b"transfer-encoding") is not None
            unread = [(b"connection", b"close")] if pending else []
            await send_json(send, CrossSiteRefused.status, CrossSiteRefused().to_dict(), unread)
            return
        client = self._client(scope, network, path)
        if client is None:
            log_event("auth_failed", logging.WARNING, route=route_template(path))
            await send_json(send, Unauthorized.status, Unauthorized().to_dict(),
                            [(b"www-authenticate", WWW_AUTHENTICATE.encode())])
            return
        method = scope.get("method", "")
        route = route_template(path)
        content = _CONTENT.get((method, route))
        declared = content_length(scope)
        limit = self.limit_for(scope)
        # Taille annoncée, plafonnée à la limite de la route (au-delà : 413 plus loin) ; corps « chunked » : la
        # limite. Declared size, capped at the route's limit (beyond: 413 further in); chunked body: the limit.
        size = min(declared, limit) if declared is not None and declared >= 0 else limit
        # MCP : délestage sur l'attente reporté à la prise d'un travailleur ; suivre un envoi en cours ne doit pas
        # être refusé parce que ce même client occupe un travailleur. MCP: wait-based shedding deferred until a worker
        # is taken; polling an upload in progress must not be refused because the same client holds a worker.
        decision = self.limiter.admit(client, cheap=content is None or route in _CHEAP_CONTENT, content=content,
                                      size=size, shed=route not in _DEFERRED_SHED)
        if decision.status:
            error: ServiceError = (RateLimited(retry_after=decision.retry_after) if decision.status == 429
                                   else ServiceBusy(retry_after=decision.retry_after))
            await refuse(scope, receive, send, error, decision.headers, limit)
            return
        state = scope.setdefault("state", {})
        state[PRINCIPAL_STATE_KEY] = client.principal
        state[BUDGET_STATE_KEY] = client.budget_key
        token = REQUEST.set(RequestContext(client, decision.ticket))
        extra = decision.headers
        status = 0

        async def send_with_headers(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                if extra:
                    message["headers"] = [*message.get("headers", ()), *extra]
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        finally:
            REQUEST.reset(token)
            ticket = decision.ticket
            if ticket is not None and status == ServiceBusy.status and not ticket.worked:
                ticket.waived = True  # refus de capacité du service : rien n'est dû / capacity refusal: nothing due
            self.limiter.finish(ticket)

    def _client(self, scope: Scope, network: Client, path: str) -> Client | None:
        """Client de la requête ; None : 401 / the request's client; None: 401."""
        if self.authenticate is not None:
            principal = self.authenticate(_header(scope, b"authorization"))
            if principal is not None:
                # Envois liés à la clé, en plus de leur capacité / uploads bound to the key, on top of the capability.
                return self.identifier.principal(principal, owner=principal, local=network.local)
        if self.keyless or path in self.open_paths or path in self.delegated:
            # Délégué (/mcp en mode à clés) : MCP répond lui-même 401, sous les limites du client réseau, pas d'un
            # seau commun qu'un seul pourrait vider. Delegated: MCP answers its own 401, under the network client's
            # limits, not a shared bucket one client could drain.
            return network
        return None


class BodySizeLimitMiddleware:
    """Limite stricte de taille et de durée des corps, y compris en « chunked » / hard body size and time limits.

    `Content-Length` permet un refus immédiat ; sinon les octets sont comptés à la réception. Au-delà de la limite,
    `receive()` lève `PayloadTooLarge` et toute réponse est remplacée par un 413. Durée : le corps entier doit
    arriver en `base_s` plus sa taille (annoncée, sinon la limite de la route) au débit `min_rate` ; au-delà,
    `receive()` lève `UploadTimeout` et la réponse devient un 408, connexion fermée. Un corps qui goutte (un octet
    toutes les 14 s passe le délai entre deux lectures de Nginx) ne tient donc ni connexion ni budget au-delà.
    `Content-Length` allows an immediate refusal; else bytes are counted on arrival. Beyond the limit, `receive()`
    raises `PayloadTooLarge` and whatever the app answers becomes a 413. Time: the whole body must arrive within
    `base_s` plus its size (declared, else the route's limit) at `min_rate`; beyond, `receive()` raises
    `UploadTimeout` and the answer becomes a 408, connection closed. A trickling body (one byte every 14 s passes
    Nginx's between-reads timeout) thus holds neither connection nor budget any longer. Après le dernier fragment,
    plus aucun délai (attente de la déconnexion) / after the last chunk, no deadline (waiting for a disconnect).
    `too_large` : le 413 de la route, limite nommée (défaut : message générique) / the route's 413, limit named.
    """

    def __init__(self, app: ASGIApp, *, limit_for: Callable[[Scope], int], base_s: float = 15.0,
                 min_rate: float = 128 * 1024, too_large: Callable[[Scope], ServiceError] | None = None) -> None:
        self.app = app
        self.limit_for = limit_for
        self.base_s = base_s
        self.min_rate = min_rate
        self.too_large = too_large or (lambda _scope: PayloadTooLarge())

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        limit = self.limit_for(scope)
        declared = content_length(scope)
        if declared == -1:
            await send_json(send, 400, {"error": {"code": "invalid_request",
                                                  "message": "Content-Length invalide / invalid Content-Length"}})
            return
        if declared is not None and declared > limit:
            await self._reject(send, self.too_large(scope))
            return
        deadline = anyio.current_time() + self.base_s + (limit if declared is None else declared) / self.min_rate
        received = 0
        refusal: ServiceError | None = None
        complete = declared == 0
        started = False
        # MCP : début du corps gardé pour répondre une erreur JSON-RPC à l'agent (408, 413) / MCP: body head kept to
        # answer the agent with a JSON-RPC error.
        probe = JsonRpcIdProbe() if is_mcp_post(scope) else None

        async def limited_receive() -> Message:
            nonlocal received, refusal, complete
            if refusal is not None:
                raise refusal
            if complete:
                return await receive()
            try:
                with anyio.fail_after(max(0.0, deadline - anyio.current_time())):
                    message = await receive()
            except TimeoutError:
                refusal = UploadTimeout()
                raise refusal from None
            if message["type"] != "http.request":
                complete = True  # déconnexion / disconnect
                return message
            received += len(message.get("body", b""))
            if received > limit:
                refusal = self.too_large(scope)
                raise refusal
            if probe is not None:
                probe.feed(message.get("body", b""))
            complete = not message.get("more_body", False)
            return message

        async def guarded_send(message: Message) -> None:
            nonlocal started
            if refusal is not None:
                if not started:
                    started = True
                    await self._reject(send, refusal, scope, probe)
                return
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, guarded_send)
        except Exception:
            if refusal is None:
                raise
        if refusal is not None and not started:
            await self._reject(send, refusal, scope, probe)

    @staticmethod
    async def _reject(send: Send, error: ServiceError, scope: Scope | None = None,
                      probe: JsonRpcIdProbe | None = None) -> None:
        if scope is not None and probe is not None:
            probe.tail = b""  # corps incomplet : seul le début compte / incomplete body: the head only
            await send_refusal(scope, send, error, [(b"connection", b"close")], probe)
            return
        await send_json(send, error.status, error.to_dict(), [(b"connection", b"close")])


def content_length(scope: Scope) -> int | None:
    """Longueur déclarée ; -1 si invalide / declared length; -1 when invalid."""
    value = _header(scope, b"content-length")
    if value is None:
        return None
    # ASCII seulement : « ² » est un chiffre pour str.isdigit() / ASCII only: "²" passes str.isdigit().
    return int(value) if value.isascii() and value.isdigit() and len(value) <= 18 else -1
