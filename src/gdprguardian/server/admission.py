"""Admission : budget mémoire des requêtes et file équitable / admission: request memory budget and fair queue.

Deux ressources, deux gardiens / two resources, two guards:

- La mémoire du processus principal. Toute requête qui porte un contenu réserve sa taille (Content-Length)
  AVANT la lecture de son corps, dans un budget global (GDPRGUARDIAN_QUEUE_MB) ; quand un travailleur la prend, elle
  réserve aussi la plus grande sortie qu'il peut rendre, ramenée ensuite à la taille réelle du résultat, jusqu'à la
  fin de la réponse (`Reservation`). Une clé (le préfixe réseau d'un client public, sinon son principal) au-delà de
  sa part équitable ne peut pas entamer la dernière réserve du budget, gardée pour les autres : un client qui inonde
  le service ne bloque jamais l'admission des autres. Budget épuisé : 503 et Retry-After, rien d'autre.
  The main process's memory. Every request carrying content reserves its size BEFORE its body is read, in a
  global budget; when a worker takes it, it also reserves the largest output the worker may return, brought down to
  the real result size afterwards, until the response ends. A key (a public client's network prefix, else its
  principal) beyond its fair share cannot dig into the last reserve of the budget, kept for the others. Budget
  exhausted: 503 and Retry-After, nothing else.
- Les travailleurs. Au plus GDPRGUARDIAN_MAX_CONCURRENCY processus travaillent en même temps. Une place libérée
  revient à la clé en attente qui en occupe le moins, puis à celle qui attend depuis le plus longtemps
  (depuis son arrivée ou la fin de son dernier travail) : une clé qui arrive passe avant une clé qui inonde le
  service (une libération au plus, derrière les seules clés arrivées avant elle), et aucune clé n'est affamée.
  Ordre d'arrivée pour une même clé.
  The workers. At most GDPRGUARDIAN_MAX_CONCURRENCY processes work at once. A freed slot goes to the waiting key
  holding the fewest slots, then to the one waiting the longest (since its arrival or the end of its last
  job): a newly arrived key goes before a key flooding the service (one release at most, behind only the keys
  that arrived before it), and no key is starved. Arrival order within a key.

Une requête synchrone dont le client se déconnecte est annulée : elle quitte la file, ou son travailleur est
tué. A synchronous request whose client disconnects is cancelled: it leaves the queue, or its worker is killed.
"""

from __future__ import annotations

import heapq
import itertools
import logging
import math
import threading
import time
from collections import deque
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Protocol

import anyio
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .clients import REQUEST
from .errors import ServiceBusy
from .logs import log_event
from .middleware import ANONYMOUS, BUDGET_STATE_KEY, PRINCIPAL_STATE_KEY, content_length, refuse, route_template

_RESERVE_SHARE = 4       # dernier quart du budget gardé pour les clés sous leur part / last quarter kept back
_MAX_RETRY_AFTER = 60
# Requêtes simulées devant une nouvelle venue, au plus ; au-delà, leur part moyenne / requests simulated ahead of a
# newcomer, at most; beyond, their average share.
_SIMULATED = 64
# Petit travail qui dépasse cette durée : compté comme gros pour l'attribution des places (la place réservée revient
# aux petites requêtes dès qu'une autre se libère). A small job running past this counts as large when slots are
# handed out (the reserved capacity goes back to small requests as soon as another slot frees).
_SMALL_OVERRUN_S = 5.0


