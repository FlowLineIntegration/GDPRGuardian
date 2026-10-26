"""Packs pays : chargement TOML et compilation unique / country packs: TOML loading, compiled once."""

from __future__ import annotations

import importlib
import re
import tomllib
from dataclasses import dataclass, field
from functools import cache
from importlib import resources
from pathlib import Path
from typing import Any

from .._text import SEP, fold
from ..labels import LABELS, Label
from ..types import (
    PRIORITY_CONTEXT,
    PRIORITY_CONTEXT_ONLY,
    PRIORITY_LENIENT,
    PRIORITY_STRUCTURAL,
    PRIORITY_VALIDATED,
    TIERS,
)
from ..validators import Validator, resolve

# {LB} se place après le premier caractère (garde le préfiltre rapide de sre) : borne gauche alphanumérique.
# {LB} goes after the first character (keeps sre's fast prefix scan): alphanumeric left boundary.
_MACROS = {"S": f"{SEP}?", "SEP": SEP, "LB": "(?<![0-9A-Za-z]{2})", "RB": "(?![0-9A-Za-z])"}
_MACRO_RE = re.compile(r"\{([A-Z]+)\}")
_FLAGS = {"i": re.IGNORECASE, "m": re.MULTILINE, "s": re.DOTALL}
_DEFAULT_SCORE = {"A": 0.95, "B": 0.85, "C": 0.75, "L": 0.8}
_BOUNDARIES = frozenset({"alnum", "word", "ip", "hex", "phone", "digit", "none"})
_RECOGNIZER_KEYS = frozenset({
    "id", "entity", "label", "tier", "pattern", "flags", "validator", "group", "boundary", "context",
    "veto", "window", "prefilter", "score", "policy", "invalid",
})
DEFAULT_WINDOW = (48, 16)


@dataclass(slots=True, frozen=True)
class PatternRecognizer:
    id: str
    pack: str
    entity: str
    label: str
    tier: str
    regex: re.Pattern[str]
    group: int | str
    validator: Validator | None
    validator_name: str | None
    contexts: tuple[str, ...]
    vetoes: tuple[str, ...]
    before: int
    after: int
    boundary: str
    prefilter: str | tuple[str, ...] | None
    score: float
    priority: int
    policy: str | None
    # `invalid = "context"` : clé fausse acceptée si un mot-clé est proche / wrong key accepted near a keyword.
    fallback: bool = False


@dataclass(slots=True)
class Pack:
    id: str
    name: str
    version: str
    country: str | None
    always_on: bool
    languages: tuple[str, ...]
    recognizers: list[PatternRecognizer]
    detector_specs: tuple[str, ...]
    context: dict[str, list[str]]
    headers: dict[str, list[str]]
    locale: dict[str, list[str]] = field(default_factory=dict)

    def group(self, name: str) -> str:
        """Nom de groupe qualifié par le pack / pack-qualified group name."""
        return name if ":" in name and name.split(":", 1)[0].isupper() else f"{self.id}:{name}"

    def build_detectors(self) -> list[Any]:
        detectors = []
        for spec in self.detector_specs:
            module_name, class_name = spec.split(":", 1)
            cls = getattr(importlib.import_module(module_name), class_name)
            detectors.append(cls(self))
        return detectors


def _expand(pattern: str) -> str:
    return _MACRO_RE.sub(lambda m: _MACROS.get(m.group(1), m.group(0)), pattern)


def _priority(tier: str, has_validator: bool) -> int:
    if tier == "A":
        return PRIORITY_VALIDATED if has_validator else PRIORITY_STRUCTURAL
    return {"B": PRIORITY_CONTEXT, "C": PRIORITY_CONTEXT_ONLY, "L": PRIORITY_LENIENT}[tier]


