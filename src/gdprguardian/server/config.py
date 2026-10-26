"""Configuration du service, lue depuis l'environnement / service configuration, read from the environment.

Trois modes, choisis explicitement : public (`GDPRGUARDIAN_PUBLIC=1`, aucune clé, limiteur par client), à clés
(`GDPRGUARDIAN_API_KEY_SHA256`, empreintes seulement : jamais de clé en clair dans l'environnement) et développement
local (`GDPRGUARDIAN_DEV_NO_AUTH=1`). Échec fermé : sans aucun des trois, le service refuse de démarrer.
Three modes, chosen explicitly: public (no key, per-client limiter), keyed (SHA-256 digests only: never a plaintext
key in the environment) and local development. Fail closed: with none of them, the service refuses to start.
"""

from __future__ import annotations

import math
import os
import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from .limiter import LimitPolicy
from .usage import MAX_SOCKET_PATH_BYTES

MIN_API_KEY_LENGTH = 32
# Clés en clair : refusées dans l'environnement (lisibles par /proc/<pid>/environ) / plaintext keys refused in the env.
PLAINTEXT_KEYS_VARIABLE = "GDPRGUARDIAN_API_KEYS"
_SHA256_HEX = re.compile(r"[0-9a-f]{64}")
_HEADER_NAME = re.compile(r"[A-Za-z0-9-]{1,64}")
# En-têtes que le service lit lui-même : jamais l'en-tête d'adresse / headers the service reads itself.
_RESERVED_HEADERS = frozenset({"host", "authorization", "content-length", "content-type", "transfer-encoding",
                               "expect", "connection", "cookie", "accept"})
MIN_PAGE_CHARS = 1_000
MAX_PAGE_CHARS = 200_000
# Marge pour l'enveloppe multipart / allowance for the multipart envelope.
MULTIPART_ENVELOPE_BYTES = 64 * 1024
# Part du dépôt de résultats qu'un client (le PUT) et son préfixe réseau peuvent tenir : 1/8 et 1/4. Un résultat ne
# dépasse jamais la part d'un client (plafond de sortie des travailleurs). Share of the result store one client (the
# PUT) and its network prefix may hold: 1/8 and 1/4. A result never exceeds one client's share (workers' output cap).
STORE_CLIENT_SHARE = 8
STORE_PREFIX_SHARE = 4
_TRUE = frozenset({"1", "true", "yes", "on"})
_FALSE = frozenset({"", "0", "false", "no", "off"})
_CGROUP_CPU_MAX = Path("/sys/fs/cgroup/cpu.max")
# Limite mémoire du conteneur : cgroup v2, puis v1 / container memory limit: cgroup v2, then v1.
_CGROUP_MEMORY_MAX = (Path("/sys/fs/cgroup/memory.max"), Path("/sys/fs/cgroup/memory/memory.limit_in_bytes"))
_QUEUE_SHARE = 4                  # file d'attente : un quart de la mémoire / queue: a quarter of the memory
_MIN_QUEUE_BYTES = 256 * 2**20
# Linux : travailleurs nés du zygote, quasi gratuits en réserve (mémoire partagée) / nearly free in reserve.
_FORKED_WORKERS = sys.platform.startswith("linux")
_SPAWNED_RESERVE = 4
SETTINGS_PREFIX = "GDPRGUARDIAN_"
# Interrupteur du moteur, lu par chaque processus à l'import de `gdprguardian` (travailleurs compris) : seule
# variable GDPRGUARDIAN_* laissée aux processus enfants. Engine switch, read by every process when `gdprguardian` is
# imported (workers included): the only GDPRGUARDIAN_* variable left to child processes.
ENGINE_SWITCHES = frozenset({"GDPRGUARDIAN_PURE_PYTHON"})


class ConfigError(ValueError):
    """Configuration invalide ; message sans secret / invalid configuration, message carries no secret."""


