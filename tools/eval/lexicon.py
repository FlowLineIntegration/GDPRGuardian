"""Lexiques du générateur (faits publics, aucune donnée réelle de personne) / generator lexicons.

Les listes complètent Faker fr_FR, dont le vocabulaire de noms est petit (environ 400 noms) : un
détecteur qui apprendrait cette liste aurait un rappel gonflé. Faker's name vocabulary is small, so
these lists add particles, compound and non-European names, and surnames that are common words.
"""

from __future__ import annotations

# Prénoms supplémentaires (composés, diversité d'origines) / extra given names.
EXTRA_GIVEN_MALE = (
    "Jean-Pierre", "Jean-Baptiste", "Pierre-Louis", "Marc-Antoine", "Karim", "Mehdi", "Youssef", "Mamadou",
    "Moussa", "Thanh", "Minh", "Wei", "Dimitri", "Sacha", "Loïc", "Gaël", "Yannick", "Erwan", "Ange", "Noé",
    "Kylian", "Rayan", "Ibrahim", "Bilal", "Hugo", "Nathan", "Timothée", "Côme", "Aurélien", "Ruben", "Lino",
    "Pierre", "Florent", "Clément", "Rémi", "Thibault", "Anis", "Samir", "Paulo", "Joaquim",
)
EXTRA_GIVEN_FEMALE = (
    "Marie-Claire", "Anne-Sophie", "Marie-Hélène", "Fatima", "Aïcha", "Leïla", "Yasmine", "Fatoumata",
    "Aminata", "Linh", "Mai", "Mei", "Oksana", "Éloïse", "Maëlle", "Gwenaëlle", "Rose", "Capucine", "Inès",
    "Chloé", "Zoé", "Maëva", "Océane", "Clémence", "Bérénice", "Sarah", "Nour", "Salomé", "Héloïse",
    "Nancy", "Florence", "Paola", "Ana", "Ludivine", "Soizic", "Nolwenn", "Laure",
)
# Noms supplémentaires : particules, composés, mots courants, origines variées.
# Extra surnames: particles, compounds, common words, varied origins.
EXTRA_SURNAMES = (
    "de La Fontaine", "Le Goff", "Le Gall", "Le Bihan", "Kerjean", "Da Silva", "Dos Santos", "Ferreira",
    "N'Diaye", "Diallo", "Traoré", "Koné", "Nguyen", "Tran", "Pham", "Benali", "Haddad", "Bensaïd",
    "Belkacem", "Cherif", "Kowalski", "Nowak", "Schmitt", "Muller", "Martin-Dubois", "Lambert-Roux",
    "Petit", "Blanc", "Boulanger", "Marchand", "Fournier", "Rousseau", "Chevalier", "Lebrun", "Moreau",
    "Lefèvre", "Mercier", "Dupuis", "Pierre", "Vidal", "Leclerc", "Garnier", "Faure", "Rey", "Colin",
    "Benoît", "Lacroix", "Picard", "Gauthier", "Perrin", "d'Almeida", "Ould Ahmed", "Abitbol", "Cohen",
    "Santoni", "Casanova", "Pinelli", "Hoarau", "Payet", "Grondin", "Fontaine", "Morel", "Duval",
)

STREET_TYPES = ("rue", "rue", "rue", "avenue", "boulevard", "impasse", "allée", "place", "chemin", "quai",
                "route", "cours", "square")
STREET_NAMES = (
    "de la République", "Victor Hugo", "Jean Jaurès", "du Général de Gaulle", "des Lilas", "Pasteur",
    "de la Gare", "du Moulin", "des Écoles", "de l'Église", "Gambetta", "Voltaire", "Émile Zola",
    "du Château", "des Acacias", "Saint-Michel", "de Verdun", "Carnot", "Foch", "de la Paix", "des Tilleuls",
    "du Stade", "de Strasbourg", "Lamartine", "de Paris", "Saint-Martin", "Paul Bert", "des Peupliers",
    "Jules Ferry", "de la Liberté", "du 8 Mai 1945", "des Vignes", "du Port", "Anatole France",
    "de la Mairie", "des Prés", "Louis Pasteur", "Sadi Carnot", "de Bretagne", "des Cordeliers",
)
NUMBER_SUFFIXES = ("bis", "ter", "B")
COMPLEMENTS = ("Bât. B, ", "Appt 12, ", "Résidence Les Pins, ", "Escalier C, ", "3e étage, ")
LOCALITIES = ("Lieu-dit Le Moulin", "Lieu-dit La Croix Blanche", "Hameau de Bellevue", "Le Bourg")

