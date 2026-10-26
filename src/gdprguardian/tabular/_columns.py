"""Typage des colonnes : a priori d'en-tête et preuves statistiques / column typing: header prior and evidence.

Le type n'est qu'un a priori : la détection par cellule reste active. Le masquage de la colonne entière est
réservé aux identifiants directs établis avec une forte confiance (test binomial contre le taux de réussite
dû au hasard, borne basse de Wilson). The type is only a prior: per-cell detection always runs. Whole-column
masking is reserved for direct identifiers established with high confidence (binomial test against the chance
pass rate, Wilson lower bound).
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .._text import fold
from ..validators import resolve
from ._values import is_temporal

if TYPE_CHECKING:
    from ..engine import Settings
    from ..packs import Pack

DETECT = "detect"   # détection par cellule seulement / per-cell detection only
MASK = "mask"       # identifiant direct : toute la colonne / direct identifier: whole column
YEAR = "year"       # date de naissance -> année / birth date -> year

SAMPLE_SIZE = 512
_ALPHA = 1e-3
_MIN_WILSON = 0.5
_MIN_WILSON_HEADERLESS = 0.6
_MIN_HEADERLESS_VALUES = 5
_HEADER_AGREEMENT = 0.6

# Taux de réussite d'un validateur sur des chiffres aléatoires / validator pass rate on random digits.
_CHANCE_RATES = {
    "fr.nir": 1 / 97, "fr.rib": 1 / 97, "fr.tva": 1 / 97, "intl.iban": 1 / 97, "fr.spi": 1 / 511,
    "fr.siren": 0.1, "fr.siret": 0.1, "fr.luhn_digits": 0.1, "fr.finess": 0.1, "fr.eori": 0.1,
    "intl.card": 0.1, "intl.imei": 0.1,
}
# Identifiants directs : colonne entière masquée si la confiance est forte / direct identifiers.
_DIRECT_ENTITIES = frozenset({
    "PERSON", "EMAIL", "PHONE", "ADDRESS", "ID", "NATIONAL_ID", "TAX_ID", "IBAN", "BANK_ACCOUNT", "CARD",
    "ID_CARD", "PASSPORT", "DRIVER_LICENSE", "RESIDENCE_PERMIT", "HEALTH_ID", "SOCIAL_ID", "STUDENT_ID", "PLATE",
    "IMEI", "MRZ", "ID_DOCUMENT",
})
_COMPANY_LABELS = frozenset({"SIREN", "SIRET", "VAT", "RCS", "RNA", "EORI"})
_FACILITY_LABELS = frozenset({"FINESS"})
_DEFAULT_ENTITIES = {
    "PERSON": "PERSON", "EMAIL": "EMAIL", "PHONE": "PHONE", "ADDRESS": "ADDRESS", "BIRTH_DATE": "BIRTH_DATE",
    "POSTAL_CODE": "POSTAL_CODE", "ID": "ID", "IBAN": "IBAN", "CARD": "CARD", "RIB": "BANK_ACCOUNT",
    "NIR": "NATIONAL_ID", "PASSPORT": "PASSPORT", "ID_CARD": "ID_CARD", "PLATE": "PLATE", "RPPS": "HEALTH_ID",
}
# Ordre de préférence à spécificité égale / preference order at equal specificity.
_PRIORITY = ("EMAIL", "IBAN", "RIB", "CARD", "NIR", "TAX_ID", "PASSPORT", "ID_CARD", "DRIVER_LICENSE",
             "RESIDENCE_PERMIT", "RPPS", "PLATE", "SIRET", "SIREN", "VAT", "BIRTH_DATE", "PHONE", "POSTAL_CODE",
             "ID", "ADDRESS", "PERSON")

# Lexique de base, complété par les en-têtes des packs (anglais et termes absents des packs).
# Base lexicon, extended by pack headers (English and terms missing from the packs).
_BASE_HEADERS: dict[str, tuple[str, ...]] = {
    "PERSON": ("name", "full name", "first name", "last name", "surname", "given name", "firstname", "lastname",
               "family name", "forename", "employee", "customer", "prénoms", "nom prénom", "nom et prénom",
               "prénom nom", "nom de naissance", "nom d'usage", "nom marital", "nom de jeune fille", "conjoint",
               "ayant droit", "vorname", "nachname", "apellido", "apellidos", "cognome"),
    "EMAIL": ("email address", "e-mail address", "adresse email", "adresse e-mail", "adresse mail",
              "adresse électronique", "courriel"),
    "PHONE": ("phone", "telephone", "phone number", "mobile phone", "cellphone", "numéro de téléphone",
              "n° de téléphone", "n° tél"),
    "BIRTH_DATE": ("date of birth", "birth date", "birthdate", "dob", "birthday", "né(e) le", "née le",
                   "date naissance", "date de naiss"),
    "ADDRESS": ("address", "street", "street address", "home address", "adresse personnelle",
                "complément d'adresse", "lieu-dit"),
    "POSTAL_CODE": ("zip", "zip code", "postcode", "postal code"),
    "CARD": ("card number", "credit card", "carte bancaire", "numéro de carte", "n° de carte", "n° cb"),
    "PASSPORT": ("passport", "passport number"),
    "ID": ("matricule", "badge", "ipp", "nda", "employee id", "customer id", "client id", "user id", "member id",
           "account number"),
}
_ID_PREFIXES = frozenset({"n", "no", "num", "numero", "ref", "reference", "id", "identifiant", "code"})
_ID_SUBJECTS = frozenset({
    "client", "contrat", "dossier", "patient", "sejour", "adherent", "police", "sinistre", "facture", "abonne",
    "pdl", "prm", "pce", "compteur", "beneficiaire", "assure", "employe", "salarie", "agent", "eleve", "etudiant",
    "usager", "utilisateur", "user", "customer", "employee", "member", "membre", "allocataire", "affilie", "licence",
    "licencie", "compte",
})
# Indices contraires : « Nom du produit » n'est pas une personne / negative cues.
_NEGATIVE: dict[str, frozenset[str]] = {
    "PERSON": frozenset({
        "produit", "produits", "article", "entreprise", "societe", "fichier", "projet", "ville", "commune", "pays",
        "rue", "voie", "service", "departement", "etablissement", "magasin", "agence", "banque", "marque", "modele",
        "region", "equipe", "groupe", "categorie", "poste", "fonction", "metier", "site", "lieu", "structure",
        "organisme", "fournisseur", "enseigne", "domaine", "serveur", "application", "logiciel", "document",
        "version", "campagne", "operation", "lot", "colonne", "variable", "champ", "onglet", "feuille", "tag",
        "product", "company", "file", "project", "city", "country", "street", "department", "brand", "team", "group",
        "category", "job", "title", "domain", "host", "server", "field", "sheet", "table", "vendor", "supplier",
        "batiment", "salle", "local", "formation", "cours", "matiere", "type", "statut", "status", "code", "id",
        "identifiant", "matricule", "numero", "no", "n", "ref", "reference",
    }),
    "BIRTH_DATE": frozenset({"lieu", "ville", "pays", "commune", "departement", "place", "city", "country", "nom",
                             "name"}),
    "ADDRESS": frozenset({"ip", "mac", "email", "mail", "electronique", "web", "url", "site", "e"}),
    "EMAIL": frozenset({"date", "envoi", "statut", "status", "nombre", "count", "objet", "subject"}),
    "PHONE": frozenset({"date", "duree", "nombre", "count", "modele", "model", "forfait", "operateur", "marque"}),
}
_GIVEN_TOKENS = frozenset({"prenom", "prenoms", "first", "firstname", "given", "forename", "vorname"})
_SURNAME_TOKENS = frozenset({"nom", "surname", "lastname", "last", "family", "nachname", "apellido", "apellidos",
                             "cognome"})
# Qualificatifs neutres : « Nom de famille », « Prénom usuel », « First name » / neutral qualifiers.
_NAME_QUALIFIERS = frozenset({"de", "d", "famille", "naissance", "usage", "marital", "jeune", "fille",
                              "patronymique", "usuel", "name", "s"})
_TOKEN_RE = re.compile(r"[a-z0-9]{1,40}")

_NAME_LIKE = re.compile(r"[^\W\d_]{1,40}\.?(?:(?:[ '’\-]{1,2}|, ?)[^\W\d_]{1,40}\.?){0,6}")
_UP, _LOW = "[A-ZÀ-ÖØ-Þ]", "[a-zß-öø-ÿ]"
_CAP_TOKEN = f"{_UP}{_LOW}{{1,30}}(?:[-']{_UP}?{_LOW}{{1,30}}){{0,3}}"
_UPPER_TOKEN = f"{_UP}{{2,30}}(?:[-']{_UP}{{1,30}}){{0,3}}"
_PARTICLE = "(?:de|du|des|del|della|di|da|van|von|der|den|le|la|ben|bin|el|al|d')"
# Prénom Nom / NOM Prénom, 2 à 4 mots capitalisés / 2 to 4 capitalised words.
_STRICT_NAME = re.compile(
    f"(?:{_CAP_TOKEN}|{_UPPER_TOKEN})(?: {{1,2}}(?:{_PARTICLE} )?(?:{_CAP_TOKEN}|{_UPPER_TOKEN})){{1,3}}")
_EMAIL_LIKE = re.compile(r"[\w.%+\-]{1,64}@(?:[\w\-]{1,63}\.){1,8}[A-Za-z]{2,24}")
_PHONE_LIKE = re.compile(r"\+?[0-9 .\-()/]{8,24}")
_DATE_LIKE = re.compile(
    r"[0-9]{1,2}[/.\-][0-9]{1,2}[/.\-][0-9]{2,4}|[0-9]{4}-[0-9]{2}-[0-9]{2}(?:[ T][0-9:]{5,8})?|(?:18|19|20)[0-9]{2}"
    r"|[0-9]{1,2}(?:er)? [a-zéû]{3,9}\.? [0-9]{4}", re.IGNORECASE)
_ALNUM_RE = re.compile(r"[^\W_]")
_IBAN_SHAPE = re.compile(r"[A-Za-z]{2}[0-9]{2}(?: ?[A-Za-z0-9]){10,32}")


def wilson_lower(successes: int, trials: int, z: float = 1.96) -> float:
    """Borne basse de l'intervalle de Wilson à 95 % / Wilson score interval lower bound."""
    if trials <= 0:
        return 0.0
    p = successes / trials
    z2 = z * z
    centre = p + z2 / (2 * trials)
    margin = z * math.sqrt(p * (1 - p) / trials + z2 / (4 * trials * trials))
    return max(0.0, (centre - margin) / (1 + z2 / trials))


