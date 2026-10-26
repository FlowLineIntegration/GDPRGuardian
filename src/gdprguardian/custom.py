"""Règles personnalisées : la couche que chaque organisation ajoute au moteur / custom rule sets.

Le moteur automatique (packs pays, clés de contrôle, heuristiques) fait le gros du travail ; un jeu de
règles l'adapte à une organisation : références internes à masquer, numéros de commande à conserver,
noms de projets confidentiels. Même esprit qu'un pack pays : déclaratif (TOML ou JSON), versionnable,
explicable. The automatic engine does the heavy lifting; a rule set adapts it to one organisation.

Sûreté / safety:
- règles non sûres (service en ligne) : exécutées par le moteur d'expressions régulières du noyau Rust, à
  temps linéaire (aucun retour arrière exponentiel), avec la sémantique exacte de `re` ; assertions de tête
  (un caractère avant la correspondance, `\\b`) et de fin (`(?=…)`, `(?!…)`, `$`, `\\Z`, `\\b`, `$` en dernière
  position d'un look-ahead positif final ou d'une alternative finale : `(?=\\s|$)`, `(?:$|\\s)`) acceptées ;
  assertions au milieu du motif, `$` suivi d'autre chose et références arrière refusées, avec la raison ;
- compilation bornée (2 Mo par motif, 16 Mo par jeu, un seul fil) dans le processus isolé de la requête ;
  l'accueil du service ne contrôle que la structure (`parse_rules`) ;
- bornes strictes (nombre de règles, longueur des motifs et des listes) ;
- jamais mises en cache ni journalisées : un motif peut contenir un nom.
Untrusted rules (online service) run on the Rust core's linear-time regex engine with `re`'s exact
semantics; leading (one character before the match, `\\b`) and trailing (`(?=…)`, `(?!…)`, `$`, `\\Z`, `\\b`,
`$` last in a final positive look-ahead or a final alternation) assertions are accepted; assertions inside the
pattern, a `$` followed by anything and backreferences are refused, with the reason; bounded compile (2 MB per
pattern, 16 MB per set, one thread) in the request's isolated process, the service front only checks the
structure; strict bounds; never cached nor logged (a pattern may contain a name).

Format (JSON ; le TOML a les mêmes clés, avec `[[rule]]`) / format (TOML uses the same keys, `[[rule]]`):
    {"name": "acme",
     "rules": [{"label": "CLIENT_ID", "pattern": "CLT-[0-9]{6}"},
               {"label": "ORDER", "pattern": "[0-9]{6}", "action": "keep", "context": ["commande"]}],
     "deny": {"PROJET": ["Opération Phénix"]},
     "allow": ["support@acme.fr"]}
"""

from __future__ import annotations

import json
import re
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from .packs import Pack, PatternRecognizer, _build_recognizer
from .types import PRIORITY_STRUCTURAL

MAX_RULES = 20
MAX_PATTERN = 500
MAX_CONTEXT_WORDS = 20
MAX_WORD = 64
MAX_TERMS = 500
MAX_WINDOW = 400
MASK, KEEP = "mask", "keep"
# Entité interne des règles « keep » : jamais rendue, elle protège sa zone / internal entity of keep rules.
KEEP_ENTITY = "_KEEP"
CUSTOM_PACK = "CUSTOM"
_LABEL_RE = re.compile(r"[A-Z][A-Z0-9_]{0,31}")
_NAME_RE = re.compile(r"[\w .-]{1,64}")
_RULE_KEYS = frozenset({"label", "pattern", "action", "context", "window", "case_sensitive", "whole_word"})
_SET_KEYS = frozenset({"name", "rules", "rule", "deny", "allow"})


class RuleError(ValueError):
    """Jeu de règles invalide ; le message désigne la règle fautive / invalid rule set, the message names the rule."""


@dataclass(frozen=True, slots=True)
class CustomRule:
    label: str
    pattern: str
    action: str = MASK
    context: tuple[str, ...] = ()
    window: tuple[int, int] = (48, 16)
    case_sensitive: bool = False
    whole_word: bool = True


@dataclass(frozen=True, slots=True)
class RuleSet:
    """Jeu de règles validé / validated rule set.

    `trusted=False` (service en ligne) : moteur linéaire exigé / linear-time engine required.
    """

    name: str = "custom"
    rules: tuple[CustomRule, ...] = ()
    deny: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    allow: tuple[str, ...] = ()
    trusted: bool = True

    def recognizers(self) -> list[PatternRecognizer]:
        """Recognizers du pseudo-pack CUSTOM, dans l'ordre des règles / pseudo-pack recognizers, in rule order."""
        pack = Pack(CUSTOM_PACK, self.name, "0", None, False, (), [], (), {}, {})
        recognizers = []
        for index, rule in enumerate(self.rules):
            raw: dict[str, Any] = {
                "id": f"CUSTOM_{index + 1}_{rule.label}", "entity": KEEP_ENTITY if rule.action == KEEP else rule.label,
                "label": rule.label, "tier": "C" if rule.context else "A", "pattern": rule.pattern,
                "flags": "" if rule.case_sensitive else "i", "boundary": "alnum" if rule.whole_word else "none",
                "window": list(rule.window), "score": 0.95,
            }
            if rule.context:
                raw["context"] = [f"r{index + 1}"]
            try:
                recognizer = _build_recognizer(pack, raw)
            except (re.error, ValueError) as error:
                raise RuleError(f"Règle n°{index + 1} ({rule.label}) : motif invalide / invalid pattern: "
                                f"{error}") from None
            # Une règle explicite passe devant les heuristiques, jamais devant une clé de contrôle validée.
            # An explicit rule wins over heuristics, never over a validated checksum.
            recognizers.append(replace(recognizer, priority=PRIORITY_STRUCTURAL))
        return recognizers

    def keyword_groups(self) -> dict[str, list[str]]:
        return {f"{CUSTOM_PACK}:r{i + 1}": list(rule.context) for i, rule in enumerate(self.rules) if rule.context}


