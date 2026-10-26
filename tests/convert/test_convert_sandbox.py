"""Bac à sable : processus séparés, délai, plantage, mémoire / sandbox: separate processes, timeout, crash, memory."""

from __future__ import annotations

import dataclasses
import os
import stat
import threading
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor

import pytest
from convert_samples import COMPROMISED, contract_pdf, encrypt_pdf, make_docx, make_eml, make_pptx

from gdprguardian.convert import _document, _sandbox, configure_sandbox, prewarm, shutdown_sandbox, to_markdown
from gdprguardian.convert._base import CRASH_MESSAGE, FAILURE_MESSAGE
from gdprguardian.documents import (
    ConversionTimeoutError,
    DocumentError,
    DocumentOptions,
    DocumentTooLargeError,
    EncryptedDocumentError,
)

SANDBOX = DocumentOptions(timeout_s=60)
LOCAL = DocumentOptions(sandbox=False)


@pytest.fixture(autouse=True)
def fresh_sandbox() -> Iterator[None]:
    configure_sandbox(**{field.name: field.default for field in dataclasses.fields(_sandbox.SandboxConfig)})
    yield
    shutdown_sandbox()


def pid() -> int:
    return _sandbox.run("convert_samples:echo", b"abc", ("x",), 30)[2]


@pytest.mark.parametrize(("builder", "name"), [(contract_pdf, "c.pdf"), (make_docx, "c.docx"), (make_pptx, "c.pptx"),
                                               (make_eml, "c.eml")])
def test_sandbox_gives_the_same_result_as_in_process(builder, name: str) -> None:
    data = builder()
    isolated, local = to_markdown(data, name, SANDBOX), to_markdown(data, name, LOCAL)
    assert (isolated.markdown, isolated.kind, isolated.pages, isolated.warnings, isolated.dropped) == (
        local.markdown, local.kind, local.pages, local.warnings, local.dropped)


def test_workers_are_reused_then_recycled() -> None:
    first = pid()
    assert pid() == first
    configure_sandbox(max_jobs_per_worker=1)
    assert pid() != pid()


def test_workers_are_confined_before_any_document(monkeypatch) -> None:
    # Un convertisseur exploité ne trouve ni secret, ni sortie standard, ni droit de créer un processus.
    # An exploited converter finds no secret, no standard output and no right to create a process.
    monkeypatch.setenv("GDPRGUARDIAN_API_KEYS", "cle-de-test-tres-secrete-0123456789abcdef")
    found = _sandbox.run("convert_samples:inspect_confinement", b"x", (), 30)
    assert found["secrets"] == []
    if os.name == "posix":
        assert found["core"] == 0 and found["nproc"] == 0
        if found.get("stdout") is not None:
            assert found["stdout"] == "/dev/null"
        if "dumpable" in found:
            assert found["dumpable"] == 0  # ni /proc/<pid>/mem, ni environ, ni ptrace / nor ptrace


def test_single_use_workers_keep_a_pristine_reserve() -> None:
    configure_sandbox(max_jobs_per_worker=1, max_idle_workers=2)
    prewarm(2)
    seen = {pid() for _ in range(4)}
    assert len(seen) == 4  # jamais deux documents dans le même processus / never two documents per process
    deadline = time.monotonic() + 30
    while len(_sandbox._current_pool()._idle) < 2 and time.monotonic() < deadline:
        time.sleep(0.1)
    assert len(_sandbox._current_pool()._idle) == 2  # réserve reconstituée / reserve refilled


def test_document_errors_cross_the_process_boundary() -> None:
    data = encrypt_pdf(contract_pdf(), "secret")
    with pytest.raises(EncryptedDocumentError) as isolated:
        to_markdown(data, "c.pdf", SANDBOX)
    with pytest.raises(EncryptedDocumentError) as local:
        to_markdown(data, "c.pdf", LOCAL)
    assert str(isolated.value) == str(local.value)
    assert pid()  # le travailleur reste utilisable / the worker stays usable


def test_timeout_kills_the_worker() -> None:
    started = time.perf_counter()
    with pytest.raises(ConversionTimeoutError, match="1 s"):
        _sandbox.run("convert_samples:sleep_forever", b"x", (), 1.0)
    assert time.perf_counter() - started < 10
    assert pid()  # un nouveau travailleur prend le relais / a new worker takes over


def test_crash_is_reported_without_details() -> None:
    with pytest.raises(DocumentError) as error:
        _sandbox.run("convert_samples:crash", b"x", (), 30)
    assert str(error.value) == CRASH_MESSAGE
    assert pid()


def test_unexpected_errors_never_carry_document_content() -> None:
    before = pid()
    with pytest.raises(DocumentError) as error:
        _sandbox.run("convert_samples:leak", b"NIR 1 85 05 78 006 084 91", (), 30)
    assert str(error.value) == FAILURE_MESSAGE and "085" not in str(error.value)
    assert error.value.__cause__ is None
    assert pid() != before  # travailleur recyclé après une erreur imprévue / recycled after an unexpected error


