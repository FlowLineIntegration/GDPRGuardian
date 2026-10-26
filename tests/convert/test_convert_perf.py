"""Vitesse de conversion (bornes larges, résultats affichés avec -s) / conversion speed (loose bounds, -s shows)."""

from __future__ import annotations

import time

import pytest
from convert_bench import DOCUMENTS

from gdprguardian.convert import shutdown_sandbox, to_markdown
from gdprguardian.documents import DocumentOptions

LOCAL = DocumentOptions(sandbox=False, max_bytes=200 << 20)
# Secondes au plus, très au-dessus des mesures, pour ne détecter que les régressions d'ordre de grandeur.
# Seconds at most, far above measurements, to catch only order-of-magnitude regressions.
BUDGETS = {"pdf": 3.0, "docx": 5.0, "pptx": 5.0, "html": 5.0, "rtf": 5.0, "odt": 3.0, "txt": 3.0}


@pytest.mark.slow
@pytest.mark.parametrize("kind", sorted(DOCUMENTS))
def test_conversion_speed(kind: str) -> None:
    data = DOCUMENTS[kind]()
    to_markdown(data, f"warm.{kind}", LOCAL)  # imports et caches / imports and caches
    started = time.perf_counter()
    result = to_markdown(data, f"doc.{kind}", LOCAL)
    elapsed = time.perf_counter() - started
    pages = f", {result.pages / elapsed:.0f} pages/s" if result.pages else ""
    print(f"\n{kind}: {len(data) / 1e6:.2f} Mo -> {len(result.markdown) / 1e6:.2f} M car. en {elapsed * 1000:.0f} ms "
          f"({len(result.markdown) / elapsed / 1e6:.1f} M car./s{pages})")
    assert elapsed < BUDGETS[kind]


@pytest.mark.slow
def test_sandbox_overhead_is_small() -> None:
    data = DOCUMENTS["pdf"](5)
    options = DocumentOptions(timeout_s=60)
    try:
        to_markdown(data, "a.pdf", options)  # démarrage du travailleur / worker start-up
        started = time.perf_counter()
        for _ in range(10):
            to_markdown(data, "a.pdf", options)
        isolated = (time.perf_counter() - started) / 10
    finally:
        shutdown_sandbox()
    started = time.perf_counter()
    for _ in range(10):
        to_markdown(data, "a.pdf", LOCAL)
    local = (time.perf_counter() - started) / 10
    print(f"\nbac à sable : {isolated * 1000:.1f} ms / en place : {local * 1000:.1f} ms par document")
    assert isolated - local < 0.25
