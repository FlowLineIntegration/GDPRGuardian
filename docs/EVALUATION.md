# Évaluation de Gardien RGPD

> **English summary.** GDPR Guardian is evaluated on a deterministic synthetic French corpus (540 documents,
> 9 document kinds, 30 templates, 5,556 annotated PII mentions, 2,228 hard-negative decoys) whose
> identifiers are valid (check digits recomputed independently and cross-checked against python-stdnum,
> used as a test-only oracle), plus a red-team corpus of 5,652 documents produced by 47 mutation
> operators. Metrics: character-level recall/precision/F2 on alphanumeric characters, TAB-style entity
> recall, document leak rates, over-masking, decoy false-mask rate and **survival** under mutation, with
> document-level bootstrap 95% CIs. Two snapshots were measured on 2026-10-24. **(A) core only** (name,
> address and organisation detectors still stubs): structured identifiers reach 98.8% character recall
> [98.3–99.3] with 98.2% precision; every checksum identifier (NIR, IBAN, RIB, SIRET, cards) and every
> e-mail is masked. **(B) text detectors being integrated**: direct-identifier recall rises to 99.2%
> (PERSON 98.5%, ADDRESS 98.2%), but 10.7% of documents make the engine raise an exception (bug in the
> name detector under development), 11.8% of documents still leak a direct identifier, and the name
> detector over-masks capitalised headings and legal references. The red team finds real gaps (line
> breaks, tabs and double spaces inside identifiers, invisible variation selectors, superscript digits,
> decomposed accents, RIB laid out field by field, local DOM phone format, Markdown table cells without
> header context). Seven core fixes were **simulated in memory and measured**: each closes its gap
> (e.g. 0% → 100% survival) at no measured cost. Throughput is 0.6–1.2 M chars/s per core on mixed
> documents (about 3 M chars/s on PII-free text), cold start 0.11–0.20 s, no catastrophic backtracking.
> **Adversarial review (same day, section 6.7)**: new bench inputs reveal **quadratic** cost in the address
> and name heuristics on a single long line (a one-line list of addresses: 100 k chars in 32 s), i.e. a
> denial-of-service vector; bounded backward scans, simulated in memory, give **identical outputs on 900
> documents** and linear time (32 s → 0.4 s). Four new red-team operators show that PDF end-of-line
> hyphenation hides 100% of names and addresses, Markdown bold hides every customer number, and the
> invisible Hangul filler U+3164 defeats every structured identifier; the first two are closed by
> simulated fixes (0 → 98.9% and 0 → 100% survival) with no change on the base corpus.

Ce document décrit la méthode, le corpus, les résultats mesurés, les faiblesses trouvées et les
correctifs recommandés. Les chiffres viennent de `benchmarks/results/` : `eval-2026-10-24-core.{json,md}`
(instantané A), `eval.{json,md}` (instantané B) et `bench.{json,md}`, produits par les commandes de la
section 2. Ils portent sur des **données synthétiques** et ne remplacent pas une mesure sur documents réels.

## 1. Ce qui est mesuré, et ce qui ne l'est pas

Gardien RGPD remplace les identifiants détectés par des balises irréversibles. L'évaluation mesure donc
d'abord **ce qui reste visible** : un identifiant direct masqué à 90 % reste une fuite. D'où des
métriques orientées rappel (F2, fuites par document, survie aux mutations), la précision venant ensuite.

Elle ne mesure pas le risque de ré-identification par le **contexte résiduel** (métier, dates, lieux,
faits rapportés) : les trois critères de la CNIL (individualisation, corrélation, inférence) ne sont pas
évalués. Un score parfait ne vaut donc pas certification d'anonymat au sens du RGPD.

## 2. Reproduire

```
python -m tools.eval.evaluate                       # corpus + équipe rouge + 3 profils -> benchmarks/results/eval.{json,md}
python -m tools.bench.bench                         # débit, latence, démarrage, mémoire -> benchmarks/results/bench.{json,md}
python -m tools.bench.bench --quick --profiles standard   # version courte
python -m tools.eval.generate --docs 500 --out corpus.jsonl  # corpus annoté seul (JSONL)
python -m tools.eval.mutate --in corpus.jsonl --out mutated.jsonl --only nbsp,line_break
python -m pytest tests/eval -q                      # tests du banc, dont les tests de fumée (quelques secondes)
```

