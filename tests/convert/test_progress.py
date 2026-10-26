"""Avancement rapporté par le travailleur : trames bornées, vérifiées / worker progress: bounded, checked frames."""

from __future__ import annotations

import json
from typing import Any

import pytest

from gdprguardian.convert import _sandbox
from gdprguardian.documents import DocumentError, DocumentOptions
from gdprguardian.server.isolation import JOB_TARGET, IsolatedRunner, document_reply_limit, document_spec
from gdprguardian.server.options import AnonymizeOptions

TEXT = "Dossier de M. Jean Martin, jean.martin@exemple.fr, 06 12 34 56 78.\n" * 20


class FakeConnection:
    """Trames rejouées / replayed frames."""

    def __init__(self, frames: list[bytes]) -> None:
        self.frames = frames

    def recv_bytes(self, _max: int) -> bytes:
        return self.frames.pop(0)


def frame(*value: Any) -> bytes:
    return json.dumps(value).encode()


def test_progress_frames_go_to_the_callback_before_the_reply() -> None:
    seen: list[tuple[str, int | None, int | None]] = []
    conn = FakeConnection([frame("progress", ["converting", 1, 4]), frame("progress", ["anonymising", None, None]),
                           frame("ok", 42)])
    reply = _sandbox._read_reply(conn, 1 << 20, lambda *args: seen.append(args))  # type: ignore[arg-type]
    assert reply == ["ok", 42] and seen == [("converting", 1, 4), ("anonymising", None, None)]


@pytest.mark.parametrize("value", [["exfiltrating", 1, 2], ["converting", -1, 2], ["converting", "1", 2],
                                   ["converting", 1], "converting", ["converting", 1, 10**12]])
def test_malformed_progress_marks_the_worker_as_faulty(value: Any) -> None:
    conn = FakeConnection([frame("progress", value), frame("ok", 1)])
    with pytest.raises(DocumentError):
        _sandbox._read_reply(conn, 1 << 20)  # type: ignore[arg-type]


def test_progress_frames_are_bounded_in_number() -> None:
    conn = FakeConnection([frame("progress", ["converting", 1, 2])] * (_sandbox._MAX_PROGRESS_FRAMES + 1)
                          + [frame("ok", 1)])
    with pytest.raises(DocumentError):
        _sandbox._read_reply(conn, 1 << 20)  # type: ignore[arg-type]


def test_a_failing_callback_never_stops_the_job() -> None:
    def broken(*_: Any) -> None:
        raise RuntimeError("observer down")

    conn = FakeConnection([frame("progress", ["converting", 1, 2]), frame("ok", 7)])
    assert _sandbox._read_reply(conn, 1 << 20, broken) == ["ok", 7]  # type: ignore[arg-type]


def test_report_progress_outside_a_tracked_call_does_nothing() -> None:
    _sandbox.report_progress("converting", 1, 2)  # aucun appel suivi : sans effet / no tracked call: no effect


def _spec() -> str:
    return document_spec(AnonymizeOptions(), "document.txt", DocumentOptions(sandbox=False), 1_000_000)


def test_inline_job_reports_converting_then_anonymising() -> None:
    seen: list[str] = []
    value = _sandbox.run_inline(JOB_TARGET, TEXT.encode(), (_spec(),), document_reply_limit(1_000_000),
                                lambda stage, *_: seen.append(stage))
    assert isinstance(value, _sandbox.Body) and "jean.martin@exemple.fr" not in value.text
    assert seen == ["converting", "anonymising"]


def test_pdf_pages_are_reported_while_converting() -> None:
    from convert_bench import big_pdf

    seen: list[tuple[str, int | None, int | None]] = []
    spec = document_spec(AnonymizeOptions(), "document.pdf", DocumentOptions(sandbox=False), 1_000_000)
    value = _sandbox.run_inline(JOB_TARGET, big_pdf(30), (spec,), document_reply_limit(1_000_000),
                                lambda *event: seen.append(event))
    assert isinstance(value, _sandbox.Body)
    assert ("converting", 30, 30) in seen and seen[-1][0] == "anonymising"
    assert seen.index(("converting", 30, 30)) < len(seen) - 1


def test_isolated_worker_reports_progress_through_the_pipe() -> None:
    seen: list[str] = []
    runner = IsolatedRunner(memory_mb=2048, reserve=0)
    try:
        value = runner.run(TEXT.encode(), _spec(), 120.0, document_reply_limit(1_000_000),
                           _sandbox.CancelHandle(lambda stage, *_: seen.append(stage)))
    finally:
        runner.stop()
    assert isinstance(value, _sandbox.Body) and "jean.martin@exemple.fr" not in value.text
    assert seen == ["converting", "anonymising"]
