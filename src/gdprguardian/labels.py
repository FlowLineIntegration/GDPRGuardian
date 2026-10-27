"""Libellés des balises et alias multilingues / placeholder labels and multilingual aliases.

Une clé de libellé (ex. "PERSON") a un texte par langue et un libellé neutre facultatif.
A label key (e.g. "PERSON") has one text per language and an optional neutral label.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

LABEL_TEXT_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,30}[A-Z0-9]$")


@dataclass(slots=True)
class Label:
    key: str
    texts: dict[str, str]
    neutral: str | None = None
    aliases: tuple[str, ...] = ()
    extra: dict[str, str] = field(default_factory=dict)

    def text(self, language: str) -> str:
        return self.texts.get(language) or self.texts.get("en") or self.key


# (clé, fr, en, neutre, alias) / (key, fr, en, neutral, aliases)
_BUILTIN: tuple[tuple[str, str, str, str | None, tuple[str, ...]], ...] = (
    ("PERSON", "PERSONNE", "PERSON", None, ("PERSONA", "PERS", "NOM", "NAME")),
    ("ORG", "ORG", "ORG", None, ("ORGANISATION", "ORGANIZATION", "SOCIETE", "COMPANY", "ENTREPRISE")),
    ("ADDRESS", "ADRESSE", "ADDRESS", None, ("ADDR", "DIRECCION", "INDIRIZZO", "ADRESSE_POSTALE")),
    ("LOCATION", "LIEU", "LOCATION", None, ("LOC", "VILLE", "CITY")),
    ("EMAIL", "EMAIL", "EMAIL", None, ("MAIL", "COURRIEL", "E_MAIL")),
    ("PHONE", "TEL", "PHONE", None, ("TELEPHONE", "TELEFONO", "TELEFON", "MOBILE")),
    ("URL", "URL", "URL", None, ("LIEN", "LINK")),
    ("IP", "IP", "IP", None, ("ADRESSE_IP", "IP_ADDRESS")),
    ("MAC", "MAC", "MAC", None, ("ADRESSE_MAC", "MAC_ADDRESS")),
    ("IBAN", "IBAN", "IBAN", None, ()),
    ("RIB", "RIB", "BANK_ACCOUNT", None, ("COMPTE", "ACCOUNT")),
    ("CARD", "CARTE", "CARD", None, ("CB", "CREDIT_CARD", "CARTE_BANCAIRE")),
    ("CRYPTO", "CRYPTO", "CRYPTO", None, ("WALLET", "PORTEFEUILLE")),
    ("IMEI", "IMEI", "IMEI", None, ()),
    ("MRZ", "MRZ", "MRZ", None, ()),
    ("SECRET", "SECRET", "SECRET", None, ("CLE_API", "API_KEY", "TOKEN", "JETON")),
    ("BIRTH_DATE", "DATE_NAISSANCE", "BIRTH_DATE", None, ("DDN", "DOB", "NAISSANCE")),
    ("DATE", "DATE", "DATE", None, ()),
    ("POSTAL_CODE", "CODE_POSTAL", "POSTAL_CODE", None, ("CP", "ZIP")),
    ("ID", "IDENTIFIANT", "IDENTIFIER", None, ("ID", "REFERENCE", "REF")),
    # Identité en ligne (filtre fort 1.0.2) : @pseudo, pseudonyme, identifiant de connexion / online identity.
    ("HANDLE", "PSEUDO", "HANDLE", None, ("PSEUDONYME", "USERNAME", "LOGIN")),
    ("NATIONAL_ID", "ID_NATIONAL", "NATIONAL_ID", None, ()),
    ("TAX_ID", "NUM_FISCAL", "TAX_ID", "TAX_ID", ("NIF", "SPI", "TIN")),
    ("COMPANY_ID", "ID_ENTREPRISE", "COMPANY_ID", None, ()),
    ("VAT", "TVA", "VAT", "COMPANY_ID", ("NUM_TVA", "VAT_NUMBER")),
    ("ID_DOCUMENT", "PIECE_IDENTITE", "ID_DOCUMENT", None, ()),
    ("ID_CARD", "CNI", "ID_CARD", "ID_DOCUMENT", ("CARTE_IDENTITE",)),
    ("PASSPORT", "PASSEPORT", "PASSPORT", "ID_DOCUMENT", ()),
    ("DRIVER_LICENSE", "PERMIS", "DRIVER_LICENSE", "ID_DOCUMENT", ("PERMIS_CONDUIRE", "NEPH")),
    ("RESIDENCE_PERMIT", "TITRE_SEJOUR", "RESIDENCE_PERMIT", "ID_DOCUMENT", ("AGDREF",)),
    ("PLATE", "PLAQUE", "PLATE", None, ("IMMATRICULATION", "LICENSE_PLATE")),
    ("HEALTH_ID", "ID_SANTE", "HEALTH_ID", None, ()),
    ("SOCIAL_ID", "ID_SOCIAL", "SOCIAL_ID", None, ()),
    ("STUDENT_ID", "ID_ETUDIANT", "STUDENT_ID", None, ()),
    # France
    ("NIR", "NIR", "NIR", "NATIONAL_ID", ("NSS", "NUM_SECU", "SECU", "INS")),
    ("SIREN", "SIREN", "SIREN", "COMPANY_ID", ()),
    ("SIRET", "SIRET", "SIRET", "COMPANY_ID", ()),
    ("RCS", "RCS", "RCS", "COMPANY_ID", ()),
    ("RNA", "RNA", "RNA", "COMPANY_ID", ()),
    ("EORI", "EORI", "EORI", "COMPANY_ID", ()),
    ("RPPS", "RPPS", "RPPS", "HEALTH_ID", ()),
    ("ADELI", "ADELI", "ADELI", "HEALTH_ID", ()),
    ("FINESS", "FINESS", "FINESS", "HEALTH_ID", ()),
    ("INE", "INE", "INE", "STUDENT_ID", ()),
    ("NUMEN", "NUMEN", "NUMEN", "ID", ()),
    ("CAF", "NUM_ALLOCATAIRE", "BENEFIT_ID", "SOCIAL_ID", ("ALLOCATAIRE", "CAF")),
    ("FRANCE_TRAVAIL", "ID_FRANCE_TRAVAIL", "JOBSEEKER_ID", "SOCIAL_ID", ("POLE_EMPLOI",)),
)


class LabelRegistry:
    """Registre extensible (les packs ajoutent leurs libellés) / extensible registry."""

    def __init__(self) -> None:
        self._labels: dict[str, Label] = {}
        self._alias_index: dict[str, str] = {}
        for key, fr, en, neutral, aliases in _BUILTIN:
            self.register(Label(key, {"fr": fr, "en": en}, neutral, aliases))

    def register(self, label: Label) -> None:
        self._labels[label.key] = label
        for text in (label.key, *label.texts.values(), *label.aliases):
            self._alias_index.setdefault(text.upper(), label.key)

    def get(self, key: str) -> Label:
        # Libellé inconnu (règle personnalisée, liste de termes) : objet éphémère, jamais inscrit. Aucune donnée
        # d'une requête ne survit dans ce registre partagé. Unknown label: ephemeral, never registered.
        return self._labels.get(key) or Label(key, {"fr": key, "en": key})

    def display(self, key: str, language: str, neutral: bool) -> str:
        """Texte affiché dans la balise / text shown in the placeholder."""
        label = self.get(key)
        if neutral and label.neutral:
            return self.get(label.neutral).text(language)
        return label.text(language)

    def key_for_alias(self, text: str) -> str | None:
        return self._alias_index.get(text.upper())

    def __contains__(self, key: str) -> bool:
        return key in self._labels


LABELS = LabelRegistry()
