# Modèles NER locaux

> **English summary.** Optional local NER for French. It runs on ONNX Runtime with `tokenizers`: no torch, no
> network at run time. It raises person, organisation and location recall on top of the regex, validator and
> heuristic layers. Models are pinned by Hugging Face commit and SHA-256 and verified on first load.
> Install with `pip install "gdprguardian[ner]"` and `python tools/download_models.py`. Enable it with
> `Anonymizer(Settings(detectors=[load_detector()]))`. The author's `model_quantized.onnx` is broken, so use
> fp32 or the locally built, quality-gated INT8 (`--build-int8`). Measured numbers are below.

Le NER est **facultatif**. Il complète les motifs, les clés de contrôle et les heuristiques pour trois types :
personnes, organisations et lieux. Les identifiants structurés (NIR, IBAN, e-mail…) restent l'affaire des
motifs validés.

Il tourne **en local** avec ONNX Runtime et `tokenizers`, sans torch ni réseau. Il ne lit que le texte du
document en cours, ne conserve rien et ne journalise aucun contenu.

## Installation

```bash
pip install "gdprguardian[ner]"                # onnxruntime, tokenizers, numpy
python tools/download_models.py                # environ 272 Mo, révision et SHA-256 figés
# Facultatif : INT8 local, plus rapide, contrôlé contre le fp32 (exige le paquet onnx à la construction)
pip install onnx
python tools/download_models.py --build-int8
```

Les fichiers vont dans `models/cache/<modèle>/` d'un dépôt cloné, que git ignore. Hors dépôt, on peut aussi
utiliser `$GDPRGUARDIAN_MODELS_DIR/<modèle>` ou le cache utilisateur : `%LOCALAPPDATA%\gdprguardian\models` sous
Windows, `$XDG_CACHE_HOME` ou `~/.cache/gdprguardian/models` ailleurs.

Options de l'outil :

| Option | Effet |
|---|---|
| `--dest` | Choisit le dossier de destination. |
| `--endpoint https://miroir.example` | Télécharge depuis un miroir HTTPS, par exemple un stockage européen. Les empreintes restent vérifiées. |
| `--verify` | Revérifie les empreintes sans réseau, INT8 local compris. |
| `--build-int8` | Construit `model_int8.onnx` depuis le fp32 vérifié et le contrôle (exige le paquet `onnx`). |
| `--with-quantized` | Ajoute l'INT8 de l'auteur, pour évaluation seulement (voir plus bas). |

C'est le **seul** composant qui accède au réseau.

## Utilisation

```python
from gdprguardian import Anonymizer, Settings
from gdprguardian.ner import load_detector

ner = load_detector()          # None si l'extra [ner] ou le modèle manque ; ne lève pas d'exception
anonymizer = Anonymizer(Settings(detectors=[ner] if ner else []))
anonymizer.anonymize("Bonjour Jean-Baptiste Dupont, M. Martin vous attend chez Renault à Lyon.").text
# 'Bonjour [PERSONNE_1], M. [PERSONNE_2] vous attend chez [ORG_1] à [LIEU_1].'
```

`load_detector()` parcourt les dossiers dans l'ordre : `$GDPRGUARDIAN_MODELS_DIR`, puis le dépôt, puis le cache
utilisateur. Dans le premier dossier qui contient le modèle, il prend `model_int8.onnx` s'il a été construit et
inscrit au manifeste, sinon `model.onnx`. Pour forcer le fp32, passer `model_file="model.onnx"`.

La session ONNX est créée au **premier appel**, après vérification des empreintes. Elle est ensuite partagée
et sûre entre threads.

