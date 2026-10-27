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

import difflib
import json
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from functools import lru_cache
from typing import Any, Literal, get_args

from ..categories import CATEGORIES, CATEGORIES_HELP, DEFAULT_MODE, fold_name, mode_warning, resolve_mode
from ..custom import RuleError, RuleSet, parse_rules
from ..engine import NAMES_FRENCH_ONLY, Anonymizer
from ..locale import LANGUAGE_SAMPLE, stopword_counts
from ..packs import available_packs, load_pack

# Ancien argument, alias déprécié de `mode` / old argument, deprecated alias of `mode`.
Profile = Literal["fast", "standard", "strict"]
LabelLanguage = Literal["fr", "en", "auto"]
LABEL_LANGUAGES: tuple[str, ...] = get_args(LabelLanguage)
MAX_COUNTRIES = 16
# Pays explicite par défaut, comme la bibliothèque ; « auto » reste expérimental / explicit country by default.
DEFAULT_COUNTRIES: tuple[str, ...] = ("FR",)
COUNTRY_MODES = ("auto", "all")

# Trois modes : un seul réglage du moteur (Settings.mode, Settings.disable), table et analyse dans `categories`,
# reprises telles quelles ici (mêmes noms, mêmes refus). « fort » par défaut à toutes les entrées.
# Three modes: one engine setting, table and parsing in `categories`, reused as they are (same names, same refusals).
Mode = Literal["fort", "essentiel", "personnalise", "strong", "essential", "custom", "basique", "basic"]
# Catégories que `disable` coupe en mode personnalisé : nom français -> alias anglais / French name -> English alias.
DISABLE_CATEGORIES: dict[str, str] = {category.name: category.alias for category in CATEGORIES}
_CATEGORY_NAMES = {**{fr: fr for fr in DISABLE_CATEGORIES}, **{en: fr for fr, en in DISABLE_CATEGORIES.items()}}
MAX_DISABLE = 32
# Descriptions communes à l'API REST et aux outils MCP (mêmes noms, schémas et textes).
# Descriptions shared by the REST API and the MCP tools (same names, schemas and texts).
MODE_DESCRIPTION = (
    "Keep the default unless the user asked for another mode. "
    "'fort' (EN 'strong', the default): masks everything it can, every code with letters and digits (product, "
    "order, invoice codes included), long numbers, shared mailboxes (support@...), handles, phone fragments. "
    "'essentiel' (EN 'essential'; 'basique' and 'basic' accepted): only what a validator, a format or a personal "
    "label proves (names, personal e-mails, phones, addresses, birth dates, IBAN, cards, national numbers, IP, "
    "plates, secrets, identifiers after a label such as 'n° client'); e.g. SKU-ALPHA-0042 and support@ stay readable. "
    "'personnalise' (EN 'custom'): 'fort' minus the categories in disable, e.g. disable [\"codes\", "
    "\"boites_fonctionnelles\"] keeps product references and shared mailboxes readable. "
    "For one precise code shape, a keep rule in rules is the precise alternative.")
DISABLE_DESCRIPTION = (
    "Only with mode 'personnalise' (or without mode, which then selects it): the categories left in clear, e.g. "
    "[\"codes\", \"boites_fonctionnelles\"] keeps product references and shared mailboxes readable. Categories "
    "(French name, English alias): " + CATEGORIES_HELP + ". Refused with mode 'fort' or 'essentiel'. 'secrets' "
    "(passwords, keys, tokens) can never be disabled. Disabling personnes leaves the text NOT anonymised: the report "
    "warns.")
PROFILE_DESCRIPTION = (
    "DEPRECATED, use mode. Old values still accepted: 'strict' = mode 'fort', 'standard' = mode 'essentiel', "
    "'fast' = mode 'essentiel' (fast always had the same detection as standard). Leave it out.")
# Avertissement « sans FR » complet : chaque type que seul le pack français couvre / full "without FR" warning.
WITHOUT_FR_WARNING = (
    "Pays FR absent : noms et adresses détectés par les lexiques français seulement, donc en clair ; restent aussi en "
    "clair : téléphones au format français, NIR, numéros fiscaux, CNI, passeports, permis, titres de séjour, numéros "
    "de santé (ADELI, RPPS, FINESS), INE, CAF, France Travail, SIRET/SIREN/TVA, plaques, identifiants après un "
    "libellé français (n° client, matricule...) et dates de naissance ; ajoutez FR (countries='FR,BE') / Country FR "
    "missing: names and addresses are detected by the French lexicons only, so they stay in clear; also left in "
    "clear: French-format phone numbers, NIR, tax numbers, identity cards, passports, driving licences, residence "
    "permits, health numbers (ADELI, RPPS, FINESS), INE, CAF, France Travail, SIRET/SIREN/VAT, plates, identifiers "
    "after a French label (n° client, matricule...) and birth dates; add FR (countries='FR,BE')")
