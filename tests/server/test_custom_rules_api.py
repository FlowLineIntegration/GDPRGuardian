"""Règles de l'organisation dans l'appel REST et MCP / organisation rules in REST and MCP calls."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import pytest
from fastapi.testclient import TestClient
from server_testkit import AUTH_A, MCP_HEADERS, NIR, mcp_call

from gdprguardian import _native

pytestmark = pytest.mark.skipif(not _native.available(), reason="noyau Rust requis / Rust core required")

RULES = {"name": "acme", "rules": [{"label": "CLIENT_ID", "pattern": "CLT-[0-9]{6}"}],
         "deny": {"PROJET": ["Opération Phénix"]}}
TEXT = f"Client CLT-204518, NIR {NIR}, Opération Phénix."


def test_rest_applies_rules_and_explains(client: TestClient) -> None:
    response = client.post("/v1/anonymize/text", headers=AUTH_A, json={"text": TEXT, "rules": RULES, "explain": True})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["text"] == "Client [CLIENT_ID_1], NIR [NIR_1], [PROJET_1]."
    reasons = {(line["tag"], line["reason"]) for line in body["report"]["explain"]}
    assert ("[CLIENT_ID_1]", "custom_rule") in reasons and ("[NIR_1]", "validated") in reasons
    assert "204518" not in response.text and body["report"]["rules"] == "acme"


@pytest.mark.parametrize(("rules", "fragment"), [
    ({"rules": [{"label": "X", "pattern": "a+(?<=a)b"}]}, "linéaire"),
    ({"rules": [{"label": "x", "pattern": "a"}]}, "MAJUSCULES"),
    ({"rules": [{"label": "X", "pattern": "a"}] * 21}, "au plus"),
])
def test_rest_rejects_invalid_rules_with_a_clear_message(client: TestClient, rules: dict[str, Any],
                                                         fragment: str) -> None:
    response = client.post("/v1/anonymize/text", headers=AUTH_A, json={"text": "x", "rules": rules})
    assert response.status_code == 422 and fragment in response.json()["error"]["message"]


def test_multipart_accepts_rules_as_json(client: TestClient) -> None:
    import json

    files = {"file": ("note.txt", TEXT.encode(), "text/plain")}
    response = client.post("/v1/anonymize/file", headers=AUTH_A, files=files,
                           data={"rules": json.dumps(RULES), "explain": "true"})
    assert response.status_code == 200, response.text
    assert "[CLIENT_ID_1]" in response.json()["markdown"] and response.json()["report"]["explain"]


def test_mcp_tool_accepts_rules(client: TestClient) -> None:
    response = client.post("/mcp", headers={**MCP_HEADERS, **AUTH_A},
                           json=mcp_call("anonymize_text", {"text": TEXT, "rules": RULES, "explain": True}))
    result = response.json()["result"]
    assert result["isError"] is False
    assert result["content"][0]["text"] == "Client [CLIENT_ID_1], NIR [NIR_1], [PROJET_1]."
    assert result["structuredContent"]["report"]["explain"]


def test_service_default_is_an_explicit_country(client: TestClient) -> None:
    report = client.post("/v1/anonymize/text", headers=AUTH_A, json={"text": "x"}).json()["report"]
    assert report["countries"] == ["FR"] and report["country_mode"] == "explicit"


# --- Accueil : contrôle de structure seulement / front: structural check only -----------------------------------

# Coûteux à compiler : ensembles larges insensibles à la casse, \w répétés après \b (revues seams et service).
# Costly to compile: wide case-insensitive sets, repeated \w after \b (seams and service reviews).
COSTLY = {"rules": [{"label": f"R{i}", "pattern": "[" + "".join(f"\\x00-\\u{0xffff - k:04x}" for k in range(38))
                     + "]" if i % 2 else r"\b\w{600}"} for i in range(20)]}
REFUSED = {"rules": [{"label": "X", "pattern": "a+(?<=a)b"}]}


def test_the_front_never_compiles_organisation_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    from gdprguardian.custom import RuleSet
    from gdprguardian.server.options import AnonymizeOptions

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        pytest.fail("compilation dans le processus d'accueil / compiled in the front process")

    monkeypatch.setattr(_native, "build", forbidden)
    monkeypatch.setattr(RuleSet, "recognizers", forbidden)
    started = time.perf_counter()
    options = AnonymizeOptions.build(rules=COSTLY)
    assert options.rules is not None and len(options.rules.rules) == 20
    assert time.perf_counter() - started < 0.5  # autrefois 5 à 50 s sur la boucle / formerly 5-50 s on the loop
    # Erreur de structure : toujours refusée à l'entrée / structural error: still refused at the door.
    with pytest.raises(ValueError, match="MAJUSCULES"):
        AnonymizeOptions.build(rules={"rules": [{"label": "x", "pattern": "a"}]})


def test_refused_patterns_come_back_from_the_worker_as_422(client: TestClient,
                                                            caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG, logger="gdprguardian.server")  # événements par requête : DEBUG / per-request
    for route in ("/v1/anonymize/text", "/v1/detect"):
        response = client.post(route, headers=AUTH_A, json={"text": TEXT, "rules": REFUSED})
        error = response.json()["error"]
        assert response.status_code == 422 and error["code"] == "invalid_request", response.text
        assert error["message"].startswith("Option invalide / invalid option: Règle n°1 (X) : construction refusée "
                                           "par le moteur linéaire / refused by the linear-time engine: ")
    files = {"file": ("note.txt", TEXT.encode(), "text/plain")}
    response = client.post("/v1/anonymize/file", headers=AUTH_A, files=files, data={"rules": json.dumps(REFUSED)})
    assert response.status_code == 422 and "linéaire" in response.json()["error"]["message"]
    # Journal : le code seulement, ni motif ni raison / log: the code only, neither pattern nor reason.
    assert "code=invalid_rules" in caplog.text and "(?<=" not in caplog.text and "ERROR" not in caplog.text
    assert NIR not in response.text


def test_an_upload_with_a_refused_pattern_fails_at_processing(client: TestClient) -> None:
    # Pas de travailleur au ticket : le motif est compilé au traitement / no worker at ticket time.
    ticket = client.post("/v1/uploads", headers=AUTH_A, json={"filename": "note.txt", "rules": REFUSED})
    assert ticket.status_code == 201, ticket.text
    put = client.put(ticket.json()["upload_url"].removeprefix("http://testserver"), headers=AUTH_A,
                     content=TEXT.encode())
    assert put.status_code == 422 and "linéaire" in put.json()["error"]["message"]
    result_url = ticket.json()["result_url"].removeprefix("http://testserver")
    result = client.get(result_url, headers=AUTH_A)
    assert result.status_code == 422 and result.json()["error"] == put.json()["error"]
    assert client.get(result_url, headers=AUTH_A).status_code == 404  # signalé une fois / reported once
    # Erreur de structure : refusée dès le ticket / structural error: refused at ticket time.
    bad = client.post("/v1/uploads", headers=AUTH_A, json={"filename": "note.txt",
                                                            "rules": {"rules": [{"label": "x", "pattern": "a"}]}})
    assert bad.status_code == 422


def test_mcp_tool_reports_a_refused_pattern(client: TestClient) -> None:
    response = client.post("/mcp", headers={**MCP_HEADERS, **AUTH_A},
                           json=mcp_call("anonymize_text", {"text": TEXT, "rules": REFUSED}))
    result = response.json()["result"]
    assert result["isError"] is True
    assert result["content"][0]["text"].startswith("invalid_request: Option invalide / invalid option: Règle n°1 (X)")
    assert NIR not in response.text


def test_a_pattern_carrying_a_lone_surrogate_gets_an_encodable_message(client: TestClient) -> None:
    # Le message de `re` cite le caractère fautif tel quel : un demi-codet isolé ne doit pas casser la réponse.
    # `re`'s message quotes the faulty character as is: a lone surrogate must not break the reply.
    body = json.dumps({"text": "x", "rules": {"rules": [{"label": "X", "pattern": "(?<\ud800a)"}]}})
    response = client.post("/v1/anonymize/text", headers={**AUTH_A, "content-type": "application/json"},
                           content=body)
    assert response.status_code == 422 and "motif invalide" in response.json()["error"]["message"]
