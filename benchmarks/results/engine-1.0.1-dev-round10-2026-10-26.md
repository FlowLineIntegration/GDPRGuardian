# Moteur 1.0.1, passe « formats du quotidien » (développement, 26 octobre 2026) / engine 1.0.1, everyday-formats pass (development)

Mesures sur les données de **développement** uniquement : graine `spec.DEV_SEED` (20261024) pour le synthétique et
l'équipe rouge, moitiés « dev » des corpus réels (`tools.corpus.real_common.split_of`), gold BOAMP 1.1 du cache.
Aucune moitié « test » n'a été lue. Mesures dans le processus (moteur Rust installé), même définition de la fuite
que le protocole 1.1 : un document passe quand aucun caractère alphanumérique d'un identifiant direct du gold ne
reste lisible.

Development data only: seed `spec.DEV_SEED` (20261024) for synthetic and red team, "dev" halves of the real corpora,
BOAMP 1.1 gold from the cache. No "test" half was read. In-process measurements (Rust core installed), same leak
definition as protocol 1.1: a document passes when no alphanumeric character of a gold direct identifier is readable.

## Correctifs de la revue / review fixes (B1, M1, M2, M3)

Python et Rust à l'identique, règles dans `docs/REGLES.md`, tests dans `tests/test_everyday_formats_102.py`.
Python and Rust identically; rules in `docs/REGLES.md`; tests in `tests/test_everyday_formats_102.py`.

1. **B1, courriel sur la ligne suivante** : le morceau de gauche d'un courriel coupé doit commencer par une lettre ;
   « Tél. 01 23 45 67 89⏎j.dupont@exemple.fr » ne colle plus le dernier groupe au courriel (téléphone, carte, date de
   naissance entiers). B1: the left piece of a wrapped e-mail must start with a letter; a number ending the line is
   no longer glued onto the e-mail.
2. **M1, lettres espacées** : seuls les lettres et chiffres comptent, au moins quatre par bloc (trois pour un mot
   capitalisé, « Z o é ») ; « chiffre à chiffre » n'est jamais recollé ; pré-test bon marché avant le balayage.
   Documents dont le texte de détection change : BOAMP 104 → 6, BODACC 6 → 0, ParlaMint 1 → 0 (moitiés dev).
   M1: only letters and digits count, at least four per block (three for a capitalised word); a digit-à-digit range
   is never collapsed; cheap pre-check. Documents whose detection text changes: BOAMP 104 → 6, BODACC 6 → 0,
   ParlaMint 1 → 0.
3. **M2, sociétés** : une civilité ou un titre (M., Mme, Mlle, Monsieur, Madame, Mademoiselle, Me, Maître, Dr) juste
   avant le nom, ou une forme suivie d'un mot capitalisé (« SARL Lumière »), laisse le nom masqué. M2: a civility or
   title before the name, or a form followed by a capitalised word, keeps the name masked.
4. **M3, verbes de lieu** : sortis de `LOCATIVES` ; ils ne servent plus qu'à une commune reprise d'une personne
   trouvée ailleurs (« Mme Lyon … quitter Lyon ») ; « gagner » retiré. « rejoindre Marie », « quitter Jean » restent
   masqués. M3: place verbs taken out of `LOCATIVES`, used only for a town repeated from a person found elsewhere.

| Famille / family | Avant correctifs / before fixes | Après correctifs / after fixes |
|---|---:|---:|
| Synthétique FR (1 000) | 96.3 % (963/1000) | 96.3 % (963/1000) |
| Équipe rouge, 25 opérateurs du quotidien / everyday red team | 86.71 % (6122/7060) | 86.73 % (6123/7060) |
| BODACC (moitié dev) | 91.90 % (1248/1358) | 91.83 % (1247/1358) |
| BOAMP (moitié dev, gold 1.1) | 93.99 % (1377/1465) | 93.99 % (1377/1465) |
| ParlaMint-FR (moitié dev) | 94.23 % (147/156) | 94.23 % (147/156) |