class MemoryBudget:
    """Octets de requêtes tenus en mémoire, partagés équitablement entre principaux / request bytes held, fairly.

    `reserve` : part du budget qu'un principal au-delà de sa part équitable ne peut pas prendre.
    `principals` : nombre maximal de principaux distincts (clés configurées), None si inconnu.
    `reserve`: share of the budget a principal beyond its fair share cannot take. `principals`: maximal
    number of distinct principals (configured keys), None if unknown.
    """

    def __init__(self, limit: int, *, reserve: int | None = None, principals: int | None = None) -> None:
        self.limit = limit
        self.reserve = limit // _RESERVE_SHARE if reserve is None else reserve
        self._principals = principals
        self._used = 0
        self._held: dict[str, int] = {}
        self._lock = threading.Lock()

    @property
    def used(self) -> int:
        return self._used

    def held(self, principal: str) -> int:
        return self._held.get(principal, 0)

    def acquire(self, principal: str, size: int) -> bool:
        """Réserve `size` octets ; False si le budget (ou la part de ce principal) est épuisé / False if exhausted.

        Un principal qui ne tient rien est toujours admis si la requête tient dans le budget : chaque clé peut
        progresser. Au-delà, sa part équitable compte une clé de plus que les actives (une nouvelle peut
        arriver). A principal holding nothing is always admitted when the request fits: every key makes
        progress. Beyond that, its fair share counts one key more than the active ones.
        """
        with self._lock:
            after = self._used + size
            if after > self.limit:
                return False
            held = self._held.get(principal, 0)
            if held:
                sharing = len(self._held) + 1
                if self._principals is not None:
                    sharing = min(sharing, self._principals)
                if held + size > self.limit // max(sharing, 1) and self.limit - after < self.reserve:
                    return False
            self._used = after
            self._held[principal] = held + size
            return True

    def release(self, principal: str, size: int) -> None:
        with self._lock:
            self._used -= size
            remaining = self._held.get(principal, 0) - size
            if remaining > 0:
                self._held[principal] = remaining
            else:
                self._held.pop(principal, None)


class Reservation:
    """Octets du budget tenus par une requête : son corps, puis la sortie de son travailleur / bytes one request holds.

    Tout est rendu à la fin de la requête (`release`), réponse envoyée. Everything is handed back when the request
    ends, response sent.
    """

    __slots__ = ("_budget", "body", "key", "output")

    def __init__(self, budget: MemoryBudget, key: str, body: int) -> None:
        self._budget = budget
        self.key = key
        self.body = body
        self.output = 0

    def set_body(self, size: int) -> None:
        """Corps « chunked » terminé : la réservation suit sa taille réelle (jamais plus) / follows the real size."""
        if size < self.body:
            self._budget.release(self.key, self.body - size)
            self.body = size

    def reserve_output(self, size: int) -> bool:
        """Réserve la plus grande sortie possible avant le travailleur ; False si le budget la refuse.

        Reserves the largest possible output before the worker; False when the budget refuses it.
        """
        if size <= self.output:
            return True
        if not self._budget.acquire(self.key, size - self.output):
            return False
        self.output = size
        return True

    def shrink_output(self, size: int) -> None:
        """Ramène la réservation de sortie à `size` (taille réelle du résultat) / brings it down to `size`."""
        if size < self.output:
            self._budget.release(self.key, self.output - size)
            self.output = size

    def release(self) -> None:
        held, self.body, self.output = self.body + self.output, 0, 0
        if held:
            self._budget.release(self.key, held)


class SlotTicket(Protocol):
    """Contraintes d'une requête vues par l'ordonnanceur (`limiter.Ticket`) / a request's scheduling constraints."""

    estimate: float
    small: bool
    constrained: bool
    max_running: int
    max_running_prefix: int

    @property
    def prefix(self) -> int | None: ...

    @property
    def local(self) -> bool: ...


class _Waiter:
    __slots__ = ("deadline", "estimate", "event", "granted", "large", "owner", "started", "ticket")

    def __init__(self, owner: str, ticket: SlotTicket | None, estimate: float, deadline: float | None) -> None:
        self.event = anyio.Event()
        self.granted = False
        self.owner = owner
        self.ticket = ticket if ticket is not None and ticket.constrained else None
        self.estimate = estimate
        self.deadline = deadline  # échéance du travail, en secondes (None : inconnue) / the job's deadline
        # Ne peut pas prendre une place réservée aux petites requêtes / may not take a slot kept for small requests.
        self.large = self.ticket is not None and (not self.ticket.small or self.ticket.local)
        self.started = 0.0

    @property
    def max_running(self) -> float:
        return self.ticket.max_running if self.ticket is not None else math.inf

    def remaining(self, now: float) -> float:
        """Durée restante estimée d'un travail en cours / estimated time left of a running job.

        Passé son estimation, un travail est supposé durer encore autant qu'il a déjà duré, jamais au-delà de son
        échéance. Past its estimate, a job is assumed to run as long again as it already has, never past its deadline.
        """
        elapsed = now - self.started
        left = self.estimate - elapsed if elapsed < self.estimate else elapsed
        if self.deadline is not None:
            left = min(left, self.deadline - elapsed)
        return max(0.0, left)

    def overrun(self, now: float) -> bool:
        """Petit travail qui dure : il tient sa place comme un gros / a small job that lasts holds its slot like a large
        one."""
        return not self.large and self.ticket is not None and now - self.started > _SMALL_OVERRUN_S


