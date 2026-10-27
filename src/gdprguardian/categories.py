"""Modes et catégories du filtre (1.0.2, docs/REGLES.md « Modes ») / filter modes and categories.

Trois modes, un seul réglage du moteur (`Settings.mode`, `Settings.disable`) :

- « fort » (EN « strong »), le défaut de toutes les entrées : tout ce que le moteur sait masquer (filtre fort).
- « essentiel » (EN « essential » ; « basique », « basic » acceptés) : le filtre classique de premier niveau, ce
  qu'un validateur, un format reconnu ou un libellé explicite prouve. Restent en clair : les codes et les nombres
  longs sans libellé personnel, les boîtes fonctionnelles (support@, contact@, rh@…), les pseudonymes « @… » sans
  indice et les fragments de téléphone.
- « personnalise » (EN « custom ») : « fort » moins les catégories listées dans `disable`.

Dans tous les modes, les règles de l'organisation s'appliquent (garder, masquer, listes) et une règle « keep »
l'emporte sur tout. Le mode coupe des règles du moteur avant la résolution : une valeur jamais trouvée n'est ni
masquée ni propagée.

Three modes, one engine setting. "fort" (default): everything. "essentiel": what a validator, a recognised format or
an explicit label proves; codes and long numbers without a personal label, functional mailboxes, "@" handles without a
cue and phone fragments stay in clear. "personnalise": "fort" minus the categories in `disable`. The organisation's
rules apply in every mode; a keep rule wins over everything. The mode switches engine rules off before resolution: a
value never found is neither masked nor propagated.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from functools import cache
from typing import Any

MODES: tuple[str, ...] = ("fort", "essentiel", "personnalise")
DEFAULT_MODE = "fort"
# Alias acceptés (anglais ; « basique », ancien nom d'essentiel) / accepted aliases.
MODE_ALIASES: dict[str, str] = {"strong": "fort", "essential": "essentiel", "essentials": "essentiel",
                                "basique": "essentiel", "basic": "essentiel", "custom": "personnalise",
                                "personnalisé": "personnalise"}
# Ancien argument `profile`, déprécié : strict -> fort, standard -> essentiel, fast -> essentiel (fast n'avait pas de
# détection propre ; il coupait seulement le modèle NER optionnel, ce qu'il fait toujours). Deprecated `profile`:
# strict -> fort, standard -> essentiel, fast -> essentiel (fast only switched the optional NER model off, as before).
PROFILE_MODES: dict[str, str] = {"strict": "fort", "standard": "essentiel", "fast": "essentiel"}


@dataclass(frozen=True, slots=True)
class Category:
    """Catégorie que `disable` peut couper / a category `disable` can switch off."""

    name: str        # nom français canonique / canonical French name
    alias: str       # alias anglais / English alias
    entities: tuple[str, ...]  # entités du moteur couvertes / engine entities covered
    rules: tuple[str, ...]     # règles propres (identifiants de règle) / own rules (rule ids)
    reasons: tuple[str, ...]   # raisons `explain` typiques / typical `explain` reasons
    essentiel: bool  # active en mode essentiel ? / on in mode essentiel?
    description: str


# Table des catégories, dans l'ordre du rapport / category table, in report order.
CATEGORIES: tuple[Category, ...] = (
    Category("personnes", "persons", ("PERSON",), ("FR_NAMES", "FR_SIGNATURE", "FR_INITIALS", "NER"),
             ("name_lexicon", "propagation", "ner_model"), True, "noms et prénoms de personnes physiques"),
    Category("emails", "emails", ("EMAIL",), ("EMAIL", "EMAIL_OBFUSCATED", "EMAIL_OBFUSCATED_DOT"),
             ("format",), True, "adresses e-mail personnelles"),
    Category("boites_fonctionnelles", "functional_mailboxes", (), ("EMAIL",), ("format",), False,
             "boîtes fonctionnelles (support@, contact@, rh@, noreply@…)"),
    Category("telephones", "phones", ("PHONE",), ("FR_PHONE", "INTL_PHONE"), ("format", "phone_numbering_plan"), True,
             "numéros de téléphone"),
    Category("fragments", "phone_fragments", (), ("FR_PHONE_FRAGMENT",), ("phone_fragment",), False,
             "fin d'un numéro déjà masqué après un indice (« ne conserve que la fin du numéro : 00 11 »)"),
    Category("adresses", "addresses", ("ADDRESS", "POSTAL_CODE", "LOCATION"), ("FR_ADDRESS", "FR_ADDRESS_FIELD"),
             ("postcode_and_town", "street_and_number"), True, "adresses postales"),
    Category("dates_naissance", "birth_dates", ("BIRTH_DATE",),
             ("BIRTH_DATE", "FR_BIRTH_DATE_TEXT", "BIRTH_DATE_SHORT", "BIRTH_DATE_COMPACT", "BIRTH_DATE_ABBR_EN",
              "FR_BIRTH_DATE_ABBR", "FR_BIRTH_DATE_MAIDEN", "FR_BIRTH_DATE_PLACE"),
             ("keyword", "matches_nir"), True, "dates de naissance (et leurs autres graphies)"),
    Category("iban", "iban", ("IBAN", "BANK_ACCOUNT"), ("INTL_IBAN", "FR_RIB", "FR_IBAN_LABELLED"), ("validated",),
             True, "IBAN et RIB"),
    Category("cartes", "cards", ("CARD",), ("CARD", "CARD_GROUPED"), ("validated",), True,
             "cartes de paiement (clé de Luhn)"),
    Category("numeros_nationaux", "national_numbers",
             ("NATIONAL_ID", "ID_CARD", "PASSPORT", "DRIVER_LICENSE", "RESIDENCE_PERMIT", "HEALTH_ID", "TAX_ID",
              "SOCIAL_ID", "STUDENT_ID", "COMPANY_ID", "VAT", "MRZ"),
             ("FR_NIR", "FR_CNI", "FR_PASSPORT", "FR_RPPS", "FR_ADELI", "FR_SIRET", "FR_SIREN", "INTL_MRZ"),
             ("validated", "keyword", "sole_trader", "civil_status_nearby"), True,
             "numéros nationaux : NIR, CNI, passeport, permis, santé, SIRET/SIREN/TVA d'une personne"),
    Category("ip", "ip", ("IP", "MAC"), ("IPV4", "IPV6", "MAC"), ("format",), True, "adresses IP et MAC"),
    Category("identifiants_techniques", "technical_identifiers", ("ID", "IMEI", "CRYPTO", "URL"),
             ("UUID", "ID_BIOMETRIC", "IMEI", "URL_PERSONAL", "URL_PERSONAL_SITE", "URL_PERSONAL_NAME",
              "FR_CONTEXTUAL_ID", "FR_LABELLED_ID", "FR_LABELLED_NUMBER", "FR_LABELLED_NUMBER_START",
              "FR_ORDER_NUMBER"), ("format", "keyword", "personal_site_name"), True,
             "identifiants techniques et identifiants annoncés par un libellé personnel (n° client, dossier…)"),
    Category("codes", "codes", (), ("ID_CODE",), ("identifier_code",), False,
             "tout code lettres + chiffres (6 caractères ou plus) sans libellé personnel juste avant"),
    Category("nombres_longs", "long_numbers", (), ("ID_LONG_NUMBER",), ("long_number",), False,
             "suite nue de 8 chiffres ou plus sans libellé personnel juste avant"),
    Category("plaques", "plates", ("PLATE", "VEHICLE_ID"),
             ("FR_PLATE_SIV", "FR_PLATE_SIV_GLUED", "FR_PLATE_FNI", "FR_PLATE_FNI_BARE", "FR_VIN"),
             ("format", "keyword"), True, "plaques d'immatriculation et VIN"),
    Category("pseudonymes", "pseudonyms", ("HANDLE",), ("FR_PSEUDONYM", "FR_PSEUDONYM_QUOTED", "LOGIN", "LOGIN_BARE",
                                                       "LOGIN_BARE_WORD", "LOGIN_BARE_WORD_NOUN", "HANDLE",
                                                       "HANDLE_CUED", "HANDLE_PLATFORM", "HANDLE_PLATFORM_TEAMS",
                                                       "HANDLE_PLATFORM_CHAT_WORD", "LOGIN_PATH",
                                                       "PSEUDONYM_LABEL_CAPS", "LOGIN_DOMAIN",
                                                       "PSEUDONYM_LABEL", "PSEUDONYM_LABEL_LOWER", "PSEUDONYM_BARE",
                                                       "PSEUDONYM_BARE_WORD"),
             ("keyword", "format"), True,
             "pseudonymes et identifiants de connexion ; « @pseudo » sans indice : mode fort seulement"),
    Category("secrets", "secrets", ("SECRET",), ("SECRET_PASSWORD", "SECRET_PASSWORD_PHRASE", "SECRET_URL_PARAM",
                                                 "SECRET_ASSIGNMENT",
                                                 "SECRET_API_KEY", "SECRET_JWT", "SECRET_COOKIE"),
             ("format", "keyword"), True, "mots de passe, clés d'API, jetons, témoins (toujours masqués en essentiel)"),
)
BY_NAME: dict[str, Category] = {c.name: c for c in CATEGORIES}
_NAMES: dict[str, str] = {**{c.name: c.name for c in CATEGORIES}, **{c.alias: c.name for c in CATEGORIES}}
# Catégories dont la coupure laisse le texte non anonymisé : avertissement appuyé / risky categories.
RISKY: tuple[str, ...] = ("personnes", "secrets")
ESSENTIEL_OFF: tuple[str, ...] = tuple(c.name for c in CATEGORIES if not c.essentiel)
MODES_HELP = "fort | essentiel | personnalise (EN: strong | essential | custom ; « basique » accepté / accepted)"
# Jamais coupée (étude de l'état de l'art, 26/10) : un mot de passe ou une clé divulgués ne sont jamais acceptables.
# Never switched off: a leaked password or key is never acceptable.
NOT_DISABLEABLE: tuple[str, ...] = ("secrets",)
CATEGORIES_HELP = ", ".join(f"{c.name} ({c.alias})" if c.alias != c.name else c.name for c in CATEGORIES
                            if c.name not in NOT_DISABLEABLE)
SECRETS_REFUSED = ("disable : « secrets » ne se coupe jamais, un mot de passe ou une clé divulgués ne sont jamais "
                   "acceptables / 'secrets' can never be disabled: a leaked password or key is never acceptable")
ESSENTIEL_LEFT_IN_CLEAR = (
    "codes et nombres longs sans libellé personnel, boîtes fonctionnelles, pseudonymes « @… » sans indice, fragments "
    "de téléphone / codes and long numbers without a personal label, functional mailboxes, '@' handles without a cue, "
    "phone fragments")

_ENTITY_CATEGORY: dict[str, str] = {e: c.name for c in CATEGORIES for e in c.entities}
_RULE_CATEGORY: dict[str, str] = {"ID_CODE": "codes", "ID_LONG_NUMBER": "nombres_longs",
                                  "FR_PHONE_FRAGMENT": "fragments"}
# Coupées avec les téléphones (voie perf, 26/10) / switched off with the phones.
_WITH_PHONES = frozenset({"fragments"})
# Règle du mode fort seulement, sans catégorie propre : « @pseudo » sans indice (pseudonymes).
# A fort-only rule without a category of its own: an "@handle" without a cue.
_FORT_ONLY_RULES = frozenset({"HANDLE"})

# Boîte fonctionnelle : premier élément de la partie locale (avant « . », « - », « _ », « + ») dans cette liste.
# Functional mailbox: first element of the local part in this list.
FUNCTIONAL_LOCAL_PARTS = frozenset({
    "accueil", "achats", "admin", "administration", "alertes", "alerts", "assistance", "bonjour", "booking",
    "bureau", "candidature", "candidatures", "careers", "ce", "commandes", "commercial", "communication", "compta",
    "comptabilite", "contact", "contacts", "cse", "direction", "dpo", "drh", "dsi", "emploi", "equipe", "facturation",
    "factures", "gdpr", "hello", "help", "helpdesk", "hostmaster", "hotline", "hr", "info", "infos", "information",
    "informations", "informatique", "it", "jobs", "juridique", "legal", "mairie", "marketing", "newsletter",
    "noreply", "no", "notification", "notifications", "office", "orders", "paie", "payroll", "postmaster", "presse",
    "press", "privacy", "reception", "recrutement", "relation", "reservation", "reservations", "rgpd", "rh", "sales",
    "sav", "secretariat", "securite", "security", "service", "serviceclient", "standard", "support", "syndic", "team",
    "ventes", "webmaster", "abuse", "billing", "ne", "nepasrepondre", "donotreply", "do", "mailer", "bounce",
})
_LOCAL_SPLIT = re.compile(r"[.\-_+]")
_MAIL_AT = re.compile(r"\s*(?:@|\(at\)|\[at\]|\{at\}|\bat\b|\barobase\b)\s*", re.IGNORECASE)

# Libellé personnel juste avant un code ou un nombre (même ligne, trois mots courts au plus entre les deux, « : »,
# « = », « # », « n° » ou une cellule « | Client | » compris) : en mode essentiel, le code reste masqué.
# A personal label right before a code or number (same line, at most three short words between): kept in essentiel.
_PERSONAL_LABEL = (
    r"(?:clients?|clientes?|comptes?|dossiers?|matricules?|salari[ée]e?s?|employ[ée]e?s?|personnel|rh|tickets?|"
    r"incidents?|contrats?|adh[ée]rente?s?|patiente?s?|assur[ée]e?s?|b[ée]n[ée]ficiaires?|pseudo(?:nyme)?s?|"
    r"identifiants?|id|ipp|nda|login|utilisateurs?|user(?:name)?|cookies?|t[ée]moins?|gabarits?|biom[ée]triques?|"
    r"vocales?|badges?|abonn[ée]e?s?|r[ée]clamations?|sinistres?|polices?)")
_PERSONAL_LABEL_BEFORE = re.compile(
    r"(?<![\w])" + _PERSONAL_LABEL + r"(?![\w])(?:[ \t]+[^\s.;,!?|()]{1,14}){0,3}[ \t]*(?:[:#=°]|n[°o]\.?)?[ \t]*"
    r"\|?[ \t]*\Z", re.IGNORECASE)
_LABEL_WINDOW = 64
# Libellé commercial juste avant (revue du 26/10, troisième tour) : « facture », « commande », « devis », « bon de
# livraison », « ticket de caisse », « produit », « référence », « lot », « article » ne sont pas des libellés
# personnels. En essentiel, le numéro qui les suit reste lisible (le mode fort le masque) ; un libellé personnel plus
# près l'emporte (« facture du client 123456 »). A business label right before: not a personal label; in essentiel the
# number after it stays readable (fort masks it); a nearer personal label wins.
_BUSINESS_LABEL_BEFORE = re.compile(
    r"(?<![\w])(?:factures?|commandes?|devis|bons?[ \t]+de[ \t]+(?:livraison|commande)|tickets?[ \t]+de[ \t]+caisse|"
    r"produits?|r[ée]f[ée]rences?|r[ée]f|lots?|articles?|sku)(?![\w])(?:[ \t]+[^\s.;,!?|()]{1,14}){0,3}[ \t]*"
    r"(?:[:#=°]|n[°o]\.?)?[ \t]*\|?[ \t]*\Z", re.IGNORECASE)
# Règles d'un numéro ou d'un code que le libellé d'avant qualifie / rules whose number the preceding label qualifies.
_LABEL_RULES = frozenset({"FR_LABELLED_NUMBER", "FR_LABELLED_NUMBER_START", "ID_CODE", "ID_LONG_NUMBER"})
# Forme d'une plaque SIV (« AB-123-CD », « ZZ-000-ZZ ») / SIV plate shape.
_SIV_SHAPE = re.compile(r"[A-Za-z]{2}[- ]?[0-9]{3}[- ]?[A-Za-z]{2}")


def fold_name(value: str) -> str:
    """Minuscules, sans accents, « - » et espaces -> « _ » / lowercase, no accents, '-' and spaces -> '_'."""
    decomposed = unicodedata.normalize("NFKD", value.strip().lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c)).replace("-", "_").replace(" ", "_")


def resolve_mode(mode: str | None, profile: str | None = None,
                 disable: str | Sequence[str] | None = None) -> tuple[str, tuple[str, ...]]:
    """(mode canonique, catégories coupées) ; `disable` sans mode choisit « personnalise ».

    (canonical mode, disabled categories); `disable` without a mode selects "personnalise". Refus (ValueError, message
    sans donnée) : mode ou catégorie inconnus, avec la liste ; `disable` avec fort ou essentiel ; `profile` inconnu ou
    qui contredit `mode`. Refused: unknown mode or category (with the list), `disable` with fort or essentiel, an
    unknown `profile` or one contradicting `mode`.
    """
    if mode is not None and not isinstance(mode, str):
        raise ValueError(f"mode : texte attendu / string expected; allowed: {MODES_HELP}")
    folded = fold_name(mode) if mode else ""
    resolved = MODE_ALIASES.get(folded, folded) or None
    if resolved is not None and resolved not in MODES:
        raise ValueError(f"mode inconnu / unknown mode; allowed: {MODES_HELP}")
    if profile is not None:
        if profile not in PROFILE_MODES:
            raise ValueError(f"profile (déprécié, utilisez mode / deprecated, use mode) ∈ {', '.join(PROFILE_MODES)}")
        if resolved is not None and resolved != PROFILE_MODES[profile]:
            raise ValueError("profile (déprécié) contredit mode : n'envoyez que mode / deprecated profile contradicts "
                             f"mode: send mode only ({MODES_HELP})")
        resolved = resolved or PROFILE_MODES[profile]
    disabled = parse_disable(disable)
    if disabled:
        if resolved in ("fort", "essentiel"):
            raise ValueError(f"disable ne s'emploie qu'avec le mode personnalise (ou sans mode) ; le mode {resolved} "
                             "ne se modifie pas / disable only works with mode personnalise (custom) or without a "
                             f"mode; mode {resolved} cannot be changed")
        resolved = "personnalise"
    return resolved or DEFAULT_MODE, disabled


def parse_disable(value: str | Sequence[str] | None) -> tuple[str, ...]:
    """Liste ou texte séparé par des virgules -> noms français canoniques, dans l'ordre de la table.

    List or comma-separated text -> canonical French names, in table order. Nom inconnu : refusé avec la liste.
    """
    if value is None or value == "":
        return ()
    items = value.split(",") if isinstance(value, str) else list(value)
    chosen: set[str] = set()
    for item in items:
        if not isinstance(item, str):
            raise ValueError(f"disable : liste de catégories attendue / list of categories expected; allowed: "
                             f"{CATEGORIES_HELP}")
        folded = fold_name(item)
        if not folded:
            continue
        if folded not in _NAMES:
            raise ValueError(f"disable : catégorie inconnue / unknown category; allowed: {CATEGORIES_HELP}")
        if _NAMES[folded] in NOT_DISABLEABLE:
            raise ValueError(SECRETS_REFUSED)
        chosen.add(_NAMES[folded])
    return tuple(c.name for c in CATEGORIES if c.name in chosen)


def mode_warning(mode: str, disable: Sequence[str]) -> str | None:
    """Ce qui reste en clair hors du mode fort, dit en clair dans le rapport / what stays in clear outside fort."""
    if mode == "essentiel":
        return f"Mode essentiel : restent en clair / left in clear: {ESSENTIEL_LEFT_IN_CLEAR}"
    if mode == "personnalise" and disable:
        warning = ("Mode personnalisé : catégories laissées en clair / categories left in clear: "
                   + ", ".join(f"{name} ({BY_NAME[name].alias})" for name in disable))
        risky = [name for name in RISKY if name in disable]
        if risky:
            warning += (f". ATTENTION : {', '.join(risky)} non masqués, le texte n'est pas anonymisé / WARNING: "
                        f"{', '.join(BY_NAME[name].alias for name in risky)} not masked, the text is not anonymised")
        return warning
    return None


def functional_mailbox(surface: str) -> bool:
    """Boîte fonctionnelle (« support@… », « rh@… », « contact.paris@… ») / functional mailbox."""
    at = _MAIL_AT.search(surface)
    if at is None or at.start() == 0:
        return False
    local = fold_name(surface[:at.start()]).replace("_", ".")
    first = _LOCAL_SPLIT.split(local, 1)[0]
    return first in FUNCTIONAL_LOCAL_PARTS or local.replace(".", "") in FUNCTIONAL_LOCAL_PARTS


def _label_start(text: str, start: int) -> int:
    """Début de la fenêtre du libellé : même ligne, `_LABEL_WINDOW` caractères au plus. La fin de ligne n'est cherchée
    que dans la fenêtre (voie perf) : sur un texte sans retour à la ligne, chercher jusqu'au début coûtait un passage
    par zone (quadratique). Same bounds, looked up inside the window only: linear on a text without line breaks."""
    lo = max(0, start - _LABEL_WINDOW)
    return max(text.rfind("\n", lo, start) + 1, lo)


def personal_label_before(text: str, start: int) -> bool:
    """Libellé personnel juste avant `start`, sur la même ligne / a personal label right before, same line."""
    return _PERSONAL_LABEL_BEFORE.search(text, _label_start(text, start), start) is not None


def business_label_before(text: str, start: int) -> bool:
    """Libellé commercial juste avant `start` (même ligne), sans libellé personnel plus près / a business label right
    before, same line, with no nearer personal label."""
    lo = _label_start(text, start)
    business = _BUSINESS_LABEL_BEFORE.search(text, lo, start)
    if business is None:
        return False
    personal = _PERSONAL_LABEL_BEFORE.search(text, lo, start)
    return personal is None or business.start() >= personal.start()


@cache
def _switched_off(mode: str, disable: tuple[str, ...]) -> frozenset[str]:
    """`Gate.off` : catégories coupées ; téléphones coupés, fragments aussi / phones off, fragments too."""
    off = frozenset(ESSENTIEL_OFF if mode == "essentiel" else disable)
    return off | _WITH_PHONES if "telephones" in off else off


def _rule(span: Any) -> str:
    source = span.source.split("+", 1)[0]
    return source.split(":", 1)[1] if source.startswith("propagated:") else source


@dataclass(frozen=True, slots=True)
class Gate:
    """Porte du mode : quelles zones détectées le mode laisse en clair / which detected spans the mode leaves in clear.

    `active` : faux en mode fort (rien n'est coupé, le moteur fusionné reste en service). `post_entities` : entités
    que la finalisation peut créer sans zone source (civilités, initiales, signatures) et que le mode coupe aussi
    après elle. `active`: false in mode fort (nothing switched off). `post_entities`: entities finalisation can create
    without a source span, also removed after it.
    """

    mode: str = DEFAULT_MODE
    disable: tuple[str, ...] = ()

    @property
    def off(self) -> frozenset[str]:
        """Catégories coupées / categories switched off.

        Téléphones coupés : leurs fragments aussi (la fin d'un numéro laissé en clair n'est pas masquée à part ;
        revue du 26/10, voie perf). Phones switched off: their fragments too. Calculé une fois par réglage (lu à
        chaque zone) / computed once per setting (read for every span).
        """
        return _switched_off(self.mode, self.disable)

    @property
    def active(self) -> bool:
        return self.mode == "essentiel" or bool(self.disable)

    def allows(self, category: str) -> bool:
        """La catégorie est-elle active dans ce mode ? Toute règle ajoutée après la détection (contrôle de sortie,
        propagation d'une famille) la consulte. Is the category on in this mode? Any rule added after detection
        (output self-check, a family's propagation) asks it."""
        return category not in self.off

    @property
    def post_entities(self) -> frozenset[str]:
        return frozenset({"PERSON"}) if "personnes" in self.off else frozenset()

    def category(self, span: Any, text: str) -> str | None:
        """Catégorie d'une zone détectée, ou None (masquée dans tous les modes) / a detected span's category."""
        rule = _rule(span)
        own = _RULE_CATEGORY.get(rule)
        if own is not None:
            return own
        if span.entity == "EMAIL" and functional_mailbox(text[span.start:span.end]):
            return "boites_fonctionnelles"
        return _ENTITY_CATEGORY.get(span.entity)

    def left_in_clear(self, span: Any, text: str) -> str | None:
        """Catégorie qui laisse la zone en clair dans ce mode, ou None si elle reste masquée.

        Category that leaves the span in clear in this mode, or None when it stays masked. Règles de l'organisation
        (règles, listes) jamais coupées ; en essentiel, un code ou un nombre long après un libellé personnel reste
        masqué, et « @pseudo » sans indice reste en clair. The organisation's rules are never switched off; in
        essentiel a code or long number after a personal label stays masked, an "@handle" without a cue stays in clear.
        """
        rule = _rule(span)
        if rule.startswith(("CUSTOM_", "keep:")) or rule == "deny_list" or span.entity in ("CUSTOM", "_KEEP"):
            return None
        category = self.category(span, text)
        if rule in _LABEL_RULES and business_label_before(text, span.start):
            # Numéro de facture, de commande… : un code, jamais un libellé personnel / an invoice or order number: a
            # code, never a personal label.
            value = text[span.start:span.end]
            category = "nombres_longs" if value.isdigit() else "codes"
        elif category in ("codes", "nombres_longs"):
            # Code ou nombre annoncé par un libellé personnel : un identifiant annoncé (fort et essentiel) ; forme de
            # plaque SIV (« ZZ-000-ZZ ») : une plaque. A code or number announced by a personal label: an announced
            # identifier (fort and essentiel); a SIV plate shape: a plate.
            if personal_label_before(text, span.start):
                category = "identifiants_techniques"
            elif _SIV_SHAPE.fullmatch(text, span.start, span.end):
                category = "plaques"
        if self.mode == "essentiel" and rule in _FORT_ONLY_RULES:
            return "pseudonymes"
        return category if category in self.off else None
