"""NER local et optionnel (ONNX Runtime + tokenizers, sans torch ni réseau) / optional local NER.

    from gdprguardian import Anonymizer, Settings
    from gdprguardian.ner import load_detector

    ner = load_detector()            # None si le modèle ou l'extra [ner] manque / None if unavailable
    anonymizer = Anonymizer(Settings(detectors=[ner] if ner else []))

Modèle : `python tools/download_models.py` (révision et SHA-256 figés) / model: pinned revision and SHA-256.
L'import de ce paquet ne charge ni numpy ni onnxruntime / importing this package loads neither.
"""

from __future__ import annotations

import importlib
import logging
import os
from importlib.util import find_spec
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .registry import (
    DEFAULT_MODEL,
    DISTILCAMEMBERT_NER,
    MODELS,
    ModelIntegrityError,
    ModelSpec,
    built_here,
    candidate_dirs,
    find_model_dir,
    has_files,
    model_files,
)

if TYPE_CHECKING:
    from .detector import NerDetector
    from .runtime import TokenClassifier

logger = logging.getLogger(__name__)

_RUNTIME_MODULES = ("numpy", "onnxruntime", "tokenizers")
_LAZY = {"NerDetector": ".detector", "TokenClassifier": ".runtime"}


def runtime_available() -> bool:
    """L'extra `gdprguardian[ner]` est-il installé ? / is the `gdprguardian[ner]` extra installed?"""
    return all(find_spec(name) is not None for name in _RUNTIME_MODULES)


def load_detector(model_dir: str | os.PathLike[str] | None = None, **options: Any) -> NerDetector | None:
    """Détecteur prêt à l'emploi, ou None si l'extra ou les fichiers du modèle manquent ; ne lève pas.

    Ready-to-use detector, or None when the extra or the model files are missing; does not raise for that.
    Les dossiers sont parcourus dans l'ordre de `candidate_dirs` ; dans chacun, sans `model_file`, l'INT8 local
    (`--build-int8`, contrôlé contre le fp32 et inscrit au manifeste) est préféré au fp32. Folders are searched in
    `candidate_dirs` order; within each, without `model_file`, the checked and recorded local INT8 wins over fp32.
    Les options sont celles de `NerDetector` (threads, max_tokens, thresholds, entities, gating…).
    Le modèle est vérifié (SHA-256) puis chargé au premier appel / verified then loaded on first use.
    """
    if not runtime_available():
        logger.info("NER indisponible : extra [ner] absent / NER unavailable: [ner] extra not installed")
        return None
    spec: ModelSpec | None = options.get("spec", DISTILCAMEMBERT_NER)
    requested = options.get("model_file")
    if requested is not None or spec is None:
        choices: tuple[str | None, ...] = (requested,)
    else:
        choices = (*(d.name for d in spec.derived), spec.model_file)
    if model_dir is not None:
        directories = [Path(model_dir)]
    elif spec is not None:
        directories = candidate_dirs(spec.name)
    else:
        directories = []
    for directory in directories:
        for model_file in choices:
            needed = model_files(spec, model_file)
            if not has_files(directory, needed):
                continue
            # Choix implicite : seulement une construction inscrite au manifeste / implicit choice: recorded only.
            if requested is None and spec is not None and spec.derived_file(needed[0]) is not None \
                    and not built_here(directory, spec, needed[0]):
                logger.warning("modèle dérivé non inscrit au manifeste : ignoré / unrecorded derived model: skipped")
                continue
            from .detector import NerDetector

            return NerDetector(directory, **{**options, "model_file": needed[0]})
    logger.info("NER indisponible : modèle absent (tools/download_models.py) / NER model not downloaded")
    return None


def __getattr__(name: str) -> Any:
    module = _LAZY.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(importlib.import_module(module, __name__), name)


__all__ = [
    "DEFAULT_MODEL",
    "DISTILCAMEMBERT_NER",
    "MODELS",
    "ModelIntegrityError",
    "ModelSpec",
    "NerDetector",
    "TokenClassifier",
    "candidate_dirs",
    "find_model_dir",
    "load_detector",
    "runtime_available",
]
