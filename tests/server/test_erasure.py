"""Effacement et isolation : ce qui ne doit survivre ni à la requête ni d'un client à l'autre.

Erasure and isolation: what must survive neither the request nor from one client to another.
"""

from __future__ import annotations

import gc

from server_testkit import AUTH_A, NIR

from gdprguardian import Anonymizer
from gdprguardian.detectors import intl
from gdprguardian.server.errors import InvalidRequest
from gdprguardian.server.options import AnonymizeOptions
from gdprguardian.server.store import JobStore


def test_reports_never_carry_internal_timings(client) -> None:
    # Processus partagé : les durées trahiraient l'activité des autres clients / timings would leak activity.
    response = client.post("/v1/anonymize/text", json={"text": f"NIR {NIR}"}, headers=AUTH_A)
    assert response.status_code == 200 and "timings_ms" not in response.json()["report"]
    detect = client.post("/v1/detect", json={"text": f"NIR {NIR}"}, headers=AUTH_A)
    assert "timings_ms" not in detect.json()["report"]


def test_phone_validation_keeps_no_shared_cache() -> None:
    # Aucun cache de module : un numéro vu pour un client n'existe plus ensuite / no module-level cache.
    assert not hasattr(intl._e164, "cache_info")
    Anonymizer(countries="FR").anonymize("Appelez le +41 79 123 45 67.")
    gc.collect()
    assert not any(isinstance(o, dict) and "+41 79 123 45 67" in o for o in gc.get_objects())


def test_a_failed_job_keeps_no_trace_of_the_document() -> None:
    store = JobStore(upload_ttl_s=60, result_ttl_s=60, processing_ttl_s=60, max_active_per_principal=4,
                     max_jobs=16, max_chars=10_000)
    job, token = store.create("alice", "document.pdf", AnonymizeOptions())
    store.claim(token, "alice")
    try:
        document = b"NIR " + NIR.encode()
        raise InvalidRequest("Document refusé / rejected", code="rejected") from ValueError(document)
    except InvalidRequest as error:
        store.fail(job, error)
    # Copie neuve jamais levée : ni pile d'appels ni cause, donc aucune référence au document.
    # Fresh, never-raised copy: no traceback nor cause, hence no reference to the document.
    assert job.error is not None and job.error.__traceback__ is None
    assert job.error.__cause__ is None and job.error.__context__ is None


def test_mcp_transport_does_not_cache_strings(client) -> None:
    import mcp.server.streamable_http as transport

    parser = transport.pydantic_core.from_json
    assert getattr(parser, "keywords", {}).get("cache_strings") is False
