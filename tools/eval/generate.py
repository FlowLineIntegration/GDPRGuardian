"""Générateur déterministe de corpus français annoté / deterministic annotated French corpus generator.

Chaque document est rendu à partir d'un gabarit ; les positions des zones sont donc exactes par
construction. Une graine par document (dérivée de la graine globale) : le document i est identique
quelle que soit la taille du corpus.
Each document is rendered from a template, so span offsets are exact by construction. One seed per
document (derived from the global seed): document i is the same whatever the corpus size.

Usage : python -m tools.eval.generate --docs 500 --seed 2026 --out benchmarks/corpus/synthetic.jsonl
"""

from __future__ import annotations

import argparse
import string
import sys
import unicodedata
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import date
from functools import cached_property
from pathlib import Path
from random import Random

if __package__ in (None, ""):  # lancé comme script / run as a script
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from faker import Faker
from tools.eval import ids, lexicon
from tools.eval.schema import GOLD_LABELS, Document, GoldSpan, write_jsonl
from tools.eval.templates import ENGLISH_TEMPLATES, KINDS, TEMPLATES

DEFAULT_SEED = 20261024
CORSICA_SPLIT_YEAR = 1976  # NIR des natifs de Corse : « 20 » avant, 2A/2B ensuite / "20" before, 2A/2B after
_FORMATTER = string.Formatter()


@dataclass(frozen=True, slots=True)
class Mention:
    """Valeur annotée produite par un champ de gabarit / annotated value produced by a template field."""

    text: str
    label: str
    entity: str  # clé d'entité locale au document / document-local entity key


Piece = str | Mention


def _pick(rng: Random, weights: dict[str, float]) -> str:
    return rng.choices(tuple(weights), tuple(weights.values()))[0]


def _slug(value: str) -> str:
    """Partie locale d'adresse e-mail : ASCII minuscule / e-mail local part: lowercase ASCII."""
    ascii_text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return "".join(c for c in ascii_text.lower() if c.isalnum() or c == "-")


def _initials(given: str) -> str:
    """« Jean-Pierre » -> « J.-P. »."""
    return "-".join(part[0] + "." for part in given.split("-") if part)


def dept_of(postcode: str) -> str:
    """Département d'un code postal (Corse 2A/2B, DOM 97x) / department of a postcode."""
    if postcode.startswith("97"):
        return postcode[:3]
    if postcode.startswith("20"):
        return "2A" if int(postcode) < 20200 else "2B"
    return postcode[:2]


# --- Acteurs / actors ----------------------------------------------------------------------------------

# Champ de gabarit -> (libellé, clé d'entité) / template field -> (label, entity key).
PERSON_MENTIONS: dict[str, tuple[str, str]] = {
    "full": ("PERSON", "name"),
    "first": ("PERSON", "name"),
    "last": ("PERSON", "name"),
    "last_upper": ("PERSON", "name"),
    "admin": ("PERSON", "name"),
    "formal": ("PERSON", "name"),
    "initial": ("PERSON", "name"),
    "email": ("EMAIL", "email"),
    "phone": ("PHONE", "phone"),
    "landline": ("PHONE", "landline"),
    "address": ("ADDRESS", "address"),
    "address_inline": ("ADDRESS", "address"),
    "home_city": ("LOCATION", "home_city"),
    "birth_city": ("LOCATION", "birth_city"),
    "birth": ("BIRTH_DATE", "birth"),
    "birth_text": ("BIRTH_DATE", "birth"),
    "nir": ("NIR", "nir"),
    "nir13": ("NIR", "nir"),
    "iban": ("IBAN", "account"),
    "rib": ("RIB", "account"),
    "card": ("CARD", "card"),
    "siren": ("SIREN", "business"),
    "siret": ("SIRET", "business"),
    "vat": ("VAT", "business"),
    "spi": ("TAX_ID", "tax"),
    "passport": ("PASSPORT", "passport"),
    "id_card": ("ID_CARD", "id_card"),
    "plate": ("PLATE", "plate"),
    "plate_old": ("PLATE", "plate_old"),
    "rpps": ("RPPS", "rpps"),
    "caf": ("CAF", "caf"),
    "france_travail": ("FRANCE_TRAVAIL", "france_travail"),
    "ip": ("IP", "ip"),
    "customer": ("ID", "customer"),
    "ipp": ("ID", "ipp"),
    "staff_id": ("ID", "staff_id"),
    "pdl": ("ID", "pdl"),
}
PERSON_PLAIN = frozenset({"civ", "civ_long", "e", "ne", "il_cap", "his", "his_cap", "him", "job"})


