# Architecture de Gardien RGPD

Ce document fixe les contrats internes. Il s'adresse aux contributeurs et aux relecteurs.

## 1. Invariants non négociables

1. **Irréversibilité.** Aucune table de correspondance balise → valeur n'est créée, renvoyée, stockée ni
   journalisée. La cohérence (`[PERSONNE_1]` partout pour la même personne) vient d'une `Scope` :
   clé aléatoire de 256 bits, empreintes BLAKE2b à clé uniquement, clé effacée à la fermeture.
   Une `Scope` couvre **une requête** (un document, ou un lot de feuilles d'un même classeur), jamais plus.
2. **Aucun contenu dans les journaux.** Les logs ne contiennent que des métadonnées (et, en service, aucun événement
   par requête ni par document) : tailles, comptes par
   type, durées, codes d'erreur. Jamais de valeur détectée, d'extrait, de nom de fichier ni de hash de valeur.
3. **Aucun LLM, aucun appel réseau** dans la chaîne de traitement. Le NER éventuel tourne en local (ONNX).
4. **Licences compatibles MIT** uniquement (voir `docs/research/licenses.detail.md`). Ne jamais copier de
   code sous LGPL ou GPL : python-stdnum ne sert que d'oracle dans les tests.
5. **Rappel d'abord** : en cas de doute sur une donnée personnelle, on masque. Les validateurs ne doivent
   jamais rejeter un identifiant réel (mois fictifs du NIR, Corse, La Poste, etc.).

## 1 bis. Choix du pays

| `countries` | Comportement |
|---|---|
| `("FR",)` (défaut) | Packs `INTL` + pays listés. Robuste et prévisible : à privilégier. |
| `"all"` | Tous les packs. Niveaux A partout ; niveaux B et C seulement avec leurs mots-clés locaux. |
| `"auto"` | **Expérimental** : `INTL` d'abord, puis pays déduits des preuves validées (IBAN, téléphones E.164, domaines des e-mails) et des mots-clés ; avertissement dans le rapport. |

Un test d'un pack pays doit donc préciser `countries=[...]` ou `countries="all"`.

## 2. Modules

| Module | Rôle | Statut |
|---|---|---|
| `_text.py` | normalisation avec conservation des positions, repliement pour les mots-clés | cœur, figé |
| `types.py` | `Span`, `Analysis`, `AnonymizedText`, priorités | cœur, figé |
| `labels.py` | libellés des balises (fr/en/neutre), alias | cœur, figé (extensible via les packs) |
| `keywords.py` | index Aho-Corasick des mots de contexte, `KeywordHits.near()` et `last_end()` | cœur, figé |
| `packs/` | chargement des packs TOML, `PatternRecognizer` | cœur, figé |
| `validators/` | clés de contrôle (`checksums.py`, `fr.py`, `intl.py`, un module par pays) | extensible |
| `detectors/intl.py` | IBAN, MRZ, e-mail, téléphones +CC | cœur |
| `detectors/fr.py` | dates de naissance cohérentes avec un NIR du document | extensible |
| `heuristics/` | personnes, adresses, organisations (sans ML) | extensible |
| `engine.py` | `Anonymizer` : cascade, résolution, propagation, rendu | cœur, figé |
| `scope.py` | `Scope` irréversible, coréférence des personnes par empreintes | cœur, figé |
| `custom.py` | règles de l'organisation (masquer, conserver, termes imposés ou permis), voir `docs/REGLES.md` | cœur |
| `_hardening.py` | durcissement des processus : non lisibles, sans core dump, sans secret, sans sortie standard | cœur |
| `operators.py`, `sanitize.py`, `locale.py` | opérateurs, nettoyage de sortie, mode `auto` | cœur |
| `documents.py` | façade fichier → Markdown anonymisé, types partagés | contrat figé |
| `convert/` | documents → Markdown (PDF, DOCX, PPTX, ODT, HTML, EML, MSG, RTF, TXT) | extensible |
| `tabular/` | Excel, ODS, CSV → Markdown anonymisé | extensible |
| `ner/` | NER ONNX optionnel | extensible |
| `server/` | API REST, serveur MCP en ligne, envois hors bande ; clés d'API (`security.py`), identité pseudonyme (`clients.py`), limiteur d'abus (`limiter.py`) | extensible |

## 3. Contrat d'un détecteur

```python
class MyDetector:
    id = "MY_DETECTOR"

    def __init__(self, pack): ...          # appelé une fois au chargement : compiler ici, pas dans detect()

    def detect(self, ctx) -> list[Span]:   # positions dans ctx.text (texte normalisé)
        ...
```

Le détecteur est déclaré dans le pack TOML : `[pack] detectors = ["module:Classe"]`.

`ctx` (`engine.DetectionContext`) expose :

| Attribut ou méthode | Usage |
|---|---|
| `ctx.text` | texte normalisé (homoglyphes repliés, chiffres ASCII, espaces unifiés, invisibles retirés) |
| `ctx.folded` | même longueur, en minuscules et sans accents : pour comparer avec des listes |
| `ctx.has("digit")`, `ctx.has(("x", "y"))` | préfiltres bon marché (sous-chaînes dans le texte replié) |
| `ctx.near(groups, start, end, before, after)` | un mot-clé de contexte est-il proche ? (respecte les segments ; l'en-tête de colonne d'un tableau Markdown vaut pour toute sa colonne) |
| `ctx.vetoed(groups, vetoes, start, end, after)` | un mot-veto se trouve-t-il entre le dernier mot-clé et la valeur ? |
| `ctx.any_context(groups)` | un mot-clé du groupe est-il présent quelque part ? |
| `ctx.found` | zones déjà trouvées dans ce passage par les motifs (exécutés avant les détecteurs), **en lecture seule** |
| `ctx.segment(pos)` | `(index, début, fin)` du segment (cellule de tableur) ; `(-1, 0, len)` hors segments |
| `ctx.countries`, `ctx.language`, `ctx.settings`, `ctx.strict` | réglages et pays actifs |

Règles :
- **Ne jamais produire une zone qui traverse une fin de segment** (`end <= ctx.segment(start)[2]`).
- Personnes : `entity="PERSON"`, `label="PERSON"`, `propagate=True`. Mettre dans `forms` les formes sûres
  à propager (le nom seul s'il n'est pas un mot courant). **Laisser les civilités hors de la zone**
  (« M. [PERSONNE_1] ») ; le moteur les retire de toute façon.
- Choisir la priorité parmi les constantes de `types.py` (`PRIORITY_HEURISTIC`, `PRIORITY_NER`…).
- Aucune E/S, aucun réseau, aucun état modifiable partagé dans `detect()` : le détecteur doit être sûr
  entre threads.

## 4. Pack pays (TOML)

```toml
[pack]
id = "BE"; name = "Belgique"; version = "2026.10.0"; country = "BE"; languages = ["fr", "nl", "de"]
detectors = []

[locale]          # indices pour le mode auto
phone_codes = ["32"]; tlds = ["be"]; iban_countries = ["BE"]; languages = ["fr", "nl", "de"]

[context.niss]    # groupes de mots de contexte, qualifiés en "BE:niss"
fr = ["numéro national", "niss"]; nl = ["rijksregisternummer"]

[headers]         # en-têtes de colonnes de tableur -> clé de libellé
NISS = ["niss", "numéro national"]

[labels.NISS]     # nouveau libellé de balise
fr = "NISS"; en = "NISS"; neutral = "NATIONAL_ID"

[[recognizer]]
id = "BE_NISS"; entity = "NATIONAL_ID"; label = "NISS"; tier = "A"
pattern = '[0-9]{2}{S}[0-9]{2}{S}[0-9]{2}{S}[0-9]{3}{S}[0-9]{2}'   # {S} séparateur optionnel
validator = "be.niss"; boundary = "alnum"; context = "niss"; prefilter = "digit"
```

Niveaux : **A**, clé forte, masqué sans contexte ; **B**, clé faible, contexte obligatoire sauf en profil
`strict` ; **C**, sans clé, contexte obligatoire ; **L**, clé non garantie, la clé n'augmente que le score.
Contexte : `context` (groupes) et `window = [avant, après]` en caractères. `veto` (groupes) : un mot-veto
placé **entre** le dernier mot-clé et la valeur annule le contexte, l'indice le plus proche l'emporte
(« né le 3 mai 1953. … la réunion du 12/02/2026 » : la seconde date reste). Les en-têtes de colonnes et les
mots-clés situés après la valeur ne sont jamais annulés. Ne mettre en veto que des événements non
personnels (réunion, facture…) : rappel d'abord.
Clé fausse (faute de frappe, OCR) : `invalid = "context"` garde la valeur si un mot-clé du contexte est
proche (score × 0,6, priorité `PRIORITY_CONTEXT_ONLY`). Pour un format imprimé très typé (NIR en
1-2-2-2-3-3-2, carte et IBAN par blocs de 4), un recognizer de niveau L suffit : la forme est la preuve.
Une forme compacte à clé fausse sans mot-clé n'est pas masquée (15 chiffres peuvent être un IMEI).
Mots de contexte d'un pack pays : ils comptent comme **preuve de pays** en mode auto, donc ils doivent être
propres au pays. Les mots génériques (téléphone, IBAN, carte d'identité, plaque…) vivent dans `INTL`
(`INTL:phone`, `INTL:iban`, `INTL:id_card`, `INTL:plate`). Un sigle partagé entre pays (NIF, NSS…) va dans
un groupe déclaré `[locale] passive_context = ["groupe"]` : contexte de proximité, jamais preuve.
Macros de motif : `{S}` séparateur optionnel, `{SEP}` séparateur, `{LB}` borne gauche alphanumérique (à
placer après le premier caractère), `{RB}` borne droite. Les motifs avec `{LB}`/`{RB}` restent en Python.
Politique `policy = "company"` : identifiant d'entreprise conservé (`company_ids="auto"`), sauf en profil
`strict` ou si une mention d'entrepreneur individuel figure **n'importe où** dans le document.
Validateurs : `fn(candidat: str) -> str | None`, qui renvoie la valeur canonique (sans séparateurs).
Motifs : bornes vérifiées en code (`boundary`), quantificateurs **toujours bornés** (pas de `+` ni de `*`
non bornés sur de longues séquences : risque de coût quadratique).

## 5. Conventions de code

- Identifiants (variables, fonctions, classes) **en anglais**.
- Commentaires **courts, utiles, en français et en anglais** : `# Clé NIR : 97 - (n mod 97) / NIR key`.
  Ne pas commenter l'évident. Docstring de module bilingue sur une ou deux lignes.
- Annotations de type partout ; `ruff check` sans erreur (longueur de ligne 120).
- Tests dans `tests/<module>/` ; aucun test ne dépend du réseau (sinon marqueur `network`).
- Performance : compiler à l'initialisation, préfiltrer avant les regex, éviter les boucles Python par
  caractère, mesurer avant d'optimiser.
- Commandes, depuis la racine du dépôt (Windows ; `.venv/bin/python` et `.venv/bin/ruff` sous Linux et macOS) :
  - `.venv/Scripts/python.exe -X utf8 -m pytest tests -q -p no:cacheprovider`
  - `.venv/Scripts/ruff.exe check src tests`

## 6. Noyau Rust (`rust/`, module `gdprguardian_core`)

Accélérateur **optionnel** (PyO3 0.30, ABI stable `abi3` dès Python 3.11, construit par maturin). Chaque classe
Python délègue à son jumeau Rust quand le noyau est installé et que `Settings.native` est vrai ;
`GDPRGUARDIAN_PURE_PYTHON=1` ou `Settings(native=False)` gardent le moteur Python seul, qui reste la référence et
fonctionne toujours sans le noyau.

| Module Rust | Référence Python | Rôle |
|---|---|---|
| `unicode.rs` | `_text.char_flags`, `_text.plane_classes`, `_text.ignorecase_data` | **table Unicode unique** du noyau : classes de `str` et de `re`, casse complète, repliement, équivalences de `re.IGNORECASE` ; plan de base construit au démarrage, plans hors BMP chargés une fois, à la première rencontre |
| `prepare.rs`, `text.rs` | `_text.normalize`, `_text.fold`, `locale.detect_language` | préparation en un appel : transcodage, gras Markdown, coupes (invisibles, césures), table des positions ; langue |
| `keywords.rs` | `keywords.KeywordIndex`, `KeywordHits` | mots-clés de contexte, un passage Aho-Corasick, `near` et `last_end` |
| `pattern/` | arbre de syntaxe de `re` (`_native.syntax`) | compilation **exacte** des motifs : `\w`, `\d`, `\s`, `re.IGNORECASE` de Python, assertions de tête et de fin (look-arounds, `\b`, `$`) réécrites sans retour arrière ; budget de compilation borné |
| `scanner.rs`, `windows.rs` | `Anonymizer._run`, `DetectionContext.near`/`vetoed`, `_boundary_checks` | motifs des packs et règles d'organisation (`regex-automata`, temps linéaire), recherche bornée aux fenêtres candidates |
| `validators/` | `validators/*.py` | clés de contrôle de tous les packs (87 validateurs), sémantique `str` de Python (`pystr.rs`) |
| `names/` | `heuristics/fr_names.py`, `heuristics/_lexicon.py` | personnes : jetons, indices, champs, tableaux, décision, forme canonique |
| `detectors/` | `heuristics/fr_address.py`, `heuristics/organizations.py`, `detectors/intl.py`, `detectors/fr.py` | adresses ; candidats d'organisations ; e-mail, IBAN, MRZ ; dates de naissance liées au NIR |
| `finalize/` | `engine._finalize`, `_propagate`, `_render`, `resolve`, `merge_same_entity`, `_apply_keep`, `scope.Scope`, `operators.py` | résolution, propagation, rendu, rapport et explications, portée irréversible |
| `engine/` | `Anonymizer.analyze`/`anonymize`, `_detect_all`, `markdown_table_zones`, `sanitize_output`, `locale.evidence`, décision des organisations | **moteur fusionné** : un document en deux appels (détection, finalisation), zones gardées en Rust de bout en bout ; Python n'exécute que les détecteurs sans jumeau (téléphones `phonenumbers`, NER, détecteurs ajoutés) et, sur un texte décomposé (diacritiques combinants), les trois détecteurs à vue NFC (noms, adresses, organisations) |
| `tabular/` | `tabular/_reader.py` (python-calamine) | lecture des classeurs xlsx : ZIP strict, XML en flux, limites anti-bombe ; tout cas non canonique est rendu à python-calamine |
| `lib.rs` | `_native.py` | enregistrement PyO3, `Scanner` |

Règles du noyau :
- Rust sûr (aucun `unsafe`), aucune panique sur une entrée ; le crochet de panique n'écrit qu'un libellé fixe (un
  message pourrait citer le texte) ; mémoire bornée ; GIL rendu (`py.detach`) pendant le travail lourd ;
  positions toujours en points de code Python.
- **Une seule source de vérité** : lexiques, listes de mots, tables Unicode de l'interpréteur, tables de repli,
  libellés et réglages viennent de Python à la construction. Rust ne devine jamais une propriété Unicode : `\w`,
  `str.isupper()`, `str.lower()` ou `re.IGNORECASE` répondent comme l'interpréteur, quelle que soit la version
  d'Unicode de Rust, y compris dans les motifs des packs et les règles d'organisation.
- Hors du domaine natif (demi-codet isolé, texte de plus de 1 Go, objet inattendu), un appel rend `None` et la
  référence Python prend le relais : jamais de résultat approché.
- Contrat de version : le noyau publie `CONTRACT`, le paquet attend le même nombre (`_native.CONTRACT`). Un noyau
  d'une autre version est écarté au chargement, avec un avertissement : le moteur Python seul répond, jamais une
  liaison d'une autre signature. `Settings(native=False)` ne touche jamais au noyau (jumeaux construits à la demande).
- Règles d'organisation reçues par le service (non sûres) : compilées sur un seul fil, 2 Mio au plus par automate
  (l'expression ancrée d'un motif à assertion de tête partage ce plafond), 16 Mio pour l'ensemble des règles, cache
  paresseux de 2 Mio ; au-delà, règle refusée avec sa raison, avant d'allouer. Les packs intégrés gardent 32 Mio par
  automate et la compilation parallèle.
- Fils d'exécution : seulement pour compiler les motifs (`scanner::compile_all`), bornés, joints, avec repli sur
  le fil courant si le système refuse d'en créer. Les travailleurs du service n'ont pas le droit de créer un fil
  (`RLIMIT_NPROC=0`) et le zygote doit n'en avoir qu'un au moment du `fork`.
- Portée irréversible : empreintes BLAKE2b à clé, clé tirée par le système, jamais visible de Python, effacée
  (`zeroize`) à la fermeture.
- Construction : `maturin build --release` (LTO complète, une unité de code), jeu d'instructions x86-64 de base.
  L'image Docker optimise en plus le noyau par profil d'exécution (`tools/pgo.py`, par défaut ; `--build-arg PGO=0`
  pour une roue reproductible au bit près, voir `deploy/README.md`) : 10 à 12 % de temps en moins sur le moteur
  complet avec le corpus, 2 à 5,5 % sur des textes hors profil.
- Mesures (corpus de 1 000 documents de 1,9 Ko en moyenne, un cœur) : 0,45 ms par document sous Windows, soit
  4,2 Mo/s, et 0,48 ms sous Linux, contre 3,9 et 3,7 ms pour le moteur Python seul ; un texte de 10 Mo en 2 s.

## 7. Contrat de parité Python / Rust

Un chemin Rust donne un résultat **identique** à la référence Python : mêmes zones (début, fin, entité,
libellé, source, valeur, score arrondi à 9 décimales, priorité, `personal`, `forms`, `propagate`), même texte
anonymisé, même rapport (`explain` compris). Toute différence est un défaut du jumeau Rust.

Preuves :
- **tests différentiels** sur les 1 000 documents du corpus, les suites existantes et un fuzzing Hypothesis
  à l'Unicode piégeux (accents, diacritiques combinants, astraux, invisibles, U+001C-U+001F, CRLF, jetons très
  longs, tableaux) : `tests/test_native.py` et `tests/test_native_engine.py` (motifs, moteur complet),
  `tests/test_unicode_native.py` (chaque bit de chaque point de code des 17 plans), `tests/test_prepare_native.py`,
  `tests/test_validators_native.py` (au moins 20 000 candidats par validateur), `tests/heuristics/test_names_native.py`,
  `tests/test_detectors_native.py`, `tests/test_finalize_native.py`, `tests/test_engine_fused.py` (moteur fusionné
  sur 9 jeux de réglages), `tests/test_tabular_native.py` (classeurs générés et mutés contre python-calamine) ;
- **gardes de dérive** (`tests/test_native_contracts.py`) : le Rust recopie à la main des motifs `re`, des
  listes, des seuils et des fonctions. Chaque cible Python recopiée y a l'empreinte de sa **source** (arbre
  syntaxique sans commentaires ni docstrings : reformater ne change rien) et le nom de son jumeau Rust ; modifier
  le Python sans le Rust fait échouer le test avec la cible, le jumeau à mettre à jour et les tests différentiels
  à relancer. Le même fichier vérifie que chaque jumeau cité existe, que les constantes recopiées en Rust
  (particules, conjonctions, formes « & Fils », longueurs IBAN, réseaux de cartes, bits des classes…) valent
  leurs sources Python, et, noyau présent, que chaque jumeau se construit (aucun repli silencieux sur Python)
  et que chaque validateur natif a son contrat ;
