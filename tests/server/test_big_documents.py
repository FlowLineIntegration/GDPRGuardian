"""Gros documents : chaque couche admet le plus gros document publié et refuse tôt, limite nommée, ce qui dépasse.

Big documents: every layer admits the largest published document and refuses early, naming the limit, whatever goes
beyond. Nginx, service, limiteur, échéances, plafond de sortie, budget mémoire, poste de travail du site et textes
publiés (site, deploy/README.md, messages d'erreur) doivent dire et faire la même chose. Nginx, service, limiter,
deadlines, output cap, memory budget, the site's workspace and the published texts must say and do the same thing.
Les mesures de bout en bout (Nginx devant le service, 5, 20 et 50 Mo par format) sont dans deploy/README.md.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import replace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from server_testkit import AUTH_A, PUBLIC, REPO, FakeClock, from_ip

from gdprguardian.convert._base import MEMORY_MESSAGE, too_large
from gdprguardian.documents import DocumentOptions, DocumentTooLargeError
from gdprguardian.server import isolation
from gdprguardian.server.clients import ClientIdentifier, Pseudonymizer
from gdprguardian.server.config import MULTIPART_ENVELOPE_BYTES, ServerConfig
from gdprguardian.server.errors import (
    OUTPUT_TOO_LARGE,
    PayloadTooLarge,
    file_too_large,
    from_document_error,
    result_too_long,
    text_too_long,
)
from gdprguardian.server.isolation import deadline_s, document_reply_limit
from gdprguardian.server.limiter import FILE, Limiter
from gdprguardian.server.options import AnonymizeOptions
from gdprguardian.server.service import Service

DEPLOY = REPO / "deploy" / "server"
SITE = REPO / "site"
MB = 2**20
# Le plus lent des documents légitimes mesurés de bout en bout (Nginx, service public, réglages de compose.yaml,
# octobre 2026) : un HTML de tableaux de 16 Mio, juste sous le million de balises, en 30 s ; un PDF de 50 Mo et de
# 3 377 pages (11,7 M caractères) prend 9,4 s. Voir deploy/README.md. The slowest legitimate document measured end to
# end: a 16 MiB HTML of tables just under one million tags, 30 s; a 50 MB, 3,377-page PDF takes 9.4 s.
SLOWEST_DOCUMENT = (16 * MB, 30.0)
SLOWEST_MAXIMAL_DOCUMENT_S = 9.4
# Le pire Word sous ses limites, petit et lent : un tableau de 99 995 cellules (0,39 Mo), juste sous les 100 000
# paragraphes, de bout en bout : 25,6 s seul, 27,9 s à deux en même temps. The worst Word document under its limits,
# small and slow: a 99,995-cell table, just under 100,000 paragraphs, end to end: 25.6 s alone, 27.9 s two at once.
WORST_WORD_AT_LIMIT = (390_000, 28.0)


def compose_config() -> ServerConfig:
    yaml = pytest.importorskip("yaml")
    service = yaml.safe_load((DEPLOY / "compose.yaml").read_text(encoding="utf-8"))["services"]["gdprguardian"]
    # Service à clés : les empreintes viennent du fichier de réglages du serveur ; une empreinte factice ici.
    # Keyed service: the digests come from the server's settings file; a dummy digest here.
    env = {name: str(value) for name, value in service["environment"].items()}
    return ServerConfig.from_env(env | {"GDPRGUARDIAN_API_KEY_SHA256": "0" * 64})


def nginx_size(value: str) -> int:
    number, unit = re.fullmatch(r"(\d+)([kKmMgG]?)", value).groups()  # type: ignore[union-attr]
    return int(number) * {"": 1, "k": 2**10, "m": 2**20, "g": 2**30}[unit.lower()]


def nginx_seconds(value: str) -> int:
    number, unit = re.fullmatch(r"(\d+)(s|m)?", value).groups()  # type: ignore[union-attr]
    return int(number) * (60 if unit == "m" else 1)


# --- Nginx / Nginx -----------------------------------------------------------------------------------------------


def test_nginx_admits_the_largest_request_and_not_much_more() -> None:
    config = compose_config()
    sizes = [nginx_size(value) for value in re.findall(r"client_max_body_size (\w+);",
                                                       (DEPLOY / "nginx-site.conf").read_text(encoding="utf-8"))
             if value != "0" and nginx_size(value) > 64 * 2**10]
    assert len(sizes) == 2  # API et /v1/ des sites / API and the sites' /v1/
    for size in sizes:
        # Fichier maximal et son enveloppe multipart, à 1 Mio près : au-delà, 413 de Nginx sans rien transmettre.
        # The largest file and its multipart envelope, within 1 MiB: beyond, Nginx answers 413 without forwarding.
        assert config.max_upload_bytes + MULTIPART_ENVELOPE_BYTES <= size <= config.largest_request + MB


def test_nginx_waits_longer_than_a_maximal_job_queued_behind_another() -> None:
    config = compose_config()
    proxy = (DEPLOY / "nginx-service-proxy.conf").read_text(encoding="utf-8")
    read_timeout = nginx_seconds(re.search(r"^proxy_read_timeout (\w+);", proxy, re.M).group(1))  # type: ignore[union-attr]
    longest = deadline_s(config.conversion_timeout_s, config.max_upload_bytes)
    assert read_timeout >= 2 * longest  # un travail maximal devant, puis le sien / one maximal job ahead, then its own


def test_nginx_413_names_the_service_limit() -> None:
    config = compose_config()
    errors = (DEPLOY / "nginx-service-errors.conf").read_text(encoding="utf-8")
    body = re.search(r"return 413 '(.+)'", errors).group(1)  # type: ignore[union-attr]
    assert json.loads(body)["error"] == file_too_large(config.max_upload_bytes).to_dict()["error"]


# --- limiteur / limiter ------------------------------------------------------------------------------------------


def test_a_maximal_document_is_admitted_on_a_full_budget_then_waits_its_fair_share() -> None:
    config = compose_config()
    clock = FakeClock()
    service = Service(replace(config, isolation=False, prewarm_workers=0), clock=clock)
    policy = service.limits
    limiter = Limiter(policy, estimated_wait=lambda _p, _s: 0.0, typical_job_s=lambda: 1.0, clock=clock)
    identifier = ClientIdentifier("X-GG-Client", Pseudonymizer(clock=clock))
    client, _ = identifier.network([(b"x-gg-client", b"203.0.113.7")], None)
    largest = config.max_upload_bytes + MULTIPART_ENVELOPE_BYTES
    assert policy.estimate(FILE, largest) > policy.cost_burst  # plus cher que la rafale / dearer than the burst
    first = limiter.admit(client, cheap=False, content=FILE, size=largest)
    assert first.status == 0 and first.ticket is not None
    # Pire cas : le travail court jusqu'à son échéance / worst case: the job runs to its deadline.
    first.ticket.worked, first.ticket.measured = True, deadline_s(config.conversion_timeout_s, config.max_upload_bytes)
    limiter.finish(first.ticket)
    second = limiter.admit(client, cheap=False, content=FILE, size=largest)
    assert second.status == 429
    # Attente équitable : le temps de travailleur consommé, rendu à 0,5 s/s, aléa compris (20 %).
    # Fair wait: the worker time used, refilled at 0.5 s/s, jitter included (20%).
    assert second.retry_after <= first.ticket.measured / policy.cost_rate * (1 + policy.jitter) + 1
    clock.advance(second.retry_after)
    third = limiter.admit(client, cheap=False, content=FILE, size=largest)
    assert third.status == 0


def test_the_debt_covers_the_longest_job() -> None:
    config = compose_config()
    service = Service(replace(config, isolation=False, prewarm_workers=0))
    assert service.limits.cost_debt >= deadline_s(config.conversion_timeout_s, config.max_upload_bytes)


# --- échéances, plafond de sortie, mémoire / deadlines, output cap, memory ----------------------------------------


def test_deadlines_cover_the_size() -> None:
    config = compose_config()
    largest = config.max_upload_bytes + MULTIPART_ENVELOPE_BYTES
    # Corps : 15 s plus la taille au débit minimal (128 Kio/s) / body: 15 s plus the size at the minimal rate.
    assert config.body_deadline_s(largest) == pytest.approx(config.body_base_s + largest / config.body_min_rate)
    # Traitement : 60 s plus 1 s par 250 Ko, quatre fois au moins le plus lent mesuré à sa taille / processing: at
    # least four times the slowest measured document at its size.
    longest = deadline_s(config.conversion_timeout_s, config.max_upload_bytes)
    assert longest == pytest.approx(config.conversion_timeout_s + config.max_upload_bytes / 250_000)
    assert longest >= 4 * SLOWEST_MAXIMAL_DOCUMENT_S
    size, seconds = SLOWEST_DOCUMENT
    assert deadline_s(config.conversion_timeout_s, size) >= 4 * seconds
    # Un Word compressé au pire sous ses limites : deux fois au moins / a compressed Word at worst: twice at least.
    size, seconds = WORST_WORD_AT_LIMIT
    assert deadline_s(config.conversion_timeout_s, size) >= 2 * seconds


def test_the_word_limits_keep_the_worst_case_within_its_deadline() -> None:
    from gdprguardian.convert import _docx, _html

    # Mesuré dans un seul processus (voir convert/_docx.py) : 0,27 ms par cellule, 25 µs par élément au pire.
    # Measured in one process: 0.27 ms per cell, 25 µs per element at worst.
    worst_s = WORST_WORD_AT_LIMIT[1]
    assert worst_s >= _docx.MAX_PARAGRAPHS * 0.27e-3
    assert worst_s >= _docx.MAX_ELEMENTS * 25e-6
    assert _docx.MAX_ELEMENTS == _html.MAX_TAGS  # même nombre, même message pour la sortie de mammoth / same number


@pytest.mark.anyio
async def test_converters_get_the_request_deadline_and_the_page_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    config = ServerConfig(dev_no_auth=True, isolation=False)
    service = Service(config)
    seen: dict[str, Any] = {}

    async def capture(principal: str, payload: Any, spec: str, timeout_s: float, *_: Any, **__: Any) -> Any:
        seen.update(json.loads(spec), deadline=timeout_s)
        raise PayloadTooLarge  # arrêt ici : seule la spécification compte / stop here: only the spec matters

    monkeypatch.setattr(service, "_process", capture)
    size = 30 * MB
    with pytest.raises(PayloadTooLarge):
        await service.anonymize_document(b"x" * size, "rapport.pdf", AnonymizeOptions(), "dev")
    # Un gros classeur n'est plus coupé à 60 s quand la requête a droit à plus / a big workbook is not cut at 60 s.
    assert seen["timeout_s"] == seen["deadline"] == pytest.approx(deadline_s(config.conversion_timeout_s, size))
    assert seen["max_pages"] == config.max_pages == 10_000
    assert seen["max_chars"] == config.max_output_chars


@pytest.mark.anyio
async def test_the_scheduler_knows_each_job_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    # L'attente estimée borne un travail qui déborde de son estimation par son échéance / the estimated wait bounds an
    # overrunning job by its deadline.
    from contextlib import asynccontextmanager

    config = ServerConfig(dev_no_auth=True, isolation=False)
    service = Service(config)
    original = service.scheduler.slot
    seen: list[float | None] = []

    @asynccontextmanager
    async def spy(principal: str, ticket: Any = None, deadline: float | None = None) -> Any:
        seen.append(deadline)
        async with original(principal, ticket, deadline):
            yield

    monkeypatch.setattr(service.scheduler, "slot", spy)
    text = "Contrat de M. Jean Dupont, jean.dupont@exemple.fr."
    await service.anonymize_text(text, AnonymizeOptions(), "dev")
    assert seen == [pytest.approx(deadline_s(config.conversion_timeout_s, len(text.encode())))]


def test_the_output_cap_and_three_maximal_jobs_fit_the_queue_budget() -> None:
    config = compose_config()
    assert config.max_output_chars == 12_500_000
    largest = config.max_upload_bytes + MULTIPART_ENVELOPE_BYTES
    # Chaque place : le corps, puis deux fois la plus grande réponse (trame lue, texte et sa copie JSON).
    # Each slot: the body, then twice the largest reply (frame read, text and its JSON copy).
    per_job = largest + 2 * document_reply_limit(config.max_output_chars)
    assert config.max_concurrency * per_job <= config.queue_bytes


# --- moteur plafonné dans le travailleur / capped engine in the worker -------------------------------------------


class _Spy:
    """Moteur qui note ses appels / engine that records its calls."""

    def __init__(self) -> None:
        self.calls = 0
        self.engine = AnonymizeOptions().anonymizer()

    def anonymize(self, text: str) -> Any:
        self.calls += 1
        return self.engine.anonymize(text)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.engine, name)


@pytest.mark.parametrize(("chars", "engine_calls"), [(2_500, 0), (1_500, 1)])
def test_a_converted_text_that_cannot_fit_is_refused_before_the_engine(chars: int, engine_calls: int) -> None:
    spy = _Spy()
    data = ("Bonjour. " * (chars // 9 + 1))[:chars].encode()
    limits = DocumentOptions(sandbox=False)
    # Plafond 1 000 : 2 500 caractères convertis (plus du double) sont refusés avant le moteur ; 1 500, après.
    # Cap 1,000: 2,500 converted characters (over twice) are refused before the engine; 1,500, after it.
    with pytest.raises(DocumentTooLargeError, match="Résultat trop volumineux"):
        document, _ = isolation._anonymize_document(data, "document.txt", spy, limits, 1_000)
        isolation._check_output(document.markdown, 1_000)
    assert spy.calls == engine_calls


def test_the_capped_engine_changes_nothing_under_the_cap() -> None:
    from gdprguardian.documents import anonymize_document

    data = b"Contrat de M. Jean Dupont, NIR 1 85 05 78 006 084 91, jean.dupont@exemple.fr.\n" * 50
    limits = DocumentOptions(sandbox=False)
    engine = AnonymizeOptions().anonymizer()
    direct = anonymize_document(data, "document.txt", engine, limits)
    capped, score = isolation._anonymize_document(data, "document.txt", engine, limits, 1_000_000)
    assert capped.markdown == direct.markdown and capped.kind == direct.kind
    assert score is None  # qualité mesurée sur les seuls PDF / quality measured on PDFs only
    assert {key: value for key, value in capped.report.items() if key != "timings_ms"} == {
        key: value for key, value in direct.report.items() if key != "timings_ms"}


def test_the_quality_score_is_measured_for_pdfs_only() -> None:
    text = "Contrat de M. Jean Dupont, signé à Lyon le premier avril, pour la mission de conseil prévue.\n" * 20
    engine = AnonymizeOptions().anonymizer()
    pdf = isolation._CappedEngine(engine, None, collect=False, measure=True)
    other = isolation._CappedEngine(engine, None, collect=False)
    assert pdf.anonymize(text).text == other.anonymize(text).text
    assert pdf.quality is not None and pdf.quality < 0.12 and other.quality is None


# --- messages : la limite nommée / messages: the limit named ------------------------------------------------------


def test_limit_messages_name_the_published_numbers() -> None:
    config = compose_config()
    assert file_too_large(config.max_upload_bytes).message == ("Fichier trop volumineux : 50 Mo au plus / file too "
                                                               "large: 50 MB at most")
    assert text_too_long(config.max_text_chars).message == ("Texte trop long : 1 000 000 caractères au plus / text "
                                                            "too long: 1,000,000 characters at most")
    result = result_too_long(config.max_output_chars)
    assert result.code == "document_too_large" and result.status == 413
    assert result.message == ("Résultat trop long : 12 500 000 caractères au plus par document / result too long: "
                              "12,500,000 characters at most per document")


@pytest.mark.parametrize(("error", "expected"), [
    (too_large("pages", "pages", 10_000), "Document trop long : 10 000 pages au plus / document too long: 10,000 "
                                          "pages at most"),
    (too_large("diapositives", "slides", 10_000), "Présentation trop longue : 10 000 diapositives au plus / "
                                                  "presentation too long: 10,000 slides at most"),
    (too_large("balises HTML", "HTML tags", 1_000_000), "HTML trop complexe : 1 000 000 balises au plus, ouvrantes "
                                                        "et fermantes / HTML too complex: 1,000,000 tags at most, "
                                                        "opening and closing"),
    (too_large("niveaux d'imbrication HTML", "HTML nesting levels", 256), "HTML trop imbriqué : 256 niveaux au plus / "
                                                                          "HTML nested too deeply: 256 levels at most"),
    (too_large("paragraphes Word", "Word paragraphs", 100_000), "Document Word trop long : 100 000 paragraphes au "
                                                                "plus, cellules de tableau comprises / Word document "
                                                                "too long: 100,000 paragraphs at most, table cells "
                                                                "included"),
    (too_large("éléments Word", "Word elements", 1_000_000), "Document Word trop complexe : 1 000 000 éléments au plus "
                                                             "/ Word document too complex: 1,000,000 elements at most"),
    (too_large("fichier (octets)", "file (bytes)", 50 * MB), "Fichier trop volumineux : 50 Mo au plus / file too "
                                                             "large: 50 MB at most"),
    (DocumentTooLargeError(OUTPUT_TOO_LARGE), "Résultat trop long : 12 500 000 caractères au plus par document / "
                                              "result too long: 12,500,000 characters at most per document"),
    (DocumentTooLargeError(MEMORY_MESSAGE), MEMORY_MESSAGE),
    # Nature inconnue ou message libre : message générique, jamais repris / unknown kind or free text: generic.
    (DocumentTooLargeError("Document trop volumineux : x > 3 / document too large: Jean Dupont > 3"),
     "Document trop volumineux / document too large"),
    (DocumentTooLargeError("Jean Dupont, 06 12 34 56 78"), "Document trop volumineux / document too large"),
])
def test_too_large_reasons_come_from_closed_tables(error: DocumentTooLargeError, expected: str) -> None:
    translated = from_document_error(error, max_output_chars=12_500_000)
    assert translated.status == 413 and translated.message == expected


def test_rest_refusals_name_the_limit(make_client: Callable[..., TestClient]) -> None:
    client = make_client(**PUBLIC, max_upload_bytes=MB, max_text_chars=1_000)
    # Content-Length au-delà de la route : refus immédiat, limite nommée / over the route: refused at once, named.
    too_big = client.post("/v1/anonymize/file", headers=from_ip("203.0.113.7"), content=b"x" * (2 * MB))
    assert too_big.status_code == 413
    assert too_big.json()["error"]["message"] == "Fichier trop volumineux : 1 Mo au plus / file too large: 1 MB at most"
    text = client.post("/v1/anonymize/text", headers=from_ip("203.0.113.8"), json={"text": "a" * 1_001})
    assert text.status_code == 413 and text.json()["error"]["message"].startswith("Texte trop long : 1 000 caractères")
    files = {"file": ("big.txt", b"x" * (MB + 1), "text/plain")}
    multipart = client.post("/v1/anonymize/file", headers=from_ip("203.0.113.9"), files=files)
    assert multipart.status_code == 413 and "1 Mo au plus" in multipart.json()["error"]["message"]


def _pdf(pages: int) -> bytes:
    """PDF minimal, une ligne de texte par page / minimal PDF, one line of text per page."""
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"",
               b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    kids = []
    for index in range(pages):
        content = b"BT /F1 12 Tf 72 720 Td (Page %d) Tj ET" % (index + 1)
        objects.append(b"<< /Length %d >>\nstream\n%s\nendstream" % (len(content), content))
        objects.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents %d 0 R "
                       b"/Resources << /Font << /F1 3 0 R >> >> >>" % len(objects))
        kids.append(len(objects))
    objects[1] = b"<< /Type /Pages /Kids [%s] /Count %d >>" % (b" ".join(b"%d 0 R" % k for k in kids), pages)
    out, offsets = bytearray(b"%PDF-1.7\n"), []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n%s\nendobj\n" % (number, body)
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
    return bytes(out)


def test_the_service_page_limit_applies_and_is_named() -> None:
    from gdprguardian.server import create_app

    app = create_app(ServerConfig(dev_no_auth=True, isolation=False, max_pages=5))
    with TestClient(app) as client:
        fits = client.post("/v1/anonymize/file", files={"file": ("a.pdf", _pdf(5), "application/pdf")})
        assert fits.status_code == 200 and fits.json()["pages"] == 5
        over = client.post("/v1/anonymize/file", files={"file": ("a.pdf", _pdf(6), "application/pdf")})
    assert over.status_code == 413 and over.json()["error"] == {
        "code": "document_too_large", "message": "Document trop long : 5 pages au plus / document too long: 5 pages "
                                                 "at most"}


def test_an_oversized_put_is_refused_unread_and_reported(make_client: Callable[..., TestClient]) -> None:
    client = make_client(max_upload_bytes=1024)
    ticket = client.post("/v1/uploads", headers=AUTH_A, json={"filename": "a.txt"}).json()
    path = ticket["upload_url"].split("://", 1)[1].partition("/")[2]
    # Taille annoncée au-delà de la limite (sous la marge de l'intergiciel) : refus avant toute lecture du corps.
    # Declared size over the limit (under the middleware's margin): refused before any body byte is read.
    response = client.put(f"/{path}", headers=AUTH_A, content=b"x" * 2048)
    assert response.status_code == 413
    assert response.json()["error"]["message"] == ("Fichier trop volumineux : 1 024 octets au plus / file too large: "
                                                   "1,024 bytes at most")
    failed = client.get("/" + ticket["result_url"].split("://", 1)[1].partition("/")[2], headers=AUTH_A)
    assert failed.status_code == 413 and failed.json()["error"]["code"] == "payload_too_large"


# --- poste de travail du site et textes publiés / site workspace and published texts ------------------------------


def _cockpit() -> str:
    return (SITE / "static" / "cockpit.js").read_text(encoding="utf-8")


def test_workspace_checks_the_service_limits_before_sending() -> None:
    config = ServerConfig(dev_no_auth=True)
    script = _cockpit()
    size, unit = re.search(r"it\.size > (\d+) \* (\d+)", script).groups()  # type: ignore[union-attr]
    assert int(size) * int(unit) == config.max_upload_bytes
    chars = re.search(r"\.length > ([0-9e.]+)\) fail\(it, 413", script).group(1)  # type: ignore[union-attr]
    assert float(chars) == config.max_text_chars


def test_workspace_waits_as_long_as_the_service_may_take() -> None:
    config = ServerConfig(dev_no_auth=True)
    match = re.search(r"x\.timeout = \((\d+) \+ it\.size \* \(1 / (\d+) \+ 2 / ([0-9e.]+)\)\) \* 1e3;", _cockpit())
    assert match is not None
    base, rate, per_second = (float(group) for group in match.groups())
    # Corps au débit minimal, puis deux échéances (un travail maximal devant, puis le sien), 30 s de marge.
    # Body at the minimal rate, then two deadlines (one maximal job ahead, then its own), 30 s margin.
    assert base == config.body_base_s + 2 * config.conversion_timeout_s + 30
    assert rate == config.body_min_rate and per_second == 250_000 == isolation._BYTES_PER_EXTRA_SECOND
    size = config.max_upload_bytes
    workspace_s = base + size * (1 / rate + 2 / per_second)
    assert workspace_s >= config.body_deadline_s(size) + 2 * deadline_s(config.conversion_timeout_s, size)


def test_workspace_shows_upload_progress_and_the_service_message_on_413() -> None:
    script = _cockpit()
    assert "x.upload.onprogress" in script and 't("up"' in script
    assert re.search(r"if \(s === 413\) b = half\(e\.message\);", script)
    # « en cours · N s » compte depuis la fin de l'envoi / "running · N s" counts from the end of the upload.
    assert "it.t1 = Date.now()" in script and "(it.t1 || it.t0)" in script
    for lang, entry in (("fr", '<li data-k="up">envoi {p} %</li>'), ("en", '<li data-k="up">uploading {p}%</li>')):
        assert entry in (SITE / "templates" / f"index.{lang}.html").read_text(encoding="utf-8")


def test_workspace_timeout_advice_fits_the_item() -> None:
    # Un court élément sans réponse à temps : le service est saturé, le découper n'y changerait rien ; la version
    # locale n'est plus conseillée (même limite de fichier, 500 pages et 60 s). A short item with no answer in time:
    # the service is busy, splitting it would not help; the local version is no longer advised.
    assert re.search(r'k = it\.size > 1048576 \? "eTime" : "eTimeS";', _cockpit())
    for lang in ("fr", "en"):
        page = (SITE / "templates" / f"index.{lang}.html").read_text(encoding="utf-8")
        entries = dict(re.findall(r'<li data-k="(e413|eTime|eTimeS)">([^<]+)</li>', page))
        assert set(entries) == {"e413", "eTime", "eTimeS"}
        assert not any("locale" in text or "local version" in text for text in entries.values())
        assert ("satur" if lang == "fr" else "overloaded") in entries["eTimeS"]


PUBLISHED = {
    "fr": ("50 Mo par fichier", "un million de caractères par texte", "12,5 millions de caractères de résultat",
           "10 000 pages ou diapositives", "un million de balises HTML (ouvrantes et fermantes)",
           "100 000 paragraphes Word (cellules de tableau comprises)"),
    "en": ("50 MB per file", "one million characters per text", "12.5 million characters of result",
           "10,000 pages or slides", "one million HTML tags (opening and closing)",
           "100,000 Word paragraphs (table cells included)"),
}


def _spaced(text: str) -> str:
    """Espaces insécables (typographie) ramenées à l'espace simple / no-break spaces turned into plain spaces."""
    return text.replace("&nbsp;", " ").replace(" ", " ").replace(" ", " ")


