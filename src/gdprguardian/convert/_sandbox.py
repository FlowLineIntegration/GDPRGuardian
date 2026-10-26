"""Bac à sable : tout document est lu dans un processus isolé / sandbox: documents are read in isolated processes.

Deux usages / two uses
    Bibliothèque : `run()` convertit dans un travailleur réutilisable (`SandboxConfig.max_jobs_per_worker`).
    Service : `WorkerPool(single_use=True)` traite chaque requête de bout en bout dans un processus neuf, qui
    meurt ensuite. Library: `run()` converts in a reusable worker. Service: `WorkerPool(single_use=True)`
    processes each request end to end in a fresh process that dies afterwards.

Naissance des travailleurs / how workers are born
    Linux : un zygote, lancé une fois, durci et préchargé (packs, automates, noyau Rust, lexiques,
    convertisseurs), crée chaque travailleur par fork en quelques millisecondes ; sa mémoire est partagée en
    copie à l'écriture. Il ne voit jamais de document, n'a qu'un fil d'exécution (sinon il lance des
    interpréteurs neufs) et tue lui-même ses enfants : aucun signal ne vise un PID recyclé. Windows et macOS :
    lancement « spawn » ; sous Windows, un Job Object plafonne la mémoire, interdit tout sous-processus et tue
    le travailleur si le parent disparaît. Le processus principal, lui, ne fait jamais de fork (il a plusieurs
    fils d'exécution).
    Linux: a zygote, started once, hardened and preloaded, forks each worker in milliseconds, its memory
    shared copy-on-write. It never sees a document, keeps a single thread (else it launches fresh
    interpreters) and kills its own children: no signal ever targets a recycled PID. Windows and macOS:
    "spawn"; on Windows a Job Object caps memory, forbids child processes and kills the worker if the parent
    dies. The main process itself never forks (it has several threads).

Confinement / confinement
    Avant tout document : aucune sortie standard, aucune variable GDPRGUARDIAN_*, processus non lisible
    (PR_SET_DUMPABLE=0), sans core dump ni droit de créer un processus, mémoire et CPU plafonnés, tué à
    l'échéance. Réponses : JSON borné (plus, au besoin, un texte UTF-8 brut), jamais de pickle : un analyseur
    compromis ne peut pas faire exécuter de code au parent. Aucun contenu dans les messages d'erreur.
    Before any document: no standard output, no GDPRGUARDIAN_* variable, non-dumpable process without core
    dumps or the right to create processes, capped memory and CPU, killed at the deadline. Replies are
    bounded JSON (plus, when needed, raw UTF-8 text), never pickle; error messages carry no content.
"""

from __future__ import annotations

import atexit
import contextlib
import gc
import heapq
import importlib
import itertools
import json
import multiprocessing
import os
import signal
import socket
import stat
import sys
import threading
import time
import weakref
from dataclasses import dataclass, replace
from functools import cache
from multiprocessing import reduction
from multiprocessing.connection import Connection, wait
from typing import Any, NoReturn

from ..documents import (
    ConversionTimeoutError,
    DocumentError,
    DocumentTooLargeError,
    EncryptedDocumentError,
    MaliciousDocumentError,
    UnsupportedFormatError,
)
from ._base import CRASH_MESSAGE, FAILURE_MESSAGE, START_MESSAGE, guarded

_ERRORS: dict[str, type[DocumentError]] = {cls.__name__: cls for cls in (
    DocumentError, UnsupportedFormatError, DocumentTooLargeError, EncryptedDocumentError, MaliciousDocumentError,
    ConversionTimeoutError)}
_MAX_ERROR = 1000  # longueur d'un message d'erreur reçu / length of a received error message
_MAX_REPLY = 1 << 30
_MAX_CONTROL = 4096  # message de contrôle (prêt, fork, kill) / control message (ready, fork, kill)
_PARALLEL_STARTS = 4  # démarrages simultanés pour la réserve / concurrent starts for the reserve
_RETRY_START_S = 1.0  # pause après un démarrage refusé / pause after a refused start
_ZYGOTE_POLL_S = 0.2  # rythme de ramassage des enfants du zygote / zygote reaping period
# Linux : travailleurs nés du zygote ; ailleurs, lancés directement / Linux: workers born from the zygote.
ZYGOTE = sys.platform.startswith("linux")
CANCELLED_MESSAGE = "Traitement annulé / processing cancelled"


@dataclass(frozen=True, slots=True)
class SandboxConfig:
    """Réglages du bac à sable / sandbox settings.

    `max_jobs_per_worker=1` : un processus neuf par document (isolation maximale). `memory_mb` : mémoire
    accordée au document, au-delà de l'empreinte du travailleur au repos (0 : sans plafond). `preload` :
    « module:fonction » exécutée une fois avant tout document (dans le zygote, sinon dans chaque travailleur).
    `prime` : « module:fonction » exécutée sur des données fictives par chaque travailleur créé pour la
    réserve, avant de se déclarer prêt : les pages copiées à l'écriture le sont pendant l'attente, pas pendant
    la requête (un travailleur créé à la demande, réserve vide, s'en passe). `fork_workers=False` : le zygote
    lance des interpréteurs neufs au lieu de fork (repli, tests).
    `max_jobs_per_worker=1` gives a fresh process per document. `memory_mb`: memory granted to the document
    on top of the idle worker's footprint (0: no cap). `preload`: "module:function" run once before any
    document. `prime`: "module:function" each reserve worker runs on fictitious data before reporting ready,
    so copy-on-write page faults happen while it waits, not during the request (a worker created on demand,
    with an empty reserve, skips it). `fork_workers=False`: the zygote launches fresh interpreters instead of
    forking.
    """

    max_idle_workers: int = 2
    max_jobs_per_worker: int = 32
    memory_mb: int = 2048
    startup_timeout_s: float = 60.0
    preload: str | None = None
    prime: str | None = None
    fork_workers: bool = True


@dataclass(frozen=True, slots=True)
class _Settings:
    """Ce que reçoit un travailleur à sa naissance / what a worker receives at birth."""

    memory_mb: int
    preload: str | None
    prime: str | None
    single_use: bool
    parent_pid: int