def scrub_settings() -> None:
    """Réglages lus : retirés de l'environnement avant tout processus enfant. Clés d'API comprises, ils
    n'atteignent ni le zygote ni les travailleurs, pas même leur bloc d'environnement initial (`/proc/<pid>/
    environ`), que le nettoyage fait dans un enfant ne peut plus effacer.

    Settings read: removed from the environment before any child process exists. API keys included, they reach
    neither the zygote nor the workers, not even their initial environment block, which a scrub done inside a
    child can no longer erase.
    """
    from .._hardening import scrub_environment

    scrub_environment(tuple(name for name in os.environ
                            if name.startswith(SETTINGS_PREFIX) and name not in ENGINE_SWITCHES))


def available_cpus() -> int:
    """Processeurs réellement utilisables (affinité, quota cgroup v2) / usable CPUs (affinity, cgroup v2 quota).

    `os.cpu_count()` compte les cœurs de l'hôte, pas la limite d'un conteneur (`docker run --cpus 2`).
    `os.cpu_count()` counts the host's cores, not a container limit.
    """
    getaffinity = getattr(os, "sched_getaffinity", None)
    count = len(getaffinity(0)) if getaffinity is not None else os.cpu_count() or 1
    try:
        quota, period = _CGROUP_CPU_MAX.read_text(encoding="ascii").split()[:2]
        if quota != "max":
            count = min(count, max(1, math.ceil(int(quota) / int(period))))
    except (OSError, ValueError):
        pass
    return max(1, count)


def memory_limit() -> int | None:
    """Mémoire utilisable : limite du conteneur (cgroup v2, puis v1), sinon mémoire physique ; None si inconnue.

    Usable memory: the container limit (cgroup v2, then v1), else physical memory; None when unknown.
    """
    physical = _physical_memory()
    for path in _CGROUP_MEMORY_MAX:
        try:
            raw = path.read_text(encoding="ascii").strip()
        except OSError:
            continue
        # « max » (v2) ou un nombre géant (v1) : pas de limite / "max" or a huge number: no limit.
        if raw.isdigit() and 0 < int(raw) < (physical or 1 << 62):
            return int(raw)
    return physical


def _physical_memory() -> int | None:
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (AttributeError, ValueError, OSError):
        pass
    if os.name != "nt":
        return None
    import ctypes

    class MemoryStatus(ctypes.Structure):
        _fields_ = (("dwLength", ctypes.c_uint32), ("dwMemoryLoad", ctypes.c_uint32),
                    ("ullTotalPhys", ctypes.c_uint64), ("ullAvailPhys", ctypes.c_uint64),
                    ("ullTotalPageFile", ctypes.c_uint64), ("ullAvailPageFile", ctypes.c_uint64),
                    ("ullTotalVirtual", ctypes.c_uint64), ("ullAvailVirtual", ctypes.c_uint64),
                    ("ullAvailExtendedVirtual", ctypes.c_uint64))

    status = MemoryStatus()
    status.dwLength = ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return None
    return int(status.ullTotalPhys)