class Person:
    """Personne fictive ; chaque attribut est tiré à la première lecture puis figé.

    Fictitious person; each attribute is drawn on first access, then frozen (repeated mentions match).
    """

    def __init__(self, key: str, rng: Random, fake: Faker) -> None:
        self.key = key
        self._rng = rng
        self._fake = fake

    def pieces(self, attr: str) -> list[Piece]:
        if attr in PERSON_MENTIONS:
            label, entity = PERSON_MENTIONS[attr]
            return [Mention(getattr(self, attr), label, f"{self.key}.{entity}")]
        if attr in PERSON_PLAIN:
            return [getattr(self, attr)]
        if attr == "rib_split":
            return self.rib_split()
        raise KeyError(f"champ de personne inconnu / unknown person field: {attr}")

    # Identité / identity
    @cached_property
    def female(self) -> bool:
        return self._rng.random() < 0.5

    @cached_property
    def first(self) -> str:
        extra = lexicon.EXTRA_GIVEN_FEMALE if self.female else lexicon.EXTRA_GIVEN_MALE
        if self._rng.random() < 0.3:
            return self._rng.choice(extra)
        return self._fake.first_name_female() if self.female else self._fake.first_name_male()

    @cached_property
    def last(self) -> str:
        return self._rng.choice(lexicon.EXTRA_SURNAMES) if self._rng.random() < 0.35 else self._fake.last_name()

    @property
    def full(self) -> str:
        return f"{self.first} {self.last}"

    @property
    def last_upper(self) -> str:
        return self.last.upper()

    @property
    def admin(self) -> str:
        return f"{self.last_upper} {self.first}"

    @property
    def formal(self) -> str:
        return f"{self.first} {self.last_upper}"

    @property
    def initial(self) -> str:
        # « M. Dupont » serait lu comme une civilité : prénom complet / "M." reads as an honorific.
        initials = _initials(self.first)
        return f"{self.first if initials == 'M.' else initials} {self.last}"

    # Accords et civilités (texte simple) / agreement and honorifics (plain text)
    @property
    def civ(self) -> str:
        return "Mme" if self.female else "M."

    @property
    def civ_long(self) -> str:
        return "Madame" if self.female else "Monsieur"

    @property
    def e(self) -> str:
        return "e" if self.female else ""

    @property
    def ne(self) -> str:
        return "née" if self.female else "né"

    @property
    def il_cap(self) -> str:
        return "Elle" if self.female else "Il"

    @property
    def his(self) -> str:
        return "her" if self.female else "his"

    @property
    def his_cap(self) -> str:
        return "Her" if self.female else "His"

    @property
    def him(self) -> str:
        return "her" if self.female else "him"

    @cached_property
    def job(self) -> str:
        return self._rng.choice(lexicon.JOBS)

    # Naissance / birth
    @cached_property
    def birth_date(self) -> date:
        return ids.random_date(self._rng, date(1946, 1, 1), date(2004, 12, 31))

    @cached_property
    def birth_country(self) -> str | None:
        """Code pays INSEE si né(e) à l'étranger / INSEE country code when born abroad."""
        return self._rng.choice(tuple(ids.BIRTH_COUNTRIES)) if self._rng.random() < 0.12 else None

    @cached_property
    def _birth_place(self) -> tuple[str, str]:
        if self.birth_country is not None:
            return self._rng.choice(lexicon.FOREIGN_BIRTH_CITIES[self.birth_country]), "99"
        city, postcode = self._rng.choice(lexicon.CITIES)
        return city, dept_of(postcode)

    @property
    def birth_city(self) -> str:
        return self._birth_place[0]

    @cached_property
    def birth(self) -> str:
        return ids.date_numeric(self.birth_date)

    @cached_property
    def birth_text(self) -> str:
        return ids.date_text(self.birth_date)

    @cached_property
    def nir_value(self) -> str:
        """NIR cohérent avec le sexe, la date et le lieu de naissance / NIR consistent with birth data."""
        rng = self._rng
        sex = "2" if self.female else "1"
        if self.birth_country is not None and rng.random() < 0.35:
            sex = "8" if self.female else "7"  # NIA (personne née à l'étranger) / foreign-born NIA
        elif rng.random() < 0.02:
            sex = "4" if self.female else "3"
        draw = rng.random()
        month = self.birth_date.month
        if draw < 0.03:
            month = rng.randint(20, 42)  # mois fictif / fictitious month
        elif draw < 0.06:
            month = rng.randint(50, 99)  # état civil incomplet / incomplete civil status
        dept = self._birth_place[1]
        if dept in ("2A", "2B") and self.birth_date.year < CORSICA_SPLIT_YEAR:
            dept = "20"  # Corse avant la partition de 1976 / Corsica before the 1976 split
        place = "99" + self.birth_country if self.birth_country else ids.nir_place(rng, dept)
        return ids.nir(rng, sex, self.birth_date.year, month, place)

    @cached_property
    def nir(self) -> str:
        return ids.fmt_nir(self.nir_value, _pick(self._rng, {"spaced": 0.65, "compact": 0.2, "key_apart": 0.15}))

    @cached_property
    def nir13(self) -> str:
        return ids.group(self.nir_value[:13], (1, 2, 2, 2, 3, 3))

    # Coordonnées / contact
    @cached_property
    def _home(self) -> tuple[str, str, str]:
        """(ligne voie, ligne ville, ville) / (street line, city line, city)."""
        rng = self._rng
        if rng.random() < 0.05:
            street = rng.choice(lexicon.LOCALITIES)
        else:
            number = str(rng.randint(1, 180))
            if rng.random() < 0.1:
                number += " " + rng.choice(lexicon.NUMBER_SUFFIXES)
            sep = ", " if rng.random() < 0.3 else " "
            street = f"{number}{sep}{rng.choice(lexicon.STREET_TYPES)} {rng.choice(lexicon.STREET_NAMES)}"
            if rng.random() < 0.12:
                street = rng.choice(lexicon.COMPLEMENTS) + street
        city, postcode = rng.choice(lexicon.CITIES)
        shown = city.upper() if rng.random() < 0.25 else city
        return street, f"{postcode} {shown}", city

    @property
    def address(self) -> str:
        return f"{self._home[0]}\n{self._home[1]}"

    @cached_property
    def address_inline(self) -> str:
        sep = ", " if self._rng.random() < 0.7 else " – "
        return f"{self._home[0]}{sep}{self._home[1]}"

    @property
    def home_city(self) -> str:
        return self._home[2]

    @cached_property
    def phone(self) -> str:
        rng = self._rng
        if self._home[1][:2] == "97":
            return ids.fmt_phone(ids.phone_dom(rng), _pick(rng, {"dom_intl": 0.45, "dom_local": 0.35, "spaced": 0.2}))
        styles = {"spaced": 0.45, "dots": 0.1, "compact": 0.1, "intl": 0.15, "intl_paren": 0.05,
                  "intl_compact": 0.05, "dashes": 0.05, "intl_00": 0.05}
        return ids.fmt_phone(ids.phone_fr(rng), _pick(rng, styles))

    @cached_property
    def landline(self) -> str:
        style = _pick(self._rng, {"spaced": 0.7, "dots": 0.15, "intl": 0.15})
        return ids.fmt_phone(ids.phone_fr(self._rng, mobile=False), style)

    @cached_property
    def email(self) -> str:
        rng = self._rng
        first, last = _slug(self.first), _slug(self.last)
        local = rng.choice((f"{first}.{last}", f"{first[0]}{last}", f"{first}{last}{rng.randint(1, 99)}",
                            f"{last}.{first}", f"{first}_{last}", f"{first}.{last}{rng.randint(50, 99)}"))
        if rng.random() < 0.7:
            return f"{local}@{rng.choice(lexicon.PERSONAL_EMAIL_DOMAINS)}"
        words = [w for w in rng.choice(lexicon.COMPANY_NAMES).split() if len(w) > 3]
        return f"{local}@{_slug(words[0])}-{rng.choice(lexicon.COMPANY_DOMAINS)}"

    # Banque / bank
    @cached_property
    def rib_value(self) -> str:
        return ids.rib(self._rng)

    @cached_property
    def iban(self) -> str:
        return ids.fmt_iban(ids.iban_fr(self.rib_value), _pick(self._rng, {"spaced": 0.75, "compact": 0.25}))

    @cached_property
    def rib(self) -> str:
        return ids.fmt_rib(self.rib_value, _pick(self._rng, {"spaced": 0.85, "compact": 0.15}))

    def rib_split(self) -> list[Piece]:
        """RIB présenté champ par champ (relevé d'identité bancaire) / RIB laid out field by field."""
        entity = f"{self.key}.account"
        value = self.rib_value
        fields = (("Code banque : ", value[:5]), ("\nCode guichet : ", value[5:10]),
                  ("\nN° de compte : ", value[10:21]), ("\nClé RIB : ", value[21:]))
        pieces: list[Piece] = []
        for caption, part in fields:
            pieces += [caption, Mention(part, "RIB_SPLIT", entity)]
        return pieces

    @cached_property
    def card(self) -> str:
        return ids.fmt_card(ids.card(self._rng), _pick(self._rng, {"spaced": 0.8, "compact": 0.15, "dashes": 0.05}))

    # Entrepreneur individuel / sole trader
    @cached_property
    def siren_value(self) -> str:
        return ids.siren(self._rng)

    @cached_property
    def siren(self) -> str:
        return ids.fmt_siren(self.siren_value, _pick(self._rng, {"spaced": 0.8, "compact": 0.2}))

    @cached_property
    def siret(self) -> str:
        value = ids.siret(self._rng, self.siren_value)
        return ids.fmt_siret(value, _pick(self._rng, {"spaced": 0.7, "compact": 0.3}))

    @cached_property
    def vat(self) -> str:
        style = _pick(self._rng, {"grouped": 0.5, "half": 0.2, "compact": 0.3})
        return ids.fmt_vat(ids.vat_fr(self.siren_value), style)

    # Autres identifiants / other identifiers
    @cached_property
    def spi(self) -> str:
        return ids.fmt_spi(ids.spi(self._rng), _pick(self._rng, {"spaced": 0.5, "compact": 0.5}))

    @cached_property
    def passport(self) -> str:
        return ids.passport_fr(self._rng)

    @cached_property
    def id_card(self) -> str:
        return ids.id_card_fr(self._rng)

    @cached_property
    def plate(self) -> str:
        style = _pick(self._rng, {"dashes": 0.75, "spaced": 0.15, "compact": 0.1})
        return ids.fmt_plate(ids.plate_siv(self._rng), style)

    @cached_property
    def plate_old(self) -> str:
        return ids.plate_fni(self._rng)

    @cached_property
    def rpps(self) -> str:
        return ids.rpps(self._rng)

    @cached_property
    def caf(self) -> str:
        return ids.caf_number(self._rng)

    @cached_property
    def france_travail(self) -> str:
        return ids.france_travail_id(self._rng)

    @cached_property
    def ip(self) -> str:
        return ids.ipv6(self._rng) if self._rng.random() < 0.15 else ids.ipv4(self._rng)

    @cached_property
    def customer(self) -> str:
        return ids.customer_id(self._rng)

    @cached_property
    def ipp(self) -> str:
        return str(self._rng.randint(1_000_000, 99_999_999))

    @cached_property
    def staff_id(self) -> str:
        return f"E{self._rng.randint(1, 99999):05d}"

    @cached_property
    def pdl(self) -> str:
        return ids.digits(self._rng, 14)


