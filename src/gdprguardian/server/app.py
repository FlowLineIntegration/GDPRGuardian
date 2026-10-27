"""Application ASGI : API REST et serveur MCP en ligne / ASGI application: REST API and online MCP server.

Le processus principal ne fait que HTTP, l'admission, l'ordonnancement et le dépôt des résultats (en mémoire,
rien sur disque, balayé en continu) ; chaque requête, règles de l'organisation comprises, est traitée dans un
processus isolé à usage unique. The main process only does HTTP, admission, scheduling and the result store
(in memory, nothing on disk, swept continuously); each request, organisation rules included, is processed in a
single-use isolated process.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import AsyncIterator, Callable, Sequence
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any

import anyio
import anyio.to_thread
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Scope

from .. import __version__
from ..categories import MODES_HELP
from .admission import AdmissionMiddleware
from .api import build_router
from .config import MULTIPART_ENVELOPE_BYTES, ServerConfig, scrub_settings
from .errors import PayloadTooLarge, ServiceError, file_too_large, text_too_long
from .logs import LOGGER, log_event
from .middleware import (
    DEEP_HEALTH,
    WWW_AUTHENTICATE,
    AccessLogMiddleware,
    BodySizeLimitMiddleware,
    GateMiddleware,
    HostGuardMiddleware,
    McpProtocolGuard,
    SecurityHeadersMiddleware,
    route_template,
)
from .options import CATEGORIES_HELP
from .security import ApiKeyAuthenticator, Authenticator, DevAuthenticator
from .service import Service

Lifespan = Callable[[Any], AbstractAsyncContextManager[Any]]

_SMALL_BODY_BYTES = 4 * 1024
# Création d'un envoi : options et règles seulement (un jeu de règles tient en quelques dizaines de Ko).
# Creating an upload: options and rules only (a rule set fits in a few tens of KB).
_UPLOAD_TICKET_BYTES = 256 * 1024
_FILE_ROUTES = frozenset({"/v1/uploads/{token}", "/v1/anonymize/file"})
# Routes dont le corps JSON porte un texte (sa limite d'octets découle de celle des caractères).
# Routes whose JSON body carries a text (its byte limit derives from the character limit).
_TEXT_ROUTES = frozenset({"/v1/anonymize/text", "/v1/detect", "/mcp"})
# Routes qui portent un corps (budget mémoire), dont celles annulées si le client part.
# Routes carrying a body (memory budget), and those cancelled when the client leaves.
_CONTENT_ROUTES = frozenset({"/v1/anonymize/text", "/v1/detect", "/v1/anonymize/file", "/v1/uploads/{token}", "/mcp",
                             "/v1/uploads"})
_SYNCHRONOUS_ROUTES = frozenset({"/v1/anonymize/text", "/v1/detect", "/v1/anonymize/file"})
_HTTP_ERROR_CODES = {404: "not_found", 405: "method_not_allowed"}
# Seuls ces noms de champs reviennent dans une erreur 422 (jamais une clé JSON inventée par le client).
# Only these field names come back in a 422 (never a JSON key made up by the client).
_KNOWN_FIELDS = frozenset({"body", "query", "path", "text", "countries", "mode", "disable", "profile", "label_language",
                           "rules", "explain", "filename", "page", "page_chars", "format", "upload_id", "token"})
_ALLOWED_VALUES = {"profile": "fast | standard | strict (deprecated: use mode)", "label_language": "fr | en | auto",
                   "format": "json | markdown", "mode": MODES_HELP,
                   "disable": "a list of categories: " + CATEGORIES_HELP, "explain": "true | false"}
_DEV_WARNING = ("!!! GDPRGUARDIAN_DEV_NO_AUTH=1 : AUCUNE AUTHENTIFICATION. Usage local uniquement, jamais exposé "
                "sur un réseau. / NO AUTHENTICATION. Local use only, never expose it on a network. !!!")


def create_app(config: ServerConfig | None = None, *, clock: Callable[[], float] = time.monotonic) -> FastAPI:
    """Construit l'application ; `clock` est injectable pour les tests / builds the app; injectable clock.

    Sans `config` (lancement par `uvicorn --factory`), les réglages sont lus puis retirés de l'environnement
    avant tout processus enfant, comme avec `gdprguardian serve`. Without `config` (launched by `uvicorn
    --factory`), settings are read then removed from the environment before any child process, as with
    `gdprguardian serve`.
    """
    if config is None:
        config = ServerConfig.from_env()
        scrub_settings()
    # Même lancé hors de `gdprguardian serve` (uvicorn --factory) : ni journal d'accès ni journal FastMCP.
    # Even outside `gdprguardian serve`: no access log, no FastMCP log.
    os.environ.setdefault("FASTMCP_LOG_ENABLED", "false")
    logging.getLogger("uvicorn.access").disabled = True
    # Aucun moteur ici, aucune règle compilée : packs, automates et lexiques sont préchargés dans les
    # travailleurs (zygote), qui compilent aussi les règles de l'organisation. No engine here, no rule compiled:
    # packs, automata and lexicons are preloaded in the workers (zygote), which also compile organisation rules.
    service = Service(config, clock=clock)
    authenticator: Authenticator | None = None
    if config.dev_no_auth:
        LOGGER.warning(_DEV_WARNING)
        authenticator = DevAuthenticator()
    else:
        if config.keyed:
            authenticator = ApiKeyAuthenticator(config.api_keys, config.api_key_sha256)
        if config.public_url is None and not config.allowed_hosts:
            # Les URL d'envoi (des capacités) suivraient l'en-tête Host / upload URLs (capabilities) would follow Host.
            LOGGER.warning("GDPRGUARDIAN_PUBLIC_URL et GDPRGUARDIAN_ALLOWED_HOSTS non définis : à définir en "
                           "production / not set: define them in production")
    if config.public and config.client_ip_header is None:
        LOGGER.warning("GDPRGUARDIAN_CLIENT_IP_HEADER non défini : chaque client est reconnu à l'adresse du pair TCP "
                       "(derrière un proxy, tous partagent la sienne) / not set: clients are told apart by the TCP "
                       "peer address (behind a proxy, they all share the proxy's)")

    mcp, mcp_app = _build_mcp(service, None if config.public else authenticator)
    app = FastAPI(
        title="Gardien RGPD · GDPR Guardian",
        version=__version__,
        summary="Anonymisation irréversible de documents avant IA / irreversible document anonymisation",
        lifespan=_lifespan(service, getattr(mcp_app, "lifespan", None)),
        docs_url="/docs" if config.docs else None,
        redoc_url=None,
        openapi_url="/openapi.json" if config.docs else None,
        # Ni redirection de barre oblique (elle viserait http://, le corps repartirait en clair) : 404 JSON.
        # No trailing-slash redirect (it would target http://, resending the body in clear): JSON 404 instead.
        redirect_slashes=False,
    )
    app.state.service = service
    app.state.mcp = mcp
    app.include_router(build_router(service))
    _install_error_handlers(app)
    if mcp_app is not None:
        # Route exacte vers l'application MCP : POST /mcp répond 200 (pas de redirection 307), et les autres
        # chemins gardent les erreurs JSON de l'API. Exact route to the MCP app: no 307, JSON errors elsewhere.
        app.add_route("/mcp", McpProtocolGuard(mcp_app), include_in_schema=False)

    def limit_for(scope: Scope) -> int:
        route = route_template(scope.get("path", ""))
        if route in _FILE_ROUTES:
            return config.max_upload_bytes + MULTIPART_ENVELOPE_BYTES
        if scope.get("method") in ("GET", "HEAD", "DELETE", "OPTIONS"):
            return _SMALL_BODY_BYTES
        if route == "/v1/uploads":
            return _UPLOAD_TICKET_BYTES
        return config.max_json_bytes

    def too_large_for(scope: Scope) -> ServiceError:
        """413 de la route, limite publiée nommée / the route's 413, its published limit named."""
        route = route_template(scope.get("path", ""))
        if route in _FILE_ROUTES:
            return file_too_large(config.max_upload_bytes)
        if route in _TEXT_ROUTES:
            return text_too_long(config.max_text_chars)
        return PayloadTooLarge()

    docs_paths = frozenset({"/docs", "/docs/oauth2-redirect", "/openapi.json"}) if config.docs else frozenset()
    # Le dernier ajouté est le plus externe : en-têtes de sécurité sur toute réponse (401, 403, 408, 413, 421, 429,
    # 500, 503 compris), puis journal des erreurs, hôte, porte d'entrée (identité, refus inter-sites,
    # authentification, limiteur) AVANT toute lecture du corps, admission (budget mémoire, le principal connu), taille
    # et durée du corps. The last added is the outermost: security headers on every response, then error log, host,
    # entry gate (identity, cross-site refusal, authentication, limiter) BEFORE any body is read, admission (memory
    # budget, principal known), then body size and duration.
    app.add_middleware(BodySizeLimitMiddleware, limit_for=limit_for, base_s=config.body_base_s,
                       min_rate=config.body_min_rate, too_large=too_large_for)
    app.add_middleware(AdmissionMiddleware, budget=service.budget, limit_for=limit_for,
                       retry_after=service.retry_after, routes=_CONTENT_ROUTES,
                       cancel_on_disconnect=_SYNCHRONOUS_ROUTES)
    app.add_middleware(GateMiddleware, authenticate=None if authenticator is None else authenticator.authenticate,
                       identifier=service.clients, limiter=service.limiter, limit_for=limit_for,
                       open_paths=frozenset({"/health", DEEP_HEALTH, "/status"}) | docs_paths,
                       delegated=frozenset({"/mcp"}) if mcp_app is not None else frozenset(),
                       keyless=config.public or config.dev_no_auth)
    app.add_middleware(HostGuardMiddleware, allowed_hosts=config.allowed_hosts)
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(SecurityHeadersMiddleware, hsts=(config.public_url or "").startswith("https://"),
                       csp_exempt=frozenset({"/docs"}) if config.docs else frozenset())
    return app


