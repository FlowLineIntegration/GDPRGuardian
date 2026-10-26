"""Admission : budget mémoire équitable, file équitable, annulation / fair memory budget, fair queue, cancel."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import anyio
import pytest
from fastapi.testclient import TestClient
from server_testkit import AUTH_A, AUTH_B, KEY_A, SENSITIVE_TEXT
from starlette.types import Message, Receive, Scope, Send

from gdprguardian.server.admission import ANONYMOUS, AdmissionMiddleware, FairScheduler, MemoryBudget
from gdprguardian.server.middleware import PRINCIPAL_STATE_KEY
from gdprguardian.server.security import ApiKeyAuthenticator

MB = 2**20


# --- budget mémoire / memory budget ------------------------------------------------------------------


def test_a_single_principal_may_use_the_whole_budget() -> None:
    budget = MemoryBudget(100 * MB, principals=1)  # mode local : un seul principal / local mode: one principal
    assert all(budget.acquire("dev", 10 * MB) for _ in range(10))
    assert not budget.acquire("dev", 1)  # épuisé / exhausted
    budget.release("dev", 10 * MB)
    assert budget.acquire("dev", 10 * MB) and budget.used == 100 * MB


def test_a_flooding_key_cannot_take_the_reserve_kept_for_others() -> None:
    budget = MemoryBudget(100 * MB)  # réserve : le dernier quart / reserve: the last quarter
    admitted = 0
    while budget.acquire("flood", 5 * MB):
        admitted += 1
    assert budget.held("flood") == 75 * MB and admitted == 15
    # Une autre clé est admise dans la réserve, jusqu'à sa part / another key gets into the reserve.
    assert budget.acquire("calm", 10 * MB) and budget.acquire("calm", 10 * MB)
    assert budget.held("calm") == 20 * MB
    # Toujours refusé pour la clé qui inonde / still refused to the flooding key.
    assert not budget.acquire("flood", 1)


def test_a_key_holding_nothing_is_admitted_whenever_its_request_fits() -> None:
    budget = MemoryBudget(64 * MB, reserve=50 * MB)  # grosse requête maximale / large maximal request
    assert budget.acquire("a", 50 * MB)               # rien de tenu : admis / holds nothing: admitted
    assert not budget.acquire("a", 10 * MB)           # au-delà de sa part, la réserve est protégée
    assert budget.acquire("b", 14 * MB)               # rien de tenu, tient dans le budget / fits
    assert not budget.acquire("c", 1)                 # budget plein / budget full
    budget.release("a", 50 * MB)
    budget.release("b", 14 * MB)
    assert budget.used == 0 and budget.held("a") == budget.held("b") == 0


# --- créneaux équitables / fair slots ------------------------------------------------------------------


@pytest.mark.anyio
async def test_slots_bound_concurrency_and_serve_keys_in_turn() -> None:
    scheduler = FairScheduler(slots=2)
    started: list[str] = []
    running = 0
    peak = 0
    gate = anyio.Event()

    async def job(principal: str, label: str) -> None:
        nonlocal running, peak
        async with scheduler.slot(principal):
            started.append(label)
            running += 1
            peak = max(peak, running)
            await gate.wait()
            await anyio.sleep(0.01)
            running -= 1

    async with anyio.create_task_group() as tasks:
        for index in range(6):  # A inonde / A floods
            tasks.start_soon(job, "A", f"A{index}")
            await anyio.sleep(0)
        await anyio.sleep(0.01)
        tasks.start_soon(job, "B", "B0")  # B arrive après les six de A / B arrives after A's six
        await anyio.sleep(0.01)
        assert started == ["A0", "A1"] and scheduler.waiting == 5 and scheduler.busy == 2
        gate.set()
    assert peak == 2 and scheduler.busy == 0 and scheduler.waiting == 0
    # B, qui ne tient aucune place, passe à la première libération ; A garde son ordre.
    # B, holding no slot, goes at the first release; A keeps its order.
    assert started == ["A0", "A1", "B0", "A2", "A3", "A4", "A5"]


class _Jobs:
    """Travaux dont la fin est pilotée par le test / jobs whose end the test drives."""

    def __init__(self, scheduler: FairScheduler) -> None:
        self.scheduler = scheduler
        self.started: list[str] = []
        self._done: dict[str, anyio.Event] = {}

    async def run(self, principal: str, label: str) -> None:
        self._done[label] = anyio.Event()
        async with self.scheduler.slot(principal):
            self.started.append(label)
            await self._done[label].wait()

    async def finish(self, label: str) -> str:
        """Termine `label` et renvoie le travail qui prend sa place / ends `label`, returns its successor."""
        count = len(self.started)
        self._done[label].set()
        await _until(lambda: len(self.started) > count)
        return self.started[-1]

    def end(self, *labels: str) -> None:
        """Termine sans attendre de successeur / ends without waiting for a successor."""
        for label in labels:
            self._done[label].set()


async def _until(condition: Callable[[], bool]) -> None:
    with anyio.fail_after(5):
        while not condition():
            await anyio.sleep(0)


@pytest.mark.anyio
async def test_a_new_key_waits_at_most_one_release_behind_a_flooding_key() -> None:
    scheduler = FairScheduler(slots=2)
    jobs = _Jobs(scheduler)
    async with anyio.create_task_group() as tasks:
        for index in range(8):  # F tient les deux places et en attend six / F holds both slots, six waiting
            tasks.start_soon(jobs.run, "F", f"F{index}")
        await _until(lambda: scheduler.waiting == 6 and jobs.started == ["F0", "F1"])
        tasks.start_soon(jobs.run, "C", "C0")
        await _until(lambda: scheduler.waiting == 7)
        assert await jobs.finish("F0") == "C0"  # une seule libération / a single release
        assert await jobs.finish("F1") == "F2"  # F ne tient plus rien, C une place / F holds none, C one
        # Deux nouveaux venus, servis dans leur ordre d'arrivée / two newcomers, served in arrival order.
        tasks.start_soon(jobs.run, "D", "D0")
        await _until(lambda: scheduler.waiting == 6)
        tasks.start_soon(jobs.run, "E", "E0")
        await _until(lambda: scheduler.waiting == 7)
        assert await jobs.finish("C0") == "D0"
        assert await jobs.finish("F2") == "E0"
        assert scheduler.held("F") == 0 and scheduler.held("D") == scheduler.held("E") == 1
        for label in ("D0", "E0", "F3", "F4", "F5"):
            await jobs.finish(label)
        jobs.end("F6", "F7")
    assert jobs.started == ["F0", "F1", "C0", "F2", "D0", "E0", "F3", "F4", "F5", "F6", "F7"]
    # Rien n'est retenu des clés inactives / nothing is kept about inactive keys.
    assert scheduler.busy == scheduler.waiting == 0 and not scheduler._since and not scheduler._running


@pytest.mark.anyio
async def test_two_busy_keys_alternate_and_keep_their_own_order() -> None:
    scheduler = FairScheduler(slots=1)
    jobs = _Jobs(scheduler)
    async with anyio.create_task_group() as tasks:
        for label in ("X0", "X1", "X2", "Y0", "Y1", "Y2"):
            tasks.start_soon(jobs.run, label[0], label)
        await _until(lambda: scheduler.waiting == 5)
        successors = [await jobs.finish(label) for label in ("X0", "Y0", "X1", "Y1", "X2")]
        jobs.end("Y2")
    # Qui attend depuis le plus longtemps d'abord : aucune clé n'en affame une autre / longest waiting first.
    assert successors == ["Y0", "X1", "Y1", "X2", "Y2"]
    assert jobs.started == ["X0", "Y0", "X1", "Y1", "X2", "Y2"]


@pytest.mark.anyio
async def test_keys_sending_one_request_at_a_time_cannot_starve_a_waiting_key() -> None:
    # O attend avec une file ; P et Q renvoient une requête dès la fin de la précédente : chacun arrive de
    # nouveau, mais après la dernière fin de travail de O, qui passe donc à son tour.
    # O waits with a queue; P and Q send a new request as soon as their previous one ends: each arrives
    # again, but after O's last job ended, so O still gets its turn.
    scheduler = FairScheduler(slots=1)
    jobs = _Jobs(scheduler)
    sent = {"P": 0, "Q": 0}
    async with anyio.create_task_group() as tasks:
        for index in range(3):
            tasks.start_soon(jobs.run, "O", f"O{index}")
        await _until(lambda: scheduler.waiting == 2)
        for expected, key in enumerate(("P", "Q"), start=3):
            tasks.start_soon(jobs.run, key, f"{key}0")
            await _until(lambda expected=expected: scheduler.waiting == expected)
        current = "O0"
        for _ in range(6):
            successor = await jobs.finish(current)
            key = current[0]
            if key in sent:  # le client séquentiel envoie la suivante / the sequential client sends the next one
                sent[key] += 1
                expected = scheduler.waiting + 1
                tasks.start_soon(jobs.run, key, f"{key}{sent[key]}")
                await _until(lambda expected=expected: scheduler.waiting == expected)
            current = successor
        jobs.end(*list(jobs._done))
    # Chacun son tour, sans famine / each in turn, no starvation.
    assert jobs.started[:7] == ["O0", "P0", "Q0", "O1", "P1", "Q1", "O2"]
    assert scheduler.busy == scheduler.waiting == 0 and not scheduler._running


@pytest.mark.anyio
async def test_a_cancelled_waiter_leaves_the_queue_and_frees_nothing_twice() -> None:
    scheduler = FairScheduler(slots=1)
    release = anyio.Event()

    async def holder() -> None:
        async with scheduler.slot("A"):
            await release.wait()

    async with anyio.create_task_group() as tasks:
        tasks.start_soon(holder)
        await anyio.sleep(0.01)
        with anyio.move_on_after(0.05):  # client parti pendant l'attente / client gone while waiting
            async with scheduler.slot("B"):
                pytest.fail("jamais servi / never served")
        assert scheduler.waiting == 0 and scheduler.busy == 1
        release.set()
    assert scheduler.busy == 0
    async with scheduler.slot("C"):
        assert scheduler.busy == 1


def test_retry_after_is_bounded() -> None:
    scheduler = FairScheduler(slots=4)
    assert 1 <= scheduler.retry_after() <= 60


# --- intergiciel d'admission / admission middleware --------------------------------------------------


def _app_recording(budget: MemoryBudget, seen: list[int]) -> Callable[[Scope, Receive, Send], Any]:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        while True:
            message = await receive()
            if not message.get("more_body", False):
                break
        seen.append(budget.used)
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    return app


def _scope(path: str, headers: list[tuple[bytes, bytes]], principal: str | None = "k_a") -> Scope:
    return {"type": "http", "method": "POST", "path": path, "headers": headers,
            "state": {PRINCIPAL_STATE_KEY: principal} if principal else {}}


async def _call(middleware: AdmissionMiddleware, scope: Scope, chunks: list[bytes]) -> list[Message]:
    sent: list[Message] = []
    queue = [{"type": "http.request", "body": chunk, "more_body": index < len(chunks) - 1}
             for index, chunk in enumerate(chunks)]

    async def receive() -> Message:
        return queue.pop(0) if queue else {"type": "http.disconnect"}

    async def send(message: Message) -> None:
        sent.append(message)

    await middleware(scope, receive, send)
    return sent


def _middleware(budget: MemoryBudget, app: Any, limit: int = 1000) -> AdmissionMiddleware:
    return AdmissionMiddleware(app, budget=budget, limit_for=lambda _scope: limit, retry_after=lambda: 7,
                               routes=frozenset({"/v1/anonymize/text"}), cancel_on_disconnect=frozenset())


@pytest.mark.anyio
async def test_declared_size_is_reserved_during_the_request_then_released() -> None:
    budget, seen = MemoryBudget(10_000), []
    middleware = _middleware(budget, _app_recording(budget, seen))
    sent = await _call(middleware, _scope("/v1/anonymize/text", [(b"content-length", b"300")]), [b"x" * 300])
    assert sent[0]["status"] == 200 and seen == [300] and budget.used == 0


@pytest.mark.anyio
async def test_chunked_body_reserves_the_limit_then_its_real_size() -> None:
    budget, seen = MemoryBudget(10_000), []
    middleware = _middleware(budget, _app_recording(budget, seen))
    sent = await _call(middleware, _scope("/v1/anonymize/text", []), [b"x" * 100, b"y" * 50])
    assert sent[0]["status"] == 200 and seen == [150] and budget.used == 0


@pytest.mark.anyio
async def test_exhausted_budget_drains_the_body_then_answers_503() -> None:
    budget, seen = MemoryBudget(1000), []
    assert budget.acquire("other", 1000)
    middleware = _middleware(budget, _app_recording(budget, seen))
    scope = _scope("/v1/anonymize/text", [(b"content-length", b"200")])
    sent = await _call(middleware, scope, [b"x" * 100, b"y" * 100])
    headers = dict(sent[0]["headers"])
    assert sent[0]["status"] == 503 and headers[b"retry-after"] == b"7" and b"connection" not in headers
    assert json.loads(sent[1]["body"])["error"]["code"] == "service_busy"
    assert seen == [] and budget.used == 1000  # rien traité, rien retenu / nothing processed, nothing held


@pytest.mark.anyio
async def test_exhausted_budget_drains_a_chunked_body_too() -> None:
    # Sans Content-Length (« chunked ») : corps lu à vide, sinon le client verrait une connexion réinitialisée.
    # Without Content-Length (chunked): the body is drained, else the client would see a connection reset.
    budget, seen = MemoryBudget(1000), []
    assert budget.acquire("other", 1000)
    middleware = _middleware(budget, _app_recording(budget, seen))
    sent = await _call(middleware, _scope("/v1/anonymize/text", []), [b"x" * 100, b"y" * 100, b"z"])
    assert sent[0]["status"] == 503 and b"connection" not in dict(sent[0]["headers"])
    assert seen == [] and budget.used == 1000


@pytest.mark.anyio
async def test_draining_a_refused_body_is_bounded_by_the_route_limit() -> None:
    budget = MemoryBudget(1000)
    assert budget.acquire("other", 1000)
    reads = 0

    async def endless() -> Message:  # client qui envoie sans fin / a client that never stops sending
        nonlocal reads
        reads += 1
        return {"type": "http.request", "body": b"x" * 400, "more_body": True}

    sent: list[Message] = []

    async def send(message: Message) -> None:
        sent.append(message)

    await _middleware(budget, _app_recording(budget, []), limit=1000)(_scope("/v1/anonymize/text", []), endless, send)
    assert reads == 3 and sent[0]["status"] == 503 and dict(sent[0]["headers"])[b"connection"] == b"close"


@pytest.mark.anyio
async def test_expect_continue_is_refused_without_reading_the_body() -> None:
    budget = MemoryBudget(1000)
    assert budget.acquire("other", 1000)
    reads = 0

    async def receive() -> Message:
        nonlocal reads
        reads += 1
        return {"type": "http.request", "body": b"x", "more_body": False}

    sent: list[Message] = []

    async def send(message: Message) -> None:
        sent.append(message)

    middleware = _middleware(budget, _app_recording(budget, []))
    scope = _scope("/v1/anonymize/text", [(b"content-length", b"200"), (b"expect", b"100-continue")])
    await middleware(scope, receive, send)
    # Le client n'a pas envoyé son corps : refus immédiat, connexion fermée / refused at once, connection closed.
    assert reads == 0 and sent[0]["status"] == 503 and dict(sent[0]["headers"])[b"connection"] == b"close"


@pytest.mark.anyio
async def test_unauthenticated_requests_share_one_anonymous_principal() -> None:
    budget, held = MemoryBudget(10_000), []

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        held.append(budget.held(ANONYMOUS))
        await _app_recording(budget, [])(scope, receive, send)

    middleware = AdmissionMiddleware(app, budget=budget, limit_for=lambda _scope: 10_000, retry_after=lambda: 1,
                                     routes=frozenset({"/mcp"}), cancel_on_disconnect=frozenset())
    await _call(middleware, _scope("/mcp", [(b"content-length", b"64")], principal=None), [b"{}" * 32])
    assert held == [64] and budget.used == 0


@pytest.mark.anyio
async def test_client_disconnect_cancels_a_synchronous_request() -> None:
    budget = MemoryBudget(10_000)
    cancelled = anyio.Event()

    async def slow_app(scope: Scope, receive: Receive, send: Send) -> None:
        await receive()
        try:
            await anyio.sleep_forever()
        finally:
            cancelled.set()

    middleware = AdmissionMiddleware(slow_app, budget=budget, limit_for=lambda _scope: 10_000, retry_after=lambda: 1,
                                     routes=frozenset({"/v1/anonymize/text"}),
                                     cancel_on_disconnect=frozenset({"/v1/anonymize/text"}))
    messages = [{"type": "http.request", "body": b"x" * 10, "more_body": False}, {"type": "http.disconnect"}]

    async def receive() -> Message:
        return messages.pop(0)

    async def send(message: Message) -> None:
        pytest.fail("aucune réponse à un client parti / no response to a client gone")

    with anyio.fail_after(5):
        await middleware(_scope("/v1/anonymize/text", [(b"content-length", b"10")]), receive, send)
    assert cancelled.is_set() and budget.used == 0


def test_a_key_over_its_share_is_refused_while_another_goes_through(make_client: Callable[..., TestClient]) -> None:
    client = make_client()
    budget = client.app.state.service.budget
    principal_a = ApiKeyAuthenticator([KEY_A]).authenticate(AUTH_A["Authorization"])
    assert principal_a is not None
    # A tient déjà tout, sauf la réserve gardée pour les autres / A already holds all but the others' reserve.
    held = budget.limit - budget.reserve
    assert budget.acquire(principal_a, held)
    try:
        refused = client.post("/v1/anonymize/text", headers=AUTH_A, json={"text": SENSITIVE_TEXT})
        accepted = client.post("/v1/anonymize/text", headers=AUTH_B, json={"text": SENSITIVE_TEXT})
    finally:
        budget.release(principal_a, held)
    assert refused.status_code == 503 and int(refused.headers["retry-after"]) >= 1
    assert accepted.status_code == 200 and budget.used == 0


# --- places sous contraintes du limiteur / slots under the limiter's constraints ---------------------------------


class _Ticket:
    """Ticket contraint minimal (mêmes attributs que `limiter.Ticket`) / minimal constrained ticket."""

    def __init__(self, estimate: float = 0.05, *, prefix: int | None = None, local: bool = False,
                 max_running: int = 1, max_running_prefix: int = 2) -> None:
        self.estimate = estimate
        self.small = estimate < 0.2
        self.constrained = True
        self.max_running = max_running
        self.max_running_prefix = max_running_prefix
        self.prefix = prefix
        self.local = local


class _TicketJobs(_Jobs):
    async def run_with(self, principal: str, label: str, ticket: _Ticket, deadline_s: float | None = None) -> None:
        self._done[label] = anyio.Event()
        async with self.scheduler.slot(principal, ticket, deadline_s):  # type: ignore[arg-type]
            self.started.append(label)
            await self._done[label].wait()

    def age(self, seconds: float) -> None:
        """Fait comme si les travaux en cours tournaient depuis `seconds` de plus / as if running jobs were older."""
        for job in self.scheduler._jobs.values():
            job.started -= seconds


@pytest.mark.anyio
async def test_a_client_runs_one_job_at_a_time_while_others_use_the_free_slots() -> None:
    scheduler = FairScheduler(slots=3)
    jobs = _TicketJobs(scheduler)
    async with anyio.create_task_group() as tasks:
        for index in range(3):  # 1 en cours + 2 en attente / 1 running + 2 queued
            tasks.start_soon(jobs.run_with, "A", f"A{index}", _Ticket())
        await _until(lambda: scheduler.waiting == 2)
        assert jobs.started == ["A0"] and scheduler.busy == 1  # deux places restent libres / two slots stay free
        tasks.start_soon(jobs.run_with, "B", "B0", _Ticket())
        await _until(lambda: "B0" in jobs.started)
        assert await jobs.finish("A0") == "A1"
        jobs.end("A1", "B0")
        await _until(lambda: "A2" in jobs.started)
        jobs.end("A2")
    assert scheduler.busy == scheduler.waiting == 0 and not scheduler._prefix_running


@pytest.mark.anyio
async def test_a_prefix_runs_at_most_two_jobs() -> None:
    scheduler = FairScheduler(slots=4)
    jobs = _TicketJobs(scheduler)
    async with anyio.create_task_group() as tasks:
        for client in "ABC":  # trois adresses du même /24 / three addresses of one /24
            tasks.start_soon(jobs.run_with, client, f"{client}0", _Ticket(prefix=24))
        tasks.start_soon(jobs.run_with, "D", "D0", _Ticket(prefix=99))
        await _until(lambda: len(jobs.started) == 3)
        assert sorted(jobs.started) == ["A0", "B0", "D0"] and scheduler.waiting == 1
        assert await jobs.finish("A0") == "C0"
        jobs.end("B0", "C0", "D0")
    assert not scheduler._prefix_running


@pytest.mark.anyio
async def test_one_slot_stays_reserved_for_small_requests() -> None:
    # Une inondation de gros documents ne prend jamais la dernière place : un petit texte passe aussitôt.
    # A flood of large documents never takes the last slot: a small text goes through at once.
    scheduler = FairScheduler(slots=3, reserved=1)
    jobs = _TicketJobs(scheduler)
    async with anyio.create_task_group() as tasks:
        for index in range(4):
            tasks.start_soon(jobs.run_with, f"big{index}", f"L{index}", _Ticket(5.0))
        await _until(lambda: scheduler.waiting == 2 and len(jobs.started) == 2)
        assert scheduler.busy == 2  # la 3e place attend une petite requête / the 3rd slot waits for a small one
        tasks.start_soon(jobs.run_with, "small", "S0", _Ticket(0.01))
        await _until(lambda: "S0" in jobs.started)
        assert scheduler.busy == 3
        # Le principal LOCAL (protocole) ne prend jamais la place réservée / LOCAL never takes the reserved slot.
        jobs.end("S0")
        await _until(lambda: scheduler.busy == 2)
        tasks.start_soon(jobs.run_with, "local", "P0", _Ticket(0.01, local=True, max_running=2))
        await _until(lambda: scheduler.waiting == 3)
        assert "P0" not in jobs.started
        jobs.end(*[label for label in list(jobs._done) if label != "S0"])
    assert scheduler.busy == 0 and scheduler._large_running == 0


@pytest.mark.anyio
async def test_the_local_principal_runs_at_most_two_jobs() -> None:
    scheduler = FairScheduler(slots=4)
    jobs = _TicketJobs(scheduler)
    async with anyio.create_task_group() as tasks:
        for index in range(4):
            tasks.start_soon(jobs.run_with, "local", f"P{index}", _Ticket(0.01, local=True, max_running=2))
        await _until(lambda: len(jobs.started) == 2 and scheduler.waiting == 2)
        assert await jobs.finish("P0") == "P2"
        jobs.end("P1", "P2")
        await _until(lambda: "P3" in jobs.started)
        jobs.end("P3")


def test_reserved_slots_never_close_the_last_open_one() -> None:
    assert FairScheduler(slots=1, reserved=1).reserved == 0
    assert FairScheduler(slots=3, reserved=5).reserved == 2


@pytest.mark.anyio
async def test_estimated_wait_follows_the_fair_queue() -> None:
    scheduler = FairScheduler(slots=2)
    jobs = _TicketJobs(scheduler)
    assert scheduler.estimated_wait("Z", True) == 0
    async with anyio.create_task_group() as tasks:
        tasks.start_soon(jobs.run_with, "A", "A0", _Ticket(10.0))
        tasks.start_soon(jobs.run_with, "B", "B0", _Ticket(10.0))
        await _until(lambda: scheduler.busy == 2)
        tasks.start_soon(jobs.run_with, "A", "A1", _Ticket(6.0))
        tasks.start_soon(jobs.run_with, "A", "A2", _Ticket(6.0))  # derrière la tête de A / behind A's head
        await _until(lambda: scheduler.waiting == 2)
        # Un nouveau venu passe avant A, qui tient déjà une place : la première place libérée (10 s).
        # A newcomer goes before A, which already holds a slot: the first slot to free (10 s).
        assert scheduler.estimated_wait("Z", True) == pytest.approx(10.0, abs=0.5)
        # A lui-même, une place à la fois : A0 (10 s), puis A1 et A2 (6 s chacune) / A itself, one slot at a time.
        assert scheduler.estimated_wait("A", True) == pytest.approx(22.0, abs=0.5)
        jobs.end("A0", "B0")
        await _until(lambda: "A1" in jobs.started)
        jobs.end("A1")
        await _until(lambda: "A2" in jobs.started)
        jobs.end("A2")


# Le plus gros document publié (50 Mio et son enveloppe) : 0,05 s + 0,4 s/Mio, échéance 60 s + 1 s par 250 Ko.
# The largest published document: estimate and deadline.
_MAXIMAL_ESTIMATE = 0.05 + 0.4 * (50 * MB + 64 * 1024) / MB
_MAXIMAL_DEADLINE = 60 + 50 * MB / 250_000


@pytest.mark.anyio
async def test_a_free_usable_slot_means_no_wait() -> None:
    # Deux documents maximaux en cours sur trois places : un petit texte a la place réservée, un gros document attend
    # la première fin (~20 s), jamais la moyenne des places. Two maximal documents on three slots: a small text has
    # the reserved slot, a large document waits for the first end, never the average over the slots.
    scheduler = FairScheduler(slots=3, reserved=1)
    jobs = _TicketJobs(scheduler)
    async with anyio.create_task_group() as tasks:
        for client in "BC":
            tasks.start_soon(jobs.run_with, client, client, _Ticket(_MAXIMAL_ESTIMATE), _MAXIMAL_DEADLINE)
        await _until(lambda: scheduler.busy == 2)
        assert scheduler.estimated_wait("Z", True) == 0
        assert scheduler.estimated_wait("Z", False) == pytest.approx(_MAXIMAL_ESTIMATE, abs=0.5)
        # Une seule en cours : place libre pour tous / only one running: a free slot for everyone.
        jobs.end("B")
        await _until(lambda: scheduler.busy == 1)
        assert scheduler.estimated_wait("Z", True) == scheduler.estimated_wait("Z", False) == 0
        jobs.end("C")


@pytest.mark.anyio
async def test_small_texts_are_admitted_while_two_maximal_documents_run() -> None:
    from gdprguardian.server.clients import ClientIdentifier, Pseudonymizer
    from gdprguardian.server.limiter import FILE, TEXT, Limiter, LimitPolicy

    scheduler = FairScheduler(slots=3, reserved=1)
    limiter = Limiter(LimitPolicy(), estimated_wait=scheduler.estimated_wait, typical_job_s=lambda: 0.5)
    identifier = ClientIdentifier("X-GG-Client", Pseudonymizer())

    def client(address: str) -> Any:
        return identifier.network([(b"x-gg-client", address.encode())], None)[0]

    jobs = _TicketJobs(scheduler)
    largest = 50 * MB + 64 * 1024
    async with anyio.create_task_group() as tasks:
        for index, address in enumerate(("203.0.113.7", "198.51.100.9")):
            decision = limiter.admit(client(address), cheap=False, content=FILE, size=largest)
            assert decision.status == 0 and decision.ticket is not None and not decision.ticket.small
            tasks.start_soon(jobs.run_with, address, f"L{index}", decision.ticket, _MAXIMAL_DEADLINE)
        await _until(lambda: scheduler.busy == 2)
        # Chaque petit texte, d'un client neuf, passe aussitôt / every small text, from a new client, goes through.
        for index in range(20):
            text = limiter.admit(client(f"192.0.2.{index + 1}"), cheap=False, content=TEXT, size=2_000)
            assert text.status == 0 and text.ticket is not None and text.ticket.small
            limiter.finish(text.ticket)
        # Un troisième gros document attendrait ~20 s : délesté, Retry-After de ~10 s plus l'aléa.
        # A third large document would wait ~20 s: shed, Retry-After of ~10 s plus jitter.
        third = limiter.admit(client("100.64.0.1"), cheap=False, content=FILE, size=largest)
        assert third.status == 503 and 10 <= third.retry_after <= 13
        assert limiter.stats()["shed"] == 1
        jobs.end("L0", "L1")


@pytest.mark.anyio
async def test_a_job_past_its_estimate_is_expected_to_last_as_long_again_within_its_deadline() -> None:
    scheduler = FairScheduler(slots=1)
    jobs = _TicketJobs(scheduler)
    async with anyio.create_task_group() as tasks:
        tasks.start_soon(jobs.run_with, "A", "A0", _Ticket(5.0), 60.0)
        await _until(lambda: scheduler.busy == 1)
        jobs.age(2)  # sous l'estimation : le reste / under the estimate: what is left
        assert scheduler.estimated_wait("Z", True) == pytest.approx(3.0, abs=0.5)
        jobs.age(18)  # 20 s, passé l'estimation : encore autant / 20 s, past the estimate: as long again
        assert scheduler.estimated_wait("Z", True) == pytest.approx(20.0, abs=0.5)
        jobs.age(30)  # 50 s : jamais au-delà de l'échéance (60 s) / never past the deadline
        assert scheduler.estimated_wait("Z", True) == pytest.approx(10.0, abs=0.5)
        jobs.end("A0")


@pytest.mark.anyio
async def test_a_small_job_that_lasts_gives_the_reserved_slot_back() -> None:
    # Un petit document compressé qui dure tient la place réservée : la place libérée suivante revient aux petites
    # requêtes, pas à un gros document. A small compressed document that lasts holds the reserved slot: the next freed
    # slot goes back to small requests, not to a large document.
    scheduler = FairScheduler(slots=3, reserved=1)
    jobs = _TicketJobs(scheduler)
    async with anyio.create_task_group() as tasks:
        tasks.start_soon(jobs.run_with, "S", "S0", _Ticket(0.1))
        tasks.start_soon(jobs.run_with, "B", "L0", _Ticket(20.0))
        await _until(lambda: scheduler.busy == 2)
        jobs.age(30)  # S0 dure depuis 30 s / S0 has run for 30 s
        tasks.start_soon(jobs.run_with, "C", "L1", _Ticket(20.0))
        await _until(lambda: scheduler.waiting == 1)
        assert scheduler.busy == 2  # la place libre reste aux petites requêtes / the free slot stays for small ones
        tasks.start_soon(jobs.run_with, "T", "S1", _Ticket(0.01))
        await _until(lambda: "S1" in jobs.started)
        jobs.end("S1")
        await _until(lambda: scheduler.busy == 2)
        assert await jobs.finish("L0") == "L1"  # une grosse place libérée / a large slot freed
        jobs.end("S0", "L1")
    assert scheduler.busy == 0 and scheduler._large_running == 0