class WorkerStartError(DocumentError):
    """Aucun travailleur n'a pu démarrer (ressources du système) / no worker could start (system resources)."""


class Body:
    """Réponse portant un grand texte, transmis brut après l'en-tête JSON : ni échappement ni analyse JSON.

    Reply carrying a large text, sent raw after the JSON header: no JSON escaping nor parsing.
    """

    __slots__ = ("meta", "text")

    def __init__(self, meta: Any, text: str) -> None:
        self.meta = meta
        self.text = text


class CancelHandle:
    """Annule un appel depuis un autre fil : le travailleur est tué / cancels a call from another thread.

    Sûr à tout moment : avant l'attribution d'un travailleur, pendant le travail ou après / safe at any time.
    """

    __slots__ = ("_cancelled", "_lock", "_worker")

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._worker: _Worker | None = None
        self._cancelled = False

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    def cancel(self) -> None:
        with self._lock:
            self._cancelled = True
            worker = self._worker
        if worker is not None:
            worker.cancel()

    def _attach(self, worker: _Worker) -> bool:
        with self._lock:
            if self._cancelled:
                return False
            self._worker = worker
            return True

    def _detach(self) -> None:
        with self._lock:
            self._worker = None


# --- protocole / protocol ----------------------------------------------------------------------------


def _encode(reply: tuple[Any, ...]) -> bytes:
    return json.dumps(reply, ensure_ascii=False).encode("utf-8", "surrogatepass")


def _decode(raw: bytes, *statuses: str) -> list[Any]:
    """Réponse JSON du travailleur, forme vérifiée : [statut, valeur] ou ["error", classe, message, recycler].

    Worker JSON reply, shape checked: [status, value] or ["error", class, message, recycle].
    """
    try:
        reply = json.loads(raw.decode("utf-8", "surrogatepass"))
    except (ValueError, RecursionError):  # l'erreur garde le texte reçu : jamais chaînée / holds the input
        reply = None
    if not isinstance(reply, list) or not reply or reply[0] not in statuses:
        raise DocumentError(CRASH_MESSAGE)
    if reply[0] != "error" and len(reply) == 2:
        return reply
    if len(reply) == 4 and isinstance(reply[1], str) and isinstance(reply[2], str) and isinstance(reply[3], bool):
        return reply
    raise DocumentError(CRASH_MESSAGE)


def _text(raw: bytes) -> str:
    """Texte brut d'une réponse « body » (UTF-8 strict) / raw text of a "body" reply (strict UTF-8)."""
    try:
        text: str | None = raw.decode("utf-8", "surrogatepass")
    except UnicodeDecodeError:  # l'erreur garde les octets reçus : jamais chaînée / holds the input
        text = None
    if text is None:
        raise DocumentError(CRASH_MESSAGE)
    return text


def _read_reply(conn: Connection, max_reply: int) -> list[Any]:
    """Lit une réponse complète ; « body » : [statut, méta, texte] / reads a whole reply."""
    reply = _decode(conn.recv_bytes(max_reply), "ok", "body", "error")
    if reply[0] == "body":
        reply.append(_text(conn.recv_bytes(max_reply)))
    return reply


def _outcome(reply: list[Any]) -> Any:
    if reply[0] == "ok":
        return reply[1]
    if reply[0] == "body":
        return Body(reply[1], reply[2])
    raise _ERRORS.get(reply[1], DocumentError)(reply[2][:_MAX_ERROR])


def _call(target: str, *args: Any) -> Any:
    module_name, _, function_name = target.partition(":")
    return getattr(importlib.import_module(module_name), function_name)(*args)


def _execute(target: str, payload: bytes | None, args: tuple[Any, ...]) -> list[bytes]:
    """Exécute la cible ; trames de la réponse (JSON, puis texte brut éventuel) / runs the target; reply frames."""
    try:
        value = guarded(_call, target, *(args if payload is None else (payload, *args)))
        if isinstance(value, Body):
            return [_encode(("body", value.meta)), value.text.encode("utf-8", "surrogatepass")]
        return [_encode(("ok", value))]
    except DocumentError as exc:
        # Erreur prévue : le travailleur reste sain, sauf erreur générique d'analyse.
        # Expected error: the worker stays healthy, except after a generic parser failure.
        return [_encode(("error", type(exc).__name__, str(exc), getattr(exc, "recycle", False)))]
    except (TypeError, ValueError):  # résultat non sérialisable / unserialisable result
        return [_encode(("error", DocumentError.__name__, FAILURE_MESSAGE, True))]


def run_inline(target: str, payload: bytes | bytearray | None, args: tuple[Any, ...],
               max_reply: int = _MAX_REPLY) -> Any:
    """Même protocole sans processus (tests, intégration) : mêmes trames, mêmes contrôles côté parent.

    Same protocol without a process (tests, embedding): same frames, same parent-side checks.
    """
    frames = _execute(target, None if payload is None else bytes(payload), args)
    if any(len(frame) > max_reply for frame in frames):
        raise DocumentError(CRASH_MESSAGE)
    reply = _decode(frames[0], "ok", "body", "error")
    if reply[0] == "body":
        reply.append(_text(frames[1]))
    return _outcome(reply)


# --- côté travailleur / worker side -----------------------------------------------------------------


def _confine() -> None:
    """Avant tout document : ni sortie, ni secret, ni journal, ni Ctrl+C / before any document.

    L'arrêt est piloté par le parent : un Ctrl+C du terminal n'interrompt pas un travail en cours.
    Shutdown is driven by the parent: a terminal Ctrl+C does not interrupt a running job.
    """
    import logging
    import warnings

    from .._hardening import scrub_environment, silence_stdio

    silence_stdio()
    scrub_environment(prefix="GDPRGUARDIAN_")
    logging.disable(logging.CRITICAL)  # aucun journal dans le travailleur / no logging in the worker
    warnings.simplefilter("ignore")
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def _preload(target: str | None) -> bool:
    """Précharge au mieux (code de confiance, aucun document) / best-effort preload (trusted code, no document)."""
    if target is None:
        return True
    try:
        _call(target)
    except Exception:
        return False  # les modules se chargeront à la demande / modules will load on demand
    return True


