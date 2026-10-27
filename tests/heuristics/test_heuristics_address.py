"""Adresses postales françaises : ancre code postal + commune, voie, boîtes postales / French postal addresses."""

from __future__ import annotations

import unicodedata

import pytest

from gdprguardian import Anonymizer
from gdprguardian.heuristics.fr_address import FrenchAddressDetector
from gdprguardian.types import PRIORITY_HEURISTIC

POSITIVES = [
    ("Il habite au 12 bis rue de la Paix, 75002 Paris depuis 2010.", ["12 bis rue de la Paix, 75002 Paris"]),
    ("Adresse : 3, avenue des Champs-Élysées\n75008 PARIS", ["3, avenue des Champs-Élysées\n75008 PARIS"]),
    ("Envoyer à BP 42 - 69441 Lyon Cedex 03.", ["BP 42 - 69441 Lyon Cedex 03"]),
    ("Courrier : CS 70001 - 75381 Paris Cedex 08", ["CS 70001 - 75381 Paris Cedex 08"]),
    ("Siège : 1 cours Napoléon, 20000 Ajaccio ; agence : BP 12, 20200 Bastia.",
     ["1 cours Napoléon, 20000 Ajaccio", "BP 12, 20200 Bastia"]),
    ("Bureau : 7 avenue de la Costa, 98000 Monaco.", ["7 avenue de la Costa, 98000 Monaco"]),
    ("Agence : 12 rue Victor Schœlcher, 97200 Fort-de-France.", ["12 rue Victor Schœlcher, 97200 Fort-de-France"]),
    ("Livraison au 5 rue de Paris, 97400 Saint-Denis.", ["5 rue de Paris, 97400 Saint-Denis"]),
    # Lieux-dits, boîtes, adjectifs, casse mêlée, Cédex accentué / named places, boxes, adjectives, mixed case.
    ("Adresse : 2 la Testière 50700 Saussemesnil", ["2 la Testière 50700 Saussemesnil"]),
    ("Adresse : La Testière 16570 Marsac", ["La Testière 16570 Marsac"]),
    ("| Adresse | Le Bourg, 20250 Corte |", ["Le Bourg, 20250 Corte"]),
    ("M. Paul Essai\nLe Bourg\n29200 Brest\nTél.", ["Le Bourg\n29200 Brest"]),
    ("Livré à l'adresse Le Bourg, 66000 Perpignan.", ["Le Bourg, 66000 Perpignan"]),
    ("Adresse : 14 grande rue 92350 Le Plessis-Robinson", ["14 grande rue 92350 Le Plessis-Robinson"]),
    ("Adresse : 6 Boulevard Paul et Jeanne Essai 05000 Gap", ["6 Boulevard Paul et Jeanne Essai 05000 Gap"]),
    ("Adresse : 29 rue du lieutenant Testeur, 57400 Sarrebourg", ["29 rue du lieutenant Testeur, 57400 Sarrebourg"]),
    ("Adresse : BP2031 - 17 rue Paul Essai, 97488 Saint-Denis Cédex",
     ["BP2031 - 17 rue Paul Essai, 97488 Saint-Denis Cédex"]),
    ("Adresse : ZAC des Essais - 4 rue du Verger, 57530 Ars-Laquenexy",
     ["ZAC des Essais - 4 rue du Verger, 57530 Ars-Laquenexy"]),
    ("Adresse : 6 rue de Testval, VOUZIERS", ["6 rue de Testval, VOUZIERS"]),
    ("Il habite au 35 allée des Essais\n– 59000 Lille.", ["35 allée des Essais\n– 59000 Lille"]),
    ("Adresse : 5 Contour des Essais CS 41234, 35044 Rennes cedex",
     ["5 Contour des Essais CS 41234, 35044 Rennes cedex"]),
    ("Monsieur Paul Essai\n15 rue des Essais\nAppartement 12 Escalier 3 Etage 2\n44300 NANTES",
     # 1.0.2 (second test terrain, item C) : voie, ligne de complément et code postal en une seule zone.
     ["15 rue des Essais\nAppartement 12 Escalier 3 Etage 2\n44300 NANTES"]),
    ("Bât. B, Résidence Les Lilas, 5 allée des Roses 13008 Marseille",
     ["Bât. B, Résidence Les Lilas, 5 allée des Roses 13008 Marseille"]),
    ("Le cabinet est au 4 place Bellecour, 69002 Lyon 2e.", ["4 place Bellecour, 69002 Lyon 2e"]),
    # Commune connue après la voie, même sans numéro : l'adresse entière / a known town after the street.
    ("Elle est domiciliée rue du Général Leclerc à Rennes.", ["rue du Général Leclerc à Rennes"]),
    ("Le locataire, demeurant 7 impasse des Tilleuls, a résilié son bail.", ["7 impasse des Tilleuls"]),
    ("Il habite 8 rue du 8 Mai 1945, 01000 Bourg-en-Bresse.", ["8 rue du 8 Mai 1945, 01000 Bourg-en-Bresse"]),
    ("Appartement 12\n3 rue des Lilas\n33000 Bordeaux", ["Appartement 12\n3 rue des Lilas\n33000 Bordeaux"]),
    # Code postal sans commune juste après la voie / postcode without a commune right after the street.
    ("Le colis est au 40 avenue de la Grande Armée 75017.", ["40 avenue de la Grande Armée 75017"]),
    # Ligne d'adresse : segments avant le code postal, voie en minuscules ou sans numéro, boîte avec Cedex.
    # Address line: chunks before the postcode, lowercase or unnumbered street, box with Cedex.
    ("Adresse : Rue des prés, 38000 Grenoble", ["Rue des prés, 38000 Grenoble"]),
    # Champ « Adresse : » (1.0.1) : toute la valeur, bâtiment compris / the whole value, building included.
    ("Adresse : Gymnase Essai, rue des Essais, 38000 Grenoble", ["Gymnase Essai, rue des Essais, 38000 Grenoble"]),
    ("Adresse : BP 71234 Cedex 02, 49000 ANGERS", ["BP 71234 Cedex 02, 49000 ANGERS"]),
    ("Adresse : CS 41234,, 60200 Compiègne cedex", ["CS 41234,, 60200 Compiègne cedex"]),
    ("Adresse : 18-20 Viaduc Essai, 54000 Nancy Cedex", ["18-20 Viaduc Essai, 54000 Nancy Cedex"]),
    ("Jean Essai, rue des prés - 38000 Grenoble", ["rue des prés - 38000 Grenoble"]),
    # Segment sans mot d'adresse : code postal et commune masqués seuls / no address word: postcode and town only.
    ("Livré chez un voisin, 33000 Bordeaux.", ["33000 Bordeaux"]),
    # Ligne longue (prose) : fenêtre de 80 caractères, le mot de domicile suffit / long line: the home word suffices.
    ("> Commande 12345678, colis 1L00000000000, toujours pas livré à l'adresse Le Bourg, 66000 PERPIGNAN. Merci.",
     ["Le Bourg, 66000 PERPIGNAN"]),
    # Code postal et commune d'un domicile : masqués / postcode and town of a home: masked.
    ("Mme Claire Essai, domiciliée à 69003 Lyon.", ["69003 Lyon"]),
    ("Domicile : 59000 Lille", ["59000 Lille"]),
    ("Il habite 06000 Nice.", ["06000 Nice"]),
    ("Lieu de résidence : 35000 Rennes", ["35000 Rennes"]),
    ("M. Yves Essai, demeurant à 33000 Bordeaux, est convoqué.", ["33000 Bordeaux"]),
    # Commune en plusieurs mots après la partie reconnue / the rest of a multi-word town.
    ("Adresse : 3 Avenue de la Testière, 30660 Gallargues le Monteux Code nuts : FR",
     ["3 Avenue de la Testière, 30660 Gallargues le Monteux"]),
    ("Adresse : 27 avenue du Président Essai, 93211 SAINT DENIS LA PLAINE CEDEX Code nuts : FR106",
     ["27 avenue du Président Essai, 93211 SAINT DENIS LA PLAINE CEDEX"]),
    ("Adresse : 12 Boulevard Paul Essai, 92110 Clichy-La-Garenne Tél : 01 00 00 00 00",
     ["12 Boulevard Paul Essai, 92110 Clichy-La-Garenne"]),
]

