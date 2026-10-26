"""Configuration : lecture de l'environnement et échec fermé / configuration: env parsing, fail closed."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from server_testkit import KEY_A, KEY_A_SHA256, KEY_B_SHA256

from gdprguardian.server import config as config_module
from gdprguardian.server.config import ConfigError, ServerConfig, available_cpus, default_queue_bytes, scrub_settings
from gdprguardian.server.limiter import LimitPolicy

KEYED = {"GDPRGUARDIAN_API_KEY_SHA256": KEY_A_SHA256}


def test_settings_are_scrubbed_before_any_child_but_the_engine_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    # Copie de l'environnement : le vrai n'est pas touché / a copy of the environment: the real one is untouched.
    monkeypatch.setattr(os, "environ", {**KEYED, "GDPRGUARDIAN_MAX_CONCURRENCY": "2", "GDPRGUARDIAN_PUBLIC": "1",
                                        "GDPRGUARDIAN_SECRET_PROBE": "x", "GDPRGUARDIAN_PURE_PYTHON": "0",
                                        "PATH": "/bin"})
    scrub_settings()
    assert os.environ == {"GDPRGUARDIAN_PURE_PYTHON": "0", "PATH": "/bin"}


def test_a_factory_launch_reads_then_scrubs_the_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    # `uvicorn --factory gdprguardian.server:create_app` : aucun réglage ne doit atteindre le zygote / none reaches it.
    from gdprguardian.server import create_app

    monkeypatch.setattr(os, "environ", {**KEYED, "GDPRGUARDIAN_LIMITS": "dry-run"})
    app = create_app()
    config = app.state.service.config
    assert config.api_key_sha256 == (KEY_A_SHA256,) and config.limits.mode == "dry-run"
    assert not any(name.startswith("GDPRGUARDIAN_") for name in os.environ)
    # Configuration fournie (tests, intégration) : l'environnement reste intact / given config: env untouched.
    monkeypatch.setattr(os, "environ", {"GDPRGUARDIAN_DOCS": "1"})
    create_app(ServerConfig(api_keys=(KEY_A,)))
    assert os.environ["GDPRGUARDIAN_DOCS"] == "1"


def test_from_env_reads_keys_and_settings() -> None:
    config = ServerConfig.from_env({
        "GDPRGUARDIAN_API_KEY_SHA256": f" {KEY_A_SHA256} , {KEY_B_SHA256.upper()},{KEY_A_SHA256}",
        "GDPRGUARDIAN_PUBLIC_URL": "https://rgpd.example.eu/",
        "GDPRGUARDIAN_ALLOWED_HOSTS": "rgpd.example.eu, api.example.eu",
        "GDPRGUARDIAN_MAX_UPLOAD_MB": "5",
        "GDPRGUARDIAN_RESULT_TTL_S": "120",
        "GDPRGUARDIAN_PAGE_CHARS": "20000",
        "GDPRGUARDIAN_DOCS": "yes",
    })
    assert config.api_key_sha256 == (KEY_A_SHA256, KEY_B_SHA256) and config.api_keys == ()
    assert config.keyed and not config.public
    assert config.public_url == "https://rgpd.example.eu"
    assert config.allowed_hosts == ("rgpd.example.eu", "api.example.eu")
    assert config.max_upload_bytes == 5 * 2**20
    assert config.result_ttl_s == 120
    assert config.page_chars == 20_000
    assert config.docs is True


def test_plaintext_keys_in_the_environment_are_refused() -> None:
    # Une clé en clair dans l'environnement se lit par /proc/<pid>/environ : refus, avec la marche à suivre.
    # A plaintext key in the environment is readable through /proc/<pid>/environ: refused, with what to do.
    with pytest.raises(ConfigError, match="GDPRGUARDIAN_API_KEY_SHA256") as caught:
        ServerConfig.from_env({"GDPRGUARDIAN_API_KEYS": KEY_A, "GDPRGUARDIAN_PUBLIC": "1"})
    assert KEY_A not in str(caught.value)
    with pytest.raises(ConfigError, match="SHA-256"):
        ServerConfig.from_env({"GDPRGUARDIAN_API_KEY_SHA256": "not-a-digest"})


def test_public_mode_needs_no_key_and_reads_its_settings() -> None:
    config = ServerConfig.from_env({"GDPRGUARDIAN_PUBLIC": "1", "GDPRGUARDIAN_CLIENT_IP_HEADER": "X-GG-Client",
                                    "GDPRGUARDIAN_LIMITS": "enforce", "GDPRGUARDIAN_LIMIT_COST_RATE": "0.25",
                                    "GDPRGUARDIAN_LIMIT_MAX_QUEUED": "3", "GDPRGUARDIAN_MAX_ACTIVE_UPLOADS": "5"})
    assert config.public and not config.keyed and config.client_ip_header == "X-GG-Client"
    assert config.limits == LimitPolicy(cost_rate=0.25, max_queued=3)
    assert config.max_active_per_principal == 5
    defaults = ServerConfig.from_env({"GDPRGUARDIAN_PUBLIC": "1"})
    assert defaults.limits == LimitPolicy() and defaults.client_ip_header is None
    assert defaults.max_active_per_principal == 10  # jetons en cours par client / outstanding tokens per client


@pytest.mark.parametrize(("name", "value"), [
    ("GDPRGUARDIAN_LIMITS", "maybe"), ("GDPRGUARDIAN_LIMIT_COST_RATE", "fast"), ("GDPRGUARDIAN_LIMIT_COST_RATE", "0"),
    ("GDPRGUARDIAN_LIMIT_MAX_RUNNING", "1.5"), ("GDPRGUARDIAN_LIMIT_JITTER", "2"),
    ("GDPRGUARDIAN_LIMIT_MAX_WAIT_S", "-1"), ("GDPRGUARDIAN_LIMIT_SMALL_S", "nan"),
    ("GDPRGUARDIAN_CLIENT_IP_HEADER", "X GG"), ("GDPRGUARDIAN_CLIENT_IP_HEADER", "Authorization"),
    ("GDPRGUARDIAN_CLIENT_IP_HEADER", "host"),
])
def test_invalid_public_settings_are_refused(name: str, value: str) -> None:
    with pytest.raises(ConfigError):
        ServerConfig.from_env({"GDPRGUARDIAN_PUBLIC": "1", name: value})


def test_keys_never_appear_in_repr() -> None:
    shown = repr(ServerConfig(api_keys=(KEY_A,), api_key_sha256=(KEY_B_SHA256,)))
    assert KEY_A not in shown and KEY_B_SHA256 not in shown


def test_fail_closed_without_keys() -> None:
    with pytest.raises(ConfigError, match="fail closed"):
        ServerConfig.from_env({})
    with pytest.raises(ConfigError, match="fail closed"):
        ServerConfig.from_env({"GDPRGUARDIAN_PUBLIC": "0"})


def test_dev_mode_is_explicit_and_exclusive() -> None:
    assert ServerConfig.from_env({"GDPRGUARDIAN_DEV_NO_AUTH": "1"}).dev_no_auth is True
    with pytest.raises(ConfigError, match="exclusive"):
        ServerConfig.from_env({"GDPRGUARDIAN_DEV_NO_AUTH": "1", **KEYED})
    with pytest.raises(ConfigError, match="exclusive"):
        ServerConfig.from_env({"GDPRGUARDIAN_DEV_NO_AUTH": "1", "GDPRGUARDIAN_PUBLIC": "1"})


@pytest.mark.parametrize("key", ["short", "x" * 31, "a" * 40 + " b", "clé-" + "é" * 40])
def test_weak_or_malformed_keys_are_refused(key: str) -> None:
    with pytest.raises(ConfigError):
        ServerConfig(api_keys=(key,)).validate()


@pytest.mark.parametrize(("name", "value"), [
    ("GDPRGUARDIAN_DEV_NO_AUTH", "maybe"),
    ("GDPRGUARDIAN_PAGE_CHARS", "lots"),
    ("GDPRGUARDIAN_PAGE_CHARS", "10"),
    ("GDPRGUARDIAN_PUBLIC_URL", "ftp://example.eu"),
    ("GDPRGUARDIAN_PUBLIC_URL", "https://example.eu/?q=1"),
    ("GDPRGUARDIAN_RESULT_TTL_S", "0"),
])
def test_invalid_values_are_refused(name: str, value: str) -> None:
    with pytest.raises(ConfigError):
        ServerConfig.from_env({**KEYED, name: value})


def test_json_limit_follows_text_limit() -> None:
    config = ServerConfig.from_env({**KEYED, "GDPRGUARDIAN_MAX_TEXT_CHARS": "3000000"})
    assert config.max_json_bytes >= 6 * 3_000_000


def test_service_keeps_a_worker_reserve_but_the_library_does_not() -> None:
    assert ServerConfig().prewarm_workers == 0
    env = {**KEYED, "GDPRGUARDIAN_MAX_CONCURRENCY": "6"}
    # Linux : un travailleur neuf par place (fork, mémoire partagée) ; ailleurs 4 au plus (interpréteurs complets).
    # Linux: one pristine worker per slot (fork, shared memory); elsewhere at most 4 (full interpreters).
    assert ServerConfig.from_env(env).prewarm_workers == (6 if sys.platform.startswith("linux") else 4)
    assert ServerConfig.from_env({**env, "GDPRGUARDIAN_PREWARM_WORKERS": "0"}).prewarm_workers == 0
    with pytest.raises(ConfigError):
        ServerConfig.from_env({**KEYED, "GDPRGUARDIAN_PREWARM_WORKERS": "-1"})


def test_isolation_cannot_be_disabled_from_the_environment() -> None:
    config = ServerConfig.from_env({**KEYED, "GDPRGUARDIAN_ISOLATION": "0"})
    assert config.isolation is True and ServerConfig().isolation is True


def test_queue_budget_and_worker_memory_from_env() -> None:
    config = ServerConfig.from_env({**KEYED, "GDPRGUARDIAN_QUEUE_MB": "300",
                                    "GDPRGUARDIAN_WORKER_MEMORY_MB": "1024"})
    assert config.queue_bytes == 300 * 2**20 and config.worker_memory_mb == 1024
    # Le budget doit contenir la plus grosse requête (50 Mo + enveloppe) / must hold the largest request.
    with pytest.raises(ConfigError, match="QUEUE_MB"):
        ServerConfig.from_env({**KEYED, "GDPRGUARDIAN_QUEUE_MB": "50"})
    with pytest.raises(ConfigError):
        ServerConfig.from_env({**KEYED, "GDPRGUARDIAN_WORKER_MEMORY_MB": "0"})


@pytest.mark.parametrize(("v2", "v1", "expected_mb"), [
    ("4294967296\n", None, 1024),          # conteneur de 4 Gio : un quart / 4 GiB container: a quarter
    ("max\n", "2147483648", 512),          # limite cgroup v1 / cgroup v1 limit
    ("max\n", "9223372036854771712", 16 * 1024),  # v1 « illimité » : mémoire physique / v1 "unlimited"
    ("536870912", None, 256),              # petit conteneur : plancher de 256 Mio / small container: floor
    (None, None, 16 * 1024),               # hors conteneur : mémoire physique / outside a container
])
def test_queue_budget_follows_the_container_memory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, v2: str | None,
                                                   v1: str | None, expected_mb: int) -> None:
    paths = (tmp_path / "memory.max", tmp_path / "memory.limit_in_bytes")
    for path, content in zip(paths, (v2, v1), strict=True):
        if content is not None:
            path.write_text(content, encoding="ascii")
    monkeypatch.setattr(config_module, "_CGROUP_MEMORY_MAX", paths)
    monkeypatch.setattr(config_module, "_physical_memory", lambda: 64 * 2**30)
    assert default_queue_bytes() == expected_mb * 2**20
    assert ServerConfig().queue_bytes == expected_mb * 2**20
    monkeypatch.setattr(config_module, "_physical_memory", lambda: None)
    if v2 is None:
        assert default_queue_bytes() == 2**30  # mémoire inconnue : 1 Gio / unknown memory: 1 GiB


def test_default_queue_budget_holds_the_largest_request(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Petit conteneur (budget par défaut de 256 Mio) et envois de 300 Mo autorisés : le service démarre, le budget
    # par défaut contient la plus grosse requête. Small container and 300 MB uploads: the service starts.
    limit = tmp_path / "memory.max"
    limit.write_text("536870912", encoding="ascii")
    monkeypatch.setattr(config_module, "_CGROUP_MEMORY_MAX", (limit,))
    config = ServerConfig.from_env({**KEYED, "GDPRGUARDIAN_MAX_UPLOAD_MB": "300"})
    assert config.queue_bytes >= config.largest_request > 300 * 2**20
    assert ServerConfig.from_env(KEYED).queue_bytes == 256 * 2**20  # inchangé / unchanged
    with pytest.raises(ConfigError, match="QUEUE_MB"):  # valeur explicite : contrôlée / explicit value: checked
        ServerConfig.from_env({**KEYED, "GDPRGUARDIAN_MAX_UPLOAD_MB": "300",
                               "GDPRGUARDIAN_QUEUE_MB": "256"})


@pytest.mark.parametrize(("content", "cap"), [("150000 100000\n", 2), ("50000 100000", 1), ("max 100000", None),
                                              ("garbage", None)])
def test_cpu_count_honours_the_container_quota(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, content: str,
                                               cap: int | None) -> None:
    # `docker run --cpus 1.5` : 2 travailleurs, pas autant que de cœurs sur l'hôte / not one per host core.
    monkeypatch.setattr(config_module, "_CGROUP_CPU_MAX", tmp_path / "absent")
    unlimited = available_cpus()
    quota = tmp_path / "cpu.max"
    quota.write_text(content, encoding="ascii")
    monkeypatch.setattr(config_module, "_CGROUP_CPU_MAX", quota)
    assert available_cpus() == (min(unlimited, cap) if cap else unlimited) >= 1
