"""API REST : points d'entrée, authentification, limites, erreurs génériques / REST endpoints and guards."""

from __future__ import annotations

import inspect
import sys
from collections.abc import Callable, Iterator, Mapping
from typing import Protocol

import pytest
from fastapi.testclient import TestClient
from server_testkit import AUTH_A, AUTH_B, EMAIL, IBAN, KEY_A, NIR, SENSITIVE_TEXT

import gdprguardian.documents as documents
from gdprguardian.documents import ConversionTimeoutError, EncryptedDocumentError, MaliciousDocumentError
from gdprguardian.server import ServerConfig, create_app
from gdprguardian.server.limiter import LimitPolicy

SECURITY_HEADERS = ("x-content-type-options", "x-frame-options", "referrer-policy", "cache-control",
                    "content-security-policy")


class HasHeaders(Protocol):
    headers: Mapping[str, str]


def assert_secure(response: HasHeaders) -> None:
    for header in SECURITY_HEADERS:
        assert header in response.headers, header
    assert response.headers["cache-control"] == "no-store"


def test_the_auth_dependency_never_hops_to_a_thread() -> None:
    # FastAPI exécute une dépendance synchrone dans un fil, à chaque requête : fils en plus (--pids-limit) et
    # latence. FastAPI runs a sync dependency in a thread on every request: extra threads and latency.
    from gdprguardian.server import api

    assert inspect.iscoroutinefunction(api._principal)


def test_health_is_public(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert_secure(response)


def test_docs_are_hidden_by_default(client: TestClient, make_client: Callable[..., TestClient]) -> None:
    # Sans clé : 401 comme tout chemin non public ; avec clé : absent / without a key 401, with a key 404.
    assert client.get("/docs").status_code == 401
    assert client.get("/docs", headers=AUTH_A).status_code == 404
    assert client.get("/openapi.json", headers=AUTH_A).status_code == 404
    documented = make_client(docs=True)
    assert documented.get("/openapi.json").status_code == 200
    docs = documented.get("/docs")
    # La page /docs charge ses scripts : pas de CSP stricte, le reste des en-têtes demeure.
    # The /docs page loads its scripts: no strict CSP there, the other headers remain.
    assert docs.status_code == 200 and "content-security-policy" not in docs.headers
    assert docs.headers["x-content-type-options"] == "nosniff"
    assert "content-security-policy" in documented.get("/health").headers


def test_rest_api_still_works_without_fastmcp(make_client: Callable[..., TestClient],
                                              monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "gdprguardian.server.mcp_online", None)
    client = make_client()
    assert client.app.state.mcp is None
    assert client.post("/v1/anonymize/text", headers=AUTH_A, json={"text": "x"}).status_code == 200
    assert client.post("/mcp", headers=AUTH_A, json={}).status_code == 404


@pytest.mark.parametrize(("method", "path"), [
    ("GET", "/v1/packs"), ("POST", "/v1/anonymize/text"), ("POST", "/v1/detect"), ("POST", "/v1/anonymize/file"),
    ("POST", "/v1/uploads"), ("PUT", "/v1/uploads/" + "x" * 43), ("GET", "/v1/results/up_" + "x" * 22),
    ("DELETE", "/v1/results/up_" + "x" * 22),
])
@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer wrong-key-0123456789-0123456789"},
                                     {"Authorization": KEY_A}])
def test_every_endpoint_requires_a_valid_key(client: TestClient, method: str, path: str,
                                             headers: dict[str, str]) -> None:
    response = client.request(method, path, headers=headers, json={"text": "x"})
    assert response.status_code == 401
    assert response.headers["www-authenticate"].startswith("Bearer")
    assert response.json()["error"]["code"] == "unauthorized"
    assert_secure(response)


