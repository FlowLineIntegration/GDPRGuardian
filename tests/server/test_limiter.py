"""Limiteur d'abus : GCRA au coût, seau bon marché, préfixes, concurrence, délestage, état borné, modes.

Abuse limiter: cost GCRA, cheap bucket, prefixes, concurrency, shedding, bounded state, modes.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Callable

import pytest
from server_testkit import FakeClock

from gdprguardian.server.clients import LOCAL_CLIENT, Client, ClientIdentifier, Pseudonymizer
from gdprguardian.server.limiter import FILE, TEXT, Decision, Limiter, LimitPolicy, Ticket, _Table

MB = 2**20


class Harness:
    """Limiteur sur horloge pilotée, attente de file réglable / limiter on a driven clock, adjustable queue wait."""

    def __init__(self, policy: LimitPolicy | None = None) -> None:
        self.policy = policy or LimitPolicy()
        self.clock = FakeClock()
        self.queue_wait = 0.0
        self.identifier = ClientIdentifier("X-GG-Client", Pseudonymizer(rotate_s=self.policy.rotate_s,
                                                                         grace_s=self.policy.grace_s,
                                                                         clock=self.clock))
        self.limiter = Limiter(self.policy, estimated_wait=lambda _principal, _small: self.queue_wait,
                               typical_job_s=lambda: 0.5, clock=self.clock)

    def client(self, address: str) -> Client:
        client, _ = self.identifier.network([(b"x-gg-client", address.encode())], None)
        return client

    def cheap(self, client: Client) -> Decision:
        return self.limiter.admit(client, cheap=True, content=None, size=0)

    def text(self, client: Client, size: int = 2_000) -> Decision:
        return self.limiter.admit(client, cheap=False, content=TEXT, size=size)

    def file(self, client: Client, size: int) -> Decision:
        return self.limiter.admit(client, cheap=False, content=FILE, size=size)

    def done(self, decision: Decision, measured: float | None = None) -> None:
        """Fin de la requête ; `measured` : un travailleur l'a traitée en ce temps / a worker took that long."""
        assert decision.ticket is not None
        if measured is not None:
            decision.ticket.worked = True
            decision.ticket.measured = measured
        self.limiter.finish(decision.ticket)


def header(decision: Decision, name: bytes) -> str:
    return dict(decision.headers)[name].decode()


# --- seau des requêtes bon marché / cheap-request bucket ------------------------------------------------------


def test_cheap_requests_burst_then_refill() -> None:
    harness = Harness()
    client = harness.client("203.0.113.7")
    assert all(harness.cheap(client).status == 0 for _ in range(30))  # rafale de 30 / burst of 30
    refused = harness.cheap(client)
    assert refused.status == 429 and refused.ticket is None
    assert refused.retry_after == 1  # 0,1 s d'attente, arrondie à la seconde / 0.1 s, rounded up
    harness.clock.advance(0.1)  # 10 requêtes par seconde / 10 requests per second
    assert harness.cheap(client).status == 0 and harness.cheap(client).status == 429
    assert harness.cheap(harness.client("198.51.100.9")).status == 0  # autre client / another client


def test_estimates_follow_the_policy() -> None:
    policy = LimitPolicy()
    assert policy.estimate(TEXT, 0) == pytest.approx(0.005)
    assert policy.estimate(TEXT, MB) == pytest.approx(0.155)
    assert policy.estimate(FILE, 10 * MB) == pytest.approx(4.05)
    assert policy.estimate(FILE, 50 * MB) == pytest.approx(20.05)


# --- coût en secondes de travailleur / worker-second cost -------------------------------------------------------


