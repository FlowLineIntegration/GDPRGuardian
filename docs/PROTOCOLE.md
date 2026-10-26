# Protocole public d'auto-évaluation de Gardien RGPD

> **English summary.** GDPR Guardian rates itself under this public protocol, version 1.0, **written on
> 25 October 2026, before any campaign, and registered by publishing its digests before the launch** (section 15).
> The **confidence index** is the share of documents in which **no direct identifier stays readable** (strict: not
> one alphanumeric character of a gold direct-identifier mention left in the output), computed per corpus family,
> then averaged with **equal weight** over the seven families of the French scope (synthetic FR, red-team mutations
> FR, BODACC, BOAMP, ParlaMint-FR, old French press, MAPA FR), with a 95% interval from a stratified bootstrap over
> documents (2,000 resamples, seed 20261025). Real corpora count on their **test half**, never used to design rules
> (earlier measurements of these halves are all listed in section 3). Every document goes through the **real
> production service** (Unix socket, local token, counted as "protocol" in the public statistics): 1,019,385
> documents, of which 1,010,907 synthetic and 8,478 real; yet **five sevenths of the weight rest on the 3,164 scored
> real test-half documents, 6 of them MAPA FR**. One campaign = one engine: the service image and the service's
> outputs on a fixed probe are checked from start to end. Failures count as leaks; volume never buys weight; the
> index is published only next to precision and over-masking, and only if pre-registered guards hold. Scores only
> are published, never text. The full English version is section 14.

Version **1.0**, écrite le **25 octobre 2026**, avant toute campagne. Elle est **enregistrée** par la publication,
avant le lancement, des empreintes de ce texte, de [`tools/protocol/spec.py`](../tools/protocol/spec.py) et du paquet
de l'outil (section 15) ; chaque résultat recopie les empreintes de ce qui l'a produit. Les définitions exécutables
sont dans `spec.py`, source unique de vérité de ce document ; l'outil est [`tools/protocol/`](../tools/protocol/), ses
tests [`tests/protocol/`](../tests/protocol/). Toute modification d'une définition fait une **nouvelle version
datée** ; l'ancienne reste dans l'historique du dépôt et chaque résultat publié cite la version qui l'a produit. Texte
complété le 26 octobre 2026, avant l'enregistrement et avant toute campagne : mesures antérieures des moitiés `test`
(section 3), campagnes répétées, écarts déclarés, refus au départ (section 9) ; aucune définition de l'indice n'a
changé.

## 1. Ce que l'on mesure

Une seule question : **dans quelle part des documents le service laisse-t-il lisible au moins un identifiant
direct ?** Gardien RGPD est une première barrière, pas une promesse de « zéro fuite » ; l'indice dit combien de fois
la barrière a tenu, document par document, sur des documents dont on connaît la vérité (le « gold »).

- **Indice de confiance** : part des documents sans aucune fuite, calculée famille par famille, puis moyenne à
  **poids égal** des sept familles du périmètre français ; intervalle de confiance à 95 %.
- **Rappel des mentions directes** : part des mentions d'identifiants directs entièrement masquées, mêmes familles,
  même poids égal.
- Tous les autres chiffres (section 6) sont publiés à côté, jamais à la place.

## 2. Familles et corpus

### Périmètre français : les sept familles de l'indice

| # | Famille | Source | Documents (tous / moitié test, dont avec mention directe) | Gold | Erreur du gold mesurée | Licence |
|---|---|---|---|---|---|---|
| 1 | Synthétique FR | générateur `tools/eval/generate.py` (Faker 40.43.0 `fr_FR`, lexiques), 9 types de documents, 30 gabarits, leurres à ne pas masquer ; graines 2026102501 à 2026102510, 45 000 documents chacune | 450 000 (tous comptent) | exact par construction | 0 (positions rendues) | MIT (dépôt) |
| 2 | Équipe rouge FR | les 51 opérateurs de `tools/eval/mutate.py` (11 familles : espaces Unicode, invisibles, chiffres de substitution, sosies, tirets, séparateurs, mise en page, OCR, casse, accents, courriels maquillés) appliqués à 12 000 documents de base (graines 2026102521 à 2026102530, 1 200 chacune) | 548 907 documents mutés (décompte exact à blanc) | exact par construction | 0 | MIT |
| 3 | BODACC | annonces commerciales nommant une personne physique, parutions de septembre 2026 (`tools/corpus/build_bodacc.py`) | 2 693 / 1 335 (1 335) | exact par construction | 0/274 mentions (borne haute 95 % : 1,4 %) ; contre-relecture 0/83 | Licence Ouverte (Etalab) |
| 4 | BOAMP | avis de marchés 2022-2023, schéma `IDENTITE` (`tools/corpus/build_boamp.py`) | 3 000 / 1 477 (1 408) | exact pour e-mail, téléphone, adresse ; noms des contacts par règle | 6/287 mentions = 2,1 % [1,0–4,5] ; contre-relecture 3/96 = 3,1 % [1,1–8,8] | Licence Ouverte (Etalab) |
| 5 | ParlaMint-FR | débats de l'Assemblée nationale, ParlaMint 5.0 | 300 / 144 (143) | partiel : orateurs et personnes de la liste du corpus | non mesurée ; exact là où il annote, incomplet ailleurs | CC BY 4.0 |
| 6 | Presse ancienne FR | Europeana Newspapers FR (515 / 245, dont 209) et HIPE-2022 NewsEye FR (140 / 72, dont 63), regroupés en **une** famille | 655 / 317 (272) | manuel (auteurs des corpus) | non mesurée par nous ; HIPE inclut des titres (« abbé ») dans les noms | CC0 ; CC BY 4.0 |
| 7 | MAPA FR | textes juridiques de l'UE en français (EUR-Lex) | 12 / 8 (6) | manuel, un annotateur | non mesurée | CC BY 4.0 |

Les révisions figées, les sources et la construction du gold sont dans [`CORPUS_REELS.md`](CORPUS_REELS.md)
(sections 3 et 4 ; version anglaise : section 11) et
[`tools/corpus/real_registry.py`](../tools/corpus/real_registry.py). Environ 6 % des documents
synthétiques viennent de deux gabarits en anglais (un ticket, un e-mail) d'un contexte français : ils restent dans
la famille, comme dans l'évaluation de développement. Les 12 000 documents de base de l'équipe rouge passent
aussi par le service (pour mesurer la survie aux mutations) mais ne comptent pas dans l'indice.

### Hors périmètre, publiés à part et en évidence

| Corpus | Langue | Documents | Pays envoyés au service |
|---|---|---:|---|
| MAPA DE, ES, IT, NL, PT | de, es, it, nl, pt | 12, 9, 12, 12, 12 | DE, ES, IT, NL, PT |
| MEDDOCAN (identifiants de substitution) | es | 1 000 | ES |
| German LER (décisions fédérales) | de | 334 | DE |
| TAB (CEDH) | en | 127 | FR (pas de pack anglais) |

Mêmes chiffres que le périmètre français, jamais mêlés à l'indice. Le 25 octobre 2026, les packs DE, ES, IT, NL et
PT ne masquaient **aucun** nom : ces corpus le montrent.

### Témoin négatif : Judilibre (précision seulement)

300 décisions déjà pseudonymisées par les juridictions (Cour de cassation, cours d'appel, tribunaux judiciaires),
sans gold. Publiés : zones masquées pour 10 000 caractères et part des décisions avec au moins une zone. La part de
faux positifs ne se mesure que par relecture manuelle (dernière : 25 octobre 2026, 31,7 % [24,0–40,4] de 120
zones relues) ; la campagne ne la refait pas.

### Pas de documents bureautiques

Aucun jeu de documents bureautiques (PDF, Word, Excel) annoté n'existe dans le dépôt : la version 1.0 du protocole
mesure la route texte (`POST /v1/anonymize/text`) et non la conversion des fichiers. C'est une limite (section 12).

## 3. Sur quoi les règles ont été conçues : dev, test, graines

- **Corpus réels.** Partition fixe, écrite le 25 octobre 2026 avant toute modification des règles : SHA-256 de
  `gdprguardian-rules2-2026-10-25|<identifiant du document>`, premiers 32 bits pairs → `dev`, impairs → `test`
  ([`tools/corpus/real_common.py`](../tools/corpus/real_common.py), `split_of`). Les règles sont retouchées sur les
  moitiés `dev` à partir du 25 octobre 2026, jusqu'au **gel du moteur** avant la campagne (le moteur gelé est
  identifié dans les résultats par l'image du service et l'empreinte de ses sorties, section 9). **L'indice compte la
  moitié `test`**, jamais utilisée pour concevoir une règle. Les deux moitiés passent quand même par le service :
  l'indice sur tous les documents et sur la moitié `dev` sont publiés à côté, et l'écart `dev` − `test` mesure le
  sur-ajustement.