@pytest.mark.parametrize(("path", "body"), [
    ("/v1/anonymize/text", b'{"text": "' + NIR.encode()),   # JSON tronqué / truncated JSON
    ("/v1/anonymize/text", b'{"texte": 1}'),                 # schéma invalide / invalid schema
    ("/v1/anonymize/file", b"--x\r\n"),                      # multipart cassé / broken multipart
])
def test_unauthenticated_bodies_are_never_parsed(client: TestClient, path: str, body: bytes) -> None:
    # 401 avant toute lecture : ni 422 ni détail de validation / 401 before any read: no 422, no details.
    response = client.post(path, content=body, headers={"Content-Type": "application/json"})
    assert response.status_code == 401
    assert set(response.json()["error"]) == {"code", "message"}


def test_unauthenticated_oversized_body_gets_401_not_413(make_client: Callable[..., TestClient]) -> None:
    client = make_client(max_json_bytes=1024)
    response = client.post("/v1/anonymize/text", content=b"x" * 4096, headers={"Content-Type": "application/json"})
    assert response.status_code == 401


def test_rate_limit_applies_before_the_body_is_parsed(make_client: Callable[..., TestClient]) -> None:
    # Rafale de coût minuscule : le premier texte la consomme, le suivant est refusé avant toute lecture.
    # Tiny cost burst: the first text uses it up, the next one is refused before anything is read.
    client = make_client(limits=LimitPolicy(cost_burst=0.006, cost_rate=0.001))
    assert client.post("/v1/anonymize/text", headers=AUTH_A, json={"text": "x"}).status_code == 200
    limited = client.post("/v1/anonymize/text", headers={**AUTH_A, "Content-Type": "application/json"},
                          content=b"{broken")
    assert limited.status_code == 429 and limited.json()["error"]["code"] == "rate_limited"
    assert set(limited.json()["error"]) == {"code", "message"}
    assert int(limited.headers["retry-after"]) >= 1 and '"cpu"' in limited.headers["ratelimit"]
    assert_secure(limited)


def test_packs(client: TestClient) -> None:
    packs = {p["id"]: p for p in client.get("/v1/packs", headers=AUTH_A).json()["packs"]}
    assert {"FR", "INTL"} <= set(packs)
    assert all({"id", "entity", "label", "tier"} <= set(r) for r in packs["FR"]["recognizers"])


def test_anonymize_text(client: TestClient) -> None:
    response = client.post("/v1/anonymize/text", headers=AUTH_A,
                           json={"text": SENSITIVE_TEXT, "countries": "FR", "profile": "strict"})
    assert response.status_code == 200
    body = response.json()
    for secret in (NIR, EMAIL, IBAN):
        assert secret not in body["text"]
    assert "[NIR_1]" in body["text"] and "[EMAIL_1]" in body["text"]
    assert body["report"]["irreversible"] is True
    assert body["report"]["profile"] == "strict"
    assert_secure(response)


def test_label_language_and_country_list(client: TestClient) -> None:
    response = client.post("/v1/anonymize/text", headers=AUTH_A,
                           json={"text": f"mail {EMAIL}", "countries": ["fr", "INTL"], "label_language": "en"})
    assert response.json()["text"] == "mail [EMAIL_1]"


def test_detect_returns_the_report_only(client: TestClient) -> None:
    response = client.post("/v1/detect", headers=AUTH_A, json={"text": SENSITIVE_TEXT})
    body = response.json()
    assert set(body) == {"report"}
    assert body["report"]["entities"]["NIR"] == 1
    assert NIR not in response.text and EMAIL not in response.text


