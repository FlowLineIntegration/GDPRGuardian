"""Durcissement des processus qui touchent des documents / hardening of processes that handle documents.

Le code ne remplace pas l'isolation du système (conteneur sans réseau, swap désactivé : voir deploy/README.md),
mais il ferme ce qu'il peut lui-même : processus non lisible par un autre, sans vidage mémoire, sans secret
dans l'environnement, sans sortie standard. Code cannot replace OS isolation, but it closes what it can:
non-readable process, no core dump, no secret in the environment, no standard output.
"""

from __future__ import annotations

import os
import sys

_PR_SET_PDEATHSIG = 1
_PR_SET_DUMPABLE = 4
# Variables secrètes lues au démarrage puis retirées de l'environnement / secrets read at start-up, then removed.
SECRET_VARIABLES = ("GDPRGUARDIAN_API_KEYS", "GDPRGUARDIAN_API_KEY_SHA256")


class HardeningError(RuntimeError):
    """Durcissement impossible : on refuse de continuer (échec fermé) / hardening failed: fail closed."""


def _prctl(option: int, value: int) -> None:
    import ctypes

    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(option, value, 0, 0, 0) != 0:
        raise HardeningError(f"prctl({option}) : errno {ctypes.get_errno()}")


def harden_process(*, die_with_parent: int | None = None, forbid_children: bool = False) -> None:
    """Linux : non vidable (ni /proc/<pid>/mem ni environ lisibles, ni ptrace, ni core), sans core dump.

    Linux: non-dumpable (no /proc/<pid>/mem or environ reads, no ptrace, no core), no core dump.
    `die_with_parent` : PID du parent ; le processus meurt avec lui / dies with this parent.
    `forbid_children` : aucun processus ni fil d'exécution de plus / no further process or thread.
    """
    if os.name != "posix":
        return
    import resource

    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    if sys.platform.startswith("linux"):
        _prctl(_PR_SET_DUMPABLE, 0)
        if die_with_parent is not None:
            import signal

            _prctl(_PR_SET_PDEATHSIG, int(signal.SIGKILL))
            if os.getppid() != die_with_parent:
                os._exit(1)  # parent déjà mort avant le prctl / parent already gone before prctl
    if forbid_children:
        # Limite dure : sans CAP_SYS_RESOURCE (--cap-drop ALL), elle ne remonte plus. Sans effet pour root.
        # Hard limit: cannot be raised again without CAP_SYS_RESOURCE. No effect for root.
        resource.setrlimit(resource.RLIMIT_NPROC, (0, 0))


def scrub_environment(names: tuple[str, ...] = SECRET_VARIABLES, prefix: str | None = None) -> None:
    """Retire les secrets de l'environnement : les processus lancés ensuite n'en héritent pas.

    Removes secrets from the environment: processes started afterwards do not inherit them.
    """
    for name in list(os.environ):
        if name in names or (prefix is not None and name.startswith(prefix)):
            del os.environ[name]


def silence_stdio() -> None:
    """Entrées et sorties standard vers le néant : rien d'un document ne peut atteindre le journal.

    Standard streams to the null device: nothing from a document can reach the log.
    """
    null = os.open(os.devnull, os.O_RDWR)
    try:
        for fd in (0, 1, 2):
            os.dup2(null, fd)
    finally:
        os.close(null)
    sys.unraisablehook = lambda _unraisable: None
