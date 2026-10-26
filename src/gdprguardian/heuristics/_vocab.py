"""Vocabulaires des heuristiques (faits linguistiques, liste manuelle) / heuristic vocabularies (hand-written).

Tout est replié à l'import avec `fold` (minuscules, sans accents, longueur conservée) pour être comparé à
`ctx.folded`. Everything is folded at import with `fold` to be compared with `ctx.folded`.
"""

from __future__ import annotations

from .._text import fold


def _fold_all(*groups: str) -> frozenset[str]:
    """Une entrée par ligne ou séparée par « | » / one entry per line or separated by '|'."""
    out: set[str] = set()
    for group in groups:
        for line in group.splitlines():
            for item in line.split("|"):
                item = item.strip()
                if item:
                    out.add(fold(item))
    return frozenset(out)


# --- Civilités / honorifics ----------------------------------------------------------------------------------

HONORIFICS = _fold_all("""
    m. | mr | mr. | monsieur | mme | mme. | madame | mlle | mlle. | mademoiselle | me | me. | maître | maitre
    dr | dr. | docteur | docteure | pr | pr. | professeur | professeure | prof | prof. | mgr | mgr. | monseigneur
    père | sœur | frère | abbé | chanoine | révérend | rév.
    mm. | messieurs | mmes | mmes. | mesdames | mlles | mlles. | mesdemoiselles | drs
    mrs | mrs. | ms | ms. | miss | mx | mx. | sir | dame | lady | lord
    herr | herrn | frau | fräulein | hr. | fr.
    sr | sr. | sra | sra. | srta | srta. | don | doña | dña. | dra. | dra
    sig. | sig.ra | sig.na | signor | signora | signore | dott. | dott.ssa | avv. | ing.
    dhr. | mevr. | mevrouw | meneer
""")
# Civilités homonymes de mots courants : exigées avec une majuscule / honorifics that need a capital letter.
CASE_SENSITIVE_HONORIFICS = _fold_all("me | me. | pr | ms | don | dame | sir | lady | lord | miss | mx | fr.")

# --- Déclencheurs moyens / medium triggers ---------------------------------------------------------------------

GREETINGS = _fold_all("""
    bonjour | bonsoir | salut | coucou | hello | hi | hey | dear | cher | chère | chers | chères | très cher
    très chère | hallo | liebe | lieber | sehr geehrte | sehr geehrter | hola | estimado | estimada | querido
    querida | gentilissimo | gentilissima | ciao | buongiorno | geachte | hej | merci | bravo | félicitations
    bienvenue | welcome | thanks | thank you | grazie | gracias | danke
""")

# Formules de fin : les lignes suivantes forment un bloc de signature / closings: next lines are a signature.
CLOSINGS = _fold_all("""
    cordialement | bien cordialement | très cordialement | bien à vous | bien à toi | amicalement | amitiés
    bisous | bises | sincères salutations | salutations distinguées | meilleures salutations | respectueusement
    veuillez agréer | je vous prie d'agréer | à bientôt | bonne journée | bonne soirée | merci d'avance
    merci par avance | best regards | kind regards | warm regards | regards | best wishes | sincerely
    yours sincerely | yours faithfully | yours truly | cheers | mit freundlichen grüßen | mit freundlichen grüssen
    freundliche grüße | viele grüße | beste grüße | liebe grüße | atentamente | saludos | saludos cordiales
    un saludo | cordiali saluti | distinti saluti | un saluto | met vriendelijke groet | vriendelijke groeten
    met vriendelijke groeten | med vänliga hälsningar | pozdrawiam | z poważaniem | atenciosamente
    melhores cumprimentos | merci | merci beaucoup | merci encore | encore merci | en vous remerciant
    avec mes remerciements | dans l'attente de votre retour | dans l'attente de votre réponse | salutations
    bonne fin de journée | bonne continuation | bonne semaine | bon week-end | à plus | à demain | cdlt | bàv
    affectueusement | je t'embrasse | je vous embrasse | thanks | many thanks | thank you | best | all the best
    take care
""")