# Détection de langue jugée sûre (label_language=auto) : mots outils de la langue retenue, et avance sur la suivante.
# Language detection deemed sure (label_language=auto): stopwords of the chosen language, and lead over the next one.
_SURE_STOPWORDS = 3
_SURE_MARGIN = 2


@dataclass(slots=True, frozen=True, eq=False)
class AnonymizeOptions:
    """Réglages exposés par l'API / API-exposed settings.

    `countries` : tuple trié de packs, ou "auto" / "all". `mode` : fort | essentiel | personnalise ; `disable` :
    catégories coupées (personnalise seulement), noms français canoniques. `rules` : jeu de règles de l'organisation,
    jamais mis en cache ni journalisé (il peut contenir des noms). `explain` : rapport « balise -> règle, raison ».
    `mode`/`disable`: canonical French names. `rules`: the organisation's rule set, never cached nor logged.
    `profile` : ancien argument déprécié, transmis tel quel au moteur (« strict » y garde ses effets d'avant, comme
    dans la bibliothèque) / deprecated old argument, passed on to the engine as is (same effects as the library).
    """

    countries: str | tuple[str, ...] = DEFAULT_COUNTRIES
    mode: str = DEFAULT_MODE
    label_language: str = "fr"
    rules: RuleSet | None = None
    explain: bool = False
    disable: tuple[str, ...] = ()
    profile: str | None = None

    @classmethod
    def build(cls, countries: str | Sequence[str] | None = None, profile: str | None = None,
              label_language: str | None = None, rules: Mapping[str, Any] | str | None = None,
              explain: bool | str | None = False, *, mode: str | None = None,
              disable: str | Sequence[str] | None = None) -> AnonymizeOptions:
        """Valide et normalise ; lève ValueError (message sans donnée) / validates; ValueError carries no data.

        `profile` : alias déprécié de `mode` (strict -> fort, standard et fast -> essentiel) / deprecated alias.
        """
        label_language = label_language or "fr"
        if label_language not in LABEL_LANGUAGES:
            raise ValueError(f"label_language ∈ {', '.join(LABEL_LANGUAGES)}")
        resolved, disabled = parse_mode(mode, profile, disable)
        return cls(parse_countries(countries), resolved, label_language, parse_rule_option(rules),
                   parse_flag(explain), disabled, profile or None)

    def to_json(self) -> dict[str, Any]:
        """Forme JSON envoyée au travailleur, règles comprises / JSON form sent to the worker, rules included."""
        countries = self.countries if isinstance(self.countries, str) else list(self.countries)
        return {"countries": countries, "mode": self.mode, "disable": list(self.disable), "profile": self.profile,
                "label_language": self.label_language, "explain": self.explain,
                "rules": None if self.rules is None else rules_to_json(self.rules)}

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> AnonymizeOptions:
        """Côté travailleur : mêmes contrôles qu'à l'entrée ; règles relues comme non sûres (moteur linéaire).

        Worker side: same checks as at the door; rules re-parsed as untrusted (linear-time engine).
        """
        options = cls.build(data["countries"], data.get("profile"), data["label_language"], None, data["explain"],
                            mode=data["mode"], disable=data["disable"] or None)
        if data["rules"] is None:
            return options
        try:
            return replace(options, rules=parse_rules(data["rules"], trusted=False))
        except RuleError as exc:
            raise ValueError(str(exc)) from None

    def for_text(self, text: str) -> AnonymizeOptions:
        """label_language=auto sur un texte court ou ambigu : la langue des pays demandés (FR -> français).

        label_language=auto on a short or ambiguous text: the requested countries' language (FR -> French). Une
        détection sûre (au moins `_SURE_STOPWORDS` mots outils et `_SURE_MARGIN` d'avance) décide comme avant ;
        sinon « Kevin Lambert conteste son solde, il dit qu'il… » (deux « il », italiens pour la table) recevrait des
        étiquettes anglaises. A sure detection decides as before; otherwise the countries decide.
        """
        if self.label_language != "auto":
            return self
        folded = "".join(c for c in unicodedata.normalize("NFKD", text[:LANGUAGE_SAMPLE].lower())
                         if not unicodedata.combining(c))
        ranked = sorted(stopword_counts(folded).values(), reverse=True)
        best, second = [*ranked, 0, 0][:2]
        if best >= _SURE_STOPWORDS and best - second >= _SURE_MARGIN:
            return self
        return replace(self, label_language=countries_label_language(self.countries))

    def engine_settings(self) -> dict[str, Any]:
        """Réglages de mode passés au moteur (Settings.mode, Settings.disable, profil déprécié) / mode settings."""
        settings: dict[str, Any] = {"mode": self.mode, "disable": self.disable}
        if self.profile is not None:
            settings["profile"] = self.profile
        return settings

    def anonymizer(self) -> Anonymizer:
        if self.rules is not None:
            # Règles propres à la requête : moteur construit pour elle seule, jamais en cache.
            # Request-specific rules: engine built for this request only, never cached.
            return Anonymizer(countries=self.countries, label_language=self.label_language, rules=self.rules,
                              explain=self.explain, **self.engine_settings())
        return _anonymizer(self.countries, self.mode, self.disable, self.profile, self.label_language, self.explain)

    def annotate(self, report: dict[str, Any]) -> dict[str, Any]:
        """Avertissement « sans FR » complet ; mode, catégories coupées et avertissement si le moteur les a omis.

        Full "without FR" warning; mode, disabled categories and warning when the engine did not write them.
        """
        warnings = report.get("warnings")
        if isinstance(warnings, list) and NAMES_FRENCH_ONLY in warnings:
            # Sans FR, tout ce que le pack français couvre reste en clair : le dire en entier.
            # Without FR, everything the French pack covers stays in clear: say it in full.
            report["warnings"] = [WITHOUT_FR_WARNING if item == NAMES_FRENCH_ONLY else item for item in warnings]
        if "mode" in report:
            return report
        report["mode"] = self.mode
        report["disable"] = list(self.disable)
        warning = mode_warning(self.mode, self.disable)
        if warning is not None:
            report["warnings"] = [*(report.get("warnings") or []), warning]
        return report