def parse_rules(data: Mapping[str, Any] | None, *, trusted: bool = True) -> RuleSet | None:
    """Valide un jeu de règles (dict JSON ou TOML) / validates a rule set (JSON or TOML dict)."""
    if not data:
        return None
    if not isinstance(data, Mapping):
        raise RuleError("Jeu de règles : objet attendu / rule set: object expected")
    unknown = set(data) - _SET_KEYS
    if unknown:
        raise RuleError(f"Clés inconnues / unknown keys: {sorted(unknown)}")
    name = data.get("name", "custom")
    if not isinstance(name, str) or not _NAME_RE.fullmatch(name):
        raise RuleError("name : 1 à 64 caractères (lettres, chiffres, espace, . _ -) / 1-64 safe characters")
    raw_rules = data.get("rules", data.get("rule", []))
    if not isinstance(raw_rules, list) or len(raw_rules) > MAX_RULES:
        raise RuleError(f"rules : liste d'au plus {MAX_RULES} règles / list of at most {MAX_RULES} rules")
    rules = tuple(_parse_rule(raw, index) for index, raw in enumerate(raw_rules, 1))
    deny = _parse_deny(data.get("deny", {}))
    allow = _terms(data.get("allow", []), "allow")
    return RuleSet(name, rules, deny, allow, trusted)


def load_rules(path: str | Path) -> RuleSet | None:
    """Jeu de règles depuis un fichier .toml ou .json (usage local, de confiance) / from a local file (trusted)."""
    path = Path(path)
    raw = path.read_bytes()
    data = tomllib.loads(raw.decode("utf-8")) if path.suffix.lower() == ".toml" else json.loads(raw)
    return parse_rules(data, trusted=True)


def _parse_rule(raw: Any, index: int) -> CustomRule:
    where = f"Règle n°{index} / rule #{index}"
    if not isinstance(raw, Mapping):
        raise RuleError(f"{where} : objet attendu / object expected")
    unknown = set(raw) - _RULE_KEYS
    if unknown:
        raise RuleError(f"{where} : clés inconnues / unknown keys {sorted(unknown)}")
    label, pattern = raw.get("label"), raw.get("pattern")
    if not isinstance(label, str) or not _LABEL_RE.fullmatch(label):
        raise RuleError(f"{where} : label en MAJUSCULES, 1 à 32 caractères [A-Z0-9_] / uppercase label, 1-32 chars")
    if not isinstance(pattern, str) or not 1 <= len(pattern) <= MAX_PATTERN:
        raise RuleError(f"{where} ({label}) : motif de 1 à {MAX_PATTERN} caractères / pattern of 1-{MAX_PATTERN} chars")
    action = raw.get("action", MASK)
    if action not in (MASK, KEEP):
        raise RuleError(f"{where} ({label}) : action ∈ mask|keep")
    context = _terms(raw.get("context", []), f"{where} context", limit=MAX_CONTEXT_WORDS)
    window = raw.get("window", (48, 16))
    if isinstance(window, int):
        window = (window, window)
    if (not isinstance(window, (list, tuple)) or len(window) != 2
            or not all(isinstance(w, int) and 0 <= w <= MAX_WINDOW for w in window)):
        raise RuleError(f"{where} ({label}) : window = [avant, après], 0 à {MAX_WINDOW} / [before, after]")
    flags = {key: raw.get(key, default) for key, default in (("case_sensitive", False), ("whole_word", True))}
    if not all(isinstance(value, bool) for value in flags.values()):
        raise RuleError(f"{where} ({label}) : case_sensitive et whole_word sont des booléens / are booleans")
    return CustomRule(label, pattern, action, context, (window[0], window[1]), **flags)


def _parse_deny(raw: Any) -> dict[str, tuple[str, ...]]:
    if not isinstance(raw, Mapping) or len(raw) > MAX_RULES:
        raise RuleError(f"deny : objet {{LIBELLÉ: [termes]}}, {MAX_RULES} libellés au plus / at most "
                        f"{MAX_RULES} labels")
    deny: dict[str, tuple[str, ...]] = {}
    for label, terms in raw.items():
        if not isinstance(label, str) or not _LABEL_RE.fullmatch(label):
            raise RuleError("deny : libellés en MAJUSCULES [A-Z0-9_] / uppercase labels")
        deny[label] = _terms(terms, f"deny.{label}")
    return deny


def _terms(raw: Any, where: str, limit: int = MAX_TERMS) -> tuple[str, ...]:
    if not isinstance(raw, Sequence) or isinstance(raw, str) or len(raw) > limit:
        raise RuleError(f"{where} : liste d'au plus {limit} termes / list of at most {limit} terms")
    terms = []
    for term in raw:
        if not isinstance(term, str) or not term.strip() or len(term) > MAX_WORD:
            raise RuleError(f"{where} : termes de 1 à {MAX_WORD} caractères / terms of 1-{MAX_WORD} characters")
        terms.append(term.strip())
    return tuple(terms)


__all__ = ["CUSTOM_PACK", "KEEP_ENTITY", "CustomRule", "RuleError", "RuleSet", "load_rules", "parse_rules"]