def test_cost_burst_refill_and_exact_wait() -> None:
    harness = Harness()
    client = harness.client("203.0.113.7")
    for _ in range(4):  # 4 × 4,05 s = 16,2 s de la rafale de 20 s / of the 20 s burst
        decision = harness.file(client, 10 * MB)
        assert decision.status == 0
        harness.done(decision, measured=4.05)  # mesure = estimation / measured = estimate
    refused = harness.file(client, 10 * MB)
    # 16,2 + 4,05 - 20 = 0,25 s de trop, rendues à 0,5 s/s : 0,5 s / 0.25 s too many at 0.5 s/s: 0.5 s.
    assert refused.status == 429 and refused.retry_after == 1
    harness.clock.advance(0.5)
    assert harness.file(client, 10 * MB).status == 0


def test_a_request_larger_than_the_burst_passes_on_a_rested_bucket_only() -> None:
    harness = Harness()
    client = harness.client("203.0.113.7")
    big = harness.file(client, 50 * MB)  # 20,05 s > rafale : admis, seau vide / admitted, empty bucket
    assert big.status == 0
    harness.done(big, measured=20.05)
    assert harness.file(client, 50 * MB).status == 429
    assert harness.text(client).status == 429  # en dette : même un petit texte attend / in debt: even a text waits


def test_true_up_charges_the_measured_time_and_refunds_overestimates() -> None:
    harness = Harness()
    cheap_estimate = harness.client("203.0.113.7")
    decision = harness.text(cheap_estimate)  # estimation 0,005 s / estimate 0.005 s
    harness.done(decision, measured=25.0)    # mais 25 s de travailleur / but 25 worker-seconds
    refused = harness.text(cheap_estimate)
    assert refused.status == 429
    over = harness.client("198.51.100.9")
    estimated = harness.file(over, 10 * MB)  # 4,05 s pré-imputées / pre-charged
    harness.done(estimated, measured=0.1)    # 0,1 s réelles : le reste est rendu / the rest is refunded
    for _ in range(4):  # sans le remboursement, la 4e dépasserait la rafale / without the refund the 4th would not fit
        decision = harness.file(over, 10 * MB)
        assert decision.status == 0
        harness.done(decision, measured=4.05)


def test_debt_is_floored() -> None:
    harness = Harness()
    client = harness.client("203.0.113.7")
    decision = harness.text(client)
    harness.done(decision, measured=10_000.0)  # document monstrueux / monstrous document
    refused = harness.text(client)
    # Niveau plafonné à 20 + 30 = 50 s : attente (50 + 0,005 - 20) / 0,5 ≈ 60 s, plus 0 à 20 % d'aléa.
    # Level capped at 20 + 30 = 50 s: wait (50 + 0.005 - 20) / 0.5 ≈ 60 s, plus 0 to 20 % jitter.
    assert refused.status == 429 and 61 <= refused.retry_after <= math.ceil(60.01 * 1.2)
    harness.clock.advance(61)
    assert harness.text(client).status == 0


def test_cheap_and_cost_buckets_are_independent() -> None:
    harness = Harness()
    client = harness.client("203.0.113.7")
    for _ in range(30):
        harness.cheap(client)
    assert harness.cheap(client).status == 429
    assert harness.text(client).status == 0  # le coût n'est pas entamé / cost bucket untouched


# --- niveau préfixe / prefix tier ------------------------------------------------------------------------------


def test_the_prefix_tier_caps_address_rotation() -> None:
    # Un /24 IPv4 a 2 fois le budget d'une adresse : la 3e adresse épuise le préfixe, pas son propre seau.
    # An IPv4 /24 gets 2 times one address's budget: the 3rd address exhausts the prefix, not its own bucket.
    harness = Harness()
    for host in range(1, 3):
        client = harness.client(f"203.0.113.{host}")
        decision = harness.file(client, 50 * MB)
        assert decision.status == 0
        harness.done(decision, measured=19.9)  # préfixe : 2 × 19,9 = 39,8 s sur 40 / prefix: 39.8 s of 40
    third = harness.file(harness.client("203.0.113.3"), 10 * MB)
    assert third.status == 429
    assert harness.file(harness.client("198.51.100.5"), 10 * MB).status == 0  # autre /24 / another /24