class Company:
    """Personne morale fictive : ses identifiants ne sont PAS personnels / legal entity, ids not personal."""

    def __init__(self, key: str, rng: Random) -> None:
        self.key = key
        self._rng = rng

    @cached_property
    def siren_value(self) -> str:
        return ids.siren(self._rng)

    @cached_property
    def _values(self) -> dict[str, str]:
        rng = self._rng
        return {
            "name": rng.choice(lexicon.COMPANY_NAMES),
            "form": rng.choice(lexicon.LEGAL_FORMS),
            "siren": ids.fmt_siren(self.siren_value, "spaced"),
            "siret": ids.fmt_siret(ids.siret(rng, self.siren_value), _pick(rng, {"spaced": 0.7, "compact": 0.3})),
            "vat": ids.fmt_vat(ids.vat_fr(self.siren_value), _pick(rng, {"grouped": 0.5, "compact": 0.5})),
        }

    def pieces(self, attr: str) -> list[Piece]:
        value = self._values[attr]
        if attr == "form":
            return [value]
        if attr == "name":
            return [Mention(value, "ORG", f"{self.key}.name")]
        return [Mention(value, "COMPANY_ID", f"{self.key}.id")]


class Decoys:
    """Valeurs non personnelles qui ressemblent à des identifiants / non-personal look-alikes."""

    def __init__(self, rng: Random) -> None:
        self._rng = rng
        self._count = 0

    def _mention(self, text: str, label: str) -> Mention:
        self._count += 1
        return Mention(text, label, f"d{self._count}")

    def pieces(self, attr: str) -> list[Piece]:
        rng = self._rng
        if attr in _DECOY_PLAIN:
            return [_DECOY_PLAIN[attr](rng)]
        if attr in _LEGAL_FIELDS:
            ref, rest = _legal(rng, attr)
            return [self._mention(ref, "LEGAL_REF"), rest]
        if attr not in _DECOY_MENTIONS:
            raise KeyError(f"leurre inconnu / unknown decoy field: {attr}")
        label, build = _DECOY_MENTIONS[attr]
        return [self._mention(build(rng), label)]


