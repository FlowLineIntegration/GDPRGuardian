"""Manifestes de valeurs plantées pour le corpus d'évaluation / planted-value manifests for the eval corpus.

Chaque manifeste fixe ce qu'un document doit contenir : personnes (et formes autorisées), identifiants
VALIDES (calculés ici, jamais par un LLM), adresses réelles, et leurres qui ne doivent PAS être masqués.
Each manifest fixes what a document must contain: persons (and allowed forms), VALID identifiers
(computed here, never by an LLM), real addresses, and decoys that must NOT be masked.

Usage : python tools/corpus/make_manifests.py --count 360 --seed 2026 --out datasets/fr/manifests.jsonl
"""

from __future__ import annotations

import argparse
import datetime
import json
import random
import string
from pathlib import Path

from faker import Faker

GENRES = (
    "e-mail professionnel", "compte rendu de réunion", "contrat de travail", "bulletin de paie (texte)",
    "facture et relance", "ticket de support client", "compte rendu d'hospitalisation", "procès-verbal de plainte",
    "entretien annuel d'évaluation", "lettre de résiliation", "conversation de messagerie (chat)",
    "curriculum vitae", "acte de vente immobilière", "décision de justice", "signalement social",
    "note de frais", "formulaire administratif (CAF, France Travail)", "transcription de message vocal",
    "tableau Markdown (liste du personnel)", "fil d'e-mails avec signatures",
)

# Couples code postal / commune réels / real postcode / commune pairs.
PLACES = (
    ("75011", "Paris"), ("69003", "Lyon"), ("13008", "Marseille"), ("31000", "Toulouse"), ("33000", "Bordeaux"),
    ("44000", "Nantes"), ("59000", "Lille"), ("67000", "Strasbourg"), ("35000", "Rennes"), ("34000", "Montpellier"),
    ("06000", "Nice"), ("38000", "Grenoble"), ("21000", "Dijon"), ("49000", "Angers"), ("37000", "Tours"),
    ("76000", "Rouen"), ("87000", "Limoges"), ("63000", "Clermont-Ferrand"), ("29200", "Brest"),
    ("20000", "Ajaccio"), ("20200", "Bastia"), ("97400", "Saint-Denis"), ("97200", "Fort-de-France"),
    ("97300", "Cayenne"), ("98000", "Monaco"), ("64000", "Pau"), ("66000", "Perpignan"), ("80000", "Amiens"),
    ("51100", "Reims"), ("57000", "Metz"), ("54000", "Nancy"), ("25000", "Besançon"), ("86000", "Poitiers"),
    ("17000", "La Rochelle"), ("74000", "Annecy"), ("73000", "Chambéry"), ("84000", "Avignon"), ("30000", "Nîmes"),
    ("83000", "Toulon"), ("72000", "Le Mans"), ("14000", "Caen"), ("56000", "Vannes"), ("22000", "Saint-Brieuc"),
    ("19100", "Brive-la-Gaillarde"), ("81000", "Albi"), ("65000", "Tarbes"), ("16000", "Angoulême"),
    ("79000", "Niort"), ("85000", "La Roche-sur-Yon"), ("45000", "Orléans"), ("42000", "Saint-Étienne"),
    ("26000", "Valence"), ("05000", "Gap"), ("71000", "Mâcon"), ("62000", "Arras"), ("78000", "Versailles"),
    ("92000", "Nanterre"), ("93000", "Bobigny"), ("94000", "Créteil"), ("95000", "Cergy"),
)
STREET_TYPES = ("rue", "avenue", "boulevard", "place", "allée", "impasse", "chemin", "quai", "route")

# Noms qui sont aussi des mots courants ou des lieux : pièges de précision / precision traps.
# (prénom, nom, sexe) / (given, surname, sex: 1 male, 2 female)
AMBIGUOUS = (("Pierre", "Blanc", 1), ("Rose", "Martin", 2), ("Marine", "Petit", 2), ("Florence", "Lebrun", 2),
             ("Olive", "Fontaine", 2), ("Victoire", "Boulanger", 2), ("Constance", "Mercier", 2),
             ("Lucie", "Roux", 2), ("Clément", "Noir", 1), ("Désiré", "Lenoir", 1))
DIVERSE = (("Mohamed", "Benali", 1), ("Thi Lan", "Nguyen", 2), ("Agnieszka", "Kowalska", 2),
           ("João", "Fernandes", 1), ("Jean-Pierre", "de La Fontaine", 1), ("Marie-Claire", "Le Gall", 2),
           ("Aïcha", "Diallo", 2), ("Grégoire", "d'Estienne", 1), ("Yanis", "Ait-Ouarab", 1),
           ("Ingrid", "van der Berg", 2))
