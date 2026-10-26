"""Limiteur d'abus du service public, en mémoire seulement / abuse limiter of the public service, memory only.

Couches, de la moins chère à la plus fine (décision avant toute lecture du corps) / layers, cheapest first
(decided before any body is read):

1. Seau des requêtes bon marché (santé, packs, résultats, MCP, création d'envoi…) : GCRA, 10 requêtes/s, rafale
   30, par client. Cheap-request bucket: GCRA, 10 requests/s, burst 30, per client.
2. Coût en secondes de travailleur (GCRA à coût variable) : recharge 0,5 s/s, rafale 20 s, par client ; le même au
   niveau du préfixe (/24 IPv4, /48 IPv6) à 2 fois. Pré-imputation estimée d'après Content-Length (texte 0,005 s +
   0,15 s/Mo ; fichier 0,05 s + 0,4 s/Mo ; corps « chunked » : le plafond de la route), multipliée par la lenteur
   observée du client (moyenne glissante mesure/estimation, de 1 à 100). Correction par le temps de travailleur
   mesuré si la requête a obtenu un travailleur ; sinon (corps trop lent, trop gros, client parti) l'estimation reste
   due, et seul un refus de capacité du service (503) la rend. Dette bornée par l'échéance du plus long travail.
   Worker-second cost (variable-cost GCRA): refill 0.5 s/s, burst 20 s, per client; the same per prefix at 2x.
   Estimated pre-charge from Content-Length, multiplied by the client's observed slowness (moving average of
   measured/estimate, 1 to 100). Trued up with the measured worker time when the request got a worker; otherwise
   (body too slow, too large, client gone) the estimate stays due, and only a capacity refusal (503) refunds it.
   Debt bounded by the longest job's deadline.
3. Concurrence : 3 requêtes à contenu en vol par client (1 en cours, 2 en attente), 12 par préfixe ; en cours, au plus
   la moitié des places non réservées par préfixe ; une place de travailleur réservée aux requêtes estimées sous
   0,2 s ; délestage (503) quand l'attente estimée dépasse 10 s. Concurrency: 3 content requests in flight per client
   (1 running, 2 queued), 12 per prefix; running, at most half of the non-reserved slots per prefix; one worker slot
   reserved for requests estimated under 0.2 s; shedding (503) when the estimated wait exceeds 10 s.

État borné (100 000 clés par niveau, clés reposées ou inactives retirées, débordement à la Space-Saving : une clé
nouvelle hérite de l'état de la clé évincée, la moins chargée d'un échantillon, et n'obtient donc jamais un budget
neuf pendant une inondation). Compteurs agrégés seulement, jamais par client. Modes enforce, dry-run (les seaux
comptent sans refuser ; plafonds de concurrence et délestage restent appliqués) et off (interrupteur d'arrêt).
Erreur interne : la requête passe (fail open) ; le balayage signale le total au plus une fois par minute. Bounded
state (100,000 keys per tier, rested or idle keys dropped, Space-Saving-style overflow: a new key inherits the state
of the evicted one, the least loaded of a sample, so it never gets a fresh budget during a flood). Aggregate counters
only, never per client. Modes enforce, dry-run (the buckets count without refusing; concurrency caps and shedding
still apply) and off (kill switch). Internal error: the request goes through (fail open); the sweep reports the
total at most once a minute.
"""

from __future__ import annotations

import logging
import math
import random
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, fields, replace
from typing import Any

from .clients import Client
from .logs import log_event

ENFORCE = "enforce"
DRY_RUN = "dry-run"
OFF = "off"
MODES = (ENFORCE, DRY_RUN, OFF)
# Nature d'une requête à contenu / kind of a content request.
TEXT = "text"
FILE = "file"
_MB = float(2**20)
_SAMPLE = 16             # échantillon d'éviction (approximation de Space-Saving) / eviction sample
_MAX_RETRY_AFTER = 600
_EPSILON = 1e-9
_ERROR_REPORT_S = 60.0   # signalement agrégé des erreurs internes, au plus / aggregate error report, at most
# Lignes de l'état : temps théorique d'arrivée (coût, bon marché), dernière vue, multiplicateur de lenteur.
# State rows: TATs (cost, cheap), last seen, slowness multiplier.
_COST, _CHEAP, _SEEN, _SLOW = 0, 1, 2, 3