def test_a_compromised_worker_cannot_run_code_in_the_parent() -> None:
    # Les réponses sont du JSON : un pickle piégé n'est jamais chargé par le parent.
    # Replies are JSON: a trapped pickle is never loaded by the parent.
    os.environ.pop(COMPROMISED, None)
    with pytest.raises(DocumentError) as error:
        _sandbox.run("convert_samples:forge_pickle_reply", b"x", (), 30)
    assert str(error.value) == CRASH_MESSAGE
    assert COMPROMISED not in os.environ
    assert pid()  # travailleur suspect remplacé / suspicious worker replaced


@pytest.mark.parametrize("raw", [b"\x80\x04K\x01.", b"not json", b"[]", b'["ok"]', b'["error", 1, "m", true]',
                                 b'["ready", 1]', b"[" * 100_000],
                         ids=["pickle", "text", "empty", "short", "bad-error", "wrong-status", "deep"])
def test_malformed_replies_are_refused(raw: bytes) -> None:
    with pytest.raises(DocumentError) as error:
        _sandbox._decode(raw, "ok", "error")
    assert str(error.value) == CRASH_MESSAGE and error.value.__context__ is None


@pytest.mark.parametrize("reply", [None, "texte", ["md", "pdf", None, []], ["md", "pdf", "2", [], {}],
                                   ["md", "pdf", None, [3], {}], ["md", "pdf", None, [], {"images": "1"}],
                                   ["md", ["pdf"], None, [], {}]])
def test_worker_results_are_type_checked(reply: object) -> None:
    with pytest.raises(DocumentError, match="arrêté brutalement"):
        _document(reply)
    assert _document(["md", "pdf", 2, ["w"], {"images": 1}]).pages == 2


def test_unserialisable_result_is_a_safe_failure() -> None:
    with pytest.raises(DocumentError) as error:
        _sandbox.run("convert_samples:unserialisable", b"secret", (), 30)
    assert str(error.value) == FAILURE_MESSAGE


def test_oversized_reply_is_refused() -> None:
    with pytest.raises(DocumentError) as error:
        _sandbox.run("convert_samples:echo", b"abc", ("x" * 5000,), 30, 1000)
    assert str(error.value) == CRASH_MESSAGE
    assert pid()


def test_memory_cap() -> None:
    configure_sandbox(memory_mb=384)
    with pytest.raises((DocumentTooLargeError, DocumentError)):
        _sandbox.run("convert_samples:allocate", b"x", (), 60)


def test_concurrent_conversions() -> None:
    data = contract_pdf()
    expected = to_markdown(data, "c.pdf", LOCAL).markdown
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: to_markdown(data, "c.pdf", SANDBOX).markdown, range(8)))
    assert results == [expected] * 8


def test_prewarm_and_configuration() -> None:
    prewarm(1)
    assert pid()
    with pytest.raises(ValueError):
        configure_sandbox(max_jobs_per_worker=0)
    with pytest.raises(TypeError):
        configure_sandbox(unknown_setting=1)


# --- cibles exécutées dans les travailleurs / targets run inside the workers ---------------------------


def parent_pid(data: bytes) -> int:
    return os.getppid()


def own_channels(data: bytes) -> int:
    """Sockets et tubes ouverts, hors entrées-sorties standard / open sockets and pipes, stdio excluded."""
    count = 0
    for fd in (int(name) for name in os.listdir("/proc/self/fd")):
        try:
            mode = os.fstat(fd).st_mode
        except OSError:
            continue  # descripteur du listage / the listing's own descriptor
        if fd > 2 and (stat.S_ISSOCK(mode) or stat.S_ISFIFO(mode)):
            count += 1
    return count


def noop() -> None:
    """Préchargement : ce module est importé avant tout appel / preload: this module is imported first."""


def body_reply(data: bytes) -> _sandbox.Body:
    return _sandbox.Body({"bytes": len(data)}, data.decode("utf-8") + "\U0001f642\ud800")


def sleep_briefly(data: bytes, seconds: float) -> int:
    time.sleep(seconds)
    return os.getpid()


def oom_score_adj(data: bytes) -> int:
    with open("/proc/self/oom_score_adj", encoding="ascii") as handle:
        return int(handle.read())


linux_only = pytest.mark.skipif(not _sandbox.ZYGOTE, reason="zygote : Linux seulement / Linux only")


@linux_only
def test_workers_are_the_preferred_oom_victims() -> None:
    # Saturation mémoire du conteneur : le noyau tue un travailleur (une requête), jamais le service.
    # Container memory saturation: the kernel kills a worker (one request), never the service.
    assert _sandbox.run(f"{__name__}:oom_score_adj", b"x", (), 30) == 1000
    with open("/proc/self/oom_score_adj", encoding="ascii") as handle:
        assert int(handle.read()) < 1000  # le parent garde son score / the parent keeps its score


