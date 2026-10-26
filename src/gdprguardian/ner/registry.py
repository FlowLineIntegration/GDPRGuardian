"""Modèles NER épinglés (commit Hugging Face + SHA-256) et emplacements locaux.

Pinned NER models (Hugging Face commit + SHA-256) and local locations. Aucune dépendance / no dependency.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

HF_ENDPOINT = "https://huggingface.co"
ENV_MODELS_DIR = "GDPRGUARDIAN_MODELS_DIR"
MANIFEST_NAME = "manifest.json"


class ModelIntegrityError(RuntimeError):
    """Fichier de modèle absent, tronqué ou modifié / missing, truncated or altered model file."""


@dataclass(frozen=True, slots=True)
class ModelFile:
    """Fichier distant figé par révision et empreinte / remote file pinned by revision and digest."""

    name: str
    repo: str
    revision: str
    path: str
    size: int
    sha256: str
    optional: bool = False

    def url(self, endpoint: str = HF_ENDPOINT) -> str:
        return f"{endpoint.rstrip('/')}/{self.repo}/resolve/{self.revision}/{self.path}"


@dataclass(frozen=True, slots=True)
class DerivedFile:
    """Fichier construit localement depuis un fichier figé, jamais téléchargé / built locally from a pinned file.

    Sa confiance repose sur le manifeste écrit à la construction : empreinte du résultat et empreinte de la
    source, qui doit être celle figée ici. Trust comes from the manifest written at build time: digest of the
    result and of its source, which must equal the pinned one.
    """

    name: str
    source: str
    recipe: str


@dataclass(frozen=True, slots=True)
class ModelSpec:
    """Modèle de classification de jetons au format ONNX / ONNX token-classification model."""

    name: str
    files: tuple[ModelFile, ...]
    license: str
    derived: tuple[DerivedFile, ...] = ()
    model_file: str = "model.onnx"
    tokenizer_file: str = "tokenizer.json"
    config_file: str = "config.json"

    def file(self, name: str) -> ModelFile | None:
        return next((f for f in self.files if f.name == name), None)

    def derived_file(self, name: str) -> DerivedFile | None:
        return next((f for f in self.derived if f.name == name), None)

    @property
    def required(self) -> tuple[ModelFile, ...]:
        return tuple(f for f in self.files if not f.optional)


_CMARKEA = "cmarkea/distilcamembert-base-ner"
_CMARKEA_REV = "e539d952f70088b450c300c28ba455da87f2dc4b"
# Le dépôt cmarkea n'a pas de tokenizer.json : celui de CamemBERT (même sentencepiece) / same sentencepiece model.
_ALMANACH = "almanach/camembert-base"
_ALMANACH_REV = "a75967561c78f2aa81cc41045378d3b4ee25af9e"
# Poids INT8 par canal, non signés : évite la saturation u8s8 sans VNNI et les valeurs aberrantes d'une échelle
# par tenseur (mesuré : rappel du fp32, 1,8x plus rapide). Per-channel unsigned INT8 weights: avoids u8s8
# saturation on CPUs without VNNI and per-tensor outliers (measured: fp32 recall, 1.8x faster).
INT8_RECIPE = "onnxruntime.quantization.quantize_dynamic(op_types=[MatMul], per_channel=True, weight_type=QUInt8)"

DISTILCAMEMBERT_NER = ModelSpec(
    name="distilcamembert-base-ner",
    license="MIT",
    files=(
        ModelFile("model.onnx", _CMARKEA, _CMARKEA_REV, "model.onnx", 270_089_674,
                  "666ce15c968ca49874d2449aa9b83164dbb1126090d012dda7c35b2ef3672e1d"),
        ModelFile("config.json", _CMARKEA, _CMARKEA_REV, "config.json", 945,
                  "103f36a11079994f128a20c46cb388912dc9d481fded4ce12fbfe2d9f63d2662"),
        ModelFile("tokenizer.json", _ALMANACH, _ALMANACH_REV, "tokenizer.json", 1_395_301,
                  "94e041bf917a884207001cc0758f393b2cdcc4a6d24fdc8b2339a83dd47c9218"),
        # INT8 dynamique fourni par l'auteur : rappel effondré, évaluation seulement / shipped dynamic INT8:
        # collapsed recall, for evaluation only (see models/README.md).
        ModelFile("model_quantized.onnx", _CMARKEA, _CMARKEA_REV, "model_quantized.onnx", 142_727_986,
                  "770067d0fef15f0bee29bfcc04509f6e63e0451b15c958d6b3472ad4a845fd96", optional=True),
    ),
    derived=(DerivedFile("model_int8.onnx", "model.onnx", INT8_RECIPE),),
)

MODELS: dict[str, ModelSpec] = {DISTILCAMEMBERT_NER.name: DISTILCAMEMBERT_NER}
DEFAULT_MODEL = DISTILCAMEMBERT_NER.name


def _source_checkout_cache() -> Path | None:
    """`models/cache` d'un dépôt cloné (installation éditable) / repository cache in a source checkout."""
    root = Path(__file__).resolve().parents[3]
    return root / "models" / "cache" if (root / "pyproject.toml").is_file() else None


