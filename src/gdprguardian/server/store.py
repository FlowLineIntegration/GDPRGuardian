"""Dépôt en mémoire des envois et des résultats, à durée de vie courte / short-lived in-memory upload and result store.

Isolation par conception : un résultat différé n'est joignable que par sa capacité. Isolation by design: a deferred
result is only reachable through its capability.

- Jeton d'envoi et identifiant de résultat : 256 bits aléatoires (le second dérivé du premier à sens unique), remis
  au seul demandeur, gardés ici en empreintes SHA-256 seulement ; aucune route ne liste quoi que ce soit.
- Le jeton ne sert qu'une fois. Faux, expiré ou déjà utilisé : la même réponse (404, `not_found`).
- Un envoi créé avec une clé d'API reste en plus lié à cette clé ; dans le service public (sans clé), la capacité
  seule donne accès.
- Quotas (`Quota` : le client et son préfixe réseau). En attente du fichier : par préfixe du créateur (40), ou par
  principal sans réseau (10), et 10 000 en tout. Reçus et non lus : par client du PUT (10) et son préfixe (40), 1 000
  en tout ; leurs caractères : 1/8 du dépôt par client du PUT, 1/4 par préfixe. Le PUT part de la machine de
  l'utilisateur : un connecteur distant ou un NAT partagé par beaucoup n'est pas bloqué par le quota d'un seul.
- Un résultat est effacé dès que toutes ses pages ont été lues, ou à expiration.
- Un envoi reçu qui attend son travailleur n'expire pas : sa requête le termine (résultat ou échec), et son délai de
  traitement ne part qu'à l'attribution du travailleur (`start`).
- Rien n'est écrit sur disque ; l'effacement de la mémoire est « au mieux » (CPython).

Upload token and result id: 256 random bits (the second derived one-way from the first), handed to the requester
alone, kept here as SHA-256 digests only; no route lists anything. The token works once. Wrong, expired or already
used: the same answer. An upload created with an API key is also bound to that key; in the public service (no key)
the capability alone grants access. Quotas (the client and its network prefix): pending uploads per creator prefix
(40), or per network-less principal (10), 10,000 in all; received and unread ones per PUT client (10) and its prefix
(40), 1,000 in all; their characters: 1/8 of the store per PUT client, 1/4 per prefix. The PUT comes from the user's
machine: a remote connector or a NAT shared by many is not stuck with one client's quota. A result is deleted once
every page has been read, or on expiry. A received upload waiting for its worker does not expire. Nothing touches
the disk; memory wiping is best effort (CPython).
"""

from __future__ import annotations

import hashlib
import heapq
import itertools
import math
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from ..documents import DocumentResult
from .config import STORE_CLIENT_SHARE, STORE_PREFIX_SHARE
from .errors import InvalidRequest, NotFound, QuotaExceeded, ResultsQuotaExceeded, ServiceBusy, ServiceError
from .options import AnonymizeOptions
from .pagination import merge_interval, page_bounds
from .security import issue_upload_token, result_digest, result_id, same_digest, token_digest
from .usage import KINDS, UPLOAD

_MAX_PAGE_SIZES = 4


@dataclass(slots=True, frozen=True)
class Quota:
    """Clés de quota d'un client : lui-même et, client réseau, son préfixe (/24, /48) / a client's quota keys.

    `client` : le principal (« c_… », « k_… », LOCAL…) ; `prefix` : « p_… », None hors réseau. Pseudonymes
    seulement, jamais une adresse. `client`: the principal; `prefix`: "p_…", None without a network. Pseudonyms
    only, never an address.
    """

    client: str
    prefix: str | None = None


class JobState(StrEnum):
    PENDING = "pending"          # en attente du fichier / waiting for the file
    PROCESSING = "processing"    # conversion et anonymisation / converting and anonymising
    READY = "ready"
    FAILED = "failed"


@dataclass(slots=True, eq=False)
class Job:
    """Un envoi ; ni le jeton ni l'identifiant de résultat en clair / an upload; neither capability in clear.

    `owner` : principal à clé auquel l'envoi est lié (None : capacité seule). `pending_key` : clé de quota qui compte
    l'envoi tant qu'il attend son fichier (préfixe du créateur, ou son principal) ; `holders` : clés qui le comptent
    ensuite, résultat compris (client du PUT, puis son préfixe). `owner`: keyed principal the upload is bound to
    (None: capability only). `pending_key`: quota key counting the upload while it waits for its file (the creator's
    prefix, or its principal); `holders`: keys counting it afterwards, result included (the PUT's client, then its
    prefix).
    """

    result_digest: bytes = field(repr=False)
    owner: str | None
    pending_key: str | None = field(repr=False)
    filename: str = field(repr=False)
    options: AnonymizeOptions
    expires_at: float
    token_digest: bytes | None = field(default=None, repr=False)
    holders: tuple[str, ...] = field(default=(), repr=False)
    state: JobState = JobState.PENDING
    # Reçu, en attente d'un travailleur : n'expire pas (sa requête le termine) / received, awaiting a worker.
    waiting: bool = False
    result: DocumentResult | None = field(default=None, repr=False)
    error: ServiceError | None = None
    served: list[tuple[int, int]] = field(default_factory=list)
    bounds: dict[int, list[int]] = field(default_factory=dict, repr=False)
    # Origine pour le compteur d'usage (`usage.KINDS`), valeur fermée / origin for the usage counter, closed value.
    usage: str = UPLOAD