def binomial_tail(successes: int, trials: int, p: float) -> float:
    """P(X >= k) pour X ~ B(n, p), en log, arrêt dès que les termes deviennent négligeables / log-space tail."""
    if successes <= 0:
        return 1.0
    if successes > trials or p <= 0.0:
        return 0.0
    if p >= 1.0:
        return 1.0
    log_p, log_q = math.log(p), math.log1p(-p)
    log_n = math.lgamma(trials + 1)
    total = 0.0
    for i in range(successes, trials + 1):
        term = math.exp(log_n - math.lgamma(i + 1) - math.lgamma(trials - i + 1) + i * log_p + (trials - i) * log_q)
        total += term
        if i > trials * p and term <= total * 1e-17:
            break
    return min(total, 1.0)


def tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(fold(text))


@dataclass(slots=True, frozen=True)
class HeaderMatch:
    label: str
    role: str
    specificity: int


@dataclass(slots=True, frozen=True)
class Probe:
    """Validateur à clé appliqué aux valeurs d'une colonne / checksum validator applied to a column."""

    label: str
    tier: str
    shape: re.Pattern[str]
    validator: Callable[[str], str | None]
    chance: float
    contexts: frozenset[str]


@dataclass(slots=True, frozen=True)
class ColumnType:
    """Type retenu pour une colonne (ou un champ de formulaire) / type chosen for a column (or form field)."""

    label: str | None = None
    entity: str | None = None
    action: str = DETECT
    role: str = ""
    evidence: str = ""
    forced: frozenset[str] = field(default_factory=frozenset)


