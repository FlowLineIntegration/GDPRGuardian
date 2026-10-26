"""Modèles figés, licences et outil de téléchargement (sans réseau) / pinned models, licences, download tool."""

from __future__ import annotations

import hashlib
import io
import json
import re
from pathlib import Path
from urllib.request import Request

import pytest

from gdprguardian.ner.registry import (
    DEFAULT_MODEL,
    ENV_MODELS_DIR,
    INT8_RECIPE,
    MANIFEST_NAME,
    MODELS,
    DerivedFile,
    ModelFile,
    ModelIntegrityError,
    ModelSpec,
    candidate_dirs,
    find_model_dir,
    verify_files,
)

ROOT = Path(__file__).resolve().parents[2]
HEX40 = re.compile(r"[0-9a-f]{40}")
HEX64 = re.compile(r"[0-9a-f]{64}")


def _spec(tmp_path: Path, payloads: dict[str, bytes], optional: tuple[str, ...] = (),
          derived: tuple[DerivedFile, ...] = ()) -> ModelSpec:
    files = tuple(ModelFile(name, "org/repo", "a" * 40, f"sub/{name}", len(data), hashlib.sha256(data).hexdigest(),
                            optional=name in optional) for name, data in payloads.items())
    return ModelSpec("fake-model", files, "MIT", derived)


class FakeOpener:
    """Remplace `urlopen` : sert des octets et note les URL / serves bytes and records URLs."""

    def __init__(self, payloads: dict[str, bytes]) -> None:
        self.payloads = payloads
        self.urls: list[str] = []

    def __call__(self, request, timeout: float) -> io.BytesIO:
        assert timeout > 0 and request.get_header("User-agent", "").startswith("gdprguardian")
        self.urls.append(request.full_url)
        return io.BytesIO(self.payloads[request.full_url.rsplit("/", 1)[1]])


# --- registre / registry


def test_registry_pins_are_well_formed():
    assert DEFAULT_MODEL in MODELS
    for spec in MODELS.values():
        names = {f.name for f in spec.required}
        assert {spec.model_file, spec.tokenizer_file, spec.config_file} <= names
        for file in spec.files:
            assert HEX40.fullmatch(file.revision) and HEX64.fullmatch(file.sha256) and file.size > 0
            assert file.url() == f"https://huggingface.co/{file.repo}/resolve/{file.revision}/{file.path}"


def test_quantized_variant_is_optional_and_not_default():
    spec = MODELS[DEFAULT_MODEL]
    quantized = spec.file("model_quantized.onnx")
    assert quantized is not None and quantized.optional
    assert spec.model_file == "model.onnx"


def test_model_licenses_file_matches_registry():
    yaml = pytest.importorskip("yaml")
    data = yaml.safe_load((ROOT / "models" / "MODEL_LICENSES.yaml").read_text(encoding="utf-8"))
    for name, spec in MODELS.items():
        entry = data["models"][name]
        for key in ("license", "source", "base_model", "training_data", "generator_llm", "files", "attribution"):
            assert entry.get(key) not in (None, "", []), f"{name}: {key}"
        assert entry["license"] == spec.license
        for dataset in entry["training_data"]:
            assert dataset["name"] and dataset["license"] and dataset["url"].startswith("https://")
        for file in spec.files:
            pinned = entry["files"][file.name]
            assert (pinned["repo"], pinned["revision"], pinned["sha256"]) == (file.repo, file.revision, file.sha256)
        for derived in spec.derived:
            built = entry["derived"][derived.name]
            assert (built["source"], built["recipe"]) == (derived.source, derived.recipe) and built["license"]


def test_candidate_dirs_honour_environment(tmp_path, monkeypatch):
    monkeypatch.setenv(ENV_MODELS_DIR, str(tmp_path))
    assert candidate_dirs()[0] == tmp_path / DEFAULT_MODEL
    spec = _spec(tmp_path, {"model.onnx": b"m", "tokenizer.json": b"t", "config.json": b"c"})
    assert find_model_dir(spec) is None
    directory = tmp_path / spec.name
    directory.mkdir()
    for file in spec.files:
        (directory / file.name).write_bytes(b"x")
    assert find_model_dir(spec) == directory