def _build_mcp(service: Service, authenticator: Authenticator | None) -> tuple[Any, ASGIApp | None]:
    """Serveur MCP en ligne, ou rien si FastMCP manque (l'API REST reste servie) / None without FastMCP.

    `authenticator` : clés exigées par MCP (mode à clés) ; None en mode public ou développement.
    `authenticator`: keys required by MCP (keyed mode); None in public or dev mode.
    """
    try:
        from .mcp_online import ApiKeyVerifier, build_online_mcp
    except ImportError:
        LOGGER.warning('MCP désactivé : pip install "gdprguardian[mcp]" '
                       '/ MCP disabled: pip install "gdprguardian[mcp]"')
        return None, None
    _no_string_cache_in_mcp_transport()
    verifier = (None if service.config.dev_no_auth or authenticator is None
                else ApiKeyVerifier(authenticator))
    mcp = build_online_mcp(service, auth=verifier)
    mcp_app = mcp.http_app(path="/mcp", stateless_http=True, json_response=True,
                           allowed_hosts=list(service.config.allowed_hosts) or None)
    return mcp, mcp_app


def _no_string_cache_in_mcp_transport() -> None:
    """Le transport MCP lit le JSON avec le cache global de chaînes de pydantic-core (≤ 64 octets) : textes
    courts et noms de fichiers y survivraient d'une requête à l'autre. On le désactive ; échec fermé si la
    bibliothèque change. The MCP transport parses JSON with pydantic-core's global string cache: short texts
    would outlive the request. Disabled here; fails closed if the library changes.
    """
    import functools
    import types

    import mcp.server.streamable_http as transport
    import pydantic_core

    if not hasattr(transport, "pydantic_core"):
        raise RuntimeError("mcp.server.streamable_http a changé : vérifier le cache de chaînes / string cache check")
    transport.pydantic_core = types.SimpleNamespace(
        from_json=functools.partial(pydantic_core.from_json, cache_strings=False))