NEGATIVES = [
    "Il a payé 10000 euros en 2024 pour 15000 litres.",
    "Le code 75001 seul n'est pas une adresse.",
    "Au cours de l'année, la mise en place de la réforme a pris du retard.",
    "Rendez-vous place de la Concorde pour le défilé.",
    "Il a suivi 2 cours de mathématiques et 3 cours de physique.",
    "La référence 12345 Dupont n'est pas un code postal valide.",
    "Version 2.0 du 13008 au 13010.",
    # Code postal et ville seuls : conservés (REGLES.md § 2) / postcode and town alone are kept.
    "Siège : 20000 Ajaccio ; agence : 20200 Bastia.",
    "Livraison au 97400 Saint-Denis.",
    "Rendez-vous à Lyon (69003) demain.",
    "Adresse : 75017 PARIS",
    "Adresse : , 75017 PARIS",
    "Cordialement\n29200 Brest",
    "Il y a 3 jours La Testière 16570 Marsac",
    # Une personne ou une société sur la ligne précédente n'est pas un lieu-dit / a person or a company on the
    # previous line is not a named place.
    "Claire Dubois\n69003 Lyon",
    "CLAIRE DUBOIS\n69003 LYON",
    "Destinataire :\nPaul Garnier\n33000 Bordeaux",
    "TESTIVO SAS\n69003 Lyon",
    # « Adresse : » seule n'est pas un domicile (adresses d'organismes) ; mot de domicile d'une autre phrase.
    # "Adresse :" alone is not a home (organisations' addresses); a home word from another sentence.
    "Adresse : 69003 Lyon",
    "Il a longtemps habité ailleurs. 06000 Nice reste sa ville.",
]


@pytest.mark.parametrize(("text", "expected"), POSITIVES)
def test_true_positives(found, text, expected):
    assert found(text, "ADDRESS") == expected