def test_ipv6_clients_are_keyed_by_their_64_and_48() -> None:
    harness = Harness()
    same_64 = [harness.client(f"2001:db8:1:2::{n:x}") for n in (1, 0xFFFF)]
    assert same_64[0].key == same_64[1].key  # même /64 : même client / same /64: same client
    other_64 = harness.client("2001:db8:1:3::1")
    assert other_64.key != same_64[0].key and other_64.prefix == same_64[0].prefix  # même /48
    decision = harness.file(same_64[0], 50 * MB)
    harness.done(decision, measured=20.0)
    assert harness.text(same_64[1]).status == 429  # l'adresse change, pas le budget / address changes, not budget


# --- concurrence, délestage / concurrency, shedding -------------------------------------------------------------


def test_one_client_holds_at_most_three_requests_in_flight() -> None:
    harness = Harness()
    client = harness.client("203.0.113.7")
    in_flight = [harness.text(client) for _ in range(3)]  # 1 en cours + 2 en attente / 1 running + 2 queued
    assert all(d.status == 0 and d.ticket is not None and d.ticket.constrained for d in in_flight)
    fourth = harness.text(client)
    assert fourth.status == 429 and fourth.retry_after >= 1
    assert harness.cheap(client).status == 0  # les requêtes bon marché passent / cheap requests still pass
    harness.done(in_flight[0])
    assert harness.text(client).status == 0


def test_the_service_sheds_when_the_estimated_wait_is_too_long() -> None:
    harness = Harness()
    client = harness.client("203.0.113.7")
    harness.queue_wait = 9.9
    assert harness.text(client).status == 0
    harness.queue_wait = 25.0
    shed = harness.text(client)
    assert shed.status == 503 and 15 <= shed.retry_after <= 18  # attente au-delà de 10 s, plus l'aléa / plus jitter
    assert harness.cheap(client).status == 0  # rien n'est délesté sans contenu / nothing shed without content
    assert harness.limiter.stats()["shed"] == 1


def test_the_local_principal_is_exempt_but_capped_and_shed() -> None:
    harness = Harness()
    for _ in range(200):
        assert harness.cheap(LOCAL_CLIENT).status == 0
        decision = harness.file(LOCAL_CLIENT, 50 * MB)
        assert decision.status == 0 and decision.headers == ()
    ticket = decision.ticket
    assert ticket is not None and ticket.local and ticket.max_running == 2  # 2 en cours au plus / 2 running at most
    harness.queue_wait = 60.0
    assert harness.text(LOCAL_CLIENT).status == 503  # protège le public / protects the public
    assert harness.limiter.stats()["tracked_clients"] == 0  # aucun état pour lui / no state kept for it


# --- modes ---------------------------------------------------------------------------------------------------


def test_dry_run_shadows_the_buckets_only() -> None:
    # Les seaux comptent sans refuser ; requêtes en vol, plafonds de l'ordonnanceur et délestage restent appliqués :
    # un service public en dry-run garde ses protections par client. The buckets count without refusing; in-flight
    # caps, scheduler caps and shedding still apply: a public service in dry-run keeps its per-client protections.
    harness = Harness(LimitPolicy(mode="dry-run", cheap_burst=1, cost_burst=0.001, cost_rate=0.0001))
    client = harness.client("203.0.113.7")
    assert harness.cheap(client).status == 0
    second = harness.cheap(client)
    assert second.status == 0  # aurait été refusée / would have been refused
    in_flight = [harness.text(client) for _ in range(3)]
    assert all(d.status == 0 and d.ticket is not None and d.ticket.constrained for d in in_flight)
    assert harness.text(client).status == 429  # 4e en vol : refusée même en dry-run / 4th in flight: refused
    harness.queue_wait = 60.0
    assert harness.text(harness.client("198.51.100.9")).status == 503  # délestage / shedding
    stats = harness.limiter.stats()
    assert stats["dry_run_limited"] >= 2 and stats["limited"] == 1 and stats["shed"] == 1


