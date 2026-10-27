"""Routes REST /v1 / REST routes.

Flux pour les agents / agent flow: `POST /v1/uploads` -> `PUT /v1/uploads/{token}` (le fichier, envoyé
sans être lu par le modèle / the file, sent without the model reading it) -> `GET /v1/results/{id}`.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field
from starlette.background import BackgroundTask
from starlette.exceptions import HTTPException

from .. import __version__
from .clients import current_client
from .config import MAX_PAGE_CHARS, MIN_PAGE_CHARS
from .errors import InvalidRequest, ServiceBusy, Unauthorized
from .middleware import DEEP_HEALTH, PRINCIPAL_STATE_KEY
from .multipart import read_multipart
from .options import (
    DISABLE_DESCRIPTION,
    MODE_DESCRIPTION,
    PROFILE_DESCRIPTION,
    AnonymizeOptions,
    LabelLanguage,
    Mode,
    Profile,
)
from .security import result_id
from .service import Service, check_upload_name

_OPTION_FIELDS = frozenset({"countries", "mode", "disable", "profile", "label_language", "rules", "explain"})
_RULES_DESCRIPTION = (
    "Jeu de règles de l'organisation (masquer, conserver, termes imposés ou permis), appliqué dans tous les modes, "
    "jamais conservé ni journalisé ; voir docs/REGLES.md / the organisation's rule set, applied in every mode, never "
    'kept nor logged. Exemple / example: {"rules": [{"label": "CLIENT_ID", "pattern": "CLT-[0-9]{6}"}, '
    '{"label": "SKU", "pattern": "SKU-[0-9]{6}", "action": "keep"}]} : SKU-123456 reste lisible, CLT-204518 est '
    "masqué / SKU-123456 stays readable, CLT-204518 is masked.")
# Mêmes descriptions que les outils MCP / same descriptions as the MCP tools.
_MODE_DESCRIPTION = MODE_DESCRIPTION
_DISABLE_DESCRIPTION = DISABLE_DESCRIPTION


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
    mode: Mode | None = Field(None, description=_MODE_DESCRIPTION)
    disable: list[str] | str | None = Field(None, description=_DISABLE_DESCRIPTION)
    profile: Profile | None = Field(None, description=PROFILE_DESCRIPTION, json_schema_extra={"deprecated": True})
    label_language: LabelLanguage = "fr"
    rules: dict[str, Any] | None = Field(None, description=_RULES_DESCRIPTION)
    explain: bool = Field(False, description="Rapport : pour chaque balise, la règle et la raison (jamais la "
                                             "valeur) / per-tag rule and reason, never the value")

    def options(self) -> AnonymizeOptions:
        return _options(self.countries, self.profile, self.label_language, self.rules, self.explain,
                        mode=self.mode, disable=self.disable)


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
    result_url: str = Field(description=(
        "Route REST du résultat (GET, JSON page par page ; « ?format=markdown » : Markdown brut, sans marqueurs). "
        "Les clients MCP utilisent get_anonymized. / REST route of the result (GET, JSON pages; '?format=markdown': "
        "raw Markdown without markers). MCP clients use get_anonymized."))


class UploadAcceptedOut(BaseModel):
    """Fichier reçu (202) : le traitement continue en arrière-plan / file received (202): processing continues."""

    upload_id: str
    status: Literal["processing"] = "processing"
    stage: str = "queued"
    received_bytes: int
    retry_after_s: int
    expires_in: int = Field(description="Durée de vie du résultat après traitement, en secondes / result lifetime "
                                        "after processing, in seconds")
    next_step: str


class ResultOut(BaseModel):
    upload_id: str
    status: str
    expires_in: int
    page: int | None = None
    pages: int | None = None
    next_page: int | None = None
    page_chars: int | None = None
    total_chars: int | None = None
    deleted: bool = Field(False, description="Tout a été lu : effacé à la fin du délai de grâce (expires_in) / fully "
                                             "read: deleted when the grace period (expires_in) ends")
    kind: str | None = None
    markdown: str | None = None
    report: dict[str, Any] | None = None
    warnings: list[str] = Field(default_factory=list)
    dropped: dict[str, int] = Field(default_factory=dict)
    stage: str | None = None
    percent: int | None = None
    pages_done: int | None = None
    pages_total: int | None = None
    elapsed_s: int | None = None
    estimated_remaining_s: int | None = None
    retry_after_s: int | None = None


_PROGRESS_FIELDS = ("stage", "percent", "pages_done", "pages_total", "elapsed_s", "estimated_remaining_s",
                    "retry_after_s")


class PacksOut(BaseModel):
    packs: list[dict[str, Any]]


def _options(countries: str | list[str] | None, profile: str | None, label_language: str | None,
             rules: dict[str, Any] | str | None = None, explain: bool | str | None = False, *,
             mode: str | None = None, disable: list[str] | str | None = None) -> AnonymizeOptions:
    try:
        return AnonymizeOptions.build(countries, profile, label_language, rules, explain, mode=mode, disable=disable)
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
                                    "countries": {"type": "string"},
                                    "mode": {"type": "string", "description": _MODE_DESCRIPTION},
                                    "disable": {"type": "string", "description": "Comma-separated / séparées par "
                                                "des virgules. " + _DISABLE_DESCRIPTION},
                                    "profile": {"type": "string", "deprecated": True},
                                    "label_language": {"type": "string"},
                                    "rules": {"type": "string", "description": "JSON"},
                                    "explain": {"type": "string"}}}}}}})
    async def anonymize_file(request: Request, principal: Principal) -> DocumentOut:
        # Mémoire réservée avant la lecture du corps (admission) / memory reserved before the body is read.
        form = await service.within_deadline(read_multipart(
            request.headers.get("content-type"), request.stream(), max_file_bytes=config.max_upload_bytes))
        if set(form.fields) - _OPTION_FIELDS:
            raise InvalidRequest(f"Champ inconnu / unknown field; allowed: file, {', '.join(sorted(_OPTION_FIELDS))}")
        options = _options(form.fields.get("countries"), form.fields.get("profile"),
                           form.fields.get("label_language"), form.fields.get("rules"), form.fields.get("explain"),
                           mode=form.fields.get("mode"), disable=form.fields.get("disable"))
        result = await service.anonymize_document(form.data, form.filename or "document", options, principal)
        return DocumentOut(markdown=result.markdown, kind=result.kind, pages=result.pages, report=result.report,
                           warnings=result.warnings, dropped=result.dropped)

    @router.post("/v1/uploads", response_model=UploadTicketOut, status_code=201, tags=["uploads"])
    async def create_upload(body: UploadBody, request: Request, principal: Principal) -> UploadTicketOut:
        options = body.options()
        # Extension et règles vérifiées avant que le fichier parte / extension and rules checked before the file goes.
        check_upload_name(body.filename)
        await service.check_rules(options, principal)
        _, token = service.create_upload(principal, body.filename, options)
        base = str(request.base_url)
        upload_id = result_id(token)  # capacité de lecture, remise au seul demandeur / read capability
        return UploadTicketOut(upload_id=upload_id, upload_url=service.upload_url(base, token),
                               expires_in=int(config.upload_ttl_s), max_bytes=config.max_upload_bytes,
                               result_url=service.result_url(base, upload_id))

    @router.put("/v1/uploads/{token}", response_model=UploadAcceptedOut, status_code=202, tags=["uploads"],
                openapi_extra={"requestBody": {"required": True, "content": {"application/octet-stream": {
                    "schema": {"type": "string", "format": "binary"}}}}})
    async def receive_upload(token: str, request: Request, principal: Principal) -> JSONResponse:
        # Taille annoncée (déjà validée par l'intergiciel des corps) : un fichier trop gros est refusé avant sa
        # lecture. Declared size (already validated by the body middleware): an oversized file is refused unread.
        length = request.headers.get("content-length")
        declared = int(length) if length is not None and length.isascii() and length.isdigit() else None
        job, data = await service.accept_upload(token, principal, request.stream(), declared)
        # Recalculée du jeton présenté (le dépôt ne la garde pas) / recomputed from the token (not kept by the store).
        upload_id = result_id(token)
        retry = 2
        accepted = UploadAcceptedOut(
            upload_id=upload_id, received_bytes=len(data), retry_after_s=retry,
            expires_in=int(config.result_ttl_s),
            next_step=(f"File received; anonymisation continues in the background. MCP: call "
                       f"get_anonymized(upload_id='{upload_id}') in {retry} s, again after each retry_after_s, then "
                       f"with next_page until it is null. REST: GET /v1/results/{upload_id} (202 while processing)."))
        # 202 dès le corps reçu ; le traitement continue dans la même requête ASGI (mêmes isolement, limites, budget
        # mémoire et échéances), après la réponse. 202 once the body is in; processing continues within the same ASGI
        # request (same isolation, limits, memory budget and deadlines), after the answer.
        return JSONResponse(accepted.model_dump(), status_code=202, headers={"retry-after": str(retry)},
                            background=BackgroundTask(service.process_upload, job, data, principal,
                                                      raise_errors=False))

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
            # Pas encore prêt : étape, avancement et délai conseillé / not ready yet: stage, progress, advised delay.
            pending = {"upload_id": view.upload_id, "status": view.status, "expires_in": view.expires_in,
                       **{key: getattr(view, key) for key in _PROGRESS_FIELDS}}
            return JSONResponse(pending, status_code=202, headers={"retry-after": str(view.retry_after_s or 1)})
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