Moyenne à poids égal (estimation de développement) / equal-weight mean (development estimate) : 92.62 %. Garde-fous
inchangés / guards unchanged : leurres / decoys 3.43 %, sur-masquage neutre / neutral over-masking 0.073 % ;
précision / precision BODACC 99.3 %, BOAMP 87.07 %, ParlaMint 95.5 %. `letter_spacing` 85.33 % (inchangé /
unchanged), `crlf` 11.67 %, `line_break` 17.67 %.

BODACC perd un document à cause de M1 (vérifié en défaisant chaque correctif tour à tour, moteur Python) : « Prénom :
<nom composé> <prénom> A O S » (valeurs réelles retirées) ; trois initiales capitales isolées ne sont plus recollées et restent lisibles.
B1, M2 et M3 ne changent aucun document BODACC. BODACC loses one document because of M1 (checked by undoing each
fix in turn): three isolated capital initials are no longer collapsed and stay readable; B1, M2 and M3 change no
BODACC document.

## Familles de l'indice / index families

| Famille / family | Avant / before | Après / after |
|---|---:|---:|
| Synthétique FR (1 000 documents) | 95.8 % (958/1000) | **96.3 %** (963/1000) |
| Équipe rouge FR, 25 opérateurs du quotidien (300 documents de base) / red team FR, 25 everyday operators | 66.77 % (4714/7060) | **86.71 %** (6122/7060) |
| BODACC (moitié dev) | 91.83 % (1247/1358) | **91.90 %** (1248/1358) |
| BOAMP (moitié dev, gold 1.1) | 94.06 % (1378/1465) | 93.99 % (1377/1465) |
| ParlaMint-FR (moitié dev) | 89.74 % (140/156) | **94.23 %** (147/156) |

Moyenne à poids égal des cinq familles (estimation de développement, pas un résultat du protocole) / equal-weight
mean of the five families (development estimate, not a protocol result) : 87.64 % avant / before, 92.63 % après /
after.

Garde-fous / guards : leurres touchés / decoys touched 3.43 % (inchangé / unchanged), sur-masquage du texte neutre /
neutral over-masking 0.073 % (inchangé / unchanged) ; précision au caractère / character precision BODACC 99.3 %
(inchangée / unchanged), BOAMP 87.07 % (86.91 % avant / before), ParlaMint 95.5 % (95.48 %).

BOAMP perd un document (« Nom complet : DR WEIGERT France SAS ») : le gold y code « WEIGERT France » comme une
personne, la nouvelle règle des sociétés le laisse lisible (forme juridique « SAS » juste après, considérant 14).
BOAMP loses one document: its gold labels "WEIGERT France" (in "DR WEIGERT France SAS") as a person; the new company
rule keeps it readable (legal form "SAS" right after it).

## Contrôle Judilibre / Judilibre control