@linux_only
def test_workers_are_forked_from_a_preloaded_zygote() -> None:
    parent = _sandbox.run(f"{__name__}:parent_pid", b"x", (), 30)
    zygote = _sandbox._current_pool().zygote
    assert zygote is not None and zygote.forks and parent == zygote.process.pid != os.getpid()


@linux_only
def test_zygote_can_launch_fresh_interpreters_instead() -> None:
    # Repli si le zygote avait plusieurs fils d'exécution (fork alors dangereux) / fallback when fork is unsafe.
    configure_sandbox(fork_workers=False, max_jobs_per_worker=1)
    parents = {_sandbox.run(f"{__name__}:parent_pid", b"x", (), 60) for _ in range(2)}
    zygote = _sandbox._current_pool().zygote
    assert zygote is not None and not zygote.forks and parents == {zygote.process.pid}
    assert pid() != pid()


@pytest.mark.parametrize(("raw", "command"), [
    (b'["fork", true]', ("fork", True)), (b'["fork", false]', ("fork", False)), (b'["kill", 42]', ("kill", 42)),
    (b'["fork"]', None), (b'["fork", 1]', None), (b'["kill", true]', None), (b'["kill", "42"]', None),
    (b'["exec", "rm"]', None), (b"\xff", None), (b"{}", None),
])
def test_zygote_commands_form_a_closed_set(raw: bytes, command: tuple[object, ...] | None) -> None:
    assert _sandbox._command(raw) == command


@linux_only
def test_a_forked_worker_keeps_no_channel_to_the_zygote() -> None:
    # Ni canal de commande ni canal d'arrêt : un travailleur exploité ne peut rien demander au zygote.
    # Neither control nor kill channel: an exploited worker cannot ask the zygote anything.
    assert _sandbox.run(f"{__name__}:own_channels", b"x", (), 30) == 1


def test_reserve_workers_outlive_the_thread_that_started_them() -> None:
    # Sous Linux, PR_SET_PDEATHSIG suit le FIL créateur : un travailleur lancé par un fil de remplissage
    # mourait avec lui. On Linux PR_SET_PDEATHSIG follows the creating THREAD: a worker started by a refill
    # thread used to die with it.
    configure_sandbox(max_jobs_per_worker=1, max_idle_workers=2)
    pool = _sandbox._current_pool()
    starter = threading.Thread(target=pool.warm, args=(2,))
    starter.start()
    starter.join()  # le fil créateur est terminé / the creating thread has ended
    time.sleep(0.5)
    reserved = {worker.pid for worker in pool._idle}
    assert len(reserved) == 2 and all(worker.alive() for worker in pool._idle)
    assert pid() in reserved  # servi par la réserve, pas par un travailleur neuf / served from the reserve


def test_large_text_replies_travel_raw_and_unchanged() -> None:
    reply = _sandbox.run(f"{__name__}:body_reply", "été".encode(), (), 30)
    assert isinstance(reply, _sandbox.Body) and reply.meta == {"bytes": 5}
    assert reply.text == "été\U0001f642\ud800"  # substitut isolé conservé / lone surrogate kept
    inline = _sandbox.run_inline(f"{__name__}:body_reply", "été".encode(), ())
    assert (inline.meta, inline.text) == (reply.meta, reply.text)


def test_raw_text_must_be_valid_utf8() -> None:
    with pytest.raises(DocumentError) as error:
        _sandbox._text(b"caf\xe9")
    assert str(error.value) == CRASH_MESSAGE and error.value.__context__ is None


def test_a_running_call_can_be_cancelled_from_another_thread() -> None:
    cancel = _sandbox.CancelHandle()
    timer = threading.Timer(0.5, cancel.cancel)
    timer.start()
    started = time.perf_counter()
    with pytest.raises(DocumentError, match="annulé"):
        _sandbox._current_pool().call("convert_samples:sleep_forever", b"x", (), 60, cancel=cancel)
    assert time.perf_counter() - started < 10 and cancel.cancelled
    early = _sandbox.CancelHandle()
    early.cancel()  # annulé avant même d'avoir un travailleur / cancelled before getting a worker
    with pytest.raises(DocumentError, match="annulé"):
        _sandbox._current_pool().call("convert_samples:echo", b"x", ("y",), 30, cancel=early)
    assert pid()  # le bac à sable continue / the sandbox carries on


def test_single_use_workers_really_run_in_parallel() -> None:
    configure_sandbox(max_jobs_per_worker=1, max_idle_workers=4, preload=f"{__name__}:noop")
    _sandbox._current_pool().warm(4)
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=4) as pool:
        pids = list(pool.map(lambda _: _sandbox.run(f"{__name__}:sleep_briefly", b"x", (0.8,), 30), range(4)))
    # Quatre processus distincts en même temps (3,2 s s'ils se suivaient) / four processes at once.
    assert len(set(pids)) == 4 and time.perf_counter() - started < 2.4