# Étiquettes de champ en début de ligne, suivies de « : » / field labels at line start, followed by ':'.
STRONG_LABELS = _fold_all("""
    nom | prénom | prénoms | nom de famille | nom d'usage | nom de naissance | nom marital | nom et prénom
    nom et prénoms | nom prénom | prénom nom | nom complet | identité | name | first name | last name | full name
    given name | family name | surname | firstname | lastname | vorname | nachname | nombre | apellido | apellidos
    nome | cognome | naam | voornaam | achternaam | patient | patiente | nom du patient | nom de la patiente
    assuré | assurée | salarié | salariée | bénéficiaire | titulaire | souscripteur | signataire | candidat
    candidate | élève | étudiant | étudiante | conjoint | conjointe | époux | épouse | enfant | nom du père
    nom de la mère | témoin | défunt | défunte | demandeur | demanderesse | défendeur | défenderesse | requérant
    requérante | prévenu | prévenue | victime | plaignant | plaignante | locataire | propriétaire | bailleur
    acquéreur | vendeur | vendeuse | acheteur | acheteuse | mandataire | tuteur | tutrice | représentant légal
    personne à contacter | personne de confiance | contact d'urgence | rédigé par | rédigée par | signé par
    signée par | auteur | autrice | auteurs | signé | signée | signature | soussigné | soussignée | pseudonyme
    nom d'épouse
""")
# Étiquettes qui commencent comme une étiquette de personne mais nomment autre chose (« Nom commercial : »).
# Labels that look like a person label but name something else ("Nom commercial :" is a trade name).
NON_PERSON_LABELS = _fold_all("""
    nom commercial | nom commerciaux | nom de domaine | nom du domaine | nom de fichier | nom du fichier
    nom de l'entreprise | nom de la société | nom de la structure | nom de l'établissement | nom de l'organisme
    nom de l'association | nom du projet | nom du produit | nom de la commune | nom de la ville | nom du site
    nom de la rue | nom de la voie | nom de voie | nom du navire | nom du lot | nom du marché | nom officiel
    nom de marque | nom de la marque | nom de code | nom de l'application
""")
# Premier mot d'une raison sociale ou d'un organisme public (« Ville de … », « Syndicat … ») : la valeur d'une
# étiquette de personne qui commence ainsi est une organisation. First word of an organisation's name.
ORG_LEADS = _fold_all("""
    société | entreprise | cabinet | association | fondation | groupe | groupement | établissement | établissements
    ets | agence | compagnie | coopérative | mutuelle | banque | syndicat | fédération | confédération | union
    laboratoire | laboratoires | holding | office | institut | centre | chambre | caisse | collectivité | commune
    ville | mairie | département | région | conseil | communauté | métropole | agglomération | préfecture
    ministère | direction | service | tribunal | cour | greffe | université | école | lycée | collège | hôpital
    clinique | ehpad | régie | maison | musée | théâtre | bibliothèque | médiathèque | parc | réseau | secrétariat
""")
WEAK_LABELS = _fold_all("""
    de | à | cc | cci | from | to | attn | attention | expéditeur | expéditrice | destinataire | destinataires
    contact | interlocuteur | interlocutrice | responsable | référent | référente | gestionnaire | conseiller
    conseillère | agent | commercial | commerciale | client | cliente | employé | employée | collaborateur
    collaboratrice | intervenant | intervenante | intervenants | participant | participante | participants
    présents | présentes | absents | excusés | invités | membres | rédacteur | rédactrice | validé par
    approuvé par | vérifié par | médecin | médecin traitant | avocat | avocate | notaire | gérant | gérante
    président | présidente | directeur | directrice | manager | superviseur | par | pour | chef de projet
    suivi par | dossier suivi par | affaire suivie par | owner | reviewer | assignee | reporter | author
    assistant | assistante | secrétaire | comptable | juriste | technicien | technicienne | stagiaire | apprenti
    apprentie | coordinateur | coordinatrice | animateur | animatrice | infirmier | infirmière | aide-soignant
    aide-soignante | éducateur | éducatrice | enseignant | enseignante | professeur | formateur | formatrice
    tuteur | tutrice | référent | référente | délégué | déléguée | représentant | représentante | correspondant
    correspondante | chargé de mission | chargée de mission | chef de service | chef d'équipe | pilote
""")