- **contrats d'exécution** : le détecteur de noms compare à sa construction ses constantes à celles de Python
  (`CONTRACT`) et refuse tout écart.
- **motifs** : chaque motif intégré est comparé à `re` sur des textes piégés (`tests/test_native_engine.py`),
  ainsi que des motifs aléatoires (classes Perl, `(?i)` avec « İ », « ı », « ſ », « K », assertions) ; un motif
  que le compilateur ne sait pas rendre exactement est refusé avec sa raison et reste à Python (un seul parmi
  les 149 motifs des packs : `NL_POSTCODE_LABELED`, assertion arrière après une répétition paresseuse).

Procédure : modifier la référence Python, porter la modification dans le jumeau Rust, relancer les tests
différentiels, puis `python tests/test_native_contracts.py` imprime la table d'empreintes à recopier.

## 8. Service : une requête, un processus

Le processus d'accueil ne fait que HTTP, l'admission, l'ordonnancement et le dépôt des résultats ; il ne lit,
n'anonymise ni ne compile jamais un contenu. Les règles d'organisation n'y subissent qu'un contrôle de structure
(nombre, longueurs, libellés) ; leurs motifs sont compilés dans le travailleur, qui renvoie un code fermé
(`invalid_rules`, 422 `invalid_request` avec le numéro de la règle et la raison du moteur, jamais le contenu).
Chaque requête (texte ou document, REST ou MCP, envoi hors bande) est traitée de bout en bout dans un **processus
isolé à usage unique** (`server/isolation.py`, `convert/_sandbox.py`). Dès la configuration lue, le processus
d'accueil retire de son environnement toutes les variables `GDPRGUARDIAN_*`, clés d'API comprises (sauf l'interrupteur
`GDPRGUARDIAN_PURE_PYTHON`), avant de lancer le moindre processus enfant.