@pytest.mark.parametrize("payload", [
    {"text": 3},
    {"text": SENSITIVE_TEXT, "profile": "paranoid"},
    {"text": SENSITIVE_TEXT, "label_language": "de"},
    {"text": SENSITIVE_TEXT, "unexpected": SENSITIVE_TEXT},
    {"texte": SENSITIVE_TEXT},
])
def test_validation_errors_never_echo_input(client: TestClient, payload: dict[str, object]) -> None:
    response = client.post("/v1/anonymize/text", headers=AUTH_A, json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
    for secret in (NIR, EMAIL, "paranoid"):
        assert secret not in response.text


@pytest.mark.parametrize(("payload", "allowed"), [({"profile": "paranoid"}, "profile: fast | standard | strict"),
                                                  ({"label_language": "de"}, "label_language: fr | en | auto")])
def test_closed_options_list_their_allowed_values(client: TestClient, payload: dict[str, str], allowed: str) -> None:
    response = client.post("/v1/anonymize/text", headers=AUTH_A, json={"text": "x", **payload})
    assert response.status_code == 422 and response.json()["error"]["allowed"] == [allowed]


def test_validation_errors_never_echo_client_keys(client: TestClient) -> None:
    # Une clé JSON inventée peut contenir une donnée personnelle / a made-up JSON key may carry personal data.
    response = client.post("/v1/anonymize/text", headers=AUTH_A, json={SENSITIVE_TEXT: "x", "text": "y"})
    assert response.status_code == 422
    assert response.json()["error"]["fields"] == ["body.?"]
    assert "Dupont" not in response.text and NIR not in response.text


def test_lone_surrogates_are_refused_cleanly(client: TestClient) -> None:
    # JSON admet « \ud800 », UTF-8 non : sans contrôle, la réponse échouait en 500 / used to fail with a 500.
    response = client.post("/v1/anonymize/text", headers={**AUTH_A, "Content-Type": "application/json"},
                           content=b'{"text": "Jean \\ud800 Dupont"}')
    assert response.status_code == 422 and response.json()["error"]["code"] == "invalid_text"
    assert "Dupont" not in response.text


def test_unknown_country_is_refused(client: TestClient) -> None:
    response = client.post("/v1/anonymize/text", headers=AUTH_A, json={"text": "x", "countries": "ZZ,FR"})
    assert response.status_code == 422
    assert "ZZ" not in response.text


def test_malformed_json(client: TestClient) -> None:
    response = client.post("/v1/anonymize/text", headers={**AUTH_A, "Content-Type": "application/json"},
                           content=b'{"text": "' + NIR.encode())
    assert response.status_code == 422
    assert NIR not in response.text


def test_text_length_limit(make_client: Callable[..., TestClient]) -> None:
    client = make_client(max_text_chars=100)
    response = client.post("/v1/anonymize/text", headers=AUTH_A, json={"text": "a" * 101})
    assert response.status_code == 413


def test_body_limit_with_content_length(make_client: Callable[..., TestClient]) -> None:
    client = make_client(max_json_bytes=2048)
    response = client.post("/v1/anonymize/text", headers=AUTH_A, json={"text": "a" * 5000})
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"
    assert_secure(response)


def test_body_limit_with_chunked_transfer(make_client: Callable[..., TestClient]) -> None:
    client = make_client(max_json_bytes=2048)

    def chunks() -> Iterator[bytes]:
        yield b'{"text": "'
        for _ in range(10):
            yield b"a" * 500
        yield b'"}'

    response = client.post("/v1/anonymize/text", headers={**AUTH_A, "Content-Type": "application/json"},
                           content=chunks())
    assert response.status_code == 413


@pytest.mark.parametrize("value", [b"abc", b"\xb2", b"-1", b"1" * 19])
def test_invalid_content_length(client: TestClient, value: bytes) -> None:
    # « ² » passe str.isdigit() mais pas int() / "²" passes str.isdigit() but not int().
    response = client.post("/v1/anonymize/text", headers={**AUTH_A, "Content-Length": value}, content=b"{}")
    assert response.status_code == 400 and response.json()["error"]["code"] == "invalid_request"


def test_anonymize_file_multipart(client: TestClient) -> None:
    response = client.post("/v1/anonymize/file", headers=AUTH_A,
                           files={"file": ("dossier.txt", SENSITIVE_TEXT.encode(), "text/plain")},
                           data={"countries": "FR", "profile": "strict", "label_language": "fr"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["kind"] == "txt" and "document.txt" not in body["markdown"]
    assert NIR not in body["markdown"] and "[NIR_1]" in body["markdown"]
    # Contenu écarté signalé en clair, aussi dans report.warnings / dropped content told, also in report.warnings.
    dropped_warning = ("1 commentaire(s) écarté(s), ni anonymisé(s) ni rendu(s) / 1 comment(s) dropped, neither "
                       "anonymised nor returned")
    assert body["warnings"] == ["note", dropped_warning] and body["dropped"] == {"comments": 1}
    assert body["report"]["warnings"][-2:] == ["note", dropped_warning]
    assert body["report"]["profile"] == "strict"


@pytest.mark.parametrize("filename", ["C:\\Users\\jdupont\\Documents\\cv_jean_dupont.txt",
                                      "/home/jdupont/CV Jean DUPONT.TXT", "cv_jean_dupont.txt. "])
def test_multipart_file_name_never_reaches_the_result(client: TestClient, filename: str) -> None:
    # Seule l'extension sert : le nom (souvent personnel) n'est ni gardé ni renvoyé / only the extension is used.
    response = client.post("/v1/anonymize/file", headers=AUTH_A, files={"file": (filename, b"hello", "text/plain")})
    assert response.json()["markdown"].strip() == "hello" and "document" not in response.text
    assert "dupont" not in response.text.lower() and "jean" not in response.text.lower()


@pytest.mark.parametrize(("files", "data", "code"), [
    ({}, {"profile": "fast"}, "invalid_request"),
    ({"document": ("a.txt", b"x", "text/plain")}, {}, "invalid_request"),
    ({"file": ("a.txt", b"x", "text/plain")}, {"surprise": "1"}, "invalid_request"),
    ({"file": ("a.txt", b"x", "text/plain")}, {"profile": "paranoid"}, "invalid_request"),
    ({"file": ("a.pdf", b"%PDF", "application/pdf")}, {}, "unsupported_format"),
])
def test_multipart_errors(client: TestClient, files: dict[str, tuple[str, bytes, str]], data: dict[str, str],
                          code: str) -> None:
    response = client.post("/v1/anonymize/file", headers=AUTH_A, files=files or None, data=data)
    assert response.json()["error"]["code"] == code


def test_multipart_two_files_refused(client: TestClient) -> None:
    files = [("file", ("a.txt", b"x", "text/plain")), ("file", ("b.txt", b"y", "text/plain"))]
    response = client.post("/v1/anonymize/file", headers=AUTH_A, files=files)
    assert response.status_code == 422


def test_multipart_requires_multipart(client: TestClient) -> None:
    response = client.post("/v1/anonymize/file", headers=AUTH_A, json={"file": "x"})
    assert response.status_code == 422


def test_multipart_file_limit(make_client: Callable[..., TestClient]) -> None:
    client = make_client(max_upload_bytes=1024)
    response = client.post("/v1/anonymize/file", headers=AUTH_A,
                           files={"file": ("a.txt", b"x" * 1025, "text/plain")})
    assert response.status_code == 413
    ok = client.post("/v1/anonymize/file", headers=AUTH_A, files={"file": ("a.txt", b"x" * 1000, "text/plain")})
    assert ok.status_code == 200


@pytest.mark.parametrize(("error", "status", "code"), [
    (EncryptedDocumentError("mot de passe de Jean Dupont"), 422, "encrypted_document"),
    (MaliciousDocumentError("zip entry Jean_Dupont.xlsx"), 422, "malicious_document"),
    (ConversionTimeoutError("délai, Jean Dupont"), 422, "conversion_timeout"),
    (ImportError("No module named 'gdprguardian.convert'"), 501, "converter_unavailable"),
    (NotImplementedError("todo"), 501, "converter_unavailable"),
    (RuntimeError(f"boom {NIR}"), 500, "internal_error"),
])
def test_document_errors_use_fixed_messages(client: TestClient, monkeypatch: pytest.MonkeyPatch,
                                            error: Exception, status: int, code: str) -> None:
    def failing(*_args: object, **_kwargs: object) -> None:
        raise error

    monkeypatch.setattr(documents, "anonymize_document", failing)
    response = client.post("/v1/anonymize/file", headers=AUTH_A, files={"file": ("a.txt", b"x", "text/plain")})
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert "Dupont" not in response.text and NIR not in response.text


def test_exhausted_memory_budget_answers_503(client: TestClient) -> None:
    # Budget des corps tenus en mémoire épuisé : refus avec Retry-After, rien n'est traité / nothing processed.
    budget = client.app.state.service.budget
    assert budget.acquire("someone-else", budget.limit)
    try:
        busy = client.post("/v1/anonymize/file", headers=AUTH_A, files={"file": ("a.txt", b"x", "text/plain")})
        text = client.post("/v1/anonymize/text", headers=AUTH_A, json={"text": SENSITIVE_TEXT})
    finally:
        budget.release("someone-else", budget.limit)
    for response in (busy, text):
        assert response.status_code == 503 and response.json()["error"]["code"] == "service_busy"
        assert int(response.headers["retry-after"]) >= 1
        assert NIR not in response.text
        assert_secure(response)
    assert budget.used == 0  # rien de retenu après le refus / nothing held after the refusal
    assert client.post("/v1/anonymize/file", headers=AUTH_A,
                       files={"file": ("a.txt", b"x", "text/plain")}).status_code == 200
    assert budget.used == 0  # réservation rendue en fin de requête / reservation released at the end


def test_rate_limit(make_client: Callable[..., TestClient]) -> None:
    client = make_client(limits=LimitPolicy(cheap_burst=2, cheap_rate=0.01))
    first = client.get("/v1/packs", headers=AUTH_A)
    assert first.status_code == 200
    assert first.headers["ratelimit-policy"] == '"req";q=2;w=200' and first.headers["ratelimit"] == '"req";r=1;t=100'
    assert client.get("/v1/packs", headers=AUTH_A).status_code == 200
    limited = client.get("/v1/packs", headers=AUTH_A)
    assert limited.status_code == 429
    # Attente du seau (100 s) plus 0 à 20 % d'aléa / the bucket's wait (100 s) plus 0 to 20 % jitter.
    assert 100 <= int(limited.headers["retry-after"]) <= 120
    assert client.get("/v1/packs", headers=AUTH_B).status_code == 200  # autre clé, autre seau / own bucket


def test_unknown_routes_and_methods_use_json_errors(client: TestClient) -> None:
    missing = client.get("/jean.dupont@exemple.fr", headers=AUTH_A)
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "not_found"
    assert_secure(missing)
    wrong = client.put("/v1/packs", headers=AUTH_A)
    assert wrong.status_code == 405 and wrong.json()["error"]["code"] == "method_not_allowed"


def test_dev_mode_needs_no_key(make_client: Callable[..., TestClient]) -> None:
    client = make_client(dev_no_auth=True)
    assert client.post("/v1/anonymize/text", json={"text": f"mail {EMAIL}"}).json()["text"] == "mail [EMAIL_1]"


def test_lifespan_starts_then_stops_the_workers(fake_documents: None, monkeypatch: pytest.MonkeyPatch,
                                                caplog: pytest.LogCaptureFixture) -> None:
    from gdprguardian.server.service import Service

    calls: list[str] = []
    monkeypatch.setattr(Service, "start_workers", lambda self: calls.append("start"))
    monkeypatch.setattr(Service, "stop_workers", lambda self: calls.append("stop"))
    with TestClient(create_app(ServerConfig(api_keys=(KEY_A,), prewarm_workers=2))) as client:
        assert client.get("/health").status_code == 200
    assert calls == ["start", "stop"]

    def broken(self: Service) -> None:
        raise OSError("spawn refusé")

    monkeypatch.setattr(Service, "start_workers", broken)
    with TestClient(create_app(ServerConfig(api_keys=(KEY_A,), prewarm_workers=1))) as client:
        assert client.get("/health").status_code == 200  # au mieux, jamais bloquant / best effort, never fatal
    assert "event=prewarm_failed error=oserror" in caplog.text
    assert calls == ["start", "stop", "stop"]  # arrêt garanti même après un démarrage raté / stop always runs


def test_hsts_only_with_https_public_url(make_client: Callable[..., TestClient]) -> None:
    assert "strict-transport-security" not in make_client().get("/health").headers
    secure = make_client(public_url="https://rgpd.example.eu")
    assert "strict-transport-security" in secure.get("/health").headers