@pytest.mark.parametrize("lang", ["fr", "en"])
def test_the_site_states_the_limits(lang: str) -> None:
    page = _spaced((SITE / "templates" / f"index.{lang}.html").read_text(encoding="utf-8"))
    for wording in PUBLISHED[lang]:
        assert wording in page, wording


def test_deploy_readme_states_the_same_limits() -> None:
    readme = _spaced((REPO / "deploy" / "README.md").read_text(encoding="utf-8"))
    french, english = readme.split("\n## English\n", 1)
    for lang, text in (("fr", french), ("en", english)):
        for wording in PUBLISHED[lang]:
            assert wording in text, (lang, wording)


def test_mcp_upload_tool_states_the_file_limit() -> None:
    pytest.importorskip("fastmcp")
    from gdprguardian.server.mcp_online import CREATE_UPLOAD_PUBLIC_DESCRIPTION

    assert "{max_mb} MB max" in CREATE_UPLOAD_PUBLIC_DESCRIPTION
    assert ServerConfig(dev_no_auth=True).max_upload_bytes // MB == 50


def test_the_page_limit_is_configurable_and_positive() -> None:
    assert ServerConfig.from_env({"GDPRGUARDIAN_PUBLIC": "1", "GDPRGUARDIAN_MAX_PAGES": "1200"}).max_pages == 1200
    with pytest.raises(ValueError):
        ServerConfig(dev_no_auth=True, max_pages=0).validate()