def default_queue_bytes() -> int:
    """Budget des requêtes en attente : un quart de la mémoire utilisable, 256 Mio au moins.

    Budget for queued requests: a quarter of the usable memory, at least 256 MiB (1 GiB when unknown).
    """
    limit = memory_limit()
    return max(_MIN_QUEUE_BYTES, (limit or _QUEUE_SHARE << 30) // _QUEUE_SHARE)


def default_reserve(concurrency: int) -> int:
    """Travailleurs neufs gardés prêts : un par place sous Linux, 4 au plus ailleurs (interpréteurs complets).

    Pristine workers kept ready: one per slot on Linux, at most 4 elsewhere (full interpreters).
    """
    return concurrency if _FORKED_WORKERS else min(concurrency, _SPAWNED_RESERVE)


@dataclass(slots=True, frozen=True)
class ServerConfig:
    """Réglages du service ; les durées sont en secondes / service settings, durations in seconds.

    `api_keys` : clés en clair, pour l'intégration en code seulement (jamais lues dans l'environnement) ;
    `api_key_sha256` : empreintes SHA-256 hexadécimales, la forme lue dans l'environnement. `api_keys`: plaintext
    keys, for in-code embedding only (never read from the environment); `api_key_sha256`: hex SHA-256 digests, the
    form read from the environment.
    """

    api_keys: tuple[str, ...] = field(default=(), repr=False)
    api_key_sha256: tuple[str, ...] = field(default=(), repr=False)
    dev_no_auth: bool = False
    # Service public : aucune authentification, limiteur par client / public service: no auth, per-client limiter.
    public: bool = False
    # En-tête de confiance portant l'adresse du client, posé par le proxy (production : X-GG-Client) ; None : le pair
    # TCP. Trusted header carrying the client address, set by the proxy; None: the TCP peer.
    client_ip_header: str | None = None
    limits: LimitPolicy = field(default_factory=LimitPolicy)
    public_url: str | None = None
    allowed_hosts: tuple[str, ...] = ()
    max_upload_bytes: int = 50 * 1024 * 1024
    max_json_bytes: int = 8 * 1024 * 1024
    max_text_chars: int = 1_000_000
    # Pages (PDF) ou diapositives (PPTX, ODP) d'un document : au-delà de 500 (défaut de la bibliothèque), un PDF de
    # 50 Mo illustré serait refusé ; les vraies bornes restent l'échéance et le plafond de sortie. Pages or slides of
    # a document: beyond the library's 500, an illustrated 50 MB PDF would be refused; the real bounds stay the
    # deadline and the output cap.
    max_pages: int = 10_000
    upload_ttl_s: float = 300.0
    result_ttl_s: float = 600.0
    page_chars: int = 40_000
    # Envois reçus et résultats non lus par client (celui du PUT), en attente du fichier par principal sans réseau
    # (clé, poste local). Received uploads and unread results per client (the PUT's), pending ones per keyed or local
    # principal.
    max_active_per_principal: int = 10
    # Par préfixe réseau (/24, /48) : envois en attente (du créateur) et envois reçus (du PUT) ; un réseau partagé
    # (NAT, connecteur distant) n'est pas bloqué à 10. Per network prefix: pending uploads (creator's) and received
    # ones (the PUT's); a shared network (NAT, remote connector) is not stuck at 10.
    max_uploads_per_prefix: int = 40
    # Envois reçus en cours ou à lire (tout le service), et en attente du fichier (minuscules, plafond à part).
    # Received uploads in progress or unread (whole service), and pending ones (tiny, separate cap).
    max_jobs: int = 1_000
    max_pending: int = 10_000
    max_store_chars: int = 200_000_000
    # Lecture d'un corps : 15 s, plus la taille au débit minimal (128 Kio/s, une ligne montante de 1 Mbit/s) ; au-delà
    # 408. Body read: 15 s plus the size at the minimal rate (128 KiB/s, a 1 Mbit/s uplink); beyond, 408.
    body_base_s: float = 15.0
    body_min_rate: int = 128 * 1024
    # Travailleurs occupés en même temps, un cœur chacun / workers busy at once, one core each.
    max_concurrency: int = field(default_factory=available_cpus)
    # Traitement d'une requête : conversion, plus une seconde par 250 Ko pour l'anonymisation.
    # Processing deadline of a request: conversion, plus one second per 250 KB for the anonymisation.
    conversion_timeout_s: float = 60.0
    sweep_interval_s: float = 15.0
    # Travailleurs neufs gardés prêts (0 en bibliothèque et en test) / pristine workers kept ready (0 by default).
    prewarm_workers: int = 0
    docs: bool = False
    # Octets de requêtes tenus en mémoire (en attente ou en cours) / request bytes held (queued or in progress).
    queue_bytes: int = field(default_factory=default_queue_bytes)
    # Mémoire accordée à un document dans son travailleur / memory granted to one document in its worker.
    worker_memory_mb: int = 2048
    # Chaque requête dans un processus isolé à usage unique. False (jamais via l'environnement) : dans ce
    # processus, pour les tests et l'intégration. Each request in a single-use isolated process; False (never
    # from the environment): in this process, for tests and embedding.
    isolation: bool = True
    # Socket Unix (datagrammes) du compteur d'usage de la page publique ; None : désactivé (`usage.py`).
    # Unix datagram socket of the public page's usage counter; None: disabled.
    usage_socket: str | None = None
    # Empreinte SHA-256 du jeton exigé des requêtes du serveur lui-même (`X-GG-Local`), None : aucun (`clients`).
    # SHA-256 digest of the token required from the server's own requests, None: none.
    local_token_sha256: str | None = field(default=None, repr=False)

    @property
    def largest_request(self) -> int:
        """Plus gros corps de requête accepté, en octets / largest accepted request body, in bytes."""
        return max(self.max_upload_bytes + MULTIPART_ENVELOPE_BYTES, self.max_json_bytes)

    @property
    def max_output_chars(self) -> int:
        """Plus long résultat (texte ou Markdown) qu'un travailleur peut rendre : la part du dépôt d'un client.

        Longest result (text or Markdown) a worker may return: one client's share of the store. Au-delà : 413 /
        beyond: 413.
        """
        return max(1, self.max_store_chars // STORE_CLIENT_SHARE)

    def body_deadline_s(self, size: int) -> float:
        """Durée accordée à la lecture d'un corps de `size` octets / time allowed to read a `size`-byte body."""
        return self.body_base_s + size / self.body_min_rate

    @property
    def keyed(self) -> bool:
        """Des clés d'API sont configurées / API keys are configured."""
        return bool(self.api_keys or self.api_key_sha256)

    def validate(self) -> None:
        if self.dev_no_auth:
            if self.keyed or self.public:
                raise ConfigError("GDPRGUARDIAN_DEV_NO_AUTH exclut les clés et GDPRGUARDIAN_PUBLIC / are mutually "
                                  "exclusive")
        elif not self.keyed and not self.public:
            raise ConfigError("Aucune authentification choisie : GDPRGUARDIAN_PUBLIC=1 (service public) ou "
                              "GDPRGUARDIAN_API_KEY_SHA256 (empreintes des clés) ; service refusé (échec fermé) / no "
                              "authentication chosen: GDPRGUARDIAN_PUBLIC=1 or GDPRGUARDIAN_API_KEY_SHA256; refusing "
                              "to start (fail closed)")
        if any(len(key) < MIN_API_KEY_LENGTH for key in self.api_keys):
            raise ConfigError(f"Clé d'API trop courte (< {MIN_API_KEY_LENGTH} caractères) / API key too short")
        if any(not key.isascii() or not key.isprintable() or " " in key for key in self.api_keys):
            raise ConfigError("Clé d'API invalide : ASCII imprimable sans espace / API key must be printable ASCII")
        if any(not _SHA256_HEX.fullmatch(digest) for digest in self.api_key_sha256):
            raise ConfigError("GDPRGUARDIAN_API_KEY_SHA256 : empreintes SHA-256 en hexadécimal (64 caractères), "
                              "séparées par des virgules / hex SHA-256 digests, comma-separated")
        if self.local_token_sha256 is not None and not _SHA256_HEX.fullmatch(self.local_token_sha256):
            raise ConfigError("GDPRGUARDIAN_LOCAL_TOKEN_SHA256 : empreinte SHA-256 en hexadécimal (64 caractères) / "
                              "hex SHA-256 digest expected")
        if self.client_ip_header is not None and (not _HEADER_NAME.fullmatch(self.client_ip_header)
                                                  or self.client_ip_header.lower() in _RESERVED_HEADERS):
            raise ConfigError("GDPRGUARDIAN_CLIENT_IP_HEADER : nom d'en-tête dédié attendu (lettres, chiffres, tirets) "
                              "/ a dedicated header name is expected")
        try:
            self.limits.validate()
        except ValueError as exc:
            raise ConfigError(str(exc)) from None
        if self.public_url is not None:
            parts = urlsplit(self.public_url)
            if parts.scheme not in ("http", "https") or not parts.netloc or parts.query or parts.fragment:
                raise ConfigError("GDPRGUARDIAN_PUBLIC_URL doit être une URL http(s) de base / "
                                  "must be a base http(s) URL")
        if not MIN_PAGE_CHARS <= self.page_chars <= MAX_PAGE_CHARS:
            raise ConfigError(f"page_chars ∈ [{MIN_PAGE_CHARS}, {MAX_PAGE_CHARS}]")
        positive = {
            "max_upload_bytes": self.max_upload_bytes, "max_json_bytes": self.max_json_bytes,
            "max_text_chars": self.max_text_chars, "max_pages": self.max_pages, "upload_ttl_s": self.upload_ttl_s,
            "result_ttl_s": self.result_ttl_s, "max_active_per_principal": self.max_active_per_principal,
            "max_uploads_per_prefix": self.max_uploads_per_prefix, "max_pending": self.max_pending,
            "max_jobs": self.max_jobs, "max_store_chars": self.max_store_chars,
            "body_base_s": self.body_base_s, "body_min_rate": self.body_min_rate,
            "max_concurrency": self.max_concurrency, "conversion_timeout_s": self.conversion_timeout_s,
            "sweep_interval_s": self.sweep_interval_s, "worker_memory_mb": self.worker_memory_mb,
        }
        for name, value in positive.items():
            if value <= 0:
                raise ConfigError(f"{name} doit être > 0 / must be > 0")
        if self.prewarm_workers < 0:
            raise ConfigError("prewarm_workers doit être ≥ 0 / must be ≥ 0")
        if self.queue_bytes < self.largest_request:
            raise ConfigError(f"GDPRGUARDIAN_QUEUE_MB doit contenir la plus grosse requête "
                              f"({math.ceil(self.largest_request / 2**20)} Mo) / must hold the largest request")
        if self.usage_socket is not None and not _socket_path(self.usage_socket):
            raise ConfigError(f"GDPRGUARDIAN_USAGE_SOCKET : chemin absolu d'au plus {MAX_SOCKET_PATH_BYTES} octets "
                              f"attendu / absolute path of at most {MAX_SOCKET_PATH_BYTES} bytes expected")

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> ServerConfig:
        """Lit les variables GDPRGUARDIAN_* / reads the GDPRGUARDIAN_* variables (see deploy/README.md)."""
        env = os.environ if env is None else env
        if env.get(PLAINTEXT_KEYS_VARIABLE, "").strip():
            raise ConfigError(f"{PLAINTEXT_KEYS_VARIABLE} n'est plus accepté (clé en clair dans l'environnement) : "
                              "donner les empreintes, GDPRGUARDIAN_API_KEY_SHA256=$(printf '%s' \"$cle\" | sha256sum | "
                              f"cut -d' ' -f1) / {PLAINTEXT_KEYS_VARIABLE} is no longer accepted (plaintext key in the "
                              "environment): give the SHA-256 digests in GDPRGUARDIAN_API_KEY_SHA256")
        digests = tuple(dict.fromkeys(d.strip().lower() for d in env.get("GDPRGUARDIAN_API_KEY_SHA256", "").split(",")
                                      if d.strip()))
        try:
            limits = LimitPolicy.from_env(env)
        except ValueError as exc:
            raise ConfigError(str(exc)) from None
        default = cls()
        max_text_chars = _int(env, "GDPRGUARDIAN_MAX_TEXT_CHARS", default.max_text_chars)
        max_concurrency = _int(env, "GDPRGUARDIAN_MAX_CONCURRENCY", default.max_concurrency)
        max_upload_bytes = _int(env, "GDPRGUARDIAN_MAX_UPLOAD_MB", default.max_upload_bytes // 2**20) * 2**20
        # JSON : jusqu'à 6 octets par caractère échappé (\uXXXX) / up to 6 bytes per escaped character.
        max_json_bytes = max(default.max_json_bytes, 6 * max_text_chars + 65_536)
        # Budget par défaut : au moins la plus grosse requête (petit conteneur, gros envois autorisés).
        # Default budget: at least the largest request (small container, large uploads allowed).
        largest = max(max_upload_bytes + MULTIPART_ENVELOPE_BYTES, max_json_bytes)
        default_queue_mb = max(default.queue_bytes // 2**20, math.ceil(largest / 2**20))
        config = cls(
            api_key_sha256=digests,
            dev_no_auth=_bool(env, "GDPRGUARDIAN_DEV_NO_AUTH"),
            public=_bool(env, "GDPRGUARDIAN_PUBLIC"),
            client_ip_header=env.get("GDPRGUARDIAN_CLIENT_IP_HEADER", "").strip() or None,
            limits=limits,
            public_url=(env.get("GDPRGUARDIAN_PUBLIC_URL") or "").strip().rstrip("/") or None,
            allowed_hosts=tuple(h.strip() for h in env.get("GDPRGUARDIAN_ALLOWED_HOSTS", "").split(",") if h.strip()),
            max_upload_bytes=max_upload_bytes,
            max_json_bytes=max_json_bytes,
            max_text_chars=max_text_chars,
            max_pages=_int(env, "GDPRGUARDIAN_MAX_PAGES", default.max_pages),
            upload_ttl_s=_int(env, "GDPRGUARDIAN_UPLOAD_TTL_S", int(default.upload_ttl_s)),
            result_ttl_s=_int(env, "GDPRGUARDIAN_RESULT_TTL_S", int(default.result_ttl_s)),
            page_chars=_int(env, "GDPRGUARDIAN_PAGE_CHARS", default.page_chars),
            max_active_per_principal=_int(env, "GDPRGUARDIAN_MAX_ACTIVE_UPLOADS", default.max_active_per_principal),
            max_uploads_per_prefix=_int(env, "GDPRGUARDIAN_MAX_UPLOADS_PER_PREFIX", default.max_uploads_per_prefix),
            max_pending=_int(env, "GDPRGUARDIAN_MAX_PENDING_UPLOADS", default.max_pending),
            max_store_chars=_int(env, "GDPRGUARDIAN_MAX_STORE_CHARS", default.max_store_chars),
            body_min_rate=_int(env, "GDPRGUARDIAN_MIN_BODY_RATE_KIB", default.body_min_rate // 1024) * 1024,
            local_token_sha256=env.get("GDPRGUARDIAN_LOCAL_TOKEN_SHA256", "").strip().lower() or None,
            max_concurrency=max_concurrency,
            conversion_timeout_s=_int(env, "GDPRGUARDIAN_CONVERSION_TIMEOUT_S", int(default.conversion_timeout_s)),
            # Service : une réserve de travailleurs neufs, la requête ne paie que l'échange / a pristine reserve.
            prewarm_workers=_int(env, "GDPRGUARDIAN_PREWARM_WORKERS", default_reserve(max(max_concurrency, 0))),
            docs=_bool(env, "GDPRGUARDIAN_DOCS"),
            queue_bytes=_int(env, "GDPRGUARDIAN_QUEUE_MB", default_queue_mb) * 2**20,
            worker_memory_mb=_int(env, "GDPRGUARDIAN_WORKER_MEMORY_MB", default.worker_memory_mb),
            usage_socket=env.get("GDPRGUARDIAN_USAGE_SOCKET", "").strip() or None,
        )
        config.validate()
        return config


def _socket_path(path: str) -> bool:
    """Chemin de socket Unix utilisable : absolu (POSIX), sans zéro, assez court / usable Unix socket path."""
    return path.startswith("/") and "\x00" not in path and len(path.encode("utf-8", "replace")) <= MAX_SOCKET_PATH_BYTES


def _bool(env: Mapping[str, str], name: str) -> bool:
    value = env.get(name, "").strip().lower()
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False
    raise ConfigError(f"{name} : booléen attendu / boolean expected (1/0, true/false)")


def _int(env: Mapping[str, str], name: str, default: int) -> int:
    raw = env.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        raise ConfigError(f"{name} : entier attendu / integer expected") from None