@pytest.mark.parametrize("text", NEGATIVES)
def test_hard_negatives(found, text):
    assert found(text, "ADDRESS") == []


def test_whole_address_becomes_one_placeholder(fr):
    out = fr.anonymize("Mme Durand, 12 rue de la Paix, 75002 Paris, et M. Petit, 12 rue de la Paix, 75002 Paris.")
    assert out.text == "Mme [PERSONNE_1], [ADRESSE_1], et M. [PERSONNE_2], [ADRESSE_1]."


def test_street_named_after_a_person_is_not_a_person(fr):
    out = fr.anonymize("Le siège est au 10 boulevard Jean Jaurès, 92100 Boulogne-Billancourt.").text
    assert out == "Le siège est au [ADRESSE_1]."


def test_span_contract(context):
    detector = FrenchAddressDetector(None)
    ctx = context("Envoyer au 12 rue de la Paix, 75002 Paris.")
    (span,) = detector.detect(ctx)
    assert (span.entity, span.label, span.priority) == ("ADDRESS", "ADDRESS", PRIORITY_HEURISTIC)
    assert ctx.text[span.start:span.end] == "12 rue de la Paix, 75002 Paris"


def test_segments_are_never_crossed():
    cells = ["12 rue de la Paix", "75002 Paris", "Lyon"]
    per_cell, _ = Anonymizer(countries="FR").analyze_segments(cells)
    # « 75002 Paris » seul dans sa cellule : code postal et ville seuls, conservés / postcode and town alone, kept.
    assert [[cells[i][s.start:s.end] for s in spans if s.entity == "ADDRESS"] for i, spans in enumerate(per_cell)] \
        == [["12 rue de la Paix"], [], []]


def test_windows_line_endings(found):
    text = "Bât. B\r\n3 rue des Lilas\r\n33000 Bordeaux"
    assert found(text, "ADDRESS") == [text]


def test_decomposed_unicode_address_is_whole(found):
    # Texte NFD : le nom de voie entier, diacritiques compris / NFD text: the whole street name, marks included.
    text = unicodedata.normalize("NFD", "Il habite 12 rue de la République, 69002 Lyon depuis 2010.")
    assert found(text, "ADDRESS") == [unicodedata.normalize("NFD", "12 rue de la République, 69002 Lyon")]


def test_no_digit_no_cue_is_skipped_cheaply(context):
    assert FrenchAddressDetector(None).detect(context("Bonjour, rien à signaler aujourd'hui.")) == []


def test_name_line_above_a_town_stays_a_person(fr):
    out = fr.anonymize("Claire Dubois\n69003 Lyon\n\nObjet : candidature\n\nDubois a travaillé chez Testivo.").text
    assert out == "[PERSONNE_1]\n69003 Lyon\n\nObjet : candidature\n\n[PERSONNE_1] a travaillé chez Testivo."


@pytest.mark.parametrize(("text", "reason"), [
    ("Siège : 3 rue des Essais, 69003 Lyon", "postcode_and_town"),
    ("Il habite 6 rue des Essais, Vouziers.", "street_and_number"),
    ("Le colis est au 40 avenue de la Grande Armée 75017.", "street_and_number"),
    ("Nous habitons Petite Route de la Gare.", "street_after_home_word"),
])
def test_explain_gives_the_address_rule_reason(text, reason):
    for native in (True, False):
        explain = Anonymizer(countries="FR", explain=True, native=native).anonymize(text).report["explain"]
        assert [(line["rule"], line["reason"]) for line in explain] == [("FR_ADDRESS", reason)], native


def test_explain_gives_the_address_field_rule():
    # Champ « Adresse : » (1.0.1) : toute la valeur de la ligne, une seule règle / the whole line value, one rule.
    for native in (True, False):
        explain = Anonymizer(countries="FR", explain=True, native=native).anonymize(
            "Adresse : 3 rue des Essais, 69003 Lyon").report["explain"]
        assert [line["rule"] for line in explain] == ["FR_ADDRESS_FIELD"], native


@pytest.mark.parametrize("native", [True, False], ids=["native", "python"])
def test_lone_postal_box_needs_capitals_and_no_year(native: bool) -> None:
    # Boîte postale seule : en capitales, pas une année ; sous 5 chiffres, un code postal ou CEDEX voisin.
    # A lone postal box: capitals, not a year; under 5 digits, a nearby postcode or CEDEX.
    an = Anonymizer(countries="FR", native=native)

    def boxes(text: str) -> list[str]:
        return [text[s.start:s.end] for s in an.analyze(text).spans if s.entity == "ADDRESS"]

    for text in ("Le budget BP 2024 a été voté, BP 2025 à venir.", "Le compte CS 1500 est soldé.",
                 "Le compte CS2024 est soldé.", "Référence BP123 du dossier.", "Envoyer en bp 61336 merci."):
        assert boxes(text) == [], text
    assert boxes("Écrire au CS61336, merci.") == ["CS61336"]
    assert "BP 123" not in an.anonymize("Écrire au BP 123, service courrier\nTestville CEDEX").text