```
client ─► en-têtes de sécurité ─► journal (erreurs 5xx seulement) ─► hôte
       ─► porte d'entrée (GateMiddleware) : identité pseudonyme, refus inter-sites, clé éventuelle, limiteur
          (seaux, requêtes en vol par client et par préfixe) — avant le corps
       ─► admission (budget mémoire équitable par préfixe, avant le corps) ─► taille et durée du corps ─► route
       ─► place équitable (FairScheduler : client, préfixe, place réservée) ─► sortie maximale réservée au budget
       ─► travailleur neuf : conversion + anonymisation + portée, sortie plafonnée
       ─► réponse (temps mesuré rendu au limiteur, réservation ramenée au résultat jusqu'à la fin de la réponse)
```

- **Service à clés** (`GDPRGUARDIAN_API_KEY_SHA256`, le service officiel) : `Authorization: Bearer <clé>` exigé, une
  clé par organisation, donnée par sa seule empreinte SHA-256 ; une clé en clair dans l'environnement est
  refusée au démarrage. Le mode public (`GDPRGUARDIAN_PUBLIC=1`, aucune clé) reste possible pour un autre déploiement.
- **Identité** (`server/clients.py`) : adresse lue dans l'en-tête de confiance posé par Nginx (`X-GG-Client`), retiré
  de la requête aussitôt ; pseudonyme immédiat, 8 octets de HMAC-SHA256 sous un secret de 32 octets en mémoire,
  renouvelé toutes les 24 h (le précédent reconnu 10 min) ; niveaux IPv4 /32 + /24, IPv6 /64 + /48. L'adresse
  n'est jamais gardée, journalisée, ni mise dans un datagramme, une erreur ou une réponse. Sans en-tête : principal
  LOCAL (le serveur lui-même ; avec `GDPRGUARDIAN_LOCAL_TOKEN_SHA256`, seulement s'il présente le jeton local dans
  `X-GG-Local`, sinon seau commun : un travailleur compromis qui joint le socket ne passe pas pour lui), hors
  budgets, deux traitements au plus, jamais la place réservée, datagrammes `"src":"protocol"`.