class FairScheduler:
    """Créneaux de travail partagés équitablement entre principaux, FIFO pour un même principal.

    Work slots shared fairly between principals, FIFO within a principal. Une place libérée revient au
    principal en attente qui en tient le moins, puis à celui qui attend depuis le plus longtemps : depuis son
    arrivée, ou depuis la fin de son dernier travail. Une clé qui arrive n'attend donc jamais derrière une clé
    qui occupe déjà des places, et des clés qui renvoient sans cesse une requête n'en affament pas une autre.
    A freed slot goes to the waiting principal holding the fewest slots, then to the one waiting the longest:
    since its arrival, or since the end of its last job. A newly arrived key thus never waits behind a key
    already holding slots, and keys that keep sending requests cannot starve another one. Une seule boucle
    d'événements / a single event loop.

    Une requête munie d'un ticket contraint (limiteur en mode enforce) n'est servie que si son client tient moins
    de `max_running` places, son préfixe moins de `max_running_prefix`, et, grosse requête ou principal LOCAL, si
    une place autre que les `reserved` places gardées aux petites requêtes est libre. A request with a constrained
    ticket (limiter in enforce mode) is only served while its client holds fewer than `max_running` slots, its prefix
    fewer than `max_running_prefix`, and, for a large request or the LOCAL principal, while a slot other than the
    `reserved` ones kept for small requests is free. Un petit travail qui dure plus de `_SMALL_OVERRUN_S` compte
    alors comme gros : la place réservée revient aux petites requêtes dès qu'une autre se libère. A small job lasting
    longer than `_SMALL_OVERRUN_S` then counts as large: the reserved capacity goes back to small requests as soon as
    another slot frees.
    """

    def __init__(self, slots: int, *, reserved: int = 0) -> None:
        self.slots = slots
        # Au moins une place reste ouverte à toutes les requêtes / at least one slot stays open to every request.
        self.reserved = max(0, min(reserved, slots - 1))
        self._free = slots
        # Files par principal, dans l'ordre d'arrivée des principaux / per-principal queues, arrival order.
        self._queues: dict[str, deque[_Waiter]] = {}
        # Places tenues (principaux actifs) et rang depuis lequel chaque principal en file attend (mémoire bornée).
        # Slots held (active principals) and the rank each queued principal has waited since (bounded memory).
        self._running: dict[str, int] = {}
        self._since: dict[str, int] = {}
        self._prefix_running: dict[int, int] = {}
        self._large_running = 0
        self._jobs: dict[int, _Waiter] = {}
        self._ticks = itertools.count()
        self._job_s = 0.5  # durée moyenne glissante d'un travail / moving average of a job's duration

    @property
    def waiting(self) -> int:
        return sum(len(queue) for queue in self._queues.values())

    @property
    def busy(self) -> int:
        return self.slots - self._free

    @property
    def typical_job_s(self) -> float:
        return self._job_s

    def held(self, principal: str) -> int:
        """Places tenues par ce principal / slots held by this principal."""
        return self._running.get(principal, 0)

    @asynccontextmanager
    async def slot(self, principal: str, ticket: SlotTicket | None = None,
                   deadline_s: float | None = None) -> AsyncIterator[None]:
        """Une place de travail ; `deadline_s` : échéance du travail, qui borne son estimation / the job's deadline."""
        waiter = await self._acquire(principal, ticket, deadline_s)
        try:
            yield
        finally:
            self._job_s = 0.8 * self._job_s + 0.2 * (time.monotonic() - waiter.started)
            self._release(principal, waiter)

    def retry_after(self) -> int:
        """Attente estimée avant qu'une place se libère, en secondes / estimated wait before room frees up."""
        rounds = self.waiting / max(self.slots, 1) + 1
        return max(1, min(_MAX_RETRY_AFTER, math.ceil(rounds * self._job_s)))

    def estimated_wait(self, principal: str, small: bool) -> float:
        """Attente estimée, en secondes, avant qu'une nouvelle requête de `principal` obtienne une place.

        Estimated wait, in seconds, before a new request from `principal` gets a slot. Simulation de la file avec les
        estimations : les travaux en cours se terminent (`_Waiter.remaining`), les requêtes servies avant la nouvelle
        venue prennent tour à tour la première place qu'elles ont le droit de prendre (gros travaux hors des places
        réservées, `max_running` par principal), puis la nouvelle venue. Devant elle : sa propre file, et la tête de
        file de chaque principal que l'équité sert avant le sien (moins de places tenues, ou autant et une attente plus
        longue). Une place utilisable libre, personne d'éligible devant : 0. Simulation of the queue with the
        estimates: running jobs end, the requests served before the newcomer each take the first slot they may take
        (large jobs outside the reserved slots, `max_running` per principal), then the newcomer. Ahead of it: its own
        queue, and the head of every principal the fair order serves before its own. A usable slot free and no
        eligible request ahead: 0. Au-delà de `_SIMULATED` requêtes devant, le reste compte pour sa part moyenne /
        beyond `_SIMULATED` requests ahead, the rest counts for its average share.
        """
        now = time.monotonic()
        own_queue = self._queues.get(principal, ())
        own_key: tuple[int, float] = (self._running.get(principal, 0), self._since.get(principal, math.inf))
        heads: list[tuple[tuple[int, float], _Waiter]] = []
        for owner, queue in self._queues.items():
            key = (self._running.get(owner, 0), self._since[owner])
            if owner != principal and key < own_key:
                heads.append((key, queue[0]))
        heads.sort(key=lambda pair: pair[0])
        ahead = [waiter for _, waiter in heads] + list(own_queue)
        usable = self.slots if small else self.slots - self.reserved
        rest = sum(waiter.estimate for waiter in ahead[_SIMULATED:]) / max(1, usable)
        # Contrainte de la nouvelle venue : celle de ses requêtes connues / the newcomer's cap: its known requests'.
        own_cap = min((waiter.max_running for waiter in (*own_queue, *self._jobs.values())
                       if waiter.owner == principal), default=math.inf)
        return self._simulate(now, ahead[:_SIMULATED], principal, not small, own_cap) + rest

    def _simulate(self, now: float, ahead: list[_Waiter], principal: str, large: bool, cap: float) -> float:
        large_cap = self.slots - self.reserved
        events: list[tuple[float, int, bool, str]] = []
        held: dict[str, int] = {}
        large_held = 0
        for index, job in enumerate(self._jobs.values()):
            counted = job.large or job.overrun(now)
            events.append((job.remaining(now), index, counted, job.owner))
            held[job.owner] = held.get(job.owner, 0) + 1
            large_held += counted
        heapq.heapify(events)
        sequence = itertools.count(len(events))
        free = self._free
        pending: list[tuple[float, bool, str, float] | None] = [
            (waiter.estimate, waiter.large, waiter.owner, waiter.max_running) for waiter in ahead]
        pending.append(None)  # la nouvelle venue / the newcomer
        clock = 0.0
        while True:
            index = 0
            while free > 0 and index < len(pending):
                item = pending[index]
                is_large, owner, limit = (large, principal, cap) if item is None else item[1:]
                if (is_large and large_held >= large_cap) or held.get(owner, 0) >= limit:
                    index += 1
                    continue
                if item is None:
                    return clock
                del pending[index]
                free -= 1
                held[owner] = held.get(owner, 0) + 1
                large_held += is_large
                heapq.heappush(events, (clock + item[0], next(sequence), is_large, owner))
            if not events:  # jamais atteint : tout libre, la nouvelle venue passe / unreachable: all free
                return clock
            end, _, was_large, owner = heapq.heappop(events)
            clock = max(clock, end)
            free += 1
            held[owner] -= 1
            large_held -= was_large

    async def _acquire(self, principal: str, ticket: SlotTicket | None, deadline_s: float | None) -> _Waiter:
        waiter = _Waiter(principal, ticket, ticket.estimate if ticket is not None else self._job_s, deadline_s)
        self._queues.setdefault(principal, deque()).append(waiter)
        self._since.setdefault(principal, next(self._ticks))
        self._dispatch()
        if waiter.granted:
            return waiter
        try:
            await waiter.event.wait()
        except BaseException:
            # Annulé : la requête quitte la file, ou rend la place qu'on venait de lui donner.
            # Cancelled: the request leaves the queue, or hands back the slot it was just given.
            if waiter.granted:
                self._release(principal, waiter)
            else:
                self._withdraw(principal, waiter)
            raise
        return waiter

    def _eligible(self, principal: str, waiter: _Waiter, overrun: int) -> bool:
        ticket = waiter.ticket
        if ticket is None:
            return True
        if self._running.get(principal, 0) >= ticket.max_running:
            return False
        prefix = ticket.prefix
        if prefix is not None and self._prefix_running.get(prefix, 0) >= ticket.max_running_prefix:
            return False
        return not waiter.large or self._large_running + overrun < self.slots - self.reserved

    def _dispatch(self) -> None:
        """Donne les places libres, tant qu'une tête de file y a droit / hands out free slots to eligible heads."""
        if self._free <= 0 or not self._queues:
            return
        # Petits travaux qui durent : comptés comme gros (ceux donnés ici sont neufs) / small jobs that last: large.
        now = time.monotonic()
        overrun = sum(1 for job in self._jobs.values() if job.overrun(now))
        while self._free > 0 and self._queues:
            eligible = [owner for owner, queue in self._queues.items() if self._eligible(owner, queue[0], overrun)]
            if not eligible:
                return
            # Le moins de places tenues, puis qui attend depuis le plus longtemps / fewest slots, then longest waiting.
            chosen = min(eligible, key=lambda owner: (self._running.get(owner, 0), self._since[owner]))
            queue = self._queues[chosen]
            waiter = queue.popleft()
            if not queue:
                del self._queues[chosen]
                del self._since[chosen]
            self._free -= 1
            self._running[chosen] = self._running.get(chosen, 0) + 1
            if waiter.ticket is not None:
                prefix = waiter.ticket.prefix
                if prefix is not None:
                    self._prefix_running[prefix] = self._prefix_running.get(prefix, 0) + 1
                self._large_running += waiter.large
            waiter.started = time.monotonic()
            self._jobs[id(waiter)] = waiter
            waiter.granted = True
            waiter.event.set()

    def _release(self, principal: str, waiter: _Waiter) -> None:
        if self._jobs.pop(id(waiter), None) is None:
            return  # déjà rendue / already released
        held = self._running.get(principal, 0) - 1
        if held > 0:
            self._running[principal] = held
        else:
            self._running.pop(principal, None)  # inactif : oublié / inactive: forgotten
        if waiter.ticket is not None:
            prefix = waiter.ticket.prefix
            if prefix is not None:
                remaining = self._prefix_running.get(prefix, 0) - 1
                if remaining > 0:
                    self._prefix_running[prefix] = remaining
                else:
                    self._prefix_running.pop(prefix, None)
            self._large_running -= waiter.large
        if principal in self._queues:
            # Sa file attend de nouveau depuis maintenant : derrière ceux déjà en attente / waits again from now.
            self._since[principal] = next(self._ticks)
        self._free += 1
        self._dispatch()

    def _withdraw(self, principal: str, waiter: _Waiter) -> None:
        queue = self._queues.get(principal)
        if queue is None or waiter not in queue:
            return
        queue.remove(waiter)
        if not queue:
            del self._queues[principal]
            del self._since[principal]
        # Une tête de file bloquée derrière elle peut maintenant passer / a head blocked behind it may now go.
        self._dispatch()


