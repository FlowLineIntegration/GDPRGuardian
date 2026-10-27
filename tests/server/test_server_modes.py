"""Trois modes côté serveur : mode, disable, profile déprécié, refus, rapport, descriptions.

Three modes on the server side: REST and every MCP anonymisation tool take `mode` and `disable` with the same names,
schemas and descriptions, mapped to the engine's Settings.mode / Settings.disable (docs/REGLES.md « Modes »).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from fastmcp import Client
from fastmcp.exceptions import ToolError
from server_testkit import AUTH_A, MCP_HEADERS, mcp_call

from gdprguardian.categories import MODES_HELP
from gdprguardian.server.api import OptionsBody
from gdprguardian.server.config import ServerConfig
from gdprguardian.server.limiter import LimitPolicy
from gdprguardian.server.mcp_local import build_local_mcp
from gdprguardian.server.mcp_online import build_online_mcp
from gdprguardian.server.options import (
    DISABLE_DESCRIPTION,
    MAX_DISABLE,
    MODE_DESCRIPTION,
    AnonymizeOptions,
    parse_mode,
)
from gdprguardian.server.service import Service

# Exemple du jeu d'évaluation du propriétaire (fictif) : deux contrôles que le mode fort masque exprès.
# The owner's evaluation example (fictitious): two controls mode fort masks on purpose.
TEXT = "Commande SKU-ALPHA-0042, écrire à support@atelier-exemple.invalid ; contact : jean.dupont@exemple.fr."
CONFIG = ServerConfig(dev_no_auth=True, limits=LimitPolicy(mode="off"), isolation=False)


# --- analyse / parsing ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(("mode", "profile", "disable", "expected"), [
    (None, None, None, ("fort", ())),                       # défaut de toutes les entrées / default everywhere
    ("strong", None, None, ("fort", ())),
    ("essentiel", None, None, ("essentiel", ())),
    ("essential", None, None, ("essentiel", ())),
    ("basique", None, None, ("essentiel", ())),             # ancien nom, accepté / former name, accepted
    ("basic", None, None, ("essentiel", ())),
    ("custom", None, ["codes"], ("personnalise", ("codes",))),
    (None, None, ["functional_mailboxes", "codes"], ("personnalise", ("boites_fonctionnelles", "codes"))),
    (None, None, "codes, boites_fonctionnelles", ("personnalise", ("boites_fonctionnelles", "codes"))),
    (None, "strict", None, ("fort", ())),                   # profil déprécié / deprecated profile
    (None, "standard", None, ("essentiel", ())),
    (None, "fast", None, ("essentiel", ())),
    ("fort", "strict", None, ("fort", ())),
])
def test_modes_and_aliases_resolve_to_canonical_names(mode: str | None, profile: str | None, disable: Any,
                                                       expected: tuple[str, tuple[str, ...]]) -> None:
    assert parse_mode(mode, profile, disable) == expected


@pytest.mark.parametrize(("mode", "profile", "disable", "message"), [
    ("turbo", None, None, f"unknown mode; allowed: {MODES_HELP}"),
    ("fort", None, ["codes"], "disable only works with mode personnalise"),
    ("essentiel", None, ["codes"], "mode essentiel cannot be changed"),
    (None, None, ["code"], "unknown category; did you mean codes?; allowed: personnes (persons)"),
    (None, None, ["paranoid"], "unknown category; allowed: personnes (persons)"),
    ("essentiel", "strict", None, "deprecated profile contradicts mode"),
    (None, None, ["codes"] * (MAX_DISABLE + 1), f"at most {MAX_DISABLE} categories"),
])
def test_refusals_name_the_allowed_values(mode: str | None, profile: str | None, disable: Any, message: str) -> None:
    with pytest.raises(ValueError, match=message.replace("(", r"\(").replace(")", r"\)").replace("?", r"\?")
                       .replace("|", r"\|")):
        parse_mode(mode, profile, disable)


def test_options_carry_mode_disable_and_profile_to_the_worker_and_the_engine() -> None:
    options = AnonymizeOptions.build("FR", None, "fr", None, False, disable="codes,functional_mailboxes")
    assert (options.mode, options.disable, options.profile) == ("personnalise", ("boites_fonctionnelles", "codes"),
                                                               None)
    restored = AnonymizeOptions.from_json(options.to_json())
    assert (restored.mode, restored.disable) == (options.mode, options.disable)
    assert options.engine_settings() == {"mode": "personnalise", "disable": ("boites_fonctionnelles", "codes")}
    legacy = AnonymizeOptions.build("FR", "strict")
    # Profil déprécié transmis au moteur (mêmes effets que la bibliothèque) / passed on, same effects as the library.
    assert legacy.engine_settings() == {"mode": "fort", "disable": (), "profile": "strict"}
    assert AnonymizeOptions.from_json(legacy.to_json()).profile == "strict"
    engine = options.anonymizer()
    assert (engine.settings.mode, tuple(engine.settings.disable)) == ("personnalise",
                                                                      ("boites_fonctionnelles", "codes"))


def test_rest_and_mcp_share_the_same_mode_descriptions() -> None:
    properties = OptionsBody.model_json_schema()["properties"]
    assert properties["mode"]["description"] == MODE_DESCRIPTION
    assert properties["disable"]["description"] == DISABLE_DESCRIPTION
    assert properties["profile"]["deprecated"] is True
    assert "Keep the default unless the user asked" in MODE_DESCRIPTION
    for example in ("'essentiel'", "\"boites_fonctionnelles\"", "keep rule"):
        assert example in MODE_DESCRIPTION


# --- REST ----------------------------------------------------------------------------------------------------------


def test_rest_default_is_fort_and_masks_codes_and_shared_mailboxes(client: TestClient) -> None:
    body = client.post("/v1/anonymize/text", headers=AUTH_A, json={"text": TEXT}).json()
    assert body["report"]["mode"] == "fort" and body["report"]["disable"] == []
    assert "SKU-ALPHA-0042" not in body["text"] and "support@" not in body["text"]
    assert not any("Mode" in warning for warning in body["report"]["warnings"])


def test_rest_essentiel_keeps_codes_and_shared_mailboxes_and_warns(client: TestClient) -> None:
    body = client.post("/v1/anonymize/text", headers=AUTH_A, json={"text": TEXT, "mode": "essentiel"}).json()
    assert body["report"]["mode"] == "essentiel"
    assert "SKU-ALPHA-0042" in body["text"] and "support@atelier-exemple.invalid" in body["text"]
    assert "jean.dupont@exemple.fr" not in body["text"]
    assert any(warning.startswith("Mode essentiel") for warning in body["report"]["warnings"])


def test_rest_disable_selects_personnalise(client: TestClient) -> None:
    body = client.post("/v1/anonymize/text", headers=AUTH_A,
                       json={"text": TEXT, "disable": ["codes", "boites_fonctionnelles"]}).json()
    assert body["report"]["mode"] == "personnalise"
    assert body["report"]["disable"] == ["boites_fonctionnelles", "codes"]
    assert "SKU-ALPHA-0042" in body["text"] and "support@atelier-exemple.invalid" in body["text"]
    assert any("categories left in clear" in warning for warning in body["report"]["warnings"])


def test_rest_disabling_persons_warns_plainly(client: TestClient) -> None:
    body = client.post("/v1/anonymize/text", headers=AUTH_A,
                       json={"text": "M. Jean Dupont signe.", "mode": "personnalise", "disable": ["persons"]}).json()
    assert any("the text is not anonymised" in warning for warning in body["report"]["warnings"])


@pytest.mark.parametrize(("payload", "message"), [
    ({"mode": "fort", "disable": ["codes"]}, "disable only works with mode personnalise"),
    ({"disable": ["code"]}, "did you mean codes?"),
])
def test_rest_refusals(client: TestClient, payload: dict[str, Any], message: str) -> None:
    response = client.post("/v1/anonymize/text", headers=AUTH_A, json={"text": "x", **payload})
    assert response.status_code == 422 and message in response.json()["error"]["message"]


def test_rest_unknown_mode_lists_the_modes(client: TestClient) -> None:
    response = client.post("/v1/anonymize/text", headers=AUTH_A, json={"text": "x", "mode": "turbo"})
    assert response.status_code == 422 and response.json()["error"]["allowed"] == [f"mode: {MODES_HELP}"]


def test_multipart_takes_mode_and_comma_separated_disable(client: TestClient) -> None:
    response = client.post("/v1/anonymize/file", headers=AUTH_A,
                           files={"file": ("dossier.txt", TEXT.encode(), "text/plain")},
                           data={"disable": "codes,boites_fonctionnelles"})
    assert response.status_code == 200, response.text
    assert response.json()["report"]["mode"] == "personnalise"
    unknown = client.post("/v1/anonymize/file", headers=AUTH_A, files={"file": ("a.txt", b"x", "text/plain")},
                          data={"modes": "fort"})
    assert unknown.status_code == 422 and "allowed: file, countries, disable, explain" in unknown.text


def test_upload_ticket_keeps_the_mode(client: TestClient) -> None:
    ticket = client.post("/v1/uploads", headers=AUTH_A, json={"filename": "dossier.txt", "mode": "essentiel"}).json()
    put = client.put(ticket["upload_url"].removeprefix("http://testserver"), headers=AUTH_A, content=TEXT.encode())
    assert put.status_code == 202
    result = client.get(ticket["result_url"].removeprefix("http://testserver"), headers=AUTH_A).json()
    assert result["report"]["mode"] == "essentiel" and "SKU-ALPHA-0042" in result["markdown"]


# --- MCP -----------------------------------------------------------------------------------------------------------


@pytest.mark.anyio
async def test_mcp_tools_take_mode_and_disable_online_and_locally(tmp_path: Any) -> None:
    online = build_online_mcp(Service(CONFIG), auth=None)
    local = build_local_mcp([tmp_path], CONFIG)
    for server, intake in ((online, "create_upload"), (local, "anonymize_file")):
        async with Client(server) as client:
            tools = {tool.name: tool for tool in await client.list_tools()}
            for name in ("anonymize_text", intake):
                properties = tools[name].inputSchema["properties"]
                assert properties["mode"]["description"] == MODE_DESCRIPTION
                assert properties["disable"]["description"] == DISABLE_DESCRIPTION
                description = (tools[name].description or "").lower()
                assert "keep the default unless the user asked" in description and "mode 'essentiel'" in description
            result = await client.call_tool("anonymize_text", {"text": TEXT, "mode": "essentiel"})
            assert result.structured_content["report"]["mode"] == "essentiel"
            assert "SKU-ALPHA-0042" in result.content[0].text
            # Avertissement du mode dans un second bloc, jamais dans le texte / mode warning in a second block.
            assert len(result.content) == 2 and "Mode essentiel" in result.content[1].text
            assert "Mode essentiel" not in result.content[0].text
            with pytest.raises(ToolError, match="disable only works with mode personnalise"):
                await client.call_tool("anonymize_text", {"text": "x", "mode": "fort", "disable": ["codes"]})


@pytest.mark.anyio
async def test_server_instructions_explain_the_three_modes(tmp_path: Any) -> None:
    for server in (build_online_mcp(Service(CONFIG), auth=None), build_local_mcp([tmp_path], CONFIG)):
        instructions = server.instructions or ""
        for needle in ("keep the default unless the user asked", "mode 'fort'", "mode 'essentiel'",
                       "mode 'personnalise'", "\"boites_fonctionnelles\"", "\"action\": \"keep\""):
            assert needle in instructions, needle


def test_mcp_over_http_reports_the_mode(make_client: Callable[..., TestClient]) -> None:
    client = make_client()
    body = client.post("/mcp", headers={**MCP_HEADERS, **AUTH_A},
                       json=mcp_call("anonymize_text", {"text": TEXT, "disable": "codes"})).json()["result"]
    assert body["structuredContent"]["report"]["mode"] == "personnalise"
    assert body["structuredContent"]["report"]["disable"] == ["codes"]