- **Pages tierces** : une requête de navigateur venue d'une autre page (`Sec-Fetch-Site` autre que `same-origin` ou
  `none`) reçoit 403 avant tout compte (Nginx, puis la porte d'entrée).
- **Limiteur** (`server/limiter.py`, mémoire seule, avant le corps) : seau des requêtes bon marché (10/s, rafale 30),
  GCRA au coût en secondes de travailleur (0,5 s/s, rafale 20 s, dette jusqu'à l'échéance du plus long travail,
  préfixe ×2 ; estimation par `Content-Length` multipliée par la lenteur observée du client ou de son préfixe, de 1
  à 100 ; correction par le temps mesuré si un travailleur a servi, sinon l'estimation reste due, sauf refus de
  capacité 503), 3 requêtes à contenu en vol par client (1 en cours + 2 en attente) et 12 par préfixe (un envoi
  en traitement après son 202 y compte encore, mais `/mcp` et la création d'envoi ne le voient qu'à la prise
  d'un travailleur, leurs corps en vol restant plafonnés dès l'accueil : suivre un envoi n'est jamais refusé
  parce que les envois du client sont en traitement), en cours au
  plus la moitié des places non réservées par préfixe, une place réservée aux requêtes estimées sous 0,2 s,
  délestage (503) au-delà de 10 s d'attente estimée ; 100 000 clés par niveau, débordement à la Space-Saving ;
  429/503 + `Retry-After` (aléa de 0 à 20 %) + `RateLimit`/`RateLimit-Policy` ; modes enforce, dry-run (seaux
  seulement), off ; erreur interne : la requête passe, avertissement agrégé au plus une fois par minute ; compteurs
  agrégés seulement (`/status`). Base légale du traitement transitoire de l'adresse : intérêt légitime (art. 6.1.f,
  considérant 49) et art. 32 du RGPD. Détail et valeurs : `deploy/README.md`.
- **Corps** : chaque corps arrive en entier en 15 s plus sa taille à 128 Kio/s (`GDPRGUARDIAN_MIN_BODY_RATE_KIB`),
  sinon 408 et connexion fermée : un corps qui goutte ne tient ni connexion ni budget.
- **Journaux** : aucun journal d'accès ni d'activité en service (`--log-level warning`) ; événements par requête et
  par document en DEBUG seulement, réponses 5xx en WARNING, métadonnées seulement.
- **Isolation des résultats** : chemins synchrones sans aucun stockage ; chemin différé joignable par capacité
  seulement (256 bits, dérivée du jeton par HMAC sous une clé en mémoire, gardée en empreinte, comparée en temps
  constant, jeton à usage unique, résultat effacé après lecture complète et délai de grâce, toujours 404 pour faux,
  expiré, utilisé ou lu, le motif n'étant dit qu'au détenteur de la capacité, aucune route qui liste) ;
  `Cache-Control: no-store` partout.