def _event_date(rng: Random) -> date:
    return ids.random_date(rng, date(2019, 1, 1), date(2026, 12, 31))


def _legal(rng: Random, attr: str) -> tuple[str, str]:
    if attr == "vat_exempt":
        return "293 B", " du CGI"
    if attr == "road_article":
        return rng.choice((("R. 413-14", " du Code de la route"), ("R. 412-6", " du Code de la route")))
    if attr == "law":
        return rng.choice((("89-462", " du 6 juillet 1989"), ("78-17", " du 6 janvier 1978"),
                           ("2014-366", " du 24 mars 2014")))
    return rng.choice(lexicon.LEGAL_REFS)


def _order_number(rng: Random) -> str:
    draw = rng.random()
    if draw < 0.25:
        return ids.luhn_order_number(rng)  # leurre difficile : ressemble à un SIREN / hard: SIREN look-alike
    if draw < 0.6:
        return f"CMD-{rng.randint(2019, 2026)}-{rng.randint(1, 999999):06d}"
    return str(rng.randint(1_000_000, 99_999_999))


def _invoice_number(rng: Random) -> str:
    year = rng.randint(2019, 2026)
    return rng.choice((f"FA-{year}-{rng.randint(1, 99999):05d}", f"{year}-{rng.randint(1, 9999):04d}",
                       f"F{year % 100}{rng.randint(1, 99999):05d}"))