def countries_label_language(countries: str | tuple[str, ...]) -> str:
    """'fr' si un pays demandé a le français pour première langue (FR, BE, LU, MC), ou pays non explicites ; sinon 'en'.

    'fr' when a requested country's first language is French, or countries not explicit; else 'en'.
    """
    if isinstance(countries, str):
        return "fr"
    for code in countries:
        languages = load_pack(code).locale.get("languages") or ()
        if languages and languages[0] == "fr":
            return "fr"
    return "en"


def _suggest(value: str) -> str:
    """« ; did you mean X? » pour une faute de frappe, sans jamais citer la valeur reçue / never quotes the value."""
    close = difflib.get_close_matches(fold_name(value), list(_CATEGORY_NAMES), n=1, cutoff=0.75)
    return f"; did you mean {_CATEGORY_NAMES[close[0]]}?" if close else ""


def parse_mode(mode: str | None, profile: str | None = None,
               disable: str | Sequence[str] | None = None) -> tuple[str, tuple[str, ...]]:
    """(mode canonique, catégories coupées) : `categories.resolve_mode`, plus une borne et une suggestion.

    (canonical mode, disabled categories): the engine's `resolve_mode` (same names, same refusals: unknown mode or
    category with the list, `disable` with fort or essentiel, a `profile` contradicting `mode`; `disable` without a
    mode selects personnalise), plus a bound on the list and a "did you mean" for a misspelt category.
    """
    items = disable.split(",") if isinstance(disable, str) else disable
    if items is not None and len(items) > MAX_DISABLE:
        raise ValueError(f"disable : {MAX_DISABLE} catégories au plus / at most {MAX_DISABLE} categories")
    try:
        return resolve_mode(mode, profile or None, disable)
    except ValueError as exc:
        message = str(exc)
        unknown = [item for item in (items or ()) if isinstance(item, str) and fold_name(item)
                   and fold_name(item) not in _CATEGORY_NAMES]
        if unknown and "; allowed:" in message:
            head, tail = message.split("; allowed:", 1)
            message = f"{head}{_suggest(unknown[0])}; allowed:{tail}"
        raise ValueError(message) from None


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
        # Le pack international est toujours actif : jamais proposé / the international pack is always on.
        listed = ", ".join(code for code in known if code != "INTL")
        separator = ("séparez les codes par une virgule, pas « ; » ni un espace / separate codes with a comma, not "
                     "';' or a space: 'FR,BE'; " if any(mark in code for code in codes for mark in ";| /") else "")
        raise ValueError(f"pack pays inconnu / unknown country pack: {separator}disponibles / available: {listed}, "
                         "'all' or 'auto' (the international pack is always on)")
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
def _anonymizer(countries: str | tuple[str, ...], mode: str, disable: tuple[str, ...], profile: str | None,
                label_language: str, explain: bool) -> Anonymizer:
    # Moteur sûr entre threads, compilé une fois par combinaison / thread-safe engine, compiled once per combination.
    extra = {} if profile is None else {"profile": profile}
    return Anonymizer(countries=countries, mode=mode, disable=disable, label_language=label_language, explain=explain,
                      **extra)