# Mots de rôle ou de parenté suivis d'un nom / role or kinship words followed by a name.
ROLES = _fold_all("""
    fils | fille | père | mère | frère | sœur | mari | femme | époux | épouse | conjoint | conjointe | compagnon
    compagne | cousin | cousine | oncle | tante | neveu | nièce | grand-père | grand-mère | petit-fils
    petite-fille | collègue | voisin | voisine | ami | amie | patron | patronne | juge | avocat | avocate
    notaire | huissier | greffier | greffière | commissaire | inspecteur | inspectrice | gendarme | brigadier
    lieutenant | capitaine | commandant | colonel | général | maréchal | adjudant | sergent | caporal | maire
    député | députée | sénateur | sénatrice | ministre | président | présidente | préfet | préfète | directeur
    directrice | secrétaire | patient | patiente | salarié | salariée | employé | employée | infirmier
    infirmière | pharmacien | pharmacienne | chirurgien | chirurgienne | médecin | défunt | défunte | prévenu
    prévenue | témoin | victime | requérant | requérante | intéressé | intéressée | sieur | nommé | nommée
    dénommé | dénommée | prénommé | prénommée | surnommé | surnommée | dit | dite | alias | née | veuve | veuf
    m'appelle | s'appelle | t'appelles | appelez-moi | je suis | my name is | ich bin | ich heiße | me llamo
    mi chiamo | rédigé par | signé par | écrit par | présenté par | validé par | approuvé par | envoyé par
    transmis par | reçu par | suivi par | géré par | représenté par | assisté par | accompagné de
    accompagné par | en présence de | à l'attention de | aux bons soins de | de la part de | remplacé par
    c/o | chez | abbé | curé | pasteur | rabbin | imam | évêque | cardinal | saint-père | soussigné | soussignée
    client | cliente | locataire | propriétaire | bailleur | bailleresse | adhérent | adhérente | bénéficiaire
    assuré | assurée | souscripteur | souscriptrice | abonné | abonnée | candidat | candidate | élève | étudiant
    étudiante | stagiaire | usager | usagère | demandeur | demandeuse | acheteur | acheteuse | vendeur | vendeuse
    interlocuteur | interlocutrice | conseiller | conseillère | technicien | technicienne | gestionnaire
    consultant | consultante | débiteur | débitrice | créancier | créancière | emprunteur | emprunteuse
    co-emprunteur | garant | garante | héritier | héritière | mandataire | utilisateur | utilisatrice
    participant | participante | résident | résidente | allocataire | contribuable | licencié | licenciée
""")

# Contexte d'éponyme : la suite nomme un lieu, une loi, une maladie, pas une personne concernée.
# Eponym context: what follows names a place, a law, a disease, not a data subject.
EPONYMS = _fold_all("""
    rue | avenue | av. | bd | boulevard | place | quai | impasse | allée | chemin | route | square | cours
    passage | esplanade | promenade | rond-point | pont | sentier | ruelle | villa | cité | résidence
    lotissement | hameau | lieu-dit | voie | faubourg | parvis | carrefour | mail | clos | quartier
    lycée | collège | école | groupe scolaire | université | faculté | institut | hôpital | clinique | polyclinique
    centre hospitalier | chu | ehpad | stade | gymnase | piscine | musée | gare | station | métro | aéroport
    salle | théâtre | cinéma | médiathèque | bibliothèque | crèche | église | cathédrale | basilique | chapelle
    paroisse | mosquée | synagogue | temple | abbaye | monastère | couvent | caserne | campus | parc | jardin
    halle | cimetière | amphithéâtre | amphi | auditorium | pavillon | bâtiment | maison de retraite | prison | palais
    maison d'arrêt | centre pénitentiaire | porte-avions | paquebot | frégate | sous-marin | tempête | ouragan
    cyclone | prix | médaille | trophée | tournoi | loi | décret | arrêt | jurisprudence | théorème | syndrome
    maladie | fondation | street | road | straße | strasse | platz | via | piazza | calle | plaza | rua | cycle
    effet | équation | constante | principe | conjecture | lemme | algorithme
""")