- **Zygote** (Linux) : lancé au démarrage, durci, préchargé une fois (packs, automates, noyau Rust, lexique des
  noms, convertisseurs, moteurs par défaut), à un seul fil ; il crée chaque travailleur par `fork` (mémoire
  partagée en copie à l'écriture), ne voit jamais de document et tue lui-même ses enfants. Une réserve de
  travailleurs neufs, amorcés sur des données fictives, attend les requêtes (`GDPRGUARDIAN_PREWARM_WORKERS`).
  Windows et macOS : lancement « spawn », un Job Object sous Windows.
- **Confinement du travailleur**, avant tout document : sorties standard vers `/dev/null`, aucune variable
  `GDPRGUARDIAN_*`, non lisible (`PR_SET_DUMPABLE=0`), sans core dump, `RLIMIT_NPROC=0` (ni processus ni fil),
  mémoire plafonnée (`RLIMIT_AS`, `GDPRGUARDIAN_WORKER_MEMORY_MB` au-delà de l'empreinte au repos), mort avec son
  parent (`PR_SET_PDEATHSIG`), aucun descripteur hérité, tué à l'échéance. Réponses : JSON borné et texte UTF-8
  brut, jamais de pickle ; ce qui est journalisé appartient à des ensembles fermés.
- **Admission** (`server/admission.py`) : chaque requête qui porte un corps réserve sa taille annoncée
  **avant** la lecture du corps, dans un budget (`GDPRGUARDIAN_QUEUE_MB`) ; à l'attribution d'un travailleur, elle
  réserve aussi deux fois la plus grande réponse possible, ramenées à la taille réelle du résultat, jusqu'à la fin de
  la réponse (`Reservation`). Clé d'équité : le préfixe réseau d'un client public, sinon son principal. Une clé qui
  ne tient rien est admise si la requête tient dans le budget ; au-delà de sa part équitable, une clé ne peut pas
  entamer la réserve gardée pour les autres (le dernier quart, au moins la plus grosse requête). Budget épuisé : 503
  et `Retry-After`, corps lu à vide (borné) sauf `Expect: 100-continue`. Un corps « chunked » réserve la limite, puis
  sa taille réelle. Un résultat (texte ou Markdown) ne dépasse jamais 1/8 du dépôt : le travailleur répond 413 sans
  l'envoyer.
- **Échéance** : délai de conversion, plus une seconde par 250 Ko reçus. Dépassée, le travailleur est tué : 422
  `processing_timeout` pour un texte, 422 `conversion_timeout` pour un document (même réponse au prochain essai,
  donc jamais 5xx). Travailleur en échec : 500 `internal_error` ; aucun travailleur disponible : 503
  `service_busy`. Catalogue complet : `deploy/README.md`.
- **Gros documents : limites** (publiées sur le site et dans `deploy/README.md`, « Gros documents » ; chaque refus est
  un 413 dont le message nomme la limite, `server/errors.py`) :
  - **50 Mo par fichier** (50 Mio, `GDPRGUARDIAN_MAX_UPLOAD_MB`), tous formats et tous chemins (site, REST, MCP) :
    refusé dès la taille annoncée (Nginx au-delà de `51m` ; le service au-delà de 50 Mio plus 64 Kio d'enveloppe
    multipart ; un `PUT` hors bande sans le lire), sinon à la lecture ;
  - **1 000 000 de caractères par texte collé** (`/v1/anonymize/text`, `anonymize_text` ;
    `GDPRGUARDIAN_MAX_TEXT_CHARS`) ;
  - **12 500 000 caractères de résultat par document** : 1/8 de `GDPRGUARDIAN_MAX_STORE_CHARS` (100 millions pour le
    service officiel, `compose.yaml` ; 25 millions avec le défaut de 200 millions). Le travailleur mesure le résultat
    et répond 413 `document_too_large` sans rien envoyer ; un texte converti de plus du double du plafond est refusé
    dès la conversion, avant le moteur (`isolation._CONVERTED_SLACK`) ;
  - **10 000 pages ou diapositives** par document (`GDPRGUARDIAN_MAX_PAGES`) ;
  - HTML (pages, courriels HTML, sortie de mammoth) : **1 000 000 de balises, ouvrantes et fermantes**, comptées avant
    l'analyse (un « < » isolé du texte n'en est pas une ; `convert/_html.MAX_TAGS`), et **256 niveaux
    d'imbrication**, vérifiés juste après l'analyse (`MAX_DEPTH` : markdownify descend récursivement) ;
  - Word : **100 000 paragraphes, cellules de tableau comprises**, et **1 000 000 d'éléments XML**, comptés avant
    mammoth dans le document, ses notes et ses commentaires, quel que soit le préfixe d'espace de noms
    (`convert/_docx.MAX_PARAGRAPHS`, `MAX_ELEMENTS`) ;
  - **échéance de traitement** : 60 s plus 1 s par 250 Ko reçus (`isolation.deadline_s`,
    `GDPRGUARDIAN_CONVERSION_TIMEOUT_S`), soit 270 s pour 50 Mio ; c'est aussi le délai interne des convertisseurs et
    des tableurs ; au-delà, le travailleur est tué (422) ;
  - **échéance du corps** : 15 s plus la taille (annoncée, sinon le plafond de la route) à 128 Kio/s
    (`ServerConfig.body_deadline_s`, `GDPRGUARDIAN_MIN_BODY_RATE_KIB`), soit environ 415 s pour 50 Mio ; au-delà, 408.
- **Gros documents : ordonnancement** (`server/admission.py`, `server/limiter.py`) :
  - **délestage par simulation de la file, place par place** (`FairScheduler.estimated_wait`) : les travaux en cours
    finissent selon leur estimation (passé celle-ci, un travail est supposé durer encore autant qu'il a déjà duré,
    jamais au-delà de son échéance) ; les requêtes que l'équité sert avant la nouvelle venue (sa propre file, puis la
    tête de file de chaque clé qui tient moins de places ou attend depuis plus longtemps) prennent tour à tour la
    première place qu'elles ont le droit de prendre (les grosses hors de la place réservée, `max_running` par client),
    puis la nouvelle venue ; au-delà de 64 requêtes devant elle, le reste compte pour sa part moyenne. Une place
    utilisable libre et personne devant : attente nulle. Attente estimée au-delà de 10 s
    (`GDPRGUARDIAN_LIMIT_MAX_WAIT_S`) : 503 `service_busy` avec `Retry-After` ;
  - **place réservée** : une place (`GDPRGUARDIAN_LIMIT_RESERVED_SLOTS`, toujours au moins une place laissée à tous)
    gardée aux requêtes estimées sous 0,2 s (`GDPRGUARDIAN_LIMIT_SMALL_S`), jamais prise par une grosse requête ni
    par le principal LOCAL. Si bien qu'un petit texte n'est jamais délesté à cause de gros documents tant qu'elle est
    libre ;
  - **règle des 5 s** : un petit travail qui dure plus de 5 s (`admission._SMALL_OVERRUN_S`) compte dès lors comme gros
    pour l'attribution des places et dans la simulation : la place réservée revient aux petites requêtes dès qu'une
    autre place se libère.
- **Ligne de commande et bibliothèque locales** : d'autres valeurs par défaut, voulues et inchangées.
  `gdprguardian anonymize` et `documents.anonymize_document` prennent `DocumentOptions()` : 50 Mio par fichier, mais
  **500 pages ou diapositives** (`max_pages`) et une **échéance de conversion fixe de 60 s** (`timeout_s`, sans la
  seconde par 250 Ko ; toute la chaîne d'un tableur, la seule conversion pour les autres formats, dont
  l'anonymisation n'a pas d'échéance), ni plafond de résultat, ni refus avant le
  moteur, ni limite d'un million de caractères pour un texte (`gdprguardian anonymize -` lit toute l'entrée
  standard). Les limites des convertisseurs (balises et imbrication HTML, paragraphes et éléments Word, cellules et
  parties des tableurs) sont les mêmes partout. Le service passe ses propres valeurs
  (`DocumentOptions(max_pages=GDPRGUARDIAN_MAX_PAGES, timeout_s=…)`, puis l'échéance de chaque requête comme délai
  interne).
- **Équité** (`FairScheduler`) : au plus `GDPRGUARDIAN_MAX_CONCURRENCY` travailleurs occupés. Une place libérée va à
  la clé en attente qui en tient le moins, puis à celle qui attend depuis le plus longtemps (depuis son arrivée,
  ou depuis la fin de son dernier travail) ; ordre d'arrivée pour une même clé. Une clé qui arrive passe donc
  avant une clé qui inonde le service (au plus une libération, derrière les seules clés arrivées avant elle), et
  des clés qui renvoient sans cesse une requête n'en affament aucune autre. Une requête synchrone dont le client
  part quitte la file, ou son travailleur est tué.
