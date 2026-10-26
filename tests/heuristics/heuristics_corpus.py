"""Corpus français annoté à la main / hand-annotated French corpus.

Annotations en ligne : ``[[P:Jean Dupont]]`` pour une personne, ``[[A:12 rue de la Paix, 75002 Paris]]`` pour
une adresse. Les civilités restent hors de la zone, comme le veut le contrat des détecteurs. Les documents
de ``NEGATIVES`` ne contiennent aucune personne ni adresse : toute détection y est un faux positif.
Inline annotations; honorifics stay outside spans. ``NEGATIVES`` contain no person and no address.
"""

from __future__ import annotations

import re

_TAG_RE = re.compile(r"\[\[([PA]):(.+?)\]\]", re.DOTALL)
ENTITIES = {"P": "PERSON", "A": "ADDRESS"}

POSITIVES = [
    # Courriel professionnel / business e-mail
    """Objet : Relance du dossier 2024-118

Bonjour [[P:Pierre]],

Suite à notre réunion avec Mme [[P:Claire Martin-Dubois]] et M. [[P:Bernard Lefèvre]], je te confirme que
le contrat sera signé jeudi. M. [[P:Lefèvre]] souhaite recevoir les annexes avant mercredi.

Bien cordialement,
[[P:Sophie Garnier]]
Responsable juridique
""",
    # Compte rendu / meeting minutes
    """Compte rendu de la réunion du 12 mars 2025

Présents : [[P:Jean Dupont]], [[P:Marie Curie]], [[P:Paul Martin]] et [[P:Rose Petit]].
Excusés : MM. [[P:Durand]] et [[P:Blanc]].

[[P:Jean Dupont]] ouvre la séance. Il rappelle que le budget a été validé en conseil. [[P:Marie]] présente
les chiffres du trimestre ; M. [[P:Durand]] demande des précisions sur les frais de déplacement.
""",
    # Courrier administratif / administrative letter
    """Madame, Monsieur,

Nous accusons réception du courrier de M. [[P:Ahmed Benali]], domicilié au [[A:18 avenue Victor Hugo, 69006 Lyon]],
concernant le remboursement de ses frais médicaux. Le dossier est suivi par Mme [[P:Nathalie Roux]].

Veuillez agréer, Madame, Monsieur, l'expression de nos salutations distinguées.
""",
    # Format administratif NOM Prénom / administrative SURNAME Given format
    """Liste des bénéficiaires :
- [[P:DUPONT Jean]], né le 3 mars 1985 ;
- [[P:MARTIN Pierre]], né le 7 juillet 1990 ;
- [[P:LEFEBVRE Anne-Sophie]], née le 1er janvier 1979.
""",
    # Jugement / court decision
    """Le tribunal, après avoir entendu Maître [[P:Durand]] pour la société demanderesse et Me [[P:Laurent Girard]]
pour M. [[P:Kevin Moreau]], constate que [[P:Kevin Moreau]] ne conteste pas la créance. Le juge [[P:Renard]]
ordonne la mainlevée de la saisie. La victime, Mme [[P:Rose Bonnet]], épouse [[P:Lambert]], est absente.
""",
    # Message informel / chat message
    """Salut [[P:Léa]] ! Tu peux rappeler [[P:Enzo]] demain ? [[P:Kevin]] et [[P:Chloé]] arrivent vers 18 h.
Merci [[P:Thomas]], à plus.""",
    # Tableau Markdown / Markdown table
    """| Nom | Prénom | Service |
|---|---|---|
| [[P:DUPONT]] | [[P:Jean]] | Comptabilité |
| [[P:Bernard]] | [[P:Rose]] | Ressources humaines |
| [[P:Nguyen]] | [[P:Thi Hoa]] | Informatique |
""",
    # Signature et adresse sur plusieurs lignes / signature and multi-line address
    """Merci de votre retour.

Cordialement,
[[P:Thomas Moreau]]
Chargé d'affaires
[[A:Bât. B, 14 rue des Lilas
33000 Bordeaux]]
""",
    # Courriel avec nom d'affichage / e-mail with display name
    """De : [[P:Julien Fabre]] <julien.fabre@exemple.fr>
À : [[P:Camille Rousseau]] <camille.rousseau@exemple.fr>

Bonjour [[P:Camille]],
[[P:Julien]]""",
    # Noms internationaux / international names
    """Le consortium réunit [[P:Hans Müller]] (Berlin), [[P:Giuseppe Rossi]] (Milan), [[P:María García López]],
[[P:Krzysztof Nowak]] et [[P:Siobhán Murphy]]. Le rapport final sera rédigé par [[P:Jan de Vries]].""",
    # Particules et noms composés / particles and compound names
    """La séance est présidée par [[P:Charles de Gaulle]], en présence de [[P:Jean de La Fontaine]] et de
M. [[P:de Villepin]]. [[P:Yann Le Goff]] et [[P:Marine Le Pen]] ont été invités, ainsi que [[P:Lucas Da Silva]].""",
    # Initiales / initials
    """Rapport rédigé par [[P:J. Dupont]] et relu par [[P:A. Lambert]]. Contact : [[P:Jean-Pierre Martin]].""",
    # Adresses variées / various addresses
    """Envoyer le dossier à [[A:BP 42 - 69441 Lyon Cedex 03]] ou au siège, [[A:3 place Saint-Nicolas, 20200 Bastia]].
Le bureau de Monaco est au [[A:7 avenue de la Costa, 98000 Monaco]]. Agence de Fort-de-France :
[[A:12 rue Victor Schœlcher, 97200 Fort-de-France]].""",
    # Patient / medical letter
    """Cher confrère,

Je vous adresse Mme [[P:Isabelle Fournier]] pour avis. Mme [[P:Fournier]] présente depuis trois semaines une
toux persistante. Son fils, [[P:Lucas]], est également suivi.

Bien confraternellement,
Dr [[P:Antoine Mercier]]""",
    # Adresse sans code postal, avec contexte / street-only address with context
    """Le locataire, M. [[P:Olivier Chevalier]], demeurant [[A:7 impasse des Tilleuls]], a résilié son bail.""",
]