def test_verify_files_detects_tampering(tmp_path):
    payloads = {"model.onnx": b"weights", "config.json": b"{}"}
    spec = _spec(tmp_path, payloads)
    for name, data in payloads.items():
        (tmp_path / name).write_bytes(data)
    verify_files(tmp_path, spec, list(payloads))
    (tmp_path / "model.onnx").write_bytes(b"weightz")
    with pytest.raises(ModelIntegrityError, match="SHA-256"):
        verify_files(tmp_path, spec, ["model.onnx"])
    (tmp_path / "config.json").write_bytes(b"{} ")
    with pytest.raises(ModelIntegrityError, match=r"taille|size"):
        verify_files(tmp_path, spec, ["config.json"])
    with pytest.raises(ModelIntegrityError):
        verify_files(tmp_path, spec, ["unknown.bin"])


# --- outil de téléchargement / download tool


def test_download_verifies_and_writes_atomically(tool, tmp_path):
    payloads = {"model.onnx": b"0123456789" * 1000, "config.json": b'{"a": 1}', "extra.onnx": b"q"}
    spec = _spec(tmp_path, payloads, optional=("extra.onnx",))
    opener = FakeOpener(payloads)
    directory = tool.fetch_model(spec, tmp_path, opener=opener, log=lambda _: None)
    assert sorted(p.name for p in directory.iterdir()) == ["config.json", "manifest.json", "model.onnx"]
    assert all(url.startswith("https://huggingface.co/org/repo/resolve/" + "a" * 40) for url in opener.urls)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["model"] == "fake-model"
    assert manifest["files"]["model.onnx"]["sha256"] == hashlib.sha256(payloads["model.onnx"]).hexdigest()
    opener.urls.clear()
    tool.fetch_model(spec, tmp_path, opener=opener, log=lambda _: None)
    assert opener.urls == []  # déjà valides / already valid
    assert tool.verify_model(spec, tmp_path, log=lambda _: None)


def test_download_rejects_corrupted_or_oversized_payload(tool, tmp_path):
    good = {"model.onnx": b"expected bytes"}
    spec = _spec(tmp_path, good)
    for payload in (b"tampered bytes", b"expected bytes and more"):
        with pytest.raises(tool.IntegrityError):
            tool.fetch_model(spec, tmp_path, opener=FakeOpener({"model.onnx": payload}), log=lambda _: None)
        assert not any((tmp_path / spec.name).glob("model.onnx*"))


def test_download_requires_https(tool, tmp_path):
    spec = _spec(tmp_path, {"model.onnx": b"x"})
    with pytest.raises(ValueError):
        tool.download(spec.files[0], tmp_path / "model.onnx", endpoint="http://mirror.example")


def test_redirects_away_from_https_are_refused(tool):
    # urllib suivrait une redirection HTTPS -> HTTP ; l'outil la refuse / urllib would follow it, the tool refuses.
    handler = tool._HttpsOnlyRedirects()
    request = Request("https://huggingface.co/org/repo/resolve/abc/model.onnx")
    with pytest.raises(ValueError, match="HTTPS"):
        handler.redirect_request(request, io.BytesIO(), 302, "Found", {}, "http://cdn.example/model.onnx")
    followed = handler.redirect_request(request, io.BytesIO(), 302, "Found", {}, "https://cdn.example/model.onnx")
    assert followed is not None and followed.full_url == "https://cdn.example/model.onnx"


def test_verify_reports_missing_files(tool, tmp_path):
    spec = _spec(tmp_path, {"model.onnx": b"x", "q.onnx": b"y"}, optional=("q.onnx",))
    (tmp_path / spec.name).mkdir()
    assert not tool.verify_model(spec, tmp_path, log=lambda _: None)
    (tmp_path / spec.name / "model.onnx").write_bytes(b"x")
    assert tool.verify_model(spec, tmp_path, log=lambda _: None)


# --- fichiers dérivés (INT8 construit localement) / derived files (locally built INT8)

_DERIVED = DerivedFile("model_int8.onnx", "model.onnx", INT8_RECIPE)
_PAYLOADS = {"model.onnx": b"fp32 weights", "tokenizer.json": b"{}", "config.json": b"{}"}