@dataclass(frozen=True, slots=True)
class LimitPolicy:
    """Politique du limiteur ; durées en secondes, coûts en secondes de travailleur / limiter policy.

    Valeurs de départ de la spécification, à étalonner sur les compteurs du mode dry-run. Starting values from the
    specification, to be calibrated on the dry-run counters.
    """

    mode: str = ENFORCE
    cost_rate: float = 0.5          # secondes de travailleur rendues par seconde / worker-seconds refilled per second
    cost_burst: float = 20.0
    # Dette maximale après correction ; le service la porte à l'échéance de son plus long travail (`for_service`).
    # Largest debt after the true-up; the service raises it to its longest job's deadline.
    cost_debt: float = 30.0
    prefix_factor: float = 2.0      # niveau préfixe (/24, /48) / prefix tier
    cheap_rate: float = 10.0        # requêtes par seconde / requests per second
    cheap_burst: float = 30.0
    text_base_s: float = 0.005
    text_per_mb_s: float = 0.15
    file_base_s: float = 0.05
    file_per_mb_s: float = 0.4
    floor_s: float = 0.005          # coût minimal d'une requête à contenu / smallest charge of a content request
    max_slowness: float = 100.0     # plafond du multiplicateur de lenteur / cap of the slowness multiplier
    max_running: int = 1            # par client / per client
    max_queued: int = 2
    # Par préfixe ; le service le borne à la moitié des places non réservées / per prefix; the service caps it at half
    # of the non-reserved slots.
    max_running_prefix: int = 2
    max_inflight_prefix: int = 12   # requêtes à contenu en vol par préfixe / content requests in flight per prefix
    local_running: int = 2          # principal LOCAL (protocole sur le serveur) / LOCAL principal
    reserved_slots: int = 1         # places réservées aux petites requêtes / slots kept for small requests
    small_s: float = 0.2
    max_wait_s: float = 10.0
    max_keys: int = 100_000
    idle_s: float = 600.0
    rotate_s: float = 86_400.0      # renouvellement du secret des pseudonymes / pseudonym secret rotation
    grace_s: float = 600.0
    jitter: float = 0.2             # aléa de Retry-After (0 à 20 %) / Retry-After jitter

    def validate(self) -> None:
        if self.mode not in MODES:
            raise ValueError(f"GDPRGUARDIAN_LIMITS ∈ {{{', '.join(MODES)}}}")
        for item in fields(self):
            value = getattr(self, item.name)
            if item.name != "mode" and (not math.isfinite(value) or value < 0):
                raise ValueError(f"{item.name} doit être ≥ 0 / must be ≥ 0")
        positive = ("cost_rate", "cost_burst", "prefix_factor", "cheap_rate", "cheap_burst", "max_running",
                    "max_running_prefix", "max_inflight_prefix", "local_running", "max_keys", "rotate_s")
        for name in positive:
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} doit être > 0 / must be > 0")
        if self.jitter > 1:
            raise ValueError("jitter ≤ 1")
        if self.max_slowness < 1:
            raise ValueError("max_slowness ≥ 1")

    def for_service(self, *, slots: int, longest_job_s: float) -> LimitPolicy:
        """Politique appliquée par un service de `slots` places / policy applied by a service with `slots` slots.

        La dette couvre le plus long travail possible (sinon une partie de son coût serait oubliée) ; un préfixe ne
        fait tourner qu'au plus la moitié des places non réservées (au moins une), si bien que deux préfixes ne
        prennent jamais toutes les places. The debt covers the longest possible job (else part of its cost would be
        forgiven); a prefix runs at most half of the non-reserved slots (at least one), so two prefixes never hold
        every slot.
        """
        reserved = max(0, min(self.reserved_slots, slots - 1))
        return replace(self, cost_debt=max(self.cost_debt, longest_job_s),
                       max_running_prefix=max(1, min(self.max_running_prefix, (slots - reserved) // 2)))

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> LimitPolicy:
        """`GDPRGUARDIAN_LIMITS` (mode) et `GDPRGUARDIAN_LIMIT_<NOM>` (réglages) / mode and tunables."""
        values: dict[str, Any] = {}
        mode = env.get("GDPRGUARDIAN_LIMITS", "").strip().lower()
        if mode:
            values["mode"] = mode
        for item in fields(cls):
            if item.name == "mode":
                continue
            raw = env.get(f"GDPRGUARDIAN_LIMIT_{item.name.upper()}", "").strip()
            if not raw:
                continue
            kind = type(getattr(cls(), item.name))
            try:
                values[item.name] = kind(raw)
            except ValueError:
                raise ValueError(f"GDPRGUARDIAN_LIMIT_{item.name.upper()} : nombre attendu / number expected") from None
        policy = cls(**values)
        policy.validate()
        return policy

    def estimate(self, kind: str, size: int) -> float:
        """Coût estimé d'une requête, en secondes de travailleur / estimated cost in worker-seconds."""
        if kind == FILE:
            return self.file_base_s + self.file_per_mb_s * size / _MB
        return self.text_base_s + self.text_per_mb_s * size / _MB


@dataclass(slots=True)
class Ticket:
    """Réservation d'une requête à contenu, suivie jusqu'à sa fin / a content request's reservation.

    `estimate` : coût pré-imputé, multiplicateur de lenteur compris ; `base` : le même sans lui. `measured` : temps
    de travailleur mesuré (cumul), qui corrige l'estimation à la fin si `worked` (un travailleur a été attribué).
    `waived` : refus de capacité du service (503) avant tout travailleur, l'estimation est rendue. Sinon (corps trop
    lent, trop gros, client parti), l'estimation reste due. `constrained` : les plafonds de l'ordonnanceur
    s'appliquent. `estimate`: pre-charged cost, slowness multiplier included; `base`: the same without it.
    `measured`: worker time measured, which trues up the estimate at the end when `worked` (a worker was granted).
    `waived`: capacity refusal (503) before any worker, the estimate is refunded. Otherwise (body too slow, too large,
    client gone) the estimate stays due. `constrained`: the scheduler's caps apply.
    """

    client: Client
    estimate: float
    small: bool
    constrained: bool
    max_running: int
    max_running_prefix: int
    base: float = 0.0
    charged: bool = False
    counted: bool = False
    counted_prefix: bool = False
    # Délestage reporté au moment de prendre un travailleur (MCP : la plupart des appels n'en prennent aucun, comme le
    # suivi d'un envoi en cours). Shedding deferred to the moment a worker is taken (MCP: most calls take none, such as
    # polling an upload being processed).
    deferred_shed: bool = False
    # Corps reçu, réponse 202 partie, traitement en cours (`mark_processing`) : compté « en traitement ».
    # Body received, 202 sent, processing (`mark_processing`): counted as "processing".
    processing: bool = False
    worked: bool = False
    waived: bool = False
    measured: float = 0.0

    @property
    def principal(self) -> str:
        return self.client.principal

    @property
    def prefix(self) -> int | None:
        return self.client.prefix

    @property
    def local(self) -> bool:
        return self.client.local


@dataclass(frozen=True, slots=True)
class Decision:
    """Issue de l'admission : `status` 0 (admise), 429 ou 503 / admission outcome."""

    status: int = 0
    retry_after: int = 0
    headers: tuple[tuple[bytes, bytes], ...] = ()
    ticket: Ticket | None = None


ALLOW = Decision()


def _rested(row: list[float], now: float) -> bool:
    """Ligne équivalente à une ligne absente : seaux pleins, aucune lenteur retenue / equals an absent row."""
    return max(row[_COST], row[_CHEAP]) <= now and row[_SLOW] <= 1.0


class _Table:
    """État borné par clé de 64 bits : [TAT coût, TAT bon marché, dernière vue, lenteur] / bounded per-key state.

    Clés et lignes dans des listes parallèles (tirage aléatoire en O(1)) ; une ligne reposée (deux TAT passés, aucune
    lenteur retenue) vaut une ligne absente. Plein : les lignes reposées d'un échantillon partent d'abord ; sinon la
    moins chargée de l'échantillon est évincée et la nouvelle clé hérite de son état (Space-Saving : surestimation,
    jamais de budget neuf). Keys and rows in parallel lists (O(1) random draws); a rested row equals an absent one.
    Full: rested rows of a sample go first; else the least loaded of the sample is evicted and the new key inherits
    its state.
    """

    __slots__ = ("_capacity", "_cursor", "_index", "_keys", "_random", "_rows", "overflows")

    def __init__(self, capacity: int) -> None:
        self._capacity = capacity
        self._index: dict[int, int] = {}
        self._keys: list[int] = []
        self._rows: list[list[float]] = []
        self._cursor = 0
        self._random = random.Random()
        self.overflows = 0

    def __len__(self) -> int:
        return len(self._keys)

    def find(self, key: int, previous: int | None = None) -> list[float] | None:
        """Ligne de `key` ; celle de la génération précédente est renommée au passage / previous one migrated."""
        index = self._index.get(key)
        if index is None and previous is not None:
            index = self._index.pop(previous, None)
            if index is not None:
                self._keys[index] = key
                self._index[key] = index
        return None if index is None else self._rows[index]

    def row(self, key: int, previous: int | None, now: float) -> list[float]:
        row = self.find(key, previous)
        if row is None:
            row = self._make_room(now) if len(self._keys) >= self._capacity else [now, now, now, 1.0]
            self._index[key] = len(self._keys)
            self._keys.append(key)
            self._rows.append(row)
        row[_SEEN] = now
        return row

    def _make_room(self, now: float) -> list[float]:
        size = len(self._keys)
        sample = {self._random.randrange(size) for _ in range(min(_SAMPLE, size))}
        rested = sorted((index for index in sample if _rested(self._rows[index], now)), reverse=True)
        for index in rested:  # du plus grand au plus petit : les échanges ne touchent pas les suivants
            self._remove(index)
        if rested:
            return [now, now, now, 1.0]
        self.overflows += 1
        victim = min(sample, key=lambda index: max(self._rows[index][_COST], self._rows[index][_CHEAP]))
        inherited = self._rows[victim]
        self._remove(victim)
        return [max(inherited[_COST], now), max(inherited[_CHEAP], now), now, inherited[_SLOW]]

    def _remove(self, index: int) -> None:
        last = len(self._keys) - 1
        key = self._keys[index]
        del self._index[key]
        if index != last:
            moved = self._keys[last]
            self._keys[index], self._rows[index] = moved, self._rows[last]
            self._index[moved] = index
        self._keys.pop()
        self._rows.pop()

    def sweep(self, now: float, idle_s: float, budget: int) -> None:
        """Examine au plus `budget` lignes et retire les reposées ou inactives, en reprenant où le balayage précédent
        s'est arrêté. Examines at most `budget` rows and drops rested or idle ones, resuming where the last sweep
        stopped."""
        index = self._cursor
        for _ in range(min(budget, len(self._keys))):
            if not self._keys:
                break
            if index >= len(self._keys):
                index = 0
            row = self._rows[index]
            if _rested(row, now) or row[_SEEN] < now - idle_s:
                self._remove(index)  # la dernière ligne prend cette place : examinée ensuite / the last row moves here
            else:
                index += 1
        self._cursor = index


def _wait(tat: float, now: float, rate: float, burst: float, cost: float) -> float:
    """GCRA à coût variable : attente avant admission (0 : admise) / variable-cost GCRA: wait before admission.

    Un coût plus grand que la rafale passe quand le seau est vide / a cost above the burst passes on an empty bucket.
    """
    level = max(0.0, tat - now) * rate
    excess = level + min(cost, burst) - burst
    return 0.0 if excess <= _EPSILON else excess / rate


def _down(value: float) -> int:
    """Entier inférieur, insensible aux erreurs d'arrondi des flottants / floor, robust to float rounding."""
    return max(0, math.floor(value + 1e-6))


def _up(value: float) -> int:
    """Entier supérieur, insensible aux erreurs d'arrondi des flottants / ceiling, robust to float rounding."""
    return max(0, math.ceil(value - 1e-6))


def _charge(row: list[float], slot: int, now: float, rate: float, cost: float, ceiling: float) -> None:
    """Ajoute `cost` (négatif : rend) sous un plafond de niveau `ceiling` / adds `cost` under a level ceiling."""
    row[slot] = min(max(row[slot], now) + cost / rate, now + ceiling / rate)


class Limiter:
    """Décisions d'admission par client et compteurs agrégés / per-client admission decisions, aggregate counters.

    `estimated_wait(principal, small)` : attente estimée pour une requête de ce client (l'ordonnanceur).
    `estimated_wait`: estimated wait for a request from this client (the scheduler).
    """

    def __init__(self, policy: LimitPolicy, *, estimated_wait: Callable[[str, bool], float],
                 typical_job_s: Callable[[], float], clock: Callable[[], float] = time.monotonic) -> None:
        policy.validate()
        self.policy = policy
        self._estimated_wait = estimated_wait
        self._typical_job_s = typical_job_s
        self._clock = clock
        self._clients = _Table(policy.max_keys)
        self._prefixes = _Table(policy.max_keys)
        self._inflight: dict[str, int] = {}
        self._inflight_prefix: dict[int, int] = {}
        # Envois en traitement après leur 202 (corps déjà reçu) / uploads processing after their 202 (body received).
        self._processing: dict[str, int] = {}
        self._processing_prefix: dict[int, int] = {}
        self._lock = threading.Lock()
        self._random = random.Random()
        self._reported_errors = 0
        self._reported_at = -math.inf
        self.counters = {"accepted": 0, "limited": 0, "shed": 0, "dry_run_limited": 0, "errors": 0}

    @property
    def mode(self) -> str:
        return self.policy.mode

    def stats(self) -> dict[str, int]:
        """Compteurs agrégés seulement, jamais par client / aggregate counters only."""
        with self._lock:
            return {**self.counters, "overflows": self._clients.overflows + self._prefixes.overflows,
                    "tracked_clients": len(self._clients), "tracked_prefixes": len(self._prefixes),
                    "in_flight": sum(self._inflight.values()) + sum(self._processing.values())}

    # --- admission ---

    def admit(self, client: Client, *, cheap: bool, content: str | None, size: int, shed: bool = True) -> Decision:
        """Décide AVANT la lecture du corps ; erreur interne : admise (fail open) / decides before the body.

        `shed=False` : pas de délestage sur l'attente estimée ici ; il a lieu si la requête prend un travailleur
        (`shed_wait`, ticket `deferred_shed`). `shed=False`: no shedding on the estimated wait here; it happens if
        the request takes a worker.
        """
        if self.policy.mode == OFF:
            return ALLOW
        try:
            with self._lock:
                return self._admit(client, cheap, content, size, shed)
        except Exception:
            self.counters["errors"] += 1
            return ALLOW

    def shed_wait(self, ticket: Ticket) -> int | None:
        """Délestage reporté : Retry-After si l'attente estimée dépasse le plafond, sinon None.

        Deferred shedding: Retry-After when the estimated wait exceeds the cap, else None.
        """
        if self.policy.mode == OFF:
            return None
        try:
            with self._lock:
                client = ticket.client
                expected = self._estimated_wait(client.principal, ticket.small and not client.local)
                if expected <= self.policy.max_wait_s:
                    return None
                self.counters["shed"] += 1
                return self._retry_after(expected - self.policy.max_wait_s)
        except Exception:
            self.counters["errors"] += 1
            return None

    def inflight_wait(self, ticket: Ticket) -> int | None:
        """Plafond de requêtes en vol reporté : Retry-After s'il est dépassé (la requête elle-même exceptée), sinon
        None. Deferred in-flight cap: Retry-After when exceeded (the request itself aside), else None.
        """
        if self.policy.mode == OFF:
            return None
        try:
            with self._lock:
                client = ticket.client
                if client.local or client.key is None:
                    return None
                if not self._over_inflight(client, own=int(ticket.counted and not ticket.processing),
                                           own_prefix=int(ticket.counted_prefix and not ticket.processing)):
                    return None
                self.counters["limited"] += 1
                return self._retry_after(max(1.0, self._typical_job_s()))
        except Exception:
            self.counters["errors"] += 1
            return None

    def mark_processing(self, ticket: Ticket | None) -> None:
        """Corps reçu et réponse 202 partie : la requête passe des places « corps en vol » à « en traitement ».

        Body received and 202 sent: the request moves from the "body in flight" places to the "processing" ones.
        """
        if ticket is None or self.policy.mode == OFF:
            return
        try:
            with self._lock:
                if ticket.processing or not ticket.counted:
                    return
                client = ticket.client
                ticket.processing = True
                self._release(self._inflight, client.principal)
                self._processing[client.principal] = self._processing.get(client.principal, 0) + 1
                if ticket.counted_prefix:
                    self._release(self._inflight_prefix, client.prefix)
                    self._processing_prefix[client.prefix] = self._processing_prefix.get(client.prefix, 0) + 1
        except Exception:
            self.counters["errors"] += 1

    def _over_inflight(self, client: Client, *, own: int = 0, own_prefix: int = 0, processing: bool = True) -> bool:
        """Plafonds en vol atteints, hors `own` requêtes déjà comptées ; `processing` : envois en traitement compris.

        In-flight caps reached, minus `own` requests already counted; `processing`: uploads processing included.
        """
        policy = self.policy
        count = self._inflight.get(client.principal, 0) - own
        if processing:
            count += self._processing.get(client.principal, 0)
        if count >= policy.max_running + policy.max_queued:
            return True
        if client.prefix is None:
            return False
        prefix_count = self._inflight_prefix.get(client.prefix, 0) - own_prefix
        if processing:
            prefix_count += self._processing_prefix.get(client.prefix, 0)
        return prefix_count >= policy.max_inflight_prefix

    def _admit(self, client: Client, cheap: bool, content: str | None, size: int, shed: bool = True) -> Decision:
        policy = self.policy
        now = self._clock()
        enforce = policy.mode == ENFORCE
        base = policy.estimate(content, size) if content is not None else 0.0
        status, wait = 0, 0.0
        rows: list[tuple[list[float], float]] = []
        tracked = not client.local and client.key is not None
        if tracked:
            rows.append((self._clients.row(client.key, client.previous_key, now), 1.0))
            if client.prefix is not None:
                rows.append((self._prefixes.row(client.prefix, client.previous_prefix, now), policy.prefix_factor))
        # Lenteur observée (client ou préfixe, la plus forte), bornée à la dette : un travail jamais plus cher que
        # le plus long possible. Observed slowness (client or prefix, the larger), bounded by the debt.
        slowness = max((row[_SLOW] for row, _ in rows), default=1.0)
        estimate = min(base * slowness, policy.cost_debt + policy.cost_burst) if content is not None else 0.0
        small = estimate < policy.small_s
        # Plafonds de requêtes en vol (corps compris) : appliqués aussi en dry-run / in-flight caps, dry-run too.
        # Routes à délestage reporté (MCP, création d'envoi) : ici, seules les requêtes dont le corps est en vol
        # comptent (corps lents bornés) ; les envois en traitement après leur 202 comptent à la prise d'un
        # travailleur (`inflight_wait`) : suivre un envoi n'est jamais refusé parce que les envois du client sont en
        # traitement. Deferred-shedding routes: only requests with a body in flight count here (slow bodies stay
        # bounded); uploads processing after their 202 count when a worker is taken: polling is never refused
        # because the client's uploads are processing.
        if tracked and content is not None and self._over_inflight(client, processing=shed):
            status, wait = 429, max(1.0, self._typical_job_s())
        bucket = 0.0
        for row, factor in rows:
            if cheap:
                bucket = max(bucket, _wait(row[_CHEAP], now, policy.cheap_rate * factor, policy.cheap_burst * factor,
                                           1))
            if content is not None:
                bucket = max(bucket, _wait(row[_COST], now, policy.cost_rate * factor, policy.cost_burst * factor,
                                           estimate))
        if not status and bucket > 0:
            if enforce:
                status, wait = 429, bucket
            else:
                self.counters["dry_run_limited"] += 1  # seaux seulement / buckets only
        if not status and content is not None and shed:
            # Le principal LOCAL ne prend jamais la place réservée / LOCAL never takes the reserved slot.
            expected = self._estimated_wait(client.principal, small and not client.local)
            if expected > policy.max_wait_s:
                status, wait = 503, expected - policy.max_wait_s
        if status:
            self.counters["limited" if status == 429 else "shed"] += 1
            return Decision(status, self._retry_after(wait), self._headers(rows, cheap, content, now))
        charged = bucket <= 0
        if charged:
            for row, factor in rows:
                if cheap:
                    _charge(row, _CHEAP, now, policy.cheap_rate * factor, 1, policy.cheap_burst * factor)
                if content is not None:
                    _charge(row, _COST, now, policy.cost_rate * factor, estimate,
                            (policy.cost_burst + policy.cost_debt) * factor)
        headers = self._headers(rows, cheap, content, now)
        ticket = None
        if content is not None:
            ticket = Ticket(client, estimate, small, constrained=True,
                            max_running=policy.local_running if client.local else policy.max_running,
                            max_running_prefix=policy.max_running_prefix, base=base,
                            charged=bool(rows) and charged, deferred_shed=not shed)
            # En dernier : une erreur plus haut ne laisse jamais une place comptée sans fin (fail open).
            # Last: an error above never leaves a counted place that would never end (fail open).
            if not client.local:
                self._inflight[client.principal] = self._inflight.get(client.principal, 0) + 1
                ticket.counted = True
                if client.prefix is not None:
                    self._inflight_prefix[client.prefix] = self._inflight_prefix.get(client.prefix, 0) + 1
                    ticket.counted_prefix = True
        self.counters["accepted"] += 1
        return Decision(0, 0, headers, ticket)

    def finish(self, ticket: Ticket | None) -> None:
        """Fin d'une requête à contenu : place rendue, coût corrigé par la mesure / release and true-up."""
        if ticket is None or self.policy.mode == OFF:
            return
        try:
            with self._lock:
                self._finish(ticket)
        except Exception:
            self.counters["errors"] += 1

    @staticmethod
    def _release(counts: dict[Any, int], key: Any) -> None:
        remaining = counts.get(key, 0) - 1
        if remaining > 0:
            counts[key] = remaining
        else:
            counts.pop(key, None)

    def _finish(self, ticket: Ticket) -> None:
        client = ticket.client
        if ticket.counted:
            ticket.counted = False
            self._release(self._processing if ticket.processing else self._inflight, client.principal)
        if ticket.counted_prefix:
            ticket.counted_prefix = False
            self._release(self._processing_prefix if ticket.processing else self._inflight_prefix, client.prefix)
        if not ticket.charged or client.key is None:
            return
        ticket.charged = False
        policy = self.policy
        if ticket.worked:
            delta = max(ticket.measured, policy.floor_s) - ticket.estimate
        elif ticket.waived:
            delta = policy.floor_s - ticket.estimate  # refus de capacité : rendu / capacity refusal: refunded
        else:
            return  # jamais arrivée à un travailleur : l'estimation reste due / never reached a worker: stays due
        now = self._clock()
        ceiling = now + (policy.cost_burst + policy.cost_debt) / policy.cost_rate  # même durée aux deux niveaux
        # Lenteur : rapport mesure / estimation de base, de 1 à `max_slowness`, en moyenne glissante.
        # Slowness: measured / base estimate ratio, 1 to `max_slowness`, as a moving average.
        ratio = (min(policy.max_slowness, max(1.0, ticket.measured / max(ticket.base, policy.floor_s)))
                 if ticket.worked else None)
        tiers: list[tuple[_Table, int, int | None, float]] = [(self._clients, client.key, client.previous_key, 1.0)]
        if client.prefix is not None:
            tiers.append((self._prefixes, client.prefix, client.previous_prefix, policy.prefix_factor))
        for table, key, previous, factor in tiers:
            rate = policy.cost_rate * factor
            row = table.find(key, previous)
            if row is not None:
                # Comme si le vrai coût avait été imputé à l'admission / as if the true cost had been charged up front.
                row[_COST] = min(row[_COST] + delta / rate, ceiling)
            elif delta > 0 or (ratio is not None and ratio > 1.0):
                # Ligne reposée puis balayée pendant le traitement : le surplus part de maintenant.
                # Row rested then swept during processing: the surplus starts from now.
                row = table.row(key, previous, now)
                _charge(row, _COST, now, rate, max(0.0, delta), (policy.cost_burst + policy.cost_debt) * factor)
            if row is not None and ratio is not None:
                row[_SLOW] = 0.5 * row[_SLOW] + 0.5 * ratio

    def sweep(self, budget: int = 20_000) -> None:
        """Retire les clés reposées ou inactives (balayage périodique, borné) ; signale les erreurs internes.

        Drops rested or idle keys (periodic, bounded sweep); reports internal errors: an aggregate WARNING at most
        once a minute while the count grows (the limiter fails open, so a silent bug would disable it).
        """
        if self.policy.mode == OFF:
            return
        try:
            with self._lock:
                now = self._clock()
                self._clients.sweep(now, self.policy.idle_s, budget)
                self._prefixes.sweep(now, self.policy.idle_s, budget)
        except Exception:
            self.counters["errors"] += 1
        self.report_errors()

    def report_errors(self) -> None:
        """Avertissement agrégé si des erreurs internes sont apparues (au plus une fois par minute).

        Aggregate warning when internal errors appeared (at most once a minute): total and new ones, nothing else.
        """
        errors = self.counters["errors"]
        now = self._clock()
        if errors > self._reported_errors and now - self._reported_at >= _ERROR_REPORT_S:
            log_event("limiter_errors", logging.WARNING, total=errors, new=errors - self._reported_errors)
            self._reported_errors, self._reported_at = errors, now

    # --- signalement / signalling ---

    def _retry_after(self, wait: float) -> int:
        """Secondes entières, avec 0 à `jitter` d'aléa : les clients refusés ne reviennent pas ensemble.

        Whole seconds, with 0 to `jitter` random extra: refused clients do not come back together.
        """
        jittered = wait * (1.0 + self._random.uniform(0.0, self.policy.jitter))
        return max(1, min(_MAX_RETRY_AFTER, math.ceil(jittered)))

    def _headers(self, rows: list[tuple[list[float], float]], cheap: bool, content: str | None,
                 now: float) -> tuple[tuple[bytes, bytes], ...]:
        """RateLimit-Policy et RateLimit (brouillon IETF httpapi-ratelimit-headers-11), au mieux, niveau client.

        RateLimit-Policy and RateLimit (IETF draft -11), best effort, client tier. « worker-ms » n'est pas une unité
        enregistrée : seul Retry-After fait foi / "worker-ms" is not a registered unit: Retry-After is authoritative.
        """
        if not rows:
            return ()
        policy = self.policy
        row = rows[0][0]
        policies: list[str] = []
        states: list[str] = []
        if cheap:
            level = max(0.0, row[_CHEAP] - now) * policy.cheap_rate
            policies.append(f'"req";q={int(policy.cheap_burst)};w={_up(policy.cheap_burst / policy.cheap_rate)}')
            states.append(f'"req";r={_down(policy.cheap_burst - level)};t={_up(level / policy.cheap_rate)}')
        if content is not None:
            level = max(0.0, row[_COST] - now) * policy.cost_rate
            policies.append(f'"cpu";q={_down(policy.cost_burst * 1000)};qu="worker-ms";'
                            f'w={_up(policy.cost_burst / policy.cost_rate)}')
            states.append(f'"cpu";r={_down((policy.cost_burst - level) * 1000)};t={_up(level / policy.cost_rate)}')
        return ((b"ratelimit-policy", ", ".join(policies).encode("ascii")),
                (b"ratelimit", ", ".join(states).encode("ascii")))


__all__ = ["ALLOW", "DRY_RUN", "ENFORCE", "FILE", "MODES", "OFF", "TEXT", "Decision", "LimitPolicy", "Limiter",
           "Ticket"]