class AdmissionMiddleware:
    """Réserve la taille du corps AVANT sa lecture ; 503 + Retry-After si le budget est épuisé.

    Reserves the body size BEFORE reading it; 503 + Retry-After when the budget is exhausted. Placé après
    l'authentification (le principal est connu) et avant la limite de taille. Placed after authentication
    (the principal is known) and before the size limit.

    `routes` : gabarits de route qui portent un contenu. `cancel_on_disconnect` : routes synchrones annulées
    si le client part (pas l'envoi hors bande : son résultat attend dans le dépôt). `routes`: route templates
    carrying content. `cancel_on_disconnect`: synchronous routes cancelled when the client leaves (not the
    out-of-band upload, whose result waits in the store).
    """

    def __init__(self, app: ASGIApp, *, budget: MemoryBudget, limit_for: Callable[[Scope], int],
                 retry_after: Callable[[], int], routes: frozenset[str],
                 cancel_on_disconnect: frozenset[str]) -> None:
        self.app = app
        self.budget = budget
        self.limit_for = limit_for
        self.retry_after = retry_after
        self.routes = routes
        self.cancel_on_disconnect = cancel_on_disconnect

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        route = route_template(scope.get("path", "")) if scope["type"] == "http" else ""
        if route not in self.routes or scope.get("method") not in ("POST", "PUT"):
            await self.app(scope, receive, send)
            return
        limit = self.limit_for(scope)
        declared = content_length(scope)
        if declared == -1 or (declared is not None and declared > limit):
            await self.app(scope, receive, send)  # refusé plus loin (400, 413) / refused further in
            return
        size = limit if declared is None else declared
        state = scope.get("state", {})
        # Préfixe réseau d'un client public (une rotation de /64 n'ouvre pas de nouvelle part), sinon le principal.
        # A public client's network prefix (rotating /64s opens no new share), else the principal.
        key = state.get(BUDGET_STATE_KEY) or state.get(PRINCIPAL_STATE_KEY) or ANONYMOUS
        if not self.budget.acquire(key, size):
            log_event("service_busy", logging.DEBUG, route=route, bytes=size, held=self.budget.used)
            await refuse(scope, receive, send, ServiceBusy(retry_after=self.retry_after()), (), limit)
            return
        reservation = Reservation(self.budget, key, size)
        context = REQUEST.get()
        if context is not None:
            context.reservation = reservation  # sortie du travailleur, réservée par le service / worker output
        received = 0

        async def counting_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if not message.get("more_body", False) and declared is None:
                    reservation.set_body(received)  # corps « chunked » terminé / chunked body complete
            return message

        try:
            if route in self.cancel_on_disconnect:
                await _cancel_on_disconnect(self.app, scope, counting_receive, receive, send)
            else:
                await self.app(scope, counting_receive, send)
        finally:
            if context is not None:
                context.reservation = None
            reservation.release()