- **Mesures déjà faites sur les moitiés `test`** (toutes, avant la campagne ; aucune règle ne doit être réglée sur
  ces chiffres ; liste recopiée dans chaque résultat depuis `spec.TEST_HALVES_MEASURED_BEFORE`) :

  | Date (UTC) | Qui, quoi | Moteur | Résultat sur la moitié `test` |
  |---|---|---|---|
  | 25 oct. 2026 | analyse des corpus entiers ([`CORPUS_REELS.md`](CORPUS_REELS.md), sections 1 à 7), avant la partition | 1.0.0 de ce jour | rappels et fuites par corpus, pas d'indice |
  | 25 oct. 2026, 20 h 21 | mise au point du moteur : évaluation en processus des moitiés `dev` et `test`, avant toute retouche des règles ([`CORPUS_REELS.md`](CORPUS_REELS.md), section 12, colonne « avant ») | 1.0.0 | documents avec fuite stricte (définition de `tools/corpus`) : BODACC 93,0 %, BOAMP 52,8 %, ParlaMint-FR 27,3 %, Europeana 78,9 %, HIPE 98,4 %, MAPA FR 83,3 % ; pas d'indice |
  | 25 oct. 2026, 21 h 04 et 21 h 18 | essais de l'outil, plan réduit, corpus réels complets | sources de cet instant | indice 45,3 % [42,0–50,3] et 45,2 % [41,7–50,2] ; sans fuite : BODACC 8,0 %, BOAMP 47,2 %, ParlaMint-FR 72,7 %, presse ancienne 16,5 %, MAPA FR 16,7 % (synthétique 91,4 %, équipe rouge 64,5 %) |
  | 25 oct. 2026, 21 h 36 à 22 h 20 | mise au point du moteur : évaluation en processus des moitiés `test` et des corpus entiers à chaque itération des règles « rules2 » (quatre fois), et du moteur 1.0.0 sur les corpus entiers (21 h 53) ; la dernière publiée à 22 h 22 (`benchmarks/results/real-rules2-comparison-2026-10-25.{md,json}`, [`CORPUS_REELS.md`](CORPUS_REELS.md) section 12) | rules2 | documents avec fuite stricte (`tools/corpus`) : BODACC 10,1 %, BOAMP 39,4 %, ParlaMint-FR 7,0 %, Europeana 78,9 %, HIPE 98,4 %, MAPA FR 83,3 % ; pas d'indice |
  | 25 oct. 2026, 21 h 42 | audit indépendant de l'outil, plan réduit, corpus réels complets | sources de cet instant | indice 61,2 % [58,1–66,4] ; BODACC 89,4 %, BOAMP 55,5 %, ParlaMint-FR 93,0 %, presse ancienne 16,5 %, MAPA FR 16,7 % (synthétique 91,8 %, équipe rouge 65,5 %) |
  | 25 oct. 2026, 22 h 59 | relecture indépendante de la mise au point du moteur : évaluation en processus des moitiés `test` et des corpus entiers, moteurs 1.0.0 et rules2 (non publiée) | 1.0.0 et rules2 | mêmes chiffres que ceux publiés à 22 h 22 |

  Le fichier de comparaison du 25 octobre dit que les moitiés `test` n'ont pas été « regardées » : leurs erreurs n'ont
  pas été lues, mais leurs scores ont été mesurés à chaque itération et publiés ; elles figurent donc ici. Après ces
  mesures, tout essai doit se faire sur la **seule moitié `dev`** (`pack-real --split dev` pour l'outil,
  `evaluate_real.py --split dev` pour la mise au point du moteur) ; une campagne standard refuse un tel paquet. Toute autre mesure
  d'une moitié `test` faite avant la campagne s'ajoute à ce tableau et à `spec.TEST_HALVES_MEASURED_BEFORE` avant
  l'enregistrement (section 15).
- **Campagnes répétées.** Après la première campagne publiée, les moitiés `test` ne sont plus aveugles : leurs scores
  par famille sont connus de qui retouche les règles. Une campagne suivante sur les mêmes moitiés le déclare : elle
  liste les campagnes antérieures dans `spec.EARLIER_CAMPAIGNS` (nouvelle version datée du protocole), que chaque
  résultat recopie, et le report vers le site refuse une campagne répétée qui omet celle déjà publiée. Pour une
  version ultérieure du moteur, l'indice principal devra passer sur des données neuves, construites avec les mêmes
  outils sur une période jamais mesurée (par exemple des parutions BODACC et BOAMP postérieures au gel du moteur). Les
  ensembles « inédits » BODACC d'août 2026 et BOAMP 2021 ([`CORPUS_REELS.md`](CORPUS_REELS.md), section 12) ont
  déjà été mesurés le 25 octobre : ils ne sont plus aveugles non plus.