def _lifespan(service: Service, inner: Lifespan | None) -> Lifespan:
    """Balayage des expirés, travailleurs isolés, cycle de vie MCP, socket du compteur d'usage fermé à l'arrêt.

    Sweep, isolated workers, MCP lifespan, usage counter socket closed at shutdown.
    """
    config = service.config

    async def sweep() -> None:
        while True:
            await anyio.sleep(config.sweep_interval_s)
            service.store.purge()
            # Clés reposées ou inactives ; erreurs internes signalées / rested or idle keys; internal errors reported.
            service.limiter.sweep()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        _start_workers(service)
        try:
            async with anyio.create_task_group() as tasks:
                tasks.start_soon(sweep)
                if inner is None:
                    yield
                else:
                    async with inner(app):
                        yield
                tasks.cancel_scope.cancel()
        finally:
            try:
                await anyio.to_thread.run_sync(service.stop_workers)
            finally:
                service.usage.close()

    return lifespan


def _start_workers(service: Service) -> None:
    """Zygote et réserve préparés en arrière-plan, au mieux / zygote and reserve warmed up, best effort."""
    try:
        service.start_workers()
    except Exception as exc:  # démarrage refusé : chaque requête réessaiera / start refused: requests will retry
        log_event("prewarm_failed", logging.WARNING, error=type(exc).__name__.lower())


def _field_path(loc: Sequence[Any]) -> str:
    return ".".join(str(part) if isinstance(part, int) or part in _KNOWN_FIELDS else "?" for part in loc)


def _install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ServiceError)
    async def service_error(_: Request, exc: ServiceError) -> JSONResponse:
        headers = {}
        if exc.status == 401:
            headers["www-authenticate"] = WWW_AUTHENTICATE
        if exc.retry_after:
            headers["retry-after"] = str(exc.retry_after)
        return JSONResponse(exc.to_dict(), status_code=exc.status, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Emplacements des champs seulement, jamais les valeurs reçues / field locations only, never input values.
        errors = exc.errors()
        fields = sorted({_field_path(error.get("loc", ())) for error in errors})
        # Valeurs admises des options fermées (tirées du schéma) / allowed values of closed options (from the schema).
        hints = sorted({f"{loc[-1]}: {_ALLOWED_VALUES[loc[-1]]}" for error in errors
                        if (loc := tuple(error.get("loc", ()))) and loc[-1] in _ALLOWED_VALUES})
        body: dict[str, Any] = {"code": "invalid_request", "message": "Requête invalide / invalid request",
                                "fields": fields}
        if hints:
            body["allowed"] = hints
        return JSONResponse({"error": body}, status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _HTTP_ERROR_CODES.get(exc.status_code, "http_error")
        return JSONResponse({"error": {"code": code, "message": code.replace("_", " ")}},
                            status_code=exc.status_code, headers=getattr(exc, "headers", None))


__all__ = ["create_app"]