def _build_recognizer(pack: Pack, raw: dict[str, Any]) -> PatternRecognizer:
    unknown = set(raw) - _RECOGNIZER_KEYS
    rec_id = raw.get("id", "?")
    if unknown:
        raise ValueError(f"{pack.id}/{rec_id}: clés inconnues / unknown keys {sorted(unknown)}")
    tier = raw.get("tier", "A")
    boundary = raw.get("boundary", "alnum")
    if tier not in TIERS or boundary not in _BOUNDARIES:
        raise ValueError(f"{pack.id}/{rec_id}: tier ou boundary invalide / invalid tier or boundary")
    flags = 0
    for letter in raw.get("flags", ""):
        flags |= _FLAGS[letter]
    contexts, vetoes = raw.get("context", ()), raw.get("veto", ())
    if isinstance(contexts, str):
        contexts = (contexts,)
    if isinstance(vetoes, str):
        vetoes = (vetoes,)
    if tier in ("B", "C") and not contexts:
        raise ValueError(f"{pack.id}/{rec_id}: un tier {tier} exige un contexte / tier {tier} needs context")
    validator_name = raw.get("validator")
    validator = resolve(validator_name) if validator_name else None
    invalid = raw.get("invalid", "reject")
    if invalid not in ("reject", "context") or (invalid == "context" and not (validator and contexts)):
        raise ValueError(f"{pack.id}/{rec_id}: invalid = reject|context, context exige validateur et contexte "
                         "/ context needs a validator and a context")
    before, after = raw.get("window", DEFAULT_WINDOW)
    prefilter = raw.get("prefilter")
    if isinstance(prefilter, list):
        prefilter = tuple(p if p == "digit" else fold(p) for p in prefilter)
    elif isinstance(prefilter, str) and prefilter != "digit":
        prefilter = fold(prefilter)
    return PatternRecognizer(
        id=rec_id,
        pack=pack.id,
        entity=raw["entity"],
        label=raw.get("label", raw["entity"]),
        tier=tier,
        regex=re.compile(_expand(raw["pattern"]), flags),
        group=raw.get("group", 0),
        validator=validator,
        validator_name=validator_name,
        contexts=tuple(pack.group(c) for c in contexts),
        vetoes=tuple(pack.group(v) for v in vetoes),
        before=before,
        after=after,
        boundary=boundary,
        prefilter=prefilter,
        score=raw.get("score", _DEFAULT_SCORE[tier]),
        priority=_priority(tier, validator is not None),
        policy=raw.get("policy"),
        fallback=invalid == "context",
    )


def parse_pack(data: dict[str, Any]) -> Pack:
    meta = data["pack"]
    pack = Pack(
        id=meta["id"],
        name=meta.get("name", meta["id"]),
        version=meta.get("version", "0"),
        country=meta.get("country"),
        always_on=bool(meta.get("always_on", False)),
        languages=tuple(meta.get("languages", ())),
        recognizers=[],
        detector_specs=tuple(meta.get("detectors", ())),
        context={},
        headers={k: list(v) for k, v in data.get("headers", {}).items()},
        locale={k: list(v) for k, v in data.get("locale", {}).items()},
    )
    for group_name, by_language in data.get("context", {}).items():
        words: list[str] = []
        for language_words in by_language.values():
            words.extend(language_words)
        pack.context[pack.group(group_name)] = words
    for key, raw_label in data.get("labels", {}).items():
        texts = {lang: raw_label[lang] for lang in ("fr", "en", "de", "es", "it", "nl", "pt") if lang in raw_label}
        LABELS.register(Label(key, texts or {"en": key}, raw_label.get("neutral"),
                              tuple(raw_label.get("aliases", ()))))
    seen: set[str] = set()
    for raw in data.get("recognizer", ()):
        recognizer = _build_recognizer(pack, raw)
        if recognizer.id in seen:
            raise ValueError(f"{pack.id}: identifiant en double / duplicate id {recognizer.id}")
        seen.add(recognizer.id)
        pack.recognizers.append(recognizer)
    return pack


def _data_dir() -> Path:
    return Path(str(resources.files(__package__) / "data"))


@cache
def available_packs() -> tuple[str, ...]:
    return tuple(sorted(p.stem.upper() for p in _data_dir().glob("*.toml")))


@cache
def load_pack(pack_id: str) -> Pack:
    path = _data_dir() / f"{pack_id.lower()}.toml"
    if not path.exists():
        raise ValueError(f"Pack inconnu / unknown pack: {pack_id} (disponibles / available: {available_packs()})")
    return load_pack_file(path)


def load_pack_file(path: str | Path) -> Pack:
    with open(path, "rb") as handle:
        return parse_pack(tomllib.load(handle))
