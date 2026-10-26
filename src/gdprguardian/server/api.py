"""Routes REST /v1 / REST routes.

Flux pour les agents / agent flow: `POST /v1/uploads` -> `PUT /v1/uploads/{token}` (le fichier, envoyé
sans être lu par le modèle / the file, sent without the model reading it) -> `GET /v1/results/{id}`.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field
from starlette.exceptions import HTTPException

from .. import __version__
from .clients import current_client
from .config import MAX_PAGE_CHARS, MIN_PAGE_CHARS
from .errors import InvalidRequest, ServiceBusy, Unauthorized
from .middleware import DEEP_HEALTH, PRINCIPAL_STATE_KEY
from .multipart import read_multipart
from .options import AnonymizeOptions, LabelLanguage, Profile
from .pagination import page_bounds
from .security import result_id
from .service import Service

_OPTION_FIELDS = frozenset({"countries", "profile", "label_language", "rules", "explain"})
_RULES_DESCRIPTION = (
    "Jeu de règles de l'organisation (masquer, conserver, termes imposés ou permis), jamais conservé ni "
    "journalisé ; voir docs/REGLES.md / the organisation's rule set, never kept nor logged. "
    'Exemple / example: {"rules": [{"label": "CLIENT_ID", "pattern": "CLT-[0-9]{6}"}]}')


async def _principal(request: Request) -> str:
    """Principal posé par `AuthGateMiddleware` ; absent = refus (échec fermé) / set by the gate, else refused.

    Asynchrone : FastAPI exécuterait une dépendance synchrone dans un fil, un aller-retour par requête.
    Async: FastAPI would run a sync dependency in a thread, one round trip per request.
    """
    principal = getattr(request.state, PRINCIPAL_STATE_KEY, None)
    if not isinstance(principal, str):
        raise Unauthorized
    return principal


Principal = Annotated[str, Depends(_principal)]


# --- Modèles / models -------------------------------------------------------------------------------


class OptionsBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    countries: str | list[str] | None = Field(None, description="'FR' (défaut), 'FR,BE', ['FR', 'BE'], 'all' ou "
                                                                 "'auto' (expérimental)")
    profile: Profile = "standard"
    label_language: LabelLanguage = "fr"
    rules: dict[str, Any] | None = Field(None, description=_RULES_DESCRIPTION)
    explain: bool = Field(False, description="Rapport : pour chaque balise, la règle et la raison (jamais la "
                                             "valeur) / per-tag rule and reason, never the value")

    def options(self) -> AnonymizeOptions:
        return _options(self.countries, self.profile, self.label_language, self.rules, self.explain)


class TextBody(OptionsBody):
    text: str


class UploadBody(OptionsBody):
    filename: str = Field(min_length=1, max_length=1024,
                          description="Nom ou extension du fichier ; seule l'extension est gardée / only the "
                                      "extension is kept")


class HealthOut(BaseModel):
    status: Literal["ok"] = "ok"
    version: str = __version__


class WorkersOut(BaseModel):
    slots: int
    reserved_small: int
    busy: int
    waiting: int


class StatusOut(BaseModel):
    """État agrégé du service (aucune donnée d'un client) / aggregate service state (nothing about a client)."""

    status: Literal["ok"] = "ok"
    version: str = __version__
    public: bool
    limits: str
    workers: WorkersOut
    estimated_wait_s: float
    counters: dict[str, int]


class TextOut(BaseModel):
    text: str
    report: dict[str, Any]


class DetectOut(BaseModel):
    report: dict[str, Any]


class DocumentOut(BaseModel):
    markdown: str
    kind: str
    pages: int | None
    report: dict[str, Any]
    warnings: list[str]
    dropped: dict[str, int]


class UploadTicketOut(BaseModel):
    upload_id: str
    upload_url: str
    method: Literal["PUT"] = "PUT"
    expires_in: int
    max_bytes: int
    result_url: str


class UploadReceiptOut(BaseModel):
    upload_id: str
    status: str
    kind: str
    total_chars: int
    pages: int
    page_chars: int
    expires_in: int
    result_url: str


class ResultOut(BaseModel):
    upload_id: str
    status: str
    expires_in: int
    page: int | None = None
    pages: int | None = None
    next_page: int | None = None
    page_chars: int | None = None
    total_chars: int | None = None
    deleted: bool = False
    kind: str | None = None
    markdown: str | None = None
    report: dict[str, Any] | None = None
    warnings: list[str] | None = None
    dropped: dict[str, int] | None = None


class PacksOut(BaseModel):
    packs: list[dict[str, Any]]


def _options(countries: str | list[str] | None, profile: str | None, label_language: str | None,
             rules: dict[str, Any] | str | None = None, explain: bool | str | None = False) -> AnonymizeOptions:
    try:
        return AnonymizeOptions.build(countries, profile, label_language, rules, explain)
    except ValueError as exc:
        # Message construit par nous, sans donnée d'entrée / our own message, no input data.
        raise InvalidRequest(f"Option invalide / invalid option: {exc}") from None


# --- Routes -----------------------------------------------------------------------------------------


def build_router(service: Service) -> APIRouter:
    """Routes /v1 ; l'authentification a lieu avant, dans `AuthGateMiddleware` / auth happens before, in the gate."""
    config = service.config
    router = APIRouter()

    @router.get("/health", response_model=HealthOut, tags=["service"])
    async def health() -> HealthOut:
        return HealthOut()

    @router.get(DEEP_HEALTH, response_model=HealthOut, include_in_schema=False)
    async def deep_health() -> HealthOut:
        # Serveur lui-même seulement (sonde de l'hôte) ; pour tout autre, la route n'existe pas.
        # The server itself only (host probe); for anyone else, the route does not exist.
        client = current_client()
        if client is None or not client.local:
            raise HTTPException(404)
        if not await service.deep_health():
            raise ServiceBusy(retry_after=10)
        return HealthOut()

    @router.get("/status", response_model=StatusOut, tags=["service"])
    async def status() -> StatusOut:
        # Places, file, attente estimée et compteurs agrégés du limiteur / slots, queue, wait, aggregate counters.
        return StatusOut.model_validate(service.status())

    @router.get("/v1/packs", response_model=PacksOut, tags=["service"])
    async def packs(_: Principal) -> PacksOut:
        return PacksOut(packs=service.packs)

    @router.post("/v1/anonymize/text", response_model=TextOut, tags=["anonymize"])
    async def anonymize_text(body: TextBody, principal: Principal) -> TextOut:
        result = await service.anonymize_text(body.text, body.options(), principal)
        return TextOut(text=result.text, report=result.report)

    @router.post("/v1/detect", response_model=DetectOut, tags=["anonymize"])
    async def detect(body: TextBody, principal: Principal) -> DetectOut:
        # Rapport seul, sans contenu ni position / report only, no content and no positions.
        result = await service.anonymize_text(body.text, body.options(), principal)
        return DetectOut(report=result.report)

    @router.post("/v1/anonymize/file", response_model=DocumentOut, tags=["anonymize"],
                 openapi_extra={"requestBody": {"required": True, "content": {"multipart/form-data": {"schema": {
                     "type": "object", "required": ["file"],
                     "properties": {"file": {"type": "string", "format": "binary"},
                                    "countries": {"type": "string"}, "profile": {"type": "string"},
                                    "label_language": {"type": "string"},
                                    "rules": {"type": "string", "description": "JSON"},
                                    "explain": {"type": "string"}}}}}}})
    async def anonymize_file(request: Request, principal: Principal) -> DocumentOut:
        # Mémoire réservée avant la lecture du corps (admission) / memory reserved before the body is read.
        form = await service.within_deadline(read_multipart(
            request.headers.get("content-type"), request.stream(), max_file_bytes=config.max_upload_bytes))
        if set(form.fields) - _OPTION_FIELDS:
            raise InvalidRequest("Champ inconnu / unknown field")
        options = _options(form.fields.get("countries"), form.fields.get("profile"),
                           form.fields.get("label_language"), form.fields.get("rules"), form.fields.get("explain"))
        result = await service.anonymize_document(form.data, form.filename or "document", options, principal)
        return DocumentOut(markdown=result.markdown, kind=result.kind, pages=result.pages, report=result.report,
                           warnings=result.warnings, dropped=result.dropped)

    @router.post("/v1/uploads", response_model=UploadTicketOut, status_code=201, tags=["uploads"])
    async def create_upload(body: UploadBody, request: Request, principal: Principal) -> UploadTicketOut:
        _, token = service.create_upload(principal, body.filename, body.options())
        base = str(request.base_url)
        upload_id = result_id(token)  # capacité de lecture, remise au seul demandeur / read capability
        return UploadTicketOut(upload_id=upload_id, upload_url=service.upload_url(base, token),
                               expires_in=int(config.upload_ttl_s), max_bytes=config.max_upload_bytes,
                               result_url=service.result_url(base, upload_id))

    @router.put("/v1/uploads/{token}", response_model=UploadReceiptOut, tags=["uploads"],
                openapi_extra={"requestBody": {"required": True, "content": {"application/octet-stream": {
                    "schema": {"type": "string", "format": "binary"}}}}})
    async def receive_upload(token: str, request: Request, principal: Principal) -> UploadReceiptOut:
        # Taille annoncée (déjà validée par l'intergiciel des corps) : un fichier trop gros est refusé avant sa
        # lecture. Declared size (already validated by the body middleware): an oversized file is refused unread.
        length = request.headers.get("content-length")
        declared = int(length) if length is not None and length.isascii() and length.isdigit() else None
        _, result = await service.receive_upload(token, principal, request.stream(), declared)
        pages = len(page_bounds(result.markdown, config.page_chars)) - 1
        # Recalculée du jeton présenté (le dépôt ne la garde pas) / recomputed from the token (not kept by the store).
        upload_id = result_id(token)
        return UploadReceiptOut(upload_id=upload_id, status="ready", kind=result.kind,
                                total_chars=len(result.markdown), pages=pages, page_chars=config.page_chars,
                                expires_in=int(config.result_ttl_s),
                                result_url=service.result_url(str(request.base_url), upload_id))

    @router.get("/v1/results/{upload_id}", response_model=ResultOut, tags=["uploads"],
                responses={202: {"description": "Fichier pas encore reçu ou en cours / not received or processing"}})
    async def read_result(
        upload_id: str,
        principal: Principal,
        page: Annotated[int, Query(ge=1, le=1_000_000)] = 1,
        page_chars: Annotated[int | None, Query(ge=MIN_PAGE_CHARS, le=MAX_PAGE_CHARS)] = None,
        output: Annotated[Literal["json", "markdown"], Query(alias="format")] = "json",
    ) -> Response | ResultOut:
        view = service.read_result(principal, upload_id, page, page_chars)
        if view.page is None:
            return JSONResponse({"upload_id": view.upload_id, "status": view.status, "expires_in": view.expires_in},
                                status_code=202, headers={"retry-after": "1"})
        if output == "markdown":
            headers = {"x-gdprguardian-page": str(view.page), "x-gdprguardian-pages": str(view.pages),
                       "x-gdprguardian-next-page": str(view.next_page or ""),
                       "x-gdprguardian-deleted": str(view.deleted)}
            return Response(view.markdown or "", media_type="text/markdown; charset=utf-8", headers=headers)
        return ResultOut.model_validate(view, from_attributes=True)

    @router.delete("/v1/results/{upload_id}", status_code=204, tags=["uploads"])
    async def delete_result(upload_id: str, principal: Principal) -> Response:
        service.store.delete(upload_id, principal)
        return Response(status_code=204)

    return router
