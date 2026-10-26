# Chiffres du site, mesures du 25 octobre 2026 / website numbers, 2026-10-25 measurements

Source de `site/data/quality.json`. Chaque nombre du site renvoie à un fichier de ce dossier.
Source of `site/data/quality.json`; every number on the website points to a file in this folder.

## Environnement / environment

Gardien RGPD 1.0.0 (paquet `src/` + noyau `gdprguardian_core` 1.0.0, roue maturin release `cp311-abi3-win_amd64`,
sans PGO), Python 3.12.11, Faker 40.43.0, numpy 2.5.4, Windows 11 (10.0.26300), AMD Ryzen 7 5800H (Zen 3, 8 cœurs /
16 fils), portable **partagé** : environ 26 % de charge CPU venant d'autres processus pendant les mesures. Un seul cœur
(appels séquentiels), GC actif. Heures en UTC.

## Commandes et durées / commands and durations

| # | Commande (depuis la racine du dépôt) | Début (UTC) | Durée | Sorties |
|---|---|---|---|---|
| 1 | `python tools/eval/evaluate.py --profiles standard --name eval-2026-10-25-standard` (pays `auto`, défaut de l'outil) | 15:57:51 | 13,6 s | `eval-2026-10-25-standard.{json,md}` |
| 2 | `python benchmarks/results/engine-2026-10-25.py benchmarks/results/engine-2026-10-25.json` | 15:58:41 | 58,7 s | `engine-2026-10-25.json` |
| 3 | `python tools/bench/bench.py --profiles standard --name bench-2026-10-25-standard` | 15:59:54 | 48,1 s | `bench-2026-10-25-standard.{json,md}` |
| 4 | `python tools/corpus/evaluate.py --profile standard --countries FR --out <temp>` (copié ensuite) | 16:00:55 | 15 s | `corpus_fr_standard-2026-10-25.json` |
| 5 | `python tools/eval/evaluate.py --profiles standard --countries FR --name eval-2026-10-25-standard-fr` (contrôle) | 16:01:21 | 11,7 s | `eval-2026-10-25-standard-fr.{json,md}` |
| 6 | `python benchmarks/results/quality-2026-10-25.py site/data/quality.json` | 16:01 | < 1 s | `site/data/quality.json` |

Les scripts 2 et 6 sont copiés ici tels qu'exécutés (seule la ligne `ROOT` passe d'un chemin absolu à un chemin
relatif au fichier ; le script 6 recopié redonne un `quality.json` identique). Aucun plantage du moteur dans aucune
exécution (0 exception sur 540 + 6 192 + 1 000 + 1 800 documents).

## Valeurs publiées / published values