# Types de voie et abréviations usuelles (La Poste, AFNOR XP Z 10-011) / street types and usual abbreviations.
STREET_TYPES = _fold_all("""
    rue | r. | avenue | av | av. | ave | boulevard | bd | bd. | bld | boul | blvd | place | pl | pl. | impasse
    imp | imp. | allée | all. | chemin | ch. | chem | route | rte | rte. | quai | square | sq | sq. | cours | crs
    passage | cité | cour | faubourg | fg | fbg | hameau | lieu-dit | lieu dit | ld | lotissement | lot. | résidence
    rés. | domaine | villa | voie | sentier | sente | ruelle | venelle | traverse | montée | rampe | esplanade
    parvis | promenade | prom. | rond-point | rdpt | carrefour | mail | clos | coteau | côte | chaussée | digue
    quartier | zone | za | zac | zad | zi | zone artisanale | zone industrielle | zone d'activités | parc | mas
    bastide | corniche | levée | galerie | plateau | carriera | camin | placa
""")
# Abréviations : retenues seulement après un numéro / abbreviations: only kept after a house number.
STREET_ABBREVIATIONS = _fold_all("""
    r. | av | av. | ave | bd | bd. | bld | boul | blvd | pl | pl. | imp | imp. | all. | ch. | chem | rte | rte.
    sq | sq. | crs | fg | fbg | ld | lot. | rés. | prom. | rdpt | za | zac | zad | zi
""")
# Types assez sûrs pour un nom de voie en minuscules / types safe enough for a lowercase street name.
STRONG_STREET_TYPES = _fold_all("""
    rue | avenue | av. | boulevard | bd | impasse | allée | chemin | route | quai | place | square
""")

# Éponymes en apposition directe seulement : « tour Eiffel », « sonde Cassini », mais « le tour de Pierre ».
# Direct-apposition eponyms only: followed by "de", the word introduces an owner instead.
EPONYMS_DIRECT = _fold_all("""
    tour | méthode | plan | test | programme | mission | navire | bateau | vaisseau | sonde | satellite | télescope
    fusée | comète | astéroïde | planète | étoile | galaxie | constellation | nébuleuse | cratère | mont | lac | île
    cap | golfe | baie | fleuve | rivière | canal | port | forêt | bois | col | pic | vallée | gorges | glacier
    volcan | rocher | stade | salle | studio | cinéma | lycée | collège | école | château | domaine | cru | opéra
    coupe
""")

# Particules de noms / name particles (lowercase gaps, or capitalised tokens inside a name).
PARTICLES = _fold_all("""
    de | du | des | d' | de la | de l' | le | la | van | von | van der | van den | van de | von der | von dem
    der | den | di | da | del | dello | della | dei | degli | delle | dos | das | do | ben | bin | ibn | bint | al
    el | y | zu | ter | ten | af | av | ould | ait | abd | abu | abou | mac
""")

# Particules capitalisées en tête d'un nom de famille (« Le Verger », « De Testval », « Van Testen ») ; ni « Ben »
# ni « Al », qui sont aussi des prénoms. Capitalised particles that start a surname; not "Ben" nor "Al", also given
# names.
SURNAME_PARTICLES = _fold_all("""
    le | la | les | de | du | des | van | von | der | den | di | da | del | della | dos | das | do | ter | ten | zu
""")

# Mots qui excluent une personne juste après (articles, déterminants) / determiners: no person right after.
DETERMINERS = _fold_all("""
    le | la | les | l' | un | une | des | du | au | aux | ce | cet | cette | ces | mon | ma | mes | ton | ta | tes
    son | sa | ses | notre | nos | votre | vos | leur | leurs | quel | quelle | quels | quelles | chaque | tout
    toute | tous | toutes | aucun | aucune | certain | certaine | plusieurs | the | an | der | die | das | dem
    den | el | los | las | il | lo | gli | het | this | that | these | those | our | your | their | its
""")
# Prépositions de lieu (sur le texte d'origine : « à » et « a » diffèrent) / place prepositions (original text).
LOCATIVES = frozenset({"à", "en", "vers", "depuis", "via", "sur", "dans", "in", "nach", "aus", "bei", "im"})
# Verbes de lieu (« quitter Lyon », « rejoindre Nantes ») : seulement pour un nom de lieu repris d'une personne
# trouvée ailleurs dans le texte (test terrain du 26/10 : « Mme Lyon » puis « quitter Lyon ») ; jamais pour un mot
# seul (« rejoindre Marie » reste masqué). Même liste dans rust/src/names/decide.rs. Place verbs: only for a place
# name repeated from a person found elsewhere in the text; never for a lone word. Same list in decide.rs.
PLACE_VERBS = ("quitter", "quitte", "quittent", "quitté", "quittée", "quittera", "rejoindre", "rejoint",
               "rejoindra", "regagner", "regagne")