def _fake_quantize(source: Path, target: Path) -> dict[str, str]:
    target.write_bytes(b"int8:" + source.read_bytes())
    return {"onnxruntime": "test"}


@pytest.fixture
def built(tool, tmp_path) -> tuple[ModelSpec, Path]:
    spec = _spec(tmp_path, _PAYLOADS, derived=(_DERIVED,))
    directory = tool.fetch_model(spec, tmp_path, opener=FakeOpener(_PAYLOADS), log=lambda _: None)
    tool.build_derived(spec, directory, quantize=_fake_quantize, check=lambda *_: (0.995, 0.99), log=lambda _: None)
    return spec, directory


def test_build_records_a_verifiable_chain_of_trust(tool, built):
    spec, directory = built
    entry = json.loads((directory / MANIFEST_NAME).read_text(encoding="utf-8"))["derived"]["model_int8.onnx"]
    assert entry["source_sha256"] == spec.file("model.onnx").sha256 and entry["recipe"] == INT8_RECIPE
    assert entry["sha256"] == hashlib.sha256(b"int8:fp32 weights").hexdigest() and entry["agreement"] == 0.995
    verify_files(directory, spec, ["model_int8.onnx", "tokenizer.json", "config.json"])
    assert tool.verify_model(spec, directory.parent, log=lambda _: None)
    # Un nouveau téléchargement conserve la construction / a new download keeps the build.
    tool.fetch_model(spec, directory.parent, opener=FakeOpener(_PAYLOADS), log=lambda _: None)
    verify_files(directory, spec, ["model_int8.onnx"])


def test_derived_file_tampering_is_detected(tool, built):
    spec, directory = built
    (directory / "model_int8.onnx").write_bytes(b"int8:fp32 weightz")
    with pytest.raises(ModelIntegrityError, match="SHA-256"):
        verify_files(directory, spec, ["model_int8.onnx"])
    assert not tool.verify_model(spec, directory.parent, log=lambda _: None)


@pytest.mark.parametrize("manifest", [{"derived": {"model_int8.onnx": {"source_sha256": "0" * 64}}},
                                      {"derived": ["not", "a", "mapping"]}, {"derived": {"model_int8.onnx": 3}}])
def test_derived_file_needs_a_matching_build_record(built, manifest):
    spec, directory = built
    (directory / MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ModelIntegrityError, match=r"construction|build"):
        verify_files(directory, spec, ["model_int8.onnx"])
    (directory / MANIFEST_NAME).write_text("{not json", encoding="utf-8")
    with pytest.raises(ModelIntegrityError):
        verify_files(directory, spec, ["model_int8.onnx"])


def test_build_rejects_a_model_too_far_from_fp32(tool, tmp_path):
    spec = _spec(tmp_path, _PAYLOADS, derived=(_DERIVED,))
    directory = tool.fetch_model(spec, tmp_path, opener=FakeOpener(_PAYLOADS), log=lambda _: None)
    for scores in ((0.62, 0.13), (0.99, 0.90)):
        with pytest.raises(tool.IntegrityError, match="fp32"):
            tool.build_derived(spec, directory, quantize=_fake_quantize, check=lambda *_, s=scores: s,
                               log=lambda _: None)
        assert not any(directory.glob("model_int8.onnx*"))


def test_build_requires_a_verified_source(tool, tmp_path):
    spec = _spec(tmp_path, _PAYLOADS, derived=(_DERIVED,))
    directory = tool.fetch_model(spec, tmp_path, opener=FakeOpener(_PAYLOADS), log=lambda _: None)
    (directory / "model.onnx").write_bytes(b"fp32 weightz")
    with pytest.raises(tool.IntegrityError, match="source"):
        tool.build_derived(spec, directory, quantize=_fake_quantize, check=lambda *_: (1.0, 1.0),
                           log=lambda _: None)


def test_int8_recipe_is_registered_for_the_default_model():
    derived = MODELS[DEFAULT_MODEL].derived_file("model_int8.onnx")
    assert derived is not None and derived.source == "model.onnx" and "QUInt8" in derived.recipe
