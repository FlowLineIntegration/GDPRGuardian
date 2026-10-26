"""Cœur du service, partagé par l'API REST et les serveurs MCP / service core shared by the REST API and MCP servers.

Chaque requête est traitée de bout en bout dans un processus isolé à usage unique (`isolation`), règles de
l'organisation comprises ; ce processus-ci ne fait que l'admission, l'ordonnancement équitable et le dépôt des
résultats, et ne lit, ne compile ni n'anonymise jamais un contenu. Toute exception tierce devient une
`ServiceError` sans reprendre son message. Every request is processed end to end in a single-use isolated
process, organisation rules included; this process only does admission, fair scheduling and the result store,
and never parses, compiles nor anonymises content. Any third-party exception becomes a `ServiceError` without
its message.
"""

from __future__ import annotations

import logging
import sys
import time
from collections.abc import AsyncIterable, Awaitable, Callable
from dataclasses import dataclass, replace
from functools import cached_property
from time import perf_counter
from typing import Any, TypeVar

import anyio
import anyio.to_thread

from ..convert._base import CRASH_MESSAGE
from ..convert._sandbox import Body, CancelHandle, WorkerStartError
from ..documents import ConversionTimeoutError, DocumentError, DocumentOptions, DocumentResult, DocumentTooLargeError
from ..packs import available_packs, load_pack
from .admission import FairScheduler, MemoryBudget
from .clients import REQUEST, ClientIdentifier, Pseudonymizer
from .config import MAX_PAGE_CHARS, MIN_PAGE_CHARS, MULTIPART_ENVELOPE_BYTES, ServerConfig
from .errors import (
    ConverterUnavailable,
    InvalidRequest,
    PayloadTooLarge,
    ProcessingTimeout,
    RulesTooCostly,
    ServiceBusy,
    ServiceError,
    UploadTimeout,
    file_too_large,
    from_document_error,
    text_too_long,
)
from .filenames import neutral_filename
from .isolation import (
    INVALID_RULES,
    InlineRunner,
    IsolatedRunner,
    JobError,
    deadline_s,
    decode_document,
    decode_text,
    document_reply_limit,
    document_spec,
    reported_cpu_s,
    text_reply_limit,
    text_spec,
)
from .limiter import Limiter
from .logs import log_event
from .options import AnonymizeOptions
from .store import Job, JobStore, Quota, ResultPage
from .usage import FILE, PUBLIC, TEXT, UPLOAD, UsageReporter, usage_format

T = TypeVar("T")
# Champs du rapport utiles à un LLM (le reste coûte des jetons) ; les avertissements du moteur (« noms détectés par
# les lexiques français seulement ») en font partie. Report fields useful to an LLM; engine warnings included.
_SUMMARY_KEYS = ("entities", "total_replaced", "kept_by_policy", "countries", "language", "irreversible", "notice",
                 "warnings", "rules", "explain")
# Fils d'attente au-delà des places : un travailleur tué rend sa place avant que son fil ne finisse.
# Waiting threads beyond the slots: a killed worker frees its slot before its thread ends.
_SPARE_THREADS = 8
# Sortie réservée avant le travailleur : deux réponses maximales (la trame lue, puis le texte décodé et sa copie
# JSON). Output reserved before the worker: two maximal replies (the frame read, then the decoded text and its JSON
# copy).
_OUTPUT_COPIES = 2
# Sonde profonde : un travail minuscule dans un vrai travailleur, hors file / deep probe: a tiny job, outside the queue.
_DEEP_HEALTH_TIMEOUT_S = 20.0
_DEEP_HEALTH_TEXT = "Jean Martin, jean.martin@exemple.fr"


@dataclass(slots=True, frozen=True)
class TextResult:
    """Texte anonymisé et rapport / anonymised text and report."""

    text: str
    report: dict[str, Any]