def _serve(conn: Connection, settings: _Settings, forked_from: int | None = None) -> NoReturn:
    """Boucle du travailleur : une requête à la fois ; ne rend jamais la main / worker loop; never returns.

    `forked_from` : PID du zygote, pour un travailleur né par fork (déjà confiné et préchargé).
    `forked_from`: the zygote's PID, for a forked worker (already confined and preloaded).
    """
    try:
        _prefer_oom_kill()
        if forked_from is None:
            _confine()
            _preload(settings.preload)
        _preload(settings.prime)  # données fictives, aucun document / fictitious data, no document
        from .._hardening import harden_process

        # Non lisible, sans enfant, mort avec son parent / unreadable, childless, dies with its parent.
        harden_process(die_with_parent=forked_from or settings.parent_pid, forbid_children=True)
        _limit_posix_memory(settings.memory_mb)
        conn.send_bytes(_encode(("ready", os.getpid())))
        while True:
            try:
                target, args, timeout_s, has_payload = conn.recv()  # du parent, de confiance / from the parent
                payload = conn.recv_bytes() if has_payload else None
            except (EOFError, OSError):
                break  # parent disparu : fin du travailleur / parent gone: worker ends
            _limit_posix_cpu(timeout_s)
            frames = _execute(target, payload, args)
            target = args = payload = None  # le document ne survit pas à la réponse / dropped before replying
            for frame in frames:
                conn.send_bytes(frame)
            frames = []
            if settings.single_use:
                break
    finally:
        # Sortie immédiate : ni finaliseurs ni tampons hérités du zygote / no finalizers nor inherited buffers.
        os._exit(0)


def _prefer_oom_kill() -> None:
    """Linux : ce travailleur est la victime préférée du tueur OOM (score 1000), avant le service et le zygote.

    Linux: this worker is the OOM killer's preferred victim (score 1000), ahead of the service and the zygote. Une
    saturation de la mémoire du conteneur ne coûte alors qu'une requête, jamais le service entier. Relever son propre
    score ne demande aucun droit. A container memory saturation then costs one request, never the whole service.
    Raising one's own score needs no privilege.
    """
    if not sys.platform.startswith("linux"):
        return
    try:
        with open("/proc/self/oom_score_adj", "w", encoding="ascii") as handle:
            handle.write("1000")
    except OSError:
        pass  # /proc absent ou en lecture seule : le plafond RLIMIT_AS reste / RLIMIT_AS still applies


def _address_space() -> int:
    """Espace d'adressage actuel en octets (Linux), 0 ailleurs / current address space in bytes (Linux)."""
    try:
        with open("/proc/self/statm", encoding="ascii") as handle:
            return int(handle.read().split()[0]) * os.sysconf("SC_PAGE_SIZE")
    except (OSError, ValueError, IndexError):
        return 0


def _limit_posix_memory(memory_mb: int) -> None:
    """Plafond d'espace d'adressage : empreinte actuelle + `memory_mb` ; aucun core dump.

    Address-space cap: current footprint + `memory_mb`; no core dump.
    """
    if os.name != "posix":
        return
    import resource

    limits = [(resource.RLIMIT_CORE, 0)]
    if memory_mb > 0:
        limits.append((resource.RLIMIT_AS, _address_space() + (memory_mb << 20)))
    for limit, value in limits:
        try:
            _soft, hard = resource.getrlimit(limit)
            value = value if hard == resource.RLIM_INFINITY else min(value, hard)
            resource.setrlimit(limit, (value, value))  # plafond dur, irréversible / hard cap, irreversible
        except (ValueError, OSError):
            pass  # macOS : RLIMIT_AS parfois refusé ; le délai reste appliqué / timeout still applies


def _limit_posix_cpu(timeout_s: float | None) -> None:
    """Plafond CPU glissant : temps déjà consommé + délai / sliding CPU cap: time used so far + timeout."""
    if os.name != "posix" or not timeout_s:
        return
    import resource

    try:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        _soft, hard = resource.getrlimit(resource.RLIMIT_CPU)
        soft = int(usage.ru_utime + usage.ru_stime + timeout_s) + 5
        resource.setrlimit(resource.RLIMIT_CPU, (soft if hard == resource.RLIM_INFINITY else min(soft, hard), hard))
    except (ValueError, OSError):
        pass


# --- zygote (Linux) ----------------------------------------------------------------------------------


def _os_threads() -> int:
    """Fils d'exécution du système (pas seulement Python) / OS threads (not only Python ones)."""
    try:
        return len(os.listdir("/proc/self/task"))
    except OSError:
        return threading.active_count()


def _zygote(control: Connection, kills: Connection, settings: _Settings, fork: bool) -> NoReturn:
    """Zygote : préchargé une fois, il ne fait que créer et tuer des travailleurs à la demande du parent.

    Zygote: preloaded once, it only creates and kills workers when the parent asks. Deux canaux : `control`
    (fork, avec réponse) et `kills` (sans réponse, jamais en attente derrière un fork). Il s'arrête quand le
    parent ferme un canal ; ses enfants meurent alors avec lui (PDEATHSIG). Two channels: `control` (fork,
    answered) and `kills` (one-way, never queued behind a fork). It stops when the parent closes a channel;
    its children then die with it (PDEATHSIG).
    """
    children: dict[int, Any] = {}  # PID -> None (fork) ou Process (spawn)
    try:
        _confine()
        from .._hardening import harden_process

        harden_process()  # non lisible, sans core dump / unreadable, no core dump
        # Processus « daemon » pour multiprocessing, mais il doit pouvoir lancer des travailleurs (repli spawn).
        # A multiprocessing "daemon", yet it must be able to launch workers (spawn fallback).
        multiprocessing.current_process()._config["daemon"] = False
        preloaded = _preload(settings.preload)
        gc.collect()
        gc.freeze()  # objets préchargés hors du ramasse-miettes : pages partagées intactes / shared pages intact
        # fork seulement sans autre fil d'exécution (un verrou tenu ailleurs serait copié fermé à jamais).
        # fork only without any other thread (a lock held elsewhere would be copied locked forever).
        fork = fork and _os_threads() == 1
        control.send_bytes(_encode(("ready", {"pid": os.getpid(), "fork": fork, "preloaded": preloaded})))
        unprimed = replace(settings, prime=None)
        while True:
            for channel in wait([control, kills], _ZYGOTE_POLL_S):
                command = _command(channel.recv_bytes(_MAX_CONTROL))
                if channel is control and command is not None and command[0] == "fork":
                    _make_child((control, kills), children, settings if command[1] else unprimed, fork)
                elif channel is kills and command is not None and command[0] == "kill":
                    _kill_child(children, command[1])
            _reap(children, fork)
    except (EOFError, OSError):
        pass  # parent disparu ou canal fermé / parent gone or channel closed
    finally:
        os._exit(0)


