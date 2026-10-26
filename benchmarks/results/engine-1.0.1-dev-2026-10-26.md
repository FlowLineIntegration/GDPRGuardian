<!-- Moteur 1.0.1, mesures de développement (moitiés dev et graine de développement seulement). Engine 1.0.1, development measurements (dev halves and development seed only). Scores seulement : aucun texte, aucune valeur. Scores only: no text, no value. -->

# Moteur 1.0.1 : mesures de développement / engine 1.0.1: development measurements — 2026-10-26

Mesures en processus (`Anonymizer(countries="FR", profile="standard")`, noyau Rust reconstruit depuis les sources),
définition de la fuite du protocole (un seul caractère alphanumérique d'une mention directe resté lisible = fuite).
**Données de développement seulement** : graine synthétique 20261024 (documents 0 à 999), équipe rouge sur les bases
100000 à 100299 de cette graine avec les 51 opérateurs de `tools/eval/mutate.py`, moitiés « dev » de BODACC, BOAMP et
ParlaMint-FR (`tools.corpus.real_common.split_of`). Aucune moitié « test » n'a été lue.

In-process measurements, protocol leak definition, development data only (synthetic seed 20261024, red-team bases
100000-100299 of that seed through the 51 operators, dev halves of BODACC, BOAMP and ParlaMint-FR). No test half read.

## Par famille / per family (dev)

| Famille / family (dev) | Avant / before | Après / after | Rappel mentions avant / après | Précision avant / après |
|---|---:|---:|---|---|
| Synthétique FR (graine 20261024, 1 000 documents) | 90.6 % (906/1000) | 95.8 % (958/1000) | 98.17 / 99.51 | — |
| Équipe rouge FR, 51 opérateurs (300 bases) | 62.1 % (8429/13577) | 73.9 % (10031/13577) | 86.23 / 90.98 | — |
| Bases de l'équipe rouge (non mutées) | 90.0 % (270/300) | 95.7 % (287/300) | 97.95 / 99.49 | — |
| BODACC, moitié dev | 89.0 % (1209/1358) | 91.8 % (1247/1358) | 97.48 / 98.06 | 99.27 / 99.28 |
| BOAMP, moitié dev | 60.3 % (883/1465) | 94.1 % (1378/1465) | — / 99.17 | — / 86.91 |
| ParlaMint-FR, moitié dev | 89.7 % (140/156) | 89.7 % (140/156) | 98.18 / 98.18 | 95.48 / 95.48 |

BOAMP « avant » : le cache BOAMP a été reconstruit à 11 h 12 UTC (`tools/corpus/build_boamp.py` modifié par un autre
chantier) entre la première mesure « avant » (60.9 %, 892/1464, ancienne construction) et la mesure « après ». Le
chiffre retenu est celui de la revue sur la construction actuelle, sans les six nouvelles règles des packs : 60.27 %
(883/1465). BOAMP "before": the BOAMP cache was rebuilt at 11:12 UTC (another lane changed the builder) between the
first "before" run (60.9 %, 892/1464, old build) and the "after" run; the figure kept is the review's, on the current
build without the six new pack rules: 60.27 % (883/1465).

Corrections de la revue (26/10, 12 h 10 – 13 h UTC) : `FR_PHONE_FIELD` n'accepte plus que les chiffres d'un seul
numéro (validateur `fr.phone_field`), car deux numéros d'une même ligne « Tél : » laissaient lisible la fin du
second ; la forme libre « (+ » des avis (outre-mer mal formé compris) garde 8 à 15 chiffres, un seul « + », sans
« / » : rappel des téléphones BOAMP 100 % (3 515/3 515). `FR_ADDRESS_FIELD` s'arrête à une fin de phrase après la
commune et à « ; ». Adresses électroniques déguisées (`&#64;`, `%40`, domaine en `[dot]` / `(point)`) :
opérateurs `at_entity`, `at_percent` de 0 % à 93.6 %, `dot_brackets`, `dot_point` de 0 % à 95.7 % ; c'est l'essentiel
du gain de l'équipe rouge (70.0 % → 73.9 %). Aussi : téléphones groupés 4-3-3, identifiants à groupes espacés après
« police n° » / « contrat n° », date d'événement collée devant une date suivie de « née le ». Synthétique, BODACC et
ParlaMint inchangés.

Review fixes: `FR_PHONE_FIELD` now accepts one phone's worth of digits only (a second number on a "Tél:" line was
partly left readable); the "(+" free form of public notices keeps 8 to 15 digits, one "+", no "/": BOAMP phone recall
100 % (3,515/3,515). `FR_ADDRESS_FIELD` stops at a sentence end after the town and at ";". Disguised e-mail addresses
(`&#64;`, `%40`, `[dot]` / `(point)` domain): `at_entity`, `at_percent` from 0 % to 93.6 %, `dot_brackets`,
`dot_point` from 0 % to 95.7 %, most of the red-team gain (70.0 % → 73.9 %). Also: 4-3-3 grouped phones, spaced-group
identifiers after "police n°" / "contrat n°", an event word right before a date followed by "née le". Synthetic,
BODACC and ParlaMint unchanged.

Opérateurs « formats du quotidien » regroupés (crlf, line_break, tab, double_space, dots, slashes, hyphens,
en_dash_groups, regroup, compact, lower, upper, surname_first, markdown_bold, pdf_hyphenation, nbsp, strip_accents) :
45.9 % avant, 59.9 % après. The 17 everyday-format operators pooled: 45.9 % before, 59.9 % after.

Garde-fous synthétiques / synthetic guards : leurres touchés 3.43 % → 3.43 %, sur-masquage du texte neutre
0.073 % → 0.073 %. Témoin négatif Judilibre (300 décisions) : 4 108 zones, 12.46 pour 10 000 caractères (protocole
1.0 : 4 125 zones, 12.5). Decoys touched 3.43 % → 3.43 %, neutral over-masking 0.073 % → 0.073 %. Judilibre negative
control (300 decisions): 4,108 zones, 12.46 per 10,000 characters (protocol 1.0: 4,125 zones, 12.5). Après les
corrections de la revue / after the review fixes: 4 112 zones, 12.47 (quatre numéros de police d'assurance espacés,
« police n° 120 137 363 », désormais masqués / four spaced insurance policy numbers now masked).

## Par opérateur / per operator (dev, 300 bases)

| Opérateur / operator | Avant / before | Après / after | Rappel mentions avant / après (mention recall before / after) |
|---|---:|---:|---|
| tab | 11.7 % | 88.7 % | 75.70 / 98.62 |
| double_space | 6.3 % | 55.0 % | 67.48 / 92.49 |
| slashes | 3.3 % | 42.0 % | 63.81 / 88.58 |
| dots | 21.8 % | 42.3 % | 84.14 / 90.89 |
| hyphens | 50.5 % | 52.6 % | 91.09 / 92.05 |
| en_dash_groups | 51.7 % | 53.7 % | 91.19 / 91.98 |
| regroup | 18.3 % | 18.7 % | 78.86 / 79.89 |
| compact | 93.1 % | 94.9 % | 98.81 / 99.40 |
| line_break | 0.0 % | 3.7 % | 36.90 / 60.57 |
| crlf | 0.0 % | 3.0 % | 34.77 / 58.47 |
| lower | 24.0 % | 27.3 % | 75.66 / 77.16 |
| upper | 87.7 % | 93.3 % | 97.59 / 99.13 |
| surname_first | 87.7 % | 90.3 % | 98.43 / 98.75 |
| markdown_bold | 86.3 % | 92.0 % | 97.43 / 98.97 |
| pdf_hyphenation | 86.3 % | 92.3 % | 97.51 / 99.09 |
| nb_hyphen | 88.8 % | 96.0 % | 98.00 / 99.56 |
| cyrillic | 67.0 % | 72.3 % | 94.39 / 95.97 |
| strip_accents, nfd | 89.5 % | 93.8 % | 98.60 / 99.30 |
| nbsp et autres espaces, invisibles, chiffres de substitution, greek | 90.0 % | 95.7 % | 97.95 / 99.49 |
| hangul_filler | 89.3 % | 95.0 % | 97.87 / 99.41 |
| arobase, at_brackets, at_parens | 90.0 % | 93.6 % | 98.97 / 99.38 |
| at_fullwidth | 92.1 % | 95.7 % | 99.17 / 99.59 |
| ocr | 7.1 % | 9.1 % | 71.57 / 72.68 |
| at_entity, at_percent | 0.0 % | 93.6 % | 82.98 / 99.38 |
| dot_brackets, dot_point | 0.0 % | 95.7 % | 83.18 / 99.59 |
| letter_spacing | 0.0 % | 0.0 % | 4.03 / 9.84 |
| math_bold | 0.0 % | 0.0 % | 33.23 / 35.72 |
| superscript | 0.0 % | 0.0 % | 55.43 / 55.43 |

Textes Windows entiers (fins de ligne CRLF partout) : même résultat que les fins de ligne LF sur 300 documents
synthétiques dev (93.3 % / 93.3 % avant, 97.0 % / 97.0 % après). L'opérateur `crlf` coupe une valeur par un saut de ligne, comme `line_break`.
Whole Windows texts (CRLF everywhere) score like LF texts; the `crlf` operator breaks a value by a line break.

## Ce qui a changé / what changed

- Couche 0 (Python et Rust, une seule table de positions) : règle GAP (tabulation ou 2 à 4 blancs entre deux
  alphanumériques dont un chiffre ; un saut de ligne LF/CRLF entre deux chiffres, groupes voisins de 12 caractères au
  plus) ; groupes séparés par « / » (4 et plus) ou « . » (5 et plus) lus comme des espaces.
- Packs : `FR_ADDRESS_FIELD` (valeur entière d'une ligne « Adresse : … »), `FR_PHONE_FIELD` (« Tél : … », formes
  libres), `FR_RIB_FIELD` (RIB champ par champ), `FR_PHONE_GROUPED` (4-2-2-2, 2-4-4), `FR_RPPS_LABELLED`,
  `FR_LABELLED_ID` (matricule, IPP, contrat n°…), borne gauche de `FR_BIRTH_DATE_TEXT` (« signé le », « ordonné le »),
  mots-veto des dates d'événement (« hospitalisé le », « désigné le »…).
- Adresses (Python et Rust) : un numéro d'article de code (« L. 1221-3 ») n'est plus un numéro de voie.
- Portée (Python et Rust) : une partie d'un nom composé (« Mme Kervadec » après « Solène Kervadec-Moulin ») garde la
  balise de la personne.

In English:

- Layer 0 (Python and Rust, one offset map): GAP rule (a tab or 2 to 4 blanks between two alphanumerics, one of them
  a digit; one LF/CRLF line break between two digits, neighbouring groups of at most 12 characters); groups split by
  "/" (4 or more) or "." (5 or more) read as spaces.
- Packs: `FR_ADDRESS_FIELD` (whole value of an "Adresse: …" line), `FR_PHONE_FIELD` ("Tél: …", free forms, one
  number's worth of digits), `FR_RIB_FIELD` (RIB field by field), `FR_PHONE_GROUPED` (4-2-2-2, 2-4-4),
  `FR_RPPS_LABELLED`, `FR_LABELLED_ID` (matricule, IPP, contrat n°…), left edge of `FR_BIRTH_DATE_TEXT` ("signé le",
  "ordonné le"), event-date veto words ("hospitalisé le", "désigné le"…).
- Addresses (Python and Rust): a code article number ("L. 1221-3") is no longer a house number.
- Scope (Python and Rust): a part of a hyphenated surname ("Mme Kervadec" after "Solène Kervadec-Moulin") keeps the
  person's placeholder.

## Performance (même processus, passes alternées, meilleure de 5) / performance (same process, interleaved)

Nouvelles règles des packs actives / désactivées : synthétique 0.296 / 0.287 ms (+3 %), BODACC 0.197 / 0.191 ms (+3 %),
Judilibre 1.079 / 1.100 ms (−2 %), BOAMP 0.947 / 0.802 ms (+18 % : cinq champs de plus masqués par avis). Mesures
bruitées (trois autres chantiers tournaient sur la machine) ; chaque règle seule coûte de 0 à 3 % sur BOAMP. Mesures
faites avant les corrections de la revue, non refaites.

New pack rules on / off: synthetic 0.296 / 0.287 ms (+3 %), BODACC 0.197 / 0.191 ms (+3 %), Judilibre 1.079 /
1.100 ms (−2 %), BOAMP 0.947 / 0.802 ms (+18 %: five more fields masked per notice). Noisy measurements (three other
lanes were running); each rule alone costs 0 to 3 % on BOAMP. Measured before the review fixes, not re-run.