NEGATIVES = [
    # Titres, mois, lieux, produits, mots courants capitalisés / headings, months, places, products
    """## Rapport Annuel De La Direction Générale

Le mois d'Avril a été marqué par une hausse des ventes à Paris, à Lyon et en Bretagne. La France reste notre
premier marché, devant l'Italie (Florence, Milan) et l'Espagne. Les équipes de Nancy ont rejoint celles de Valence.""",
    """La Société Générale et le Crédit Agricole ont publié leurs résultats. Le CAC 40 progresse.
Microsoft Teams et Google Docs sont utilisés par les équipes. Le Moulin Rouge et le Mont Blanc attirent les
touristes, tout comme la tour Eiffel et l'avenue des Champs-Élysées.""",
    """Le lycée Victor Hugo et le collège Jean Moulin organisent une sortie au musée Rodin. L'hôpital
Georges Pompidou se situe rue Leblanc. La maladie de Parkinson et le syndrome de Down sont étudiés.""",
    """Monsieur le Maire, Madame la Présidente, Mesdames et Messieurs les conseillers,
Le conseil municipal se réunira le 3 juin. Rappel : la Fête de la Musique a lieu le 21 juin.""",
    """La pierre angulaire du projet, la refonte du portail, a pris du retard. Rose des vents et Marine nationale
sont des expressions courantes. Le cycle de Krebs et la loi de Moore sont au programme.""",
    """Louis XIV et Henri IV ont marqué l'histoire. Le XIXe siècle voit naître l'industrie. Voir Tableau 3 et
Annexe B. Article 12 : les parties conviennent de ce qui suit.""",
    """Il a payé 10000 euros en 2024 pour 15000 litres. Le code 75001 n'est pas une adresse ici.""",
    """Sommaire
1. Introduction
2. Contexte et Enjeux
3. Méthodologie Générale
4. Conclusion""",
]


def parse(document: str) -> tuple[str, list[tuple[str, int, int]]]:
    """Texte nettoyé et zones attendues (entité, début, fin) / clean text and expected spans."""
    parts: list[str] = []
    expected: list[tuple[str, int, int]] = []
    cursor = 0
    length = 0
    for m in _TAG_RE.finditer(document):
        before = document[cursor:m.start()]
        parts.append(before)
        length += len(before)
        value = m.group(2)
        expected.append((ENTITIES[m.group(1)], length, length + len(value)))
        parts.append(value)
        length += len(value)
        cursor = m.end()
    parts.append(document[cursor:])
    return "".join(parts), expected
