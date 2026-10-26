# Corpus réels : évaluation de Gardien RGPD sur des textes authentiques

> **English summary.** GDPR Guardian 1.0.0 (native core, `profile="standard"`) was measured on 22 runs over
> **real** texts on 25 October 2026: two exact-gold corpora built from French open data (BODACC, 2,693
> announcements naming natural persons; BOAMP, 3,000 procurement notices), debates of the Assemblée nationale
> (ParlaMint-FR), historical French press (Europeana, HIPE-2022 NewsEye), EU legal texts in six languages (MAPA),
> Spanish clinical reports with surrogate identifiers (MEDDOCAN), German court decisions (German LER), English
> ECHR judgments (TAB) and, as a negative control, 300 already-pseudonymised French decisions (Judilibre).
> On French text, person names are masked in **98.1%** of BODACC fields [97.8–98.5], **93.2%** of
> politicians' names in debates [91.7–94.7], **71.4%** of names in historical OCR press, **45.6%** in the NewsEye
> press (gold spans include titles such as "abbé") and only **34.8%** in EU legal prose (MAPA FR, initials).
> E-mails reach **99.9%** (7,230 real BOAMP e-mails), phones **89.4%**, street addresses **89.1%** (BODACC)
> but **69.4%** (BOAMP: building or service names before the street, streets without a house number, postal
> boxes "CS", "BP", "Cedex"). The worst leak: only **5.3%** of the 2,667 SIREN/RCS
> numbers of individual entrepreneurs in BODACC are masked. Without the French pack, the DE, ES, IT, NL and PT
> packs mask **no** person name at all (0% on MAPA, German LER and MEDDOCAN); adding the French pack recovers
> 31–40% on MAPA but drops precision to 5.4% on German court text. In the Judilibre control, **31.7%**
> [24.0–40.4] of the masked spans are false positives (company names, capitalised words) and 68.3% are real
> residual personal data (magistrates', lawyers' and clerks' names, birth dates). The gold of BODACC and BOAMP was
> reviewed by hand on 2 × 50 documents each: final error rates 0/274 and 6/287 personal mentions. The English
> version of this page is at the end (section 11). **Update "rules2" (section 12):** rules designed on dev halves
> and checked on test halves and unseen sets raise BODACC to 97.6% (leaking notices 92.6% → 10.5%), BOAMP to 90.2%
> (addresses 70.5% → 83.5%) and ParlaMint-FR to 98.3%. **Fix round "rules3" (section 13):** the regressions an
> independent review found on ordinary forms and lists (absent from these corpora) are fixed; corpus scores are
> unchanged or slightly better.

Ce document décrit les corpus réels, la construction de leur gold, leurs licences, ce que chacun permet de
mesurer, la règle de confidentialité, les résultats et les commandes exactes pour tout reproduire. Il complète
[`EVALUATION.md`](EVALUATION.md), qui porte sur un corpus **synthétique**. Les chiffres viennent de
`benchmarks/results/real-*-2026-10-25.{md,json}` et de `real-summary-2026-10-25.json` (synthèse lisible par
programme). Aucun texte, aucun nom et aucune valeur annotée ne figure dans ces fichiers : uniquement des scores.

## 1. Résumé des résultats (25 octobre 2026)

Moteur : `gdprguardian` 1.0.0, noyau Rust actif, `Anonymizer(countries=…, profile="standard")`, Python 3.12,
Windows 11, un fil, poste partagé. Pays : ceux du corpus (FR pour les textes français, DE, ES, IT, NL, PT pour
MAPA, ES pour MEDDOCAN, DE pour German LER ; FR pour TAB, faute de pack anglais). Intervalles à 95 % par
bootstrap sur les **documents** (1 000 tirages, graine 0).

| Corpus | Langue | Documents | Mentions personnelles | Rappel strict [IC 95 %] | Précision [IC 95 %] | Documents avec fuite (stricte / littérale) |
|---|---|---:|---:|---|---|---|
| BODACC (`bodacc_fr`) | fr | 2 693 | 14 207 | 78,9 % [78,5–79,3] | 90,1 % [89,6–90,5] | 92,6 % / 90,8 % |
| BOAMP (`boamp_fr`) | fr | 3 000 | 24 404 | 84,5 % [83,1–85,8] | 80,9 % [79,1–82,5] | 53,8 % / 11,9 % |
| ParlaMint-FR (`parlamint_fr`) | fr | 300 | 3 006 | 93,2 % [91,7–94,7] | non mesurable | 30,1 % / 3,3 % |
| Europeana FR (`europeana_fr`) | fr | 515 | 4 272 | 71,4 % [68,7–73,8] | 76,6 % [73,9–79,3] | 75,1 % / 69,2 % |
| HIPE-2022 NewsEye FR (`hipe_newseye_fr`) | fr | 140 | 6 664 | 45,6 % [43,6–48,1] | 74,3 % [70,0–78,5] | 96,7 % / 84,4 % |
| MAPA FR (`mapa_fr`) | fr | 12 | 282 | 34,8 % [23,7–44,6] | 42,7 % [32,2–53,4] | 88,9 % / 88,9 % |
| MAPA DE, ES, IT, NL, PT | de, es, it, nl, pt | 12, 9, 12, 12, 12 | 337, 271, 110, 363, 378 | **0,0 %** partout | aucune zone masquée (NL : 1 zone, hors gold) | 100 % / 89 à 100 % |
| MEDDOCAN (`meddocan_es`) | es | 1 000 | 9 822 | 10,9 % [10,6–11,1] | 61,1 % [60,3–61,9] | 100 % / 100 % |
| German LER (`german_ler_de`) | de | 334 | 337 | **0,0 %** | 0 % (une seule zone masquée, hors gold) | 100 % / 67,3 % |
| TAB (`tab_en`) | en | 127 | 958 | 83,3 % [77,3–88,9] | 77,5 % [72,7–81,9] | 37,8 % / 20,5 % |
| Judilibre (`judilibre_fr`), témoin négatif | fr | 300 | — (pas de gold) | — | 31,7 % [24,0–40,4] des zones masquées relues sont des faux positifs | 12,6 [11,3–14,2] zones masquées pour 10 000 caractères |

Rappel strict : une mention compte comme masquée si **aucun** de ses caractères alphanumériques ne reste
visible. Fuite stricte : un document garde au moins un caractère d'une mention personnelle ; fuite littérale :
le texte de la mention (3 caractères alphanumériques ou plus) se retrouve tel quel, comme mot, dans la sortie.

Par famille (rappel strict de mention, IC 95 %) :

| Corpus | PERSON | ADDRESS | EMAIL | PHONE | ID |
|---|---|---|---|---|---|
| BODACC | 98,1 % [97,8–98,5] (8 728) | 89,1 % [88,0–90,3] (2 812) | — | — | **5,3 %** [4,4–6,2] (2 667 SIREN/RCS/RM d'entrepreneurs individuels) |
| BOAMP | 88,5 % [85,4–91,2] (693) | 69,4 % [66,9–71,7] (9 715) | 99,9 % [99,9–100] (7 230) | 89,4 % [87,9–91,0] (6 766) | — |
| ParlaMint-FR | 93,2 % : étiquettes d'orateur 92,4 % (2 011), mentions dans le discours 95,0 % (995) | — | — | — | — |
| MEDDOCAN | 0,0 % (4 012) | 0,1 % (1 709) | 99,3 % (959) | 82,5 % (137) | 0,0 % (3 005) |

Variante « pack FR ajouté » (`--countries XX,FR --tag with-fr`), pour mesurer ce que les heuristiques françaises
font sur une autre langue :

| Corpus | Rappel strict | Précision |
|---|---|---|
| MEDDOCAN (ES,FR) | 49,8 % [49,4–50,3] ; PERSON 95,3 % [94,4–96,0] (en-tête « Nombre : … Apellidos : … ») | 60,1 % [59,3–60,8] |
| German LER (DE,FR) | 22,3 % [17,6–26,7] | **5,4 %** [4,0–7,0] |
| MAPA DE, ES, IT, NL, PT (+FR) | 32,0 %, 31,7 %, 38,2 %, 31,1 %, 40,2 % | 14,1 %, 54,9 %, 23,5 %, 37,9 %, 31,0 % |

Aucune exception du moteur : 8 478 documents distincts, 22 passages (15 principaux, 7 variantes).

## 2. Règle de confidentialité

- Les corpus réels contiennent des données personnelles de personnes réelles, publiées par ailleurs (BODACC,
  BOAMP, débats, décisions de justice). Ils sont téléchargés et construits **localement**, dans un dossier de
  cache **hors du dépôt** (`--cache`, par défaut `$GDPRG_CORPORA_CACHE` ou `~/.cache/gdprguardian-corpora`) ;
  les outils refusent un cache situé dans le dépôt. Ils servent **uniquement à l'évaluation** et ne sont ni
  versionnés, ni republiés, ni envoyés à un service.
- Seuls des **scores agrégés** sortent de la machine : les rapports `real-*.md/json` ne contiennent ni texte,
  ni exemple, ni valeur. Les fichiers de relecture manuelle (`spotcheck/`) restent dans le cache.
- **Avertissement de la DILA** sur les données à caractère personnel (BODACC, BOAMP, fichier
  `AVERTISSEMENT-Donnees_a_caractere_personnel.pdf` sur `echanges.dila.gouv.fr/OPENDATA/`, relu le 25/10/2026) :
  la réutilisation reste soumise à la loi Informatique et libertés (article L322-2 du CRPA) et ne peut avoir pour
  objet ou pour effet de réidentifier des personnes dont les données ont été anonymisées avant diffusion. La page
  data.gouv.fr de chaque jeu ajoute que le réutilisateur **doit prendre en compte les demandes de mise à jour**
  publiées par la DILA dans le forum du jeu : la DILA y demande régulièrement la suppression d'annonces (14 demandes
  sur la première page du forum BODACC, la dernière le 18/09/2026). Nous y ajoutons nos propres règles : ni
  republication, ni croisement. Donc **retélécharger** avant toute nouvelle mesure et effacer le cache ensuite.
- Les décisions Judilibre sont déjà pseudonymisées par les juridictions ; les noms de magistrats, greffiers et
  avocats qui y restent ne sont ni extraits ni publiés.

## 3. Sources, licences et versions

| Corpus | Source | Version figée | Licence | Texte réel |
|---|---|---|---|---|
| BODACC | DILA, API Opendatasoft `annonces-commerciales` | parutions du 1ᵉʳ au 30/09/2026, 500 par famille (196 pour « Ventes et cessions », tout ce que la période contenait), téléchargées le 25/10/2026 | Licence Ouverte / Open Licence (Etalab), voir note | oui ; mise en lignes reconstruite par nous d'après bodacc.fr |
| BOAMP | DILA, API Opendatasoft `boamp` | parutions 2022-01 à 2023-12, 125 par mois, schéma `IDENTITE` | Licence Ouverte / Open Licence (Etalab), voir note | oui ; mise en lignes « Libellé : valeur » par nous |
| ParlaMint-FR | CLARIN.SI, hdl 11356/2004 | ParlaMint 5.0, `ParlaMint-FR.tgz` | CC BY 4.0 | oui |
| Europeana Newspapers FR | GitHub `EuropeanaNewspapers/ner-corpora` | commit `6bf838d2` | CC0 1.0 | oui (OCR XIXᵉ–XXᵉ s.) |
| HIPE-2022 NewsEye FR | GitHub `hipe-eval/HIPE-2022-data` | v2.1, commit `147f5bc3` | CC BY 4.0 (sous-ensemble NewsEye) | oui (OCR) |
| MAPA | HF `joelniklaus/mapa` | `bbb2a015` | CC BY 4.0 | oui (EUR-Lex, tokenisé) |
| MEDDOCAN | Zenodo 10.5281/zenodo.4279323 | `meddocan.zip` | CC BY 4.0 | cas cliniques réels, **identifiants de substitution** |
| German LER | HF `elenanereiss/german-ler` | `405b6923`, split test | CC BY 4.0 | oui (décisions fédérales, tokenisé) |
| TAB | GitHub `NorskRegnesentral/text-anonymization-benchmark` | `558e09e2`, `echr_test.json` | MIT | oui (CEDH) |
| Judilibre | HF `antoinejeannot/jurisprudence` (miroir de l'API Judilibre) | `8019db10`, 100 décisions ≥ 2022 par juridiction | Licence Ouverte 2.0 (etalab-2.0) | oui, déjà pseudonymisé |

Notes de licence, vérifiées sur les pages sources le 25/10/2026. BODACC et BOAMP : data.gouv.fr déclare la
« Licence Ouverte / Open Licence » sous l'identifiant `fr-lo` (version 1.0 de 2011), le portail Opendatasoft de
la DILA affiche « licence etalab-2.0 » pour tout le site ; les deux versions autorisent la réutilisation, y compris
commerciale, avec mention de la source et de la date de mise à jour. HIPE-2022 : le README du dépôt annonce
« CC BY-NC-SA 4.0 » pour l'ensemble, mais son tableau donne « CC BY 4.0 » pour `newseye`, et la publication
d'origine des données NewsEye (Zenodo, 10.5281/zenodo.4573313) est sous CC BY 4.0 : nous retenons CC BY 4.0 pour
ce seul sous-ensemble.

Écartés pour licence non commerciale (scores publiés sur un site) : HIPE-2022 `hipe2020` et `letemps`
(CC BY-NC-SA), WikiNEuRal et MultiNERD (CC BY-NC-SA), E3C (CC BY-NC), XFUND (CC BY-NC-SA), CATIE-AQ (hérite de
jeux NC). Non disponibles : corpus cliniques français dé-identifiés (eHOP, MERLOT), décisions annotées de la
Cour de cassation, jeu d'anonymisation du Tribunal fédéral suisse.

Attributions : DILA (BODACC, BOAMP) ; Erjavec et al., ParlaMint 5.0, CLARIN.SI ; KB / BnF, Europeana Newspapers ;
Ehrmann et al., HIPE-2022, données NewsEye ; de Gibert Bonet et al., MAPA (LREC 2022), miroir J. Niklaus ;
Marimon et al., MEDDOCAN (IberLEF 2019) ; Leitner et al., German LER (DFKI) ; Pilán et al., TAB (Norsk
Regnesentral) ; Cour de cassation, Judilibre, miroir A. Jeannot.

## 4. Construction du gold

**BODACC — gold exact par construction.** Seules les annonces nommant au moins une personne physique
(`typePersonne = pp`) sont gardées (six familles : procédures collectives, créations, immatriculations, ventes et
cessions, modifications, radiations). Chaque annonce est rendue avec les libellés et l'ordre de sa page
bodacc.fr (« Annonce déposée au », « n° RCS », « Nom », « Prénom », « Adresse », « Établissement(s) »,
« Complément Jugement »…), vérifiés sur trois pages réelles ; les mots sont ceux de l'enregistrement, la mise en
lignes est la nôtre. Les positions des valeurs sont connues au rendu : PERSON (nom, chaque prénom, nom d'usage,
pseudonyme), ADDRESS (toute adresse avec voie), ID (numéro RCS/RM d'une personne physique : le SIREN d'un
entrepreneur individuel l'identifie). S'y ajoutent les répétitions exactes du nom dans l'annonce, les noms et
prénoms écrits dans un nom commercial ou une enseigne, et les adresses de la formule fixe « Adresse de
l'ancien/du nouveau propriétaire : ». Familles conservées par politique : ORG (sociétés, greffe), ORG_ID (SIREN
de société), LOCATION (code postal + ville sans voie), DATE, OTHER (nationalité). Les champs de texte libre
(complément de jugement, commentaires, oppositions) nomment des mandataires et des notaires qu'aucun champ ne
décrit : ils sont marqués « ignorés » (hors précision) ; les mentions gold qui s'y trouvent comptent pour le
rappel.

**BOAMP — gold exact par construction, noms par règle.** Avis 2022-2023 au schéma `IDENTITE` (avis nationaux,
MAPA, et avis européens d'avant eForms ; le schéma eForms de 2024 n'est pas converti). L'arbre `donnees` est
rendu dans son ordre en lignes « Libellé : valeur ». Gold : EMAIL, PHONE (TEL, FAX) et ADDRESS (voie + code
postal + ville) de chaque bloc de partie (acheteur, adresses complémentaires, instances de recours,
titulaires), quel que soit le propriétaire, puisque le moteur masque ces valeurs sans connaître leur
titulaire ; PERSON extrait des champs CONTACT et CORRESPONDANT par une règle (civilité retirée, rôle après une
virgule ou un tiret retiré, mots de rôle rejetés, plusieurs personnes et e-mails ou téléphones inclus) ; titulaire
précédé d'une civilité (« Maître … ») en PERSON. Valeurs de plus de 80 caractères (description, critères,
informations complémentaires) : zones ignorées. ORG, ORG_ID (SIRET), LOCATION sont conservées par politique.

**ParlaMint-FR — gold partiel.** 60 séances tirées au hasard (graine 20261025), 5 extraits de ≤ 4 000 caractères
par séance. Les interventions sont rendues comme au compte rendu (« M. Prénom Nom. Texte ») ; le président de
séance devient « M. le président » / « Mme la présidente ». Gold : l'étiquette de l'orateur (exacte, depuis
l'attribut `who`) et, dans le discours, les correspondances exactes « Prénom Nom » ou « civilité + Nom » des 1 000
et quelques personnes de la liste du corpus. Les personnes absentes de la liste et les noms seuls (« notre
collègue Nom ») ne sont pas annotés : la précision n'est **pas** mesurable.

**Europeana, HIPE, MAPA, German LER, TAB — gold manuel** des auteurs, converti : textes recollés depuis les
jetons (espacement d'origine pour HIPE grâce à `NoSpaceAfter`), étiquettes ramenées aux familles du moteur
(PER, juge, avocat → PERSON ; rue → ADDRESS ; ville, pays → LOCATION ; organisations, juridictions → ORG ;
lois, jurisprudence → OTHER). Europeana : documents de 400 jetons. German LER : blocs de 20 phrases. TAB :
mentions DIRECT et QUASI du premier annotateur. Partout, une civilité en tête d'une zone PERSON (« M. »,
« Mme », « Mr », « Dr »…) est retirée de la zone, comme l'exige le contrat des détecteurs.

**MEDDOCAN — gold manuel, identifiants fictifs.** Les 1 000 cas (train, dev, test) ; 29 types ramenés aux familles
(NOMBRE_* → PERSON, CALLE → ADDRESS, CORREO → EMAIL, TELEFONO/FAX → PHONE, ID_* → ID ou NATIONAL_ID,
TERRITORIO/PAIS → LOCATION, FECHAS → DATE, HOSPITAL/INSTITUCION → ORG ; âge, sexe, profession → OTHER). Les
cas cliniques publiés sont réels mais, selon l'article du corpus (Marimon et al. 2019), les auteurs les ont
**enrichis d'informations personnelles fictives** (en-tête « Datos del paciente » : nom, adresse, numéros,
e-mail ; nous ne l'avons pas vérifié au-delà de la lecture des fichiers) : on mesure la détection de formats
espagnols, pas de vraies données.

**Judilibre — pas de gold.** 100 décisions de 2022 ou plus par juridiction (Cour de cassation, cours d'appel,
tribunaux judiciaires), tirées des derniers groupes de lignes des fichiers Parquet, coupées à 60 000 caractères.
Les zones masquées sont relues à la main sur un échantillon.

## 5. Relecture manuelle du gold

Deux échantillons de 50 documents par corpus, tirés au hasard (`spotcheck_real.py`, graines 20261025 et
20261026), lus en entier avec les zones gold en ligne. Le premier a servi à corriger les règles ; le second,
tiré **après** les corrections, donne l'estimation retenue.

| Corpus | Avant corrections (échantillon 1) | Gold final (échantillon 2) |
|---|---|---|
| BODACC | 8/50 documents, 8 erreurs sur ~263 mentions (3,0 % [1,5–5,9]) : 2 bornes (« (EI) » dans la zone), 6 noms écrits dans un nom commercial absents du gold | **0/50 documents, 0/274 mentions** (borne haute à 95 % : 1,4 %) ; 1 adresse de propriétaire manquée dans le texte libre (formule « Adresse ancien propriétaire », règle élargie ensuite) |
| BOAMP | 9/50 documents, 15 erreurs sur ~481 mentions (3,1 % [1,9–5,1]) : contacts avec rôle ou e-mail, avocat titulaire étiqueté ORG, adresses saisies dans le nom ou l'identifiant | **6/50 documents, 6/287 mentions (2,1 % [1,0–4,5])** : 4 manques (nom après « Monsieur le Président », titulaire personne physique sans civilité, 2 adresses saisies dans le champ ville ou collées à « Hôtel de Ville »), 1 fausse adresse (« Tunnel de … (09) »), 1 borne (noms de services dans le champ adresse) ; non corrigé pour garder l'échantillon sans biais |

**Contre-relecture indépendante** (troisième échantillon, graine 7000003, 15 annonces BODACC et 15 avis BOAMP,
lus en entier par un relecteur qui n'a pas écrit les constructeurs) :

- BODACC : 0/15 document, 0/83 mention personnelle en erreur dans la zone notée (borne haute à 95 % : 4,4 %).
  Comme prévu, le texte libre ignoré contient des données personnelles hors gold (un codébiteur, son SIRET et son
  adresse dans un « Complément Jugement ») : elles ne comptent ni en rappel ni en précision.
- BOAMP : 3/15 documents, 3/96 mentions (3,1 % [1,1–8,8]) : une adresse de voie dans un champ hors bloc de partie
  (« Lieu ouverture offres »), donc absente du gold ; un titulaire personne physique écrit « NOM PRÉNOM » sans
  civilité, étiqueté ORG ; une zone d'adresse qui commence par des noms de services. S'y ajoutent deux adresses
  e-mail saisies dans un champ URL (« http://greffe…@… »), non annotées. Mêmes familles d'erreurs que
  l'échantillon 2, taux compatible avec son intervalle.

Lors de la seconde relecture BOAMP, les lignes de codes, montants, critères et intitulés étaient masquées.
ParlaMint : un contrôle de 6 extraits confirme que le gold est exact là où il annote mais incomplet (noms seuls
sans civilité). HIPE NewsEye inclut des titres et fonctions dans les zones de personne (« abbé X », « cocher
X », « metteur en scène X ») : le rappel strict y est sous-estimé.

## 6. Ce que chaque corpus mesure, et ne mesure pas

| Corpus | Mesure | Ne mesure pas |
|---|---|---|
| BODACC | rappel des noms réels, adresses et SIREN d'entrepreneurs individuels ; précision sur les champs rendus | mandataires et notaires du texte libre ; mise en page d'origine du PDF |
| BOAMP | e-mails réels, formats de téléphone réels (« (+33) 1-23-45-67-89 »), adresses avec CS/BP/Cedex, noms des contacts | coordonnées écrites seulement en texte libre ; la plupart des valeurs appartiennent à des organismes publics |
| ParlaMint-FR | noms de responsables politiques dans une prose française moderne | précision ; identifiants de particuliers |
| Europeana, HIPE | noms dans la presse ancienne bruitée (OCR) | identifiants modernes (absents) |
| MAPA | noms, adresses, dates dans des textes juridiques européens de six langues | numéros (non annotés) ; 9 à 12 documents par langue : test de fumée, pas preuve statistique |
| MEDDOCAN | noms, adresses, e-mails, téléphones, numéros en espagnol clinique | de vraies données (identifiants fictifs) |
| German LER | noms de juges, avocats, personnes, rues en prose juridique allemande | identités des parties (déjà pseudonymisées) ; numéros |
| TAB | noms en prose juridique anglaise | pas de pack anglais : pack FR + détecteurs internationaux |
| Judilibre | ce que le moteur masque encore dans un texte déjà pseudonymisé : données résiduelles contre faux positifs | rappel (pas de gold) |

## 7. Résultats détaillés et faiblesses constatées

Détail par corpus : `benchmarks/results/real-<corpus>-2026-10-25.md` (familles, origine du gold, familles
conservées, relecture). Faiblesses, par gravité :

1. **SIREN/RCS des entrepreneurs individuels non masqués (BODACC).** Dans « n° RCS : 123 456 789 RCS Ville »
   suivi de « Nom : … », seuls 5,3 % [4,4–6,2] des 2 667 numéros sont masqués : la politique « identifiant de
   société » ne masque un SIREN que près des mots « entrepreneur individuel ». C'est la cause principale des
   92,6 % d'annonces qui fuient (et des 90,8 % de fuites littérales) : 2 090 des 2 495 annonces qui fuient ne
   fuient que par ce numéro ; sans lui, 15,0 % des annonces fuiraient (405 sur 2 693). Les noms (98,1 %) et
   adresses (89,1 %) sont, eux, bien masqués.
2. **Aucun détecteur de noms ni d'adresses pour DE, ES, IT, NL, PT.** 0 % de rappel sur MAPA (cinq langues),
   German LER et les noms de MEDDOCAN. Ajouter le pack FR n'est pas une solution : 31 à 40 % de rappel sur MAPA,
   95 % sur l'en-tête étiqueté de MEDDOCAN, mais une précision de 5,4 % sur le droit allemand (noms communs
   capitalisés) et de 14 à 55 % sur MAPA.
3. **Adresses sans numéro en tête, avec nom de bâtiment ou boîte postale (BOAMP : 69,4 %).** Sur les 2 974
   adresses BOAMP manquées, 1 470 ne commencent pas par un numéro de voie, dont 1 000 par un nom de bâtiment ou
   de service (« Hôtel de Ville », « Direction … », « Immeuble … ») que le gold inclut dans l'adresse ; 709
   laissent visibles le code postal et la ville (183 avec « Cedex ») ; 279 seulement laissent visible un numéro
   de boîte (« CS 12345 », « BP »). Taux d'échec : 25 % sans boîte ni Cedex, 33 % avec Cedex, 37 à 48 % avec
   une boîte. Voies en minuscules ou sans numéro (« rue x y, … », « Rue x, Plateau y, … ») également manquées ;
   adresses en texte libre de BODACC : 86,0 %.
4. **Noms dans la prose juridique et historique.** MAPA FR 34,8 % (initiales, pseudonymes « E. B. », titres) ;
   HIPE 45,6 % et Europeana 71,4 % (césure « ¬ », mots collés, noms seuls sans civilité, OCR) ; ParlaMint 93,2 %.
5. **Noms à particule ou apostrophe.** Forme « Prénom Le Nom » : seul le prénom est masqué, le nom de famille
   « Le Nom » reste visible (ParlaMint : 127 des 130 étiquettes d'orateur à particule manquées, 25 des 25
   mentions à particule manquées ; ces noms causent 130 des 153 étiquettes d'orateur manquées, un même orateur
   revenant souvent) ; forme « X'y El Nom » manquée en entier.
6. **Sur-masquage dépendant du contexte.** BODACC : 88,2 % des 2 265 zones masquées hors gold sont la référence
   de bulletin « Bodacc B » (un mot suivi d'une capitale isolée pris pour « Nom Initiale ») et 7,7 % des noms
   commerciaux après « Nom commercial : ». BOAMP : 58,7 % des 13 001 zones hors gold sont des noms
   d'organismes après le libellé « Nom complet : » (le mot « Nom » déclenche le détecteur de personnes) et
   21,6 % (2 811) des lignes d'adresse sans voie, conservées par le gold comme LOCATION (dont 1 706 réduites à
   « code postal + ville ») ; 7,9 % sont des lieux d'exécution : la moitié des noms d'organisations BOAMP est
   touchée. Ces chiffres dépendent de la mise en page : la référence « Bodacc B »
   et « Nom commercial : » figurent sur les pages bodacc.fr (vérifié), le libellé « Nom complet : » est notre
   choix pour BOAMP.
7. **Témoin Judilibre.** 4 153 zones masquées dans 300 décisions (12,6 pour 10 000 caractères). Sur 120 relues :
   82 (68,3 % [59,6–76,0]) sont de vraies données résiduelles laissées par la pseudonymisation des juridictions
   (78 noms de magistrats, greffiers et avocats, 3 dates de naissance de parties, 1 nom de résidence) ; 38
   (31,7 % [24,0–40,4]) sont des faux positifs : 27 noms de sociétés, de marques ou de cabinets d'avocats,
   6 mots courants capitalisés (« doit », « Faisant », « Premier »), 2 mentions d'un nom de restaurant, un
   cépage, une date d'embauche prise pour une date de naissance, une référence légale prise pour une adresse.
   Recomptage indépendant des 120 zones : mêmes totaux ; deux noms de cabinets formés de noms d'avocats sont
   comptés en faux positifs alors que les noms de SCP comptent comme données résiduelles (frontière discutable,
   ± 2 zones). Aucun marqueur de pseudonymisation (« [E] », « [Adresse 1] ») n'a été masqué.
8. **Dates.** MEDDOCAN : 61 % des dates (toutes catégories) sont masquées comme dates de naissance ; Judilibre :
   date d'embauche masquée.

Points forts mesurés sur texte réel : e-mails 99,3 à 99,9 % ; noms dans des champs étiquetés 98,1 % ; noms
de responsables politiques 93,2 % ; débit de 2,5 (BODACC) à 8,6 (Judilibre) M caractères/s sur les corpus français (appel
`anonymize` seul, un fil, poste partagé) ; aucune exception sur 8 478 documents. Ces chiffres restent
**en dessous** du corpus synthétique d'`EVALUATION.md` (rappel direct 99,2 %), comme annoncé.

## 8. Reproduire

Depuis la racine du dépôt (Python 3.11+, paquet `gdprguardian` installé, `huggingface_hub` ; `pyarrow` pour
German LER et Judilibre, ou `--pyarrow-path DOSSIER`). `DIR` est un dossier **hors du dépôt**.

```
python tools/corpus/build_bodacc.py --cache DIR --per-family 500 --start 2026-09-01 --end 2026-09-30
python tools/corpus/build_boamp.py  --cache DIR --per-month 125 --start 2022-01 --end 2023-12
python tools/corpus/fetch_real.py   --cache DIR            # ParlaMint, Europeana, HIPE, MAPA x6, MEDDOCAN, German LER, TAB, Judilibre
python tools/corpus/evaluate_real.py --cache DIR --date 2026-10-25
python tools/corpus/evaluate_real.py --cache DIR --corpora meddocan_es --countries ES,FR --tag with-fr
python tools/corpus/evaluate_real.py --cache DIR --corpora german_ler_de --countries DE,FR --tag with-fr
python tools/corpus/evaluate_real.py --cache DIR --corpora mapa_de --countries DE,FR --tag with-fr   # idem es, it, nl, pt
python tools/corpus/spotcheck_real.py --cache DIR --corpus bodacc_fr --n 50 --seed 20261026
python tools/corpus/spotcheck_real.py --cache DIR --corpus boamp_fr --n 50 --seed 20261026 --ignore-preview 80
python tools/corpus/spotcheck_real.py --cache DIR --corpus judilibre_fr --detections --detection-contexts 120
python -m pytest tests/corpus -q
# Section 12 : moitiés dev/test, ensembles inédits, comparaison / dev-test halves, unseen sets, comparison
python tools/corpus/evaluate_real.py --cache DIR --split dev --tag dev-rules2 --summary real-summary-dev-rules2.json --no-overwrite
python tools/corpus/build_bodacc.py --cache DIR_AOUT --per-family 500 --start 2026-08-01 --end 2026-08-31
python tools/corpus/build_boamp.py  --cache DIR_2021 --per-month 125 --start 2021-01 --end 2021-12
python tools/corpus/compare_real.py --results APRES --before-results AVANT --before base --after rules2
```

Les comptes de relecture sont lus dans `DIR/spotcheck/reviews.json` (comptes seulement) et recopiés dans les
rapports. BODACC et BOAMP viennent d'une API vivante : un nouveau téléchargement peut différer légèrement
(annonces retirées par la DILA). Les autres sources sont figées par révision, handle ou DOI.

## 9. Fichiers

| Fichier | Rôle |
|---|---|
| `tools/corpus/real_common.py` | format JSONL, construction de texte avec positions, résolution des zones, BIO, détokenisation, cache hors dépôt |
| `tools/corpus/real_registry.py` | registre : source, licence, révision, gold, pays, ce qui est mesuré, commande |
| `tools/corpus/build_bodacc.py`, `build_boamp.py` | constructeurs à gold exact (Licence Ouverte) |
| `tools/corpus/fetch_real.py` | téléchargement et conversion des autres corpus |
| `tools/corpus/evaluate_real.py` | mesures, intervalles bootstrap, rapports `real-*` et synthèse |
| `tools/corpus/spotcheck_real.py` | échantillons à relire (gold ou zones masquées), écrits dans le cache |
| `tools/corpus/compare_real.py` | comparaison avant / après par corpus et par moitié (scores seuls) |
| `tests/corpus/` | tests sur données inventées (rendu, gold, convertisseurs, mesures) |
| `benchmarks/results/real-*-2026-10-25.{md,json}`, `real-summary-2026-10-25.json` | scores et métadonnées uniquement |
| `benchmarks/results/real-*-rules3-2026-10-26.{md,json}`, `real-rules3-comparison-2026-10-26.*` | passe de corrections (section 13), scores seuls |
| `benchmarks/results/eval-2026-10-26-standard-fr-rules3.*`, `bench-2026-10-26-standard-rules3.*` | corpus synthétique et banc de performance de la section 13 |

## 10. Limites de cette évaluation

Mise en lignes de BODACC et BOAMP reconstruite (les valeurs et le texte libre sont réels) ; gold BOAMP des
contacts par règle (2,1 % d'erreurs mesurées) ; gold ParlaMint partiel ; MAPA minuscule par langue ;
MEDDOCAN à identifiants fictifs ; Judilibre sans rappel. BOAMP : les entités HTML de la source (« &amp;quot; »,
« &amp;amp; ») ne sont pas décodées au rendu (365 avis sur 3 000 en contiennent ; « quot » est le premier mot visible
de 104 adresses manquées), et les adresses ou e-mails saisis hors des blocs de partie (« Lieu ouverture offres »,
champs URL) ne sont pas dans le gold. Entités et « Lieu ouverture offres » : corrigés depuis (section 12.2). Aucun de ces corpus ne contient de NIR, d'IBAN, de
carte ou de plaque réels en quantité : ces identifiants restent mesurés sur le corpus synthétique.

## 11. English version

**Scope.** GDPR Guardian 1.0.0 (native Rust core, `profile="standard"`) on real texts, 25 October 2026, one
thread on a shared Windows 11 machine. Countries match each corpus (FR for French texts; DE, ES, IT, NL, PT for
MAPA; ES for MEDDOCAN; DE for German LER; FR for TAB, as there is no English pack). 95% intervals: bootstrap over
documents (1,000 resamples, seed 0). Strict mention recall: no alphanumeric character of the mention left
visible. Document leak: strict (one character left) and literal (the mention's text, 3+ alphanumeric
characters, still present as a word).

**Headline.** BODACC 78.9% [78.5–79.3] recall, 90.1% precision (PERSON 98.1%, ADDRESS 89.1%, individual
entrepreneurs' SIREN/RCS 5.3%); BOAMP 84.5% [83.1–85.8], precision 80.9% (EMAIL 99.9%, PHONE 89.4%, PERSON
88.5%, ADDRESS 69.4%); ParlaMint-FR 93.2% [91.7–94.7] (precision not measurable); Europeana FR 71.4%; HIPE NewsEye
FR 45.6%; MAPA FR 34.8%; MAPA DE/ES/IT/NL/PT 0.0%; MEDDOCAN 10.9% (e-mails 99.3%, phones 82.5%, names 0%);
German LER 0.0%; TAB 83.3%; Judilibre control: 12.6 masked spans per 10,000 characters, of which 31.7%
[24.0–40.4] are false positives on a 120-span review. With the French pack added: MEDDOCAN 49.8% (names 95.3%),
MAPA 31–40%, German LER 22.3% at 5.4% precision. No engine exception: 8,478 distinct documents, 22 runs.

**Privacy rule.** Real corpora contain personal data of real people that are already public. They are built in
a cache folder outside the repository (the tools refuse a cache inside it), used for evaluation only, never
committed, republished or sent anywhere. Only aggregate scores are published; reports contain no text, no
example and no value. The DILA personal-data warning (BODACC, BOAMP) is respected: no use contrary to data
protection law, no re-identification, no cross-linking; withdrawn announcements are honoured by re-downloading
before any new measurement and deleting the cache afterwards.

**Sources and licences.** BODACC and BOAMP (DILA, Licence Ouverte / Open Licence: version 1.0 "fr-lo" on
data.gouv.fr, etalab-2.0 on the DILA Opendatasoft portal; both allow commercial reuse with attribution);
ParlaMint-FR 5.0 (CC BY 4.0); Europeana Newspapers FR (CC0); HIPE-2022 NewsEye FR (CC BY 4.0 per the dataset
table and the original NewsEye release on Zenodo, although the HIPE-2022 README states CC BY-NC-SA 4.0 for the
repository as a whole); MAPA (CC BY 4.0); MEDDOCAN (CC BY 4.0, surrogate identifiers); German LER (CC BY 4.0);
TAB (MIT); Judilibre mirror (Licence Ouverte 2.0). The DILA warning makes reuse subject to French data protection
law and forbids re-identifying persons whose data were anonymised; data.gouv.fr requires reusers to honour the
deletion requests the DILA posts in each dataset's forum (latest for BODACC: 18 September 2026). Excluded as
non-commercial: HIPE hipe2020 and letemps, WikiNEuRal, MultiNERD, E3C, XFUND, CATIE-AQ. Pinned revisions are in
section 3 and in `tools/corpus/real_registry.py`.

**How the gold was built.** BODACC: natural-person announcements rendered with the labels and field order of
bodacc.fr; gold positions are known while rendering (surname, given names, usage name, pseudonym, street
addresses, RCS/RM number of the person), plus exact name repeats, names inside trade names and owner addresses
in a fixed phrase; free-text fields are left out of precision. BOAMP: 2022-2023 notices in the IDENTITE schema
rendered as "Label: value" lines; e-mail, phone, fax and street address fields of every party block are gold;
contact names are extracted by a rule. ParlaMint: speaker labels from TEI metadata, plus exact in-text matches of
listed persons (partial gold, precision not measurable). Europeana, HIPE, MAPA, German LER, TAB, MEDDOCAN: the
authors' manual gold mapped to the engine's families; leading honorifics removed from person spans. Judilibre:
no gold, manual review of masked spans.

**Gold review.** Two random samples of 50 documents per corpus, read in full. BODACC: 8/50 documents with an
error before fixes, then 0/50 documents and 0/274 personal mentions on a fresh sample (upper 95% bound 1.4%).
BOAMP: 9/50 documents (15 of ~481 mentions) before fixes, then 6/50 documents, 6/287 mentions (2.1% [1.0–4.5])
on a fresh sample, left unfixed to keep the estimate unbiased. An independent third sample (seed 7000003, read by a
reviewer who did not write the builders) found 0/15 BODACC documents and 0/83 mentions in error, and 3/15 BOAMP
documents, 3/96 mentions (3.1% [1.1–8.8]): a street address in a field outside the party blocks ("Lieu ouverture
offres"), a sole-trader awardee written "SURNAME Given-name" and labelled ORG, and service names inside an address
field; plus two e-mail addresses typed in a URL field and left unannotated.

**What each corpus can and cannot measure.** See the table of section 6: BODACC measures real names, addresses
and individual-entrepreneur SIREN numbers, not court officers in free text; BOAMP real e-mails, phone formats and
box addresses, mostly of public bodies; ParlaMint politicians' names in modern prose, not precision; Europeana and
HIPE names in noisy historical OCR; MAPA six languages but only 9 to 12 documents each; MEDDOCAN Spanish formats
with fictitious identifiers; German LER judges', lawyers' and street names, not the parties; TAB English names
without an English pack; Judilibre residual data versus false positives, not recall.

**Weaknesses found.** (1) Individual entrepreneurs' SIREN/RCS numbers: 94.7% of the 2,667 BODACC numbers left
visible, the main reason why 92.6% of notices leak: 2,090 of the 2,495 leaking notices leak only through this
number; without it, 15.0% of notices would leak. (2) No name or address detector in the DE, ES, IT, NL, PT packs
(0% recall); adding the French pack is not a fix (5.4% precision on German law). (3) BOAMP addresses: 69.4%. Of
the 2,974 missed addresses, 1,470 do not start with a house number (1,000 of them start with a building or service
name such as "Hôtel de Ville", which the gold includes), 709 leave the postcode and city visible (183 with
"Cedex"), and only 279 leave just a postal-box number (CS, BP) visible. (4) Names in EU legal prose (34.8%,
initials) and historical OCR (45.6–71.4%). (5) Particle and apostrophe surnames: in "Given-name Le Surname" only
the given name is masked and the surname "Le Surname" stays visible (127 of the 130 missed ParlaMint speaker
labels with a particle; these names account for 130 of the 153 missed speaker labels). (6) Context-driven
over-masking: "Bodacc B" taken for a name (88.2% of BODACC over-masked spans); organisation names after the label
"Nom complet :" (58.7% of BOAMP over-masked spans) and street-less address lines kept as LOCATION by the gold
(21.6%, 1,706 of them a bare postcode + city); these depend on the layout ("Bodacc B" and "Nom commercial :"
appear on bodacc.fr, checked by the builder; "Nom complet :" is our BOAMP label). (7) Judilibre: 31.7% of masked
spans are false positives (company, brand and law-firm names, capitalised common words), 68.3% are real residual
personal data (magistrates', clerks' and lawyers' names, parties' birth dates); an independent recount of the 120
spans gives the same totals. (8) Dates: 61% of MEDDOCAN dates masked as birth dates.

**Reproduce.** The commands of section 8, from the repository root, with `DIR` outside the repository.

## 12. Règles « rules2 » : corrections tirées des corpus réels (25 octobre 2026)

> **English summary.** New detection rules for the weaknesses of section 7, designed on half of each real corpus
> and measured on the other half and on two unseen sets; full English text in 12.9.

### 12.1 Méthode

- **Moitiés fixées avant toute règle.** Chaque corpus réel est coupé en deux par une empreinte de l'identifiant de
  document : premiers 32 bits de SHA-256(`gdprguardian-rules2-2026-10-25|` + identifiant), pairs → *dev*, impairs →
  *test* (`tools/corpus/real_common.split_of`, option `--split` d'`evaluate_real.py`). Seules les erreurs des
  moitiés *dev* ont été lues ; les moitiés *test* ont seulement été mesurées.
- **Deux ensembles inédits**, construits par les mêmes outils sur d'autres périodes et jamais lus : BODACC
  d'août 2026 (2 689 annonces, 500 par famille) et BOAMP 2021 (1 500 avis, 125 par mois). Aucun identifiant commun
  avec les corpus principaux (0 sur 2 693 et 0 sur 3 000).
- **Avant** : le moteur 1.0.0 publié (paquets de `dist/1.0.0`), sur les mêmes fichiers. **Après** : ce dépôt
  (`--tag rules2`). Le corpus BOAMP reconstruit (12.2) sert aux deux mesures.
- Règles générales du français écrit, sans liste de noms tirée des corpus, explicables (REGLES.md § 2), identiques
  en Python et dans le noyau Rust (empreintes de contrat et tests différentiels) ; irréversibilité inchangée.

### 12.2 Corrections des constructeurs (gold)

- BOAMP : entités HTML décodées (`html.unescape` jusqu'à stabilité, trois passes au plus) et caractères de
  contrôle C1 relus en cp1252, dans les valeurs comme dans les en-têtes ; l'adresse du champ « Lieu ouverture
  offres » entre au gold ADDRESS (80 caractères au plus, avec un mot de voie ou de boîte) ; un titulaire personne
  physique écrit « NOM Prénom » sans civilité est étiqueté PERSON (deux ou trois mots, le premier en capitales,
  4 lettres au moins, ni prénom, ni mot courant, ni mot d'organisme ; les suivants prénoms de rang 6 ou plus).
- Les quatre corpus construits (BODACC, BOAMP et les deux inédits) se reconstruisent à l'identique depuis le
  cache (SHA-256 égal sur deux reconstructions).
- Relecture Judilibre : la ventilation des 120 zones relues (section 7, point 7) est recopiée dans le fichier de
  relecture du cache.

### 12.3 Règles ajoutées ou modifiées

Détail et exemples : [`REGLES.md`](REGLES.md) § 2.

1. **Numéro d'entrepreneur individuel** (SIREN, SIRET, RCS, RM) : masqué quand l'état civil d'une personne physique
   (« Prénom », « Nom d'usage », « né le », « date de naissance »…) est à moins de 120 caractères, sans mot de
   personne morale (« société », « SAS », « dénomination », « capital social »…) à moins de 80 caractères avant ou
   40 après. Groupes de contexte `natural_person` et `legal_entity` du pack FR, jamais preuves de pays ; « RM »,
   « répertoire des métiers », « registre du commerce » ajoutés au contexte du SIREN.
2. **« Prénom Le Nom »** : une particule capitalisée (le, la, de, du, van, di…) et le mot courant qui la suit,
   après un prénom, forment le nom, propagé entier (« Le Verger ») ; une particule en tête n'est jamais un prénom.
3. **« Saint Quentin »** sans trait d'union : un seul jeton de lieu, jamais une personne seule.
4. **Mot qui suit un code postal connu** (« 30600 VAUVERT ») : jamais une personne.
5. **« Bodacc B », « Annexe C »** : mot inconnu suivi d'une lettre sans point, pas un « Nom Initiale ».
6. **Étiquettes** : « Nom commercial : », « Nom de la société : », « Nom de domaine : »… ne sont pas des étiquettes
   de personne ; une valeur qui porte une forme de société (« SAS », « S.A.R.L. », pas « EI ») ou qui commence par
   un mot d'organisme (« Ville », « Syndicat », « Direction »…) non suivi d'un prénom n'est pas une personne ; un mot
   seul suivi de mots capitalisés (« TESTIX INDUSTRIES ») non plus.
7. **Adresses** : code postal et ville seuls (en tête de ligne, après une étiquette ou dans une phrase sans
   virgule ni tiret devant eux, aucune voie à moins de 40 caractères) conservés, comme le gold les classe
   (LOCATION) ; masqués avec une voie (même à la
   ligne ou après un tiret), une boîte (BP, CS, TSA, en toutes casses, avant ou après la voie), un complément
   (bâtiment, appartement, ZAC, parc, lotissement, hôtel, lieu-dit…), un lieu-dit (« 2 la Testière », « Adresse :
   La Testière », « Le Bourg » sur la ligne précédente, jamais un groupe qui finit par une particule ; en prose, fenêtre
   de 80 caractères avec un mot de domicile ou une étiquette) ou des segments d'adresse séparés par une virgule ou
   un tiret (« Rue des prés, 38000 Grenoble », « BP 8 Cedex 02, 49000 Angers », « 22-24 … ») ; précédés d'un autre
   segment sur leur ligne, code postal et ville sont masqués seuls. Aussi : « Cedex » et « Cédex » en toutes casses,
   adjectifs avant le type de voie (« Grande Rue »), noms de voie en minuscules puis capitales (« rue du lieutenant
   X »), commune connue après une voie numérotée sans code postal (« 6 rue des Essais, Vouziers »).
8. **Rapport** : sans le pays FR, avertissement bilingue « Noms et adresses : détectés par les lexiques français
   seulement » (`report.warnings`).
9. **Nom de fichier** : jamais écrit dans la sortie d'un document converti (plus de titre « # document.pdf ») ;
   pour un classeur, le rapport reprend les avertissements du moteur.

### 12.4 Résultats : moitiés dev et test, ensembles inédits

Rappel strict, précision (caractères), documents avec fuite stricte et littérale ; 1.0.0 → rules2, en %. Fichiers :
`benchmarks/results/real-rules2-comparison-2026-10-25.{md,json}` (toutes les moitiés),
`real-<corpus>-rules2-2026-10-25.*` (corpus entiers), `real-<corpus>-unseen-*-{base,rules2}-2026-10-25.*`,
`real-{bodacc,boamp}-fr-base-2026-10-25.*` (1.0.0 sur les corpus reconstruits).

| Corpus | Moitié | Documents | Rappel strict | Précision | Fuite stricte | Fuite littérale |
|---|---|---:|---|---|---|---|
| BODACC | dev | 1 358 | 79,0 → 97,5 | 90,4 → 99,3 | 92,3 → 11,0 | 90,6 → 6,8 |
| BODACC | test | 1 335 | 78,9 → 97,8 | 89,8 → 99,1 | 93,0 → 10,1 | 91,0 → 5,6 |
| BODACC | inédit (août 2026) | 2 689 | 79,3 → 97,6 | 90,1 → 99,2 | 91,9 → 10,2 | 89,9 → 6,0 |
| BOAMP | dev | 1 523 | 85,5 → 90,8 | 80,8 → 86,6 | 54,2 → 39,4 | 10,7 → 11,3 |
| BOAMP | test | 1 477 | 84,4 → 89,5 | 81,2 → 87,3 | 52,8 → 39,4 | 12,7 → 13,2 |
| BOAMP | inédit (2021) | 1 500 | 83,8 → 90,1 | 83,3 → 87,9 | 66,1 → 48,3 | 10,9 → 11,2 |
| ParlaMint-FR | dev | 156 | 92,9 → 98,2 | — | 32,7 → 10,3 | 4,5 → 4,5 |
| ParlaMint-FR | test | 144 | 93,7 → 98,5 | — | 27,3 → 7,0 | 2,1 → 1,4 |
| Europeana FR | dev / test | 270 / 245 | 71,9 → 71,9 / 71,0 → 71,0 | 77,1 → 77,0 / 76,1 → 76,3 | inchangée | inchangée |
| HIPE NewsEye FR | dev / test | 68 / 72 | 46,5 → 46,5 / 44,7 → 44,8 | 73,2 → 73,3 / 75,1 → 75,2 | inchangée | inchangée |
| MAPA FR | dev / test | 4 / 8 | 37,8 → 37,8 / 32,5 → 32,5 | 36,8 / 46,8 inchangées | inchangée | inchangée |
| TAB (EN) | dev / test | 72 / 55 | 83,6 → 83,6 / 82,8 → 82,6 | 77,3 → 77,2 / 77,9 → 78,3 | inchangée | inchangée |
| MEDDOCAN, German LER, MAPA DE ES IT NL PT | dev / test | — | inchangés (0 à 11 %) | inchangée | inchangée | inchangée |

Par famille (rappel strict) :

| Corpus | Moitié | PERSON | ADDRESS | ID | EMAIL / PHONE |
|---|---|---|---|---|---|
| BODACC | dev | 98,0 → 98,0 | 89,8 → 95,1 | 5,4 → 98,4 | — |
| BODACC | test | 98,3 → 98,4 | 88,4 → 94,6 | 5,1 → 99,3 | — |
| BODACC | inédit | 98,0 → 98,0 | 90,1 → 95,0 | 5,2 → 99,2 | — |
| BOAMP | dev | 88,6 → 88,6 | 71,2 → 84,9 | — | inchangés (99,9 / 88,9) |
| BOAMP | test | 88,8 → 88,8 | 69,8 → 82,2 | — | inchangés (100,0 / 89,9) |
| BOAMP | inédit | 86,2 → 86,2 | 68,8 → 83,9 | — | inchangés (100,0 / 90,5) |
| ParlaMint-FR | dev / test | 92,9 → 98,2 / 93,7 → 98,5 | — | — | — |

Les gains de la moitié dev se retrouvent sur la moitié test et sur les ensembles inédits, à un ou deux points près
(BOAMP, adresses : +13,7 sur dev, +12,4 sur test, +15,1 sur l'inédit).

**Corpus entiers** (1.0.0 → rules2) : BODACC 78,9 → 97,6 % de rappel, 90,1 → 99,2 % de précision, fuite stricte
92,6 → 10,5 %, littérale 90,8 → 6,2 % (SIREN/RCS d'entrepreneurs individuels 5,3 → 98,8 %, adresses 89,1 →
94,8 %) ; BOAMP reconstruit 85,0 → 90,2 %, 81,0 → 86,9 %, 53,5 → 39,4 %, littérale 11,7 → 12,2 % (adresses 70,5 →
83,5 %) ; ParlaMint-FR 93,2 → 98,3 %, fuite 30,1 → 8,7 % ; Europeana, HIPE, MAPA, TAB, MEDDOCAN, German LER :
rappel à 0,1 point près. Aucune exception du moteur.

**Fuite littérale BOAMP** : +0,5 point (11,7 → 12,2 %, moitiés dev 10,7 → 11,3, test 12,7 → 13,2). Cause, lue sur
dev : le code postal et la ville seuls ne sont plus masqués (politique LOCATION du gold) ; quand la voie d'une
vraie adresse n'est pas reconnue, la mention entière reste alors lisible au lieu d'une moitié. La règle des
lignes d'adresse (12.3, point 7) a ramené cet écart de +4,3 à +0,6 point sur dev ; le reste est une longue traîne
(segments de plus de 80 caractères, guillemets, abréviations rares) et sept erreurs du gold (organismes ou ville
suivie de « Cedex » étiquetés PERSON par la règle des contacts).

**Variante pack FR ajouté** (hors périmètre : noms DE, ES, IT, NL, PT) : MEDDOCAN, MAPA ES, IT, NL inchangés ;
German LER 22,3 → 20,8 %, MAPA DE 32,0 → 30,6 %, MAPA PT 40,2 → 38,1 % : la règle « Bodacc B » écarte les
initiales sans point des textes déjà pseudonymisés (une fonction suivie d'une seule lettre).

### 12.5 Témoin négatif Judilibre

4 153 → 4 124 zones masquées (12,60 → 12,51 pour 10 000 caractères). 38 zones disparaissent, 9 apparaissent :
22 faux positifs en moins (15 noms de lieux après « St » ou « Saint », dont 11 dans le nom d'un barreau
d'outre-mer, un autre nom de commune, deux codes postaux et villes de juridictions, deux sigles suivis d'une
lettre) ; un lieu de naissance, conservé par politique ; 15 zones remplacées par 9 zones aux bornes plus
justes (noms à particule ou à « Saint » entiers, adresses avec boîte ou « Grande Rue » ; une fois le mot
« demeurant » est compris dans l'adresse). Aucune des 120 zones relues n'est touchée :
l'estimation relue reste 31,7 % [24,0–40,4] de faux positifs ; rapportée au total, environ 31,4 %.

### 12.6 Corpus synthétique (`tools/eval`, 540 documents et équipe rouge)

Profil standard, FR, 1.0.0 → rules2. Corpus de base : rappel direct 99,18 → 99,23 %, précision 98,82 → 98,82 %,
documents avec fuite 9,07 → 8,33 %, adresses 97,5 → 98,5 %, noms inchangés (99,3 %). Équipe rouge (mutations
Unicode, 6 192 documents) : rappel direct 87,50 → 87,61 %, précision 98,54 → 98,53 %, fuite 36,1 → 35,3 %,
adresses 86,7 → 88,7 %, fuite littérale 2 068 → 2 071 documents (bruit). Aucune régression hors du bruit sur ces
corpus ; la revue indépendante a pourtant trouvé des régressions sur des formulaires et des listes ordinaires qu'ils
ne contiennent pas, corrigées en section 13.
Fichier : `benchmarks/results/eval-2026-10-25-standard-fr-rules2.{md,json}`.

### 12.7 Performance

Même poste (Windows 11, 16 cœurs logiques, partagé avec d'autres travaux), un fil, 1.0.0 et rules2 l'un après
l'autre. Corpus réels (`anonymize` seul, meilleur de 3 passes, meilleur de 2 tours), en ms par document : BODACC
0,200 → 0,213 (+6,2 %), BOAMP 1,158 → 1,177 (+1,7 %), ParlaMint-FR 0,605 → 0,539, Europeana 0,568 → 0,539, HIPE
1,923 → 1,833, Judilibre 1,434 → 1,491 (+3,9 %). Banc `tools/bench` (profil standard, deux tours alternés) :
médiane par document 0,27 à 0,30 → 0,23 à 0,27 ms ; 1 M caractères mêlés, meilleur échantillon 212 → 187 ms ; texte
sans donnée personnelle de 100 k caractères, mesuré en alternance (3 × 30 passages par moteur) : médiane 6,94 ms
des deux côtés. Démarrage à froid 561 → 606 ms (vocabulaires plus grands), mémoire inchangée (pic RSS 158 → 160 Mo
pour 1 M caractères). Entrées adverses : toutes linéaires (exposant de croissance 1,25 au plus). Aucun
ralentissement au-delà de 10 %. Fichier : `benchmarks/results/bench-2026-10-25-standard-rules2.{md,json}`.

### 12.8 Ce qui reste

- BOAMP, noms (88,7 %, inchangé) : la plupart des manques lus sur dev sont des erreurs du gold par règle (noms
  d'organismes ou de services dans les champs de contact) ; le reste, des noms après « Monsieur le Président ».
- BOAMP, adresses (83,5 %) : segments de plus de 80 caractères, noms de bâtiments ou de services sans mot
  d'adresse, mots collés à une boîte postale, guillemets ; adresses des champs « lieu principal » hors du gold
  (comptées en faux positifs). Fuite littérale : +0,5 point (12.4).
- Presse ancienne (Europeana, HIPE) et initiales européennes (MAPA FR) : inchangées ; aucune règle à la fois
  générale et sûre n'a été trouvée sur les moitiés dev (OCR, césures, noms seuls).
- Noms DE, ES, IT, NL, PT : hors de ce travail ; avec le pack FR ajouté, la règle « Bodacc B » coûte 1,5 à 2 points
  sur les textes allemands et portugais aux initiales sans point.

### 12.9 English version

**Method.** Each real corpus was split before any rule change by a fixed hash of the document id (first 32 bits
of SHA-256(`gdprguardian-rules2-2026-10-25|` + id), even → dev, odd → test; `--split` in `evaluate_real.py`).
Only dev errors were read; test halves were only measured. Two unseen sets were built with the same builders on
other periods and never read: BODACC August 2026 (2,689 notices) and BOAMP 2021 (1,500 notices), with no document
id shared with the main corpora. "Before" is the published 1.0.0 engine (`dist/1.0.0` packages) on the same files.
Rules are general French writing patterns with no name list taken from the corpora, explainable (REGLES.md § 2),
identical in Python and in the Rust core (contract fingerprints and differential tests); irreversibility unchanged.

**Builder fixes.** BOAMP: HTML entities decoded (`html.unescape` until stable, at most three passes) and C1
control characters read as cp1252, in values and headers; the "Lieu ouverture offres" address joins the ADDRESS
gold (at most 80 characters, with a street or box word); a sole-trader awardee written "SURNAME Given-name" without
an honorific is labelled PERSON (two or three words, the first in capitals with 4+ letters and neither a given
name, a common word nor an organisation word, the others given names of rank 6 or more). The four built corpora
rebuild byte-identically from the cache. The Judilibre review breakdown was copied into the cache review file.

**Rules added or changed.** (1) An individual entrepreneur's SIREN, SIRET, RCS or RM number is masked when a
natural person's civil status is within 120 characters and no legal-entity word within 80 before or 40 after
(pack context groups `natural_person`, `legal_entity`, never country evidence). (2) "Given-name Le Surname": a
capitalised particle and the common word after it, following a given name, form the surname, propagated whole; a
leading particle is never a given name. (3) Hyphenless "Saint Quentin" is one place token. (4) The word after a
known postcode is never a person. (5) "Bodacc B": an unknown word plus a dotless capital letter is not "Name
Initial". (6) "Nom commercial :" and similar labels are not person labels; a person-label value carrying a company
form, or starting with an organisation word not followed by a given name, or a single word followed by capitalised
words, is not a person. (7) Addresses: a postcode and town alone (at line start, after a label, or in a sentence
with no comma or dash before them, and no street within 40 characters) are kept, as the gold classifies them
(LOCATION); they are masked with a street
(even on the next line or after a dash), a postal box (BP, CS, TSA, any case, before or after the street), a
complement (building, flat, ZAC, park, estate, hôtel, lieu-dit…), a named place (never ending with a particle; in
prose, an 80-character window with a home word or a label), or comma- or dash-separated address chunks ("Rue des
prés, 38000 Grenoble", "BP 8 Cedex 02, 49000 Angers", "22-24 …"); preceded by any other chunk on their line, the
postcode and town alone are masked. Also: "Cedex"/"Cédex" in any case, adjectives before the street type ("Grande
Rue"), lowercase-then-capitalised street names, a known town after a numbered street without a postcode. (8) Without
country FR, the report carries a bilingual warning that names and addresses are detected by the French lexicons
only. (9) The uploaded file name is never written into a converted document's output (no "# document.pdf" title);
workbook reports carry the engine warnings.

**Results** (strict recall, precision, documents with a strict / literal leak; 1.0.0 → rules2, %). BODACC dev
79.0 → 97.5, 90.4 → 99.3, 92.3 → 11.0 / 90.6 → 6.8; test 78.9 → 97.8, 89.8 → 99.1, 93.0 → 10.1 / 91.0 → 5.6;
unseen August 2026 79.3 → 97.6, 90.1 → 99.2, 91.9 → 10.2 / 89.9 → 6.0 (individual entrepreneurs' numbers
5.2 → 99.2, addresses 90.1 → 95.0). BOAMP dev 85.5 → 90.8, 80.8 → 86.6, 54.2 → 39.4 / 10.7 → 11.3; test
84.4 → 89.5, 81.2 → 87.3, 52.8 → 39.4 / 12.7 → 13.2; unseen 2021 83.8 → 90.1, 83.3 → 87.9, 66.1 → 48.3 /
10.9 → 11.2 (addresses 68.8 → 83.9; names, e-mails, phones unchanged). ParlaMint-FR dev 92.9 → 98.2, test
93.7 → 98.5 (leak 32.7 → 10.3 and 27.3 → 7.0). Europeana, HIPE, MAPA, TAB, MEDDOCAN, German LER: recall within
0.2 point.
Whole corpora: BODACC 78.9 → 97.6 (precision 90.1 → 99.2, leak 92.6 → 10.5); rebuilt BOAMP 85.0 → 90.2 (81.0 →
86.9, leak 53.5 → 39.4, literal 11.7 → 12.2); ParlaMint 93.2 → 98.3. The BOAMP literal leak rises by 0.5 point:
postcode and town alone are no longer masked, so when the street of a real address is missed the whole mention
stays readable instead of half of it; the address-line rule cut this gap from +4.3 to +0.6 point on dev. With the
French pack added to DE and PT text (out of scope), recall drops by 1.5 to 2 points (dotless initials).

**Judilibre control.** 4,153 → 4,124 masked spans (12.60 → 12.51 per 10,000 characters): 22 fewer false positives
(place names after "St"/"Saint", court postcodes and towns, "word + letter"), one birthplace kept by policy, 15
spans replaced by 9 with better bounds. None of the 120 reviewed spans changed: the reviewed estimate stays 31.7%
[24.0–40.4] false positives, about 31.4% over the whole set.

**Synthetic corpus** (540 documents and red team, standard profile). Direct recall 99.18 → 99.23%, precision
98.82 → 98.82%, leaking documents 9.07 → 8.33%, addresses 97.5 → 98.5%; red team: direct recall 87.50 → 87.61%,
precision 98.54 → 98.53%, leak 36.1 → 35.3%, addresses 86.7 → 88.7%. No regression beyond noise on these corpora;
the independent review still found regressions on ordinary forms and lists that they do not contain, fixed in
section 13.

**Performance.** Same shared machine, one thread, 1.0.0 and rules2 run one after the other. Real corpora
(`anonymize` only, best of 3 passes and of 2 rounds), ms per document: BODACC 0.200 → 0.213 (+6.2%), BOAMP 1.158
→ 1.177 (+1.7%), ParlaMint-FR 0.605 → 0.539, Europeana 0.568 → 0.539, HIPE 1.923 → 1.833, Judilibre 1.434 → 1.491
(+3.9%). `tools/bench` (standard profile, two alternating rounds): per-document median 0.27–0.30 → 0.23–0.27 ms;
1 M mixed characters, best sample 212 → 187 ms; 100 k PII-free characters measured alternately (3 × 30 runs per
engine): median 6.94 ms on both sides. Cold start 561 → 606 ms (larger vocabularies), memory unchanged (peak RSS
158 → 160 MB for 1 M characters); adversarial inputs all linear (growth exponent at most 1.25). No slowdown above
10%. File: `benchmarks/results/bench-2026-10-25-standard-rules2.{md,json}`.

**What is left.** BOAMP names (88.7%, mostly rule-based gold errors in contact fields); BOAMP addresses (83.5%:
chunks over 80 characters, building or service names without an address word, glued words, addresses of
"main place" fields outside the gold); historical OCR press and EU initials unchanged; DE, ES, IT, NL, PT names out
of scope.

## 13. Revue indépendante et corrections « rules3 » (26 octobre 2026)

> **English summary.** An independent review of rules2 found regressions that the real corpora cannot show:
> ordinary one-line forms and postcode-led lists where 1.0.0 masked every name and rules2 left surnames visible.
> All findings were fixed (or rejected with a reason), identically in Python and Rust; the corpus scores did not
> move or improved slightly. Full English text in 13.6.

### 13.1 Ce que la revue a trouvé

Deux bloquants : (B1) dans un formulaire d'une ligne, l'étiquette suivante comptait comme un mot courant
capitalisé, et la règle « Nom : TESTIX INDUSTRIES » retirait le nom (« Nom : Dupont Prénom : Jean » : Dupont
visible ; 546 noms visibles sur 2 100 mises en page générées, aucun avec 1.0.0) ; (B2) le mot qui suit tout code
postal connu n'était jamais une personne (« Matricule 75012 Sophie Martin » : 3 200 sur 3 200). Trois majeurs :
(M1) une forme de société n'importe où dans la valeur d'une étiquette (« Signataire : Mercier pour Testivo SAS » :
144 sur 640) ; (M2) l'avertissement « sans le pays FR » n'atteignait pas les clients MCP ; (M3) les noms des pièces
jointes d'un courriel sortaient tels quels (« CV_Jean_Dupont.pdf »). Neuf mineurs : domicile en code postal et
ville seuls, nom absorbé par l'adresse de la ligne suivante, nom inconnu suivi d'une initiale sans point, fenêtres
de l'état civil traversant les lignes, raisons `explain` par détecteur, communes en plusieurs mots coupées,
« AVENANT N° 2 » pris pour une personne et « M. Le Verger » visible, documentation, mémoire de chaque moteur FR+X
(49 Mio).

### 13.2 Corrections

Détail des règles : [`REGLES.md`](REGLES.md) § 2 et § 4. Toutes identiques en Python et dans le noyau Rust
(contrat 5), avec empreintes de contrat et tests.

- **B1** : la règle « raison sociale » ne s'applique plus quand les mots capitalisés qui suivent commencent
  l'étiquette suivante (un à quatre mots puis « : » sur la même ligne).
- **B2** : après un code postal, un prénom connu et un autre nom forment une personne, sauf si le premier mot
  commence une commune de ce code (« 80300 ALBERT CEDEX », « 97400 Saint Denis » restent des communes).
- **M1** : la forme de société n'est cherchée que dans la valeur propre du champ, avant « pour », « de », « chez »,
  une parenthèse, une virgule ou un tiret isolé.
- **M2** : `warnings` fait partie du rapport résumé des outils MCP ; `anonymize_text` ajoute un second bloc de
  texte (le texte anonymisé reste seul dans le premier) et `get_anonymized` imprime l'avertissement avant le cadre
  du document.
- **M3** : pièces jointes listées par numéro et type (« Pièce jointe 1 (application/pdf) »), jamais par nom, pour
  les courriels EML et MSG et aussi pour les PDF.
- **m1** : code postal et ville seuls après un mot de domicile (« domicilié », « demeurant », « réside »,
  « habite ») sur la même ligne et dans la même phrase : masqués. **Rejeté en partie** : « Adresse : » seule ne
  suffit pas, c'est l'étiquette des adresses d'organismes des marchés publics, que le gold classe LOCATION.
- **m2** : une ligne précédente qui nomme une personne (deux mots dont un prénom connu) ou une société (forme
  juridique) n'est pas un lieu-dit ; la personne reste une personne et le code postal et la ville seuls restent en
  clair. Limité à la ligne précédente, comme la revue le proposait (13.3).
- **m3** : une lettre sans point après un mot inconnu n'est une lettre de série que suivie d'un numéro (« Bodacc A
  n° 2026… ») ; « MBAPPA K », « Testarossi P, » redeviennent des noms ; sous un indice, un mot inconnu et une
  initiale suffisent (« Présents : Testarossi P »).
- **m4** : l'état civil est cherché d'abord sur la ligne du numéro (une personne morale y l'emporte), puis dans son
  paragraphe, jamais au-delà d'une ligne vide ; « employeur » rejoint le groupe `legal_entity`.
- **m5** : raisons propres dans `explain` : `sole_trader`, `civil_status_nearby` (numéros d'entreprise),
  `street_and_number`, `street_after_home_word` (adresses sans commune vérifiée). Nouveau champ `Span.reason`.
- **m6** : fin d'une commune en plusieurs mots (particule puis mot capitalisé) masquée avec l'adresse
  (« Gallargues le Monteux », « SAINT DENIS LA PLAINE CEDEX », « Clichy-La-Garenne »).
- **m7** : « N° » n'est jamais une initiale ; « avenant », « devis », « bordereau » exigent un indice ; après une
  civilité, un article capitalisé qui forme un nom connu porte l'indice (« M. Le Verger »), sauf un rôle
  (« M. Le Maire ») ou un titre (« M. Le Comte »).
- **m8** : formulation « aucune régression hors du bruit » précisée (12.6, 12.9).
- **m9** : les motifs des packs sont compilés une fois par processus et partagés par les analyseurs de chaque
  ensemble de packs (clé : drapeaux et source du motif ; jamais une règle d'organisation).

### 13.3 Vérifications

**Mises en page générées de la revue** (noms de famille français courants, aucune personne réelle), noms laissés
visibles, rules2 → rules3, moteurs natif et Python : formulaires d'une ligne 546 → 0 sur 2 100 ; code postal puis
prénom et nom 3 200 → 0 sur 3 200 (témoin 99999 : 0 → 0 sur 320) ; valeur d'étiquette avec une société 144 → 0 sur
640. Les quatre fichiers de sondes de la revue (≈ 150 extraits) donnent le même texte en natif et en Python.

**Parité Rust / Python** : 0 écart, 0 repli, 0 erreur sur 40 000 textes fabriqués autour de chaque règle (FR) et
10 000 (FR, DE, BE), et sur 16 628 textes (1 000 documents synthétiques, tous les corpus réels en cache, les deux
ensembles inédits et les deux ensembles neufs de la revue), en FR puis en FR, DE, BE ; zones comparées avec leur
raison.

**Corpus réels** (rules2 → rules3, en %) : `benchmarks/results/real-rules3-comparison-2026-10-26.{md,json}`,
`real-<corpus>-rules3-2026-10-26.*`, `real-*-unseen-*-rules3-2026-10-26.*`.

| Corpus | Moitié | Rappel strict | Précision | Fuite stricte | Fuite littérale |
|---|---|---|---|---|---|
| BODACC | dev | 97,48 → 97,48 | 99,29 → 99,27 | 10,97 → 10,97 | 6,85 → 6,77 |
| BODACC | test | 97,80 → 97,80 | 99,13 → 99,13 | 10,11 → 10,11 | 5,62 → 5,54 |
| BODACC | inédit (août 2026) | 97,64 → 97,65 | 99,16 → 99,16 | 10,19 → 10,15 | 5,95 → 5,91 |
| BODACC | neuf de la revue (mars 2025) | 97,65 → 97,65 | 99,03 → 99,03 | 10,85 → 10,85 | 5,62 → 5,62 |
| BOAMP | dev | 90,75 → 90,87 | 86,55 → 86,55 | 39,41 → 39,07 | 11,27 → 11,20 |
| BOAMP | test | 89,53 → 89,59 | 87,26 → 87,26 | 39,42 → 39,28 | 13,21 → 13,21 |
| BOAMP | inédit (2021) | 90,06 → 90,15 | 87,87 → 87,87 | 48,33 → 47,93 | 11,20 → 11,20 |
| BOAMP | neuf de la revue (2019) | 90,70 → 90,73 | 84,97 → 84,99 | 46,37 → 46,12 | 14,43 → 14,43 |

Adresses BOAMP : 84,9 → 85,2 (dev), 82,2 → 82,3 (test), 83,9 → 84,1 (2021), 84,2 → 84,3 (2019) : fin des
communes en plusieurs mots. Corpus entiers : BODACC inchangé (97,64 %, 99,20 %, fuite 10,55 %, littérale 6,24 →
6,16 %) ; BOAMP 90,15 → 90,24 %, fuite 39,42 → 39,17 % ; ParlaMint, Europeana, HIPE, MAPA, TAB, MEDDOCAN : à
0,3 point près. Avec le pack FR ajouté (hors périmètre), les initiales sans point reviennent : German LER 20,8 →
22,3 %, MAPA DE 30,6 → 33,5 %, IT 38,2 → 40,9 %, NL 31,1 → 32,0 %, PT 38,1 → 41,8 %.

Méthode : les règles de cette passe viennent de la revue (extraits inventés), pas des corpus. Une seule décision a
regardé une moitié test, en comptes seulement : étendue aussi aux lieux-dits de la même ligne, la vérification
« personne ou société » coûtait 79 caractères d'adresse du gold dans 4 annonces BODACC du test (aucune sur dev) ; elle
a été ramenée à la ligne précédente, la seule visée par la revue. Aucun texte d'une moitié test n'a été lu.

**Judilibre** : 4 124 → 4 125 zones (une zone remplacée par une plus juste, un nom à particule pris en entier ; un
faux positif, une abréviation dans une ligne de frais). Aucune des 120 zones relues n'est touchée : 31,7 %
[24,0–40,4] de faux positifs.

**Corpus synthétique** (540 documents et équipe rouge) : inchangé ; rappel direct 99,23 %, précision 98,82 %, fuite
8,33 % ; équipe rouge 87,61 → 87,60 %, précision 98,53 %, fuite 35,3 %, fuites littérales 2 071 documents.
Fichier : `benchmarks/results/eval-2026-10-26-standard-fr-rules3.{md,json}`.

**Mémoire et démarrage des moteurs FR+X** (WSL, noyau natif) : coût de chacun des neuf moteurs FR+X 53,5 → 1,9 Mio,
construction 136 à 195 → 35 à 43 ms ; moteur FR seul inchangé (181 Mio après la première requête).

**Performance** (même poste partagé, un fil, 1.0.0 et rules3 en alternance). Corpus réels (`anonymize` seul,
meilleur de 3 passes et de 2 tours), en ms par document : BODACC 0,164 → 0,166 (+1,2 %), BOAMP 0,694 → 0,724
(+4,4 %), ParlaMint-FR 0,332 → 0,339 (+2,3 %), Europeana 0,292 → 0,292, HIPE 1,207 → 1,236 (+2,4 %), Judilibre
0,878 → 0,921 (+4,9 %). Banc `tools/bench` (profil standard, deux tours alternés) : médiane par document (pondérée,
meilleur tour) 0,179 → 0,186 ms ; 1 M caractères mêlés, meilleur échantillon 165 → 171 ms, médiane 192 → 186 ms ;
100 k caractères sans donnée personnelle, médiane 6,60 → 6,69 ms. Démarrage à froid (11 processus neufs alternés,
médiane) 545 → 609 ms, dont environ 24 ms pour les deux nouveaux vocabulaires (premier mot des communes de chaque
code postal, prénoms pour les lignes nommées) ; rules2 en était à 606 ms (12.7). Mémoire du banc : pic tracemalloc
inchangé (2,7 Mo pour 1 M caractères), pic RSS 151 → 173 Mo (rules2 : 145 → 160). Entrées adverses : les 30 du banc
et 20 motifs propres aux règles de cette passe (natif et Python, quatre tailles) restent linéaires (exposant de
croissance 1,23 au plus). Aucun ralentissement au-delà de 5 % par document. Fichier :
`benchmarks/results/bench-2026-10-26-standard-rules3.{md,json}`.

### 13.4 Ce qui reste

- Code postal et ville seuls après « Adresse : » ou « Adresse du salarié : » restent en clair (politique § 2) ;
  seul un mot de domicile les fait masquer.
- Un nom écrit sur la même ligne que le code postal (« Claire Dubois 69003 Lyon ») est masqué comme une adresse.
- « M. Le Maire » écrit avec une majuscule est masqué comme un nom (« Le Maire » est un nom connu) ; l'initiale
  « M » après un nom (« Kowalczyk M ») reste visible (civilité « M » sans point).
- Préchargement des neuf moteurs FR+X : désormais peu coûteux (≈ 17 Mio, ≈ 350 ms) ; décision laissée à
  l'exploitation.

### 13.5 Reproduire

```
python tools/corpus/evaluate_real.py --cache DIR --split dev --tag dev-rules3 --summary real-summary-dev-rules3.json
python tools/corpus/compare_real.py --results APRES --before-results AVANT --before rules2 --after rules3 \
    --date 2026-10-26 --before-date 2026-10-25 --name real-rules3-comparison
```

### 13.6 English version

**Findings.** Two blockers: (B1) in a one-line form, the next field label counted as a capitalised common word, so
the "Nom : TESTIX INDUSTRIES" rule dropped the surname ("Nom : Dupont Prénom : Jean"; 546 of 2,100 generated
layouts, none with 1.0.0); (B2) the word after any known postcode was never a person ("Matricule 75012 Sophie
Martin"; 3,200 of 3,200). Three majors: (M1) a company form anywhere in a label value ("Signataire : Mercier pour
Testivo SAS"; 144 of 640); (M2) the "no FR" warning never reached MCP clients; (M3) e-mail attachment names were
output verbatim. Nine minors (home postcode and town, name line absorbed into the next line's address, unknown
surname plus a dotless initial, civil-status windows across lines, per-detector explain reasons, cut multi-word
towns, "AVENANT N° 2" and "M. Le Verger", documentation, 49 MiB per FR+X engine).

**Fixes** (REGLES.md § 2 and § 4; identical in Python and Rust, contract 5). B1: the company-name rule is skipped
when the capitalised words on the right start the next label (one to four words then ":" on the same line). B2: a
known given name and another name after a postcode form a person unless the first word starts one of the
postcode's towns. M1: the company form is only looked for in the value's own phrase (before "pour", "de", "chez",
a bracket, a comma or a lone dash). M2: `warnings` is part of the MCP summary report; `anonymize_text` adds a
second text block and `get_anonymized` prints the warning before the document frame. M3: attachments are listed by
number and type, never by name (EML, MSG and PDF). m1: postcode and town after a home word on the same line and in
the same sentence are masked; "Adresse :" alone is rejected as a cue (organisations' addresses in public
procurement, gold LOCATION). m2: a previous line naming a person (two words with a known given name) or a company is
not a named place. m3: a dotless letter after an unknown word is a series letter only when a number follows;
under a cue, an unknown word and an initial are a name. m4: civil status is read on the number's line first (a
legal entity there wins), then in its paragraph, never past a blank line; "employeur" joins `legal_entity`. m5: own
explain reasons `sole_trader`, `civil_status_nearby`, `street_and_number`, `street_after_home_word` (new field
`Span.reason`). m6: the rest of a multi-word town (particle then capitalised word) is masked with the address. m7:
"N°" is never an initial; "avenant", "devis", "bordereau" need a cue; after an honorific, a capitalised article
forming a known name carries the cue ("M. Le Verger"), not a role or a title. m8: wording fixed. m9: pack patterns
are compiled once per process and shared by every pack set's scanner (never an organisation's rule).

**Checks.** Generated layouts, surnames left visible rules2 → rules3, native and Python: one-line forms 546 → 0 of
2,100; postcode then names 3,200 → 0 of 3,200 (control 0 of 320); label value with a company 144 → 0 of 640.
Parity: 0 mismatches, fallbacks or errors on 40,000 fuzzed texts (FR) and 10,000 (FR, DE, BE) around every rule,
and on 16,628 texts (synthetic documents, every cached real corpus, unseen and fresh sets) for both country sets,
spans compared with their reason. Real corpora, rules2 → rules3: BODACC unchanged on every half (literal leak
6.85 → 6.77 dev, 5.62 → 5.54 test); BOAMP recall 90.75 → 90.87 dev, 89.53 → 89.59 test, 90.06 → 90.15 unseen 2021,
90.70 → 90.73 fresh 2019, strict leak 39.41 → 39.07, 39.42 → 39.28, 48.33 → 47.93, 46.37 → 46.12 (addresses
+0.1 to +0.3 point: multi-word towns); whole corpora BODACC 97.64%, BOAMP 90.15 → 90.24%; the other corpora within
0.3 point; with the French pack added, dotless initials come back (German LER 20.8 → 22.3%, MAPA DE 30.6 → 33.5%,
PT 38.1 → 41.8%). The rules come from the review's invented snippets, not from the corpora; one decision looked at
a test half, by counts only: the person-or-company check, extended to same-line named places, lost 79 gold address
characters in 4 BODACC test notices (none on dev), so it was limited to the previous line, as the review proposed.
Judilibre: 4,124 → 4,125 spans, none of the 120 reviewed spans touched. Synthetic corpus unchanged (recall 99.23%,
precision 98.82%, leak 8.33%; red team 87.60%, 98.53%, 35.3%). Each FR+X engine now costs 1.9 MiB instead of
53.5 MiB and builds in 35–43 ms instead of 136–195 ms.

**Performance** (same shared machine, one thread, 1.0.0 and rules3 alternated). Real corpora (`anonymize` only,
best of 3 passes and of 2 rounds), ms per document: BODACC 0.164 → 0.166 (+1.2%), BOAMP 0.694 → 0.724 (+4.4%),
ParlaMint-FR 0.332 → 0.339 (+2.3%), Europeana 0.292 → 0.292, HIPE 1.207 → 1.236 (+2.4%), Judilibre 0.878 → 0.921
(+4.9%). `tools/bench` (standard profile, two alternating rounds): per-document median (weighted, best round)
0.179 → 0.186 ms; 1 M mixed characters, best sample 165 → 171 ms, median 192 → 186 ms; 100 k PII-free characters,
median 6.60 → 6.69 ms. Cold start (11 alternating fresh processes, median) 545 → 609 ms, about 24 ms of it for the
two new vocabularies (first word of each postcode's towns, given names for named lines); rules2 was at 606 ms
(12.7). Bench memory: tracemalloc peak unchanged (2.7 MB for 1 M characters), peak RSS 151 → 173 MB (rules2:
145 → 160). Adversarial inputs: the bench's 30 and 20 patterns aimed at this round's rules (native and Python, four
sizes) stay linear (growth exponent at most 1.23). No per-document slowdown above 5%. File:
`benchmarks/results/bench-2026-10-26-standard-rules3.{md,json}`.

**What is left.** Postcode and town alone after "Adresse :" stay readable (policy); a name on the postcode's own
line is masked as an address; a capitalised "M. Le Maire" is masked as a name; the dotless initial "M" after a
surname stays visible; preloading the nine FR+X engines is now cheap (about 17 MiB, 350 ms), an operations
decision.

## 14. Gold aligné sur le protocole 1.1 (26 octobre 2026) / gold aligned with protocol 1.1

**FR.** Le protocole 1.1 ([`PROTOCOLE.md`](PROTOCOLE.md), section « Version 1.1 ») écrit le périmètre d'une fuite :
toute adresse postale, tout téléphone, tout courriel et tout autre identifiant direct, quel qu'en soit le titulaire,
et les noms de personnes physiques ; pas les noms de sociétés ; une ville seule, ou un code postal et une ville sans
voie ni boîte postale, est un lieu. Contrôle de chaque gold : synthétique, BODACC et ParlaMint-FR conformes ;
**BOAMP** corrigé dans `build_boamp.py` : (a) boîte postale collée à son numéro ou écrite avec des points
(« BP60120 », « CS44416 », « C.S.80794 », y compris dans le champ d'identification), ou voie écrite dans les champs
code postal et ville (« 97122 Rue … ») : l'adresse de la partie devient `ADDRESS` au lieu de `LOCATION` ; (b) un mot
de rôle collé par un trait d'union (« DGEEP-Direction ») et les mots « groupe », « maintenance » arrêtent un nom de
contact : un service n'est pas une personne. Repérage préalable sur le corpus entier (compteurs, script hors dépôt) :
3 `PERSON` contenant un mot d'organisation sur 733, 2 `ORG` commençant par une civilité, 86 `LOCATION` sur 5 399 avec
un mot de voie ou un numéro hors code postal et CEDEX (la plupart des boîtes postales collées). Reconstruction hors
ligne depuis les avis bruts du cache : la construction 1.0 refaite à l'identique (SHA-256 `e87658ea3af8b67e…`, octet
pour octet), puis la 1.1 (SHA-256 `435373ea39a1814a…`, enregistré dans `PROTOCOL-REGISTRATION-1.1.json`) : 3 000
documents, textes identiques, 42 `ADDRESS` ajoutées, 35 `LOCATION` et 5 `PERSON` retirées, 40 documents touchés (22
`dev`, 18 `test`). Relecture des 82 zones changées : 0 erreur de libellé ; 5 des
42 adresses ajoutées couvrent aussi un nom de service écrit dans le champ adresse (bornes trop larges, plus sévères
pour le moteur ; gardées). Restent non corrigés (comptés comme lieux) : un nom de bâtiment seul avec code postal et
CEDEX (« Villa … », « Carrefour de l'Agriculture »), une voie étrangère (« …strasse »), une boîte postale collée à un
mot (« HocquardCS 81004 »).

**EN.** Protocol 1.1 writes down the scope of a leak (every postal address, phone, e-mail and other direct
identifier, whoever owns it, and natural persons' names; not company names; a town alone, or a postcode and town
without a street or postal box, is a place). Synthetic, BODACC and ParlaMint-FR conform. **BOAMP** fixed in
`build_boamp.py`: a postal box glued to its number or written with dots, or a street written in the postcode/town
fields, makes the party address an `ADDRESS`; a hyphen-joined role word and the words "groupe", "maintenance" stop a
contact name. Offline rebuild from the cached raw notices: the 1.0 build is reproduced byte for byte (SHA-256
`e87658ea3af8b67e…`), then 1.1 (SHA-256 `435373ea39a1814a…`, registered in `PROTOCOL-REGISTRATION-1.1.json`):
3,000 documents, identical texts, 42 `ADDRESS` added, 35 `LOCATION` and 5 `PERSON` removed, 40 documents touched (22
dev, 18 test). All 82 changed spans reviewed: 0 label error; 5 of the 42 new addresses also cover a service name
written in the address field (too wide, harsher on the engine; kept). Not fixed (still places): a building name alone
with postcode and CEDEX, a foreign street ("…strasse"), a postal box glued to a word.