- **Envois hors bande** (`server/store.py`) : jeton et identifiant de résultat de 256 bits (le second dérivé du
  premier par HMAC sous une clé en mémoire), gardés en empreintes, jeton à usage unique ; liés en plus à la clé si
  l'envoi en vient (mode public : la capacité seule). Quotas : en attente, 40 par préfixe du créateur et 10 000 en
  tout ; reçus non lus, 10 par client du PUT et 40 par son préfixe ; caractères, 1/8 du dépôt par client du PUT et
  1/4 par préfixe (le PUT part de la machine de l'utilisateur, pas d'un connecteur partagé). Une URL d'envoi vaut
  `GDPRGUARDIAN_UPLOAD_TTL_S` ; un envoi reçu n'expire
  pas tant qu'il attend son travailleur (sa requête le termine, résultat ou échec) et son délai de traitement part
  de l'attribution du travailleur ; chaque lecture repousse l'expiration à `GDPRGUARDIAN_RESULT_TTL_S`, jamais
  au-delà de 3 durées depuis la publication du résultat (`store.MAX_LIFE_TTLS`, 30 minutes par défaut) ; une fois
  tout lu (ou l'échec signalé), le résultat reste relisible 120 s (`store.READ_GRACE_S`, réponse perdue), puis il
  est effacé. Erreurs distinctes, toujours 404 : `already_read`, `expired`, `deleted` (empreinte et motif fermé
  gardés une heure, au plus 50 000 ; seul le détenteur de la capacité de 256 bits les apprend), `not_found` sinon ;
  une URL d'envoi rejouée répond `upload_used` à son détenteur (demander une nouvelle URL), une fausse ou celle d'une
  autre clé `not_found`. Sur `/mcp`, un refus de la porte (429, 503, 408, 413) part en erreur JSON-RPC sous HTTP 200
  (`data.code`, `data.retry_after_s`, `Retry-After` gardé) : un client MCP ne lit pas le corps d'un 4xx/5xx.
- **Gros documents sans blocage** (motif des tâches MCP, SEP-1686, fait avec de simples outils pour tous les
  clients) : le `PUT` répond `202 Accepted` dès le corps reçu (`UploadAcceptedOut` : étape `queued`,
  `retry_after_s`) ; le traitement continue **dans la même requête ASGI**, après la réponse (tâche de fond
  Starlette) : même travailleur isolé, même budget mémoire, même ticket du limiteur, mêmes échéances, la requête
  n'étant pas annulée par le départ du client. La lecture du résultat (`get_anonymized`, `GET /v1/results/…` en
  202) rend l'étape (`awaiting_upload`, `queued`, `converting`, `anonymising`, `done`, `failed`), les pages faites
  et le total quand le convertisseur les connaît (PDF), sinon une estimation sur la taille, le pourcentage, le
  temps écoulé et `retry_after_s`. L'avancement vient du travailleur par des trames `progress` du protocole
  (`_sandbox.report_progress` : étapes fermées, entiers bornés, 4 096 trames au plus, une toutes les 0,5 s ; forme
  vérifiée par le parent, sinon le travailleur est tenu pour défaillant). Le MCP local attend 20 s, puis rend
  l'avancement de la même façon. Sur `/mcp` et `POST /v1/uploads`, le délestage sur l'attente estimée est reporté
  au moment où l'appel prend vraiment un travailleur (`Ticket.deferred_shed`, `Limiter.shed_wait`) : suivre un envoi
  en cours n'est jamais refusé parce que le même client occupe un travailleur.
- **Qualité minimale du texte** (`server/quality.py`, dans le travailleur, sur un échantillon borné du texte
  converti) : part des mots en minuscules absents des listes du paquet et porteurs d'un 4-gramme de lettres jamais
  vu, mots d'une ou deux lettres hors mots-outils, jetons mêlant chiffres et lettres, césures cassées. Seuil 0,12,
  étalonné sur les moitiés « dev » des corpus et vérifié sur les moitiés « test » : aucune fausse alerte sur
  ParlaMint, Judilibre, MAPA et TAB, 0 à 0,1 % sur BODACC et BOAMP ; presse ancienne signalée pour ses pages les plus
  dégradées (Europeana 12 à 13 %, HIPE 1,5 à 7 %). Français et anglais seulement. Jamais un refus :
  l'avertissement va dans `report.warnings`. PDF seulement (le produit ne fait pas d'OCR : un texte d'OCR n'arrive
  que par la couche texte d'un PDF), jamais un texte collé ni un document bureautique ; l'écriture informatique
  propre (codes en capitales et chiffres, noms de produits en casse chameau, sigles de deux capitales) n'est pas
  comptée comme déformée.
- **Travailleur victime préférée du tueur OOM** (`oom_score_adj` 1000, début de `_sandbox._serve`) : une saturation
  de la mémoire du conteneur coûte une requête, jamais le service.
- Mesures (16 cœurs, Linux, concurrence 4 sauf mention) :
  - texte de 2 Ko de bout en bout : p50 5,2 ms, p95 6,6 ms, p99 8,6 ms ;
  - débit soutenu : 160 à 260 textes de 2 Ko par seconde à concurrence 8, limité par le processus d'accueil HTTP
    (les travailleurs seuls en traitent environ 400) ;
  - 8 textes de 10 Mo simultanés : 6,5 s (4,5 s à concurrence 8) ;
  - 100 PDF de 10 Mo simultanés : tous traités en 8,7 s ; 100 fichiers mixtes de 10 Mo (DOCX, PDF, XLSX, texte)
    à concurrence 8 : tous traités en 34,8 s, pic de mémoire de 4,1 Go ;
  - au repos : environ 390 Mo de mémoire, prêt en 2 s.

## 6-8 (English). Rust core, parity contract, isolated service

**Rust core.** An optional accelerator (PyO3 0.30, `abi3` from Python 3.11, built by maturin). Each Python class
delegates to its Rust twin when the core is installed and `Settings.native` is true; `GDPRGUARDIAN_PURE_PYTHON=1` or
`Settings(native=False)` keep the Python engine alone, which stays the reference and always works without the
core. Modules (see the table above): `unicode.rs` (the core's single Unicode table, built from Python's own
predicates, astral planes loaded once on first use), `prepare.rs` + `text.rs` (normalisation, folding, offsets,
language), `keywords.rs`, `pattern/` (exact compilation of `re`'s syntax tree: Python's `\w`/`\d`/`\s`,
`re.IGNORECASE`, leading and trailing look-arounds rewritten without backtracking, bounded compile budget),
`scanner.rs` + `windows.rs` (pack patterns and organisation rules on a linear-time engine, searched only in
candidate windows), `validators/` (87 checksums of every pack, Python `str` semantics), `names/` (persons),
`detectors/` (addresses, organisation candidates, e-mail, IBAN, MRZ, NIR birth dates), `finalize/` (resolution,
propagation, rendering, report, irreversible scope), `engine/` (the fused engine: one document in two calls,
spans kept in Rust end to end; Python only runs detectors without a twin, such as `phonenumbers` phones, NER and
added detectors, plus, on decomposed text, the three NFC-view detectors), `tabular/` (xlsx reader: strict ZIP,
streamed XML, bomb limits; anything non-canonical goes back to python-calamine), `lib.rs`. Rules: safe Rust, no
panic on any input (the panic hook only prints a fixed label), bounded memory, GIL released for heavy work,
Python code-point positions; a single source of truth (every list, lexicon and Unicode table comes from Python at
construction, including the classes and case rules of pack patterns and organisation rules); version contract
(`CONTRACT` in the core and in `_native`: a core of another version is set aside at import, with a warning, and
the Python engine answers; `Settings(native=False)` never touches the core); organisation rules received by the
service compile on one thread under 2 MiB per automaton and 16 MiB per rule set, refused with their reason
before allocating; outside the native
domain a call returns `None` and the Python reference takes over; threads only to compile patterns, scoped,
joined, falling back to the current thread (service workers may not create threads and the zygote must stay
single-threaded when it forks); keyed BLAKE2b scope with an OS-drawn key wiped on close. Release builds use
fat LTO, one codegen unit and the baseline x86-64 instruction set; the Docker image also applies profile-guided
optimisation by default (`tools/pgo.py`; `--build-arg PGO=0` for a bit-reproducible wheel): 10-12% less time on
the whole engine with the corpus, 2-5.5% on held-out texts. Measured on the 1,000-document corpus (1.9 KB on
average, one core): 0.45 ms per document on Windows (4.2 MB/s) and 0.48 ms on Linux, against 3.9 and 3.7 ms for
the Python engine alone; a 10 MB text in 2 s.