- **Synthétique.** Graines neuves (2026102501 à 2026102510 ; 2026102521 à 2026102530 pour l'équipe rouge). La graine
  de développement (20261024, l'évaluation de 540 documents qui a servi à régler le moteur) est **exclue par le
  code** : l'outil refuse un plan qui la contient.
- **Limite assumée.** L'analyse des faiblesses du 25 octobre ([`CORPUS_REELS.md`](CORPUS_REELS.md), section 7) a porté
  sur les corpus entiers, et les mesures du tableau ci-dessus ont vu les moitiés `test` : celles-ci ne sont pas
  aveugles aux *types* d'erreurs (numéros RCS des entrepreneurs, noms à particule, adresses BOAMP…) ; entre les deux
  essais, BODACC passe de 8,0 % à 89,4 % après une modification des règles, et les scores des
  moitiés `test` étaient visibles à chaque itération de rules2. Elles le sont aux valeurs : aucun nom ni numéro d'un corpus réel ne doit
  entrer dans le moteur, dont le code est public.

## 4. Ce qu'est un identifiant direct, par corpus

- **Synthétique et équipe rouge** : les libellés du gold de type `DIRECT` ([`tools/eval/schema.py`](../tools/eval/schema.py)) :
  PERSON, EMAIL, PHONE, ADDRESS, NIR, IBAN, RIB, RIB_SPLIT, CARD, SIRET et SIREN (entrepreneurs individuels seulement),
  VAT, TAX_ID, PASSPORT, ID_CARD, PLATE, RPPS, CAF, FRANCE_TRAVAIL, IP. Ne comptent pas : les quasi-identifiants
  (BIRTH_DATE, LOCATION, ORG, ID pour les numéros de client, de patient ou de matricule) et les leurres (montants,
  numéros de commande et de facture, références légales, identifiants de sociétés…).
- **Corpus réels** : les familles personnelles de `tools/corpus` sauf la date de naissance : PERSON, ADDRESS, EMAIL,
  PHONE, NATIONAL_ID, TAX_ID, IBAN, BANK_ACCOUNT, CARD, ID, URL, IP. Présentes : BODACC PERSON, ADDRESS, ID (numéro
  RCS/RM, c'est-à-dire le SIREN d'un entrepreneur individuel) ; BOAMP PERSON, ADDRESS, EMAIL, PHONE (quel qu'en soit le
  titulaire, souvent un organisme public : le moteur ne le sait pas) ; ParlaMint PERSON ; presse ancienne PERSON ;
  MAPA FR PERSON, ADDRESS. Conservés par politique, hors calcul : ORG, ORG_ID, LOCATION, DATE, OTHER.
- Une mention ne compte que si elle contient au moins un caractère alphanumérique.

## 5. Fuite, indice, intervalle

**Lisible.** Un caractère alphanumérique de l'entrée est lisible s'il figure encore, à sa place, dans la sortie du
service. Le service ne rend pas de positions : l'outil les retrouve en alignant la sortie sur l'entrée (balises
`[LIBELLE_N]`, caractères invisibles que la sortie retire). Quand un segment de texte entre deux balises peut se
placer à plusieurs endroits, tout caractère qui **peut** être visible compte comme visible (borne prudente).
Vérification en processus, sur 48 955 documents distincts (évaluation de développement et ses 6 192 mutations,
20 000 documents synthétiques neufs, 13 745 mutés, les 8 478 documents réels) : zones reconstruites identiques à
celles du moteur sur chaque document synthétique, aucune borne prudente prise en défaut (aucun caractère vraiment
visible manqué), et 3 documents réels seulement (BODACC 1, BOAMP 2 ; 10 caractères en tout) où la borne prudente
compte comme visibles des caractères en fait masqués.

**Fuite.** Un document fuit dès qu'**un** caractère alphanumérique d'**une** mention d'identifiant direct du gold
reste lisible (le dernier chiffre d'un téléphone suffit).

**Échecs.** Un document que le service refuse ou n'arrive pas à traiter (toute erreur HTTP après les reprises), ou
dont la sortie ne s'aligne pas, compte comme une **fuite**, toutes ses mentions directes non masquées.

**Documents sans mention directe** : exclus de l'indice (ils le gonfleraient), comptés et publiés.

**Formules.** Pour chaque famille *f* : *P<sub>f</sub>* = documents sans fuite / documents ayant au moins une mention
directe. **Indice = (1/7) · Σ<sub>f</sub> *P<sub>f</sub>***, sur les sept familles, quelle que soit leur taille : un
million de documents synthétiques pèsent autant que les 6 documents MAPA FR de la moitié test. **Rappel des mentions
= (1/7) · Σ<sub>f</sub> (mentions directes entièrement masquées / mentions directes)**. Sans les sept familles, pas
d'indice.

**Intervalle à 95 %.** Bootstrap stratifié sur les **documents** : dans chaque famille, on tire avec remise autant de
documents qu'elle en compte ; 2 000 tirages, graine 20261025, percentiles 2,5 et 97,5. Le tirage s'appuie sur
l'histogramme des issues par document (mentions directes, mentions masquées) : le nombre de documents tirés dans
chaque case suit exactement une loi multinomiale, tirée par binomiales successives, soit la même loi qu'un tirage
document par document, sans tableau d'un million d'entrées ([`tools/protocol/stats.py`](../tools/protocol/stats.py),
test d'équivalence dans [`tests/protocol/test_stats.py`](../tests/protocol/test_stats.py)). Même méthode pour
l'intervalle du rappel des mentions.

**Ce que l'intervalle ne couvre pas.** Il ne mesure que le hasard du tirage des documents : ni les erreurs du gold
(section 2), ni le choix des sept familles, ni la dépendance entre documents mutés (les ~46 variantes d'un même
document de base sont retirées comme si elles étaient indépendantes, ce qui rend trop étroit l'intervalle de la famille
équipe rouge). Un seul document MAPA FR (6 notés) déplace l'indice de 1/6 × 1/7 ≈ 2,38 points : MAPA FR fait à lui
seul l'essentiel de la largeur de l'intervalle (environ 95 % de sa variance dans les essais).

## 6. Autres chiffres publiés

- **Par famille** : part des documents sans fuite (intervalle de Wilson), rappel des mentions, rappel par type
  d'identifiant, erreurs du service, alignements ambigus.
- **Familles synthétiques** (définitions de `tools/eval`) : rappel au caractère (directs, structurés, tous), précision
  (caractères masqués tombant sur une donnée personnelle du gold), sur-masquage du texte neutre, leurres masqués à tort,
  taux de fuite au sens de `tools/eval` (strict, structuré, littéral), rappel des entités.
- **Corpus réels** (définitions de `tools/corpus`, moitié test, moitié dev et tous les documents) : rappel strict et à
  80 % des mentions, rappel au caractère, précision avec intervalle bootstrap (précision non mesurable sur
  ParlaMint), sur-masquage, documents qui fuient (strict et littéral), familles conservées touchées.
- **Équipe rouge, par opérateur** : part sans fuite, rappel des mentions, **survie** (mentions masquées sans mutation
  qui le restent après).
- **Par graine** : part sans fuite (stabilité d'une graine à l'autre).
- **Hors périmètre**, dans une section à part des résultats, jamais mêlée au périmètre français, et **témoin
  Judilibre** : section 2.
- **Historique** : mesures des moitiés `test` faites avant la campagne et campagnes antérieures (section 3).
- **Écarts déclarés** : tout écart permis à la procédure (swap actif, service redéployé après la fin de la campagne),
  inscrit par `run-protocol.sh` dans le point de reprise et les résultats, et rappelé par le report vers le site.
- **Campagne** : documents, débit, temps cédé aux visiteurs, reprises, erreurs, empreinte du moteur (image du
  service, version, packs, sorties sur la sonde) et nombre de contrôles du moteur, jeton local reconnu ou non,
  empreinte du plan, empreintes SHA-256 des documents synthétiques, mutés et réels envoyés.
- **Enregistrement** : empreintes de l'outil (fichiers `tools/`, `spec.py`, ce texte, paquet, Faker) et
  comparaison du décompte envoyé (documents, empreintes) au décompte enregistré dans `spec.py` (section 15).

Fichiers : `benchmarks/results/protocol-<date>.json` et `.md`. Le site reçoit dix clés (section 10).

## 7. Garde-fous : l'indice seul pourrait mentir

Un moteur qui masquerait tout obtiendrait 100 %. L'indice n'est donc publié que si, sur la même campagne :

| Garde-fou | Seuil | Mesure de référence (25 octobre 2026) |
|---|---|---|
| Sur-masquage du texte neutre, familles synthétiques | ≤ 2 % | 0,08 % |
| Leurres masqués à tort, famille synthétique | ≤ 10 % | 3,5 % |
| Précision au caractère, BODACC et BOAMP (moitié test) | ≥ 70 % chacun | 90,1 % et 80,9 % (tous documents) |

Le script de report vers le site refuse sinon ; le forcer (`--force-guards`) oblige à le déclarer publiquement. La
précision et le sur-masquage sont toujours publiés à côté de l'indice.

## 8. Ce qui pourrait embellir l'indice, et ce que le protocole y oppose

| Ce qui embellirait | Ce que fait le protocole |
|---|---|
| Régler les règles sur les documents mesurés | indice sur la moitié `test` ; graines neuves ; graine de développement refusée par le code ; écart `dev` − `test` publié ; toute mesure antérieure des moitiés `test` listée (section 3) et recopiée dans les résultats |
| Répéter la campagne sur des moitiés `test` déjà vues | campagnes antérieures listées dans `spec.EARLIER_CAMPAIGNS` et recopiées dans les résultats ; report vers le site refusé si la campagne publiée manque ; données neuves pour un moteur suivant |
| Taire un écart à la procédure | écarts permis (swap, redéploiement après la fin) inscrits dans les résultats et rappelés par le report vers le site ; `--force-guards` à déclarer |
| Données synthétiques faciles (mêmes gabarits que ceux sur lesquels le moteur a été réglé : les valeurs changent, pas les mises en page) | synthétique et équipe rouge ne pèsent que 2/7, quel que soit leur volume ; chaque famille est publiée |
| Le volume | poids égal par famille |
| Tout masquer | garde-fous ; précision, sur-masquage et leurres publiés à côté |
| Écarter les documents difficiles, les erreurs | une erreur ou une sortie non alignable compte comme une fuite ; documents sans gold comptés et publiés |
| Une définition indulgente de la fuite | stricte : un seul caractère alphanumérique visible suffit |
| Un alignement complaisant | borne prudente : ce qui peut être visible compte comme visible |
| Arrêter la campagne quand le chiffre plaît, garder le meilleur essai | tailles fixées ici ; la campagne va à son terme ; aucun rapport final sur une campagne incomplète ; une campagne terminée ne se relance pas dans le même dossier ; chaque campagne publiée, datée (une campagne abandonnée garde un rapport partiel, à déclarer) |
| Changer de moteur en cours de campagne | une campagne = un moteur : image du service, version, packs et sorties sur une sonde fixe contrôlés au départ, à chaque point de reprise, après toute panne ou tout redémarrage et à la fin ; un écart arrête tout, sans rien écrire après le dernier contrôle réussi ; `finish` revérifie l'image |
| Retoucher les définitions après coup | empreintes de `spec.py`, de ce texte et du paquet publiées avant le lancement et recopiées dans les résultats, recalculées depuis le contenu du paquet à chaque départ (un paquet modifié après sa construction est refusé) ; décompte du plan comparé à celui enregistré, report vers le site refusé sinon ; reprise refusée si l'outil change |
| Une surcharge du service comptée comme fuites (ou l'inverse) | `429`/`503` au-delà de 30 minutes pour un document : pause, jamais une fuite ; report refusé si une telle erreur a été comptée |
| Une campagne passée sans le jeton local (trafic compté comme public) | sonde `/health/deep` au départ : campagne standard refusée sans jeton reconnu ; report refusé sinon |
| Choisir le pays ou le profil qui arrange | réglages par défaut du produit : FR, `standard`, balises en français |
| Gold incomplet (ParlaMint, noms seuls non annotés) | il **favorise** l'indice : un nom non annoté n'est pas compté comme fuite ; c'est écrit ici et la famille ne pèse qu'un septième |
| Erreurs du gold (BOAMP 2,1 %) | elles jouent dans les deux sens ; taux mesurés publiés |
| Apprendre les valeurs des corpus publics (listes de noms) | moitié `test` jamais utilisée ; le moteur est public : toute liste tirée d'un corpus se verrait |

## 9. La campagne sur le serveur de production

- **Outil** : [`tools/protocol/`](../tools/protocol/), bibliothèque standard de Python plus Faker (MIT, pur Python),
  livré en un paquet autonome reproductible (`gg-protocol.pyz`, qui porte aussi ce texte). Il tourne dans un
  **conteneur jetable de l'image exacte du service en cours** (même Python 3.12) : aucun réseau, système en lecture
  seule, utilisateur 10001, aucune capacité, 2 Go de mémoire sans swap, aucun fichier core (`--ulimit core=0` : la
  mémoire de l'outil porte les corpus réels), un processeur à faible priorité (`--cpu-shares 256`), socket du service
  en lecture seule ; le jeton local arrive sur l'entrée standard depuis son fichier root 0600, jamais en argument ni
  sur disque ([`tools/protocol/server/run-protocol.sh`](../tools/protocol/server/run-protocol.sh)). Au départ,
  l'outil recalcule les empreintes du paquet depuis son contenu et refuse un paquet modifié après sa construction.
- **Refus au départ, avant toute requête** : une campagne standard (graines et tailles enregistrées) est refusée sans
  l'image du service, avec des tailles d'unité autres que celles enregistrées (les empreintes du plan en dépendent),
  avec un drapeau d'essai (`--allow-disk-real`, sonde fixée), ou avec un paquet de corpus réels réduit à la moitié
  `dev` ou privé d'un des quinze corpus (sans quoi l'indice manquerait après des heures de travail).
- **Jeton local vérifié** : au départ, l'outil interroge `/health/deep`, qui n'existe que pour le principal LOCAL ;
  sans jeton reconnu, une campagne standard est refusée (un essai continue, signalé comme trafic public).
- **Requêtes** : `POST /v1/anonymize/text` sur le socket Unix du service, **sans** `X-GG-Client` et **avec** le jeton
  local `X-GG-Local` : principal LOCAL, hors budgets par client, deux traitements à la fois au plus, jamais la place
  réservée aux petites requêtes. Chaque document envoie un datagramme d'usage `"src":"protocol"` : **toute la campagne
  compte dans les statistiques publiques du site, comme protocole** (sondes du moteur comprises). Options :
  `countries` FR (ou le pays du corpus hors périmètre), `profile` `standard`, `label_language` `fr`.
- **Une campagne = un moteur** : empreinte du moteur = image du conteneur du service (`docker inspect`, passée par
  `run-protocol.sh`), version, catalogue des packs et SHA-256 des **sorties** du service sur une sonde fixe (200
  documents de la graine de développement, jamais notés). Contrôlée au départ, avant chaque point de reprise (toutes
  les 60 secondes), après toute panne de connexion ou tout redémarrage du service (compteurs de `/status` en baisse)
  et à la fin. Un soupçon de redémarrage abandonne les unités en cours (refaites ensuite) et bloque les nouvelles
  jusqu'au contrôle ; une unité n'est comptée qu'après un relevé de `/status` sans redémarrage postérieur à sa fin.
  Un écart arrête la campagne sans rien écrire après le dernier contrôle réussi ; la reprise exige le même moteur ;
  `finish` vérifie encore que l'image du service est celle du début. Coût : 200 requêtes par minute de campagne
  (environ 1,5 % des requêtes ; une sonde dure 2 secondes environ sous WSL), prioritaires sur les fils de travail.
- **Priorité aux visiteurs** : l'ordonnanceur du service sert un visiteur en attente avant le traitement suivant de
  la campagne ; en plus, l'outil lit `/status` toutes les 2 secondes et ne garde qu'une requête en vol tant que
  quelqu'un d'autre occupe ou attend une place ; `429` et `503` sont respectés (`Retry-After`, gigue) ; au-delà de
  30 minutes d'attente pour un même document, la campagne se met en **pause** (une surcharge n'est jamais comptée
  comme une fuite). Mesuré sous WSL avec quatre visiteurs envoyant sans relâche des textes de 20 Ko : 95 % des
  réponses en 27 ms seuls, en 57 ms pendant la campagne (aucun refus) ; la campagne a cédé la place 24 secondes sur
  une minute.
- **Concurrence** : trois fils (deux en cours au service, un en file).
- **Reprise** : unités rejouables à l'identique (1 500 documents synthétiques, 30 bases d'équipe rouge, 100 documents
  réels) ; point de reprise atomique et durable (copie de la version précédente, `fsync`, retour à la copie si le
  dernier est illisible ; agrégats seulement) ; arrêt (`stop`, SIGTERM) = pause ; `start` reprend ; reprise refusée
  si le moteur, l'outil, le plan ou les corpus réels ont changé : ne pas redéployer le service pendant une campagne.
  Une erreur de notation d'un document compte comme une fuite (`exception:<type>`) ; une erreur de l'outil hors d'un
  document arrête la campagne avec son type, jamais en silence. Une campagne terminée ne se relance pas : `finish`
  archive son dossier de travail (`/var/lib/gg-protocol-<date>-<plan>`). Sur une campagne incomplète, `finish`
  n'efface rien (le paquet des corpus réels reste en mémoire vive si leurs unités ne sont pas faites) et `start` la
  reprend ; elle s'abandonne par `GG_PROTOCOL_ABANDON=1 bash run-protocol.sh finish`, qui garde un rapport partiel à
  déclarer.
- **Écarts permis, inscrits** : `GG_PROTOCOL_ALLOW_SWAP=1` (swap actif malgré tout) et
  `GG_PROTOCOL_REDEPLOYED_AFTER=1` (service redéployé après la fin de la campagne, avant `finish`) ne passent qu'en
  laissant une trace : `run-protocol.sh` les inscrit (`--disclose`) dans le point de reprise et les résultats, et le
  report vers le site les rappelle ; ils sont à déclarer avec l'indice.
- **Rien que des scores** : l'outil n'écrit ni n'affiche jamais un texte, une valeur annotée ou une sortie du service ;
  points de reprise et résultats ne contiennent que des compteurs, des bits (un par document) et des empreintes.
- **Corpus réels en mémoire vive seulement** : le paquet est copié dans `/dev/shm` (tmpfs), l'outil refuse un paquet
  hors mémoire vive, et `run-protocol.sh` refuse de travailler si un swap est actif (une page de tmpfs pourrait
  atteindre le disque ; `sudo swapoff -a` le temps de la campagne). Les corpus réels passent en premier (quelques
  minutes) ; dès leurs unités enregistrées, **l'outil efface le paquet**, l'oublie et l'inscrit aussitôt dans le
  point de reprise ; `finish` d'une campagne terminée ou abandonnée vide aussi `/dev/shm/gg-protocol`. Les corpus
  BODACC et BOAMP sont reconstruits depuis leur source le jour de la campagne si possible (demandes de suppression de
  la DILA), et le paquet local est effacé après la copie.
- **Durée** : mesurée sous WSL (16 cœurs, service local en mode public, jeton local, deux places LOCAL, outil dans
  un conteneur jetable) : 215 à 225 documents synthétiques par seconde, 2,4 ms de processeur client par document ;
  les 8 478 documents réels en 4 minutes environ, dont 3 pour les corpus hors périmètre (les moteurs DE, ES, IT, NL,
  PT ne sont pas préchargés : environ 0,3 s par requête). Le plan complet (1 019 385 documents) demande donc environ
  1 h 20 sur une telle machine. **Sur le serveur, la durée n'est pas mesurée** : avant la campagne, un essai
  chronométré (paquet de la seule moitié `dev`, plan réduit par `GG_PROTOCOL_ARGS`, section 10) donne le débit, d'où
  la durée du plan complet ; la campagne doit finir avant le redémarrage automatique de 03 h 30 UTC, sinon
  `GG_PROTOCOL_HOURS` la met en pause propre (par exemple au bout de 3 heures) et `start` la reprend plus tard.

## 10. Rejouer

Depuis la racine du dépôt (Python 3.12+), `DIR` hors du dépôt :

```
python tools/corpus/build_bodacc.py --cache DIR --per-family 500 --start 2026-09-01 --end 2026-09-30
python tools/corpus/build_boamp.py  --cache DIR --per-month 125 --start 2022-01 --end 2023-12
python tools/corpus/fetch_real.py   --cache DIR
python -m tools.protocol plan --count                      # sans service : nombres et empreintes ci-dessous
python -m tools.protocol bundle --out gg-protocol.pyz      # paquet autonome, reproductible au bit près
python -m tools.protocol registration --bundle gg-protocol.pyz   # empreintes à publier AVANT le lancement
python -m tools.protocol pack-real --cache DIR --out /dev/shm/gg/real-corpora.jsonl.gz
python -I gg-protocol.pyz run --socket /run/gdprguardian/app.sock --token-stdin --engine-id IMAGE --work WORK \
       --real /dev/shm/gg/real-corpora.jsonl.gz --wipe-real-when-done < /etc/gdprguardian/local-header
python tools/protocol/merge_quality.py WORK/results/protocol-<date>.json site/data/quality.json
```

`IMAGE` est l'image du conteneur du service (`docker inspect -f '{{.Image}}' <conteneur>`). Un service se lance comme
dans [`deploy/README.md`](../deploy/README.md) (mode public, `GDPRGUARDIAN_LOCAL_TOKEN_SHA256`). Pour un **essai**,
jamais publié : plan réduit (`--synthetic-docs`, `--redteam-bases`…) et paquet de la seule moitié `dev`
(`pack-real --split dev`), pour ne plus toucher aux moitiés `test`.

**Sur le serveur, dans l'ordre** ([`docs/PUBLISHING.md`](PUBLISHING.md) détaille les copies) : geler et déployer le
moteur ; refaire le contrôle croisé sur ce moteur (section 11) ; construire le paquet, `registration --bundle`, publier
ces empreintes ; `bash run-protocol.sh prepare` (refusé tant qu'un swap est actif : `sudo swapoff -a`) ; **essai
chronométré** avec un paquet `--split dev` et `GG_PROTOCOL_ARGS="--synthetic-docs 3000 --redteam-bases 30"`, puis
`status` (débit) et `finish` (résultats rangés à part dans `results/trial-<date>/`, jamais publiés) ; puis `prepare`
à nouveau, le paquet complet dans `/dev/shm/gg-protocol/`, `GG_PROTOCOL_HOURS=3 bash run-protocol.sh start`, `status` jusqu'à la fin,
`finish`, et le report vers le site. Empreintes attendues du plan (Faker 40.43.0),
enregistrées aussi dans `spec.REGISTERED_PLAN` et comparées par l'outil : 450 000 documents synthétiques, 12 000
bases, 548 907 documents mutés ; SHA-256 synthétique
`0b91be78435e5434ee5a3b136ab8f08dd10a2c3673dad56fc6dca469c87a955b`, équipe rouge
`d984ee1bf9dba70bf2ccf32957cab9da9bbf1fdf02adf5b7444956fa0137760b`. Les corpus BODACC et BOAMP viennent d'une API
vivante : leurs empreintes, publiées dans les résultats, peuvent changer d'un téléchargement à l'autre.

Clés du site (`site/data/quality.json`) : `confidence_index`, `confidence_ci_low`, `confidence_ci_high`,
`mention_recall_pct` (pourcentages à une décimale), `protocol_docs` (documents envoyés par la campagne, sondes du
moteur non comprises), `protocol_families` (7), `real_corpora` et `real_docs` (corpus réels annotés et leurs
documents, sans le témoin Judilibre), `protocol_date` (date ISO de la campagne), `protocol_engine` (version du service
et 12 premiers caractères de son image, par exemple `1.0.0+af877bdf62ae` : deux moteurs de même version restent
distincts). Tant qu'une campagne complète n'a pas eu lieu, elles valent « — » et le site affiche « pas encore
mesuré ».

## 11. Contrôle croisé de l'outil (fait avant la campagne, refait sur le moteur gelé)

**Méthode.** L'évaluation synthétique de développement (540 documents et 6 192 mutés, graine 20261024) passe par un
service local en mode public avec jeton local (socket Unix) ; l'outil reconstruit les zones masquées depuis la seule
sortie, puis les fonctions de `tools/eval` les notent. Chaque nombre du résumé (8 535 feuilles pour les mutés) est
comparé à l'évaluation **en processus du même moteur** (copie figée des sources, chargée par le service et par
l'évaluation) et au fichier de référence du dépôt ([`tools/protocol/crosscheck.py`](../tools/protocol/crosscheck.py),
commandes `crosscheck` puis `crosscheck-summary`). L'outil est validé quand, sur le même moteur, les dix indicateurs
principaux sont identiques, aucun document n'échoue et chaque autre écart est un effet de frontière : la frontière
entre deux balises séparées par une espace ne se lit pas dans la sortie, ce qui ne touche que les chiffres par
libellé du *système* (confusion, précision et F2 par libellé, taux typé, rappel strict d'entité), jamais ce qui est
masqué. Un écart avec le fichier de référence où le service et l'évaluation en processus s'accordent vient du moteur,
qui a changé depuis la référence (ou, pour les bornes d'intervalle, des tirages).

**Résultats.**

- **25 octobre 2026, 20 h 47 UTC, moteur d'avant rules2** : les dix indicateurs du service égalaient au bit près ceux
  de `eval-2026-10-25-standard.json` (rappel direct 99,18 %, précision 98,82 %, fuite stricte 9,07 %…). La partie
  « même moteur » de ce jour a chargé une copie prise pendant une retouche (2 documents en échec des deux côtés) :
  elle est remplacée ([`protocol-crosscheck-2026-10-25.md`](../benchmarks/results/protocol-crosscheck-2026-10-25.md),
  gardé pour l'historique).
- **26 octobre 2026, 00 h 04 UTC, copie figée des sources du moteur rules2** (empreinte de l'arbre `a992428d25533cc6`,
  moteur Python : le noyau natif installé ne faisait pas tourner ces sources ; empreinte de sonde `eeb38986e44c`, celle
  qu'une campagne enregistre pour un moteur aux mêmes sorties) : **outil validé** pour les pays `auto` et `FR` ; dix
  indicateurs identiques entre service et évaluation en processus (rappel direct 99,23 %, précision 98,82 %, fuite
  stricte 8,33 %), aucun échec ; 12 feuilles sur 773 (base) et 31 sur 8 535 (mutés) diffèrent, toutes par l'effet de
  frontière. Contre `eval-2026-10-25-standard-fr-rules2.json` (pays `FR`), les dix indicateurs sont identiques ; les
  10 feuilles des mutés qui diffèrent viennent du moteur, retouché depuis cette référence. Détail :
  [`protocol-crosscheck-2026-10-26.md`](../benchmarks/results/protocol-crosscheck-2026-10-26.md).
- Le moteur était encore en cours de mise au point pendant ce contrôle : il est **refait sur le moteur gelé**, avant
  l'enregistrement, et son empreinte de sonde doit égaler celle de la campagne.

## 12. Limites et biais connus

- Données synthétiques : gabarits connus du moteur ; l'équipe rouge ne couvre que 51 opérateurs.
- Gold : BOAMP 2,1 % d'erreurs mesurées ; ParlaMint partiel (favorable) ; titres dans les noms HIPE (défavorable) ;
  MAPA FR minuscule (6 documents notés dans la moitié test : un document déplace l'indice de 2,38 points).
- Poids réel : la campagne envoie plus d'un million de documents, mais cinq septièmes de l'indice reposent sur les
  3 164 documents notés des moitiés `test` réelles.
- L'intervalle ne couvre que le tirage des documents : ni les erreurs du gold, ni le choix des familles, ni la
  dépendance entre variantes mutées d'un même document (section 5).
- Moitiés `test` déjà mesurées avant la campagne (section 3, tableau) : par la mise au point du moteur avant les retouches
  (20 h 21 UTC) et à chaque itération des règles rules2 (21 h 36 à 22 h 20, publiée à 22 h 22), par deux essais de
  l'outil, par son audit et par la relecture de la mise au point du moteur. Leurs erreurs n'ont pas été lues, mais leurs scores
  étaient visibles pendant la mise au point : un réglage involontaire sur ces scores ne peut pas être exclu ; l'écart
  `dev` − `test` publié en donne la mesure.
- Après la première campagne publiée, les moitiés `test` ne sont plus aveugles : une campagne répétée le déclare
  (section 3) ; un moteur suivant demande des données neuves.
- Règles retouchées sur les moitiés `dev` à partir du 25 octobre 2026, jusqu'au gel du moteur ; analyse des
  faiblesses faite sur les corpus entiers.
- Seulement des identifiants directs : la ré-identification par le contexte (fonction, lieu, événement rare) n'est
  pas mesurée.
- Route texte seulement : la conversion des PDF, Word, Excel n'est pas mesurée (aucun gold bureautique).
- Mise en page de BODACC et BOAMP reconstruite ; entités HTML non décodées dans BOAMP.
- Les corpus réels contiennent des données publiques de personnes réelles : ils ne quittent jamais la machine de
  mesure que vers la mémoire vive du serveur, ne sont ni versionnés ni republiés, et sont effacés après usage.
- Le serveur sert aussi les visiteurs pendant la campagne : le débit en dépend, pas les scores.

## 13. Fichiers

| Fichier | Rôle |
|---|---|
| `tools/protocol/spec.py` | définitions pré-enregistrées (familles, graines, tailles, identifiants directs, garde-fous, mesures antérieures des moitiés `test`, campagnes antérieures, écarts à déclarer) |
| `tools/protocol/align.py` | zones masquées retrouvées depuis la seule sortie du service |
| `tools/protocol/outcomes.py`, `stats.py` | notation par document, agrégats, indice, bootstrap |
| `tools/protocol/campaign.py`, `transport.py`, `plan.py` | campagne, empreinte et contrôles du moteur, socket et jeton local, plan, reprise |
| `tools/protocol/report.py`, `merge_quality.py` | résultats JSON et Markdown, report vers le site |
| `tools/protocol/bundle.py`, `provenance.py`, `server/run-protocol.sh` | paquet autonome, empreintes de l'outil et enregistrement, lancement sur le serveur |
| `tools/protocol/crosscheck.py`, `dryrun.py` | contrôle croisé et son résumé publié, décompte à blanc |
| `tests/protocol/` | tests (alignement, bootstrap, reprise, moteur changé ou redémarré, jeton local, aucun texte écrit, report, refus au départ, paquet altéré, écarts déclarés, campagnes répétées, contrôle croisé) |

## 14. English version

**Version 1.0, written on 25 October 2026, before any campaign; registered by publishing, before the launch, the
digests of this text, of `spec.py` and of the tool bundle (section 15)**; every result copies the digests of what
produced it. Executable definitions: [`tools/protocol/spec.py`](../tools/protocol/spec.py), the single source of truth
of this document; tool: [`tools/protocol/`](../tools/protocol/); tests: [`tests/protocol/`](../tests/protocol/).
Changing a definition means a new dated version; the old one stays in the repository history and every published
result names its version. Text completed on 26 October 2026, before the registration and before any campaign:
earlier measurements of the `test` halves (item 3), repeat campaigns, disclosed departures, refusals at start (item
9); no definition of the index changed.

**1. What is measured.** One question: in what share of documents does the service leave at least one direct
identifier readable? GDPR Guardian is a first barrier, not a "zero leak" promise. The **confidence index** is the
share of documents without any leak, computed per family, then averaged with **equal weight** over the seven
French-scope families, with a 95% interval. The **direct-mention recall** is the share of direct-identifier mentions
fully masked, same families, same equal weight. Every other figure (item 6) is published next to it, never instead.

**2. Families and corpora.** French scope, the seven families of the index:

| # | Family | Source | Documents (all / test half, with a direct mention) | Gold | Measured gold error | Licence |
|---|---|---|---|---|---|---|
| 1 | Synthetic FR | `tools/eval/generate.py` (Faker 40.43.0 `fr_FR`, lexicons), 9 document kinds, 30 templates, decoys that must stay; seeds 2026102501 to 2026102510, 45,000 documents each | 450,000 (all count) | exact by construction | 0 | MIT (repository) |
| 2 | Red team FR | the 51 operators of `tools/eval/mutate.py` (11 families: Unicode spaces, invisibles, substitute digits, look-alikes, dashes, separators, layout, OCR, case, accents, obfuscated e-mails) on 12,000 base documents (seeds 2026102521 to 2026102530, 1,200 each) | 548,907 mutated documents (exact dry-run count) | exact by construction | 0 | MIT |
| 3 | BODACC | commercial announcements naming a natural person, September 2026 | 2,693 / 1,335 (1,335) | exact by construction | 0/274 mentions (95% upper bound 1.4%); independent recheck 0/83 | Licence Ouverte (Etalab) |
| 4 | BOAMP | 2022-2023 procurement notices, `IDENTITE` schema | 3,000 / 1,477 (1,408) | exact for e-mail, phone, address; contact names by a rule | 6/287 mentions = 2.1% [1.0–4.5]; independent recheck 3/96 = 3.1% [1.1–8.8] | Licence Ouverte (Etalab) |
| 5 | ParlaMint-FR | Assemblée nationale debates, ParlaMint 5.0 | 300 / 144 (143) | partial: speakers and listed persons | not measured; exact where it annotates, incomplete elsewhere | CC BY 4.0 |
| 6 | Old French press | Europeana Newspapers FR (515 / 245, 209) and HIPE-2022 NewsEye FR (140 / 72, 63) pooled as **one** family | 655 / 317 (272) | manual (corpus authors) | not measured by us; HIPE includes titles ("abbé") in names | CC0; CC BY 4.0 |
| 7 | MAPA FR | EU legal texts in French (EUR-Lex) | 12 / 8 (6) | manual, single annotator | not measured | CC BY 4.0 |

Pinned revisions, sources and gold construction: [`CORPUS_REELS.md`](CORPUS_REELS.md) (sections 3 and 4; English
version: section 11) and `tools/corpus/real_registry.py`. About 6% of the synthetic documents come from two English templates (a ticket, an
e-mail) of a French context; they stay in the family, as in the development evaluation. The 12,000 red-team base
documents also go through the service (to measure survival) but do not count in the index. **Out of scope,
published apart and prominently**: MAPA DE, ES, IT, NL, PT (12, 9, 12, 12, 12 documents; sent with DE, ES, IT, NL,
PT), MEDDOCAN (es, 1,000, surrogate identifiers; ES), German LER (de, 334; DE), TAB (en, 127; FR, no English pack);
on 25 October 2026 the DE, ES, IT, NL and PT packs masked **no** name at all. **Negative control, precision only**:
Judilibre, 300 decisions already pseudonymised by the courts, no gold; published: masked spans per 10,000
characters and share of decisions with a masked span; the false-positive share needs a manual review (last one on
25 October 2026: 31.7% [24.0–40.4] of 120 reviewed spans) that the campaign does not redo. **No office documents**:
no gold-annotated office set exists in the repository, so version 1.0 measures the text route
(`POST /v1/anonymize/text`), not file conversion.

**3. What the rules were designed on.** Real corpora: fixed split written on 25 October 2026 before any rule change,
SHA-256 of `gdprguardian-rules2-2026-10-25|<document id>`, first 32 bits even → `dev`, odd → `test`
(`tools/corpus/real_common.split_of`). Rules are adjusted on the `dev` halves from 25 October 2026 until the **engine
is frozen** before the campaign (the frozen engine is identified in the results by the service image and the digest
of its outputs, item 9); **the index counts the `test` halves**, never used to design a rule. Both halves still go
through the service: the index on all documents and on the `dev` half is published next to it, and the `dev` − `test`
gap measures overfitting. **Measurements already taken on the `test` halves** (all of them, before the campaign; no
rule may be tuned on these figures; the list is copied into every result from `spec.TEST_HALVES_MEASURED_BEFORE`),
all on 25 October 2026, UTC:

| When (UTC) | Who, what | Engine | Result on the `test` half |
|---|---|---|---|
| during the day | whole-corpus analysis (`CORPUS_REELS.md`, sections 1 to 7), before the split | 1.0.0 of that day | per-corpus recalls and leaks, no index |
| 20:21 | engine tuning: in-process evaluation of the `dev` and `test` halves before any rule change (`CORPUS_REELS.md`, section 12, "before" column) | 1.0.0 | documents with a strict leak (`tools/corpus` definition): BODACC 93.0%, BOAMP 52.8%, ParlaMint-FR 27.3%, Europeana 78.9%, HIPE 98.4%, MAPA FR 83.3%; no index |
| 21:04 and 21:18 | tool trials, scaled plan, full real corpora | sources of that moment | index 45.3% [42.0–50.3] and 45.2% [41.7–50.2]; no-leak shares BODACC 8.0%, BOAMP 47.2%, ParlaMint-FR 72.7%, old press 16.5%, MAPA FR 16.7% (synthetic 91.4%, red team 64.5%) |
| 21:36 to 22:20 | engine tuning: in-process evaluation of the `test` halves and whole corpora at each of the four "rules2" iterations, and of 1.0.0 on whole corpora (21:53); the last one published at 22:22 (`benchmarks/results/real-rules2-comparison-2026-10-25.{md,json}`, `CORPUS_REELS.md` section 12) | rules2 | documents with a strict leak (`tools/corpus`): BODACC 10.1%, BOAMP 39.4%, ParlaMint-FR 7.0%, Europeana 78.9%, HIPE 98.4%, MAPA FR 83.3%; no index |
| 21:42 | independent audit of the tool, scaled plan, full real corpora | sources of that moment | index 61.2% [58.1–66.4]; BODACC 89.4%, BOAMP 55.5%, ParlaMint-FR 93.0%, old press 16.5%, MAPA FR 16.7% (synthetic 91.8%, red team 65.5%) |
| 22:59 | independent review of the engine tuning: in-process evaluation of the `test` halves and whole corpora, engines 1.0.0 and rules2 (not published) | 1.0.0 and rules2 | same figures as published at 22:22 |

The comparison file of 25 October says the `test` halves were "not looked at": their errors were not read, but their
scores were measured at every iteration and published, so they are listed here. After these measurements every trial
must use the **`dev` half only** (`pack-real --split dev` for the tool, `evaluate_real.py --split dev` for the engine
tuning), which a standard campaign refuses; any other pre-campaign measurement of a `test` half is added to this table
and to `spec.TEST_HALVES_MEASURED_BEFORE` before the registration (section 15). **Repeat campaigns**: after the first
published campaign, the `test` halves are no longer blind (their per-family scores are known to whoever edits the
rules). A later campaign on the same halves says so: it lists the earlier campaigns in `spec.EARLIER_CAMPAIGNS` (a new
dated protocol version), which every result copies, and the merge into the site refuses a repeat campaign that omits
the published one. For a later engine version, the headline index must move to fresh data built with the same tools
over a period never measured (for example BODACC and BOAMP notices published after the engine freeze); the "unseen"
BODACC August 2026 and BOAMP 2021 sets (`CORPUS_REELS.md`, section 12) were already measured on 25 October and are no
longer blind either. Synthetic: fresh seeds; the development seed 20261024 (the 540-document evaluation used to tune
the engine) is **refused by the code**. Stated limit: the weakness analysis of 25 October (`CORPUS_REELS.md`, section
7) covered whole corpora and the measurements above saw the `test` halves, so these are not blind to the *kinds* of
errors (entrepreneurs' RCS numbers, particle names, BOAMP addresses…); between the two trials BODACC went from 8.0% to
89.4% after a rule change, and the `test` scores were visible at every rules2 iteration. They are blind to the
values: no name or number of a real corpus may enter the engine, whose code is public.

**4. What a direct identifier is.** Synthetic and red team: the gold labels of type `DIRECT` (`tools/eval/schema.py`):
PERSON, EMAIL, PHONE, ADDRESS, NIR, IBAN, RIB, RIB_SPLIT, CARD, SIRET and SIREN (sole traders only), VAT, TAX_ID,
PASSPORT, ID_CARD, PLATE, RPPS, CAF, FRANCE_TRAVAIL, IP; quasi-identifiers (BIRTH_DATE, LOCATION, ORG, ID for customer,
patient or staff numbers) and decoys do not count. Real corpora: the personal families of `tools/corpus` except the
birth date: PERSON, ADDRESS, EMAIL, PHONE, NATIONAL_ID, TAX_ID, IBAN, BANK_ACCOUNT, CARD, ID, URL, IP. Present: BODACC
PERSON, ADDRESS, ID (RCS/RM number, i.e. an individual entrepreneur's SIREN); BOAMP PERSON, ADDRESS, EMAIL, PHONE
(whoever owns them, often a public body: the engine cannot know); ParlaMint PERSON; old press PERSON; MAPA FR PERSON,
ADDRESS. Kept by policy, outside the computation: ORG, ORG_ID, LOCATION, DATE, OTHER. A mention counts only if it
holds at least one alphanumeric character.

**5. Leak, index, interval.** *Readable*: an alphanumeric character of the input that is still present, at its place,
in the service's output. The service returns no offsets: the tool aligns the output with the input (`[LABEL_N]`
placeholders, invisible characters the output strips). When a text segment between two placeholders fits at several
places, every character that **may** be visible counts as visible (conservative bound). Checked in process on 48,955
distinct documents (the development evaluation and its 6,192 mutations, 20,000 fresh synthetic, 13,745 mutated, the
8,478 real documents): rebuilt zones equal to the engine's on every synthetic document, the conservative bound never
missed a truly visible character, and only 3 real documents (BODACC 1, BOAMP 2; 10 characters in all) where it counts
characters that were in fact masked as visible. *Leak*: a document leaks as soon as **one** alphanumeric character of **one** gold
direct-identifier mention stays readable (the last digit of a phone number is enough). *Failures*: a document the
service refuses or fails on (any HTTP error after retries), or whose output cannot be aligned, counts as a **leak**
with all its direct mentions unmasked. *Documents without a direct mention*: left out of the index (they would
inflate it), counted and published. *Formulas*: for each family *f*, *P_f* = documents without leak / documents with at
least one direct mention; **index = (1/7) · Σ_f P_f** over the seven families whatever their size (a million synthetic
documents weigh as much as the 6 scored MAPA FR documents of the test half); **mention recall = (1/7) · Σ_f (fully
masked direct mentions / direct mentions)**; no index without all seven families. *95% interval*: stratified
bootstrap over **documents** (within each family, as many documents as it holds are drawn with replacement), 2,000
resamples, seed 20261025, 2.5 and 97.5 percentiles. The draw uses the histogram of per-document outcomes (direct
mentions, masked mentions): the count drawn in each cell follows exactly a multinomial law, drawn by successive
binomials, the same law as drawing documents one by one without a million-entry array (`tools/protocol/stats.py`,
equivalence test in `tests/protocol/test_stats.py`). Same method for the mention-recall interval. *What the interval
does not cover*: it measures document sampling only, not gold errors (item 2), not the choice of the seven families,
not the dependence between mutated documents (the ~46 variants of one base document are resampled as if
independent, which makes the red-team family's interval too narrow). One MAPA FR document (6 scored) moves the index
by 1/6 × 1/7 ≈ 2.38 points: MAPA FR alone makes most of the interval's width (about 95% of its variance in the
trials).

**6. Other published figures.** Per family: no-leak share (Wilson interval), mention recall, recall per identifier
type, service errors, ambiguous alignments. Synthetic families (`tools/eval` definitions): character recall (direct,
structured, all), precision (masked characters falling on gold personal data), over-masking of neutral text, decoys
wrongly masked, `tools/eval` leak rates (strict, structured, literal), entity recall. Real corpora (`tools/corpus`
definitions, test half, dev half and all documents): strict and 80% mention recall, character recall, precision with
a bootstrap interval (not measurable on ParlaMint), over-masking, leaking documents (strict and literal), kept
families touched. Red team per operator: no-leak share, mention recall, **survival** (mentions masked without the
mutation that stay masked with it). Per seed: no-leak share (stability). Out of scope, in a section of the results of
its own, never mixed with the French scope, and Judilibre control: item 2. History: the `test`-half measurements taken
before the campaign and the earlier campaigns (item 3). Disclosed departures: every allowed departure from the
procedure (swap active, service redeployed after the campaign ended), written by `run-protocol.sh` into the checkpoint
and the results and recalled by the merge into the site. Campaign: documents, throughput, time yielded to visitors, retries, errors, engine fingerprint (service image,
version, packs, outputs on the probe) and number of engine checks, whether the local token was accepted, plan
fingerprint, SHA-256 fingerprints of the synthetic, mutated and real documents sent. Registration: the tool's digests
(`tools/` files, `spec.py`, this text, bundle, Faker) and the comparison of what was sent (documents, digests) with the
count registered in `spec.py` (section 15). Files: `benchmarks/results/protocol-<date>.json` and `.md`; the site
receives ten keys (item 10).

**7. Guards: the index alone could lie.** An engine that masked everything would score 100%. The index is published
only if, on the same campaign, neutral-text over-masking on the synthetic families is ≤ 2% (0.08% on 25 October),
decoys wrongly masked on the synthetic family are ≤ 10% (3.5%), and character precision on BODACC and BOAMP (test
halves) is ≥ 70% each (90.1% and 80.9% on all documents on 25 October). Otherwise the merge script refuses; forcing it
(`--force-guards`) must be disclosed publicly. Precision and over-masking are always published next to the index.

**8. What could make the index look better than reality, and what the protocol does.** Tuning rules on the measured
documents: index on the `test` halves, fresh seeds, development seed refused by the code, `dev` − `test` gap published,
every earlier measurement of the `test` halves listed (item 3) and copied into the results. Repeating the campaign on
`test` halves already seen: earlier campaigns listed in `spec.EARLIER_CAMPAIGNS` and copied into the results, the merge
into the site refused when the published one is missing, fresh data for a later engine. Keeping quiet about a
departure from the procedure: allowed departures (swap, redeploy after the end) written into the results and recalled
by the merge; `--force-guards` must be disclosed.
Easy synthetic data (the same templates the engine was tuned on; values change, layouts do not): synthetic and red
team weigh 2/7 whatever their volume, each family is published. Volume: equal weights. Masking everything: guards;
precision, over-masking and decoys published next to it. Dropping hard documents or failures: an error or an
unalignable output counts as a leak; documents without gold are counted and published. A lenient leak definition:
strict, one visible alphanumeric character is enough. A convenient alignment: conservative bound. Stopping when the
number looks good, keeping the best run: sizes fixed here, the campaign runs to its end, no final report on an
incomplete campaign, a completed campaign is never run again in the same folder, every campaign published and dated
(an abandoned one keeps a partial report, to be disclosed). Changing the engine mid-campaign: one campaign = one
engine; service image, version, packs and outputs on a fixed probe are checked at start, at every checkpoint, after
any failure or restart and at the end; a difference stops everything without writing anything after the last passing
check, and `finish` checks the image again. Editing the definitions afterwards: digests of `spec.py`, of this text and
of the bundle published before the launch and copied into the results, recomputed from the bundle's contents at every
start (a bundle edited after its build is refused); the plan count compared with the registered one, the merge into
the site refused otherwise; resume refused if the tool changes. Service overload counted as leaks
(or the reverse): `429`/`503` beyond 30 minutes for one document pauses the campaign, never a leak, and the merge
refuses a campaign where such an error was counted. A campaign run without the local token (traffic counted as
public): `/health/deep` probe at start, a standard campaign is refused without an accepted token, and so is the
merge.
Picking the country or profile that suits: the product defaults (FR, `standard`, French placeholders). Incomplete gold
(ParlaMint, bare names not annotated): it **favours** the index, since an unannotated name is not counted as a leak;
stated here, and the family weighs one seventh. Gold errors (BOAMP 2.1%): they cut both ways; measured rates
published. Learning the values of public corpora (name lists): `test` halves never used; the engine is public, so any
list taken from a corpus would show.

**9. The campaign on the production server.** *Tool*: `tools/protocol/`, Python's standard library plus Faker (MIT,
pure Python), shipped as a reproducible self-contained bundle (`gg-protocol.pyz`, which also carries this text), run
in a **throwaway container of the running service's exact image** (same Python 3.12): no network, read-only root, user
10001, no capability, 2 GB of memory without swap, no core file (`--ulimit core=0`: the tool's memory holds the real
corpora), one CPU at low weight (`--cpu-shares 256`), service socket mounted read-only; the local token arrives on
standard input from its root 0600 file, never as an argument nor on disk (`tools/protocol/server/run-protocol.sh`). At
start the tool recomputes the bundle's digests from its contents and refuses a bundle edited after its build.
*Refusals at start, before any request*: a standard campaign (registered seeds and sizes) is refused without the
service image, with unit sizes other than the registered ones (the plan fingerprints depend on them), with a trial
flag (`--allow-disk-real`, fixed probe), or with a real-corpus pack reduced to the `dev` half or missing one of the
fifteen corpora (the index would otherwise be missing after hours of work). *Local token checked*: at start the tool queries `/health/deep`, which
exists for the LOCAL principal only; without an accepted token a standard campaign is refused (a trial goes on,
flagged as public traffic). *Requests*: `POST /v1/anonymize/text` on the service's Unix socket, **without**
`X-GG-Client` and **with** the local token `X-GG-Local`: the LOCAL principal, outside per-client budgets, two jobs at
once at most, never the slot reserved for small requests. Each document sends one usage datagram with
`"src":"protocol"`: **the whole campaign counts in the site's public statistics, as protocol** (engine probes
included). Options: `countries` FR (or the out-of-scope corpus' country), `profile` `standard`, `label_language` `fr`.
*One campaign = one engine*: the engine fingerprint is the service container's image (`docker inspect`, passed by
`run-protocol.sh`), version, pack catalogue and the SHA-256 of the service's **outputs** on a fixed probe (200
development-seed documents, never scored). It is checked at start, before every checkpoint (every 60 seconds), after
any connection failure or service restart (`/status` counters going down) and at the end. A suspected restart drops
the units in progress (redone later) and holds new ones until the check; a unit counts only after a `/status`
reading without restart taken after it finished. A difference stops the campaign without writing anything after the
last passing check; resuming requires the same engine; `finish` checks again that the service image is the one of
the start. Cost: 200 requests per minute of campaign (about 1.5% of the requests; one probe takes about 2 seconds
under WSL), served before the worker threads. *Visitors first*: the service's scheduler
serves a waiting visitor before the campaign's next job; on top of that the tool reads `/status` every 2 seconds and
keeps only one request in flight while anyone else holds or waits for a slot; `429` and `503` are honoured
(`Retry-After`, jitter); past 30 minutes of waiting for one document the campaign **pauses** (an overload never counts
as a leak). Measured under WSL with four visitors sending 20 KB texts non-stop: 95% of answers within 27 ms alone,
within 57 ms during the campaign (no refusal); the campaign yielded 24 seconds out of a minute. *Concurrency*: three
threads (two running at the service, one queued). *Resume*: replayable units (1,500 synthetic documents, 30 red-team
bases, 100 real documents); atomic and durable checkpoint (the previous one is copied, `fsync`, fallback to the copy
when the last one is unreadable; aggregates only); `stop` or SIGTERM pauses, `start` resumes; resume refused if the
engine, the tool, the plan or the real corpora changed, so the service must not be redeployed during a campaign. A
scoring error on one document counts as a leak (`exception:<type>`); a tool error outside a document stops the
campaign with its type, never silently. A completed campaign is never run again: `finish` archives its work folder
(`/var/lib/gg-protocol-<date>-<plan>`). On an incomplete campaign `finish` wipes nothing (the real-corpus pack stays
in RAM while its units are not done) and `start` resumes it; it is abandoned with `GG_PROTOCOL_ABANDON=1 bash
run-protocol.sh finish`, which keeps a partial report to be disclosed. *Allowed departures, written down*:
`GG_PROTOCOL_ALLOW_SWAP=1` (swap active anyway) and `GG_PROTOCOL_REDEPLOYED_AFTER=1` (service redeployed after the
campaign ended, before `finish`) only pass by leaving a trace: `run-protocol.sh` writes them (`--disclose`) into the
checkpoint and the results, and the merge into the site recalls them; they are disclosed with the index. *Scores
only*: the tool never writes nor prints
a text, an annotated value or a service output; checkpoints and results hold counters, bits (one per document) and
fingerprints. *Real corpora in RAM only*: the pack is copied to `/dev/shm` (tmpfs), the tool refuses a pack outside
RAM-backed storage, and `run-protocol.sh` refuses to work while a swap is active (a tmpfs page could reach the disk;
`sudo swapoff -a` for the campaign). Real corpora go first (a few minutes); as soon as their units are saved **the tool
wipes the pack**, drops it from memory and records the wipe in the checkpoint at once; `finish` of a completed or
abandoned campaign also empties `/dev/shm/gg-protocol`. BODACC and BOAMP are rebuilt from their source on the campaign
day when possible (DILA deletion requests), and the local pack is deleted after the copy. *Duration*: measured under
WSL (16 cores, local service in public mode, local token, two LOCAL slots, tool in a throwaway container): 215 to 225
synthetic documents per second, 2.4 ms of client CPU per document; the 8,478 real documents in about 4 minutes, 3 of
them for the out-of-scope corpora (the DE, ES, IT, NL, PT engines are not preloaded: about 0.3 s per request). The
full plan (1,019,385 documents) thus takes about 1 h 20 on such a machine. **On the server the duration is not
measured**: before the campaign, a timed trial (`dev`-half pack, plan scaled with `GG_PROTOCOL_ARGS`, item 10) gives
the throughput, hence the full plan's duration; the campaign must end before the 03:30 UTC automatic reboot, otherwise
`GG_PROTOCOL_HOURS` pauses it cleanly (for example after 3 hours) and `start` resumes it later.

**10. Replay.** The commands of section 10 above, from the repository root (Python 3.12+), `DIR` outside the
repository; `IMAGE` is the service container's image (`docker inspect -f '{{.Image}}' <container>`); a service is
started as in `deploy/README.md` (public mode, `GDPRGUARDIAN_LOCAL_TOKEN_SHA256`). A **trial**, never published, uses a
scaled plan (`--synthetic-docs`, `--redteam-bases`…) and a pack of the `dev` half only (`pack-real --split dev`), so the
`test` halves are no longer touched. **On the server, in order** (`docs/PUBLISHING.md` details the copies): freeze and
deploy the engine; redo the cross-check on that engine (item 11); build the bundle, `registration --bundle`, publish
those digests; `bash run-protocol.sh prepare` (refused while a swap is active: `sudo swapoff -a`); **timed trial** with
a `--split dev` pack and `GG_PROTOCOL_ARGS="--synthetic-docs 3000 --redteam-bases 30"`, then `status` (throughput) and
`finish` (results kept apart in `results/trial-<date>/`, never published); then `prepare` again, the full pack in
`/dev/shm/gg-protocol/`, `GG_PROTOCOL_HOURS=3 bash run-protocol.sh start`, `status` until the end, `finish`, and the
merge into the site. Expected plan fingerprints (Faker 40.43.0), also registered in
`spec.REGISTERED_PLAN` and compared by the tool: 450,000 synthetic documents, 12,000 bases, 548,907 mutated documents;
synthetic SHA-256 `0b91be78435e5434ee5a3b136ab8f08dd10a2c3673dad56fc6dca469c87a955b`, red team
`d984ee1bf9dba70bf2ccf32957cab9da9bbf1fdf02adf5b7444956fa0137760b`. BODACC and BOAMP come from a live API: their
fingerprints, published in the results, may change between downloads. Site keys (`site/data/quality.json`):
`confidence_index`, `confidence_ci_low`, `confidence_ci_high`, `mention_recall_pct` (percent, one decimal),
`protocol_docs` (documents sent by the campaign, engine probes excluded), `protocol_families` (7), `real_corpora` and
`real_docs` (annotated real corpora and their documents, without the Judilibre control), `protocol_date` (ISO date of
the campaign), `protocol_engine` (service version and the first 12 characters of its image, for example
`1.0.0+af877bdf62ae`: two engines of the same version stay distinct). Until a complete campaign has run they hold "—"
and the site shows "not measured yet".

**11. Cross-check of the tool (done before the campaign, redone on the frozen engine).** *Method*: the development
synthetic evaluation (540 documents and 6,192 mutated, seed 20261024) goes through a local service in public mode with
a local token (Unix socket); the tool rebuilds the masked zones from the output alone and the `tools/eval` functions
score them. Every number of the summary (8,535 leaves for the mutated set) is compared with the **in-process
evaluation of the same engine** (one frozen copy of the sources, loaded by the service and by the evaluation) and with
the repository's reference file (`tools/protocol/crosscheck.py`, commands `crosscheck` then `crosscheck-summary`). The
tool is validated when, on the same engine, the ten headline indicators are identical, no document fails and every
other difference is a boundary effect: the boundary between two placeholders separated by a space cannot be read from
the output, which only touches the figures per *system* label (confusion, per-label precision and F2, typed rate,
strict entity rate), never what is masked. A difference from the reference file on which the service and the
in-process evaluation agree comes from the engine, changed since the reference (or, for interval bounds, from the
random draws). *Results*: on 25 October 2026 at 20:47 UTC, engine before rules2, the service's ten indicators equalled
those of `eval-2026-10-25-standard.json` bit for bit (direct recall 99.18%, precision 98.82%, strict leak 9.07%…); that
day's "same engine" part loaded a copy taken mid-edit (2 documents failed on both sides) and is superseded
(`benchmarks/results/protocol-crosscheck-2026-10-25.md`, kept for the record). On 26 October 2026 at 00:04 UTC, frozen
copy of the rules2 engine sources (tree digest `a992428d25533cc6`, pure-Python engine because the installed native core
did not run these sources; probe digest `eeb38986e44c`, the one a campaign records for an engine with the same
outputs): **tool validated** for countries `auto` and `FR`; ten identical indicators between the service and the
in-process evaluation (direct recall 99.23%, precision 98.82%, strict leak 8.33%), no failure; 12 of 773 leaves (base)
and 31 of 8,535 (mutated) differ, all by the boundary effect. Against `eval-2026-10-25-standard-fr-rules2.json`
(countries `FR`) the ten indicators are identical; the 10 differing mutated leaves come from the engine, edited since
that reference. Details: `benchmarks/results/protocol-crosscheck-2026-10-26.md`. The engine was still being tuned during
this check: it is **redone on the frozen engine** before the registration, and its probe digest must
equal the campaign's.

**12. Known limits and biases.** Synthetic data: templates known to the engine; the red team covers 51 operators
only. Gold: BOAMP 2.1% measured errors; ParlaMint partial (favourable); titles inside HIPE names (unfavourable); MAPA FR
tiny (6 scored documents in the test half: one document moves the index by 2.38 points). Real weight: the campaign
sends over a million documents, but five sevenths of the index rest on the 3,164 scored documents of the real `test`
halves. The interval covers document sampling only: not gold errors, not the choice of families, not the dependence
between mutated variants of one document (item 5). The `test` halves were measured before the campaign (item 3): by
the engine tuning before the rule changes (20:21 UTC) and at every rules2 iteration (21:36 to 22:20, published at
22:22), by two tool trials, by the tool's audit and by the review of the engine tuning. Their errors were not read, but
their scores were visible during tuning: unintended tuning on these scores cannot be ruled out; the published `dev` −
`test` gap measures it. After the first published campaign the `test` halves are no longer blind: a repeat campaign
says so (item 3), and a later engine needs fresh data. Rules adjusted on the `dev` halves from 25 October
2026 until the engine freeze; weakness analysis done on whole corpora. Direct identifiers only: re-identification
through context
(role, place, rare event) is not measured. Text route only: PDF, Word and Excel conversion is not measured (no office
gold). BODACC and BOAMP layouts rebuilt by us; HTML entities not decoded in BOAMP. The real corpora hold public data of
real people: they leave the measuring machine only for the server's RAM, are never committed nor republished, and are
wiped after use. The server keeps serving visitors during the campaign: throughput depends on it, scores do not.

**13. Files.** See the table of section 13 above.

## 15. Enregistrement / Registration

**FR.** Ce texte ne peut pas contenir sa propre empreinte : l'enregistrement se fait donc **hors du texte**, avant le
lancement. Une fois le moteur gelé et le paquet construit, `python -m tools.protocol registration --bundle
gg-protocol.pyz` donne les empreintes à publier : `spec_sha256` (`tools/protocol/spec.py`), `protocole_md_sha256` (ce
texte), `tools_sha256` (tous les fichiers `tools/` du paquet), `bundle_sha256` (le paquet lui-même), la version de
Faker et le décompte enregistré du plan (`spec.REGISTERED_PLAN`) ; elles sont publiées (dépôt, puis étiquette de
version à son ouverture) **avant** le premier document envoyé. Chaque campagne recopie ces empreintes dans son point
de reprise (une reprise avec un autre outil est refusée) et dans ses résultats (`registration`), avec la comparaison
du décompte réellement envoyé au décompte enregistré : documents par famille, empreintes SHA-256 des documents
synthétiques et mutés, Faker. Le report vers le site refuse une campagne standard dont le décompte diffère. Chacun
peut vérifier que les empreintes d'un résultat sont celles publiées avant son lancement. Elles sont recalculées depuis
le contenu du paquet (jamais lues dans son manifeste) : un paquet modifié après sa construction est refusé. `spec.py`
porte aussi les mesures antérieures des moitiés `test` et les campagnes antérieures (section 3) : toute mesure ou
campagne nouvelle change `spec_sha256` et demande un nouvel enregistrement, avant le lancement.

**EN.** This text cannot hold its own digest, so registration happens **outside the text**, before the launch. Once
the engine is frozen and the bundle built, `python -m tools.protocol registration --bundle gg-protocol.pyz` gives the
digests to publish: `spec_sha256` (`tools/protocol/spec.py`), `protocole_md_sha256` (this text), `tools_sha256` (every
`tools/` file of the bundle), `bundle_sha256` (the bundle itself), the Faker version and the registered plan count
(`spec.REGISTERED_PLAN`); they are published (repository, then a version tag when it opens) **before** the first
document is sent. Every campaign copies these digests into its checkpoint (resuming with another tool is refused) and
into its results (`registration`), with the comparison of the count actually sent against the registered one:
documents per family, SHA-256 digests of the synthetic and mutated documents, Faker. The merge into the site refuses
a standard campaign whose count differs. Anyone can check that a result's digests are the ones published before its
launch. They are recomputed from the bundle's contents (never read from its manifest): a bundle edited after its build
is refused. `spec.py` also carries the earlier measurements of the `test` halves and the earlier campaigns (item 3):
any new measurement or campaign changes `spec_sha256` and calls for a new registration, before the launch.