def _user_cache() -> Path:
    base = os.environ.get("LOCALAPPDATA") if os.name == "nt" else os.environ.get("XDG_CACHE_HOME")
    return Path(base) if base else Path.home() / ".cache"


def candidate_dirs(name: str = DEFAULT_MODEL) -> list[Path]:
    """Ordre de recherche : $GDPRGUARDIAN_MODELS_DIR, dépôt source, cache utilisateur / search order."""
    roots: list[Path] = []
    env = os.environ.get(ENV_MODELS_DIR)
    if env:
        roots.append(Path(env))
    checkout = _source_checkout_cache()
    if checkout is not None:
        roots.append(checkout)
    roots.append(_user_cache() / "gdprguardian" / "models")
    return [root / name for root in roots]


def model_files(spec: ModelSpec | None, model_file: str | None = None) -> tuple[str, str, str]:
    """(modèle ONNX, tokenizer, configuration) ; noms usuels sans spécification / usual names without a spec."""
    if spec is None:
        return model_file or "model.onnx", "tokenizer.json", "config.json"
    return model_file or spec.model_file, spec.tokenizer_file, spec.config_file


def has_files(directory: Path, names: Sequence[str]) -> bool:
    return all((directory / name).is_file() for name in names)


def find_model_dir(spec: ModelSpec | str = DEFAULT_MODEL, model_file: str | None = None) -> Path | None:
    """Premier dossier contenant les fichiers requis, sinon None / first folder holding the required files."""
    spec = MODELS[spec] if isinstance(spec, str) else spec
    needed = model_files(spec, model_file)
    return next((d for d in candidate_dirs(spec.name) if has_files(d, needed)), None)


def sha256_file(path: Path) -> str:
    with open(path, "rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def read_manifest(directory: Path) -> dict[str, Any]:
    try:
        data = json.loads((directory / MANIFEST_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _check(path: Path, size: object, sha256: object) -> None:
    if not path.is_file() or path.stat().st_size != size:
        raise ModelIntegrityError(f"{path.name}: taille inattendue / unexpected size")
    if sha256_file(path) != sha256:
        raise ModelIntegrityError(f"{path.name}: SHA-256 inattendu / unexpected SHA-256")


def _build_record(manifest: dict[str, Any], spec: ModelSpec, derived: DerivedFile) -> dict[str, Any] | None:
    """Entrée du manifeste d'une construction conforme à la recette et à la source figée / matching build record."""
    entries = manifest.get("derived")
    entry = entries.get(derived.name) if isinstance(entries, dict) else None
    source = spec.file(derived.source)
    if not isinstance(entry, dict) or source is None:
        return None
    if entry.get("source_sha256") != source.sha256 or entry.get("recipe") != derived.recipe:
        return None
    return entry


def built_here(directory: Path, spec: ModelSpec, name: str) -> bool:
    """Le fichier dérivé est-il présent et inscrit au manifeste (sans le hacher) / present and recorded?"""
    derived = spec.derived_file(name)
    return (derived is not None and (directory / name).is_file()
            and _build_record(read_manifest(directory), spec, derived) is not None)


def verify_files(directory: Path, spec: ModelSpec, names: Sequence[str]) -> None:
    """Contrôle taille et SHA-256 : valeurs figées dans le code, ou manifeste de construction pour un fichier
    dérivé dont la source doit être le fichier figé. Size and SHA-256 against pinned values, or against the build
    manifest for a derived file whose recorded source must be the pinned file.
    """
    manifest: dict[str, Any] | None = None
    for name in names:
        pinned = spec.file(name)
        if pinned is not None:
            _check(directory / name, pinned.size, pinned.sha256)
            continue
        derived = spec.derived_file(name)
        if derived is None:
            raise ModelIntegrityError(f"{name}: absent du registre / not in the registry ({spec.name})")
        manifest = read_manifest(directory) if manifest is None else manifest
        entry = _build_record(manifest, spec, derived)
        if entry is None:
            raise ModelIntegrityError(f"{name}: construction inconnue / unknown build "
                                      "(python tools/download_models.py --build-int8)")
        _check(directory / name, entry.get("size"), entry.get("sha256"))
