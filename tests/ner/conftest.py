"""Fixtures NER : corpus annoté, fausse session ONNX, modèle réel s'il est téléchargé.

NER fixtures: annotated corpus, fake ONNX session, real model when downloaded.
"""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Callable, Mapping
from importlib.util import find_spec
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from _ner_corpus import Sample, load_corpus

from gdprguardian.ner import load_detector

HAS_RUNTIME = all(find_spec(m) is not None for m in ("numpy", "tokenizers"))
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def tool() -> ModuleType:
    """tools/download_models.py chargé comme module / the download tool loaded as a module."""
    spec = importlib.util.spec_from_file_location("download_models", ROOT / "tools" / "download_models.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def fake_session() -> Any:
    if not HAS_RUNTIME:
        pytest.skip("extra [ner] absent / [ner] extra not installed")
    from _ner_fakes import FakeSession

    return FakeSession()


@pytest.fixture
def make_detector(fake_session: Any) -> Callable[..., Any]:
    """Fabrique de détecteurs branchés sur une fausse session / detector factory over a fake session."""
    from _ner_fakes import IO_LABELS, make_classifier

    from gdprguardian.ner import NerDetector

    def factory(session: Any = None, labels: Mapping[int, str] = IO_LABELS, **options: Any) -> NerDetector:
        return NerDetector(classifier=make_classifier(session or fake_session, labels), spec=None, **options)

    return factory


@pytest.fixture(scope="session")
def corpus() -> list[Sample]:
    return load_corpus()


def _real(model_file: str, hint: str) -> Any:
    if not HAS_RUNTIME:
        pytest.skip("extra [ner] absent / [ner] extra not installed")
    detector = load_detector(model_file=model_file)
    if detector is None:
        pytest.skip(f"{model_file} absent ({hint})")
    return detector


@pytest.fixture(scope="session")
def real_detector() -> Any:
    """Modèle fp32 figé / pinned fp32 model."""
    return _real("model.onnx", "python tools/download_models.py")


@pytest.fixture(scope="session")
def int8_detector() -> Any:
    """INT8 construit localement / locally built INT8."""
    return _real("model_int8.onnx", "python tools/download_models.py --build-int8")