def test_off_mode_is_a_kill_switch() -> None:
    harness = Harness(LimitPolicy(mode="off", cheap_burst=1))
    client = harness.client("203.0.113.7")
    assert all(harness.cheap(client) == Decision() for _ in range(100))
    assert harness.text(client).ticket is None
    assert harness.limiter.stats()["tracked_clients"] == 0


def test_an_internal_error_lets_the_request_through_silently(caplog: pytest.LogCaptureFixture) -> None:
    harness = Harness()

    def broken(_principal: str, _small: bool) -> float:
        raise RuntimeError("203.0.113.7")

    harness.limiter._estimated_wait = broken
    caplog.set_level(logging.DEBUG)
    decision = harness.text(harness.client("203.0.113.7"))
    assert decision.status == 0 and decision.ticket is None  # passe, sans place comptée / passes, nothing counted
    assert harness.limiter.stats()["errors"] == 1 and harness.limiter.stats()["in_flight"] == 0
    assert caplog.records == []  # rien de journalisé / nothing logged


# --- signalement / signalling --------------------------------------------------------------------------------


def test_ratelimit_headers_follow_the_ietf_draft_shape() -> None:
    harness = Harness()
    client = harness.client("203.0.113.7")
    cheap = harness.cheap(client)
    assert header(cheap, b"ratelimit-policy") == '"req";q=30;w=3'
    assert header(cheap, b"ratelimit") == '"req";r=29;t=1'
    text = harness.text(client)
    assert header(text, b"ratelimit-policy") == '"cpu";q=20000;qu="worker-ms";w=40'
    assert header(text, b"ratelimit").startswith('"cpu";r=1999')
    both = harness.limiter.admit(client, cheap=True, content=TEXT, size=100)  # /mcp
    assert header(both, b"ratelimit-policy").count('"') == 6


@pytest.mark.parametrize("wait", [0.3, 1.0, 7.5, 59.0])
def test_retry_after_is_whole_seconds_with_at_most_20_percent_jitter(wait: float) -> None:
    limiter = Harness().limiter
    values = {limiter._retry_after(wait) for _ in range(300)}
    assert min(values) >= max(1, math.ceil(wait)) and max(values) <= math.ceil(wait * 1.2)
    assert all(isinstance(value, int) for value in values)


def test_counters_are_aggregates_only() -> None:
    harness = Harness()
    harness.cheap(harness.client("203.0.113.7"))
    stats = harness.limiter.stats()
    assert set(stats) == {"accepted", "limited", "shed", "dry_run_limited", "errors", "overflows",
                          "tracked_clients", "tracked_prefixes", "in_flight"}
    assert all(type(value) is int for value in stats.values())


# --- état borné / bounded state ------------------------------------------------------------------------------


def test_rested_keys_are_swept() -> None:
    harness = Harness()
    for host in range(50):
        harness.cheap(harness.client(f"203.0.113.{host}"))
    assert harness.limiter.stats()["tracked_clients"] == 50
    harness.clock.advance(3.1)  # seaux de nouveau pleins / buckets full again
    harness.limiter.sweep()
    assert harness.limiter.stats()["tracked_clients"] == 0


def test_overflow_never_hands_a_fresh_budget_to_a_new_key() -> None:
    # Table pleine de clés en dette (inondation de /64 neufs) : une nouvelle clé hérite de l'état d'une évincée.
    # Table full of keys in debt (flood of fresh /64s): a new key inherits the state of an evicted one.
    harness = Harness(LimitPolicy(max_keys=8))
    for n in range(8):
        client = harness.client(f"2001:db8:{n:x}::1")
        decision = harness.file(client, 50 * MB)
        harness.done(decision, measured=40.0)
    newcomer = harness.text(harness.client("2001:db8:ffff::1"))
    assert newcomer.status == 429 and harness.limiter.stats()["overflows"] >= 1
    assert harness.limiter.stats()["tracked_clients"] <= 8