class ColumnTyper:
    """Lexique et sondes compilés une fois par Anonymizer ; sans état modifiable (sûr entre threads).

    Lexicon and probes compiled once per Anonymizer; no mutable state (thread-safe). Ne garde aucune
    référence à l'Anonymizer (cache à clés faibles) / keeps no reference to the Anonymizer (weak-key cache).
    """

    def __init__(self, packs: Sequence[Pack], settings: Settings) -> None:
        self._settings = settings
        entries: dict[tuple[str, ...], str] = {}
        self._entity_of = dict(_DEFAULT_ENTITIES)
        self._validators: dict[str, list[Callable[[str], str | None]]] = {
            "EMAIL": [resolve("intl.email")], "IBAN": [resolve("intl.iban")],
            "PHONE": [resolve("fr.phone"), resolve("intl.digits_e164")],
        }
        for pack in packs:
            for label, words in pack.headers.items():
                for word in words:
                    entries.setdefault(tuple(tokens(word)), label)
            for rec in pack.recognizers:
                self._entity_of.setdefault(rec.label, rec.entity)
        for label, words in _BASE_HEADERS.items():
            for word in words:
                entries.setdefault(tuple(tokens(word)), label)
        self._by_first: dict[str, list[tuple[tuple[str, ...], str]]] = {}
        for key, label in entries.items():
            if key:
                self._by_first.setdefault(key[0], []).append((key, label))
        self._probes = self._build_probes(packs)
        for probe in self._probes:
            validators = self._validators.setdefault(probe.label, [])
            if probe.validator not in validators:
                validators.append(probe.validator)
        # Validateurs identiques à ceux du moteur : la balise directe est la même / same validators as the engine.
        # La forme n'est lue que comme booléen : `fullmatch` directement / the shape is only read as a boolean.
        self._direct: dict[str, tuple[Callable[[str], str | None], Callable[[str], object]]] = {
            "EMAIL": (resolve("intl.email"), _EMAIL_LIKE.fullmatch),
            "PHONE": (resolve("fr.phone"), _PHONE_LIKE.fullmatch),
            "IBAN": (resolve("intl.iban"), _IBAN_SHAPE.fullmatch),
        }
        for probe in self._probes:
            if probe.label not in self._direct:
                self._direct[probe.label] = (probe.validator, probe.shape.fullmatch)
        maskable = {label for label, entity in self._entity_of.items() if entity in _DIRECT_ENTITIES}
        maskable -= _COMPANY_LABELS | _FACILITY_LABELS
        if settings.company_ids == "mask":
            maskable |= _COMPANY_LABELS
        if settings.facility_ids == "mask":
            maskable |= _FACILITY_LABELS
        self._maskable = frozenset(label for label in maskable if self.entity_allowed(self._entity_of[label]))

    @staticmethod
    def _build_probes(packs: Sequence[Pack]) -> tuple[Probe, ...]:
        chance_of = {resolve(name): rate for name, rate in _CHANCE_RATES.items()}
        probes: list[Probe] = []
        for pack in packs:
            for rec in pack.recognizers:
                chance = chance_of.get(rec.validator) if rec.validator is not None else None
                if chance is not None and rec.group == 0:
                    probes.append(Probe(rec.label, rec.tier, rec.regex, rec.validator, chance,
                                        frozenset(rec.contexts)))
        probes.append(Probe("IBAN", "A", _IBAN_SHAPE, resolve("intl.iban"), 1 / 97, frozenset()))
        return tuple(probes)

    # --- en-têtes / headers ---

    def entity(self, label: str) -> str:
        return self._entity_of.get(label, label)

    def entity_allowed(self, entity: str) -> bool:
        if entity in self._settings.exclude_entities:
            return False
        return self._settings.entities is None or entity in self._settings.entities

    def direct_value(self, label: str, text: str) -> str | None:
        """Valeur canonique si la cellule est exactement une valeur valide du type de la colonne.

        Le moteur donnerait la même balise (mêmes validateurs) : il est alors inutile de le lancer.
        Canonical value when the cell is exactly one valid value of the column type; the engine would give
        the same placeholder (same validators), so it need not run.
        """
        entry = self._direct.get(label)
        if entry is None:
            return None
        validator, shape = entry
        stripped = text.strip()
        return validator(stripped) if shape(stripped) else None

    def direct_values(self, label: str | None, texts: Iterable[str]) -> list[str | None] | None:
        """`direct_value` de chaque texte, en une boucle ; None si le type n'a pas de valeur directe.

        `direct_value` of each text, in one loop; None when the type has no direct value.
        """
        entry = self._direct.get(label) if label else None
        if entry is None:
            return None
        validator, shape = entry
        values: list[str | None] = []
        append = values.append
        for text in texts:
            stripped = text.strip()
            append(validator(stripped) if shape(stripped) else None)
        return values

    def canonical(self, label: str, text: str) -> str:
        """Valeur canonique du moteur (validateur), pour des balises cohérentes / engine canonical value."""
        stripped = text.strip()
        for validator in self._validators.get(label, ()):
            value = validator(stripped)
            if value is not None:
                return value
        return stripped

    def match_header(self, header: str) -> HeaderMatch | None:
        """Libellé du lexique le plus spécifique contenu dans l'en-tête / most specific lexicon label in a header."""
        words = tokens(header)
        if not words or len(words) > 12:
            return None
        present = set(words)
        best: tuple[int, int, str] | None = None
        for start, word in enumerate(words):
            for key, label in self._by_first.get(word, ()):
                if tuple(words[start:start + len(key)]) != key or present & _NEGATIVE.get(label, frozenset()):
                    continue
                rank = (len(key), -_PRIORITY.index(label) if label in _PRIORITY else -len(_PRIORITY), label)
                if best is None or rank > best:
                    best = rank
        if any(w in _ID_PREFIXES for w in words) and any(w in _ID_SUBJECTS for w in words):
            rank = (2, -_PRIORITY.index("ID"), "ID")
            if best is None or rank > best:
                best = rank
        if best is None:
            return None
        label = best[2]
        # Rôle lu sur l'en-tête enfant : « Identité / Nom » est un nom de famille / role from the child header.
        role = _person_role(set(tokens(header.rsplit(" / ", 1)[-1]))) if label == "PERSON" else ""
        return HeaderMatch(label, role, best[0])

    def is_label(self, text: str, groups_of: Callable[[str], frozenset[str]]) -> bool:
        """Le texte ressemble-t-il à un libellé de champ ? (en-têtes, formulaires) / is it a field label?"""
        words = tokens(text)
        if not words or len(words) > 6:
            return False
        match = self.match_header(text)
        if match is not None and 2 * match.specificity >= len(words):
            return True
        return len(words) <= 3 and bool(groups_of(text))

    # --- classement / classification ---

    def classify(self, header: str, values: Sequence[tuple[Any, str]], occurrences: int,
                 forced: frozenset[str], single: bool = False) -> ColumnType:
        """Type d'une colonne d'après son en-tête et ses valeurs distinctes (échantillon) / column type.

        `values` : couples (brut, texte) distincts et non nuls ; `occurrences` : cellules non vides ;
        `forced` : groupes de contexte de l'en-tête. `values`: distinct non-null (raw, text) pairs;
        `occurrences`: non-empty cells; `forced`: the header's context groups.
        """
        match = self.match_header(header) if header else None
        texts = [text.strip() for _, text in values]
        if not single and texts:
            proven = self._checksum_evidence(texts, match, forced)
            if proven is not None:
                label, evidence = proven
                action = MASK if label in self._maskable else DETECT
                return ColumnType(label, self.entity(label), action, "", evidence, forced)
        if match is not None:
            label = match.label
            entity = self.entity(label)
            if label == "BIRTH_DATE" and self.entity_allowed(entity):
                agree = sum(1 for (raw, _), text in zip(values, texts, strict=True)
                            if is_temporal(raw) or _DATE_LIKE.fullmatch(text))
                if _agrees(agree, len(texts), single):
                    return ColumnType(label, entity, YEAR, "", "header+values", forced)
            elif label in self._maskable:
                predicate = self._shape(label)
                agree = sum(1 for text in texts if predicate(text))
                if _agrees(agree, len(texts), single):
                    return ColumnType(label, entity, MASK, match.role, "header+values", forced)
            return ColumnType(label, entity, DETECT, match.role, "header", forced)
        if not single and "PERSON" in self._maskable and self._headerless_names(texts, occurrences):
            return ColumnType("PERSON", "PERSON", MASK, "", "values", forced)
        return ColumnType(forced=forced)

    def person_column(self, covered: int, distinct: int) -> bool:
        """La détection a-t-elle reconnu assez de personnes pour typer la colonne ? / enough detected persons?"""
        return ("PERSON" in self._maskable and distinct >= _MIN_HEADERLESS_VALUES
                and wilson_lower(covered, distinct) >= _MIN_WILSON)

    def _checksum_evidence(self, texts: Sequence[str], match: HeaderMatch | None,
                           forced: frozenset[str]) -> tuple[str, str] | None:
        """Sonde dont la clé réussit bien au-delà du hasard ; l'accord avec l'en-tête départage (un SIRET passe
        aussi Luhn comme une carte). Probe whose checksum passes far beyond chance; header agreement breaks ties."""
        best: tuple[bool, float, str, str] | None = None
        for probe in self._probes:
            shaped = [text for text in texts if probe.shape.fullmatch(text)]
            if 2 * len(shaped) < len(texts):
                continue
            passed = sum(1 for text in shaped if probe.validator(text) is not None)
            lower = wilson_lower(passed, len(shaped))
            if lower < _MIN_WILSON or binomial_tail(passed, len(shaped), probe.chance) >= _ALPHA:
                continue
            header_agrees = (match is not None and match.label == probe.label) or bool(forced & probe.contexts)
            if probe.tier != "A" and not header_agrees:
                continue
            rank = (header_agrees, lower, probe.label, f"checksum {passed}/{len(shaped)}")
            if best is None or rank[:2] > best[:2]:
                best = rank
        return (best[2], best[3]) if best is not None else None

    def _shape(self, label: str) -> Callable[[str], bool]:
        if label == "PERSON":
            return lambda text: len(text) <= 80 and _NAME_LIKE.fullmatch(text) is not None
        if label == "EMAIL":
            return lambda text: _EMAIL_LIKE.fullmatch(text) is not None
        if label == "PHONE":
            return lambda text: _PHONE_LIKE.fullmatch(text) is not None and 8 <= sum(c.isdigit() for c in text) <= 15
        if label == "ADDRESS":
            return lambda text: any(c.isalpha() for c in text)
        shapes = [probe.shape for probe in self._probes if probe.label == label]
        if shapes:
            # Forme seule : une coquille garde la forme mais pas la clé / shape only: a typo keeps the shape.
            return lambda text: any(shape.fullmatch(text) for shape in shapes)
        return lambda text: len(text) <= 64 and _ALNUM_RE.search(text) is not None

    @staticmethod
    def _headerless_names(texts: Sequence[str], occurrences: int) -> bool:
        """Colonne sans en-tête de « Prénom NOM » distincts / headerless column of distinct full names."""
        if len(texts) < _MIN_HEADERLESS_VALUES or 2 * len(texts) < occurrences:
            return False
        hits = sum(1 for text in texts if not text.isupper() and _STRICT_NAME.fullmatch(text))
        return wilson_lower(hits, len(texts)) >= _MIN_WILSON_HEADERLESS


def _agrees(agree: int, total: int, single: bool) -> bool:
    """L'en-tête est l'a priori fort ; les valeurs doivent seulement ne pas le contredire.

    The header is the strong prior; values only need not to contradict it (60 %, as Purview's threshold).
    """
    if total <= 0:
        return False
    return agree == total if single else agree >= _HEADER_AGREEMENT * total


def _person_role(words: set[str]) -> str:
    """'given' ou 'surname' seulement pour un en-tête fait de ces seuls mots ; sinon 'full'.

    'given' or 'surname' only when the header holds nothing else; otherwise 'full'.
    """
    rest = words - _NAME_QUALIFIERS
    if rest and rest <= _GIVEN_TOKENS:
        return "given"
    if rest and rest <= _SURNAME_TOKENS:
        return "surname"
    return "full"


def sample_evenly(items: Sequence[Any], limit: int = SAMPLE_SIZE) -> list[Any]:
    """Échantillon réparti (début, milieu, fin) : évite les artefacts de tri / spread sample, avoids sort artefacts."""
    if len(items) <= limit:
        return list(items)
    step = len(items) / limit
    return [items[int(i * step)] for i in range(limit)]