def _product_ref(rng: Random) -> str:
    letters = "".join(rng.choices(ids.SIV_LETTERS, k=2))
    return rng.choice((f"{letters}-{rng.randint(100, 9999)}", f"X{rng.randint(10, 999)}-{rng.choice('ABCD')}",
                       f"REF{ids.digits(rng, 6)}"))


# Leurres : champ -> (libellé, fabrique) / decoys: field -> (label, factory).
_DECOY_MENTIONS: dict[str, tuple[str, Callable[[Random], str]]] = {
    "amount": ("AMOUNT", ids.amount),
    "order": ("ORDER_NUMBER", _order_number),
    "tracking": ("ORDER_NUMBER", lambda rng: f"{rng.choice(('6A', '8R', '1L'))}{ids.digits(rng, 11)}"),
    "invoice": ("INVOICE_NUMBER", _invoice_number),
    "date": ("EVENT_DATE", lambda rng: ids.date_text(_event_date(rng))),
    "date_num": ("EVENT_DATE", lambda rng: ids.date_numeric(_event_date(rng))),
    "date_iso": ("EVENT_DATE", lambda rng: ids.date_numeric(_event_date(rng), "iso")),
    "ref": ("PRODUCT_REF", _product_ref),
    "ean": ("PRODUCT_REF", ids.ean13),
    "case": ("CASE_NUMBER", lambda rng: f"{rng.randint(19, 26)}/{rng.randint(1, 99999):05d}"),
    "bic": ("BIC", lambda rng: rng.choice(lexicon.BICS)),
    "version": ("VERSION", lambda rng: f"{rng.randint(1, 12)}.{rng.randint(0, 20)}.{rng.randint(0, 9)}"),
    "ticket": ("TICKET", lambda rng: str(rng.randint(10000, 999999))),
    "finess": ("FACILITY_ID", ids.finess),
    "laposte_siret": ("COMPANY_ID", lambda rng: ids.fmt_siret(ids.siret_la_poste(rng), "spaced")),
}
_LEGAL_FIELDS = frozenset({"article", "vat_exempt", "road_article", "law"})
# Texte simple, sans annotation / plain text, not annotated.
_DECOY_PLAIN: dict[str, Callable[[Random], str]] = {
    "month": lambda rng: rng.choice(lexicon.MONTHS),
    "item": lambda rng: rng.choice(lexicon.PRODUCTS),
    "symptom": lambda rng: rng.choice(lexicon.SYMPTOMS),
    "city": lambda rng: rng.choice(lexicon.CITIES)[0],
    "hour": lambda rng: f"{rng.randint(8, 19)}h{rng.choice(('00', '15', '30', '45'))}",
    "year": lambda rng: str(rng.randint(2020, 2026)),
    "km": lambda rng: f"{rng.randint(5, 220)} {rng.randint(0, 999):03d}",
    "age": lambda rng: str(rng.randint(18, 92)),
    "kwh": lambda rng: str(rng.randint(120, 2400)),
}