def test_rested_entries_make_room_before_any_eviction() -> None:
    table = _Table(capacity=4)
    for key in range(4):
        table.row(key, None, now=10.0)  # reposées dès maintenant / rested right away
    table.row(99, None, now=11.0)
    assert len(table) <= 4 and table.overflows == 0 and table.find(99) is not None


def test_pseudonym_rotation_keeps_state_through_the_grace_period() -> None:
    harness = Harness(LimitPolicy(rotate_s=10.0, grace_s=5.0))
    client = harness.client("203.0.113.7")
    decision = harness.file(client, 50 * MB)
    harness.done(decision, measured=40.0)
    harness.clock.advance(10.0)  # nouveau secret (niveau 40 - 5 = 35 s) / new secret (level 35 s)
    rotated = harness.client("203.0.113.7")
    assert rotated.key != client.key and rotated.previous_key == client.key
    assert harness.text(rotated).status == 429  # état repris de la génération précédente / state carried over
    harness.clock.advance(5.0)
    after_grace = harness.client("203.0.113.7")
    assert after_grace.previous_key is None  # l'ancien secret est oublié / the old secret is forgotten


# --- revue adverse : préfixes, corps lents, coût / adversarial review: prefixes, slow bodies, cost ----------------


def test_a_prefix_holds_at_most_twelve_requests_in_flight() -> None:
    # Un /48 qui tourne ses /64 (chacun 3 en vol) ne dépasse pas 12 requêtes en vol ; un autre /48 passe.
    # A /48 rotating its /64s (3 in flight each) never exceeds 12 requests in flight; another /48 goes through.
    harness = Harness()
    held = [harness.text(harness.client(f"2001:db8:bb:{net:x}::1"), 8 * MB) for net in range(4) for _ in range(3)]
    assert all(decision.status == 0 for decision in held)
    refused = harness.text(harness.client("2001:db8:bb:99::1"), 8 * MB)
    assert refused.status == 429 and harness.limiter.stats()["in_flight"] == 12
    assert harness.text(harness.client("2001:db8:cc::1")).status == 0
    harness.done(held[0])
    assert harness.text(harness.client("2001:db8:bb:99::1")).status == 0  # une place rendue / one place back


def test_a_request_that_never_reached_a_worker_keeps_its_charge() -> None:
    # Corps lent coupé (408), trop gros (413) ou client parti : l'estimation reste due, la tentative n'est pas gratuite.
    # Slow body cut (408), too large (413) or client gone: the estimate stays due, the attempt is not free.
    harness = Harness()
    client = harness.client("203.0.113.7")
    first = harness.file(client, 50 * MB)
    harness.done(first)  # jamais de travailleur / never a worker
    assert harness.file(client, 50 * MB).status == 429
    # Refus de capacité du service (503) : rien n'est dû / the service's capacity refusal: nothing due.
    other = harness.client("198.51.100.9")
    refused = harness.file(other, 50 * MB)
    assert refused.ticket is not None
    refused.ticket.waived = True
    harness.limiter.finish(refused.ticket)
    harness.clock.advance(0.1)  # le coût plancher (0,005 s) se rembourse en 0,01 s / the floor charge refills in 0.01 s
    assert harness.file(other, 50 * MB).status == 0