def _command(raw: bytes) -> tuple[str, int | bool] | None:
    """Commande du parent : ["fork", amorcer] ou ["kill", pid] / parent command: ["fork", prime] or ["kill", pid]."""
    try:
        command = json.loads(raw)
    except ValueError:
        return None
    if not (isinstance(command, list) and len(command) == 2):
        return None
    if command[0] == "fork" and type(command[1]) is bool:
        return ("fork", command[1])
    if command[0] == "kill" and type(command[1]) is int:
        return ("kill", command[1])
    return None


def _make_child(channels: tuple[Connection, Connection], children: dict[int, Any], settings: _Settings,
                fork: bool) -> None:
    """Crée un travailleur relié au parent par une paire de sockets / creates a worker wired to the parent."""
    control = channels[0]
    ours, theirs = socket.socketpair()
    try:
        try:
            if fork:
                zygote = os.getpid()
                pid = os.fork()
                if pid == 0:
                    ours.close()
                    _forked_worker(channels, theirs, settings, zygote)
                children[pid] = None
            else:
                child = Connection(os.dup(theirs.fileno()))
                try:
                    process = multiprocessing.get_context("spawn").Process(
                        target=_serve, args=(child, replace(settings, parent_pid=os.getpid())),
                        name="gdprguardian-worker", daemon=True)
                    process.start()
                finally:
                    child.close()
                pid = process.pid
                children[pid] = process
        except OSError:  # fork ou lancement refusé (ressources) / fork or launch refused (resources)
            control.send_bytes(_encode(("error", WorkerStartError.__name__, START_MESSAGE, False)))
            return
        control.send_bytes(_encode(("forked", pid)))
        reduction.send_handle(control, ours.fileno(), 0)
    finally:
        ours.close()
        theirs.close()


def _forked_worker(channels: tuple[Connection, ...], sock: socket.socket, settings: _Settings,
                   zygote: int) -> NoReturn:
    """Enfant du zygote : coupe tout canal hérité, puis sert / zygote child: drops inherited channels, serves."""
    try:
        for channel in channels:
            channel.close()  # plus aucun accès au zygote / no way back to the zygote
        own = sock.detach()
        _close_inherited_channels(own)
        _serve(Connection(own), settings, forked_from=zygote)
    finally:
        os._exit(1)


def _close_inherited_channels(keep: int) -> None:
    """Ferme sockets et tubes hérités (outils de multiprocessing…), sauf le sien.

    Closes inherited sockets and pipes (multiprocessing helpers…), except its own.
    """
    try:
        descriptors = [int(name) for name in os.listdir("/proc/self/fd")]
    except (OSError, ValueError):
        return
    for fd in descriptors:
        if fd <= 2 or fd == keep:
            continue
        try:
            mode = os.fstat(fd).st_mode
        except OSError:
            continue  # descripteur du listage, déjà fermé / the listing's own descriptor, already closed
        if stat.S_ISSOCK(mode) or stat.S_ISFIFO(mode):
            os.close(fd)


def _kill_child(children: dict[int, Any], pid: int) -> None:
    """Tue un enfant que ce zygote n'a pas encore ramassé : tant qu'il ne l'est pas, son PID ne peut pas être
    recyclé, et un PID ramassé est ignoré. Kills a child this zygote has not reaped yet: until then its PID
    cannot be recycled, and a reaped PID is ignored (same single-threaded loop for both).
    """
    if pid not in children:
        return
    process = children[pid]
    if process is not None:
        process.kill()
        return
    with contextlib.suppress(ProcessLookupError):
        os.kill(pid, signal.SIGKILL)


def _reap(children: dict[int, Any], fork: bool) -> None:
    """Ramasse les enfants terminés (aucun zombie durable) / reaps finished children (no lingering zombie)."""
    if not fork:
        for pid, process in list(children.items()):
            if not process.is_alive():
                del children[pid]
        return
    while children:
        try:
            pid, _status = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            children.clear()
            return
        if pid == 0:
            return
        children.pop(pid, None)