300 décisions, zones masquées / masked zones : 3 807 (11.55 pour 10 000 caractères) au lieu de 4 112 (12.47). Les
305 zones en moins viennent toutes de la règle des sociétés (règle coupée : 4 112, à l'identique) : surtout le premier
nom d'un cabinet d'avocats (« la SCP Foussard et Froger », « SELARL … ») collé à sa forme juridique, désormais lisible
comme toute raison sociale ; les noms suivants du cabinet restent masqués. À trancher par le propriétaire : garder
les sociétés d'exercice libéral (SCP, SELARL…) dans la règle, ou les en sortir.
300 decisions: 3,807 masked zones (11.55 per 10,000 characters) instead of 4,112 (12.47). All 305 fewer zones come
from the company rule (rule off: 4,112, identical): mostly the first name of a law firm ("la SCP Foussard et Froger",
"SELARL …") next to its legal form, now readable like any company name; the firm's later names stay masked. Owner's
call: keep professional partnerships (SCP, SELARL…) under the rule, or take them out.

## Équipe rouge, par opérateur du quotidien / red team, per everyday operator

| Opérateur / operator | Avant / before | Après / after | Documents |
|---|---:|---:|---:|
| `crlf` | 3.00 % | 11.67 % | 300 |
| `line_break` | 3.67 % | 17.67 % | 300 |
| `letter_spacing` | 0.00 % | 85.33 % | 300 |
| `nbsp` | 95.67 % | 99.00 % | 300 |
| `narrow_nbsp` | 95.67 % | 99.00 % | 300 |
| `thin_space` | 95.67 % | 99.00 % | 300 |
| `figure_space` | 95.67 % | 99.00 % | 300 |
| `ideographic_space` | 95.67 % | 99.00 % | 300 |
| `tab` | 88.67 % | 91.67 % | 300 |
| `double_space` | 55.00 % | 94.67 % | 300 |
| `dots` | 42.28 % | 98.66 % | 298 |
| `hyphens` | 52.58 % | 98.63 % | 291 |
| `slashes` | 42.00 % | 91.67 % | 300 |
| `compact` | 94.89 % | 96.35 % | 274 |
| `regroup` | 18.67 % | 95.67 % | 300 |
| `en_dash_groups` | 54.00 % | 98.00 % | 300 |
| `nb_hyphen` | 96.05 % | 98.03 % | 152 |
| `pdf_hyphenation` | 92.33 % | 95.67 % | 300 |
| `soft_hyphen` | 95.67 % | 99.00 % | 300 |
| `upper` | 93.33 % | 96.67 % | 300 |
| `lower` | 27.33 % | 29.33 % | 300 |
| `surname_first` | 90.31 % | 98.24 % | 227 |
| `strip_accents` | 93.78 % | 98.56 % | 209 |
| `nfd` | 93.78 % | 98.56 % | 209 |
| `markdown_bold` | 92.00 % | 95.67 % | 300 |
| **regroupé / pooled** | **66.77 %** (4714/7060) | **86.71 %** (6122/7060) | 7060 |
| moyenne des opérateurs / mean of operators | 68.31 % | 87.39 % | |
| documents de base / base documents | 95.67 % | 99.00 % | 300 |

## Ce qui a changé / what changed

Python et Rust à l'identique (empreintes de contrat enregistrées, `tests/test_native_contracts.py`) ; règles dans
`docs/REGLES.md`. Python and Rust identically (contract fingerprints recorded); rules in `docs/REGLES.md`.

1. **Règle BREAK (couche 0)** : un saut de ligne (LF ou CRLF, sans blanc autour) à l'intérieur d'un courriel
   (« jean.du⏎pont@exemple.fr », domaine incomplet d'un côté et complet une fois recollé) ou d'un IBAN collé (clé
   mod 97 pas déjà juste à gauche, chiffre à droite) est retiré du texte de détection ; deux groupes en majuscules et
   chiffres, chacun avec un chiffre, de 12 caractères au plus (« 47CY⏎74524 »), sont lus séparés par une espace. La
   table de positions ramène la balise sur le texte d'origine : le masque couvre le saut de ligne.
   BREAK rule: a line break inside an e-mail or a pasted IBAN is removed from the detection text; two capital-and-digit
   groups each holding a digit are read as space-separated. The mask covers the break.
2. **Lettres espacées (couche 0)** : « J e a n   D u p o n t », « 0 6   1 2 », « j e a n . d u p o n t @ x . f r » :
   au moins trois caractères isolés séparés par une espace sont recollés, 2 à 4 espaces séparent les mots ; une
   minuscule suivie d'une majuscule coupe la suite (« à J e a n »). Letter spacing collapsed for detection.
3. **Groupes regroupés librement (packs)** : téléphone (mot-clé de téléphone ; mobile 06/07 seul), RPPS, carte
   d'identité, passeport, RIB, SIRET, numéro fiscal, TVA, CAF, plaques, carte bancaire (Luhn) et IBAN français
   (mod 97) acceptent un séparateur (espace, point, tiret, tiret demi-cadratin, « / ») entre deux caractères ; nouvelle
   borne `group` (Python `engine._boundary_checks`, Rust `scanner.rs`) : la valeur est toute la suite de groupes,
   jamais un morceau d'un numéro plus long (un NIR sans clé n'est plus coupé en téléphone).
   Freely regrouped identifiers, with a new `group` boundary: the whole run of groups, never part of a longer number.
4. **Étage avec son rang** (« 3e étage, 75 cours des Vignes… ») dans les compléments d'adresse
   (`fr_address._COMPLEMENT`, Rust `floor_rank`). Floor with its rank in address complements.
5. **Tests terrain** : « SARL DUPONT » / « DUPONT SARL » (forme juridique de personne morale juste avant ou après)
   reste lisible, « M. Dupont » masqué, « EI Jean Dupont » masqué ; « quitter Lyon » garde la commune quand « Mme
   Lyon » figure dans le texte (verbes de lieu ajoutés à `LOCATIVES`) ; après une civilité, le mot capitalisé qui
   suit un nom trouvé entre dans la balise (« Mme Christine Pires Beaune », « M. Matthieu Orphelin »).
   Field tests: company names with a legal form stay readable; "quitter Lyon" keeps the town; after a civility, the
   capitalised word following a found name joins the tag.

## Limites restantes / remaining limits

- `crlf` et `line_break` restent bas (11.67 % et 17.67 %) : un saut de ligne entre deux lettres (« Jean⏎Dupont »,
  « 12 rue des⏎Lilas », « Bo⏎nneau ») n'est pas recollé, faute de pouvoir le distinguer d'une fin de ligne ordinaire
  sans risquer de fusionner deux lignes. `crlf` and `line_break` stay low: a break between two letters is not joined.
- `lower` reste à 29.33 % : les noms tout en minuscules sans indice fort ne sont pas détectés.
  `lower` stays at 29.33 %: all-lowercase names without a strong cue are not detected.
- Couples d'un même nom : « M. Le Floch » et « Mme Le Floch » reçoivent encore la même balise.
  Couples sharing a surname still get the same tag.
- L'équipe rouge du quotidien reste sous 90 % (86.71 %) ; les quatre autres familles dépassent 90 %.
  The everyday red team stays below 90 % (86.71 %); the four other families are above 90 %.

## Performance (meilleure de 5 à 7 passes, ms par document) / performance (best of 5 to 7 passes, ms per document)

| Corpus | Tour précédent / previous round | Ce tour / this round (3 mesures / runs) | Sans les règles regroupées / without the regrouped rules |
|---|---:|---:|---:|
| Synthétique / synthetic | 0.296 | 0.284 – 0.301 | 0.259 |
| BODACC | 0.197 | 0.207 – 0.221 | 0.213 |
| BOAMP | 0.947 | 1.063 – 1.092 | 1.108 |
| Judilibre | 1.079 (150 décisions) | 1.211 – 1.374 (145 décisions) | 1.375 |

Mesures bruitées (une autre voie tournait : ±7 % entre deux passes identiques). Retirer les 4 règles nouvelles et les
11 règles regroupées ne change rien au-delà du bruit. La normalisation native (où vivent BREAK et les lettres
espacées) pèse 18 % du temps sur BOAMP (0.209 ms sur 1.156) et 26 % sur Judilibre (0.388 sur 1.500). Face au tour
précédent, BOAMP paraît à +12 à +15 %, au-dessus du budget de 10 % : à vérifier sur une machine au repos avant de
conclure. Noisy measurements (another lane was running: ±7 % between two identical passes). Removing the 4 new and
11 regrouped rules changes nothing beyond noise. Native normalisation (BREAK and letter spacing) is 18 % of the time
on BOAMP and 26 % on Judilibre. Against the previous round, BOAMP looks +12 to +15 %, above the 10 % budget: to be
checked on an idle machine before concluding.

## Tests

- Windows : 4 595 réussis, 24 ignorés, 4 échecs (733 s) : l'archive des skills (attendu) et 3 tests de
  `tests/heuristics/test_heuristics_orgs.py` qui codaient l'ancienne règle (« Dupont SARL » masqué) ; mis à jour pour
  la règle du 26/10, ils passent (`tests/heuristics` : vert). ruff : vert. / Windows: 4,595 passed, 24 skipped,
  4 failed: the skills archive (expected) and 3 tests encoding the old rule, updated and now green; ruff green.
- WSL (noyau Linux reconstruit) / WSL (Linux core rebuilt) : 4 567 réussis, 7 ignorés, 1 échec (archive des skills,
  attendu) en 707 s. `cargo fmt --check` et `cargo clippy --all-targets -D warnings` : verts / green.
- Après les correctifs de la revue (noyau Windows reconstruit) / after the review fixes (Windows core rebuilt) :
  `tests/test_native_contracts.py`, `tests/test_everyday_formats_102.py`, `tests/heuristics`, `tests/test_text.py` :
  verts / green ; ruff vert / green ; `cargo fmt --check` et / and `cargo clippy --all-targets -D warnings` (WSL) :
  verts / green. Suite complète Windows / full Windows suite (649 s) : un seul échec, l'archive des skills (attendu,
  `tools/build_skills.py build` avant publication) / one failure only, the skills archive (expected). Suite WSL non
  relancée dans ce tour / WSL suite not re-run in this round. Performance (machine non au repos / machine not idle, meilleure de 5 / best of 5) : synthétique
  0.370, BODACC 0.216, BOAMP 1.127, Judilibre 1.508 ms par document ; normalisation native / native normalisation
  BOAMP 0.176 ms (0.194 avant le pré-test / before the pre-check), Judilibre 0.357 ms (0.361). À re-mesurer sur une
  machine au repos / to re-measure on an idle machine.