# (ville, code postal) : faits publics / (city, postcode): public facts.
CITIES = (
    ("Paris", "75011"), ("Paris", "75015"), ("Paris", "75018"), ("Paris", "75004"), ("Marseille", "13008"),
    ("Marseille", "13001"), ("Lyon", "69003"), ("Lyon", "69007"), ("Toulouse", "31000"), ("Nice", "06000"),
    ("Nantes", "44000"), ("Montpellier", "34000"), ("Strasbourg", "67000"), ("Bordeaux", "33000"),
    ("Lille", "59000"), ("Rennes", "35000"), ("Reims", "51100"), ("Toulon", "83000"),
    ("Saint-Étienne", "42000"), ("Le Havre", "76600"), ("Grenoble", "38000"), ("Dijon", "21000"),
    ("Angers", "49000"), ("Nîmes", "30000"), ("Villeurbanne", "69100"), ("Clermont-Ferrand", "63000"),
    ("Le Mans", "72000"), ("Aix-en-Provence", "13100"), ("Brest", "29200"), ("Tours", "37000"),
    ("Amiens", "80000"), ("Limoges", "87000"), ("Perpignan", "66000"), ("Metz", "57000"),
    ("Besançon", "25000"), ("Orléans", "45000"), ("Rouen", "76000"), ("Mulhouse", "68100"), ("Caen", "14000"),
    ("Nancy", "54000"), ("Argenteuil", "95100"), ("Montreuil", "93100"), ("Saint-Denis", "93200"),
    ("Ajaccio", "20000"), ("Porto-Vecchio", "20137"), ("Bastia", "20200"), ("Corte", "20250"),
    ("Saint-Denis", "97400"), ("Saint-Pierre", "97410"), ("Fort-de-France", "97200"),
    ("Pointe-à-Pitre", "97110"), ("Cayenne", "97300"), ("Mamoudzou", "97600"), ("Annecy", "74000"),
    ("Pau", "64000"), ("La Rochelle", "17000"), ("Quimper", "29000"), ("Vannes", "56000"), ("Colmar", "68000"),
    ("Poitiers", "86000"), ("Avignon", "84000"), ("Chambéry", "73000"), ("Bayonne", "64100"),
    ("Lorient", "56100"), ("Saint-Malo", "35400"), ("Carcassonne", "11000"), ("Albi", "81000"),
    ("Laval", "53000"), ("Niort", "79000"), ("Valence", "26000"), ("Troyes", "10000"), ("Domme", "24250"),
    ("Eguisheim", "68420"), ("Locronan", "29180"), ("Gordes", "84220"), ("Conques-en-Rouergue", "12320"),
)
FOREIGN_BIRTH_CITIES = {
    "350": ("Casablanca", "Rabat", "Fès"), "352": ("Alger", "Oran", "Constantine"), "351": ("Tunis", "Sfax"),
    "109": ("Berlin", "Munich"), "134": ("Madrid", "Barcelone"), "139": ("Porto", "Lisbonne"),
    "127": ("Rome", "Naples"), "131": ("Bruxelles", "Liège"), "341": ("Dakar", "Thiès"),
    "243": ("Hanoï", "Hô Chi Minh-Ville"),
}

PERSONAL_EMAIL_DOMAINS = ("gmail.com", "orange.fr", "free.fr", "laposte.net", "outlook.fr", "sfr.fr",
                          "wanadoo.fr", "hotmail.fr", "yahoo.fr", "icloud.com", "proton.me")

# Noms d'entreprises fictifs, sans nom de famille (évite la confusion avec PERSON).
# Fictitious company names without surnames (avoids confusion with PERSON).
COMPANY_NAMES = (
    "Solutions Horizon", "Nova Conseil", "Atelier Lumière", "Transports Azur", "Bâti-Ouest", "Datalink",
    "Optique du Centre", "Imprimerie Moderne", "Les Jardins de Provence", "Cabinet Arcade", "Boulangerie des Halles",
    "Garage de la Gare", "Pharmacie du Marché", "Logistique Express", "Énergies Nouvelles", "Studio Pixel",
    "Agence Boréale", "Menuiserie Artisanale", "Clinique des Sources", "Pépinières du Val", "Alpha Sécurité",
    "Cuisines Prestige", "Ingénierie Delta", "Laboratoires Vega", "Assurances Mutuelles du Nord",
)
LEGAL_FORMS = ("SAS", "SARL", "SA", "SASU", "EURL", "SCI")
COMPANY_DOMAINS = ("entreprise.fr", "societe.com", "groupe.fr", "conseil.fr")
JOBS = ("comptable", "responsable des ressources humaines", "chef de projet", "technicien de maintenance",
        "assistante de direction", "développeur", "infirmière", "commercial", "juriste", "directeur général",
        "chargée de clientèle", "ingénieur qualité", "agent d'accueil", "consultante")
PRODUCTS = ("Maintenance annuelle", "Audit de sécurité", "Licence logicielle (12 mois)", "Formation RGPD",
            "Développement module paiement", "Câble réseau Cat. 6", "Écran 27 pouces", "Prestation de conseil",
            "Hébergement serveur", "Support niveau 2")
BICS = ("BNPAFRPPXXX", "SOGEFRPP", "CRLYFRPP", "PSSTFRPPPAR", "AGRIFRPP882", "CMCIFRPP", "CEPAFRPP751",
        "BREDFRPPXXX")
LEGAL_REFS = (
    ("L. 1234-5", " du Code du travail"), ("L1232-6", " du Code du travail"), ("L. 3141-3", " du Code du travail"),
    ("R. 4127-35", " du Code de la santé publique"), ("1240", " du Code civil"), ("1103", " du Code civil"),
    ("L. 441-10", " du Code de commerce"), ("293 B", " du CGI"), ("L. 221-18", " du Code de la consommation"),
    ("9", " du RGPD"), ("L. 1111-7", " du Code de la santé publique"), ("R. 1221-1", " du Code du travail"),
)
SYMPTOMS = ("des douleurs thoraciques à l'effort", "une dyspnée d'aggravation progressive",
            "des palpitations récidivantes", "une hypertension artérielle mal contrôlée",
            "un malaise avec perte de connaissance brève")
MONTHS = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
          "novembre", "décembre")