class _Zygote:
    """Côté parent : le zygote et ses deux canaux / parent side: the zygote and its two channels."""

    def __init__(self, settings: _Settings, fork: bool, timeout_s: float) -> None:
        context = multiprocessing.get_context("spawn")
        try:
            parent_conn, child_conn = context.Pipe(duplex=True)
        except OSError:
            raise WorkerStartError(START_MESSAGE) from None
        try:
            kill_reader, kill_writer = context.Pipe(duplex=False)
        except OSError:
            parent_conn.close()
            child_conn.close()
            raise WorkerStartError(START_MESSAGE) from None
        self.process = context.Process(target=_zygote, args=(child_conn, kill_reader, settings, fork),
                                       name="gdprguardian-zygote", daemon=True)
        try:
            self.process.start()
        except OSError:
            parent_conn.close()
            kill_writer.close()
            raise WorkerStartError(START_MESSAGE) from None
        finally:
            child_conn.close()
            kill_reader.close()
        self.conn = parent_conn
        self.kills = kill_writer
        self.lock = threading.Lock()
        self.kill_lock = threading.Lock()
        self.timeout_s = timeout_s
        self.broken = False
        try:
            ready = parent_conn.poll(timeout_s) and _decode(parent_conn.recv_bytes(_MAX_CONTROL), "ready")
        except (EOFError, OSError, DocumentError):
            ready = False
        info = ready[1] if ready else None
        if not (isinstance(info, dict) and type(info.get("pid")) is int and type(info.get("fork")) is bool
                and type(info.get("preloaded")) is bool):
            self.close()
            raise WorkerStartError(START_MESSAGE)
        self.forks: bool = info["fork"]
        self.preloaded: bool = info["preloaded"]

    def spawn(self, prime: bool) -> tuple[Connection, int]:
        """Un travailleur neuf, amorcé ou non : son canal et son PID / a fresh worker, primed or not."""
        with self.lock:
            try:
                self.conn.send_bytes(_encode(("fork", prime)))
                reply = (_decode(self.conn.recv_bytes(_MAX_CONTROL), "forked", "error")
                         if self.conn.poll(self.timeout_s) else None)
                if reply is not None and reply[0] == "forked":
                    handle = reduction.recv_handle(self.conn)
                    if type(reply[1]) is int:
                        return Connection(handle), reply[1]
                    os.close(handle)
                    reply = None
            except (EOFError, OSError, RuntimeError, AssertionError, DocumentError):  # recv_handle / recvfds
                reply = None
            if reply is None:
                self.broken = True  # canal désynchronisé ou zygote mort / channel out of sync or zygote dead
            raise WorkerStartError(START_MESSAGE)  # fork refusé (ressources) / fork refused (resources)

    def kill(self, pid: int) -> None:
        """Fait tuer un travailleur, sans attendre / has a worker killed, without waiting."""
        with self.kill_lock:
            try:
                self.kills.send_bytes(_encode(("kill", pid)))
            except OSError:
                self.broken = True  # zygote mort : ses enfants aussi / zygote dead: so are its children

    def close(self) -> None:
        """Arrêt immédiat ; ses travailleurs meurent avec lui / immediate stop; its workers die with it."""
        if self.process.is_alive():
            self.process.kill()
        self.process.join(5.0)
        with self.lock, self.kill_lock:
            self.conn.close()
            self.kills.close()


# --- travailleurs vus du parent / workers seen from the parent --------------------------------------


class _Watchdog:
    """Un seul fil surveille toutes les échéances, sans minuteur ni fil par appel.

    One thread watches every deadline, with no timer nor thread per call. Il tue le travailleur à l'échéance,
    même au milieu d'un envoi ou d'une réception : aucun appel ne dépasse son délai. It kills the worker at
    the deadline, even mid-send or mid-receive: no call outlives its timeout.
    """

    def __init__(self) -> None:
        self._cond = threading.Condition()
        self._heap: list[tuple[float, int, _Worker]] = []
        self._armed: set[int] = set()
        self._tokens = itertools.count()
        self._thread: threading.Thread | None = None

    def arm(self, worker: _Worker, timeout_s: float) -> int:
        token = next(self._tokens)
        with self._cond:
            heapq.heappush(self._heap, (time.monotonic() + timeout_s, token, worker))
            self._armed.add(token)
            if self._thread is None:
                self._thread = threading.Thread(target=self._run, name="gdprguardian-watchdog", daemon=True)
                self._thread.start()
            self._cond.notify()
        return token

    def disarm(self, token: int) -> None:
        with self._cond:
            self._armed.discard(token)

    def _run(self) -> None:
        while True:
            expired: list[_Worker] = []
            with self._cond:
                while not expired:
                    now = time.monotonic()
                    # Échues ou désarmées en tête de tas : retirées / due or disarmed at the top: removed.
                    while self._heap and (self._heap[0][0] <= now or self._heap[0][1] not in self._armed):
                        _deadline, token, worker = heapq.heappop(self._heap)
                        if token in self._armed:
                            self._armed.discard(token)
                            expired.append(worker)
                    if not expired:
                        self._cond.wait(self._heap[0][0] - now if self._heap else None)
            for worker in expired:  # hors du verrou : tuer peut écrire au zygote / outside the lock
                worker._expire()


_WATCHDOG = _Watchdog()


def _reset_watchdog() -> None:
    # Après un fork, le fil du chien de garde n'existe plus dans l'enfant / after a fork, no watchdog thread.
    global _WATCHDOG
    _WATCHDOG = _Watchdog()


if hasattr(os, "register_at_fork"):  # POSIX
    os.register_at_fork(after_in_child=_reset_watchdog)


class _Worker:
    """Travailleur vu du parent : une requête à la fois, sous chien de garde / worker seen from the parent."""

    __slots__ = ("busy", "cancelled", "conn", "expired", "jobs", "lock", "pid")

    def __init__(self, conn: Connection, pid: int) -> None:
        self.conn = conn
        self.pid = pid
        self.jobs = 0
        self.lock = threading.Lock()
        self.busy = self.expired = self.cancelled = False

    def _await_ready(self, timeout_s: float) -> None:
        try:
            ready = self.conn.poll(timeout_s) and bool(_decode(self.conn.recv_bytes(256), "ready"))
        except (EOFError, OSError, DocumentError):
            ready = False
        if not ready:
            self.close()
            raise WorkerStartError(START_MESSAGE)

    def call(self, target: str, payload: bytes | bytearray | None, args: tuple[Any, ...], timeout_s: float | None,
             max_reply: int) -> list[Any]:
        self.jobs += 1
        with self.lock:
            if self.cancelled:
                raise DocumentError(CANCELLED_MESSAGE)
            self.busy = True
        watchdog = _WATCHDOG
        token = watchdog.arm(self, timeout_s) if timeout_s is not None else None
        try:
            self.conn.send((target, args, timeout_s, payload is not None))
            if payload is not None:
                self.conn.send_bytes(payload)
            return _read_reply(self.conn, max_reply)
        except (EOFError, OSError):
            if self.expired:
                raise ConversionTimeoutError(f"Conversion interrompue après {timeout_s:g} s / conversion timed "
                                             f"out after {timeout_s:g} s") from None
            if self.cancelled:
                raise DocumentError(CANCELLED_MESSAGE) from None
            raise DocumentError(CRASH_MESSAGE) from None
        finally:
            with self.lock:
                self.busy = False  # d'abord : un chien de garde en retard ne tue rien / a late watchdog kills nothing
            if token is not None:
                watchdog.disarm(token)

    def _expire(self) -> None:
        with self.lock:
            if self.busy:  # jamais après la fin de l'appel / never once the call is over
                self.expired = True
                self.kill()

    def cancel(self) -> None:
        with self.lock:
            self.cancelled = True
            if self.busy:
                self.kill()

    def kill(self) -> None:
        raise NotImplementedError

    def alive(self) -> bool:
        raise NotImplementedError

    def close(self) -> None:
        """Arrêt immédiat, quel que soit son état / immediate stop, whatever its state."""
        raise NotImplementedError

    def release(self) -> None:
        """Fin normale d'un travailleur à usage unique qui a répondu : il se termine seul.

        Normal end of a single-use worker that has replied: it exits on its own.
        """
        self.close()