# Formes juridiques (casse vérifiée) / legal forms (case checked on the original text).
LEGAL_FORMS_SUFFIX = (
    "SAS", "S.A.S.", "SASU", "S.A.S.U.", "SARL", "S.A.R.L.", "SARLU", "EURL", "E.U.R.L.", "SA", "S.A.", "SCI",
    "S.C.I.", "SNC", "S.N.C.", "SCOP", "SCP", "S.C.P.", "SCM", "SELARL", "SELAS", "SELAFA", "SELCA", "SELURL",
    "SCA", "SCS", "GIE", "G.I.E.", "GAEC", "EARL", "SCEA", "SEM", "SEML", "SPL", "SPFPL", "SICAV", "SCPI",
    "SAEM", "EI", "EIRL", "GmbH", "gGmbH", "AG", "KG", "KGaA", "OHG", "GbR", "UG", "e.V.", "eG", "SE", "S.L.",
    "S.L.U.", "SLU", "S.A.U.", "S.Coop.", "S.p.A.", "SpA", "S.r.l.", "Srl", "SRL", "S.r.l.s.", "S.n.c.",
    "S.a.s.", "B.V.", "BV", "N.V.", "NV", "V.O.F.", "BVBA", "SPRL", "ASBL", "VZW", "Ltd", "Ltd.", "Limited",
    "LLC", "L.L.C.", "LLP", "plc", "PLC", "Inc", "Inc.", "Incorporated", "Corp.", "Corporation", "Sàrl", "Sarl",
    "Oy", "Oyj", "AB", "A/S", "ApS", "ASA", "s.r.o.", "a.s.", "Kft.", "Zrt.", "Nyrt.", "d.o.o.", "d.d.", "OÜ",
    "UAB", "SIA", "Lda", "Lda.",
)
# Formes juridiques françaises pouvant précéder le nom / French legal forms that may precede the name.
LEGAL_FORMS_PREFIX = frozenset({
    "SAS", "SASU", "SARL", "SARLU", "EURL", "SCI", "SNC", "SCP", "SCM", "SELARL", "SELAS", "SELAFA", "GAEC",
    "EARL", "SCEA", "GIE", "EI", "EIRL", "SCOP", "SEM", "SPL", "SCA",
})
# Entrepreneur individuel : la raison sociale est souvent le nom de la personne / sole trader forms.
SOLE_TRADER_FORMS = frozenset({"EI", "EIRL"})
LEGAL_FORM_KEYS = frozenset(fold(f).replace(".", "") for f in LEGAL_FORMS_SUFFIX)
# Formes juridiques d'une personne morale (sans points, repliées) ; l'entrepreneur individuel (EI) en est exclu.
# Legal forms of a legal entity (folded, dotless); the sole trader (EI) is left out: it is a natural person.
COMPANY_FORM_KEYS = LEGAL_FORM_KEYS - frozenset(fold(f) for f in SOLE_TRADER_FORMS)

# Jetons capitalisés jamais pris pour un nom / capitalised tokens never taken as a name.
# Les mots de rôle et de voie n'en font pas partie : « Maréchal », « Place » sont aussi des noms de famille,
# ils ne servent de déclencheur que suivis d'un nom. Role and street words are contextual instead.
_DOTLESS_HONORIFICS = frozenset(h.rstrip(".") for h in HONORIFICS if h.endswith("."))  # « M », « Dr »
_ALPHA_LEGAL_FORMS = frozenset(f for f in LEGAL_FORM_KEYS if f.isalpha() and len(f) >= 2)  # « Jean Dupont EI »
STOP = HONORIFICS | GREETINGS | _DOTLESS_HONORIFICS | _ALPHA_LEGAL_FORMS | _fold_all("""
    objet | date | total | annexe | article | chapitre | page | tableau | figure | note | remarque | important
    attention | rappel | résumé | introduction | conclusion | sommaire | référence | réf | cordialement
    signature | signé | madame | monsieur | mademoiselle | messieurs | mesdames | oui | non | ok | nb | ps | pj
    cv | re | tr | fw | fwd | ceo | cto | cfo | coo | drh | rh | pdg | dg | daf | dsi | rssi | dpo | vp | hr
    it | ue | eu | usa | uk | onu | oms | cnil | rgpd | gdpr | sncf | ratp | edf | caf | cpam | urssaf | msa
    insee | tva | ht | ttc | sas | sarl | sa | sci | eurl | pme | tpe | cdi | cdd | smic | rib | iban | bic | pdf
    csv | json | api | url | sql | ia | ai | llm | gpt | faq | asap | fyi | nord | sud | est | ouest | centre
    junior | senior | jr | saint | sainte | st | ste | fc | ac | afc | sc | rc | og | ufc | psg
    siret | siren | rcs | naf | ape | rna | nir | finess | rpps | adeli | eori | duns
""")
# Mots de rôle et de voie : déclencheurs seulement s'ils précèdent un autre jeton capitalisé.
# Role and street words: triggers only when followed by another capitalised token.
CONTEXTUAL = frozenset(w for w in ROLES | EPONYMS | EPONYMS_DIRECT if " " not in w)

