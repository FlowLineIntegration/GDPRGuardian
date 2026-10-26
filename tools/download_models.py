"""Télécharge les modèles NER figés (commit + SHA-256) dans models/cache/<nom>/.

Downloads the pinned NER models (commit + SHA-256) into models/cache/<name>/. Seul outil autorisé à
utiliser le réseau ; la bibliothèque n'y accède jamais / the only networked tool, the library never is.

    python tools/download_models.py                    # modèle par défaut / default model
    python tools/download_models.py --build-int8       # + model_int8.onnx construit et contrôlé localement
    python tools/download_models.py --with-quantized   # + model_quantized.onnx (évaluation seulement)
    python tools/download_models.py --verify           # revérifie les empreintes, sans réseau / offline check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import IO, Any
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
try:
    from gdprguardian.ner import registry
except ImportError:  # dépôt non installé / checkout not installed
    sys.path.insert(0, str(ROOT / "src"))
    from gdprguardian.ner import registry

USER_AGENT = "gdprguardian-download-models/1"
CHUNK = 1 << 20
# Contrôle de la construction INT8 : accord des étiquettes avec le fp32 / INT8 build check: label agreement.
MIN_AGREEMENT = 0.98
MIN_ENTITY_AGREEMENT = 0.95
CHECK_SENTENCES = (
    "Bonjour Claire Vasseur, je vous confirme le rendez-vous avec Thomas Lemoine à Grenoble.",
    "Le salarié Mathieu Carpentier a été embauché par Valmont Industries le 2 mai.",
    "Le docteur Rachid Mansouri adresse sa patiente au professeur Hélène Brunet, du CHU de Bordeaux.",
    "Maître Florence Chevalier, avocate au barreau de Lyon, représente la société Altéa Conseil.",
    "La commande a été passée par Aurélie Brun pour le compte du Groupe Delmas à Marseille.",
    "Le maire de Saint-Malo, Jean-Luc Prigent, a signé l'arrêté transmis à la préfecture.",
    "DUPONT Jean, né le 3 mars 1985 à Saint-Étienne, demeurant à Aix-en-Provence.",
    "Airbus a annoncé un contrat avec Air France, selon Bruno Clément de BNP Paribas.",
    "Hervé Le Bihan et Gwenaëlle Le Roux sont originaires de Lorient, en Bretagne.",
    "Charles-Édouard de La Rochefoucauld a présidé la séance du conseil d'administration.",
    "Mme Nguyen signale une allergie ; elle est suivie par l'hôpital Pasteur de Nice.",
    "Le contrat est conclu pour une durée indéterminée et prend effet à sa signature.",
)
Opener = Callable[..., Any]
Log = Callable[[str], None]


class IntegrityError(RuntimeError):
    """Taille, empreinte ou contrôle de qualité inattendus / unexpected size, digest or quality check."""


class _HttpsOnlyRedirects(HTTPRedirectHandler):
    """Refuse toute redirection hors HTTPS (urllib l'accepterait) / refuses redirects away from HTTPS."""

    def redirect_request(self, req: Request, fp: IO[bytes], code: int, msg: str, headers: Any,
                         newurl: str) -> Request | None:
        if not newurl.lower().startswith("https://"):
            raise ValueError("redirection hors HTTPS refusée / non-HTTPS redirect refused")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


https_open: Opener = build_opener(_HttpsOnlyRedirects).open


def is_valid(path: Path, expected: registry.ModelFile) -> bool:
    return path.is_file() and path.stat().st_size == expected.size and registry.sha256_file(path) == expected.sha256


def _copy_verified(source: IO[bytes], out: IO[bytes], expected: registry.ModelFile, log: Log) -> None:
    digest = hashlib.sha256()
    size = 0
    step = max(expected.size // 10, CHUNK)
    next_report = step
    while chunk := source.read(CHUNK):
        size += len(chunk)
        if size > expected.size:
            raise IntegrityError(f"{expected.name}: plus gros que prévu / larger than expected")
        digest.update(chunk)
        out.write(chunk)
        if size >= next_report:
            log(f"  {expected.name}: {size * 100 // expected.size} %")
            next_report += step
    if size != expected.size:
        raise IntegrityError(f"{expected.name}: taille {size} != {expected.size} / size mismatch")
    if digest.hexdigest() != expected.sha256:
        raise IntegrityError(f"{expected.name}: SHA-256 inattendu / unexpected SHA-256")


def download(expected: registry.ModelFile, target: Path, endpoint: str = registry.HF_ENDPOINT,
             opener: Opener = https_open, log: Log = print) -> None:
    """Télécharge vers un `.part`, vérifie, puis renomme (atomique) / download, verify, then atomic rename."""
    url = expected.url(endpoint)
    if not url.startswith("https://"):
        raise ValueError("HTTPS obligatoire / HTTPS required")
    part = target.with_name(target.name + ".part")
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with opener(request, timeout=60) as response, open(part, "wb") as out:
            _copy_verified(response, out, expected, log)
        os.replace(part, target)
    finally:
        part.unlink(missing_ok=True)


def write_manifest(spec: registry.ModelSpec, directory: Path,
                   derived: Mapping[str, Mapping[str, Any]] | None = None) -> Path:
    """Manifeste des fichiers présents ; les constructions déjà présentes sont conservées / keeps prior builds."""
    previous = registry.read_manifest(directory).get("derived")
    entries = {**(previous if isinstance(previous, dict) else {}), **(derived or {})}
    manifest = {
        "model": spec.name,
        "license": spec.license,
        "model_file": spec.model_file,
        "updated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "files": {
            f.name: {"repo": f.repo, "revision": f.revision, "path": f.path, "size": f.size, "sha256": f.sha256}
            for f in spec.files if (directory / f.name).is_file()
        },
        "derived": {name: dict(entry) for name, entry in entries.items() if (directory / name).is_file()},
    }
    path = directory / registry.MANIFEST_NAME
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return path


def fetch_model(spec: registry.ModelSpec, dest_root: Path, *, with_optional: bool = False,
                endpoint: str = registry.HF_ENDPOINT, opener: Opener = https_open, log: Log = print) -> Path:
    directory = dest_root / spec.name
    directory.mkdir(parents=True, exist_ok=True)
    for expected in spec.files:
        if expected.optional and not with_optional:
            continue
        target = directory / expected.name
        if is_valid(target, expected):
            log(f"ok    {expected.name} (déjà présent / already present)")
            continue
        log(f"get   {expected.name} <- {expected.repo}@{expected.revision[:12]} ({expected.size / 1e6:.1f} MB)")
        download(expected, target, endpoint, opener, log)
    write_manifest(spec, directory)
    return directory


# --- construction INT8 locale / local INT8 build -------------------------------------------------------


def quantize_int8(source: Path, target: Path) -> dict[str, str]:
    """Recette `registry.INT8_RECIPE` ; exige le paquet `onnx` / requires the `onnx` package."""
    try:
        import onnx
        import onnxruntime
        from onnxruntime.quantization import QuantType, quantize_dynamic
    except ImportError as exc:
        raise RuntimeError("--build-int8 exige / requires: pip install onnx") from exc
    root = logging.getLogger()
    level = root.level
    root.setLevel(logging.ERROR)  # « run pre-processing » : sans objet ici / not applicable here
    try:
        quantize_dynamic(str(source), str(target), op_types_to_quantize=["MatMul"], per_channel=True,
                         weight_type=QuantType.QUInt8)
    finally:
        root.setLevel(level)
    return {"onnxruntime": onnxruntime.__version__, "onnx": onnx.__version__}


def label_agreement(directory: Path, spec: registry.ModelSpec, candidate: Path) -> tuple[float, float]:
    """Accord des étiquettes argmax avec le fp32 : global et sur les jetons d'entité / label agreement with fp32."""
    import numpy as np

    from gdprguardian.ner.runtime import TokenClassifier

    tokenizer, config = directory / spec.tokenizer_file, directory / spec.config_file
    reference = TokenClassifier.load(directory / spec.model_file, tokenizer, config, threads=4)
    built = TokenClassifier.load(candidate, tokenizer, config, threads=4)
    named = reference.scheme.type_matrix.any(axis=1)  # classes PER/ORG/LOC (ni O ni MISC) / named-entity classes
    same = total = same_entity = entity = 0
    for sentence in CHECK_SENTENCES:
        ids = np.array([reference.tokenizer.encode(sentence).ids], np.int64)
        feeds = {"input_ids": ids, "attention_mask": np.ones_like(ids)}
        expected = reference.session.run(None, feeds)[0].argmax(-1)
        got = built.session.run(None, feeds)[0].argmax(-1)
        on_entity = named[expected]
        same += int((expected == got).sum())
        total += expected.size
        entity += int(on_entity.sum())
        same_entity += int((on_entity & (expected == got)).sum())
    return same / total, same_entity / max(entity, 1)


def build_derived(spec: registry.ModelSpec, directory: Path, *,
                  quantize: Callable[[Path, Path], Mapping[str, str]] = quantize_int8,
                  check: Callable[[Path, registry.ModelSpec, Path], tuple[float, float]] = label_agreement,
                  log: Log = print) -> dict[str, dict[str, Any]]:
    """Construit chaque fichier dérivé depuis sa source vérifiée, le contrôle, puis l'inscrit au manifeste.

    Builds each derived file from its verified source, checks it against fp32, then records it in the manifest.
    """
    built: dict[str, dict[str, Any]] = {}
    for derived in spec.derived:
        source = spec.file(derived.source)
        if source is None or not is_valid(directory / derived.source, source):
            raise IntegrityError(f"{derived.source}: source absente ou modifiée / missing or altered source")
        target = directory / derived.name
        part = target.with_name(target.name + ".part")
        try:
            log(f"build {derived.name} <- {derived.source}")
            versions = dict(quantize(directory / derived.source, part))
            overall, on_entities = check(directory, spec, part)
            log(f"  accord / agreement: {overall:.1%} (jetons d'entité / entity tokens {on_entities:.1%})")
            if overall < MIN_AGREEMENT or on_entities < MIN_ENTITY_AGREEMENT:
                raise IntegrityError(f"{derived.name}: trop éloigné du fp32 / too far from fp32 "
                                     f"({overall:.1%}, {on_entities:.1%})")
            os.replace(part, target)
        finally:
            part.unlink(missing_ok=True)
        built[derived.name] = {
            "sha256": registry.sha256_file(target), "size": target.stat().st_size, "source": derived.source,
            "source_sha256": source.sha256, "recipe": derived.recipe, "agreement": round(overall, 4),
            "entity_agreement": round(on_entities, 4), "built_with": versions,
            "built_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        }
    write_manifest(spec, directory, built)
    return built


def verify_model(spec: registry.ModelSpec, dest_root: Path, log: Log = print) -> bool:
    directory = dest_root / spec.name
    healthy = True
    for expected in spec.files:
        path = directory / expected.name
        if not path.is_file():
            if not expected.optional:
                log(f"MISSING {expected.name}")
                healthy = False
            continue
        good = is_valid(path, expected)
        healthy &= good
        log(f"{'ok' if good else 'BAD':7} {expected.name}")
    for derived in spec.derived:
        if (directory / derived.name).is_file():
            try:
                registry.verify_files(directory, spec, [derived.name])
                log(f"ok      {derived.name} (construit / built)")
            except registry.ModelIntegrityError:
                log(f"BAD     {derived.name}")
                healthy = False
    return healthy


def default_dest() -> Path:
    env = os.environ.get(registry.ENV_MODELS_DIR)
    return Path(env) if env else ROOT / "models" / "cache"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", choices=[*registry.MODELS, "all"], default="all")
    parser.add_argument("--dest", type=Path, default=None, help="dossier parent / parent folder (models/cache)")
    parser.add_argument("--with-quantized", action="store_true",
                        help="INT8 fourni par l'auteur, évaluation seulement / shipped INT8, evaluation only")
    parser.add_argument("--build-int8", action="store_true",
                        help="construit et contrôle model_int8.onnx (exige onnx) / build and check (needs onnx)")
    parser.add_argument("--endpoint", default=os.environ.get("HF_ENDPOINT", registry.HF_ENDPOINT),
                        help="miroir HTTPS (empreintes toujours vérifiées) / HTTPS mirror, digests still checked")
    parser.add_argument("--verify", action="store_true", help="vérifie sans réseau / offline verification")
    args = parser.parse_args(argv)
    dest = args.dest or default_dest()
    specs = list(registry.MODELS.values()) if args.model == "all" else [registry.MODELS[args.model]]
    try:
        for spec in specs:
            if args.verify:
                if not verify_model(spec, dest):
                    return 1
                continue
            directory = fetch_model(spec, dest, with_optional=args.with_quantized, endpoint=args.endpoint)
            if args.build_int8:
                build_derived(spec, directory)
            print(f"done  {spec.name} -> {directory}")
    except (OSError, IntegrityError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