class _SpawnedWorker(_Worker):
    """Interpréteur neuf (Windows, macOS) / fresh interpreter (Windows, macOS)."""

    __slots__ = ("job", "process")

    def __init__(self, settings: _Settings, config: SandboxConfig) -> None:
        context = multiprocessing.get_context("spawn")
        try:
            parent_conn, child_conn = context.Pipe(duplex=True)
        except OSError:  # ressources épuisées : l'API ne lève que des DocumentError / API raises DocumentError only
            raise WorkerStartError(START_MESSAGE) from None
        self.process = context.Process(target=_serve, args=(child_conn, settings), name="gdprguardian-worker",
                                       daemon=True)
        try:
            self.process.start()
        except OSError:
            parent_conn.close()
            raise WorkerStartError(START_MESSAGE) from None
        finally:
            child_conn.close()  # sinon un travailleur mort ne produit jamais EOF / else a dead worker never yields EOF
        super().__init__(parent_conn, self.process.pid or 0)
        self.job = _windows_job(self.pid, config.memory_mb) if os.name == "nt" else None
        if os.name == "nt" and self.job is None:
            # Jamais de travailleur sans confinement : échec fermé / never an unconfined worker: fail closed.
            self.close()
            raise WorkerStartError(START_MESSAGE)
        self._await_ready(config.startup_timeout_s)
        if self.job is not None and config.memory_mb > 0 and not _windows_rebase(self.job, config.memory_mb):
            self.close()
            raise WorkerStartError(START_MESSAGE)

    def kill(self) -> None:
        self.process.kill()

    def alive(self) -> bool:
        return self.process.is_alive()

    def close(self) -> None:
        """Arrêt immédiat : un travailleur inactif n'a rien à perdre / immediate stop: an idle worker loses nothing."""
        self._stop(join=True)

    def release(self) -> None:
        # Tué sans attendre sa fin : multiprocessing le ramasse au prochain lancement.
        # Killed without waiting for it: multiprocessing reaps it at the next launch.
        self._stop(join=False)

    def _stop(self, *, join: bool) -> None:
        if self.process.is_alive():
            self.process.kill()
        if join:
            self.process.join(5.0)
        self.conn.close()
        if self.job is not None:
            _close_handle(self.job)
            self.job = None


class _ForkedWorker(_Worker):
    """Enfant du zygote (Linux) ; le zygote seul le tue / zygote child (Linux); only the zygote kills it."""

    __slots__ = ("zygote",)

    def __init__(self, conn: Connection, pid: int, zygote: _Zygote, timeout_s: float) -> None:
        super().__init__(conn, pid)
        self.zygote = zygote
        self._await_ready(timeout_s)

    def kill(self) -> None:
        # Réveille aussitôt le fil qui attend la réponse, puis fait tuer le processus par son parent.
        # Wakes the thread waiting for the reply at once, then has the process killed by its parent.
        try:
            with socket.fromfd(self.conn.fileno(), socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.zygote.kill(self.pid)

    def alive(self) -> bool:
        try:
            return not self.conn.poll(0)  # un travailleur au repos n'écrit rien / an idle worker writes nothing
        except OSError:
            return False

    def close(self) -> None:
        # Toujours tué, même après sa réponse : un travailleur compromis ne survit pas à sa requête.
        # Always killed, even after replying: a compromised worker never outlives its request.
        self.zygote.kill(self.pid)  # sans effet s'il est déjà terminé / no effect once it has exited
        self.conn.close()


class _SpawnFactory:
    """Travailleurs lancés directement (Windows, macOS) / workers launched directly (Windows, macOS)."""

    def __init__(self, config: SandboxConfig, settings: _Settings) -> None:
        self._config = config
        self._settings = settings
        self._unprimed = replace(settings, prime=None)

    def prepare(self) -> None:
        """Rien à préparer / nothing to prepare."""

    def new_worker(self, prime: bool = True) -> _Worker:
        return _SpawnedWorker(self._settings if prime else self._unprimed, self._config)

    def close(self) -> None:
        """Rien à arrêter / nothing to stop."""


class _ZygoteFactory:
    """Travailleurs nés du zygote, relancé s'il meurt (Linux) / workers born from the zygote (Linux)."""

    def __init__(self, config: SandboxConfig, settings: _Settings) -> None:
        self._config = config
        self._settings = settings
        self._lock = threading.Lock()
        self._zygote: _Zygote | None = None
        self._closed = False

    def prepare(self) -> _Zygote:
        with self._lock:
            if self._closed:
                raise WorkerStartError(START_MESSAGE)
            if self._zygote is None or self._zygote.broken:
                if self._zygote is not None:
                    self._zygote.close()
                    self._zygote = None
                self._zygote = _Zygote(self._settings, self._config.fork_workers, self._config.startup_timeout_s)
            return self._zygote

    def new_worker(self, prime: bool = True) -> _Worker:
        for attempt in range(2):  # un zygote mort est remplacé une fois / a dead zygote is replaced once
            zygote = self.prepare()
            try:
                conn, pid = zygote.spawn(prime)
            except WorkerStartError:
                if not zygote.broken or attempt:
                    raise
                continue
            return _ForkedWorker(conn, pid, zygote, self._config.startup_timeout_s)
        raise WorkerStartError(START_MESSAGE)

    @property
    def zygote(self) -> _Zygote | None:
        return self._zygote

    def close(self) -> None:
        with self._lock:
            self._closed = True
            zygote, self._zygote = self._zygote, None
        if zygote is not None:
            zygote.close()


# --- Windows ----------------------------------------------------------------------------------------


@cache
def _win32() -> tuple[Any, type]:
    """kernel32 et la structure des limites étendues d'un Job Object / kernel32 and the extended limits."""
    import ctypes
    from ctypes import wintypes

    class BasicLimits(ctypes.Structure):
        _fields_ = (("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                    ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                    ("SchedulingClass", wintypes.DWORD))

    class ExtendedLimits(ctypes.Structure):
        _fields_ = (("BasicLimitInformation", BasicLimits), ("IoInfo", ctypes.c_uint64 * 6),
                    ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t))

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.SetInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD)
    kernel32.SetInformationJobObject.restype = wintypes.BOOL
    kernel32.QueryInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
                                                   ctypes.c_void_p)
    kernel32.QueryInformationJobObject.restype = wintypes.BOOL
    kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel32.CloseHandle.restype = wintypes.BOOL
    return kernel32, ExtendedLimits