# --- Rendu / rendering ----------------------------------------------------------------------------------


class Cast:
    """Acteurs d'un document, créés à la demande / a document's actors, created on demand."""

    def __init__(self, rng: Random, fake: Faker) -> None:
        self._rng = rng
        self._fake = fake
        self._actors: dict[str, Person | Company | Decoys] = {}

    def resolve(self, field_name: str) -> list[Piece]:
        actor_key, _, attr = field_name.partition(".")
        actor = self._actors.get(actor_key)
        if actor is None:
            if actor_key == "d":
                actor = Decoys(self._rng)
            elif actor_key[:1] == "p" and actor_key[1:].isdigit():
                actor = Person(actor_key, self._rng, self._fake)
            elif actor_key[:1] == "c" and actor_key[1:].isdigit():
                actor = Company(actor_key, self._rng)
            else:
                raise KeyError(f"acteur inconnu / unknown actor: {actor_key}")
            self._actors[actor_key] = actor
        return actor.pieces(attr)


def render(template: str, cast: Cast, doc_id: str) -> tuple[str, tuple[GoldSpan, ...]]:
    """Gabarit -> (texte, zones annotées) / template -> (text, gold spans)."""
    parts: list[str] = []
    spans: list[GoldSpan] = []
    position = 0
    for literal, field_name, _spec, _conversion in _FORMATTER.parse(template):
        if literal:
            parts.append(literal)
            position += len(literal)
        if field_name is None:
            continue
        for piece in cast.resolve(field_name):
            text = piece.text if isinstance(piece, Mention) else piece
            if isinstance(piece, Mention):
                spans.append(GoldSpan(position, position + len(text), piece.label, f"{doc_id}:{piece.entity}",
                                      GOLD_LABELS[piece.label]))
            parts.append(text)
            position += len(text)
    return "".join(parts), tuple(spans)


class CorpusGenerator:
    """Générateur réutilisable (une instance Faker) / reusable generator (one Faker instance)."""

    def __init__(self, seed: int = DEFAULT_SEED) -> None:
        self.seed = seed
        self._fake = Faker("fr_FR")

    def document(self, index: int, kind: str | None = None) -> Document:
        rng = Random(f"{self.seed}/{index}")
        self._fake.seed_instance(rng.getrandbits(64))
        kind = kind or KINDS[index % len(KINDS)]
        choices = TEMPLATES[kind]
        template_index = rng.randrange(len(choices))
        template = choices[template_index]
        source = template if isinstance(template, str) else template(rng)
        doc_id = f"{kind}-{index:05d}"
        text, spans = render(source, Cast(rng, self._fake), doc_id)
        language = "en" if (kind, template_index) in ENGLISH_TEMPLATES else "fr"
        doc = Document(doc_id, kind, text, spans, language, meta={"template": template_index, "seed": self.seed})
        doc.check()
        return doc

    def corpus(self, count: int, kinds: tuple[str, ...] | None = None) -> Iterator[Document]:
        """`count` documents, types en rotation équilibrée / balanced kind rotation."""
        selected = kinds or KINDS
        for index in range(count):
            yield self.document(index, selected[index % len(selected)])


def generate_corpus(count: int, seed: int = DEFAULT_SEED, kinds: tuple[str, ...] | None = None) -> list[Document]:
    return list(CorpusGenerator(seed).corpus(count, kinds))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Corpus synthétique annoté / synthetic annotated corpus (JSONL)")
    parser.add_argument("--docs", type=int, default=500)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--kinds", default=",".join(KINDS), help="types de documents / document kinds")
    parser.add_argument("--out", type=Path, default=Path("benchmarks/corpus/synthetic.jsonl"))
    args = parser.parse_args(argv)
    kinds = tuple(k.strip() for k in args.kinds.split(",") if k.strip())
    unknown = set(kinds) - set(KINDS)
    if unknown:
        parser.error(f"types inconnus / unknown kinds: {sorted(unknown)}")
    count = write_jsonl(CorpusGenerator(args.seed).corpus(args.docs, kinds), args.out)
    print(f"{count} documents -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
