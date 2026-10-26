"""Tests des packs pays et textes de référence partagés / country-pack tests and shared reference texts.

Les textes « pièges » emploient des mots qui ressemblent aux indices d'autres pays (BCE, AVS, RCI…) :
le mode auto ne doit activer aucun pack sur ces seuls mots.
The "trap" texts use words that look like other countries' cues: auto mode must not activate any pack.
"""

from __future__ import annotations

from gdprguardian._text import fold
from gdprguardian.packs import available_packs, load_pack

# Document purement français, avec les homonymes des mots-clés belges, suisses, luxembourgeois et monégasques.
# Purely French document, with homonyms of the Belgian, Swiss, Luxembourg and Monaco keywords.
FRENCH_DOCUMENT = """\
Objet : attestation employeur — dossier de Mme Claire Martin

La société ACME SAS, immatriculée au registre du commerce et des sociétés de Lyon (RCS Lyon B 732 829 320),
TVA FR44 732829320, inscrite au registre national des entreprises, atteste que Mme Martin, matricule 4521,
numéro de sécurité sociale 2 69 05 49 588 157 80, est salariée depuis 2019. Téléphone : 06 12 34 56 78,
courriel claire.martin@exemple.fr, IBAN FR76 3000 6000 0112 3456 7890 189. Carte d'identité n° X4RTBPFW4.

Elle a accompagné son fils, suivi par une AVS (auxiliaire de vie scolaire), puis a financé sa voiture
auprès de RCI Banque. Le 3919 est le numéro national d'écoute ; la BCE a relevé ses taux directeurs.
Réunion au Palais du Luxembourg, promenade au Jardin du Luxembourg, puis week-end au Grand Prix de Monaco.
L'équipe utilise un IDE et suit les recommandations de la Suisse et de la Belgique sur le télétravail.
Code postal 69003, conseil fédéral de l'association, office du tourisme, direction du développement
économique de la métropole. Le SIREN est le numéro d'identification des entreprises ; ne communiquez jamais
votre numéro d'identification personnel (code PIN). Elle est travailleuse indépendante.
"""

# Document néerlandais des Pays-Bas : ne doit pas activer la Belgique / Netherlands Dutch, must not activate BE.
DUTCH_DOCUMENT = """\
Geachte heer De Vries, uw burgerservicenummer (BSN) 111222333 en uw KvK-nummer 12345678 zijn bijgewerkt.
Het btw-nummer NL123456789B01 en het rekeningnummer staan op de factuur. Telefoon 06 12345678,
postcode 1234 AB Amsterdam. Neem uw identiteitskaart of paspoort mee naar de afspraak.
"""

# Document allemand (Allemagne, Autriche) : ne doit pas activer la Suisse / German, must not activate CH.
GERMAN_DOCUMENT = """\
Sehr geehrte Frau Schneider, Ihre Steuer-ID und Ihre Sozialversicherungsnummer wurden aktualisiert.
Rechnung inkl. MwSt., USt-IdNr. DE123456789, UID-Nr. ATU12345678, Handelsregister Amtsgericht München.
Telefon 089 1234567, Handy 0151 23456789, Personalausweis bitte mitbringen. Kennzeichen M-AB 1234.
"""

# En mode auto, le premier pack (ordre alphabétique) qui liste un en-tête impose son libellé à tout classeur : ces
# mots, qui désignent autre chose ailleurs, n'ont rien à faire dans le lexique d'un pack pays.
# In auto mode the first pack (alphabetical order) listing a header labels every workbook's column with it: these
# words mean something else elsewhere, so no country pack may list them.
GENERIC_HEADERS = frozenset({
    "matricule", "matrikelnummer", "numéro d'identification", "n° d'identification", "identifiant national",
    "sozialversicherungsnummer", "versichertennummer", "unternehmensnummer", "ide", "idi", "uid", "uid-nr", "eid",
    "kaartnummer", "kennzeichen",
})


def foreign_header_conflicts(pack_id: str) -> dict[str, str]:
    """En-têtes du pack qu'un autre pack range sous un autre libellé / headers another pack labels differently."""
    own = {fold(word): label for label, words in load_pack(pack_id).headers.items() for word in words}
    conflicts: dict[str, str] = {}
    for other_id in available_packs():
        if other_id == pack_id:
            continue
        for label, words in load_pack(other_id).headers.items():
            for word in words:
                mine = own.get(fold(word))
                if mine is not None and mine != label:
                    conflicts[fold(word)] = f"{pack_id}:{mine} / {other_id}:{label}"
    return conflicts