def _windows_job(pid: int, memory_mb: int) -> int | None:
    """Job Object : mémoire plafonnée, aucun sous-processus, mort avec le parent / capped memory, no children."""
    try:
        import ctypes

        kernel32, ExtendedLimits = _win32()
        job = kernel32.CreateJobObjectW(None, None)
        if not job:
            return None
        info = ExtendedLimits()
        # ACTIVE_PROCESS 0x8, PROCESS_MEMORY 0x100, DIE_ON_UNHANDLED_EXCEPTION 0x400, KILL_ON_JOB_CLOSE 0x2000
        info.BasicLimitInformation.LimitFlags = 0x8 | 0x400 | 0x2000 | (0x100 if memory_mb > 0 else 0)
        info.BasicLimitInformation.ActiveProcessLimit = 1
        info.ProcessMemoryLimit = max(memory_mb, 0) << 20
        process = kernel32.OpenProcess(0x0100 | 0x0001, False, pid)  # PROCESS_SET_QUOTA | PROCESS_TERMINATE
        ok = bool(process) and bool(kernel32.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info)))
        ok = ok and bool(kernel32.AssignProcessToJobObject(job, process))
        if process:
            kernel32.CloseHandle(process)
        if not ok:
            kernel32.CloseHandle(job)
            return None
        return int(job)
    except (OSError, AttributeError, ValueError):
        return None  # échec fermé côté appelant / the caller fails closed


def _windows_rebase(job: int, memory_mb: int) -> bool:
    """Plafond = empreinte du travailleur prêt (pic mesuré par le système) + `memory_mb`.

    Cap = the ready worker's footprint (peak measured by the system) + `memory_mb`.
    """
    try:
        import ctypes

        kernel32, ExtendedLimits = _win32()
        info = ExtendedLimits()
        handle = ctypes.c_void_p(job)
        if not kernel32.QueryInformationJobObject(handle, 9, ctypes.byref(info), ctypes.sizeof(info), None):
            return False
        info.ProcessMemoryLimit = info.PeakProcessMemoryUsed + (memory_mb << 20)
        return bool(kernel32.SetInformationJobObject(handle, 9, ctypes.byref(info), ctypes.sizeof(info)))
    except (OSError, AttributeError, ValueError):
        return False


def _close_handle(handle: int) -> None:
    import ctypes

    _win32()[0].CloseHandle(ctypes.c_void_p(handle))


# --- réserve de travailleurs / worker pool -----------------------------------------------------------