# Mots-outils capitalisés en tête de phrase : leur voisinage ne fait pas d'une suite un nom propre composé.
# Capitalised function words at sentence start: their adjacency does not make a compound proper noun.
FUNCTION = _fold_all("""
    le | la | les | un | une | des | du | de | au | aux | ce | cet | cette | ces | mon | ma | mes | ton | ta | tes
    son | sa | ses | notre | nos | votre | vos | leur | leurs | pour | par | dans | avec | sans | sur | sous
    selon | chez | vers | entre | depuis | pendant | avant | après | contre | malgré | et | ou | mais | donc | or
    ni | car | que | qui | quand | comme | si | il | elle | ils | elles | on | nous | vous | je | tu | j | c | voici
    voilà | ainsi | alors | puis | ensuite | enfin | aussi | déjà | hier | aujourd'hui | demain | maintenant
    ici | là | oui | non | bien | très | encore | toujours | jamais | souvent | parfois | seulement | également
    notamment | cependant | toutefois | pourtant | néanmoins | désormais | finalement | heureusement
    malheureusement | évidemment | effectivement | actuellement | récemment | merci | bonjour | bonsoir | salut
    bravo | félicitations | hello | hi | dear | cher | chère | à | en | the | and | with | for | from | to | of
    when | if | but | so | then | thanks | und | mit | für | von | y | con | para | e | per | di
""") | HONORIFICS | GREETINGS

# Mots qui introduisent une organisation / words introducing an organisation.
ORG_KEYWORDS = _fold_all("""
    société | entreprise | cabinet | association | fondation | groupe | groupement | établissements | ets
    agence | compagnie | cie | coopérative | mutuelle | banque | syndicat | fédération | confédération
    laboratoire | laboratoires | holding | studio | atelier | office notarial | étude | boulangerie | pâtisserie
    boucherie | charcuterie | pharmacie | garage | restaurant | brasserie | hôtel | librairie | imprimerie
    menuiserie | plomberie | transports | ambulances | taxis | auto-école | salon | institut de beauté
    company | firm | gesellschaft | firma | sociedad | empresa | società | azienda
""")
# Contexte d'organisation : n'empêche pas d'y voir un nom de personne (« Boulangerie Petit SARL »).
# Organisation context: does not prevent seeing a person name inside it.
ORG_CONTEXT = ORG_KEYWORDS | LEGAL_FORM_KEYS
# Mots de raison sociale familiale (« Dupont & Fils ») : jamais un nom de personne à eux seuls.
# Family-business words: never a person name on their own.
ORG_FAMILY = _fold_all("""
    fils | filles | frères | sœurs | associé | associée | associés | associées | cie | compagnie | co | partners
    partenaires | sons | söhne
""")
# Suffixes d'organisation (casse d'origine) / organisation suffixes (original case).
ORG_SUFFIXES = (
    "& Fils", "et Fils", "& fils", "et fils", "& Cie", "et Cie", "& Co", "& Co.", "Frères", "& Associés",
    "et Associés", "& associés", "et associés", "Associés", "Partners", "Group", "Groupe", "Holding",
    "Conseil", "Consulting", "Avocats", "Immobilier", "Industries", "Industrie", "Services", "Solutions",
    "Technologies", "Technology", "International", "Transports", "Construction", "Distribution", "Développement",
    "Ingénierie", "Architecture", "Architectes", "Notaires", "Expertise", "Audit", "Finance", "Gestion",
)