@dataclass(slots=True, frozen=True)
class ResultPage:
    """Vue d'une page de résultat / one page of a result."""

    upload_id: str
    status: str
    expires_in: int
    page: int | None = None
    pages: int | None = None
    next_page: int | None = None
    page_chars: int | None = None
    total_chars: int | None = None
    markdown: str | None = None
    kind: str | None = None
    report: dict[str, Any] | None = None
    warnings: list[str] | None = None
    dropped: dict[str, int] | None = None
    deleted: bool = False


class JobStore:
    """Dépôt sûr entre threads ; expiration par tas, O(log n) / thread-safe store; heap-based expiry."""

    def __init__(self, *, upload_ttl_s: float, result_ttl_s: float, processing_ttl_s: float,
                 max_active_per_principal: int, max_jobs: int, max_chars: int, max_per_prefix: int = 40,
                 max_pending: int = 10_000, clock: Callable[[], float] = time.monotonic) -> None:
        self._upload_ttl = upload_ttl_s
        self._result_ttl = result_ttl_s
        self._processing_ttl = processing_ttl_s
        self._max_active = max_active_per_principal
        self._max_per_prefix = max_per_prefix
        self._max_jobs = max_jobs
        self._max_pending = max_pending
        self._max_chars = max_chars
        self._clock = clock
        self._lock = threading.Lock()
        # Clés : empreintes des capacités, jamais les capacités / keys: capability digests, never the capabilities.
        self._jobs: dict[bytes, Job] = {}
        self._tokens: dict[bytes, bytes] = {}
        # Comptes par clé de quota (pseudonymes) / counts per quota key (pseudonyms).
        self._pending: dict[str, int] = {}
        self._active: dict[str, int] = {}
        self._held_chars: dict[str, int] = {}
        self._pending_total = 0
        self._chars = 0
        self._heap: list[tuple[float, int, bytes]] = []
        self._seq = itertools.count()

    # --- cycle de vie / lifecycle ---

    def create(self, principal: str, filename: str, options: AnonymizeOptions, *, usage: str = UPLOAD,
               bound: bool = True, quota: Quota | None = None) -> tuple[Job, str]:
        """Réserve un envoi ; renvoie le travail et le jeton en clair (seule copie, l'identifiant de résultat en
        dérive : `security.result_id`). `bound` : lié à `principal` (clé d'API, poste local), sinon la capacité seule
        donne accès. `quota` : clés du créateur (défaut : `principal` seul) ; l'attente du fichier compte pour son
        préfixe réseau s'il en a un, sinon pour lui.

        Reserves an upload; returns the job and the plain token (the only copy; the result id derives from it).
        `bound`: bound to `principal`, else the capability alone grants access. `quota`: the creator's keys (default:
        `principal` alone); the wait for the file counts against its network prefix when it has one, else itself.
        """
        if usage not in KINDS:
            raise ValueError("usage inconnu / unknown usage")
        quota = quota or Quota(principal)
        key = quota.prefix or quota.client
        cap = self._max_per_prefix if quota.prefix is not None else self._max_active
        with self._lock:
            now = self._purge()
            if self._pending.get(key, 0) >= cap:
                raise QuotaExceeded
            if self._pending_total >= self._max_pending:
                raise ServiceBusy
            token, digest = issue_upload_token()
            capability = hashlib.sha256(result_id(token).encode("ascii")).digest()
            job = Job(capability, principal if bound else None, key, filename, options,
                      now + self._upload_ttl, digest, usage=usage)
            self._jobs[capability] = job
            self._tokens[digest] = capability
            _add(self._pending, key, 1)
            self._pending_total += 1
            self._schedule(job)
            return job, token

    def claim(self, token: str, principal: str, *, quota: Quota | None = None) -> Job:
        """Consomme le jeton (usage unique) / consumes the single-use token.

        Faux, expiré, d'une autre clé ou déjà utilisé : la même erreur. Jeton valable mais client du PUT (`quota`,
        défaut `principal`) au-delà de ses quotas : 429 ou 503, jeton intact. Le travail attend ensuite son travailleur
        sans expirer : la lecture du corps est bornée par la requête (408), la file est équitable. Wrong, expired,
        another key's or already used: the same error. Valid token but the PUT's client beyond its quotas: 429 or 503,
        token kept. The job then waits for its worker without expiring.
        """
        digest = token_digest(token)
        quota = quota or Quota(principal)
        with self._lock:
            now = self._purge()
            capability = self._tokens.get(digest) if digest is not None else None
            job = self._jobs.get(capability) if capability is not None else None
            if (job is None or not same_digest(job.token_digest or b"", digest or b"")
                    or not self._allowed(job, principal) or job.state is not JobState.PENDING):
                raise NotFound
            holders = (quota.client,) if quota.prefix is None else (quota.client, quota.prefix)
            for key, cap, share in zip(holders, (self._max_active, self._max_per_prefix),
                                       (STORE_CLIENT_SHARE, STORE_PREFIX_SHARE), strict=False):
                if self._active.get(key, 0) >= cap:
                    raise QuotaExceeded
                if self._held_chars.get(key, 0) >= self._max_chars // share:
                    raise ResultsQuotaExceeded
            if len(self._jobs) - self._pending_total >= self._max_jobs:
                raise ServiceBusy
            self._release_pending(job)
            for key in holders:
                _add(self._active, key, 1)
            job.holders = holders
            job.state = JobState.PROCESSING
            job.waiting = True
            job.expires_at = now + self._processing_ttl
            self._schedule(job)
            return job

    def start(self, job: Job) -> None:
        """Un travailleur prend l'envoi : son délai de traitement part de maintenant (l'attente ne compte pas).

        A worker takes the upload: its processing delay starts now (time queued does not count). NotFound
        si l'envoi a été supprimé entre-temps : aucun travailleur n'est alors occupé pour rien / NotFound
        when the upload was deleted meanwhile: no worker is then busy for nothing.
        """
        with self._lock:
            now = self._purge()
            if self._jobs.get(job.result_digest) is not job or job.state is not JobState.PROCESSING:
                raise NotFound
            job.waiting = False
            job.expires_at = now + self._processing_ttl
            self._schedule(job)

    def complete(self, job: Job, result: DocumentResult) -> None:
        """Publie le résultat / publishes the result.

        NotFound si expiré entre-temps, ServiceBusy si le dépôt est plein, ResultsQuotaExceeded si le client du PUT
        (ou son préfixe) dépasserait sa part. NotFound if expired meanwhile, ServiceBusy when the store is full,
        ResultsQuotaExceeded when the PUT's client (or its prefix) would exceed its share.
        """
        with self._lock:
            now = self._purge()
            if self._jobs.get(job.result_digest) is not job:
                raise NotFound
            size = len(result.markdown)
            error: ServiceError | None = ServiceBusy() if self._chars + size > self._max_chars else None
            for key, share in zip(job.holders, (STORE_CLIENT_SHARE, STORE_PREFIX_SHARE), strict=False):
                if error is None and self._held_chars.get(key, 0) + size > self._max_chars // share:
                    error = ResultsQuotaExceeded()
            if error is not None:
                self._fail(job, error, now)
                raise type(error)()
            self._chars += size
            for key in job.holders:
                _add(self._held_chars, key, size)
            job.result = result
            job.filename = ""
            job.state = JobState.READY
            job.waiting = False
            job.expires_at = now + self._result_ttl
            self._schedule(job)

    def fail(self, job: Job, error: ServiceError) -> None:
        with self._lock:
            now = self._purge()
            if self._jobs.get(job.result_digest) is job:
                self._fail(job, error, now)

    def get(self, upload_id: str, principal: str) -> Job:
        with self._lock:
            self._purge()
            return self._owned(upload_id, principal)

    def read(self, upload_id: str, principal: str, page: int, page_chars: int) -> ResultPage:
        """Sert une page ; efface le résultat quand tout a été lu / serves a page; deletes once fully read."""
        with self._lock:
            now = self._purge()
            job = self._owned(upload_id, principal)
            expires_in = max(0, math.ceil(job.expires_at - now))
            if job.state is JobState.FAILED:
                # L'échec est signalé une fois, puis oublié / the failure is reported once, then forgotten.
                error = job.error or ServiceError()
                self._delete(job)
                raise type(error)(error.message, code=error.code)
            if job.result is None:
                return ResultPage(upload_id, job.state.value, expires_in)
            markdown = job.result.markdown
            bounds = job.bounds.get(page_chars)
            if bounds is None:
                # Tailles de page bornées : pas de recalcul à chaque lecture / bounded sizes, no recompute per read.
                if len(job.bounds) >= _MAX_PAGE_SIZES:
                    raise InvalidRequest("Trop de tailles de page différentes / too many distinct page sizes",
                                         code="too_many_page_sizes")
                bounds = job.bounds[page_chars] = page_bounds(markdown, page_chars)
            pages = len(bounds) - 1
            if not 1 <= page <= pages:
                raise NotFound("Page inexistante / no such page", code="page_not_found")
            start, end = bounds[page - 1], bounds[page]
            merge_interval(job.served, start, end)
            deleted = job.served == [(0, len(markdown))]
            result = job.result
            first = page == 1
            view = ResultPage(
                upload_id=upload_id, status=job.state.value, expires_in=expires_in, page=page, pages=pages,
                next_page=page + 1 if page < pages else None, page_chars=page_chars, total_chars=len(markdown),
                markdown=markdown[start:end], kind=result.kind,
                # Rapport, avertissements et éléments écartés en page 1 / report, warnings, dropped on page 1.
                report=result.report if first else None, warnings=list(result.warnings) if first else None,
                dropped=dict(result.dropped) if first else None, deleted=deleted,
            )
            if deleted:
                self._delete(job)
            return view

    def delete(self, upload_id: str, principal: str) -> None:
        with self._lock:
            self._purge()
            self._delete(self._owned(upload_id, principal))

    def purge(self) -> None:
        """Efface ce qui a expiré, même sans requête (balayage) / drops expired items, used by the sweeper."""
        with self._lock:
            self._purge()

    def stats(self) -> dict[str, int]:
        """Métadonnées seulement / metadata only."""
        with self._lock:
            self._purge()
            return {"jobs": len(self._jobs), "stored_chars": self._chars}

    def __len__(self) -> int:
        return len(self._jobs)

    # --- interne / internals (verrou tenu / lock held) ---

    @staticmethod
    def _allowed(job: Job, principal: str) -> bool:
        return job.owner is None or job.owner == principal

    def _owned(self, upload_id: str, principal: str) -> Job:
        """Travail désigné par sa capacité ; faux, expiré, lu ou d'une autre clé : la même erreur.

        Job designated by its capability; wrong, expired, consumed or another key's: the same error.
        """
        digest = result_digest(upload_id)
        job = self._jobs.get(digest) if digest is not None else None
        if job is None or not same_digest(job.result_digest, digest or b"") or not self._allowed(job, principal):
            raise NotFound
        return job

    def _fail(self, job: Job, error: ServiceError, now: float) -> None:
        if job.state is JobState.FAILED:
            return  # la première cause reste / the first cause stays
        job.state = JobState.FAILED
        job.waiting = False
        # Copie neuve, jamais levée : ni pile d'appels ni contexte, donc aucune référence au document reçu.
        # Fresh copy, never raised: no traceback nor context, hence no reference to the received document.
        job.error = type(error)(error.message, code=error.code, retry_after=error.retry_after)
        job.filename = ""
        job.expires_at = now + self._result_ttl
        self._schedule(job)

    def _schedule(self, job: Job) -> None:
        heapq.heappush(self._heap, (job.expires_at, next(self._seq), job.result_digest))

    def _purge(self) -> float:
        now = self._clock()
        heap = self._heap
        rearmed: dict[bytes, Job] = {}
        while heap and heap[0][0] <= now:
            _, _, digest = heapq.heappop(heap)
            job = self._jobs.get(digest)
            if job is None or job.expires_at > now:
                continue
            if job.waiting and job.state is JobState.PROCESSING:
                rearmed[digest] = job  # en file : réarmé une fois, jamais effacé / queued: re-armed once
            else:
                self._delete(job)
        for job in rearmed.values():
            job.expires_at = now + self._processing_ttl
            self._schedule(job)
        return now

    def _release_pending(self, job: Job) -> None:
        if job.pending_key is not None:
            _add(self._pending, job.pending_key, -1)
            self._pending_total -= 1
            job.pending_key = None

    def _delete(self, job: Job) -> None:
        if self._jobs.pop(job.result_digest, None) is None:
            return
        if job.token_digest is not None:
            self._tokens.pop(job.token_digest, None)
        self._release_pending(job)
        for key in job.holders:
            _add(self._active, key, -1)
        if job.result is not None:
            size = len(job.result.markdown)
            self._chars -= size
            for key in job.holders:
                _add(self._held_chars, key, -size)
        job.holders = ()
        # Références coupées au plus tôt (effacement au mieux) / drop references early (best-effort wipe).
        job.result = None
        job.error = None
        job.filename = ""
        job.bounds.clear()
        job.served.clear()


def _add(counts: dict[str, int], key: str, delta: int) -> None:
    """Compte par clé, la clé retirée à zéro (mémoire bornée) / per-key count, key dropped at zero."""
    value = counts.get(key, 0) + delta
    if value > 0:
        counts[key] = value
    else:
        counts.pop(key, None)
