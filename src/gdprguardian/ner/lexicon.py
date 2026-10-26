"""Listes de mots repliés (minuscules, sans accents) pour le filtrage et le nettoyage du NER.

Folded word lists (lowercase, no accents) for NER gating and span cleanup.
"""

from __future__ import annotations

from ..scope import HONORIFICS


def _words(text: str) -> frozenset[str]:
    return frozenset(text.split())


_DAYS_MONTHS = _words("""
    lundi mardi mercredi jeudi vendredi samedi dimanche janvier fevrier mars avril mai juin juillet aout
    septembre octobre novembre decembre monday tuesday wednesday thursday friday saturday sunday january
    february march april june july august september october november december
""")

_PRONOUNS = _words("""
    je j tu il elle on nous vous ils elles moi toi lui eux me m te t se s y en ceci cela ca celui celle ceux
    celles qui que qu quoi dont lequel laquelle lesquels lesquelles chacun chacune personne rien quelqu'un
    i you he she it we they him her us them me myself yourself himself herself
""")

# Mots fréquents en début de phrase, jamais des noms : ils n'ouvrent pas le filtre.
# Frequent sentence-initial words that are not names: they do not open the gate.
COMMON_STARTERS = _PRONOUNS | _DAYS_MONTHS | HONORIFICS | _words("""
    le la les l un une des du de d au aux ce cet cette ces mon ma mes ton ta tes son sa ses notre nos votre vos
    leur leurs quel quelle quels quelles chaque plusieurs certains certaines tout toute tous toutes aucun aucune
    autre autres meme tel telle a apres avant avec chez contre dans depuis derriere des devant durant entre
    envers hors malgre par parmi pendant pour sans selon sous suivant sur vers via concernant conformement
    grace jusqu jusque lors pres outre et mais ou donc or ni car puis ensuite enfin alors ainsi aussi cependant
    toutefois neanmoins pourtant sinon si quand lorsque lorsqu comme puisque puisqu parce afin bien tres trop
    plus moins encore deja toujours jamais souvent parfois ici aujourd hier demain maintenant desormais oui non
    ne n pas voici voila certes evidemment notamment egalement seulement surtout vraiment environ combien
    comment pourquoi est sont etait etaient sera seront ete etre avoir ont avait avaient fait faire faut peut
    peuvent doit doivent veuillez merci bonjour bonsoir salut coucou cordialement cher chere chers cheres objet
    re tr fw fwd pj nb ps voir note remarque attention important rappel conclusion resume introduction total
    date lieu page article chapitre annexe section partie titre nom prenom adresse telephone tel email mail
    courriel contact signature madame monsieur mesdames messieurs premier premiere deuxieme troisieme dernier
    derniere nouveau nouvelle the a an this that these those my your his its our their in on at for with from
    to of by as if when while and but or so then please thanks thank hello hi dear regards best yes no there
    here what which who how why where is are was were be have has had do does did can could will would should
    may might must not all some any each every after before during about also subject
""")

# Abréviations suivies d'un point qui ne terminent pas une phrase (« M. Dupont », « art. 12 »).
# Abbreviations whose period does not end a sentence.
ABBREVIATIONS = HONORIFICS | _words("""
    mm mmes mlles drs prof mgr st ste sts av ave bd bld boul fg pl rte imp ch sq etc cf ex ibid id op cit no nos
    num p pp vol art al chap fig ref tel fax inc ltd co cie jr sr mr mrs ms vs env approx min max dept dep adm gen
    col cdt lt cne sgt adj ss janv fevr avr juil sept oct nov dec lun mer jeu ven sam dim hab nb ps pj obs bis
    ter cass civ crim soc com req c
""")

# Civilités, formules et noms de dossier à laisser hors d'une zone PERSONNE : le modèle rend « Dossier Lemoine »
# ou « Famille Dupont » en entier, et la portée y verrait un prénom (deux balises pour une même personne).
# Honorifics, greetings and file nouns kept outside a PERSON span: the scope would read them as a given name.
LEADING_PERSON_WORDS = HONORIFICS | _words("""
    bonjour bonsoir salut coucou cher chere chers cheres hello hi dear merci mesdames messieurs mamie mamy
    papi papy tonton tata tatie tante oncle dossier affaire cabinet famille projet maison consorts epoux epouse
    veuve veuf succession heritiers indivision foyer menage client cliente patient patiente compte
""")

# Zones à rejeter si elles se réduisent à l'un de ces mots / spans rejected when they are exactly one of these.
STOP_SPANS = _PRONOUNS | _DAYS_MONTHS | LEADING_PERSON_WORDS | _words("""
    cordialement bien amicalement client cliente clients patient patiente salarie salariee employe employee
    employeur locataire bailleur proprietaire vendeur acheteur acquereur preneur mandant mandataire demandeur
    demanderesse defendeur defenderesse requerant requerante prevenu prevenue victime temoin avocat avocate
    notaire juge medecin infirmier infirmiere directeur directrice president presidente gerant gerante maire
    prefet ministre societe entreprise association etablissement tribunal cour mairie prefecture commune ville
    region departement pays objet signature nom prenom adresse
""")
