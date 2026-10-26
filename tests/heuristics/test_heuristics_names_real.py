"""Noms : formes relevées sur des documents français réels, ici avec des noms inventés / name patterns found on
real French documents, tested on invented names (corpus BODACC, BOAMP, débats parlementaires, rule set "rules2")."""

from __future__ import annotations

import pytest

from gdprguardian import Anonymizer
from gdprguardian.scope import split_person_name

PERSON_CASES = [
    # « Prénom Le Nom » : la particule et le mot courant qui la suit forment le nom / particle + common word.
    ("M. Paul Le Verger. Merci.", ["Paul Le Verger"]),
    ("Mme Jeanne Le Coq a voté.", ["Jeanne Le Coq"]),
    ("Hugo Le Maire est venu.", ["Hugo Le Maire"]),
    # « Hugo Saint Laurent » : prénom puis nom de saint sans trait d'union / given name then a saint's name.
    ("Hugo Saint Laurent a dessiné.", ["Hugo Saint Laurent"]),
    # Étiquette de personne et prénom : « MAISON Pierre » reste une personne / a given name keeps the person.
    ("Nom : MAISON Pierre", ["MAISON Pierre"]),
    # Un seul mot inconnu après une étiquette forte reste un nom / a lone unknown word after a strong label.
    ("Nom : Testix", ["Testix"]),
    # Formulaire sur une ligne : l'étiquette suivante n'est pas une raison sociale / one-line form: the next label
    # is not a company name.
    ("Nom : Dupont Prénom : Jean", ["Dupont", "Jean"]),
    ("NOM : DUPONT PRENOM : JEAN", ["DUPONT", "JEAN"]),
    ("Nom de naissance : Dupont Nom d'usage : Martin", ["Dupont", "Martin"]),
    ("Patient : Garnier Médecin : Dr Lambert", ["Garnier", "Lambert"]),
    ("Signataire : Mercier Date : 12/10/2026", ["Mercier"]),
    ("Nom : Lefebvre Signature :", ["Lefebvre"]),
    # Forme de société hors de la valeur propre (« pour », « de », parenthèse) / company form outside the value.
    ("Signataire : Mercier pour Testivo SAS", ["Mercier"]),
    ("Représentant : Durand, gérant de TESTIVO SARL", ["Durand"]),
    # Prénom et nom après un code postal qui n'annonce pas sa commune / given name and surname after a postcode.
    ("Matricule 75012 Sophie Martin", ["Sophie Martin"]),
    ("Tél. 0612345678 – 75012 Sophie Martin", ["Sophie Martin"]),
    ("Réf. 10100 Marie Dupont", ["Marie Dupont"]),
    # Initiale sans point après un nom inconnu, sous un indice ou en capitales / dotless initial.
    ("Présents : Testarossi P, Brakvoort T", ["Testarossi P", "Brakvoort T"]),
    ("Relevé : MBAPPA K", ["MBAPPA K"]),
    # Civilité puis nom à particule capitalisée / honorific then a capitalised particle surname.
    ("M. Le Verger, M. Le Goff et Mme De Testval.", ["Le Verger", "Le Goff", "De Testval"]),
]

NO_PERSON_CASES = [
    # Lettre de série après un mot inconnu / series letter after an unknown word.
    "Référence de publication : Bodacc B n° 99 du 01/01/2026",
    "Annonce n° 1 du BODACC B n° 20260001",
    # « Saint X » sans trait d'union : un lieu / a place.
    "n° RCS : 123 456 782 RCS Saint Etienne",
    "Adresse : SAINT QUENTIN",
    # Commune après un code postal connu / town after a known postcode.
    "Adresse : 30600 VAUVERT",
    # Valeur d'étiquette qui est une organisation / a field value that is an organisation.
    "Nom complet : Ville de Testville",
    "Nom complet : Syndicat des Eaux de Testville",
    "Nom complet : TESTIX ESPACES VERTS",
    # « Nom commercial » : nom d'autre chose / the name of something else.
    "Nom commercial : Testix Services",
    # « Nom : TESTIX INDUSTRIES » : raison sociale, aussi avant une valeur sans étiquette / a company name.
    "Nom : TESTIX INDUSTRIES",
    "Signataire : Testivo SAS, Lyon",
    # La commune d'un code postal, même homonyme d'un prénom / the town of a postcode, even a given-name homonym.
    "Code postal : 80300 Albert Cedex",
    "Adresse : 3 rue des Essais, 97400 Saint Denis",
    # Types de document et signe de numéro / document types and the number sign.
    "AVENANT N° 2",
    "DEVIS N° 112",
    "Objet : Avenant n° 2 au contrat de maintenance",
    "Avenant\n\nLe présent avenant modifie l'article 4.",
    "Bordereau",
]