Fonctions utiles :
- `detector.warmup()` vérifie, charge et exécute une fois le modèle (sonde de disponibilité d'un serveur).
- `detector.replace(**réglages)` crée une variante qui partage la même session.

| Option | Défaut | Rôle |
|---|---|---|
| `threads` | `min(4, CPU)` | Threads intra-opérateur d'ONNX Runtime. Avec plusieurs requêtes en parallèle, garder `requêtes × threads ≤ cœurs`. |
| `entities` | `PERSON, ORG, LOCATION` | Types produits. Le modèle ne tourne pas si `Settings.entities` ou `exclude_entities` les écartent tous. |
| `thresholds` | `0,5` partout | Seuils du profil `standard`, par type. |
| `strict_thresholds` | `0,3` / `0,35` / `0,35` | Seuils du profil `strict` (personnes / organisations / lieux). |
| `gating` | `True` | N'envoie au modèle que les phrases qui portent un indice. |
| `max_tokens`, `overlap` | `256`, `32` | Fenêtre et chevauchement, en jetons. |
| `batch_tokens` | `512` | Jetons par appel du modèle, remplissage compris : beaucoup de cellules courtes ou deux fenêtres longues. |
| `model_file`, `verify` | | Variante du modèle ; contrôle des empreintes. |

Comportement selon le profil :
- `fast` : le NER est inactif.
- `standard` : seuils `thresholds`.
- `strict` : seuils `strict_thresholds`, plus bas, pour un rappel maximal.

Les zones dont le score est inférieur au `min_score` du moteur (0,5 en `standard`, 0,3 en `strict`) sont
écartées : un seuil NER plus bas que `min_score` reste sans effet.

## Fonctionnement

1. **Phrases.** Le texte est découpé en phrases, sans couper après « M. », « art. 12 » ou une initiale. Une unité
   ne traverse jamais un segment (cellule), un paragraphe ni une clôture de bloc de code. Un retour à la ligne
   souple est recollé : ligne qui continue en minuscule, ou ligne longue non terminée, typique d'un PDF.
2. **Filtre.** Seules les phrases qui portent un indice vont au modèle : un mot à majuscule (hors mots d'attaque
   courants comme « Le », « Nous », « Article ») ou une civilité, même abrégée en minuscules (« m. dupont »,
   « dr martin »). Des phrases identiques (cellules, signatures) ne sont inférées qu'une fois.
   Une ligne n'est sautée que si elle n'a rien à lire :
   - des chiffres ou des jetons opaques seulement (URL, adresse e-mail, empreinte, base64) ;
   - ou une instruction de code reconnue à sa syntaxe (`def f(x):`, `const x = f();`, `import numpy as np`),
     sans chaîne littérale ni commentaire.

   Le rappel prime : un en-tête « De : Jean Dupont <jean.dupont@…> », un lien Markdown, une ligne JSON, un
   commentaire de code, une requête SQL avec `'Dupont'` ou une phrase anglaise qui commence par « from » ou
   « let » passent par le modèle. Une clôture ``` termine l'unité en cours ; dans le bloc, chaque ligne est une
   unité et passe le même filtre. Un bloc non refermé ne cache donc rien.
3. **Fenêtres.** Chaque fenêtre compte au plus 256 jetons, avec 32 jetons de chevauchement, et commence sur un
   début de mot. Chaque jeton appartient à la fenêtre où il est le plus central : une entité coupée par une
   fenêtre est vue entière par la suivante.
4. **Lots.** Les séquences sont triées par longueur, puis groupées jusqu'à 512 jetons par appel, remplissage
   compris : une vingtaine de phrases, une centaine de cellules ou deux fenêtres longues. Une seule session ONNX sert tous les
   appels, sans attente active entre eux.
5. **Décodage vectorisé.** Pour chaque type, la probabilité est la somme B + I. Un jeton est une entité selon sa
   **masse** : la somme des probabilités des types voulus. Son type est le plus probable d'entre eux. Un nom
   partagé entre deux types reste ainsi masqué : « Malletier » a 0,48 en lieu et 0,42 en organisation, aucun
   type seul n'atteint 0,5, mais la masse vaut 0,9. Les types exclus (`entities`, `exclude_entities`) ne
   comptent ni dans la masse ni dans le choix du type. Les entités MISC sont ignorées.
   Une **hystérésis** évite de couper les entités de plusieurs mots : un jeton rejoint une entité dès la moitié
   du seuil, et l'entité est gardée si son maximum atteint le seuil. Sans elle, « Transports » et « Rivière » se
   séparent.
6. **Nettoyage.**
   - Les zones sont étendues aux mots entiers, traits d'union compris.
   - Les suites d'une même entité séparées par une apostrophe sont jointes (« d'Orléans »).
   - Restent hors zone : les civilités et les formules (« Bonjour », « Mamie »), les élisions minuscules et les
     particules orphelines.
   - Les noms de dossier restent aussi hors d'une personne. Le modèle rend « Dossier Lemoine » ou « Famille
     Dupont » en entier, et la portée y lirait un prénom : « Thomas Lemoine » recevrait alors une autre balise.
     On obtient « Dossier [PERSONNE_1] », puis [PERSONNE_1] pour Thomas Lemoine.
   - Les mots communs en tête d'un lieu ou d'une organisation sont retirés (« hôpital Necker » → « Necker »), mais
     jamais en tête d'une personne.
   - Une liste d'exclusion écarte les pronoms, les rôles, les jours et les mois.
   - Une zone ne traverse jamais une cellule de tableau.
   - Une zone ne touche jamais une balise déjà présente : le modèle étiquetait `ORG_2` dans « [ORG_2] », qui
     devenait « [[ORG_1]] ». Un texte déjà anonymisé repasse donc sans être altéré.
7. **Personnes.** Les zones de personnes portent `propagate=True` : le nom de famille est propagé s'il commence
   par une majuscule et n'est pas un mot courant. Un « jean blanc » écrit en minuscules ne masque donc pas chaque
   « vin blanc ». Leur priorité est `PRIORITY_NER` (55), sous les heuristiques (60), avec lesquelles elles
   fusionnent.

## Intégrité et sécurité

- **Fichiers figés.** La révision, la taille et le SHA-256 de chaque fichier sont écrits dans le code
  (`src/gdprguardian/ner/registry.py`). L'outil les vérifie au téléchargement : écriture dans un `.part`, puis
  renommage atomique. La bibliothèque les revérifie au chargement et lève `ModelIntegrityError` en cas d'écart.
- **INT8 local.** Il est construit depuis le fp32 vérifié, avec la recette `quantize_dynamic(MatMul,
  per_channel=True, weight_type=QUInt8)`. Un contrôle de qualité est obligatoire : au moins 98 % d'accord des
  étiquettes avec le fp32, et au moins 95 % sur les jetons d'entité. Sinon le fichier est supprimé. Son
  empreinte et celle de sa source sont inscrites dans `manifest.json`, et le chargement vérifie les deux.
- **Périmètre de confiance.** Le SHA-256 des fichiers figés est écrit dans le code. Celui de l'INT8 local est lu
  dans `manifest.json`, à côté du modèle. Quiconque peut écrire dans ce dossier peut donc remplacer l'INT8 et son
  manifeste, ou échanger un fichier entre sa vérification et son chargement. Ce dossier se protège donc comme le
  code installé.
  - Charger le modèle depuis les octets vérifiés fermerait cette fenêtre, mais double la mémoire résidente :
    550 Mo au lieu de 280 Mo, et un pic de 814 Mo au lieu de 376 Mo (mesuré en fp32).
  - Pour s'en tenir aux empreintes du code, passer `model_file="model.onnx"`.
- **Formats.** Uniquement de l'ONNX et du JSON : pas de pickle, pas de `trust_remote_code`. Le réseau n'est
  utilisé que par l'outil, en HTTPS. L'outil refuse toute redirection hors HTTPS, alors qu'urllib la suivrait.
- **Échec fermé.** Un fichier altéré lève `ModelIntegrityError` au premier appel, et l'anonymisation échoue
  au lieu de rendre un texte moins masqué. `detector.warmup()` permet de le savoir dès le démarrage.
- **Journaux.** Les journaux ne contiennent que des comptes et des durées. `repr(detector)` ne révèle aucun
  contenu.
- **Mémoire.** Le cache de mots du tokenizer (Unigram) est désactivé : sinon il garderait jusqu'à 10 000 mots des
  documents passés, des noms compris, pendant toute la vie du processus. Coût mesuré : 0,5 ms pour 10 Ko.

## Mesures (2026-10-24)

Conditions :
- Machine : AMD Ryzen mobile (Zen 3, 8 cœurs, 16 threads, sans VNNI), Windows 11, Python 3.12.11,
  ONNX Runtime 1.31.0.
- Réglages : 4 threads, valeurs par défaut.
- Script : `tests/ner/bench_ner.py`.
- Variabilité : les temps varient jusqu'à ±25 % d'une série à l'autre sur ce portable ; les plages ci-dessous
  couvrent plusieurs séries.

**Latence pour 10 Ko de texte français** (105 à 107 phrases, dont 37 % passent le filtre) :

| Configuration | Médiane |
|---|---|
| Heuristiques seules | 6 à 17 ms |
| + NER fp32, filtre actif (défaut) | 346 à 474 ms |
| + NER fp32, sans filtre | 1 091 à 1 289 ms |
| + NER INT8 local, filtre actif | 299 à 358 ms |
| + NER INT8 local, sans filtre | 736 à 1 025 ms |

- **Où va le temps.** 96 % du temps est passé dans `session.run`, et 90 % de ce temps dans les MatMul : le modèle
  est limité par le calcul (environ 85 MFLOP par jeton). Le reste du pipeline (découpage, filtre, décodage,
  nettoyage) coûte quelques millisecondes. Le découpage et le filtre restent linéaires : 4 à 55 ms pour
  200 Ko d'entrées hostiles (longues suites de parenthèses, de points, de mots-clés).
- **Filtre et INT8.** Le filtre est le premier levier (×2,6 à ×3,6). Le second est l'INT8 local : ×1,4 à ×1,8 sur
  le détecteur seul.
- **Threads.** 8 threads gagnent 15 à 30 % par rapport à 4. 16 threads logiques sont plus lents.
- **Lots.** Un lot est rempli jusqu'à 512 jetons, remplissage compris, plutôt qu'à un nombre fixe de séquences.
  - Cellules de tableur (900 cellules d'environ 5 jetons) : 1,84 s au lieu de 2,59 s avec des lots de 8 séquences.
  - Prose et fenêtres de 256 jetons : temps inchangés, aux variations de mesure près.
  - Au-delà de 1 024 jetons par lot, c'est plus lent.
- **Démarrage à froid.** Contrôle SHA-256, création de la session et premier appel prennent 0,65 à 0,71 s en fp32,
  et 0,37 à 0,52 s en INT8.

**Rappel du NER seul** : part des mentions de référence entièrement masquées, sans les heuristiques.
- Corpus de réglage : 80 textes, 129 mentions (`tests/ner/data/fr_sentences.txt`).
- Corpus de contrôle : 30 textes, 54 mentions (`fr_heldout.txt`), rédigé après le réglage et jamais utilisé pour
  régler.

| Modèle | Réglage, standard | Réglage, strict | Contrôle, standard | Contrôle, strict | Faux positifs |
|---|---|---|---|---|---|
| fp32 (`model.onnx`) | 97,7 % | 100 % | 96,3 % | 96,3 % | 0 |
| INT8 local (`model_int8.onnx`) | 98,4 % | 100 % | 96,3 % | 96,3 % | 0 à 1 |
| INT8 de l'auteur (`model_quantized.onnx`) | 1,6 % | 23,3 % | 7,4 % | 35,2 % | jusqu'à 15 |

Ce que le NER rate :
- En `standard`, des prénoms seuls dans un message familier (« Léa », « Maxime », « Zoé »), que le profil
  `strict` retrouve.
- Dans les deux profils, « Mehdi » et « Anaïs » dans « salut c'est Mehdi, tu peux dire à Anaïs… ».

**Gain par rapport aux heuristiques seules.** Mesuré dans le moteur, avec les heuristiques françaises dans leur
état du 2026-10-24, encore en développement en parallèle. Aucun faux positif dans ces configurations.

| | Heuristiques seules | + NER fp32, standard | + NER fp32, strict |
|---|---|---|---|
| Réglage | 65,9 % | 99,2 % | 100 % |
| Contrôle | 66,7 % | 98,1 % | 98,1 % |

Les heuristiques couvraient bien les personnes (98,8 % et 97,3 %), mais ni les lieux (0 à 4 %) ni les
organisations (0 à 20 %). Le NER apporte surtout ces deux types, et les personnes que les listes de noms ne
connaissent pas.

Ces deux corpus sont en prose. Les lignes d'en-tête de courriel, les liens, le JSON et les commentaires de code
sont couverts par des tests dédiés (`tests/ner/test_ner_model.py`).

Ces corpus sont petits et rédigés par nous. Ils montrent un ordre de grandeur, pas une garantie : il faut mesurer
sur ses propres documents.

## Pourquoi pas `model_quantized.onnx`

Le fichier INT8 publié par l'auteur s'accorde avec le fp32 sur 61,5 % des étiquettes, et sur seulement 12,7 % des
jetons d'entité. Sur ce processeur sans VNNI, deux causes cassent la quantification dynamique de ce modèle :
- une échelle par tenseur, écrasée par les valeurs aberrantes : 21 % de rappel en essai ;
- des poids signés, qui saturent le noyau u8s8 : 62 % d'accord.

Des poids **non signés par canal** évitent les deux : 99,4 % d'accord (98,5 % sur les jetons d'entité), avec le
rappel du fp32. C'est la recette de `--build-int8`.

La construction est déterministe pour une version donnée d'ONNX Runtime et d'onnx : deux constructions donnent le
même SHA-256. Comme elle peut changer d'une version à l'autre, son empreinte est inscrite au manifeste local et
non figée dans le code.

## Limites connues

- **Données d'entraînement.** Le modèle a appris sur WikiNER, avec des étiquettes « argent » issues de Wikipédia.
  Il est plus faible sur les messages familiers (prénoms seuls), le texte tout en minuscules et les cellules de
  tableau isolées.
- **Langue.** Le modèle est français. Sur d'autres langues, il reconnaît en partie les noms, sans évaluation.
- **Masquage des lieux et organisations.** Par défaut, les lieux et organisations sont masqués, ce qui protège
  mais retire du sens. Pour ne masquer que les personnes : `load_detector(entities=("PERSON",))`, ou
  `Settings(exclude_entities=...)`.
- **Retours à la ligne.** Leur traitement reste heuristique : seuil de 50 caractères pour une ligne longue non
  terminée.

## Licences

Voir `MODEL_LICENSES.yaml`.
- Les poids sont sous licence MIT (Crédit Mutuel Arkéa).
- Les données d'entraînement, WikiNER, sont sous CC BY 4.0 : l'attribution est recommandée. L'effet juridique de
  cette licence sur des poids entraînés n'est pas établi.
- Le tokenizer vient de `almanach/camembert-base`, sous licence MIT.
- Aucune donnée n'a été générée par un LLM.