class WorkerPool:
    """Travailleurs prêts à l'emploi, sûrs entre fils d'exécution / ready workers, thread-safe.

    `single_use` : chaque travailleur sert une seule fois puis meurt ; la réserve (`start(n)`) garde n
    processus neufs prêts, reconstituée en arrière-plan. `single_use`: each worker serves once then dies; the
    reserve (`start(n)`) keeps n pristine processes ready, refilled in the background.
    """

    def __init__(self, config: SandboxConfig, *, single_use: bool = False) -> None:
        self.config = config
        self.single_use = single_use or config.max_jobs_per_worker == 1
        self.pid = os.getpid()
        settings = _Settings(config.memory_mb, config.preload, config.prime, self.single_use, self.pid)
        self._factory: _SpawnFactory | _ZygoteFactory = (
            _ZygoteFactory(config, settings) if ZYGOTE else _SpawnFactory(config, settings))
        self._idle: list[_Worker] = []
        self._lock = threading.Lock()
        self._wake = threading.Condition(self._lock)
        self._target = 0      # réserve visée / reserve target
        self._starting = 0    # démarrages en cours pour la réserve / starts in progress for the reserve
        self._fillers = 0     # fils de remplissage vivants / live filler threads
        self._closed = False
        _POOLS.add(self)

    @property
    def zygote(self) -> _Zygote | None:
        """Zygote courant (Linux), pour l'exploitation et les tests / current zygote (Linux)."""
        return self._factory.zygote if isinstance(self._factory, _ZygoteFactory) else None

    def call(self, target: str, payload: bytes | bytearray | None, args: tuple[Any, ...], timeout_s: float | None,
             max_reply: int = _MAX_REPLY, cancel: CancelHandle | None = None) -> Any:
        """Exécute `target(payload, *args)` dans un travailleur / runs `target(payload, *args)` in a worker.

        Résultat JSON (les tuples deviennent des listes), ou `Body` / JSON result, or `Body`.
        """
        # Borné à TIMEOUT_MAX : au-delà, le minuteur du chien de garde lèverait OverflowError / Timer would overflow.
        deadline = min(timeout_s, threading.TIMEOUT_MAX) if timeout_s and timeout_s > 0 else None
        worker = self._take()
        self._refill()  # la réserve se reconstitue pendant le travail / the reserve refills meanwhile
        if cancel is not None and not cancel._attach(worker):
            worker.close()
            raise DocumentError(CANCELLED_MESSAGE)
        try:
            reply = worker.call(target, payload, args, deadline, max_reply)
        except BaseException:
            worker.close()
            raise
        finally:
            if cancel is not None:
                cancel._detach()
        recycle = reply[0] == "error" and reply[3]  # erreur imprévue : état incertain / unexpected error
        if self.single_use:
            worker.release()  # a répondu, se termine seul / has replied, exits on its own
        elif recycle or worker.expired or worker.jobs >= self.config.max_jobs_per_worker:
            worker.close()
        else:
            self._give_back(worker)
        return _outcome(reply)

    def warm(self, count: int) -> None:
        """Démarre `count` travailleurs maintenant et en fait la réserve / starts `count` workers now."""
        count = min(count, self.config.max_idle_workers)
        with self._lock:
            self._target = max(self._target, count)
        for _ in range(count):
            self._give_back(self._factory.new_worker())

    def start(self, reserve: int) -> None:
        """Prépare en arrière-plan le zygote et une réserve de `reserve` travailleurs / background warm-up."""
        with self._lock:
            self._target = max(self._target, min(reserve, self.config.max_idle_workers))
        if self._target:
            self._refill()
        else:
            threading.Thread(target=self._prepare, name="gdprguardian-prepare", daemon=True).start()

    def _prepare(self) -> None:
        try:
            self._factory.prepare()
        except BaseException:
            return  # au mieux : la première requête réessaiera / best effort: the first request retries

    def _missing(self) -> int:
        return self._target - len(self._idle) - self._starting  # verrou tenu / lock held

    def _refill(self) -> None:
        """Remplace en arrière-plan les travailleurs consommés : la réserve reste pleine de processus neufs.

        Replaces used workers in the background: the reserve stays full of pristine processes. Quelques fils
        de remplissage durables, réveillés ici : aucun fil créé par requête. A few long-lived filler threads,
        woken here: no thread created per request.
        """
        with self._lock:
            if self._closed or self.pid != os.getpid() or self._missing() <= 0:
                return
            while self._fillers < min(_PARALLEL_STARTS, self._target):
                self._fillers += 1
                threading.Thread(target=self._fill, name="gdprguardian-refill", daemon=True).start()
            self._wake.notify()

    def _fill(self) -> None:
        while True:
            with self._lock:
                while not self._closed and self._missing() <= 0:
                    self._wake.wait()
                if self._closed:
                    self._fillers -= 1
                    return
                self._starting += 1
            worker = None
            try:
                worker = self._factory.new_worker()
            except BaseException:
                with self._lock:  # au mieux : nouvel essai plus tard / best effort: retry later
                    self._wake.wait(_RETRY_START_S)
            finally:
                with self._lock:
                    self._starting -= 1
            if worker is not None:
                self._give_back(worker)

    def _take(self) -> _Worker:
        while True:
            with self._lock:
                if self._closed:
                    raise WorkerStartError(START_MESSAGE)
                worker = self._idle.pop() if self._idle else None
            if worker is None:
                # Réserve vide (charge soutenue) : l'amorce coûterait plus qu'elle ne fait gagner à cette requête.
                # Empty reserve (sustained load): priming would cost this request more than it saves.
                return self._factory.new_worker(prime=False)
            if worker.alive():
                return worker
            worker.close()

    def _give_back(self, worker: _Worker) -> None:
        with self._lock:
            if not self._closed and len(self._idle) < self.config.max_idle_workers:
                self._idle.append(worker)
                return
        worker.close()

    def shutdown(self) -> None:
        with self._lock:
            self._closed = True
            idle, self._idle = self._idle, []
            self._wake.notify_all()  # les fils de remplissage s'arrêtent / filler threads stop
        for worker in idle:
            worker.close()
        self._factory.close()


_POOLS: weakref.WeakSet[WorkerPool] = weakref.WeakSet()
_state_lock = threading.Lock()
_config = SandboxConfig()
_pool: WorkerPool | None = None


def _current_pool() -> WorkerPool:
    global _pool
    with _state_lock:
        if _pool is None or _pool.pid != os.getpid():
            # Après un fork, les travailleurs hérités appartiennent au parent : on les ignore.
            # After a fork, inherited workers belong to the parent: they are left alone.
            _pool = WorkerPool(_config)
        return _pool


def run(target: str, payload: bytes | bytearray | None, args: tuple[Any, ...], timeout_s: float | None,
        max_reply: int = _MAX_REPLY) -> Any:
    """Exécute `target(payload, *args)` dans un travailleur ; résultat JSON d'au plus `max_reply` octets.

    Runs `target(payload, *args)` in a worker; JSON result of at most `max_reply` bytes (tuples come
    back as lists).
    """
    return _current_pool().call(target, payload, args, timeout_s, max_reply)


def configure(**changes: Any) -> SandboxConfig:
    """Modifie la configuration ; les travailleurs inactifs sont arrêtés / updates settings, stops idle workers."""
    global _config, _pool
    with _state_lock:
        new_config = replace(_config, **changes)
        if new_config.max_jobs_per_worker < 1 or new_config.max_idle_workers < 0:
            raise ValueError("max_jobs_per_worker >= 1, max_idle_workers >= 0")
        old, _pool, _config = _pool, None, new_config
    if old is not None and old.pid == os.getpid():
        old.shutdown()
    return new_config


def prewarm(workers: int = 1, target: str | None = None) -> None:
    """Démarre des travailleurs à l'avance, `target` préchargée (serveurs) / starts workers ahead of time."""
    if target is not None and target != _config.preload:
        configure(preload=target)
    _current_pool().warm(workers)


def shutdown() -> None:
    global _pool
    with _state_lock:
        old, _pool = _pool, None
    if old is not None and old.pid == os.getpid():
        old.shutdown()


def _shutdown_all() -> None:
    for pool in list(_POOLS):
        if pool.pid == os.getpid():
            pool.shutdown()


atexit.register(_shutdown_all)

__all__ = ["Body", "CancelHandle", "SandboxConfig", "WorkerPool", "WorkerStartError", "configure", "prewarm", "run",
           "run_inline", "shutdown"]