class Service:
    """Anonymisation, envois hors bande et résultats paginés / anonymisation, out-of-band uploads, paged results.

    À utiliser depuis une seule boucle d'événements / to be used from a single event loop.
    """

    def __init__(self, config: ServerConfig, *, clock: Callable[[], float] = time.monotonic) -> None:
        config.validate()
        self.config = config
        longest_job_s = deadline_s(config.conversion_timeout_s, config.max_upload_bytes)
        self.store = JobStore(
            upload_ttl_s=config.upload_ttl_s, result_ttl_s=config.result_ttl_s,
            processing_ttl_s=config.result_ttl_s + longest_job_s,
            max_active_per_principal=config.max_active_per_principal, max_jobs=config.max_jobs,
            max_chars=config.max_store_chars, max_per_prefix=config.max_uploads_per_prefix,
            max_pending=config.max_pending, clock=clock,
        )
        # Clés configurées ; service public : clients sans nombre fixe / configured keys; public: no fixed number.
        principals = (None if config.public else
                      1 if config.dev_no_auth else len(config.api_keys) + len(config.api_key_sha256) + 1)
        self.budget = MemoryBudget(config.queue_bytes, reserve=max(config.queue_bytes // 4, config.largest_request),
                                   principals=principals)
        # Politique appliquée : dette couvrant le plus long travail, préfixe borné à la moitié des places non
        # réservées. Applied policy: debt covering the longest job, prefix capped at half the non-reserved slots.
        limits = config.limits.for_service(slots=config.max_concurrency, longest_job_s=longest_job_s)
        self.limits = limits
        self.scheduler = FairScheduler(config.max_concurrency, reserved=limits.reserved_slots)
        # Identité des clients (pseudonymes en mémoire) et limiteur d'abus / client identity and abuse limiter.
        self.clients = ClientIdentifier(config.client_ip_header,
                                        Pseudonymizer(rotate_s=limits.rotate_s, grace_s=limits.grace_s, clock=clock),
                                        local_token_sha256=config.local_token_sha256)
        self.limiter = Limiter(limits, estimated_wait=self.scheduler.estimated_wait,
                               typical_job_s=lambda: self.scheduler.typical_job_s, clock=clock)
        self.runner: IsolatedRunner | InlineRunner = (
            IsolatedRunner(config.worker_memory_mb, config.prewarm_workers) if config.isolation else InlineRunner())
        self._threads = anyio.CapacityLimiter(config.max_concurrency + _SPARE_THREADS)
        # En isolation, le travailleur est le bac à sable : pas de second processus de conversion. Le délai interne des
        # convertisseurs est celui de la requête (posé par document), les pages suivent la limite du service.
        # Under isolation, the worker is the sandbox: no second conversion process. The converters' inner deadline is
        # the request's (set per document); pages follow the service's limit.
        self._document_options = DocumentOptions(max_bytes=config.max_upload_bytes,
                                                 timeout_s=config.conversion_timeout_s,
                                                 sandbox=not config.isolation, max_pages=config.max_pages)
        # Compteur d'usage : un datagramme de métadonnées par anonymisation, depuis ce processus seulement.
        # Usage counter: one metadata datagram per anonymisation, from this process only.
        self.usage = UsageReporter(config.usage_socket)

    # --- travailleurs / workers ---

    def start_workers(self) -> None:
        """Prépare zygote et réserve en arrière-plan (non bloquant) / prepares zygote and reserve (non-blocking)."""
        self.runner.start()

    def stop_workers(self) -> None:
        """Arrête tous les travailleurs (bloquant, court) / stops every worker (blocking, short)."""
        self.runner.stop()

    # --- garde-fous / guards ---

    async def within_deadline(self, reader: Awaitable[T], size: int | None = None) -> T:
        """Lecture d'un corps sous délai (client trop lent), filet derrière celui de l'intergiciel des corps.

        Body read under a deadline (slow client), a safety net behind the body middleware's own. `size` : taille
        maximale du corps (défaut : le plus gros envoi) / largest body size (default: the largest upload).
        """
        limit = self.config.max_upload_bytes + MULTIPART_ENVELOPE_BYTES if size is None else size
        try:
            with anyio.fail_after(self.config.body_deadline_s(limit)):
                return await reader
        except TimeoutError:
            raise UploadTimeout from None

    def retry_after(self) -> int:
        """Délai conseillé à un client refusé (503) / delay advised to a refused client."""
        return self.scheduler.retry_after()

    async def _process(self, principal: str, payload: bytes | bytearray, spec: str, timeout_s: float,
                       max_reply: int, on_start: Callable[[], None] | None = None) -> tuple[Any, float]:
        """Attend son tour (équitable par clé), puis un travailleur traite la requête / waits its turn, then runs.

        `on_start` : appelé à l'attribution de la place, avant le travailleur ; une erreur l'annule.
        `on_start`: called when the slot is granted, before the worker; raising cancels the work.
        Requête annulée (client parti) : elle quitte la file, ou son travailleur est tué.
        Cancelled request (client gone): it leaves the queue, or its worker is killed.

        Le ticket du limiteur (contexte de la requête) borne la place (client, préfixe, place réservée) et reçoit
        le temps de travailleur mesuré, qui corrige l'estimation. La réservation de la requête (budget mémoire)
        prend, avant le travailleur, la place de la plus grande réponse possible ; budget épuisé : 503 sans
        travailleur. The limiter ticket (request context) constrains the slot (client, prefix, reserved slot) and
        receives the measured worker time, which trues up the estimate. The request's reservation (memory budget)
        takes, before the worker, room for the largest possible reply; budget exhausted: 503 without a worker.
        """
        context = REQUEST.get()
        ticket = context.ticket if context is not None else None
        reservation = context.reservation if context is not None else None
        queued = perf_counter()
        async with self.scheduler.slot(principal, ticket, timeout_s):
            waited_ms = (perf_counter() - queued) * 1000
            if reservation is not None and not reservation.reserve_output(_OUTPUT_COPIES * max_reply):
                log_event("output_refused", logging.DEBUG, bytes=_OUTPUT_COPIES * max_reply)
                raise ServiceBusy(retry_after=self.retry_after())
            if on_start is not None:
                on_start()
            if ticket is not None:
                ticket.worked = True
            cancel = CancelHandle()
            started = perf_counter()
            value: Any = None
            try:
                value = await anyio.to_thread.run_sync(self.runner.run, payload, spec, timeout_s, max_reply, cancel,
                                                       abandon_on_cancel=True, limiter=self._threads)
            except anyio.get_cancelled_exc_class():
                cancel.cancel()
                raise
            finally:
                if ticket is not None:
                    # Occupation de la place, mesurée ici, ou temps processeur rapporté s'il est plus grand.
                    # Slot occupancy measured here, or the reported CPU time if larger.
                    ticket.measured += max(perf_counter() - started, reported_cpu_s(value))
                if reservation is not None:
                    # Ramenée à ce que la réponse tient vraiment / brought down to what the answer really holds.
                    reservation.shrink_output(_held_bytes(value))
        return value, waited_ms

    @staticmethod
    def _src() -> str:
        """Provenance pour le compteur d'usage / provenance for the usage counter."""
        context = REQUEST.get()
        return PUBLIC if context is None else context.client.src

    # --- anonymisation ---

    async def anonymize_text(self, text: str, options: AnonymizeOptions, principal: str, *,
                             usage: str = TEXT) -> TextResult:
        """`usage` : origine pour le compteur d'usage (`usage.KINDS`) / origin for the usage counter.

        Compté (un datagramme, réussite ou échec) dès que le texte est accepté pour traitement ; un texte refusé
        à l'entrée (trop long, substitut isolé) ne l'est pas. Counted (one datagram, success or failure) once
        the text is accepted for processing; a text refused at the door (too long, lone surrogate) is not.
        """
        if len(text) > self.config.max_text_chars:
            raise text_too_long(self.config.max_text_chars)
        payload = _utf8(text)
        if payload is None:
            # JSON admet « \ud800 » seul ; la réponse ne serait pas encodable / lone surrogates break the reply.
            raise InvalidRequest("Texte invalide : substitut UTF-16 isolé / invalid text: lone surrogate",
                                 code="invalid_text")
        started = perf_counter()
        cap = self.config.max_output_chars
        with self.usage.measure(usage, len(payload), "text", self._src()) as measure:
            try:
                value, waited_ms = await self._process(principal, payload, text_spec(options, cap),
                                                       deadline_s(self.config.conversion_timeout_s, len(payload)),
                                                       text_reply_limit(len(text), cap))
                outcome = decode_text(value)
            except ServiceError:
                raise  # place ou budget refusés avant le travailleur / slot or budget refused before the worker
            except DocumentTooLargeError as exc:
                # Résultat au-delà du plafond, ou mémoire du travailleur épuisée : la limite est nommée.
                # Result over the cap, or the worker's memory exhausted: the limit is named.
                raise PayloadTooLarge(from_document_error(exc, max_output_chars=cap).message) from None
            except ConversionTimeoutError:
                # Échéance dépassée : même réponse au prochain essai, donc 422 comme un document / same next time.
                # Deadline exceeded: the same outcome next time, hence 422 like a document.
                log_event("text_rejected", logging.DEBUG, code=ProcessingTimeout.code, chars=len(text))
                raise ProcessingTimeout from None
            except WorkerStartError:
                raise ServiceBusy(retry_after=self.retry_after()) from None
            except JobError as exc:
                if exc.code == INVALID_RULES and options.rules is not None:
                    raise _rules_refused(exc.message, "text") from None
                raise _internal_error(exc.error_type, "text") from None
            except DocumentError as exc:
                if options.rules is not None and _crashed(exc):
                    # Filet de sécurité : sans convertisseur, la cause probable est le coût des règles du client.
                    # Safety net: with no converter involved, the likely cause is the cost of the client's rules.
                    log_event("text_rejected", logging.DEBUG, code=RulesTooCostly.code, chars=len(text))
                    raise RulesTooCostly from None
                raise _internal_error("worker_failure", "text") from None
            except Exception as exc:
                raise _internal_error(type(exc).__name__.lower(), "text") from None
            report = _strip_internals(outcome.meta["report"])
            log_event("text_anonymized", logging.DEBUG, chars=len(text), replaced=report.get("total_replaced"),
                      ms=(perf_counter() - started) * 1000, wait_ms=waited_ms, worker=outcome.worker)
            measure.ok = True
        return TextResult(outcome.text, report)

    async def anonymize_document(self, data: bytes | bytearray, filename: str, options: AnonymizeOptions,
                                 principal: str, on_start: Callable[[], None] | None = None, *,
                                 usage: str = FILE) -> DocumentResult:
        """`on_start` : voir `_process` (envoi hors bande : départ de son délai) / see `_process`.

        `usage` : origine pour le compteur d'usage ; une réussite y donne le format détecté, un échec le format
        de l'extension déclarée. `usage`: origin for the usage counter; a success reports the detected format,
        a failure the declared extension's format.
        """
        started = perf_counter()
        size = len(data)
        name = neutral_filename(filename)  # « document.pdf » ou « document »
        with self.usage.measure(usage, size, usage_format(name.partition(".")[2]), self._src()) as measure:
            cap = self.config.max_output_chars
            try:
                deadline = deadline_s(self.config.conversion_timeout_s, size)
                # Délai interne des convertisseurs et tableurs = échéance de la requête : un gros classeur n'est plus
                # coupé à 60 s quand son travailleur a droit à davantage. Converters' and spreadsheets' inner deadline
                # = the request's: a big workbook is no longer cut at 60 s while its worker may run longer.
                spec = document_spec(options, name, replace(self._document_options, timeout_s=deadline), cap)
                value, waited_ms = await self._process(principal, data, spec, deadline, document_reply_limit(cap),
                                                       on_start)
                result, worker = decode_document(value)
            except ServiceError:
                raise  # déjà une erreur de service (envoi supprimé pendant l'attente) / already a service error
            except WorkerStartError:
                raise ServiceBusy(retry_after=self.retry_after()) from None
            except DocumentError as exc:
                error = from_document_error(exc, max_output_chars=cap)
                log_event("document_rejected", logging.DEBUG, code=error.code, bytes=size)
                raise error from None
            except JobError as exc:
                if exc.code == INVALID_RULES and options.rules is not None:
                    raise _rules_refused(exc.message, "document") from None
                if exc.code != "converter_unavailable":
                    raise _internal_error(exc.error_type, "document") from None
                log_event("document_rejected", logging.DEBUG, code=ConverterUnavailable.code, bytes=size)
                raise ConverterUnavailable from None
            except Exception as exc:
                raise _internal_error(type(exc).__name__.lower(), "document") from None
            result.report = _strip_internals(result.report)
            log_event("document_anonymized", logging.DEBUG, kind=result.kind, bytes=size, chars=len(result.markdown),
                      replaced=result.report.get("total_replaced"), ms=(perf_counter() - started) * 1000,
                      wait_ms=waited_ms, worker=worker)
            measure.fmt = usage_format(result.kind)
            measure.ok = True
        return result

    # --- envois hors bande / out-of-band uploads ---

    def create_upload(self, principal: str, filename: str, options: AnonymizeOptions, *,
                      usage: str = UPLOAD) -> tuple[Job, str]:
        """Réserve un envoi. Les motifs des règles ne sont compilés qu'au traitement, dans le travailleur : un
        motif refusé fait échouer l'envoi (422 au PUT, puis à la lecture du résultat). `usage` : origine
        comptée au traitement (REST ou MCP).

        Reserves an upload. Rule patterns are only compiled at processing time, in the worker: a refused pattern
        fails the upload (422 on the PUT, then when the result is read). `usage`: origin counted at processing.

        Lié au principal s'il vient d'une clé (ou hors requête HTTP : poste local) ; client anonyme du service
        public : la capacité seule donne accès, le quota reste compté pour lui. Bound to the principal when it comes
        from a key (or outside an HTTP request: local computer); anonymous public client: the capability alone
        grants access, the quota still counts for it.
        """
        context = REQUEST.get()
        bound = context is None or context.client.owner is not None
        # Seule l'extension est conservée, même temporairement / only the extension is kept, even transiently.
        job, token = self.store.create(principal, neutral_filename(filename), options, usage=usage, bound=bound,
                                       quota=_quota(principal))
        log_event("upload_created", logging.DEBUG)
        return job, token

    async def receive_upload(self, token: str, principal: str, chunks: AsyncIterable[bytes],
                             declared: int | None = None) -> tuple[Job, DocumentResult]:
        """Consomme le jeton, lit le corps borné puis anonymise / consumes the token, reads, anonymises.

        Un service saturé répond 503 avant (admission), un client du PUT au-delà de ses quotas 429 : le jeton n'est
        pas consommé. A saturated service answers 503 before (admission), a PUT client beyond its quotas 429: the
        token is not burned. Quotas du résultat comptés pour le client du PUT (la machine de l'utilisateur), pas pour
        celui qui a créé l'envoi (souvent un connecteur MCP partagé). Result quotas count against the PUT's client
        (the user's machine), not the upload's creator (often a shared MCP connector). `declared` : taille annoncée
        (Content-Length) ; au-delà de la limite, refus aussitôt, sans lire le corps, échec noté pour le lecteur du
        résultat. `declared`: announced size; over the limit, refused at once without reading the body, the failure
        recorded for the result's reader.
        """
        context = REQUEST.get()
        reservation = context.reservation if context is not None else None
        # Sortie réservée avant de consommer le jeton : un budget plein répond 503 et l'URL reste valable.
        # Output reserved before burning the token: a full budget answers 503 and the URL stays valid.
        if reservation is not None and not reservation.reserve_output(
                _OUTPUT_COPIES * document_reply_limit(self.config.max_output_chars)):
            raise ServiceBusy(retry_after=self.retry_after())
        job = self.store.claim(token, principal, quota=_quota(principal))
        try:
            if declared is not None and declared > self.config.max_upload_bytes:
                raise file_too_large(self.config.max_upload_bytes)
            data = await self.within_deadline(read_limited(chunks, self.config.max_upload_bytes))
            # L'attente en file ne compte pas dans le délai de traitement / time queued does not count.
            result = await self.anonymize_document(data, job.filename, job.options, principal,
                                                   on_start=lambda: self.store.start(job), usage=job.usage)
            self.store.complete(job, result)
        except ServiceError as error:
            self.store.fail(job, error)
            raise
        except BaseException:
            # Client parti ou annulation : l'envoi est perdu / client gone or cancelled: upload lost.
            self.store.fail(job, InvalidRequest("Envoi interrompu / upload interrupted", code="upload_interrupted"))
            raise
        return job, result

    def read_result(self, principal: str, upload_id: str, page: int, page_chars: int | None) -> ResultPage:
        page_chars = page_chars or self.config.page_chars
        if not MIN_PAGE_CHARS <= page_chars <= MAX_PAGE_CHARS:
            raise InvalidRequest(f"page_chars ∈ [{MIN_PAGE_CHARS}, {MAX_PAGE_CHARS}]")
        view = self.store.read(upload_id, principal, page, page_chars)
        if view.page is not None:
            log_event("result_read", logging.DEBUG, page=view.page, pages=view.pages, deleted=view.deleted)
        return view

    async def deep_health(self) -> bool:
        """Un travail minuscule dans un vrai travailleur, hors file et sans compteur d'usage : la chaîne zygote,
        travailleur et moteur répond-elle ? Réservé au serveur lui-même (la sonde de l'hôte).

        A tiny job in a real worker, outside the queue and without a usage datagram: does the zygote, worker and
        engine chain answer? For the server itself only (the host's probe).
        """
        options = AnonymizeOptions()
        cap = self.config.max_output_chars
        payload = _DEEP_HEALTH_TEXT.encode()
        cancel = CancelHandle()
        try:
            with anyio.fail_after(_DEEP_HEALTH_TIMEOUT_S):
                value = await anyio.to_thread.run_sync(self.runner.run, payload, text_spec(options, cap),
                                                       _DEEP_HEALTH_TIMEOUT_S, text_reply_limit(len(payload), cap),
                                                       cancel, abandon_on_cancel=True)
            outcome = decode_text(value)
        except anyio.get_cancelled_exc_class():
            cancel.cancel()
            raise
        except Exception as exc:
            cancel.cancel()
            log_event("deep_health_failed", logging.WARNING, error=type(exc).__name__.lower())
            return False
        return "jean.martin@exemple.fr" not in outcome.text

    def status(self) -> dict[str, Any]:
        """État agrégé, sans rien d'un client / aggregate state, nothing about any client."""
        scheduler = self.scheduler
        return {"status": "ok", "public": self.config.public, "limits": self.limiter.mode,
                "workers": {"slots": scheduler.slots, "reserved_small": scheduler.reserved, "busy": scheduler.busy,
                            "waiting": scheduler.waiting},
                "estimated_wait_s": round(scheduler.estimated_wait("", True), 1),
                "counters": self.limiter.stats()}

    def upload_url(self, base_url: str, token: str) -> str:
        return f"{(self.config.public_url or base_url).rstrip('/')}/v1/uploads/{token}"

    def result_url(self, base_url: str, upload_id: str) -> str:
        return f"{(self.config.public_url or base_url).rstrip('/')}/v1/results/{upload_id}"

    # --- catalogue / catalogue ---

    @cached_property
    def packs(self) -> list[dict[str, Any]]:
        """Description des packs pays (sans donnée personnelle) / country-pack description."""
        catalogue = []
        for pack_id in available_packs():
            pack = load_pack(pack_id)
            catalogue.append({
                "id": pack.id, "name": pack.name, "version": pack.version, "country": pack.country,
                "always_on": pack.always_on, "languages": list(pack.languages),
                "entities": sorted({r.entity for r in pack.recognizers}),
                "recognizers": [{"id": r.id, "entity": r.entity, "label": r.label, "tier": r.tier}
                                for r in pack.recognizers],
                "detectors": [spec.rsplit(":", 1)[-1] for spec in pack.detector_specs],
            })
        return catalogue


# Mesures internes jamais renvoyées : elles décrivent le service, pas le document.
# Internal measurements never returned: they describe the service, not the document.
_INTERNAL_KEYS = ("timings_ms",)


def _strip_internals(report: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in report.items() if key not in _INTERNAL_KEYS}


def _held_bytes(value: Any) -> int:
    """Octets qu'une réponse de travailleur tient encore jusqu'à la fin de la requête : le texte décodé, sa copie
    JSON et ses octets UTF-8 (au plus 4 par caractère). Bytes a worker reply still holds until the request ends: the
    decoded text, its JSON copy and its UTF-8 bytes (at most 4 per character)."""
    text = value.text if isinstance(value, Body) else None
    return 2 * sys.getsizeof(text) + 4 * len(text) if isinstance(text, str) else 0


def _quota(principal: str) -> Quota:
    """Clés de quota du client de la requête en cours (préfixe réseau compris), sinon le principal seul.

    Quota keys of the current request's client (network prefix included), else the principal alone.
    """
    context = REQUEST.get()
    client = context.client if context is not None else None
    if client is None or client.principal != principal:
        return Quota(principal)
    return Quota(principal, client.prefix_key)


def summarize_report(report: dict[str, Any]) -> dict[str, Any]:
    """Rapport compact pour un LLM / compact report for an LLM."""
    return {key: report[key] for key in _SUMMARY_KEYS if key in report}


def _utf8(text: str) -> bytes | None:
    """UTF-8 strict ; None pour un substitut isolé (l'erreur, qui cite le texte, n'est pas gardée).

    Strict UTF-8; None for a lone surrogate (the error, which quotes the text, is not kept).
    """
    try:
        return text.encode("utf-8")
    except UnicodeEncodeError:
        return None


async def read_limited(chunks: AsyncIterable[bytes], limit: int) -> bytearray:
    """Lit un flux en mémoire avec une limite stricte, sans copie finale / reads a stream with a hard limit."""
    buffer = bytearray()
    async for chunk in chunks:
        if len(buffer) + len(chunk) > limit:
            raise file_too_large(limit)
        buffer += chunk
    return buffer


def _internal_error(error: str, stage: str) -> ServiceError:
    # Type d'exception seulement : son message pourrait citer le document / type only, the message may quote data.
    log_event("internal_error", logging.ERROR, stage=stage, error=error)
    return ServiceError()


def _rules_refused(reason: str, stage: str) -> InvalidRequest:
    """Règles refusées par le travailleur : le même 422 qu'une option invalide, raison du moteur comprise.

    Rules refused by the worker: the same 422 as an invalid option, with the engine's reason. La raison n'est
    jamais journalisée (un motif peut contenir un nom) / the reason is never logged (a pattern may hold a name).
    """
    log_event(f"{stage}_rejected", logging.DEBUG, code=INVALID_RULES)
    return InvalidRequest(f"Option invalide / invalid option: {reason}")


def _crashed(error: DocumentError) -> bool:
    """Travailleur mort en cours de travail (ni refus du document ni échéance) / worker died mid-job."""
    return type(error) is DocumentError and str(error) == CRASH_MESSAGE