## Parité Python / Rust / parity

0 différence / 0 mismatch : 80 000 textes ciblés (`fuzz10.py`, graines 3, 4 et 5, sur le noyau final), 20 000 textes du fuzz de la revue
précédente (`fuzz2.py 3 20000`, texte normalisé, table de positions et sortie), 3 000 documents (`fuzz.py 1 3000`),
7 660 documents de l'équipe rouge (300 documents de base, 25 opérateurs) et du synthétique (graine de développement), 3 337 documents réels (moitiés dev
entières de BODACC, BOAMP et ParlaMint, et les 300 décisions Judilibre). 0 mismatch on targeted fuzz texts, the previous review's fuzz, red-team and real documents.

Après les correctifs de la revue, sur le noyau reconstruit / after the review fixes, on the rebuilt core :
`fuzz10.py` graines / seeds 41 à 45 (100 000 textes / texts) : 0 différence de normalisation, 0 de sortie /
0 normalisation and 0 output mismatches ; fuzz de la revue / review fuzz (`fuzz_rv.py`, graines / seeds 7 et 8,
60 000 textes : blocs de signature, sauts de ligne, lettres espacées, civilités, verbes de lieu, formes juridiques) :
0 et 0 ; équipe rouge et synthétique / red team and synthetic (`parity_redteam.py 300`) : 7 660 documents,
0 différence ; corpus réels / real corpora (`parity_real.py 5000`) : BODACC 1 358, BOAMP 1 523, ParlaMint 156,
Judilibre 300 documents, 0 différence.

## Reproduire / reproduce

Scripts dans le répertoire de travail de la voie E (non versionnés) / scripts in lane E's scratch directory:
`eval_dev.py --synthetic 1000 --bases 300 --real bodacc_fr,boamp_fr,parlamint_fr` (opérateurs du quotidien par
défaut / everyday operators by default), `fuzz10.py <graine> <n>` (Python contre Rust / Python against Rust).