_MONTHS = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
           "novembre", "décembre")
DECOY_TEMPLATES = (
    "commande n° CMD-{y}-{n6}", "facture FAC-{y}-{n5}", "référence produit REF-{L2}-{n4}", "{amount} €",
    "l'article L. {n4}-{d1} du Code du travail", "ticket #{n6}", "lot {L1}{n5}", "la réunion du {date}",
    "colis {L2}{n9}FR", "version {d1}.{d1}.{d1}", "salle {L1}{d1}0{d1}", "{n3} mètres carrés",
)
COMMON_WORD_DECOYS = ("la rose du jardin", "le blanc de l'œuf", "une pierre angulaire", "le petit déjeuner",
                      "à Florence en Italie", "la fontaine du parc", "le boulanger du quartier", "en avril dernier")


def _luhn_digit(body: str) -> str:
    total = 0
    for i, ch in enumerate(reversed(body)):
        d = int(ch)
        if i % 2 == 0:
            d *= 2
            d -= 9 if d > 9 else 0
        total += d
    return str((10 - total % 10) % 10)


def nir(rng: random.Random, sex_digit: int, birth: datetime.date) -> str:
    """NIR cohérent avec le sexe et la naissance ; parfois NIA (7/8) ou mois fictif / sometimes NIA or fictitious."""
    sex = str(sex_digit + 6) if rng.random() < 0.05 else str(sex_digit)
    year = birth.year % 100
    month = rng.choice([birth.month] * 18 + [rng.randint(20, 42), rng.randint(50, 99)])
    kind = rng.random()
    if kind < 0.08:
        dept, commune = rng.choice(("2A", "2B")), f"{rng.randint(1, 366):03d}"
    elif kind < 0.16:
        dept, commune = f"97{rng.randint(1, 6)}", f"{rng.randint(1, 34):02d}"
    elif kind < 0.22:
        dept, commune = "99", f"{rng.randint(100, 450):03d}"
    else:
        dept, commune = f"{rng.choice([d for d in range(1, 96) if d != 20]):02d}", f"{rng.randint(1, 900):03d}"
    body = f"{sex}{year:02d}{month:02d}{dept}{commune}{rng.randint(1, 999):03d}"
    numeric = body.replace("2A", "19").replace("2B", "18") if dept in ("2A", "2B") else body
    key = 97 - int(numeric) % 97
    raw = f"{body}{key:02d}"
    style = rng.random()
    if style < 0.6:
        return f"{raw[0]} {raw[1:3]} {raw[3:5]} {raw[5:7]} {raw[7:10]} {raw[10:13]} {raw[13:]}"
    return raw if style < 0.9 else ".".join((raw[0], raw[1:3], raw[3:5], raw[5:7], raw[7:10], raw[10:13], raw[13:]))


def siren(rng: random.Random) -> str:
    body = "".join(rng.choice(string.digits) for _ in range(8))
    return body + _luhn_digit(body)


def siret(rng: random.Random, base: str) -> str:
    body = base + "".join(rng.choice(string.digits) for _ in range(4))
    return body + _luhn_digit(body)


def tva(base: str) -> str:
    return f"FR{(12 + 3 * (int(base) % 97)) % 97:02d}{base}"


def iban_fr(rng: random.Random) -> str:
    bank, branch = f"{rng.randint(10000, 99999)}", f"{rng.randint(10000, 99999)}"
    account = "".join(rng.choice(string.digits) for _ in range(11))
    key = 97 - (89 * int(bank) + 15 * int(branch) + 3 * int(account)) % 97
    bban = f"{bank}{branch}{account}{key:02d}"
    check = 98 - int(bban + "152700") % 97
    raw = f"FR{check:02d}{bban}"
    return " ".join(raw[i:i + 4] for i in range(0, len(raw), 4))


def card(rng: random.Random) -> str:
    body = "4" + "".join(rng.choice(string.digits) for _ in range(14))
    raw = body + _luhn_digit(body)
    return " ".join(raw[i:i + 4] for i in range(0, 16, 4))


def phone(rng: random.Random) -> str:
    digits = f"0{rng.choice('67')}" + "".join(rng.choice(string.digits) for _ in range(8))
    style = rng.random()
    if style < 0.5:
        return " ".join(digits[i:i + 2] for i in range(0, 10, 2))
    if style < 0.7:
        return "+33 " + digits[1] + " " + " ".join(digits[i:i + 2] for i in range(2, 10, 2))
    return digits if style < 0.85 else ".".join(digits[i:i + 2] for i in range(0, 10, 2))