| Clé | Valeur | Origine |
|---|---|---|
| `recall_structured_pct` | 98,8 | exéc. 1, `headline.recall_structured` (IC 95 % 98,3–99,3) : rappel au caractère des identifiants directs structurés (hors noms et adresses) |
| `precision_structured_pct` | 98,1 | exéc. 1, `system_labels` : précision au caractère des masques de libellés structurés (tout sauf PERSON, ADDRESS, LOCATION, ORG ; 39 228 caractères masqués). Précision globale, noms compris : 98,8 (IC 98,6–99,1) |
| `recall_direct_pct` | 99,2 | exéc. 1, `headline.recall_direct` (IC 98,9–99,4) |
| `docs_leak_structured_pct` | 4,6 | exéc. 1, `headline.doc_leak_rate_structured` (IC 3,0–6,5) : 25 documents sur 540 laissent visible au moins un caractère d'un identifiant structuré |
| `overmask_pct` | 0,1 | exéc. 1, `headline.over_masking` = 0,082 % (IC 0,05–0,12) du texte neutre masqué |
| `eval_docs`, `eval_mentions`, `eval_decoys` | 540, 5 556, 2 228 | exéc. 1 : documents de base, mentions annotées DIRECT + QUASI, leurres NO_MASK |
| `redteam_docs`, `redteam_operators` | 6 192, 51 | exéc. 1 : 135 documents de base × 51 opérateurs (seules les variantes réellement mutées sont gardées) |
| `parity_docs` | 1 000 | exéc. 2 : moteur natif et moteur Python seul (`native=False`) donnent le même texte **et** les mêmes zones sur 1 000 / 1 000 documents de `datasets/fr/docs` |
| `ms_per_doc` | 0,56 | exéc. 2 : médiane de 9 passes complètes sur les 1 000 documents (1,92 Ko en moyenne), pays FR, profil standard ; meilleure passe 0,49 ; latence par document p50 0,51, p95 0,77, p99 0,87 ms |
| `mb_per_s` | 3,4 | exéc. 2 : octets UTF-8 / temps, même médiane ; meilleure passe 3,9 |
| `text_10mb_s` | 2,1 | exéc. 2 : texte de 10 000 000 octets (documents du corpus concaténés), médiane de 3 essais : 2,09 s (1,95 au mieux), 151 909 zones masquées |
| `docs_tested` | 17 624 | somme par exécution, chaque document compté une fois par exécution (préchauffages et répétitions de chronométrage exclus) : 6 732 (exéc. 1) + 1 000 (exéc. 2) + 360 (exéc. 3, documents chronométrés un à un) + 2 800 (exéc. 4 : 1 000 + 6 × 300 variantes) + 6 732 (exéc. 5, même corpus que l'exéc. 1 avec les pays FR). Sans le contrôle n° 5 : 10 892 |
| `service_p50_ms`, `service_p99_ms`, `pdf100_s` | 5,2, 8,6, 8,7 | banc du service sur serveur Linux 16 cœurs, mesuré plus tôt (non rejouable sur ce poste) |
| `tests_windows`, `tests_linux`, `tests_offline_image` | 3 751, 3 701, 12 | suites complètes du 25 octobre 2026, version 1.0.0 (non rejouées ici) |
| `image_mb`, `core_mb` | 103, 3,6 | image Docker et noyau Linux, mesurés plus tôt (le `.pyd` Windows fait 3,3 Mo) |

Le contrôle n° 5 (pays FR, défaut du moteur et de l'API) donne **exactement** les mêmes indicateurs que le n° 1
(pays `auto`).

## Autres mesures du jour / other measurements of the day

- Moteur Python seul, même session (exéc. 2) : 5,19 ms par document, 0,37 Mo/s ; le noyau Rust est donc 9,3 fois
  plus rapide. Tous pays (`countries="all"`) : 0,83 ms par document, 2,3 Mo/s.
- `tools/bench` (exéc. 3, documents synthétiques de 380 à 810 caractères) : p50 0,13 à 0,33 ms selon le type ;
  5,3 M car./s sur 1 M car. mixtes, 14,3 M car./s sur du texte sans donnée personnelle, 3,3 M car./s sur des tableaux
  denses ; 30 entrées adverses de 200 k car. sans alerte (exposant de croissance 0,88 à 1,25, débit ≥ 2,0 M car./s) ;
  pic tracemalloc 2,7 Mo pour 1 M car. ; démarrage à froid 531 ms (import 75, construction 455, premier appel 0,6).
- Corpus à valeurs plantées (exéc. 4, 1 000 documents, pays FR) : aucune fuite sur 2 463 adresses, e-mails, NIR et
  téléphones, 1 215 IBAN, 376 cartes, 369 passeports, 450 plaques, 283 SIRET et TVA d'entrepreneurs individuels ;
  4 dates de naissance sur 2 463 ; 49 jetons de nom sur 5 090 (99,0 % masqués) ; aucun des 5 942 leurres modifié ;
  716 SIRET de sociétés sur 717 conservés. Perturbations (300 documents chacune) : espaces insécables, invisibles,
  pleine chasse, homoglyphes d'e-mail sans fuite structurée ; faute de frappe qui fausse la clé : 50 NIR sur 718
  visibles. **Cohérence des balises** : 2 269 personnes sur 2 463 (92,1 %) ont une seule balise ; 194 sont
  éclatées sur plusieurs balises ; 44 partagent la balise d'une autre personne.

## Écarts par rapport à `docs/EVALUATION.md` / changes versus `docs/EVALUATION.md`

- **Débit** : 0,56 ms par document et 3,4 Mo/s, contre 0,45 ms et 4,2 Mo/s publiés. Le moteur Python seul est
  ralenti dans la même proportion (5,2 ms contre 3,9), et le rapport Rust / Python ne bouge pas (9,3 contre 8,7) :
  c'est le poste chargé, pas une régression. La meilleure passe (0,49 ms, 3,9 Mo/s) le confirme. Le texte de 10 Mo
  reste à 2 s environ (2,09 s en médiane).
- **Plantages** : 0 document, contre 10,7 % à l'instantané B.
- **Sur-masquage** : 0,08 %, contre 1,4 % à l'instantané B ; précision globale 98,8 % (98,2 % lors de la revue).
- **Rappel** : PERSON 99,3 % (98,5), BIRTH_DATE 100 % (61,4) ; ADDRESS 97,5 % (98,2), en légère baisse.
- **Équipe rouge**, gains : remplisseur hangul 13,8 → 100 %, sélecteurs de variante et U+034F 0 → 100 %, césure des
  PDF 0 → 98,7 %, gras Markdown 93,9 → 100 %, accents décomposés 8 → 100 %, OCR 6,5 → 24,2 %, minuscules 28 → 57 %.
- **Inchangé, encore faible** : documents avec fuite d'identifiant structuré 4,6 % (RIB en champs séparés : 0 % ;
  téléphones 98,0 %, les manqués étant les mobiles des DOM en forme locale « 0692 12 34 56 »), tabulations 0 %, retours à la ligne 4,5 %, CRLF 3,9 %,
  doubles espaces 7,1 %, barres obliques 5,9 %, exposants 7 %, lettres mathématiques 55 %, lettres espacées 2,2 %,
  e-mails `&#64;`, `%40`, « [dot] », « (point) » 0 % ; identifiants de sociétés masqués à tort 27,3 % (précision
  SIRET 63 %, SIREN 38 %). Les correctifs de la section 8.1 sur ces points ne sont pas encore intégrés.
- **Démarrage à froid** : 531 ms (construction 455 ms), contre 113 à 203 ms (construction 46 à 81 ms, portée à
  288 ms une fois tous les packs chargés) : la construction du moteur natif est plus longue.