# En-têtes de colonnes de personnes (tableaux Markdown) / person column headers (Markdown tables).
GIVEN_HEADERS = _fold_all("""
    prénom | prénoms | first name | firstname | given name | vorname | nombre | nome | voornaam
""")
SURNAME_HEADERS = _fold_all("""
    nom | nom de famille | nom d'usage | nom de naissance | last name | lastname | surname | family name
    nachname | apellido | apellidos | cognome | achternaam | nom marital | nom d'épouse | pseudonyme
""")
PERSON_HEADERS = GIVEN_HEADERS | SURNAME_HEADERS | _fold_all("""
    nom complet | nom et prénom | nom et prénoms | nom prénom | prénom nom | identité | name | full name | personne
    salarié | salariée | salariés | employé | employée | collaborateur | collaboratrice | client | cliente
    patient | patiente | contact | titulaire | bénéficiaire | responsable | interlocuteur | signataire | auteur
    demandeur | candidat | candidate | élève | étudiant | étudiante | participant | participante | membre
    adhérent | adhérente | locataire | propriétaire | destinataire | expéditeur | conjoint | enfant | parent
    médecin | avocat | représentant | gérant | dirigeant | associé | témoin | intervenant | agent | conseiller
    employee | customer | owner | manager | contact name | author | assignee | reporter
    chef de projet | chef d'équipe | référent | référente | pilote | rédacteur | rédactrice | validateur | valideur
    approbateur | assigné à | attribué à | affecté à | suivi par | créé par | modifié par | demandé par
    enseignant | enseignante | professeur | formateur | formatrice | tuteur | tutrice | stagiaire | apprenti
    apprentie | assuré | assurée | souscripteur | mandataire | acheteur | vendeur | technicien | technicienne
    praticien | infirmier | infirmière | médecin traitant | prescripteur | passager | passagère | voyageur
    inscrit | inscrite | invité | invitée | conducteur | conductrice | chauffeur | nom du salarié | nom du patient
    nom de l'élève | requester | reviewer | approver | created by | assigned to | employee name | customer name
""")
# Valeurs de cellule qui ne sont pas des noms / cell values that are not names.
EMPTY_CELLS = _fold_all("""
    - | -- | — | n/a | na | nc | nd | néant | aucun | aucune | inconnu | inconnue | x | ? | / | oui | non | yes
    no | tbd | tbc | à définir | à préciser | vacant | vacante | tous | toutes | all | none | null
    non précisé | non précisée | non renseigné | non renseignée | non communiqué | non communiquée
""")

# Mots courants absents des lexèmes Wikidata (relevé sur des documents administratifs) : jamais un nom inconnu.
# Common words missing from the Wikidata lexemes (found on administrative documents): never an unknown name.
EXTRA_WORDS = _fold_all("""
    paie | paies | facture | factures | virement | virements | licenciement | licenciements | embauche | embauches
    astreinte | astreintes | relevé | relevés | récapitulatif | récapitulatifs | échéancier | échéanciers | impayé
    impayés | créance | créances | copropriété | copropriétés | résiliation | résiliations | détachement
    titularisation | télétravail | webinaire | webinaires | saisie | saisies | suivi | suivis | avoir | avoirs
""")

# Formes verbales homonymes de noms de famille (« Rendu le 3 mars », « Donne acte ») : mots courants.
# Verb forms that are also surnames: treated as common words (the build excludes verb lexemes).
VERB_FORMS = _fold_all("""
    rendu | rendue | donne | donné | fini | finie | choisi | battu | pendu | clos | attendu | entendu | vu | lu
    su | tenu | venu | reçu | connu | perdu | vendu | ordonne | condamne | confirme | constate | déclare
""")
# Types de document homonymes de noms de famille rares (« AVENANT N° 2 », « Devis », « Bordereau ») : ambigus, un
# nom seulement avec un indice (« M. Devis »). Document types that are also rare surnames: a name only with a cue.
DOCUMENT_WORDS = _fold_all("avenant | devis | bordereau")
# Titres de noblesse ou de souveraineté (« M. Le Comte ») : jamais le nom à particule qu'une civilité désignerait.
# Titles: never the particle surname an honorific would point at ("M. Le Verger" is one).
TITLES = _fold_all("""
    comte | comtesse | vicomte | vicomtesse | baron | baronne | duc | duchesse | prince | princesse | roi | reine
    pape | marquis | marquise | dauphin | dauphine | seigneur | sire
""")
