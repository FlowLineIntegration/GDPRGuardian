"""Fixtures du service : horloge injectée, convertisseur factice, clients / service fixtures."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import ExitStack
from typing import Any

import pytest
from fastapi.testclient import TestClient
from server_testkit import KEY_A, KEY_B, FakeClock, fake_anonymize_document

import gdprguardian.documents as documents
from gdprguardian.server import ServerConfig, create_app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def fake_documents(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(documents, "anonymize_document", fake_anonymize_document)


@pytest.fixture
def make_client(clock: FakeClock, fake_documents: None) -> Iterator[Callable[..., TestClient]]:
    """Fabrique de clients ; le cycle de vie (MCP) tourne pour chacun / client factory, lifespan running.

    Même protocole que les travailleurs, exécuté dans ce processus (faux convertisseur utilisable) ; les
    processus isolés ont leurs propres tests (test_isolation.py). Same protocol as the workers, run in this
    process (fake converter usable); isolated processes have their own tests.
    """
    with ExitStack() as stack:
        def factory(**overrides: Any) -> TestClient:
            settings: dict[str, Any] = {"api_keys": (KEY_A, KEY_B), "isolation": False, **overrides}
            if settings.get("dev_no_auth") or (settings.get("public") and "api_keys" not in overrides):
                settings["api_keys"] = ()
            app = create_app(ServerConfig(**settings), clock=clock)
            return stack.enter_context(TestClient(app))

        yield factory


@pytest.fixture
def client(make_client: Callable[..., TestClient]) -> TestClient:
    return make_client()
