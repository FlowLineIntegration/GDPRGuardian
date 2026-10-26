"""Options d'anonymisation validées et cache des moteurs / validated anonymisation options and engine cache.

Les options voyagent vers le travailleur isolé en JSON (`to_json`, `from_json`) : jamais de pickle, et les
règles de l'organisation y sont relues comme non sûres. Options travel to the isolated worker as JSON:
never pickle, and the organisation's rules are re-parsed there as untrusted.

À l'accueil, les règles ne subissent qu'un contrôle de structure (nombres, longueurs, libellés) : leurs motifs
ne sont compilés que dans le travailleur plafonné, qui refuse un motif hors du moteur linéaire (422).
At the door, rules only get a structural check (counts, lengths, labels): their patterns are compiled only in
the capped worker, which refuses a pattern outside the linear-time engine (422).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from functools import lru_cache
from typing import Any, Literal, get_args

from ..custom import RuleError, RuleSet, parse_rules
from ..engine import PROFILES, Anonymizer
from ..packs import available_packs

Profile = Literal["fast", "standard", "strict"]
LabelLanguage = Literal["fr", "en", "auto"]
LABEL_LANGUAGES: tuple[str, ...] = get_args(LabelLanguage)
MAX_COUNTRIES = 16
# Pays explicite par défaut, comme la bibliothèque ; « auto » reste expérimental / explicit country by default.
DEFAULT_COUNTRIES: tuple[str, ...] = ("FR",)
COUNTRY_MODES = ("auto", "all")


@dataclass(slots=True, frozen=True, eq=False)
class AnonymizeOptions:
    """Réglages exposés par l'API / API-exposed settings.

    `countries` : tuple trié de packs, ou "auto" / "all". `rules` : jeu de règles de l'organisation, jamais
    mis en cache ni journalisé (il peut contenir des noms). `explain` : rapport « balise -> règle, raison ».
    `rules`: the organisation's rule set, never cached nor logged (it may contain names).
    """

    countries: str | tuple[str, ...] = DEFAULT_COUNTRIES
    profile: str = "standard"
    label_language: str = "fr"
    rules: RuleSet | None = None
    explain: bool = False

    @classmethod
    def build(cls, countries: str | Sequence[str] | None = None, profile: str | None = None,
              label_language: str | None = None, rules: Mapping[str, Any] | str | None = None,
              explain: bool | str | None = False) -> AnonymizeOptions:
        """Valide et normalise ; lève ValueError (message sans donnée) / validates; ValueError carries no data."""
        profile = profile or "standard"
        label_language = label_language or "fr"
        if profile not in PROFILES:
            raise ValueError(f"profile ∈ {', '.join(PROFILES)}")
        if label_language not in LABEL_LANGUAGES:
            raise ValueError(f"label_language ∈ {', '.join(LABEL_LANGUAGES)}")
        return cls(parse_countries(countries), profile, label_language, parse_rule_option(rules),
                   parse_flag(explain))

    def to_json(self) -> dict[str, Any]:
        """Forme JSON envoyée au travailleur, règles comprises / JSON form sent to the worker, rules included."""
        countries = self.countries if isinstance(self.countries, str) else list(self.countries)
        return {"countries": countries, "profile": self.profile, "label_language": self.label_language,
                "explain": self.explain, "rules": None if self.rules is None else rules_to_json(self.rules)}

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> AnonymizeOptions:
        """Côté travailleur : mêmes contrôles qu'à l'entrée ; règles relues comme non sûres (moteur linéaire).

        Worker side: same checks as at the door; rules re-parsed as untrusted (linear-time engine).
        """
        options = cls.build(data["countries"], data["profile"], data["label_language"], None, data["explain"])
        if data["rules"] is None:
            return options
        try:
            return replace(options, rules=parse_rules(data["rules"], trusted=False))
        except RuleError as exc:
            raise ValueError(str(exc)) from None

    def anonymizer(self) -> Anonymizer:
        if self.rules is not None:
            # Règles propres à la requête : moteur construit pour elle seule, jamais en cache.
            # Request-specific rules: engine built for this request only, never cached.
            return Anonymizer(countries=self.countries, profile=self.profile, label_language=self.label_language,
                              rules=self.rules, explain=self.explain)
        return _anonymizer(self.countries, self.profile, self.label_language, self.explain)


def parse_countries(value: str | Sequence[str] | None) -> str | tuple[str, ...]:
    """'FR', 'FR,BE', ['FR', 'BE'], 'auto' ou 'all' -> tuple trié de packs connus, ou le mode.

    -> sorted tuple of known packs, or the mode. Absent : France (pays explicite) / missing: France.
    """
    if value is None:
        return DEFAULT_COUNTRIES
    items = value.split(",") if isinstance(value, str) else list(value)
    if len(items) > MAX_COUNTRIES:
        raise ValueError(f"{MAX_COUNTRIES} pays au plus / at most {MAX_COUNTRIES} countries")
    codes = []
    for item in items:
        if not isinstance(item, str):
            raise ValueError("code pays attendu / country code expected")
        if item.strip():
            codes.append(item.strip().upper())
    if not codes:
        return DEFAULT_COUNTRIES
    if len(codes) == 1 and codes[0].lower() in COUNTRY_MODES:
        return codes[0].lower()
    known = available_packs()
    if any(code not in known for code in codes):
        raise ValueError(f"pack pays inconnu / unknown country pack (disponibles / available: {', '.join(known)})")
    return tuple(sorted(set(codes)))


def parse_rule_option(value: Mapping[str, Any] | str | None) -> RuleSet | None:
    """Jeu de règles en objet ou en texte JSON (formulaire) ; non sûr : moteur linéaire exigé.

    Rule set as an object or JSON text (form field); untrusted: linear-time engine required. Contrôle de
    structure seulement, rien n'est compilé ici : le travailleur isolé compile les motifs, sous son plafond
    mémoire. Structural check only, nothing compiled here: the isolated worker compiles the patterns, under its
    memory cap.
    """
    if value is None or value == "":
        return None
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            raise ValueError("rules : JSON invalide / invalid JSON") from None
    try:
        return parse_rules(value, trusted=False)
    except RuleError as exc:
        raise ValueError(str(exc)) from None


def rules_to_json(rules: RuleSet) -> dict[str, Any]:
    """Jeu de règles validé -> JSON que `parse_rules` relit à l'identique / validated rules -> JSON, round trip."""
    return {
        "name": rules.name,
        "rules": [{"label": rule.label, "pattern": rule.pattern, "action": rule.action, "context": list(rule.context),
                   "window": list(rule.window), "case_sensitive": rule.case_sensitive, "whole_word": rule.whole_word}
                  for rule in rules.rules],
        "deny": {label: list(terms) for label, terms in rules.deny.items()},
        "allow": list(rules.allow),
    }


def parse_flag(value: bool | str | None) -> bool:
    if isinstance(value, bool) or value is None:
        return bool(value)
    if value.strip().lower() in ("1", "true", "yes", "oui"):
        return True
    if value.strip().lower() in ("", "0", "false", "no", "non"):
        return False
    raise ValueError("explain : booléen attendu / boolean expected")


@lru_cache(maxsize=64)
def _anonymizer(countries: str | tuple[str, ...], profile: str, label_language: str, explain: bool) -> Anonymizer:
    # Moteur sûr entre threads, compilé une fois par combinaison / thread-safe engine, compiled once per combination.
    return Anonymizer(countries=countries, profile=profile, label_language=label_language, explain=explain)