def plate(rng: random.Random) -> str:
    letters = "ABCDEFGHJKLMNPQRSTVWXYZ"
    first = rng.choice([a + b for a in letters for b in letters if a + b not in ("SS", "WW")])
    last = rng.choice([a + b for a in letters for b in letters if a + b != "SS"])
    return f"{first}-{rng.randint(1, 999):03d}-{last}"


def passport(rng: random.Random) -> str:
    return f"{rng.randint(10, 99)}{rng.choice(string.ascii_uppercase)}{rng.choice(string.ascii_uppercase)}" \
           f"{rng.randint(10000, 99999)}"


def birth_text(rng: random.Random, date: datetime.date) -> str:
    return f"{date.day} {_MONTHS[date.month - 1]} {date.year}" if rng.random() < 0.5 else date.strftime("%d/%m/%Y")


def _decoy(rng: random.Random, fake: Faker) -> str:
    template = rng.choice(DECOY_TEMPLATES)
    return template.format(
        y=rng.randint(2019, 2026), n3=rng.randint(100, 999), n4=rng.randint(1000, 9999),
        n5=rng.randint(10000, 99999), n6=rng.randint(100000, 999999), n9=rng.randint(10**8, 10**9 - 1),
        d1=rng.randint(1, 9), L1=rng.choice(string.ascii_uppercase),
        L2="".join(rng.choice(string.ascii_uppercase) for _ in range(2)),
        amount=f"{rng.randint(1, 9)} {rng.randint(100, 999)},{rng.randint(10, 99)}",
        date=fake.date_this_year().strftime("%d/%m/%Y"),
    )


def person(rng: random.Random, fake: Faker) -> dict:
    roll = rng.random()
    if roll < 0.15:
        given, surname, sex = rng.choice(AMBIGUOUS)
    elif roll < 0.3:
        given, surname, sex = rng.choice(DIVERSE)
    else:
        sex = rng.choice((1, 2))
        given = fake.first_name_male() if sex == 1 else fake.first_name_female()
        surname = fake.last_name()
    honorific = "M." if sex == 1 else "Mme"
    birth = fake.date_of_birth(minimum_age=18, maximum_age=85)
    postcode, city = rng.choice(PLACES)
    street = f"{rng.randint(1, 120)} {rng.choice(STREET_TYPES)} {fake.last_name()}"
    local = f"{given}.{surname}".lower().replace(" ", "").replace("'", "")
    return {
        "given": given,
        "surname": surname,
        "allowed_forms": [f"{given} {surname}", f"{honorific} {surname}", f"{given[0]}. {surname}",
                          f"{surname.upper()} {given}", given],
        "email": f"{local}@{rng.choice(('exemple.fr', 'mail.example', 'societe-test.fr'))}",
        "sex": "M" if sex == 1 else "F",
        "phone": phone(rng),
        "nir": nir(rng, sex, birth),
        "birth_date": birth_text(rng, birth),
        "address": f"{street}, {postcode} {city}",
        "iban": iban_fr(rng) if rng.random() < 0.5 else None,
        "card": card(rng) if rng.random() < 0.15 else None,
        "passport": passport(rng) if rng.random() < 0.15 else None,
        "plate": plate(rng) if rng.random() < 0.2 else None,
    }


def manifest(index: int, rng: random.Random, fake: Faker) -> dict:
    persons = [person(rng, fake) for _ in range(rng.randint(1, 4))]
    base = siren(rng)
    sole_trader = rng.random() < 0.3
    company = {
        "name": f"{fake.last_name()} {rng.choice(('Conseil', 'Services', 'Industries', 'Logistique', 'Santé'))}"
                f" {rng.choice(('SAS', 'SARL', 'SA', 'EURL'))}",
        "siren": base,
        "siret": siret(rng, base),
        "tva": tva(base),
        "sole_trader": sole_trader,
    }
    decoys = sorted({_decoy(rng, fake) for _ in range(rng.randint(3, 6))})
    decoys += rng.sample(COMMON_WORD_DECOYS, k=rng.randint(1, 2))
    return {"id": f"fr-{index:05d}", "genre": GENRES[index % len(GENRES)], "persons": persons,
            "company": company, "decoys": decoys}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=360)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--out", type=Path, default=Path("datasets/fr/manifests.jsonl"))
    args = parser.parse_args()
    rng = random.Random(args.seed)
    fake = Faker("fr_FR")
    Faker.seed(args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as handle:
        for index in range(args.count):
            handle.write(json.dumps(manifest(index, rng, fake), ensure_ascii=False) + "\n")
    print(f"{args.count} manifestes -> {args.out}")


if __name__ == "__main__":
    main()