async def _cancel_on_disconnect(app: ASGIApp, scope: Scope, receive: Receive, raw_receive: Receive,
                                send: Send) -> None:
    """Annule la requête si le client se déconnecte avant la réponse / cancels it if the client leaves first.

    Une fois le corps lu, l'application ne lit plus rien : on attend alors la déconnexion (ou la fin de la
    réponse) sur le canal d'origine. Once the body is read the application reads nothing more: we then wait
    for the disconnect (or the end of the response) on the original channel.
    """
    body_read = anyio.Event()
    responding = False

    async def tracking_receive() -> Message:
        message = await receive()
        if message["type"] != "http.request" or not message.get("more_body", False):
            body_read.set()
        return message

    async def tracking_send(message: Message) -> None:
        nonlocal responding
        if message["type"] == "http.response.start":
            responding = True
        await send(message)

    async with anyio.create_task_group() as tasks:
        async def watch() -> None:
            await body_read.wait()
            message = await raw_receive()
            if message["type"] == "http.disconnect" and not responding:
                log_event("request_abandoned", logging.DEBUG, route=route_template(scope.get("path", "")))
                tasks.cancel_scope.cancel()

        tasks.start_soon(watch)
        await app(scope, tracking_receive, tracking_send)
        tasks.cancel_scope.cancel()


__all__ = ["ANONYMOUS", "AdmissionMiddleware", "FairScheduler", "MemoryBudget", "Reservation", "SlotTicket"]