def test_observed_slowness_inflates_the_next_estimates() -> None:
    # Un petit fichier piégé occupe un travailleur 60 s : le suivant n'est plus « petit » (place réservée) et coûte
    # davantage d'avance. A small booby-trapped file holds a worker 60 s: the next one is no longer "small" (reserved
    # slot) and costs more upfront.
    harness = Harness()
    client = harness.client("203.0.113.7")
    first = harness.file(client, 100_000)
    assert first.ticket is not None and first.ticket.small and first.ticket.base == first.ticket.estimate
    harness.done(first, measured=60.0)
    harness.clock.advance(120)  # dette remboursée / debt repaid
    second = harness.file(client, 100_000)
    assert second.status == 0 and second.ticket is not None
    assert not second.ticket.small and second.ticket.estimate >= 40 * second.ticket.base
    # Une nouvelle adresse du même /24 hérite de la lenteur du préfixe / a new address of the /24 inherits it.
    neighbour = harness.file(harness.client("203.0.113.8"), 100_000)
    assert neighbour.ticket is not None and not neighbour.ticket.small
    # Des travaux rapides la font redescendre, jamais sous 1 / fast jobs bring it down, never below 1.
    harness.done(second, measured=second.ticket.base)
    harness.done(neighbour, measured=0.0)
    for _ in range(12):
        harness.clock.advance(60)
        decision = harness.file(client, 100_000)
        harness.done(decision, measured=0.0)
    assert decision.ticket is not None and decision.ticket.small


def test_the_service_policy_covers_the_longest_job_and_shares_the_slots() -> None:
    policy = LimitPolicy().for_service(slots=3, longest_job_s=270.0)
    assert policy.cost_debt == 270.0 and policy.max_running_prefix == 1  # (3 - 1 réservée) // 2
    # Le réglage reste un plafond / the setting stays a ceiling.
    assert LimitPolicy().for_service(slots=16, longest_job_s=10.0).max_running_prefix == 2
    assert LimitPolicy(max_running_prefix=6).for_service(slots=16, longest_job_s=10.0).max_running_prefix == 6
    assert LimitPolicy().for_service(slots=1, longest_job_s=10.0).max_running_prefix == 1


def test_a_slow_job_cannot_escape_most_of_its_cost() -> None:
    # Dette au niveau de l'échéance : un document de 270 s se paie en entier (attente ~ 540 s à 0,5 s/s).
    # Debt at the deadline's level: a 270 s document is paid in full (wait ~540 s at 0.5 s/s).
    harness = Harness(LimitPolicy().for_service(slots=3, longest_job_s=270.0))
    client = harness.client("203.0.113.7")
    decision = harness.file(client, 50 * MB)
    harness.done(decision, measured=270.0)
    refused = harness.text(client)
    assert refused.status == 429 and refused.retry_after >= 500


def test_internal_errors_are_reported_once_a_minute(caplog: pytest.LogCaptureFixture) -> None:
    harness = Harness()

    def broken(_principal: str, _small: bool) -> float:
        raise RuntimeError("203.0.113.7")

    harness.limiter._estimated_wait = broken
    caplog.set_level(logging.DEBUG)
    for _ in range(3):
        harness.text(harness.client("203.0.113.7"))
    harness.limiter.sweep()
    harness.text(harness.client("203.0.113.7"))
    harness.limiter.sweep()  # moins d'une minute après : rien / under a minute later: nothing
    harness.clock.advance(61)
    harness.limiter.sweep()
    messages = [record.getMessage() for record in caplog.records]
    assert messages == ["event=limiter_errors total=3 new=3", "event=limiter_errors total=4 new=1"]
    assert all(record.levelno == logging.WARNING for record in caplog.records)
    assert "203.0.113" not in caplog.text


def _ticket(estimate: float) -> Ticket:
    return Ticket(LOCAL_CLIENT, estimate, estimate < 0.2, True, 2, 2)


def test_ticket_reports_its_scheduling_constraints() -> None:
    ticket = _ticket(1.0)
    assert ticket.principal == "local" and ticket.prefix is None and ticket.local and not ticket.small


@pytest.mark.parametrize("factory", [lambda: LimitPolicy(mode="fast"), lambda: LimitPolicy(cost_rate=0),
                                     lambda: LimitPolicy(max_running=0), lambda: LimitPolicy(jitter=1.5)])
def test_invalid_policies_are_refused(factory: Callable[[], LimitPolicy]) -> None:
    with pytest.raises(ValueError):
        factory().validate()