@pytest.fixture(scope="module")
def fr() -> Anonymizer:
    return Anonymizer(countries="FR")


@pytest.mark.parametrize(("text", "expected"), PERSON_CASES)
def test_real_name_patterns(fr: Anonymizer, text: str, expected: list[str]) -> None:
    assert [text[s.start:s.end] for s in fr.analyze(text).spans if s.entity == "PERSON"] == expected


@pytest.mark.parametrize("text", NO_PERSON_CASES)
def test_real_non_person_patterns(fr: Anonymizer, text: str) -> None:
    assert [text[s.start:s.end] for s in fr.analyze(text).spans if s.entity == "PERSON"] == []


def test_particle_surname_is_propagated_whole_with_one_placeholder(fr: Anonymizer) -> None:
    out = fr.anonymize("La parole est à M. Paul Le Verger, puis M. Le Verger répond.").text
    assert out == "La parole est à M. [PERSONNE_1], puis M. [PERSONNE_1] répond."


def test_python_and_native_agree(fr: Anonymizer) -> None:
    python = Anonymizer(countries="FR", native=False)
    for text in [t for t, _ in PERSON_CASES] + NO_PERSON_CASES + [t for t, _ in _layouts()]:
        assert python.anonymize(text).text == fr.anonymize(text).text, text


_SURNAMES = ("Martin", "Bernard", "Petit", "Durand", "Moreau", "Lefebvre", "Garnier", "Mercier")
_NEXT_LABELS = ("Prénom : Jean", "Prénom(s) : Jean", "Date de naissance : 12/03/1980", "Né le : 12/03/1980",
                "Sexe : F", "Fonction : Comptable", "Service : Achats", "Téléphone : 06 12 34 56 78",
                "Adresse : 4 rue des Roses, 75011 Paris", "Nationalité : Française", "Qualité : Gérant",
                "Signature :", "Email : contact@exemple.fr", "Matricule : A1234", "Poste : Technicien")


def _layouts() -> list[tuple[str, str]]:
    """Formulaires d'une ligne, noms après un code postal, valeur avec une société / generated layouts (all names
    common French surnames, no real person)."""
    cases = [(f"{label} : {s.upper() if label.isupper() else s} {nxt}", s.upper() if label.isupper() else s)
             for label in ("Nom", "NOM", "Nom du salarié", "Patient", "Signataire") for nxt in _NEXT_LABELS
             for s in _SURNAMES[:3]]
    cases += [(f"{prefix} {code} Sophie {s}".strip(), s) for prefix in ("Matricule", "Réf.", "Badge", "N°", "")
              for code in ("75012", "69003", "13008", "33000") for s in _SURNAMES[3:6]]
    cases += [(f"{label} : {s} pour {company}", s) for label in ("Signataire", "Contact", "Nom")
              for company in ("Testivo SAS", "la société Testivo SAS", "TESTIVO S.A.S.") for s in _SURNAMES[5:]]
    return cases


@pytest.mark.parametrize("native", [True, False], ids=["native", "python"])
def test_generated_layouts_never_leave_the_surname_visible(native: bool) -> None:
    engine = Anonymizer(countries="FR", native=native)
    visible = [text for text, surname in _layouts() if surname in engine.anonymize(text).text]
    assert visible == []


@pytest.mark.parametrize(("name", "parts"), [
    ("Le Verger", (None, "Verger")),
    ("Paul Le Verger", ("Paul", "Verger")),
    ("De Testval", (None, "Testval")),
    ("Le", (None, "Le")),          # un seul mot : gardé / a single word is kept
    ("M. Van Testen", (None, "Testen")),
])
def test_leading_particle_is_not_a_given_name(name: str, parts: tuple[str | None, str]) -> None:
    assert split_person_name(name) == parts
