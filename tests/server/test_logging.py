"""Aucun contenu, nom de fichier, jeton ni clé dans les journaux / no content, file name, token or key in logs."""

from __future__ import annotations

import logging
import os
import sys
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from server_testkit import AUTH_A, AUTH_B, KEY_A, KEY_B, MCP_HEADERS, SECRETS, SENSITIVE_TEXT, mcp_call

import gdprguardian.documents as documents
from gdprguardian.server.logs import ThirdPartyTracebackFilter, configure_logging, log_event

FILENAME = "cv_jean_dupont_1985.txt"


@pytest.fixture
def all_logs(caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch) -> pytest.LogCaptureFixture:
    for name in ("fastmcp", "mcp", "uvicorn", "starlette", "fastapi"):
        monkeypatch.setattr(logging.getLogger(name), "propagate", True)
    caplog.set_level(logging.DEBUG)
    return caplog


def test_no_personal_data_in_logs(make_client: Callable[..., TestClient], all_logs: pytest.LogCaptureFixture,
                                  monkeypatch: pytest.MonkeyPatch) -> None:
    client = make_client(max_upload_bytes=4096)
    leaks: list[str] = [KEY_A, KEY_B, FILENAME, "dupont", "Dupont", *SECRETS]

    client.post("/v1/anonymize/text", headers=AUTH_A, json={"text": SENSITIVE_TEXT})
    client.post("/v1/detect", headers=AUTH_A, json={"text": SENSITIVE_TEXT})
    client.post("/v1/anonymize/text", headers=AUTH_A, json={"text": SENSITIVE_TEXT, "profile": SENSITIVE_TEXT})
    client.post("/v1/anonymize/file", headers=AUTH_A, files={"file": (FILENAME, SENSITIVE_TEXT.encode(), "text/plain")})
    client.get("/v1/packs", headers={"Authorization": f"Bearer {KEY_A}-wrong"})
    client.get(f"/{SECRETS[1]}", headers=AUTH_A)

    ticket = client.post("/v1/uploads", headers=AUTH_A, json={"filename": FILENAME}).json()
    token = ticket["upload_url"].rsplit("/", 1)[-1]
    leaks += [token, ticket["upload_id"]]
    client.put(f"/v1/uploads/{token}", headers=AUTH_B, content=SENSITIVE_TEXT.encode())
    client.put(f"/v1/uploads/{token}", headers=AUTH_A, content=SENSITIVE_TEXT.encode())
    client.get(f"/v1/results/{ticket['upload_id']}", headers=AUTH_A)

    too_big = client.post("/v1/uploads", headers=AUTH_A, json={"filename": FILENAME}).json()
    leaks.append(too_big["upload_url"].rsplit("/", 1)[-1])
    client.put(too_big["upload_url"].removeprefix("http://testserver"), headers=AUTH_A, content=b"x" * 5000)

    created = client.post("/mcp", headers={**MCP_HEADERS, **AUTH_A},
                          json=mcp_call("create_upload", {"filename": FILENAME})).json()
    mcp_ticket = created["result"]["structuredContent"]
    leaks += [mcp_ticket["upload_url"].rsplit("/", 1)[-1], mcp_ticket["upload_id"]]
    client.post("/mcp", headers={**MCP_HEADERS, **AUTH_A}, json=mcp_call("anonymize_text", {"text": SENSITIVE_TEXT}))
    client.post("/mcp", headers={**MCP_HEADERS, **AUTH_A},
                json=mcp_call("get_anonymized", {"upload_id": mcp_ticket["upload_id"]}))
    client.post("/mcp", headers={**MCP_HEADERS, "Authorization": f"Bearer {SECRETS[0]}"},
                json=mcp_call("anonymize_text", {"text": SENSITIVE_TEXT}))
    invalid = client.post("/mcp", headers={**MCP_HEADERS, **AUTH_A},
                          json=mcp_call("anonymize_text", {"text": "x", "profile": SENSITIVE_TEXT}))
    assert "Dupont" not in invalid.text
    client.post("/v1/anonymize/text", json={"text": SENSITIVE_TEXT})  # sans clé / without a key
    client.post("/v1/uploads", headers=AUTH_A, json={"filename": FILENAME, SENSITIVE_TEXT: 1})

    def explode(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError(f"échec sur {SENSITIVE_TEXT} ({FILENAME})")

    monkeypatch.setattr(documents, "anonymize_document", explode)
    failed = client.post("/v1/anonymize/file", headers=AUTH_A,
                         files={"file": (FILENAME, SENSITIVE_TEXT.encode(), "text/plain")})
    assert failed.status_code == 500

    # Journaux du serveur seulement : httpx est ici le client de test / server logs only, httpx is the test client.
    text = "\n".join(record.getMessage() for record in all_logs.records
                     if not record.name.startswith(("httpx", "httpcore")))
    assert "event=request" in text and "route=/v1/uploads/{token}" in text
    assert "event=internal_error" in text and "error=runtimeerror" in text
    assert "event=auth_failed" in text
    for leak in leaks:
        assert leak not in text, leak


def test_third_party_tracebacks_are_stripped() -> None:
    # Ex. « Exception in ASGI application » d'uvicorn : la trace citerait le document / the traceback would quote.
    try:
        raise ValueError(f"cellule illisible : {SENSITIVE_TEXT}")
    except ValueError:
        record = logging.LogRecord("uvicorn.error", logging.ERROR, __file__, 1, "Exception in %s", ("ASGI",),
                                   sys.exc_info())
    assert ThirdPartyTracebackFilter().filter(record)
    text = logging.Formatter().format(record)
    assert text == "Exception in ASGI [ValueError, trace supprimée / traceback suppressed]"
    own = logging.LogRecord("gdprguardian.server", logging.ERROR, __file__, 1, "own", None, None)
    assert ThirdPartyTracebackFilter().filter(own) and own.msg == "own"


def test_configure_logging_uses_one_filtered_handler(monkeypatch: pytest.MonkeyPatch) -> None:
    root, fastmcp_logger = logging.getLogger(), logging.getLogger("fastmcp")
    monkeypatch.setattr(root, "handlers", list(root.handlers))
    monkeypatch.setattr(root, "level", root.level)
    monkeypatch.setattr(fastmcp_logger, "handlers", [logging.NullHandler()])
    monkeypatch.setattr(fastmcp_logger, "propagate", False)
    monkeypatch.setattr(os, "environ", dict(os.environ))
    configure_logging("info")
    assert len(root.handlers) == 1 and root.level == logging.INFO
    assert any(isinstance(f, ThirdPartyTracebackFilter) for f in root.handlers[0].filters)
    # Les sorties Rich de FastMCP (non propagées, avec traces) sont coupées / FastMCP's Rich output is removed.
    assert fastmcp_logger.propagate and not fastmcp_logger.handlers
    assert os.environ["FASTMCP_LOG_ENABLED"] == "false"


@pytest.mark.parametrize(("value", "expected"), [
    (12, "12"), (1.25, "1.2"), (True, "true"), (None, "none"), ("pdf", "pdf"), ("PUT", "PUT"),
    ("/v1/results/{upload_id}", "/v1/results/{upload_id}"), ("Jean Dupont", "redacted"),
    ("jean.dupont@exemple.fr", "redacted"), ("x" * 49, "redacted"), (b"bytes", "redacted"),
])
def test_log_values_are_restricted(caplog: pytest.LogCaptureFixture, value: object, expected: str) -> None:
    caplog.set_level(logging.INFO, logger="gdprguardian.server")
    log_event("probe", value=value)  # type: ignore[arg-type]
    assert caplog.records[-1].getMessage() == f"event=probe value={expected}"