Options utiles : `--countries` (`auto` par défaut, comme le moteur ; `FR`, `FR,BE` ou `all`), `--mutations`
(liste d'opérateurs), `--bootstrap 0` (sans intervalles), `--out` (dossier des rapports). Les rapports
JSON et Markdown sont écrits avec des fins de ligne LF sur tous les systèmes.

Tout est déterministe pour une graine et une version de Faker données (graine par défaut `20261024`,
Faker 40.43.0) : le document *i* ne dépend que de la graine et de *i*, pas de la taille du corpus. Les
outils sont hors du paquet publié (`tools/`), sans réseau ; ils n'utilisent que le groupe `dev`
(numpy, s'il est présent, accélère seulement le bootstrap). Un plantage du moteur sur un document n'arrête
pas l'évaluation : il est compté à part (type d'exception et identifiant du document, jamais de contenu).

## 3. Corpus synthétique

### 3.1 Documents

| Type | Gabarits | Contenu |
|---|---|---|
| `email` | 4 | changement de RIB, réclamation (carte, IBAN), courriel en anglais avec identifiants français, courriel privé |
| `minutes` | 2 | comité de direction, assemblée générale d'association |
| `hr_record` | 3 | fiche individuelle (tableau), avenant au contrat, note d'embauche (passeport, CNI, RIB) |
| `contract` | 3 | bail d'habitation, prestation avec entrepreneur individuel, cession de véhicule |
| `invoice` | 3 | facture d'entrepreneur individuel, facture d'entreprise à un particulier, facture d'électricité |
| `ticket` | 3 | ticket de support (IP), livraison non reçue (carte), ticket en anglais (passeport) |
| `medical` | 2 | courrier entre confrères (NIR, IPP, FINESS), ordonnance (RPPS, NIR sans clé) |
| `table` | 3 | export RH, liste d'émargement, clients en retard (tableaux Markdown de 3 à 8 lignes) |
| `letter` | 7 | CAF, France Travail, avis d'imposition (SPI), contravention (plaque), relevé d'identité bancaire, URSSAF, La Poste |

Les gabarits sont du français écrit naturel (accords, civilités, typographie) ; les civilités restent
hors des zones annotées, comme l'exige le contrat des détecteurs. Une même personne est citée sous
plusieurs formes (« Jean Dupont », « M. Dupont », « DUPONT Jean », « J. Dupont », « Jean »), ce qui
permet le rappel d'entité à la TAB.

### 3.2 Identifiants valides

Les clés sont recalculées dans `tools/eval/ids.py`, indépendamment du moteur, puis vérifiées dans
`tests/eval/test_eval_ids.py` contre les validateurs de Gardien RGPD **et** contre python-stdnum (LGPL,
oracle de test uniquement, jamais importé depuis `src/`) :

- **NIR** : sexe 1/2, NIA 7/8 (nés à l'étranger), 3/4 ; mois réels, fictifs (20-42) et d'état civil
  incomplet (50-99) ; Corse 2A/2B (clé calculée avec 19/18), et « 20 » pour les natifs de Corse nés
  avant 1976 (antérieurs à la partition), DOM 97x (commune sur 2 chiffres), étranger
  99 + code pays ; NIR cohérent avec la date et le lieu de naissance de la personne ; formes groupée,
  compacte, clé séparée, et sans clé (13 caractères).
- **SIREN, SIRET** (Luhn), dont **La Poste** (356 000 000, somme des chiffres multiple de 5, siège exclu) ;
  **TVA** à clé numérique ; **RIB** (clé 97, lettres converties, comptes avec lettre) et **IBAN** FR,
  plus DE, BE et ES avec leurs clés nationales ; **cartes** Visa, Mastercard (51-55 et 2221-2720), Amex ;
  **SPI** (clé mod 511), **RPPS**, **FINESS**, **EAN-13** ; plaques **SIV** (sans I, O, U, ni SS/WW) et
  **FNI** ; passeport, CNI (ancien format et CNIe) ; téléphones métropole (8 écritures) et DOM
  (+262, +590, +594, +596, et forme locale « 0692 12 34 56 ») ; e-mails dérivés des noms ; IPv4, IPv6.

Les noms combinent Faker fr_FR (environ 400 noms de famille seulement) et des lexiques ajoutés :
particules (« de La Fontaine »), noms composés, noms qui sont aussi des mots (Petit, Blanc, Boulanger),
origines variées (Nguyen, N'Diaye, Benali, Da Silva, Kowalski), DOM et Corse. Les villes et codes postaux
sont réels (faits publics), y compris des homonymes de prénoms (Nancy, Laval, Valence).

### 3.3 Annotation

Schéma inspiré de TAB : `{doc_id, text, spans[start, end, label, entity_id, identifier_type, mutation]}`,
positions en points de code du texte original, vérifiées par construction (`Document.check`).

| Type | Libellés |
|---|---|
| `DIRECT` | PERSON, EMAIL, PHONE, ADDRESS, NIR, IBAN, RIB, RIB_SPLIT, CARD, SIRET, SIREN, VAT, TAX_ID, PASSPORT, ID_CARD, PLATE, RPPS, CAF, FRANCE_TRAVAIL, IP |
| `QUASI` | BIRTH_DATE, LOCATION (lieu de naissance, ville), ORG, ID (n° client, IPP, matricule, PDL) |
| `NO_MASK` (leurres) | AMOUNT, ORDER_NUMBER (dont des numéros à 9 chiffres valides Luhn), INVOICE_NUMBER, LEGAL_REF (« article L. 1234-5 », « 293 B du CGI »), EVENT_DATE (dont des dates d'embauche juste après une date de naissance), PRODUCT_REF (dont EAN-13), CASE_NUMBER, COMPANY_ID, FACILITY_ID, BIC, VERSION, TICKET |

Choix de politique, alignés sur le moteur : les SIREN/SIRET/TVA d'une **personne morale** sont des
leurres (`COMPANY_ID`), ceux d'un **entrepreneur individuel** sont directs ; le FINESS d'un
établissement est un leurre.

### 3.4 Limites du corpus

Données générées par gabarits : formats canoniques, prose fluide, pas d'erreurs de conversion PDF ni
de mise en page réelle (sauf ce que simule l'équipe rouge). Les scores réels seront plus bas. Les noms
proviennent en partie de Faker, dont le vocabulaire est petit : un détecteur qui l'apprendrait verrait
son rappel gonflé. Il manque encore un jeu réel annoté (voir section 8).

## 4. Métriques

Seuls les caractères **alphanumériques** comptent (TAB ignore espaces et ponctuation ; sa règle de
catégories grammaticales anglaises n'est pas reprise). Notations : G = caractères des zones à masquer
(DIRECT et QUASI), P = caractères masqués par Gardien RGPD (zones `personal` réellement remplacées, en
positions du texte original), N = caractères hors de toute zone annotée.

| Métrique | Définition |
|---|---|
| Rappel caractère | \|G ∩ P\| / \|G\|, par libellé, direct seul, « structurés » seuls (hors PERSON/ADDRESS) |
| Précision caractère | \|G ∩ P\| / \|P\| ; un masque sur un leurre ou sur N est une erreur |
| F2 | 5·P·R / (4·P + R) : le rappel pèse quatre fois plus |
| Rappel de mention | mention sans aucun caractère significatif visible ; intervalle de Wilson 95 % |
| Rappel d'entité (TAB) | une entité compte si **toutes** ses mentions sont masquées ; variante stricte sans aucun caractère visible entre le premier et le dernier caractère significatif |
| Fuite de document | stricte : au moins un caractère d'un identifiant direct visible ; « structurée » : idem hors noms et adresses ; souple : au moins 4 caractères significatifs consécutifs visibles ; littérale : la valeur annotée se retrouve dans la sortie (formes canoniques NFKC, sans caractères de format ni caractères « default ignorable » comme U+FE0F, U+034F ou U+3164, des deux côtés) |
| Sur-masquage | \|P ∩ N\| / \|N\| |
| Leurres masqués | part des leurres dont au moins un caractère est masqué |
| Survie (équipe rouge) | parmi les mentions masquées **avant** mutation, part encore masquée **après** |
| Secondaires | appariement de zones à IoU ≥ 0,9 (presidio-evaluator), bon libellé, confusions de libellés |

Les intervalles de confiance des indicateurs principaux sont obtenus par **bootstrap sur les documents**
(1 000 rééchantillonnages, graine fixe) et jamais sur les caractères. Les scorers sont des fonctions
pures testées sur des cas construits à la main (fuite partielle, décalage de borne, mentions éclatées,
leurres, quasi-identifiants, survie, zones imbriquées) dans `tests/eval/test_eval_metrics.py`. Une zone
masquée hors des bornes du texte lève une erreur au lieu de décaler silencieusement toutes les mesures.

## 5. Équipe rouge

51 opérateurs (`tools/eval/mutate.py`) réécrivent chaque mention éligible ; le texte est recomposé par
concaténation et les positions recalculées. Familles : espaces Unicode (5), caractères invisibles (11 :
U+200B, U+200D, U+2060, U+FEFF, U+00AD, U+200E, isolats bidi, caractères d'étiquette, sélecteur de
variante U+FE0F, U+034F, remplisseur hangul U+3164), chiffres et lettres de substitution (pleine chasse,
mathématiques gras, arabo-indiens, dévanagaris, exposants), sosies cyrilliques et grecs, tirets Unicode,
séparateurs ASCII (points, tirets, barres obliques, doubles espaces, suppression, regroupement
irrégulier), mise en page (retour à la ligne, CRLF, tabulations, lettres espacées « J e a n » et césure
« Du-⏎pont » des extractions PDF, gras Markdown « **…** »), OCR (0/O, 1/l, 5/S, 8/B), casse et accents
(majuscules, minuscules, « NOM Prénom », accents retirés, NFD), e-mails maquillés (« [at] », « (at) »,
« arobase », `&#64;`, `%40`, `＠`, « [dot] », « (point) »). Les instantanés A et B (section 6) ont été
mesurés avec les 47 premiers ; les quatre derniers ont été ajoutés par la revue (section 6.7). Dans le
code, tout caractère invisible ou d'espacement est écrit en échappement `\uXXXX`.

## 6. Résultats (24 octobre 2026)

Configuration : `Anonymizer(profile=…, countries="auto")`, Gardien RGPD 0.1.0, Python 3.12.11, Windows 11,
AMD Zen 3 (famille 25, modèle 80), un cœur. Les profils `fast` et `standard` donnent des résultats
identiques : ils ne diffèrent qu'une fois le NER branché.

Le moteur évoluait pendant la mesure (d'autres modules étaient développés en parallèle). Deux
instantanés sont donc rapportés, sans les mélanger :

| Instantané | Heure (UTC) | Détecteurs Python actifs | Fichier |
|---|---|---|---|
| A, cœur seul | 19 h 17 | `EMAIL`, `INTL_IBAN` ; noms, adresses, organisations : ébauches sans aucune zone | `eval-2026-10-24-core.*` |
| B, détecteurs de texte en intégration | 19 h 29 | `FR_NAMES` (2 057 zones), `FR_ADDRESS` (340), `ORGANIZATIONS` (43), `EMAIL`, `INTL_IBAN` ; 11 packs pays chargés en mode auto | `eval.*` |

Aucun modèle NER n'était branché. `INTL_PHONE` et `INTL_MRZ` n'ont rien émis (les numéros +33 sont pris
par les motifs du pack FR ; le corpus ne contient pas de bande MRZ). Les sections 6.2 à 6.4 décrivent
l'instantané A, qui isole les identifiants structurés ; la section 6.6 décrit l'instantané B.

### 6.2 Indicateurs principaux, instantané A (540 documents)

| Indicateur | standard | strict |
|---|---|---|
| Rappel caractère, identifiants directs | 49,9 % [47,6–51,9] | 49,9 % |
| … dont identifiants structurés (hors noms et adresses) | 98,8 % [98,3–99,3] | 98,9 % [98,4–99,3] |
| Précision caractère | 98,2 % [97,8–98,7] | 94,0 % [93,1–94,9] |
| F2 (direct + quasi) | 53,3 % [51,7–54,7] | 53,1 % |
| Rappel d'entité directe (TAB) | 52,2 % [50,3–53,9] | 52,2 % |
| Documents avec fuite stricte | 100 % (noms et adresses non détectés) | 100 % |
| Documents avec fuite d'identifiant structuré | 4,6 % [3,0–6,5] | 4,6 % |
| Sur-masquage du texte neutre | 0,0 % | 0,0 % |
| Leurres masqués à tort | 2,8 % [2,2–3,5] | 9,7 % [8,6–10,9] |

Les 4,6 % de documents qui laissent fuir un identifiant structuré viennent de deux causes seulement :
les RIB présentés champ par champ (12 documents) et la forme locale des mobiles des DOM (13 documents).

### 6.3 Par type d'identifiant, instantané A (profil standard)

| Libellé | Mentions | Rappel de mention [IC 95 %] | Précision | Remarque |
|---|---|---|---|---|
| NIR | 273 | 100 % [98,6–100] | 100 % | dont mois fictifs, Corse, DOM, NIA, sans clé |
| IBAN | 281 | 100 % [98,7–100] | 100 % | |
| RIB | 42 | 100 % [91,6–100] | 100 % | |
| RIB_SPLIT | 48 | **0 %** [0–7,4] | – | RIB en champs séparés : non détecté |
| SIRET (entrepreneur individuel) | 36 | 100 % [90,4–100] | 70,5 % | précision : SIRET de sociétés voisines masqués |
| SIREN (entrepreneur individuel) | 9 | 100 % [70,1–100] | 37,5 % | idem |
| TVA | 21 | 100 % [84,5–100] | 100 % | |
| CARD | 35 | 100 % [90,1–100] | 76,5 % | précision : SIRET compacts et EAN-13 pris pour des cartes |
| EMAIL | 478 | 100 % [99,2–100] | 100 % | |
| PHONE | 647 | 98,0 % [96,6–98,8] | 100 % | manque « 0692 12 34 56 » (DOM, forme locale) |
| PLATE | 57 | 100 % [93,7–100] | 100 % | SIV avec ou sans tirets, FNI |
| ID_CARD, PASSPORT | 42, 47 | 100 % | 100 % | 20 passeports étiquetés CNI (contextes voisins), masqués quand même |
| RPPS, TAX_ID, CAF, FRANCE_TRAVAIL, IP | 60, 10, 7, 6, 15 | 100 % | 100 % | |
| BIRTH_DATE (quasi) | 337 | 61,4 % [56,1–66,5] | 92,3 % | manquées dans les cellules de tableau ; dates d'embauche voisines masquées |
| ID (quasi) | 265 | 44,5 % [38,7–50,5] | 100 % | matricules en tableau, références sans libellé reconnu |

Leurres : aucun montant, article de loi, numéro de facture, de dossier ou de version n'est masqué. Sont
masqués à tort, en profil standard : 28,8 % des identifiants de **sociétés** (fenêtre « entrepreneur
individuel » de 200 caractères, et motif CARD), 2,4 % des dates d'événement, 6,1 % des références
produit (EAN-13 valides Luhn). En profil strict, par construction, tous les identifiants de sociétés et
d'établissements et 16,5 % des numéros de commande (9 chiffres valides Luhn) sont masqués.

### 6.4 Équipe rouge, instantané A : survie des identifiants structurés (profil standard)

| Résultat | Opérateurs (survie) |
|---|---|
| Neutralisés (100 %) | espaces Unicode (5), invisibles de catégorie Cf (8), pleine chasse, chiffres arabo-indiens et dévanagaris, sosies cyrilliques et grecs, trait d'union insécable, majuscules, « [at] », « (at) », « arobase », « ＠ » |
| Presque (≥ 99 %) | suppression des séparateurs (99,3 %) |
| Partiels | tirets cadratins entre groupes 83,6 %, tirets 81,0 %, points 62,2 % (IBAN 0/74, cartes 0/11, RPPS 0/15), lettres mathématiques 55,0 % (e-mails 0/114, IBAN 0/74), regroupement irrégulier 41,0 % (NIR 67/67 mais cartes, SIRET, RIB, TVA 0 %) |
| Échecs | sélecteur de variante U+FE0F et U+034F (0 %), tabulations (0 %), retours à la ligne (3,1 %), CRLF (1,9 %), barres obliques (5,9 %), doubles espaces (7,1 %), OCR (6,5 %), exposants (7,0 %), `&#64;`, `%40`, « [dot] », « (point) » (0 %) |

Le motif du NIR, qui admet un séparateur facultatif entre **chaque** chiffre, survit à tous les
regroupements : c'est le modèle à généraliser.

### 6.5 Performance

Source : `benchmarks/results/bench.md` (19 h 18 UTC), un cœur, appels séquentiels, GC actif,
préchauffage, échantillons d'au moins 50 ms. Le poste était **partagé** avec d'autres travaux : d'une
exécution à l'autre, le débit médian a varié de 0,6 à 1,2 M car./s sur la même entrée. Le « meilleur
échantillon », entre parenthèses, est la borne basse la moins sensible à cette charge.

| Mesure (profil standard) | Résultat |
|---|---|
| Latence par document (380 à 810 caractères) | p50 0,45 à 0,86 ms ; p95 0,54 à 1,42 ms selon le type |
| Débit, documents mixtes de 10 k car. | 1,13 M car./s (1,21) |
| Débit, 100 k car. / 1 M car. | 0,92 (1,05) / 0,74 (0,83) M car./s |
| Débit, texte sans donnée personnelle (100 k car.) | 2,85 (3,39) M car./s |
| Débit, tableaux denses en identifiants (100 k car.) | 0,74 (0,97) M car./s |
| Répartition du temps (1 M car.) | pack FR 41 %, pack INTL 33 %, préparation 10 %, packs BE et CH 7 %, résolution 2 % |
| Démarrage à froid (processus neuf, médiane de 5) | 113 à 203 ms selon la charge (import 65 à 114 ms, construction 46 à 81 ms, premier appel < 1 ms) ; construction portée à 288 ms une fois les autres packs et listes de noms arrivés (profils standard et strict) |
| Mémoire (entrée de 1 M car.) | pic tracemalloc 9,6 Mo (10 octets alloués par caractère) ; pic RSS 41 → 53 Mo |
| Entrées adverses (19 × 200 k car.) | aucune explosion : exposant de croissance 0,85 à 1,24 et débit ≥ 0,31 M car./s, sauf « DUPONT DUPONT … » (voir 6.6) |

Le débit baisse un peu avec la taille (1,1 M car./s à 10 k, 0,8 M car./s à 1 M) : léger coût
super-linéaire, à surveiller. Les motifs les plus chers en balayage brut (URL_PERSONAL,
EMAIL_OBFUSCATED : 20 ms pour 100 k car.) sont évités par leurs préfiltres ; parmi ceux qui tournent,
IPV6, IPV4, FR_CONTEXTUAL_ID (sans préfiltre) et SECRET_PASSWORD (préfiltre « pass » satisfait par
« passeport ») coûtent 5 à 7 ms pour 100 k car.

### 6.6 Instantané B : détecteurs de texte en cours d'intégration (profil standard)

| Indicateur | Résultat |
|---|---|
| Documents faisant planter le moteur | **58 / 540 (10,7 %)**, `AttributeError` dans `fr_names` ; 596 / 5 652 dans le corpus muté ; exclus des mesures ci-dessous |
| Rappel caractère, identifiants directs | 99,2 % [98,9–99,4] |
| PERSON : rappel de mention / précision | 98,5 % [97,8–98,9] / 92,8 % |
| ADDRESS : rappel de mention / précision | 98,2 % [96,2–99,2] / 100 % |
| ORG / LOCATION (quasi) : rappel de mention | 29,0 % (76,1 % en strict) / 0,6 % |
| Rappel d'entité directe (TAB) | 98,4 % [97,9–98,8] |
| F2 (direct + quasi) | 93,4 % [92,7–94,1] |
| Documents avec fuite stricte / structurée | 11,8 % [8,9–14,7] / 4,6 % |
| Sur-masquage du texte neutre | 1,4 % [1,1–1,7] |
| Leurres masqués à tort | 4,0 % [3,1–5,0], dont 18,2 % des références légales |
| Débit indicatif pendant l'évaluation | 0,28 M car./s (contre 0,45 à 0,79 M car./s dans les exécutions de l'instantané A) |

Faux positifs typiques du détecteur de noms : « B du CGI » (dans « 293 B du CGI »), « FACTURE N »,
titres en capitales (« COMPTE RENDU DE L'ASSEMBLÉE GÉNÉRALE »), « Câble », « Audit », « Her French ».

Équipe rouge sur les entités textuelles (noms, adresses, organisations ; survie) : 100 % pour les espaces Unicode, les invisibles Cf, la
pleine chasse, les sosies grecs et les accents retirés ; 99 % pour les tabulations, 97 % pour « NOM
Prénom », 95 % en capitales ; mais **28 % en minuscules**, **8 % avec accents décomposés (NFD)**, 43 à
49 % avec un retour à la ligne, 86 % avec des sosies cyrilliques, 16 % en lettres mathématiques et
moins de 1 % avec U+FE0F ou U+034F.

Le banc de performance a relevé, sur ce code en cours d'écriture, une croissance super-linéaire sur la
répétition de mots en capitales (temps en n^1,2 à n^1,7 : 800 k car. en 3,5 s au lieu d'environ 0,15 s)
et l'exception ci-dessus sur l'entrée mixte de 1 M car.

### 6.7 Revue adverse (24 octobre 2026, soir)

Une revue adverse a cherché à casser le banc lui-même et le moteur. Arbre du soir, profil standard, poste
partagé : seuls les rapports avant/après et les exposants comptent, pas les durées absolues. Les correctifs
du cœur ont été **simulés en mémoire** (aucun fichier du cœur modifié), comme en section 8.1.

**Coût quadratique sur une longue ligne : déni de service.** Les nouvelles entrées adverses du banc
(`tools/bench`) répètent un motif réaliste sur une seule ligne :

| Entrée répétée | Taille | Avant | Correctif simulé |
|---|---|---|---|
| « 12 rue de la Paix, 75011 Paris ; » (liste d'adresses) | 100 k car. | **32,4 s** (exposant 2,05) | 0,40 s (1,00) |
| « 12 rue de la Paix » | 40 k car. | 7,6 s (2,13) | 0,22 s (0,92) |
| adresse sur trois lignes avec complément | 100 k car. | 2,0 s (1,82) | 0,26 s (1,09) |
| « Nom : Dupont » | 400 k car. | 3,3 s (1,72) | 1,4 s (1,07) |
| « DUPONT » | 400 k car. | 1,6 s (1,29) | 0,67 s (0,97) |
| « entrepreneur individuel SIRET … » | 400 k car. | 1,6 s (1,39) | 0,75 s (1,02) |

Causes : dans `heuristics/fr_address.py`, `_complement` cherche un complément depuis le début de la
ligne pour chaque voie (et copie ce préfixe), et `_before` parcourt toutes les voies du document pour
chaque code postal ; dans `heuristics/fr_names.py`, `_line_start` copie le début de ligne de chaque
candidat, `_line_style` et `_labels` remontent jusqu'au début du texte (`rfind`). Correctif : borner les
recherches arrière (un complément tient en 320 caractères, une liaison `_LINK_RE` en 15) et précalculer
les débuts de ligne. Sorties **identiques** sur 900 documents (540 de base, 360 mutés avec retours à la
ligne, CRLF, tabulations, doubles espaces, espaces insécables, majuscules), temps linéaire. Les
responsables des heuristiques ont depuis borné ces recherches (fenêtres de 160 et 24 caractères,
recherche dichotomique des voies, `line_bounds`) : sur l'arbre actuel, les 30 entrées adverses du banc
(200 k car.) ont un exposant de croissance de 0,69 à 1,13 et un débit d'au moins 0,20 M car./s, sans
aucune alerte (`python -m tools.bench.bench --quick --profiles standard --no-memory`). Ces entrées restent
dans le banc comme tests de non-régression. Le même passage mesure 0,34 M car./s sur 100 k car. mixtes
(0,92 à l'instantané A, avant les détecteurs de texte) et 1,07 M car./s sur du texte sans donnée
personnelle (2,85) ; le pack FR, heuristiques comprises, prend 56 % du temps. Le poste était chargé :
à remesurer sur poste calme avant toute conclusion.

**Quatre nouveaux opérateurs** (135 documents de base ; survie, voir section 4) :

| Opérateur | Identifiants structurés | Entités textuelles | Détail |
|---|---|---|---|
| `hangul_filler` (U+3164 inséré) | 13,8 % (n = 588) | 49,3 % (n = 619) | **0 %** pour NIR, IBAN, téléphones, cartes, SIRET, RIB |
| `letter_spacing` (« 0 6 1 2 … ») | 2,2 % | 4,7 % | titres espacés des PDF |
| `pdf_hyphenation` (« Du-⏎pont ») | – | **0 %** (n = 616) | tous les noms et adresses coupés |
| `markdown_bold` (« **…** ») | 93,9 % | 97,3 % | n° client, IPP, PDL : 0/25 ; dates de naissance : 39/50 |

Sur le même arbre : `variation_selector` 0 % / 0 %, `line_break` 4,8 % / 57,4 %. Corpus de base : rappel
direct 99,2 % [98,9–99,4], précision 98,2 %, documents avec fuite stricte 9,4 % [7,0–12,0] et structurée
4,6 %, aucun plantage. Deux correctifs simulés laissent le corpus de base **strictement inchangé**
(rappel, précision, leurres) : `FR_CONTEXTUAL_ID` qui tolère l'emphase Markdown autour du libellé et de la
valeur (gras, structurés : 552 → 577 sur 588, n° client 0 → 25 sur 25) ; la césure de fin de ligne
recollée dans le texte de détection, positions conservées (0 → 609 sur 616). U+3164 relève du correctif
de normalisation de la section 8.1 (caractères « default ignorable »).

**Corrections de l'outillage.** Elles ne changent aucun chiffre des instantanés A et B (les zones du
moteur sont disjointes et dans les bornes) mais rendent les scorers sûrs pour toute entrée :

- `metrics` : une zone qui en englobe d'autres échappait à la recherche de la zone dominante (confusions
  et IoU faux) ; une zone hors bornes agrandissait le masque et décalait silencieusement tous les
  calculs (elle lève maintenant une erreur) ; la forme canonique retire aussi les « default ignorable ».
- `evaluate` : le rapport Markdown plantait quand tous les documents faisaient planter le moteur (débit
  indéfini), c'est-à-dire quand il est le plus utile ; arguments validés ; fins de ligne LF.
- `bench` : un démarrage à froid bloqué arrêtait tout le banc ; une sortie illisible d'un sous-processus
  aussi ; les entrées « 1k … 1M » faisaient 2 caractères de moins qu'annoncé ; l'état des préfiltres est
  désormais calculé par le code du moteur (`DetectionContext.has`) et non par une copie qui divergeait
  (chiffres Unicode) ; 11 entrées adverses ajoutées ; le rapport indique les pays réellement chargés.
- `generate` : NIR « 20 » des natifs de Corse d'avant 1976 ; gabarits anglais marqués `en`.

## 7. Faiblesses constatées

Classées par gravité. Les correctifs touchant le cœur relèvent des responsables des modules concernés ;
ceux qui ont été simulés et mesurés figurent dans la section 8.

Ajouts de la revue adverse (section 6.7), par gravité :

- A. **Coût quadratique sur une longue ligne** (adresses, noms) : déni de service par un simple document
  de 100 k car. ; corrigé depuis par les responsables, gardé dans le banc comme non-régression.
- B. **Césure de fin de ligne des PDF** (« Du-⏎pont ») : 0 % de survie des noms et adresses.
- C. **Valeur en gras Markdown** : n° client, IPP, PDL jamais masqués, 22 % des dates de naissance perdues.
- D. **Remplisseur hangul U+3164** inséré dans un identifiant : 0 % de survie des NIR, IBAN, téléphones,
  cartes ; **lettres espacées** (« 0 6 1 2 … ») : 2 à 5 %.

Constats des instantanés A et B :

1. **Plantages du détecteur de noms** (instantané B) : 10,7 % des documents font lever une exception.
   Ce n'est pas une fuite (rien n'est produit) mais le service devient indisponible pour ces documents.
   Cause : un `re.match(...)` dont le résultat `None` n'est pas testé (`_AFTER_EPONYM_RE` exige une
   espace après l'éponyme ; il échoue avant une virgule, une fin de ligne ou la fin du texte).
2. **Noms encore visibles** : 11,8 % des documents laissent fuir un identifiant direct (instantané B) ;
   noms en minuscules, à accents décomposés ou coupés par un retour à la ligne.
3. **Identifiants coupés par la mise en page** : retour à la ligne, tabulation ou double espace dans un
   IBAN, un NIR, une carte (survie 0 à 7 %). C'est la sortie normale d'une extraction PDF ou OCR.
4. **Évasion par caractères invisibles non retirés** : U+FE0F et U+034F (catégorie Mn, « default
   ignorable ») insérés dans une valeur la rendent invisible au moteur (survie ≈ 0 %), alors que les
   invisibles Cf sont neutralisés.
5. **Chiffres en exposant** (7 %), **lettres mathématiques** (e-mails, IBAN, plaques, noms) et **accents
   décomposés** : non ramenés à la forme canonique par la normalisation.
6. **Grammaires de groupement rigides** : IBAN avec points, cartes, SIRET, RIB et TVA regroupés
   autrement que la norme ; RPPS, CNI et passeports avec séparateurs.
7. **RIB présenté champ par champ** (« Code banque : … Code guichet : … ») : 0 %, alors que c'est la
   présentation d'un relevé d'identité bancaire.
8. **Mobiles des DOM en forme locale** (« 0692 12 34 56 », usuelle à La Réunion et aux Antilles) :
   3,4 % des documents contenant un téléphone fuient.
9. **Tableaux Markdown** : le contexte d'en-tête (« Date de naissance », « Matricule ») ne s'applique pas
   aux cellules ; 38,6 % des dates de naissance et la plupart des matricules restent visibles. Le mode
   tableur (`analyze_segments` avec en-têtes forcés) existe, mais pas pour les tableaux d'un document.
10. **E-mails maquillés mixtes** (`&#64;`, `%40`, vrai « @ » avec « [dot] » ou « (point) ») : 0 %.
11. **Sur-masquage** (sans risque de fuite, mais coût d'utilité) : motif CARD sur des SIRET compacts de
    14 chiffres et des EAN-13 ; fenêtre « entrepreneur individuel » de 200 caractères qui fait masquer
    les identifiants des sociétés clientes du même document ; dates d'embauche proches d'une date de
    naissance ; titres en capitales et références légales pris pour des noms (instantané B).
12. **OCR** (0/O, 1/l…) : 6,5 % ; attendu sans traitement dédié, priorité basse.
13. **Performance** : croissance super-linéaire du détecteur de noms (point 1) ; 12 motifs sans préfiltre
    (FR_TVA, FR_RCS, FR_RCS_PERSON, FR_EORI, FR_RNA, FR_PLATE_SIV, FR_PLATE_SIV_LOOSE, FR_PLATE_FNI,
    FR_CONTEXTUAL_ID, FR_BIRTH_DATE_TEXT, MAC, BTC) ; préfiltre « pass » de SECRET_PASSWORD satisfait par
    « passeport » ; une itération Python par « @ » dans le détecteur d'e-mails (entrée adverse la plus lente).

## 8. Recommandations

### 8.1 Correctifs simulés et mesurés

Chaque correctif a été appliqué **en mémoire** dans un processus neuf (aucun fichier du cœur modifié),
puis le corpus de base et l'équipe rouge complets ont été rejoués (profil standard, arbre de
l'instantané B). Aucun n'a fait baisser le rappel ; la précision globale est restée à ±0,1 point (pour
l'e-mail, une seconde mesure isolée donne exactement les mêmes faux positifs et le même temps).

| Correctif | Effet mesuré |
|---|---|
| Normalisation (`_text.py`) : retirer aussi les caractères « default ignorable » (U+034F, U+115F-1160, U+17B4-17B5, U+180B-180F, U+3164, U+FE00-FE0F, U+FFA0, U+E0100-E01EF) et les marques combinantes U+0300-036F ; ramener exposants, indices et lettres mathématiques à l'ASCII | identifiants : U+FE0F et U+034F 0 → 100 %, exposants 7 → 100 %, lettres mathématiques 56 → 100 % ; noms : NFD 8 → 100 %, lettres mathématiques 16 → 100 % ; précision 96,71 → 96,75 % |
| `SEP` : tabulation et une à trois espaces | tabulations 0 → 76 %, doubles espaces 7 → 58 % |
| `IbanDetector` : séparateurs « . », tabulation, retour à la ligne | points 63 → 78 %, retours à la ligne 5 → 18 %, tabulations 0 → 20 % |
| `FR_PHONE` : forme 4-2-2-2 (« 0692 12 34 56 ») | PHONE 97,9 → 100 % ; documents avec fuite structurée 4,6 → 2,1 % |
| Validateur de carte : longueurs par réseau (13 : Visa ; 14 : Diners 30/36/38/39 ; 15 : Amex 34/37) | précision CARD 78 → 100 % ; EAN-13 masqués 7,4 → 0 % ; identifiants de sociétés masqués 26 → 20 % |
| `EMAIL_OBFUSCATED` : `&#64;`, `&commat;`, `%40`, « @ » suivi de « [dot] » ou « (point) » | 0 → 100 % pour ces quatre maquillages ; aucun nouveau faux positif, temps inchangé |
| Fenêtre « entrepreneur individuel » : 200/200 → 120/40 caractères | précision SIREN 32 → 100 %, SIRET 71 → 100 % ; identifiants de sociétés masqués 26 → 7 % ; rappel des SIREN/SIRET d'entrepreneurs inchangé (100 %) |
| Revue : recherches arrière bornées dans `fr_address` et `fr_names` | sorties identiques sur 900 documents ; 32,4 s → 0,40 s sur 100 k car. (exposant 2,05 → 1,00) ; depuis intégré par les responsables |
| Revue : `FR_CONTEXTUAL_ID` tolère `*`/`_` (1 à 3) après le libellé et avant la valeur | gras Markdown : n° client 0 → 25 sur 25, identifiants structurés 93,9 → 98,1 % ; corpus de base inchangé |
| Revue : césure « lettre-⏎lettre » recollée dans le texte de détection (positions conservées) | césure PDF : noms et adresses 0 → 98,9 % ; corpus de base inchangé |

### 8.2 Autres recommandations, par priorité

1. **Détecteur de noms** : tester le `None` de `_AFTER_EPONYM_RE.match` (plantages), borner le travail
   par jeton pour supprimer la croissance super-linéaire, exclure les titres entièrement en capitales et
   les références légales (« B du CGI »), puis relancer `tools.eval.evaluate` ; cible indicative
   PERSON ≥ 0,93 de rappel et aucun plantage, sur ce corpus **et** sur un jeu réel.
2. **Retours à la ligne** dans les identifiants à clé forte (NIR, carte, SIRET, RIB) : admettre un saut
   de ligne unique entre deux groupes (la clé borne le risque de faux positif) et généraliser l'approche
   du NIR (séparateur facultatif entre chaque caractère) aux cartes, SIRET, RIB et TVA.
3. **Détecteur de RIB en champs** : repérer la séquence « code banque / code guichet / n° de compte /
   clé », recomposer, valider la clé RIB, masquer les quatre champs.
4. **Tableaux Markdown** : appliquer aux tableaux d'un document le mécanisme d'en-têtes forcés du mode
   tableur (une colonne « Date de naissance » ou « Matricule » donne son contexte à chaque cellule).
5. **Performance** : préfiltres bon marché pour les motifs qui n'en ont pas (« fr » pour TVA et EORI,
   « rcs », « né »/« nee » pour les dates de naissance en toutes lettres, `digit` pour BTC et les plaques
   SIV), préfiltre de SECRET_PASSWORD borné au mot (« password », « passwd », « pwd », « mot de passe »,
   « mdp ») ; le banc `tools/bench` mesure l'effet (table des motifs coûteux).
6. **Évaluation** : ajouter un jeu réel ou consenti d'au moins 300 documents annotés, jamais utilisé
   pour régler le moteur, et les jeux externes sous licence compatible (FR-PII-Bench v0, MAPA FR, TAB) ;
   intégrer à la CI les tests de fumée (dont « aucun plantage ») et un seuil de non-régression par
   libellé (baisse ≤ 0,5 point).

## 9. Fichiers

| Fichier | Rôle |
|---|---|
| `tools/eval/schema.py` | schéma annoté, libellés de référence, JSONL |
| `tools/eval/ids.py` | générateurs d'identifiants valides (clés recalculées) |
| `tools/eval/lexicon.py`, `templates.py` | lexiques et gabarits |
| `tools/eval/generate.py` | générateur déterministe (CLI) |
| `tools/eval/mutate.py` | 51 opérateurs de l'équipe rouge (CLI) |
| `tools/eval/metrics.py` | scorers purs, Wilson, bootstrap |
| `tools/eval/evaluate.py` | exécution, synthèse, rapports JSON et Markdown (CLI) |
| `tools/bench/bench.py` | débit, latence, démarrage à froid, mémoire, 30 entrées adverses, coût des motifs (CLI) |
| `tests/eval/` | tests du banc : identifiants (oracle python-stdnum), générateur, mutations, métriques, exécution, banc de performance, fumée (`test_eval_smoke.py`) |
| `benchmarks/results/` | rapports des instantanés A et B et du banc de performance |