**Parity contract.** A Rust path gives an **identical** result: same spans (start, end, entity, label, source,
value, score rounded to 9 decimals, priority, personal, forms, propagate), same text, same report (explain
included). Proof: differential tests over the 1,000-document corpus, the existing suites and Hypothesis fuzzing
with adversarial Unicode (files listed above); drift guards in `tests/test_native_contracts.py`, where every
hand-copied Python target records its source fingerprint (syntax tree without comments or docstrings) and its
Rust twin, so editing the Python side alone fails with the target, the twin to update and the differential
tests to rerun; the same file checks that cited twins exist, that constants copied into Rust equal their Python
sources, and, with the core, that every twin builds (no silent fallback) and every native validator has a
contract. Procedure: change the Python reference, port it to the twin, rerun the differential tests, then
`python tests/test_native_contracts.py` prints the fingerprint table to paste. Patterns: every built-in pattern
is compared with `re` on trap texts, and so are random patterns (Perl classes, `(?i)` with "İ", "ı", "ſ", "K",
assertions); a pattern the compiler cannot render exactly is refused with its reason and stays with Python (one
of the 149 pack patterns: `NL_POSTCODE_LABELED`, a look-behind after a lazy repetition).

**Service: one request, one process.** The front process only does HTTP, admission, scheduling and the result
store; it never reads, anonymises or compiles content. Organisation rules only get a structural check there;
their patterns are compiled in the worker, which returns a closed code (`invalid_rules`, 422 `invalid_request`
with the rule number and the engine's reason, never content). Right after reading its configuration the front
removes every `GDPRGUARDIAN_*` variable from its environment, API keys included (except the `GDPRGUARDIAN_PURE_PYTHON`
switch), before starting any child process. Every request is processed end to end in a single-use isolated worker. On Linux a hardened,
single-threaded zygote preloaded once forks every worker (copy-on-write); a reserve of primed pristine workers
waits for requests (`GDPRGUARDIAN_PREWARM_WORKERS`); Windows and macOS spawn (with a Job Object on Windows). Each
worker, before any document: standard streams to `/dev/null`, no `GDPRGUARDIAN_*` variable, non-dumpable, no core
dump, `RLIMIT_NPROC=0`, capped address space, `PR_SET_PDEATHSIG`, no inherited descriptor, killed at its
deadline; replies are bounded JSON plus raw UTF-8 text, never pickle; a result never exceeds 1/8 of the store
(413 from the worker, nothing sent). Admission reserves the declared body size before reading it, within
`GDPRGUARDIAN_QUEUE_MB`, then, when a worker is granted, twice the largest possible reply, brought down to the real
result until the response ends; the fairness key is a public client's network prefix, else its principal; a key
holding nothing is admitted whenever the request fits, a key beyond its fair share cannot take the reserve kept for
the others; exhausted budget: 503 with `Retry-After`. Every body must arrive within 15 s plus its size at 128 KiB/s,
else 408 and the connection is closed. Deadline: conversion timeout plus one second per 250 KB; exceeded, the worker is killed and the
client gets 422 `processing_timeout` (text) or 422 `conversion_timeout` (document). Fairness: a freed slot goes
to the waiting key holding the fewest slots, then to the one waiting the longest (since its arrival or the end
of its last job); FIFO within a key; a new key waits at most one release behind a flooding key (behind only the
keys that arrived before it), and keys that keep resending requests starve no other key. Out-of-band uploads:
single-use 256-bit token and 256-bit result id (derived from the token by HMAC under an in-memory key), both stored
as digests, also bound to the key when the upload came with one (public mode: the capability alone); quotas:
pending, 40 per creator prefix and 10,000 in all; received and unread, 10 per PUT client and 40 per its prefix;
characters, 1/8 of the store per PUT client and 1/4 per prefix (the PUT comes from the user's machine, not a shared
connector); a received upload never expires
while waiting for its worker, its processing delay starts when the worker is granted; each read pushes the expiry to
`GDPRGUARDIAN_RESULT_TTL_S`, never beyond 3 lifetimes from the result's publication (`store.MAX_LIFE_TTLS`, 30 minutes
by default); once fully read (or its failure told) the result stays readable for a 120 s grace period
(a lost answer), then it is wiped; distinct 404 codes `already_read`, `expired`, `deleted` (digest and closed reason
kept one hour, 50,000 at most, learnt only by the capability holder), else `not_found`; a replayed upload URL
answers `upload_used` to its holder (request a new URL), a wrong one or another key's `not_found`. On `/mcp`, a gate
refusal (429, 503, 408, 413) goes out as a JSON-RPC error over HTTP 200 (`data.code`, `data.retry_after_s`,
`Retry-After` kept): an MCP client does not read the body of a 4xx/5xx. Big documents never block
(the MCP Tasks pattern, SEP-1686, done with plain tools): the `PUT` answers `202 Accepted` once the body is in, and
processing continues within the same ASGI request after the answer (same worker isolation, memory budget, limiter
ticket and deadlines); reading the result returns the stage (`queued`, `converting`, `anonymising`, `done`,
`failed`), pages done / total when the converter knows them, else a size-based estimate, percent, elapsed time and
`retry_after_s`, from bounded, shape-checked `progress` frames of the worker protocol. Minimum text quality
(`server/quality.py`): a degraded-OCR score on a bounded sample of the converted text (French and English), threshold
0.12 calibrated on the dev halves of the corpora, never a refusal, a warning in `report.warnings`; PDFs only (the
product does no OCR, so OCR text only arrives as a PDF text layer), never pasted text or office documents, and clean
IT writing (upper-case codes with digits, camel-case product names, two-capital acronyms) is not counted as garbled. Workers are the OOM
killer's preferred victims (`oom_score_adj`
1000). **Keyed service** (`GDPRGUARDIAN_API_KEY_SHA256`, the official service): `Authorization: Bearer <key>`
required, one key per organisation, given as SHA-256 digests only; plaintext keys in the environment are refused;
public mode (`GDPRGUARDIAN_PUBLIC=1`, no key) remains for another deployment. An entry gate decides
before any body is read: the client address comes from the trusted header Nginx sets (`X-GG-Client`), removed from
the request at once and turned into an in-memory pseudonym (8 bytes of HMAC-SHA256 under a 32-byte secret renewed
every 24 h, previous one honoured 10 min; IPv4 /32 + /24, IPv6 /64 + /48), never stored, logged, sent or echoed;
without the header the request comes from the server itself (LOCAL, and with `GDPRGUARDIAN_LOCAL_TOKEN_SHA256` only
when it presents the local token in `X-GG-Local`, else the shared bucket, so a compromised worker reaching the socket
does not pass for it: exempt from client budgets, two jobs at most, never the reserved slot, datagrams
`"src":"protocol"`). A browser request from another page (`Sec-Fetch-Site` other than `same-origin` or `none`) gets
403 before anything is counted. The limiter (`server/limiter.py`, memory only): cheap bucket 10/s burst 30; cost
GCRA in worker-seconds (0.5 s/s, burst 20 s, debt down to the longest job's deadline, prefix tier ×2; estimate from
`Content-Length` times the observed slowness of the client or its prefix, 1 to 100; true-up with the measured time
when a worker was used, else the estimate stays due unless the service refused for capacity, 503); 3 content
requests in flight per client (1 running + 2 queued) and 12 per prefix (an upload processing after its 202 still
counts, but `/mcp` and upload creation only see it when the call takes a worker, their bodies in flight staying
capped at the gate, so polling is never refused because the client's uploads are processing), at most half of the
non-reserved slots
running per prefix; one slot reserved for requests estimated under 0.2 s; 503 when the estimated wait exceeds 10 s;
100,000 keys per tier with a Space-Saving-style overflow; 429/503 with jittered `Retry-After` and
`RateLimit`/`RateLimit-Policy`; enforce, dry-run (buckets only) and off modes; fail open, with an aggregate warning
at most once a minute; aggregate counters only (`/status`). No access or activity log in production
(`--log-level warning`): per-request and per-document events at DEBUG only. Legal basis of the transient address
processing: legitimate interest (GDPR art. 6(1)(f), recital 49) and art. 32. Result isolation: synchronous paths
store nothing; deferred results are reachable by capability only (always 404 for wrong, expired, used or read, the
reason told to the capability holder only; no listing route; constant-time comparison); `Cache-Control: no-store` everywhere. Details: `deploy/README.md`. Measurements (16 cores, Linux, concurrency 4 unless stated): a 2 KB text end to end
p50 5.2 ms, p95 6.6 ms, p99 8.6 ms; sustained 160-260 texts of 2 KB per second at concurrency 8, limited by the
HTTP front (workers alone handle about 400); 8 simultaneous 10 MB texts in 6.5 s (4.5 s at concurrency 8); 100
simultaneous 10 MB PDFs all processed in 8.7 s; 100 mixed 10 MB files (DOCX, PDF, XLSX, text) at concurrency 8
all processed in 34.8 s, 4.1 GB memory peak; idle, about 390 MB of memory, ready in 2 s.

**Big documents: limits** (published on the site and in `deploy/README.md`, "Big documents"; every refusal is a 413
whose message names the limit, `server/errors.py`): **50 MB per file** (50 MiB, `GDPRGUARDIAN_MAX_UPLOAD_MB`), every
format and path (site, REST, MCP), refused from the declared size when there is one (Nginx beyond `51m`, the service
beyond 50 MiB plus a 64 KiB multipart envelope, an out-of-band `PUT` without reading it), else while reading;
**1,000,000 characters per pasted text** (`/v1/anonymize/text`, `anonymize_text`; `GDPRGUARDIAN_MAX_TEXT_CHARS`);
**12,500,000 result characters per document**, 1/8 of `GDPRGUARDIAN_MAX_STORE_CHARS` (100 million on the official
service, `compose.yaml`; 25 million with the 200 million default): the worker measures the result and answers 413
`document_too_large` without sending it, and a converted text over twice the cap is refused at conversion, before
the engine (`isolation._CONVERTED_SLACK`); **10,000 pages or slides** per document (`GDPRGUARDIAN_MAX_PAGES`); HTML
(pages, HTML e-mails, mammoth's output): **1,000,000 tags, opening and closing**, counted before parsing (a lone "<"
in the text is not one; `convert/_html.MAX_TAGS`), and **256 nesting levels**, checked right after parsing
(`MAX_DEPTH`: markdownify recurses); Word: **100,000 paragraphs, table cells included**, and **1,000,000 XML
elements**, counted before mammoth in the document, its notes and its comments, whatever the namespace prefix
(`convert/_docx.MAX_PARAGRAPHS`, `MAX_ELEMENTS`); **processing deadline** 60 s plus 1 s per 250 KB received
(`isolation.deadline_s`, `GDPRGUARDIAN_CONVERSION_TIMEOUT_S`), 270 s for 50 MiB, also the converters' and
spreadsheets' inner deadline, after which the worker is killed (422); **body deadline** 15 s plus the size (declared,
else the route's cap) at 128 KiB/s (`ServerConfig.body_deadline_s`, `GDPRGUARDIAN_MIN_BODY_RATE_KIB`), about 415 s for
50 MiB, after which 408.

**Big documents: scheduling** (`server/admission.py`, `server/limiter.py`). Load shedding **simulates the queue slot
by slot** (`FairScheduler.estimated_wait`): running jobs end on their estimates (past it, a job is assumed to run as
long again as it already has, never past its deadline); the requests the fair order serves before the newcomer (its
own queue, then the head of every key holding fewer slots or waiting longer) each take the first slot they may take
(large ones outside the reserved slot, `max_running` per client), then the newcomer; beyond 64 requests ahead, the
rest counts for its average share. A usable slot free and nobody ahead: no wait. An estimated wait over 10 s
(`GDPRGUARDIAN_LIMIT_MAX_WAIT_S`): 503 `service_busy` with `Retry-After`. **Reserved slot**: one slot
(`GDPRGUARDIAN_LIMIT_RESERVED_SLOTS`, always leaving at least one slot open to all) kept for requests estimated under
0.2 s (`GDPRGUARDIAN_LIMIT_SMALL_S`), never taken by a large request or by the LOCAL principal, so a small text is
never shed because of big documents while it is free. **The 5 s rule**: a small job running past 5 s
(`admission._SMALL_OVERRUN_S`) from then on counts as large, for handing out slots and in the simulation: the
reserved capacity goes back to small requests as soon as another slot frees.

**Local command line and library: other defaults, on purpose and unchanged.** `gdprguardian anonymize` and
`documents.anonymize_document` take `DocumentOptions()`: 50 MiB per file, but **500 pages or slides** (`max_pages`)
and a **fixed 60 s conversion deadline** (`timeout_s`, without the second per 250 KB; the whole pipeline of a
spreadsheet, the conversion alone for other formats, whose anonymisation has no deadline), no result cap, no
refusal before the engine, and no one-million-character limit on a text (`gdprguardian anonymize -` reads the whole
standard input). The converters' limits (HTML tags and nesting, Word paragraphs and elements, spreadsheet cells and
parts) are the same everywhere. The service passes its own values (`DocumentOptions(max_pages=GDPRGUARDIAN_MAX_PAGES,
timeout_s=…)`, then each request's deadline as the inner deadline).
