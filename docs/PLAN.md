# Gardien RGPD : plan directeur

Version 0.2, 24/10/2026. Document de travail destiné à l'équipe projet.
Sources : recherche web vérifiée en contradictoire (41 agents, 15 axes et 5 angles morts), détaillée dans
[research/README.md](research/README.md). Les points marqués *(à vérifier)* n'ont pas pu être confirmés sur une source primaire.

> ### Décisions du 24/10/2026 (elles prévalent sur le reste du document)
>
> 1. **Anonymisation irréversible uniquement.** Balises cohérentes `[PERSONNE_1]`, `[PERSONNE_2]`… dans un
>    document, sans aucune table de correspondance : personne, nous compris, ne peut retrouver les noms.
>    Tout ce qui concerne la réversibilité, le coffre de correspondances, la réhydratation et la portée
>    « client » est abandonné (§2.3, §8, §11, §15, §17-6, §18).
> 2. **Surface prioritaire : MCP en ligne et skill Claude.** Claude envoie le document sans le lire (envoi
>    hors bande via une URL d'envoi à usage unique) et ne lit que le Markdown anonymisé renvoyé. Un hook
>    Claude Code bloque la lecture directe des documents bruts. L'API REST sert la même chaîne. Le proxy LLM
>    passe après, en anonymisation seule.
> 3. **Packaging** : un seul paquet `gdprguardian` avec des extras (`office`, `phone`, `ner`, `api`, `mcp`) au
>    lieu d'un monorepo multi-paquets ; contrats internes dans [ARCHITECTURE.md](ARCHITECTURE.md).
> 4. **Packs** décrits en TOML (bibliothèque standard, regex en chaînes littérales) plutôt qu'en YAML.
> 5. Projet R&D de Guillaume CLEMENT - Flow Line Intégration, fourni en l'état, sans responsabilité.
> 6. **Choix du pays** (remplace le §5.6 comme comportement par défaut) : comme Presidio, Google DLP,
>    Macie et Purview, on ne devine pas le pays par défaut.
>    - `countries=["FR"]` (**défaut**, ou pays par défaut du client sur le service) : robuste et prévisible.
>    - `countries="all"` : tous les packs ; identifiants à clé forte masqués partout, identifiants faibles
>      seulement avec leurs mots-clés locaux. Pour les documents d'origine inconnue.
>    - `countries="auto"` : **expérimental**, sur demande explicite ; pays déduit des preuves validées
>      (IBAN, téléphones E.164, domaines) et des mots-clés ; signalé dans le rapport.
>    - Le pack international (e-mail, IBAN, cartes, téléphones `+CC`, IP, secrets) tourne toujours.
> 7. **Noyau Rust optionnel** (`rust/`, paquet `gdprguardian-core`) pour le chemin critique (mots-clés,
>    motifs, clés de contrôle), sans GIL ; résultats identiques au moteur Python (tests différentiels).

---

## 0. En bref

1. **Produit** : une bibliothèque Python sous licence MIT (`gdprguardian-core`) et trois façons de l'utiliser : une **API REST**, un **proxy LLM** compatible OpenAI et Anthropic, et un **serveur MCP** (FastMCP 4). Aucun LLM dans la chaîne. Fonctionne sur CPU seul.
2. **Le MCP seul ne protège pas les échanges.** Quand un LLM appelle un outil MCP, c'est lui qui écrit les arguments : s'il passe le texte brut, il l'a déjà lu, et le fournisseur l'a déjà reçu. Le MCP sert donc aux **fichiers lus par le serveur** (chemin, envoi séparé). Pour les échanges avec le LLM, il faut un **proxy placé avant le fournisseur** ou un **appel REST fait par l'application** (§2).
3. **Détection en cascade, bon marché d'abord** : normalisation, puis mots de contexte, puis motifs et clés de contrôle (packs pays), puis listes de noms et déclencheurs (civilités, signatures), puis NER sur CPU **seulement si nécessaire**, enfin fusion, propagation à toutes les occurrences et regroupement des variantes d'un même nom (§4 à §7).
4. **Packs pays** versionnés (fichiers YAML et validateurs MIT écrits d'après les spécifications officielles) avec **trois niveaux de confiance** : clé forte, clé faible, pas de clé. L'appelant passe `countries=["FR"]` ou `"auto"`. En mode `auto`, le pays est **déduit d'indices** (mots-clés, IBAN, indicatif téléphonique, écriture, devise) et jamais de la seule langue (§5).
5. **Remplacement irréversible** par balises typées numérotées `[PERSONNE_1]`, cohérentes dans le document. La cohérence vient d'empreintes **BLAKE2b à clé éphémère** (l'idée de « clé qui change ») ; la clé est détruite après chaque document (§8).
6. **Documents** : conversion en Markdown, anonymisation, sortie en Markdown. Pas d'édition de document. Les dépendances lourdes (OCR, Docling) sont optionnelles (§9).
7. **Excel : oui dès la v1**, avec un **pipeline tabulaire dédié** : lecture avec calamine, typage des colonnes, sortie Markdown paginée. On ne modifie jamais le fichier d'origine (§10).
8. **Vocabulaire** : « anonymisation irréversible des identifiants » (aucune table de correspondance), toujours accompagnée de la mention du risque résiduel lié au contexte (lignes directrices CEPD 02/2026) (§13).
9. **Mise en ligne** : hébergeur européen non soumis au CLOUD Act, aucun contenu conservé, journaux sans contenu, documents de sous-traitance (art. 28) publiés (§13).
10. **Licences** : liste blanche, interdictions nominatives (PyMuPDF, modèles spaCy fr/es/it, python-stdnum à l'exécution, etc.), contrôle automatique en CI, registre des modèles avec la provenance de leurs données (§14).

---

## 1. Ce que la recherche corrige dans les documents de départ

| Affirmation de départ | Réalité (octobre 2026) | Conséquence pour le plan |
|---|---|---|
| FastMCP est le standard, sous MIT | FastMCP **4.1.3** (20/10/2026) est sous **Apache-2.0**, ce qui est compatible. La spécification MCP **2026-07-28** **supprime les sessions protocolaires** : tout état passe par des *handles* opaques créés par le serveur et liés à l'utilisateur authentifié. | Le coffre de correspondances (*vault*) est indexé par un handle `<sub>:<handle>`. Le handle n'est jamais une preuve d'authentification. |
| Presidio est le standard (MIT) | Toujours sous MIT, mais **déplacé chez `data-privacy-stack`** depuis juin 2026. spaCy est **obligatoire** et tourne à **chaque appel**. **Aucun reconnaisseur français** (NIR, SIREN et SIRET ne sont que des PR ou issues ouvertes). Son intégration GLiNER traite des blocs de 250 caractères les uns après les autres : 255 ms médian et 2,9 Gio mesurés par un tiers. | On écrit **notre propre moteur léger**, avec une **interface compatible Presidio** et une **façade REST compatible Presidio** pour rester branchable sur LiteLLM, Lasso, NeMo. On reprend leurs validateurs MIT (version ≥ 2.2.364). |
| NIR : la regex `[12]…` plus mod 97 donne « 100 % de précision » | La clé est juste, mais la regex est incomplète : chiffre de sexe **3/4/7/8**, mois **20-42, 50-99 et 13**, séparateurs **espace insécable, point, tiret**, `2a` en minuscules. Et « 100 % » est faux en général : **1 nombre aléatoire sur 10 passe Luhn**, et beaucoup d'identifiants n'ont pas de clé. | Trois niveaux de confiance, mots de contexte obligatoires pour les niveaux faibles, spécification corrigée au §5.5. |
| SIRET = Luhn | Sauf **La Poste** : un SIRET commençant par 356000000, hors siège 35600000000048, doit avoir une **somme de chiffres multiple de 5**. | Exception codée et testée. |
| Presidio fait primer la règle sur l'IA en cas de conflit | Son analyseur ne fusionne que les chevauchements **de même type**. Les conflits entre types différents sont laissés à l'anonymiseur. | Politique de fusion explicite (§4, étape 6). |
| GLiNER est l'état de l'art, avec des micro-latences | Sur des **PII françaises**, les modèles sous licence permissive font **24 à 49 de F1** (gliner_multi_pii-v1 : 48,9). Compter **60 à 250 ms par bloc** sur CPU. | Le NER **complète** la détection pour les noms, organisations et adresses. Le cœur reste algorithmique. |
| gliner-pii-edge, bi-encodeur 130× plus rapide | Ce sont des **encodeurs anglais**. Le bi-encodeur ne se justifie qu'au-delà d'environ 50 libellés ; nous en utilisons moins de 10. | Écartés pour le français. |
| INT8 ONNX : −75 % de mémoire et accélération massive | En **INT8 dynamique**, GLiNER a **perdu 18 points de rappel** (70,9 → 53,1). L'INT8 **sur les poids seuls** (MatMulNBits) préserve la qualité (162 décisions identiques sur 164) et réduit la mémoire (309 Mo contre 1,7 Go), mais **sans accélérer**. | Modèles en fp32, ou en int8 poids seuls après test de rappel. Jamais d'INT8 dynamique non testé. |
| fr_core_news_lg est sous LGPL-LR | Confirmé. De plus, es_core_news est sous **GPL-3.0** et it_core_news sous **CC-BY-NC-SA**. | Tous les trois sont interdits. |
| pdfminer.six pour caviarder les PDF | Hors périmètre, puisque la sortie est du Markdown. Pour extraire le texte, **pypdfium2** (Apache/BSD) est environ 50 fois plus rapide (0,1 s par document contre 5,3 s). **PyMuPDF est sous AGPL.** | pypdfium2 par défaut. PyMuPDF et pymupdf4llm interdits. |
| ARX via pyarxaas | **ARXaaS archivé** (11/2025), pyarxaas en alpha depuis 2020. | Pas de k-anonymat en v1. On propose des opérateurs de généralisation et un rapport du k minimal. |
| SHA-256(sel + donnée) | Il faut un **HMAC**. Un hash simple de téléphone ou de NIR se retrouve par force brute (CEPD 02/2026 §50). | HMAC uniquement en interne. **Aucun hash** dans le texte envoyé au LLM. |
| « Dictionnaire détruit par le ramasse-miettes : irréversibilité garantie, conformité absolue » | **Python ne peut pas effacer la mémoire de façon fiable** (documentation de *cryptography*). La sortie reste une **donnée personnelle** pour le client, qui garde l'original, et pour tout sous-traitant (CEPD 02/2026 §15). | On parle de **réduction du risque**. L'effacement est « au mieux » (pas de swap, pas de core dump, workers recyclés). |
| « Clé qui change constamment » | Oui pour un **document**. Dans une **conversation**, si la clé change à chaque tour, `[PERSONNE_1]` du tour 1 ne désigne plus la même personne au tour 2. | La clé vit le temps de la **portée** : requête, conversation (avec durée limitée) ou client. |
| LLM Guard, scrubadub… | LLM Guard **archivé** (07/2026). scrubadub figé depuis 2023. Guardrails detect_pii archivé. | On n'en dépend pas. On reprend seulement des idées. |

---

## 2. Point d'architecture n°1 : par où entre la donnée brute

### 2.1 Le problème

- **Outil MCP qui prend du texte en argument** : le modèle a lu ce texte avant d'appeler l'outil. Avec les connecteurs claude.ai, l'appel part même **depuis le cloud du fournisseur**. Un tel outil ne protège **rien** vis-à-vis du fournisseur.
- **Outil MCP qui prend un chemin de fichier** (serveur local, en stdio) : le serveur lit le fichier et ne renvoie au modèle que le Markdown anonymisé. Là, la protection est réelle.
- **Outil de réhydratation exposé au modèle** : à proscrire. Un document piégé pourrait demander au modèle de « restaurer » les données puis de les exfiltrer, par exemple via une image Markdown dont l'URL contient les valeurs.

### 2.2 Surfaces et canaux couverts

| Canal | API REST | Proxy LLM | MCP local (chemin) | MCP hébergé | Hooks client |
|---|---|---|---|---|---|
| Application maison qui appelle un LLM | ✅ | ✅ | – | – | – |
| Agent qui lit des fichiers locaux (Claude Code, VS Code) | – | ✅ (si `BASE_URL` modifiable) | ✅ | – | ✅ |
| Prompt saisi dans Claude Code | – | ✅ (`ANTHROPIC_BASE_URL`) | – | – | blocage seulement |
| Fichiers envoyés par API (en base64, Files API, code interpreter) | – | ✅ | – | – | – |
| Claude for Excel en mode « passerelle LLM » | – | ✅ | – | – | – |
| Fichier transmis à un MCP hébergé | – | – | – | ✅ via envoi hors bande (*URL elicitation*) | – |
| Envoi de fichiers sur chatgpt.com ou claude.ai | – | ❌ | – | – | v2 : extension navigateur, fragile |
| M365 Copilot dans Excel, Gemini dans Sheets | ❌ | ❌ | ❌ | ❌ | ❌ |

Conséquence : **le proxy est la surface principale pour les « échanges LLM »**. Le MCP local est la surface principale pour les **documents d'un poste de travail**. L'API REST est la surface principale pour les **intégrations applicatives**.

### 2.3 Règles fixes

- Pas d'outil `deanonymize` ou `rehydrate` appelable par le modèle. La réhydratation se fait **seulement** dans le proxy, dans le backend de l'appelant (REST, avec un jeton dédié) ou côté client.
- La table de correspondance n'apparaît jamais dans `content`, `structuredContent` ni `_meta`. La spécification recommande de doubler `structuredContent` en texte, donc il atteint le modèle.
- Si un outil `anonymize_text` existe, sa description dit explicitement que **le modèle a déjà vu le texte**. Cet outil sert seulement pour du texte produit par l'agent et destiné à un tiers.
- Le Markdown renvoyé est **nettoyé** (caractères invisibles, bidi et tags Unicode retirés, images et liens externes neutralisés) et **encadré comme contenu non fiable** (OWASP MCP06, LLM01).

---

## 3. Architecture cible

```
gdprguardian/                      (monorepo, workspace uv, Python ≥ 3.11 imposé par calamine 0.9 et ONNX Runtime 1.31)
├─ packages/
│  ├─ core/        gdprguardian-core     normalisation, détection, fusion, remplacement, coffre, rapport — aucun accès réseau
│  ├─ packs/       gdprguardian-packs    packs pays YAML, validateurs MIT, gazetteers compilés, lexiques d'en-têtes
│  ├─ convert/     gdprguardian-convert  documents → Markdown, pipeline tabulaire, exécuté en sous-processus isolé
│  ├─ ner/         gdprguardian-ner      [extra] ONNX Runtime + tokenizers, NER par jetons et décodage GLiNER, sans torch
│  ├─ api/         gdprguardian-api      REST /v1, façade compatible Presidio, endpoint de garde LiteLLM
│  ├─ proxy/       gdprguardian-proxy    compatible OpenAI (Chat/Responses), Anthropic (Messages), Azure
│  ├─ mcp/         gdprguardian-mcp      FastMCP 4 : stdio (fichiers locaux) et HTTP streamable (hébergé)
│  └─ eval/        gdprguardian-eval     [dev] générateurs synthétiques, adaptateurs de jeux de test, métriques
├─ data/           téléchargés au build et figés par hash : INSEE, COG, base La Poste, Wikidata, GeoNames
├─ models/         MODEL_LICENSES.yaml (licence des poids, données, LLM générateur éventuel, révision HF)
├─ docs/           PLAN.md, research/, THIRD_PARTY_NOTICES, DATA_ATTRIBUTION, docs RGPD
└─ deploy/         images Docker (CPU, sans torch), nsjail, Valkey optionnel
```

Principe : **chaque surface est une fine couche par-dessus `gdprguardian-core`**. Le cœur est déterministe, sans état par défaut, sans réseau, et testable hors ligne.

---

## 4. Le moteur de détection : une cascade conçue pour le CPU

| Étape | Rôle | Coût | Outils |
|---|---|---|---|
| 0. Normalisation | Copie de travail en NFKC « 1 pour 1 » avec **table de correspondance des positions** : séparateurs (U+00A0, U+202F, U+2009) unifiés, caractères de largeur nulle et tirets conditionnels retirés, ligatures dépliées, césures de fin de ligne recollées, homoglyphes repliés (UTS #39). **Neutralisation des balises déjà présentes** dans l'entrée. | µs | stdlib, données UTS #39 (licence Unicode) |
| 1. Contexte | **Un seul passage Aho-Corasick** sur les mots de contexte de tous les packs actifs et sur les déclencheurs (civilités, formules de politesse). Produit les indices de pays et les fenêtres de contexte. | µs-ms | `ahocorasick_rs` (Apache-2.0) ou `pyahocorasick` (BSD-3) |
| 2. Motifs et clés | Préfiltre multi-motifs, puis regex exacte sur les candidats, puis **validateur** (clé de contrôle, plages, dates) et **contrôle des bornes en code**. Les motifs n'utilisent pas de *lookaround*, ce qui les rend compatibles avec RE2 et Vectorscan. | ms | Vectorscan via `hyperscan` 0.9.1 (MIT/BSD, roues Windows incluses), RE2 ou `re` sur les candidats |
| 3. Heuristiques | Noms (listes de noms avec repère d'ambiguïté, civilités, salutations, blocs de signature, partie locale des e-mails), adresses (ancrage code postal + commune), organisations (formes juridiques), téléphones (`phonenumbers`), dates de naissance (avec contexte). | ms | INSEE, Wikidata, base La Poste, phonenumbers |
| 4. NER sur CPU, **à la demande** | Seulement si la politique demande PERSONNE, ORG ou ADRESSE, et seulement sur les phrases qui portent un signal (majuscule hors début de phrase, civilité, nom connu, mot-clé d'adresse). On saute le code, le JSON et les tableaux numériques. Les zones déjà détectées sont passées au modèle. | 40-250 ms par bloc | ONNX Runtime (§7) |
| 5. Fusion | Règle de priorité : **regex validée > NER > regex non validée**. Puis la portée la plus longue, puis le meilleur score. Le type retenu est celui de l'identifiant **englobant** (SIRET ⊃ SIREN, IBAN ⊃ RIB, TVA ⊃ SIREN). Si plusieurs pays valident sans contexte, on masque en `[IDENTIFIANT_n]` (le rappel prime). | µs | maison |
| 6. Propagation et coréférence | Chaque forme détectée est **recherchée partout** dans le document ou la session (idée reprise de la Cour de cassation). Les mentions d'une même personne sont **regroupées** sur le nom normalisé, avec prénom compatible et genre de civilité cohérent (« M. Dupont », « Jean Dupont », « J. Dupont », « DUPONT Jean »). Une mention du nom seul, ambiguë, reste au niveau du nom. | ms | Aho-Corasick |
| 7. Remplacement et rapport | Choix de l'opérateur par type et par politique, émission des balises, **rapport** : comptes par type et par niveau, pays retenus avec leurs raisons, risques résiduels, contenus écartés. | µs | maison |

Profils : **`fast`** (étapes 0 à 3, 5 à 7, sans NER), **`standard`** (NER à la demande), **`strict`** (rappel maximal : seuils bas, identifiants d'entreprise et de professionnels de santé masqués, signalement des catégories particulières).

---

## 5. Packs pays et mode `auto` (le cœur algorithmique)

### 5.1 Format d'un pack

```yaml
# packages/packs/fr/recognizers.yaml
pack: FR
version: "2026.10.0"            # versionné indépendamment du code ; dates d'effet par règle
languages: [fr]
macros:
  SEP: "[ .\\-\\x{00A0}\\x{202F}\\x{2009}]?"
recognizers:
  - id: FR_NIR                   # mêmes identifiants que les PR Presidio (FR_NIR, FR_SIREN, FR_SIRET…)
    canonical: NATIONAL_ID       # type canonique interne (anglais)
    labels: {fr: NIR, en: NIR, neutral: ID_NATIONAL}
    tier: A                      # A = clé forte : masquage sans contexte
    pattern: "[1-478](?:{SEP}\\d){4}{SEP}(?:\\d{SEP}\\d|2{SEP}[ABab])(?:{SEP}\\d){8}"
    boundary: alnum              # vérifié en code (motif sans lookaround)
    validator: fr.nir            # module MIT écrit d'après la spécification INSEE
    context:
      fr: ["sécurité sociale", "n° ss", "nss", "nir", "numéro insee", "carte vitale", "matricule ins"]
    context_window: {before_tokens: 8, after_tokens: 3}
    variants:
      - id: FR_NIR_SANS_CLE      # 13 chiffres : uniquement avec contexte ou en-tête de colonne
        pattern: "[1-478](?:{SEP}\\d){4}{SEP}(?:\\d{SEP}\\d|2{SEP}[ABab])(?:{SEP}\\d){6}"
        tier: C
    personal_data: always
    default_operator: replace
    vectors: vectors/fr_nir.yaml # exemples officiels et cas limites
headers:                         # lexique d'en-têtes pour les tableurs (amorcé depuis Wikidata, licence CC0)
  FR_NIR: ["nir", "n° ss", "no secu", "numéro de sécurité sociale", "nss", "matricule ins"]
  GIVEN_NAME: ["prénom", "prenom", "first name"]
policies:
  company_ids: {standard: keep_legal_persons, strict: replace}   # SIREN/SIRET : personnels seulement pour les EI
```

### 5.2 Niveaux de confiance

| Niveau | Définition | Décision |
|---|---|---|
| **A** | Clé forte et structure distinctive (NIR mod 97, n° fiscal SPI mod 511, TVA à clé numérique, IBAN mod 97-10, MRZ 7-3-1 à plusieurs clés, carte bancaire Luhn + IIN + longueur, préfixe CH 756 + EAN-13…) | Masquage sur simple validation |
| **B** | Clé faible (Luhn, mod 10, mod 11 : environ 10 % de faux positifs aléatoires) : SIREN, SIRET, RPPS, FINESS, BSN, NIF PT, AFM, NHS… | Il faut un **mot de contexte** dans la fenêtre, un **en-tête de colonne** ou un **a priori** au niveau du document |
| **C** | Pas de clé : CNI, passeport, NEPH, AGDREF, CAF, France Travail, plaques FNI, codes postaux… | **Contexte seulement** |
| **L** (indulgent) | La clé n'est plus garantie : CPR danois depuis 2007, kennitala islandaise depuis le 18/02/2026, Norvège après 2032, codes lituaniens en 9, MRZ issues d'OCR | La clé **augmente le score** mais ne **bloque** pas. La structure et la date servent de plancher. |

### 5.3 Pack `INTL`, toujours actif

Les éléments suivants sont sûrs partout, car ils ont une clé ou une structure distinctive : e-mail (y compris les formes obfusquées `[at]`, `arobase`), URL contenant des données personnelles, **IBAN de tous pays** (table de longueurs à jour du registre SWIFT), **cartes bancaires** (attention : UnionPay n'utilise pas toujours Luhn), **MRZ** ICAO 9303 (TD1/TD2/TD3 et le format 2×36 de l'ancienne CNI française), BTC (base58check, bech32 et bech32m), ETH EIP-55, IMEI, IPv4/IPv6/MAC validées, téléphones écrits en `+CC` ou `00CC` (`phonenumbers`, sans région par défaut), **secrets** (portage des règles gitleaks, sous MIT, avec préfiltre par mot-clé ; **jamais réhydratés**).

### 5.4 Pack `FR` (v1)

| Identifiant | Niveau | Validation | Remarques |
|---|---|---|---|
| NIR / INS (sécurité sociale) | A | 97 − (13 chiffres mod 97), avec 2A→19 et 2B→18 | Sexe 1/2/3/4/7/8, mois 01-13, 20-42 et 50-99, départements 97x et 99. Variante sans clé en niveau C. |
| N° fiscal SPI | A | 3 derniers chiffres = 10 premiers mod 511 ; premier chiffre 0-3 | Excel supprime le 0 initial |
| TVA intracommunautaire FR | A (clé numérique) / B (clé alphanumérique, mod 11) | (12 + 3 × (SIREN mod 97)) mod 97 | Numéros monégasques (000) valides |
| IBAN FR et clé RIB | A | ISO 13616 et 97 − ((89·banque + 15·guichet + 3·compte) mod 97), lettres converties | Comptes alphanumériques |
| MRZ (CNI, CNIe, passeport, titre de séjour) | A | 7-3-1 mod 10 sur chaque champ, plus mise en page fixe | On masque **tout le bloc**. Correspondance tolérante pour l'OCR. |
| SIREN, SIRET, RCS, EORI | B | Luhn, plus l'**exception La Poste** pour le SIRET | Politique « entreprises » (EI = donnée personnelle) |
| RPPS, FINESS, ADELI | B | Luhn (pour FINESS : substitution propre pour 2A/2B ; clé ADELI *à vérifier*) | Professionnel ou établissement : réglé par politique |
| CNI (12 caractères, ancien modèle ; 9 alphanumériques, CNIe) | C | aucune | L'ancien modèle reste valide jusqu'en 2036 environ |
| Passeport, permis (NEPH), AGDREF, RNA, NUMEN, INE | C (INE : B *à vérifier*) | aucune ou non officielle | Formats INE, ADELI, NIA *à vérifier* auprès de l'ANS et du MEN |
| N° allocataire CAF, identifiant France Travail | C | aucune | Formats *à vérifier* |
| Plaques SIV / FNI | C (SIV plutôt distinctif) | lettres sans I, O, U ; « WW » accepté (plaques provisoires) | Contexte « immatriculation, carte grise » |
| Téléphones (métropole, DOM, +33) | via `phonenumbers` | plages officielles | Le 0 initial disparaît dans Excel |
| Codes postaux, adresses, dates de naissance | quasi-identifiants | La Poste, COG | **Généralisation** proposée : code postal → département, date de naissance → année |
| N° client, contrat, dossier, IPP, PDL/PRM | C | aucune | Règle « libellé + valeur » : on masque la **valeur** seulement |

### 5.5 NIR : spécification corrigée (remplace l'extrait de la conversation)

```python
import re

SEP = "[ .\\-   ]"
NIR_CANDIDATE = re.compile(
    rf"[1-478](?:{SEP}?\d){{4}}{SEP}?(?:\d{SEP}?\d|2{SEP}?[ABab])(?:{SEP}?\d){{8}}"
)  # bornes (pas de lettre ni de chiffre autour) vérifiées dans le code

def valid_nir(raw: str) -> bool:
    s = re.sub(SEP, "", raw).upper()
    if len(s) != 15 or s[0] not in "123478":
        return False
    dept = s[5:7]
    body = s[:5] + {"2A": "19", "2B": "18"}.get(dept, dept) + s[7:13]
    if not (body.isdigit() and s[13:].isdigit()):
        return False
    return int(s[13:]) == 97 - int(body) % 97  # ni le mois ni le département ne sont vérifiés : la clé tranche
```

### 5.6 Le mode `auto`

1. **Niveau G0, toujours actif** : le pack `INTL`.
2. **Niveau G1, global avec pondération** : identifiants dont la structure est très distinctive (CN RIC, CURP et RFC mexicains, PAN indien, CPF et CNPJ brésiliens formatés, y compris le **CNPJ alphanumérique en vigueur depuis le 31/07/2026**, SSN américain formaté avec ses plages interdites).
3. **Niveau L, activé par pays** : les packs nationaux, activés si le pays est **déduit** ou **fourni** par l'appelant, ou **déverrouillés localement** par un mot de contexte (CURP, Aadhaar, TC Kimlik, NAS, RNOKPP…).
4. **Score de pays** : a priori du client + 3 × mots-clés trouvés + 3 × pays de l'IBAN validé + 3 × région du téléphone `+CC` + 2 × écriture (hébreu, kana, cyrillique…) + 1 × domaine national (ccTLD) + 1 × devise + 1 × format de code postal + 0,5 × langue détectée. On active les k meilleurs pays au-dessus d'un seuil, et **les raisons figurent dans le rapport**.
5. **La langue ne décide jamais seule** : le français désigne aussi bien FR que BE, CH, CA, MA, DZ, TN, SN, CI ou CM. Détection de langue : `py3langid` (BSD-3) limité aux langues des packs ; `lingua` (Apache-2.0, environ 170 Mo) en option ; fastText lid.176 (CC-BY-SA) **jamais embarqué**.
6. Appel : `countries="auto"` (par défaut, avec l'a priori du client), `["FR"]`, ou `["FR","BE"]`.

### 5.7 Ordre de déploiement des packs

1. **v1** : `INTL` et `FR` (avec DOM-TOM et Monaco).
2. **v1.x** : pays francophones voisins, `BE` (NISS mod 97, règle des naissances après 2000), `LU` (matricule Luhn + Verhoeff), `CH` (AVS 756), `MC`.
3. **v2** : `DE` (Steuer-ID avec la **règle officielle de répétition des chiffres** : 1 sur 270 au lieu de 1 sur 10), `ES`, `IT`, `NL`, `PT`, `AT`, `UK`, `IE`. Les validateurs Presidio pour le DE comportent des bugs (carte d'identité, passeport, Führerschein) : ils sont **réécrits**.
4. **v3** : pays nordiques, baltes et d'Europe centrale et orientale, plus un **reconnaisseur TVA UE unique** basé sur le préfixe (EL, XI, IM compris).
5. **Plus tard** : Maghreb et Afrique francophone (MRZ et contexte, formats non vérifiés), Amériques et Asie via G1.

### 5.8 Règles d'écriture des validateurs

- **Écriture indépendante** à partir des spécifications officielles. L'URL de la spécification figure dans chaque module, avec des exemples tirés des spécifications. Les algorithmes ne sont pas protégés par le droit d'auteur (directive 2009/24/CE art. 1(2), CJUE C-406/10). **Ne jamais copier le code de python-stdnum** (LGPL), y compris en le « réécrivant » avec un LLM.
- python-stdnum, stdnum-js et django-localflavor servent d'**oracles différentiels en CI uniquement**, avec des listes d'exceptions pour leurs erreurs connues : kennitala IS 2026, règle NO 2032, codes LT en 9, registre IBAN v101 pour le BR, plages ITIN américaines.
- Tests par propriétés (Hypothesis, dépendance de développement uniquement) : tout identifiant valide généré est accepté, la modification d'un seul chiffre est rejetée, les séparateurs n'ont pas d'effet.
- **Dates d'effet** par règle (FI 2023, LV « 32 » depuis 2017, IS 2026, NO 2032, BR 2026) et **surveillance des changements** de formats.

---

## 6. Noms, adresses et organisations sans LLM

- **Listes de noms** :
  - INSEE *Fichier des prénoms* 1900-2025 (Licence Ouverte 2.0, avec la répartition par sexe) ;
  - INSEE *Fichier des noms* (218 982 noms, édition 2018) ;
  - fréquences de noms **agrégées** tirées du fichier des décès (jamais les fiches elles-mêmes) ;
  - Wikidata (CC0), y compris les lexèmes pour repérer les noms qui sont aussi des mots courants ;
  - SSA américaine (CC0), ISTAT et INE (CC BY 4.0).
  - Chaque pack est compilé en automate avec, par nom, sa fréquence, son sexe et un repère d'ambiguïté.
- **Deux catégories de noms** :
  - non ambigus : masqués dès qu'ils portent une majuscule hors début de phrase ;
  - ambigus (Pierre, Rose, Blanc, Martin, Marine, France, Nancy, Avril…) : masqués seulement avec un **déclencheur** (civilité, salutation, bloc de signature, partie locale d'un e-mail, nom voisin) ou par **propagation** depuis une mention confirmée.
- **Adresses FR** : ancrage sur le **code postal suivi de la commune**, couple validé dans la base officielle La Poste (Licence Ouverte 2.0). On étend ensuite vers la gauche : numéro, bis/ter, type de voie (lexique issu de la BAN), nom de voie. On gère aussi BP, CS, TSA et CEDEX. Pour les autres pays : formats de codes postaux GeoNames (CC BY 4.0) et lexiques de voies (-straße, Via, C/…). **libpostal est exclu** : il analyse une adresse déjà repérée sans en trouver dans un texte libre, pèse environ 2 Go, et ses données ont une provenance ODbL ambiguë.
- **Organisations** : forme juridique (SAS, SARL, GmbH, S.p.A., B.V., Ltd…), SIREN à proximité. **Une raison sociale qui contient un nom de personne est masquée** (règle « physicomorale » de la Cour de cassation).
- **Catégories particulières (art. 9 et 10)** : simple **signalement de risque**, avec lexiques BDPM, Wikidata (maladies, religions, partis), syndicats et termes pénaux, et masquage optionnel de la phrase. **Jamais présenté comme exhaustif** : la CJUE retient aussi les révélations indirectes (C-184/20, C-21/23). Ne pas embarquer les libellés de la CIM-10 (CC BY-ND) ni le MeSH Inserm (CC BY-NC).

---

## 7. NER sur CPU (optionnel et déclenché à la demande)

| Usage | Modèle | Licence (poids / données) | Note |
|---|---|---|---|
| FR rapide | `cmarkea/distilcamembert-base-ner` | MIT / WikiNER CC BY 4.0 | 67,5 M paramètres, environ 43 ms par appel sur portable. Le `model_quantized.onnx` fourni doit passer un **test de rappel**, sinon on le requantifie sur les poids seuls. |
| FR précis | `Jean-Baptiste/camembert-ner` | MIT / WikiNER | F1 0,948 sur les personnes |
| Multilingue | `urchade/gliner_multi_pii-v1` | Apache-2.0 / données **générées par Mistral** | 48,9 de F1 en PII français, max_len 384 mots. Version int8 poids seuls **reconstruite par nos soins** (environ 300 Mo). |
| À évaluer | `DataikuNLP/kiji-pii-model` | Apache-2.0 / données générées par LLM | 6 langues dont le français, aucun F1 publié |
| Après validation juridique | GLiNER2-PII (fastino), gliner-x | Apache-2.0 / données **GPT-5.4 et GPT-4o** | Meilleur rappel (SPY 0,477) mais précision de 0,35 |
| **Exclus** | OpenMed FR PII, piiranha, nvidia/gliner-pii, gliner-stream (Qwen), openai/privacy-filter, Flair, spaCy fr | NC, ND, licence propriétaire, ou dérivé d'un LLM | — |

- **Libellés** : 4 à 8 au maximum (personne, organisation, adresse, ville, éventuellement date de naissance). Les identifiants structurés restent aux regex.
- **Exécution** : ONNX Runtime 1.31 avec `tokenizers`, **sans torch**. La bibliothèque `gliner` impose torch, donc on écrit un **petit décodeur ONNX maison** inspiré de gline-rs (Apache-2.0). Fenêtres alignées sur les phrases d'environ 300 mots, chevauchement de 40 à 60 mots, micro-lots, seuils par libellé (0,3 à 0,5 pour les personnes), liste d'exclusion (pronoms, noms communs). **On ne compte jamais sur la troncature de GLiNER**, qui est silencieuse.
- **Plus tard** : un **modèle PII français maison** entraîné **sans données issues de LLM** (gabarits Faker, identifiants générés par nos validateurs, WikiNER, noms INSEE), affiné à partir de CamemBERTav2 ou mmBERT-small, publié sous Apache-2.0 avec sa fiche de données.

---

## 8. Remplacement irréversible et clé éphémère

> **Décision du 24/10/2026** : Gardien RGPD est **exclusivement irréversible**. Aucune table de correspondance,
> aucun mode réversible, aucune réhydratation : ni le client, ni l'opérateur du service, ni l'IA ne peuvent
> retrouver les valeurs d'origine. Les sous-sections 8.2 (partie « réversible »), 8.3 (`encrypt_det`, FF1)
> et 8.4 ci-dessous sont **abandonnées** et conservées seulement comme trace de l'analyse.
>
> Mise en œuvre retenue (`src/gdprguardian/scope.py`) : une `Scope` par document ; clé aléatoire de 256 bits ;
> empreintes **BLAKE2b à clé** (`digest -> numéro`, rien d'autre) ; coréférence des personnes par empreintes
> du nom et du prénom ; clé effacée à la fermeture. Deux documents sont traités avec deux clés
> indépendantes : on ne peut pas les recouper.

### 8.1 Syntaxe des balises

`\[([A-Z][A-Z0-9_]*[A-Z0-9])_([1-9][0-9]{0,6})\]`, par exemple `[PERSONNE_1]`, `[ORG_2]`, `[ADRESSE_1]`, `[EMAIL_1]`, `[TEL_1]`, `[IBAN_1]`, `[NIR_1]`, `[DATE_NAISSANCE_1]`.

- **Crochets, jamais de chevrons** : en CommonMark, `<PERSON>` est une balise HTML que les moteurs de rendu font disparaître.
- Type canonique en anglais en interne. **Libellé dans la langue du pack**. Option `labels=neutral` pour éviter qu'un libellé ne trahisse la nationalité (`[ID_NATIONAL_1]` plutôt que `[PESEL_1]`).
- Les civilités (M., Mme) restent **en dehors** de la zone remplacée, pour préserver les accords en français.

### 8.2 La clé éphémère (ton idée, dans sa forme sûre)

- À chaque portée : `K = secrets.token_bytes(32)`, puis `index_interne = HMAC-SHA256(K, type ‖ 0x00 ‖ normaliser(valeur))`. La normalisation comprend NFKC, la casse, les espaces et, pour les identifiants, la suppression des séparateurs.
- En mode **irréversible**, on ne stocke que `digest → n` : **aucun texte en clair**. En mode **réversible**, on ajoute `n → original`.
- **Portées** :

| Portée | Usage par défaut | Durée de vie | Remarque |
|---|---|---|---|
| Requête | documents, MCP, REST sans option | la réponse | Rien n'est stocké |
| Conversation | proxy de chat | 30 min d'inactivité, 12 h au plus (configurable, ≤ 24 h) | Indispensable pour que `[PERSONNE_1]` reste cohérent d'un tour à l'autre |
| Client | sur option explicite, clé fournie par le client (BYOK) | durable | Rend les sessions **reliables entre elles** : à inscrire dans l'AIPD du client |

- **Où vit la correspondance réversible** : de préférence **chez l'appelant** (son backend en REST, ou le proxy s'il l'héberge lui-même). Si c'est nous qui hébergeons, on la garde en **RAM**, ou dans **Valkey** (BSD-3, jamais Redis 8 embarqué) **chiffrée en AES-GCM avec une clé fournie par le client à chaque requête**. Le serveur ne peut alors pas la lire au repos.
- **Honnêteté technique** : la remise à zéro du `bytearray` de la clé est faite au mieux. OpenSSL et HMAC copient la clé, et les `str` Python ne s'effacent pas. On le compense par : pas de swap, pas de core dump, recyclage périodique des workers, aucun journal de valeurs.

### 8.3 Opérateurs

| Opérateur | Défaut | Usage |
|---|---|---|
| `replace` (balise typée numérotée) | **oui** | Tous les identifiants directs |
| `generalize` | sur option | Date de naissance → année ou tranche, code postal → département (en passant par la table INSEE, à cause de la Corse et des DOM), montant → tranche |
| `date_shift` | sur option | Décalage aléatoire par portée, multiple de 7 jours |
| `mask` | affichage seulement | `**** 1234` |
| `redact` | sur option | Suppression pure |
| `hmac_token` | sur option | Jeton opaque à sens unique, 64 bits minimum |
| `surrogate` (Faker) | sur option, pour la rédaction | Valeurs fictives réservées (`example.com`, numéros non attribuables). **Jamais pour les identifiants nationaux.** Inconvénient : un nom oublié se fond alors dans les faux noms. |
| `encrypt_det` (AES-SIV) | sur option, portée client | Réversible sans coffre, mais révèle les égalités |
| FF1 (chiffrement préservant le format) | plus tard | NIST a retiré FF3. Domaine minimal ≥ 10⁶. Les clés de contrôle doivent être recalculées. |

### 8.4 Réhydratation (proxy et client uniquement)

- Analyseur tolérant : échappements Markdown (`\[PERSONNE\_1\]`), casse, séparateurs `_`, `-` ou espace, crochets alternatifs, **table fermée d'alias entre langues** (PERSONNE = PERSON = PERSONA). **Jamais de correspondance approximative sur les chiffres** : avec la distance de Levenshtein de LLM Guard, `[…_1]` et `[…_2]` peuvent être confondus.
- **Jamais** de réhydratation dans une URL, une source d'image, un lien ou un argument d'outil réseau (exfiltration de type EchoLeak, CVE-2025-32711).
- Pour le JSON et le CSV : **analyser, réhydrater les valeurs, puis resérialiser**, jamais un `str.replace` brut (c'est le défaut de LiteLLM et de LLM Guard). En flux continu (*streaming*) : mettre en mémoire tampon jusqu'au `]` qui ferme la balise.
- Une balise inconnue ou inventée par le LLM est laissée telle quelle et signalée. Les secrets ne sont jamais réhydratés.
- Le préambule « les crochets sont des pseudonymes » reste optionnel : son effet n'est pas démontré (Deußer et al., 2026).

---

## 9. Documents → Markdown (sur CPU, sans édition)

| Format | Installation de base (sans torch) | Points d'attention |
|---|---|---|
| PDF | `pypdfium2` (Apache/BSD) page par page, titres repérés par la taille de police ; `pypdf` (BSD) pour les **valeurs de formulaires** | Une page avec moins de 30 caractères et plus de 50 % d'image est **scannée** : OCR sur option, sinon signalée. Ne pas jeter le texte invisible (c'est la couche OCR des PDF déjà océrisés). Métadonnées Info/XMP **jamais** émises. |
| DOCX | `mammoth` (BSD-2) puis `markdownify` (MIT) ; `python-docx` (MIT) pour les en-têtes, pieds de page et commentaires | Modifications suivies affichées acceptées (le texte supprimé n'est pas émis). Commentaires sur option. Images remplacées par `[IMAGE: alt]`. core.xml, app.xml et custom.xml jamais émis. |
| PPTX | `python-pptx` (MIT) | Notes du présentateur incluses. Diapositives masquées : même politique que les feuilles masquées. |
| ODT, ODP / ODS | `odfdo` *(licence à vérifier)* / calamine | — |
| RTF | `striprtf` *(licence à vérifier)* | — |
| HTML | `beautifulsoup4` et `markdownify` | Suppression de script, style, iframe et meta. **Aucune ressource distante** chargée. Les href et src sont anonymisés. |
| EML / MSG | `email` (bibliothèque standard) / `python-oxmsg` (MIT) | En-têtes émis : From, To, Cc, Date, Subject seulement. Received, X-Originating-IP et DKIM supprimés. Pièces jointes listées (noms anonymisés). |
| TXT, MD, CSV | `charset-normalizer` (MIT) | Les CSV passent par le pipeline tabulaire (§10) |
| Extras | `[ocr]` Tesseract, RapidOCR ou OnnxTR ; `[quality]` Docling (torch, environ 3 s par page) | Désactivés par défaut |

- **Interdits** : PyMuPDF et pymupdf4llm (AGPL), marker (poids sous OpenRAIL-M et SDK de LLM), MinerU (licence spécifique), html2text (GPL), extract-msg (GPL), pandoc embarqué (GPL).
- **MarkItDown** (MIT) sert de source d'inspiration, mais pas de moteur : il émet les feuilles Excel masquées, ignore les commentaires et ne lit dans les MSG que From, To, Subject et le corps.
- **Tout** le Markdown est anonymisé, y compris les URL, les textes alternatifs et le **nom du fichier**.
- **Sécurité** : chaque analyse tourne dans un **sous-processus jetable** sans réseau (nsjail ou gVisor). Limites : RLIMIT_AS 1 à 2 Go, 60 s de CPU, pas d'écriture disque. Contrôle de l'archive ZIP avant analyse : au plus 2 000 entrées, 200 Mo décompressés et un ratio de 100 pour 1. `defusedxml`. Un fichier chiffré est refusé sauf si le mot de passe est fourni. pdfminer.six ≥ 20251230 s'il est utilisé (CVE-2025-64512 et CVE-2025-70559).

---

## 10. Excel et CSV : décision et conception

### 10.1 Décision

**On les traite dès la v1, toujours via une référence de fichier, avec un pipeline tabulaire dédié et une sortie Markdown, sans jamais modifier le fichier d'origine.**

- **Pourquoi** :
  - Ce sont les fichiers les plus denses en données personnelles (exports RH, CRM, paie).
  - Ce sont **les documents les plus envoyés à ChatGPT après les PDF** : environ 28 % des documents hors images selon Harmonic.
  - Les passerelles du marché ne traitent pas les fichiers. Les produits de dé-identification (Limina, Tonic, Skyflow) ont des lacunes documentées : commentaires laissés tels quels, rien sur les feuilles masquées.
- **Pourquoi pas la conversion générique en Markdown puis NER** : elle perd les types, émet les feuilles masquées et ne permet pas de **raisonner par colonne**, alors que c'est ce qui rend le traitement à la fois bon marché et fiable.

### 10.2 Pipeline

1. **Garde** : taille du fichier, taille décompressée, nombre d'entrées, refus des fichiers chiffrés. Exception : si le mot de passe est fourni, déchiffrement avec `msoffcrypto-tool` (MIT). Les fichiers protégés par MIP ou IRM sont refusés avec un message clair, et ce message **ne reprend pas** le `siteId` du locataire.
2. **Inventaire** du ZIP (OOXML) ou de l'OLE (xls) : commentaires et commentaires en fil (avec `persons.xml`), docProps, `custom.xml` (`MSIP_Label_*_SiteId` = identifiant de locataire Entra), `LabelInfo`, `pivotCacheRecords` (**copie complète des données sources**), liaisons externes, caches de graphiques, noms définis, en-têtes et pieds de page, VBA, objets incorporés, révisions, Power Query. **Rien de tout cela n'est émis en v1.** Tout est **listé dans le rapport**.
3. **Lecture** avec `python-calamine` (MIT ; xlsx, xlsm, xls, xlsb, ods). Valeurs **en cache** seulement : **aucune formule n'est évaluée** (pycel est sous GPL et a une CVE notée 9,8, formulas est sous EUPL). python-calamine 0.9.0 embarque encore calamine 0.36 : passer à la première version qui embarque calamine ≥ 0.37 (correctifs sur l'époque 1904 et sur les cellules de graphique dans les xls) et, d'ici là, détecter nous-mêmes le système de dates 1904. Fichiers CSV et TSV : `charset-normalizer` et `csv.Sniffer` (exports français en `;` et cp1252).
4. **Structure** : on utilise les **tableaux Excel nommés** (`load_tables`) quand ils existent. Sinon, composantes connexes avec les cellules fusionnées considérées comme pleines, détection de la ligne d'en-tête (y compris les en-têtes sur plusieurs lignes), **feuilles de type formulaire** clé-valeur, test de transposition, lignes de total et de notes. Selon TableSense et Auto-Tables, environ 2 tableaux par feuille et 30 à 50 % de tableaux non relationnels : le cas « un tableau propre en ligne 1 » est minoritaire.
5. **Remise en forme des valeurs** :
   - flottant entier → chaîne d'entier ;
   - zéros initiaux rétablis grâce au format de nombre ou à la longueur attendue pour l'en-tête ;
   - nombres de 16 chiffres ou plus finissant par 0 dans une colonne « carte » : considérés comme **tronqués** (Excel garde 15 chiffres significatifs) et masqués d'après l'en-tête ;
   - le **NIR, de 15 chiffres, est stocké exactement** : il suffit de le convertir correctement depuis le flottant ;
   - dates en numéro de série converties en tenant compte du **système 1904**.
6. **Typage des colonnes**, qui sert d'**a priori** :
   - **en-tête** comparé au lexique multilingue du pack (amorcé depuis Wikidata, CC0, puis complété à la main : DDN, N° SS, tél.) ;
   - **validateurs appliqués à toutes les cellules** qui ont la bonne forme, puis test binomial contre le taux de réussite dû au hasard (Luhn 0,10, mod 97 environ 0,01) : type accepté si p < 10⁻³ et si la borne basse de Wilson est ≥ 0,5. Exemples : 8 sur 20 pour Luhn, 3 sur 10 pour mod 97.
7. **Détection par cellule toujours active**, puisque les regex et validateurs coûtent peu. L'a priori de colonne **abaisse le seuil** du NER et permet d'accepter les formats sans clé. Le NER ne tourne que sur les **valeurs distinctes** des colonnes de texte libre, au format `"en-tête : valeur"`. Une colonne entière n'est masquée que si son type est un **identifiant direct établi avec une forte confiance**.
8. **Opérateurs par type de colonne** :

| Colonne | Défaut |
|---|---|
| Nom, prénom | `[PERSONNE_n]`. Prénom et nom d'une même ligne partagent le même n. |
| E-mail, téléphone, adresse | `[EMAIL_n]`, `[TEL_n]`, `[ADRESSE_n]`. La ville est conservée. |
| Identifiants nationaux, IBAN | `[NIR_n]`, `[IBAN_n]` |
| Identifiant numérique interne | **substitut entier par session**, partagé entre les feuilles, pour garder les jointures et le type numérique |
| Date de naissance | **année** (tranche sur option) |
| Autres dates, montants, catégories | conservés (`date_shift` ou tranches sur option) |
| Catégories particulières | signalées, masquage sur option |

9. **Une seule table de correspondance** pour toutes les feuilles et tous les fichiers de la session : un même client reçoit la même balise partout, et le LLM peut encore regrouper, compter et joindre.

### 10.3 Contrat de sortie

- **Réponse** :
  - un **bloc de résumé** : feuilles, tailles, comptes par type, éléments écartés ;
  - un **tableau GFM par feuille** avec une première colonne `#` qui donne le numéro de ligne Excel ;
  - le caractère `|` est échappé et les retours à la ligne sont remplacés par `<br>`.
- **Seuil d'envoi intégral : environ 40 000 caractères** (à calibrer sur des classeurs français). C'est en dessous de la limite de Claude Code (au-delà de 50 000 caractères, le résultat est enregistré dans un fichier ; alerte à 10 000 jetons) et de celle de claude.ai (environ 150 000 caractères, 240 s).
- **Au-delà du seuil** :
  - **schéma, profil et échantillon** : type de chaque colonne, taux de remplissage, entités détectées, action appliquée, statistiques sur les colonnes non identifiantes seulement, 20 lignes anonymisées ;
  - un **handle** pour lire la suite avec `read_rows(handle, cursor, max_chars, layout)` ;
  - le handle vit en RAM, est lié à l'utilisateur, expire après 15 min d'inactivité et 60 min au plus, et **ces durées figurent dans la description de l'outil**.
- **Feuilles larges** (plus de 20 colonnes) : affichage **en fiches** (« ### Ligne 17 », puis « colonne : valeur »). La précision s'effondre au-delà de 25 colonnes (MMTU).
- **Formats possibles** : `markdown` (par défaut), `csv` (le moins cher), `toon`, `json` (sortie structurée pour les programmes).
- **Export CSV** (option, v1.x) : UTF-8 avec BOM, **séparateur `;`** par défaut en français, et neutralisation des injections de formules (`= + - @ TAB CR LF` et leurs variantes pleine chasse).
- **Classeur reconstruit** (option, v2) : `XlsxWriter` avec `strings_to_formulas`, `strings_to_urls` et `strings_to_numbers` à False. Valeurs uniquement. Noms de feuilles génériques, auteur vide, date figée. Un test en CI vérifie qu'aucune autre partie que celles autorisées n'est présente. **Jamais de modification en place** et jamais openpyxl pour écrire.

### 10.4 Contenus masqués (recommandation à valider, §17)

| Élément | Recommandation | Raison |
|---|---|---|
| Feuilles masquées et très masquées | **Exclues par défaut**, avec un avis dans le rapport ; `include_hidden=true` pour les inclure | Minimisation : données oubliées (référentiel RH). La visibilité est connue pour tous les formats. |
| Lignes et colonnes masquées | **Incluses et anonymisées** | Les lignes filtrées sont des données attendues. Leur détection ne fonctionne que pour le xlsx, alors qu'une règle unique doit valoir pour tous les formats. |
| Commentaires et notes | Exclus par défaut ; sur option, émis **après anonymisation** | — |
| Formules | **Jamais évaluées.** Texte de formule sur option en v2 (PR #137 de python-calamine ou tokeniseur openpyxl), avec suppression des littéraux | — |

### 10.5 Hors v1

- Optimisation de k-anonymat (ARX demande une JVM et des hiérarchies). En v1, on propose les opérateurs de généralisation et un **rapport du k minimal** calculé avec `polars group_by` sur les quasi-identifiants déclarés.
- Couverture de M365 Copilot et de Gemini dans Sheets : impossible techniquement, et la documentation le dit.

---

## 11. Surfaces et contrats

### 11.1 API REST (surface principale pour les intégrations)

- `POST /v1/anonymize` reçoit du texte ou un fichier (multipart). Paramètres : `countries`, `profile`, `scope`, `reversible`, `labels`, `operators` et options tabulaires. Réponse : `{markdown|text, handle?, mapping?, report}`. `mapping` n'est renvoyé **qu'au backend appelant**, et seulement si `reversible=true`.
- `POST /v1/detect` renvoie le **rapport seul**, sans contenu, pour les audits.
- `POST /v1/rehydrate` exige un jeton à portée limitée et réservé au backend. Il n'est jamais exposé à un LLM.
- `GET /v1/packs` décrit les entités, les niveaux et les versions.
- **Façade compatible Presidio** (`/analyze`, `/anonymize`) : elle sert de remplaçant direct pour la garde PII de LiteLLM (`PRESIDIO_ANALYZER_API_BASE`), pour Lasso et pour NeMo.
- **Endpoint « Generic Guardrail » de LiteLLM.**

Exemple de rapport :

```json
{
  "countries": {"active": ["FR"], "reasons": ["context:numéro de sécurité sociale", "phone:+33", "iban:FR"]},
  "entities": {"PERSONNE": 12, "NIR": 1, "IBAN": 2, "EMAIL": 3},
  "tiers": {"A": 3, "B": 1, "C": 0},
  "ner": {"used": true, "model": "gliner_multi_pii-v1@<sha>", "chunks": 4},
  "residual_risk": ["dates_present", "job_titles", "special_category:health"],
  "dropped": {"hidden_sheets": 1, "comments": 4, "doc_properties": true},
  "timings_ms": {"convert": 35, "detect": 6, "ner": 120}
}
```

### 11.2 Proxy LLM (surface principale pour les échanges)

- **Formats** : OpenAI Chat et Responses, Anthropic Messages, Azure OpenAI. Le client reste en **BYOK** : il signe directement avec le fournisseur, et nous ne revendons pas d'accès aux LLM.
- **Ce qui est anonymisé** : les messages, les **prompts système** (y compris CLAUDE.md), les résultats d'outils et les arguments d'appels d'outils.
- **Ce qui est réhydraté** : la réponse en flux continu, avec tampon pour les balises coupées, et les **arguments d'outils** destinés aux outils locaux.
- **Cohérence entre tours** : une pré-passe remplace les valeurs déjà présentes dans le coffre. Comme la sortie est déterministe, le cache de prompt du fournisseur continue de fonctionner.
- **Fichiers** :
  - base64 en ligne : décodé, anonymisé, réencodé ;
  - Files API (multipart, chargements fragmentés) : identifiants de fichiers émis par le proxy, expiration côté fournisseur inférieure ou égale à la durée de vie de la correspondance ;
  - fichier transmis par URL : le proxy le récupère et l'intègre ;
  - xlsx : remplacé par un **CSV anonymisé** pour le code interpreter.
- **Claude for Excel en mode passerelle** :
  - exposer `/v1/messages` et `/v1/models` ;
  - envoyer les en-têtes CORS pour `https://pivot.claude.ai`, **y compris sur les erreurs** ;
  - anonymiser les `tool_result` (données des cellules) et réhydrater les `tool_use` (écriture dans les cellules).

### 11.3 Serveur MCP (FastMCP 4)

**Mode local (stdio, `uvx gdprguardian-mcp`)**, avec des répertoires autorisés déclarés dans la configuration (*Roots* est déprécié) :

- `anonymize_file(path, countries, profile, output)` renvoie le Markdown et le rapport ;
- `scan_file(path)` renvoie le rapport sans contenu ;
- `read_rows(handle, cursor, max_chars, layout)` et `release(handle)` pour les tableurs ;
- `anonymize_text(text, …)`, dont la description avertit que le modèle a déjà vu le texte ;
- une ressource `gdprguardian://packs/{pays}` (entités et niveaux) ;
- un prompt « analyse anonymisée » qui impose de passer par `anonymize_file`.

**Mode hébergé (HTTP streamable)** :

- OAuth 2.1 : OIDCProxy de FastMCP devant le fournisseur d'identité, avec CIMD. Le DCR utilisé par KeycloakAuthProvider est déprécié.
- Les entrées passent par `document_ref` : un **envoi hors bande** via *URL elicitation* (la spécification interdit les URL pré-authentifiées et impose de vérifier l'utilisateur), ou une URL https protégée contre le SSRF.
- Limitation de débit, *Tasks* pour les gros fichiers (si le client les déclare), progression à intervalles réguliers (elle remet à zéro le délai d'inactivité).

**Mode passerelle (plus tard)** :

- Un `ProxyProvider` FastMCP placé devant les autres serveurs MCP de l'entreprise, avec un middleware qui anonymise leurs résultats.
- **À tester d'abord** : la documentation dit que le proxy laisse passer les résultats tels quels.
- Suivre les intercepteurs SEP-2624. Fournir un adaptateur pour les intercepteurs HTTP de Docker MCP Gateway et un plugin Lasso.

### 11.4 Hooks client

Un plugin Claude Code :

- `PostToolUse.updatedToolOutput` anonymise les sorties de Read, Bash, WebFetch et des MCP. **Il faut tester la conformité de forme** : une sortie mal formée est ignorée silencieusement, et l'original fuit.
- `PreToolUse.updatedInput` réhydrate les arguments de Write et Edit.
- `UserPromptSubmit` sait seulement **bloquer** (avec `suppressOriginalPrompt`) et conseiller de passer par un fichier.
- Forcer le passage par la passerelle avec le réglage géré `allowedProviders` *(à vérifier)*.

---

## 12. Performance CPU et exploitation

- **Objectifs** (hypothèses à valider sur le matériel cible) :
  - chemin déterministe ≥ 1 Mo/s par vCPU ;
  - NER : 3 000 à 5 000 caractères/s par vCPU (encodeur à 6 couches, int8) et 1 500 à 2 500 en fp32 pour GLiNER ;
  - message de chat de 2 000 caractères : quelques ms sans NER, objectif p95 < 150 ms avec le NER à la demande.
- **Modèle de processus** :
  - une **session ONNX Runtime par conteneur**, partagée entre K threads (`run()` libère le GIL ; depuis la 1.31, la création de session aussi) ;
  - `intra_op_num_threads` à 1 ou 2, et `workers × threads ≤ vCPU` ;
  - `OMP_NUM_THREADS=1` ;
  - **aucune session créée avant un fork** : seuls les automates et les listes de noms sont préchargés, suivis de `gc.freeze()` ;
  - longueur de séquence plafonnée, et réduction de l'arène mémoire ONNX Runtime activée.
- **Regex** :
  - préfiltre Vectorscan, puis RE2 ou `re` sur les candidats ;
  - **les regex personnalisées des clients passent uniquement par RE2**, pour éviter le ReDoS ;
  - jamais Intel Hyperscan ≥ 5.5, qui est propriétaire.
- **phonenumbers** : `load_all()` au démarrage, `phonenumberslite`, une passe `+CC` puis une passe par région déduite. Ne pas reprendre les 8 régions par défaut de Presidio.
- **Démarrage à froid** : modèles intégrés à l'image, graphe ONNX optimisé hors ligne pour le CPU cible, préchauffage avant la sonde de disponibilité.
- **Rust / PyO3** : seulement si le profilage (py-spy) montre que la glue Python dépasse environ 20 % du CPU. gline-rs donne une indication d'environ 4 fois plus rapide. On ne réécrit jamais la couche HTTP ou MCP.
- **Protocole de mesure** : débit en caractères/s par cœur, latences p50, p95 et p99 sur 1 Ko, 10 Ko et 1 Mo, classeur de 100 000 cellules, démarrage à froid, RSS maximale, montée à 1, 4 et 16 requêtes simultanées. Le chemin regex seul et le chemin regex + NER sont mesurés **séparément**.

---

## 13. RGPD et mise en ligne

### 13.1 Vocabulaire (règle produit)

- Le produit réalise une **anonymisation irréversible des identifiants détectés** : aucune table de correspondance n'existe, ni chez le client ni chez l'opérateur (décision du 24/10/2026).
- Ne pas promettre « conforme RGPD » ni « données anonymes » au sens juridique sans analyse du contexte : le statut du texte dépend aussi des quasi-identifiants restants (CEPD 02/2026 §40 ; CNIL, exemple du CV dont seul le nom est remplacé).
- Joindre à chaque réponse un **avertissement de risque résiduel** (champ `notice` du rapport) : des éléments de contexte non détectés (rôles, dates, lieux, événements rares) peuvent subsister.
- Les noms « Gardien RGPD » et « GDPR Guardian » peuvent être lus comme une garantie de conformité ou une certification : ajouter une mention qui précise que ce n'est ni l'une ni l'autre.

### 13.2 Cadre juridique (octobre 2026)

- **CJUE C-413/23 P, CEPD c. CRU (04/09/2025)** :
  - des données pseudonymisées ne sont pas personnelles « dans tous les cas et pour toute personne » (§86) ;
  - elles le restent pour qui détient le moyen de ré-identification (§76) ;
  - elles peuvent ne pas l'être pour un destinataire qui n'a pas de moyen raisonnable de le faire (§77).
- **Lignes directrices CEPD 02/2026 sur l'anonymisation**, en consultation **jusqu'au 30/10/2026**. Trois critères : pas d'isolement, pas de liaison, pas d'inférence. Approche relative. Point important au **§15** : un **sous-traitant adopte la perspective du responsable de traitement**. Donc les données sont personnelles **pour nous** quand nous hébergeons, et **pour un fournisseur de LLM qui agit comme sous-traitant du client**. *Il est encore possible de déposer une contribution.*
- **Lignes directrices CEPD 01/2025 sur la pseudonymisation** : toujours à l'état de projet (v1).
- **Omnibus numérique** : en négociation. La position du Conseil est rapportée au 21/10/2026 et n'est pas vérifiée. **Aucun changement n'est applicable.**
- **AI Act** :
  - le modèle NER est probablement un « système d'IA », mais ni interdit, ni à haut risque, ni GPAI ;
  - exemption open source (art. 2(12)) ;
  - art. 4 (maîtrise de l'IA) modifié par l'Omnibus IA, règlement 2026/1744, *à vérifier* ;
  - fiches de modèle obligatoires dans notre organisation.

### 13.3 Rôles

| Configuration | Rôle de Gardien RGPD |
|---|---|
| Logiciel MIT auto-hébergé | Éditeur de logiciel, sans rôle RGPD |
| Service hébergé | **Sous-traitant (art. 28)** pour les contenus traités ; **responsable** pour les comptes, la facturation et les journaux de sécurité |
| Proxy | BYOK : le fournisseur de LLM est le destinataire ou le sous-traitant **du client** |

### 13.4 Mesures techniques du service hébergé

- **Traitement en RAM uniquement** : ni disque, ni swap, ni core dump, tampons limités à la requête, sous-processus de conversion jetables.
- **Journaux sans contenu**, et cette règle est publiée :
  - on enregistre seulement : locataire, horodatage, endpoint, tailles, comptes par type, pack, latence, versions de modèles, codes d'erreur ;
  - on n'enregistre jamais de valeurs ni de hash de valeurs ;
  - les traces d'erreur sont expurgées, et la journalisation des corps de requête est désactivée dans le reverse proxy, le WAF et l'APM ;
  - les adresses IP sont traitées comme des données personnelles ;
  - les journaux de sécurité sont conservés de 6 à 12 mois (CNIL, délibération 2021-122).
- **Hébergement** : hébergeur européen, **sans société mère ni présence aux États-Unis** (le CLOUD Act touche aussi les entreprises européennes présentes aux États-Unis), aucun CDN américain qui terminerait le TLS sur les contenus. Une offre **qualifiée SecNumCloud** pour le secteur public et les données sensibles (liste à jour sur cyber.gouv.fr *à vérifier*). On évite de dépendre du Data Privacy Framework, contre lequel un pourvoi est pendant.
- **Données de santé (HDS)** : on ne sait pas si un traitement sans stockage relève de l'activité 5. **Poser la question par écrit à l'ANS.** En attendant, les producteurs de soins sont orientés vers l'**édition auto-hébergée**. L'article R.1111-9-1 du CSP imposerait un stockage UE/EEE depuis le 26/09/2026 *(à vérifier sur Légifrance)*.
- **NIR** : rappeler que son usage est encadré (décret 2019-341, *à vérifier*). Le reconnaître dans un texte n'autorise pas à le traiter.

### 13.5 Documents à publier

1. Un **DPA** fondé sur les clauses types 2021/915 (annexes I, II, III).
2. La **liste des sous-traitants ultérieurs**, avec un préavis de 30 jours.
3. Un **livre blanc sécurité**.
4. Une **politique de confidentialité** (art. 13).
5. Un **site sans cookie** : aucun traceur, pas de police ni de CDN tiers.
6. Un **modèle de fiche de registre** et un **kit d'AIPD** pour les clients (gabarit AIPD du CEPD 2026).
7. Une **fiche des limites de détection** : couverture par pays, rappel et précision mesurés.
8. Un **runbook de violation de données** (gabarit CEPD 2026), avec un objectif contractuel de notification sous 24 à 48 h.

### 13.6 Organisation

- Un **DPO**, ou au minimum un référent : l'art. 37(1)(c) peut s'appliquer.
- Une **AIPD du service**, réalisée volontairement et publiée en synthèse.
- **ISO 27001** et/ou **ISO 27701:2025** (désormais certifiable seule), visées à 12-18 mois.
- Vérifier si NIS2 s'applique au fil de la croissance.
- **Les textes de la CNIL sont sous CC BY-ND** et la page OWASP sous CC BY-SA : on les cite, on ne les adapte pas dans la documentation MIT.

---

## 14. Licences et chaîne d'approvisionnement

**Base autorisée** (vérifiée) :

- runtime : `onnxruntime` (MIT), `tokenizers`, `fastmcp` (Apache-2.0), `mcp` (MIT), `pydantic` (MIT), `phonenumbers` (Apache-2.0), `pyahocorasick` (BSD-3), `ahocorasick_rs` (Apache-2.0), `hyperscan` (MIT, Vectorscan BSD), `google-re2` (BSD-3), `regex` (Apache-2.0), `iso3166` (MIT), `babel` (BSD-3 et CLDR), `py3langid` (BSD-3) ;
- conversion : `pypdfium2` (Apache/BSD), `pypdf` (BSD-3), `mammoth` (BSD-2), `python-docx`, `python-pptx`, `python-calamine`, `fastexcel`, `markdownify`, `beautifulsoup4`, `charset-normalizer`, `python-oxmsg`, `msoffcrypto-tool` (tous MIT), `defusedxml` (PSF), `cryptography` (Apache/BSD), `XlsxWriter` (BSD-2) ;
- tests et données : `Faker` (MIT), Valkey (BSD-3).

**Interdits nommément** : PyMuPDF, pymupdf4llm, marker (poids), MinerU, html2text, extract-msg, pycel, formulas, pyxlsb (LGPL-3), modèles spaCy fr, es et it, modèles Flair classiques, piiranha, OpenMed PII FR, jeux ai4privacy 200k à 500k, nvidia/gliner-pii, gliner-stream, TruffleHog (AGPL), Intel Hyperscan ≥ 5.5, extraits OSM et BANO (ODbL), modèle libpostal, Redis ≥ 7.4 embarqué, fastText lid.176 embarqué (CC-BY-SA), deduce, Textwash, `name-dataset` (issu de la fuite Facebook).

**À utiliser avec précaution** :

- python-stdnum (LGPL) : oracle en CI uniquement ;
- pycountry (LGPL-2.1-only) : remplacé par `iso3166` + `babel`, et attention à `schwifty`, qui l'importe ;
- `opencv-python-headless` (FFmpeg sous LGPL) via RapidOCR : notices obligatoires ;
- LibreOffice (MPL) : inutile grâce à calamine ;
- torch : **jamais à l'exécution**. Les roues Linux par défaut tirent des paquets `nvidia-*` propriétaires ; si besoin, utiliser l'index CPU.

**Mise en œuvre** :

- **`models/MODEL_LICENSES.yaml`** : pour chaque poids, la licence SPDX, le modèle de base, les jeux d'entraînement et leurs licences, le **LLM générateur éventuel** et la révision HF (SHA). La CI échoue si un champ manque. Les poids ne sont jamais dans la roue pip : ils sont téléchargés à la première utilisation, figés par hash et copiés sur un stockage européen. Seuls les formats safetensors et ONNX sont acceptés, sans `trust_remote_code`.
- **CI** :
  - `pip-licenses --from=all --partial-match --allow-only …` sur les extras réellement résolus ;
  - `reuse lint` (en-têtes SPDX) ;
  - **ScanCode** sur l'image Docker ;
  - génération de `THIRD_PARTY_NOTICES` et `DATA_ATTRIBUTION` (« Source : Insee » avec la date, GeoNames, WikiNER, BDPM) ;
  - **SBOM** ;
  - dépendances **épinglées par hash** (LiteLLM a été compromis sur PyPI le 24/03/2026).

---

## 15. Évaluation et qualité

- **Corpus principal FR** : un générateur maison de 10 000 à 50 000 documents (e-mails, comptes rendus, contrats, RH, tickets, factures, bulletins de paie, ordonnances, tableaux Markdown).
  - Base Faker fr_FR, plus des générateurs propres pour les cas limites : NIR (sexe 3/4/7/8, mois 20-42 et 50-99, 2A/2B, 97x, 99), SIRET La Poste, clé RIB. `company_vat()` de Faker est désormais valide.
  - **Noms et adresses tirés aussi de l'INSEE et de la BAN**, pour ne pas gonfler les scores en restant dans la distribution de Faker.
  - **Faux positifs volontaires** : montants, numéros de commande, « article L. 1234-5 ».
- **Jeux externes**, téléchargés au moment de l'évaluation et figés par hash : TAB (MIT, EN), MAPA `joelniklaus/mapa` (CC BY 4.0, FR petit), Gretel finance multilingue (Apache-2.0, 4 400 FR, étiquettes approximatives), FR-PII-Bench v0 (CC BY 4.0, 300 documents), Nemotron-PII (EN), Judilibre (LO 2.0), classeurs xlsx de data.gouv sous Licence Ouverte (structure seulement).
- **Jeu de contrôle privé** : au moins 300 documents réels ou consentis, annotés avec LABEL (MIT, Cour de cassation), **jamais utilisés pour le réglage**.
- **Métriques** :
  - **F2** orienté rappel ;
  - rappel par entité à la manière de TAB (une entité ne compte que si **toutes** ses mentions sont masquées) ;
  - **taux de fuite par document** ;
  - taux de sur-masquage ;
  - taux de masquage des leurres ;
  - résultats par type et par opérateur de perturbation.
- **Perturbations testées** : séparateurs (y compris U+00A0, U+202F, U+2009), sauts de ligne, `<br>` ou tiret conditionnel au milieu d'un identifiant, chiffres pleine chasse ou mathématiques, caractères de largeur nulle, contrôles bidi, homoglyphes cyrilliques ou grecs, confusions OCR (O/0, l/1, rn/m), e-mails obfusqués, « NOM Prénom », mélange français-anglais, identifiant coupé entre deux cellules.
- **Objectifs v1** (corpus synthétique ; entre crochets, avec perturbations) :

| Catégorie | Objectif |
|---|---|
| Identifiants à clé | rappel ≥ 0,995 [0,98], précision ≥ 0,98 |
| E-mail, téléphone, IP, URL | rappel ≥ 0,98 [0,95] |
| PERSONNE | rappel ≥ 0,93, F2 ≥ 0,90 (jeu privé : ≥ 0,90) |
| ADRESSE | rappel ≥ 0,85 |
| Fuite par document | ≤ 1 % (synthétique), ≤ 3 % (jeu privé) |
| Sur-masquage | ≤ 3 % |

- **Réhydratation** : aller-retour exact à 100 % (testé par propriétés). Aucune balise forgée ne doit être réhydratée à tort. La structure Markdown doit être conservée.
- **Niveaux de CI** :
  - sur chaque PR, en moins de 10 min : tests unitaires, tests par propriétés, fichiers de référence, perturbations, micro-évaluation sur 500 documents, et **blocage si le rappel d'un type baisse de plus de 0,5 point** ou si une fuite apparaît, plus un contrôle de performance relatif ;
  - **chaque nuit** : jeux complets, intervalles de confiance par bootstrap, historique asv.

---

## 16. Feuille de route

| Phase | Contenu | Critères de sortie |
|---|---|---|
| **0. Fondations** | Monorepo et CI (lint, tests, licences, SBOM, SPDX). Moteur de balises et portées HMAC. Schéma du rapport. Schéma et compilateur des packs. **Validateurs FR et INTL** avec tests par propriétés et oracles. Squelette d'évaluation et générateur FR v0. | 100 % des exemples officiels passent. Aller-retour exact. CI des licences au vert. |
| **1. MVP déterministe FR** | Normalisation avec table des positions. Étapes 0 à 3 et 5 à 7 de la cascade. Listes de noms et déclencheurs. Adresses FR. Propagation et coréférence. Convertisseurs de base dans le bac à sable. **REST** `/v1/anonymize` et `/v1/detect`. **MCP stdio** (`anonymize_file`, `scan_file`). Premières mesures CPU. | Objectifs atteints pour les identifiants à clé. Rappel PERSONNE mesuré (référence). Latences publiées. |
| **2. NER, Excel, auto** | Décodeur ONNX sans torch. distilcamembert et gliner_multi_pii-v1 (int8 poids seuls) avec **tests de rappel**. NER à la demande. **Pipeline tabulaire v1** et pagination par handle. **Mode auto**. Packs BE, LU, CH, MC. | PERSONNE ≥ 0,93 (synthétique). Suite de tests Excel au vert. Métriques du mode auto. |
| **3. Proxy et intégrations** | Proxy OpenAI, Anthropic et Azure. Réhydratation en flux continu et des appels d'outils. Fichiers (base64, Files API). Portée conversation. **Mode passerelle Claude for Excel.** Façade Presidio. Garde LiteLLM. Plugin Claude Code. | Tests de bout en bout sur les 3 formats. Aucune fuite sur le jeu de référence. |
| **4. Service en ligne UE** | Hébergement. OAuth 2.1. MCP hébergé avec `document_ref` et envoi hors bande. Limitation de débit. Durcissement du bac à sable. Observabilité sans contenu. **Documents RGPD.** Test d'intrusion. DPO. Packs DE, ES, IT, NL, PT, AT, UK, IE. | DPA publié. Test d'intrusion clos. AIPD du service publiée. |
| **5. Extensions** | Packs nordiques et d'Europe de l'Est. OCR. Option Docling. Exports CSV et xlsx reconstruit. Formules (tokeniseur et analyse de dépendances). **Modèle PII FR maison.** Extension navigateur (coller d'abord). Complément Office. Passerelle MCP. Cœur Rust si le profilage le justifie. | Selon la demande. |

---

## 17. Décisions à prendre (avec ma recommandation)

| # | Question | Recommandation |
|---|---|---|
| 1 | Accepte-t-on des poids NER entraînés sur des données **générées par un LLM** ? gliner_multi_pii-v1 l'est par Mistral ; le pipeline, lui, reste sans LLM. | **Oui, en le documentant**, pour Mistral (poids ouverts sous Apache) ; **non** pour les données issues de GPT, tant qu'aucun avis juridique ne l'autorise. Objectif : notre propre modèle « sans LLM » en phase 5. |
| 2 | Comportement par défaut pour Excel : feuilles masquées, lignes masquées, commentaires | Feuilles masquées **exclues avec avis**. Lignes et colonnes masquées **incluses et anonymisées**. Commentaires **sur option**. |
| 3 | Sorties CSV et xlsx en plus du Markdown | Markdown en v1. **CSV sur option en v1.x** (code interpreter). xlsx reconstruit en v2. Jamais d'édition en place. |
| 4 | SIREN et SIRET des personnes morales | **Conservés par défaut**, masqués si le contexte indique un EI ou une micro-entreprise, ou en profil `strict`. |
| 5 | Libellés précis (`[NIR_1]`) ou neutres (`[ID_NATIONAL_1]`) | **Précis par défaut**, utiles au LLM. Neutres en option pour le client. |
| 6 | Où vit la correspondance réversible du service hébergé | **Chiffrée avec une clé que le client fournit à chaque appel**. Valkey optionnel. Aucune clé conservée par nous. |
| 7 | Distribution : pip seul ou aussi des images Docker | Les deux. L'image implique de fournir les notices Apache et CC-BY : c'est automatisé en CI. |
| 8 | Santé et HDS | Exclu du service en ligne tant que l'ANS n'a pas répondu ; édition auto-hébergée en attendant. |
| 9 | Nom du produit | **Décidé le 25/10/2026** : « Gardien RGPD » en français, « GDPR Guardian » en anglais, un seul identifiant technique (`gdprguardian`), avec une mention « pas une certification » sur le site. |
| 10 | Contribuer à la consultation CEPD 02/2026 (jusqu'au 30/10/2026) | Optionnel, mais donne de la visibilité au projet. |

---

## 18. Risques principaux

- **Faux négatifs = fuites.** Atténuations : cascade orientée rappel, propagation, profil `strict`, rapport de risque résiduel, objectifs publiés. Il n'existe **aucune garantie** de couverture complète.
- **Affirmations juridiques excessives** : règle de vocabulaire (§13.1), fiche des limites de détection.
- **Le coffre de correspondances comme cible** : clé fournie par le client, durée de vie courte, handle lié à l'utilisateur, aucune sauvegarde.
- **Évolution des spécifications et des API** : MCP 2026-07-28 (prise en charge de la version 2025-11-25 pendant au moins 12 mois), API des fournisseurs, formats nationaux. D'où les packs versionnés et la veille.
- **Chaîne d'approvisionnement** : épinglage par hash, SBOM, ScanCode, modèles figés par SHA.
- **Dépendances peu maintenues** : openpyxl (aucune version depuis 06/2024), defusedxml (2021), gouvernance de Presidio en transition. Ces dépendances restent périphériques ou peuvent être remplacées.
- **Formats non vérifiés** (INE, ADELI, CAF, France Travail, passeport, NIA, EORI FR, Maghreb) : à confirmer auprès des sources officielles avant leur activation par défaut.

---

## Annexe : sources clés

- Spécification MCP 2026-07-28 (changelog) : https://modelcontextprotocol.io/specification/2026-07-28/changelog
- FastMCP : https://gofastmcp.com/updates
- Presidio (nouvelle maison) : https://github.com/data-privacy-stack/presidio
- CJUE C-413/23 P (analyse FPF) : https://fpf.org/blog/rethinking-personal-data-the-cjeus-contextual-turn-in-edps-vs-srb/
- Lignes directrices CEPD 02/2026 sur l'anonymisation : https://www.edpb.europa.eu/public-consultations/guidelines-022026-on-anonymisation_en
- Lignes directrices CEPD 01/2025 sur la pseudonymisation : https://www.edpb.europa.eu/our-work-tools/documents/public-consultations/2025/guidelines-012025-pseudonymisation_en
- CNIL, anonymisation : https://www.cnil.fr/fr/technologies/lanonymisation-de-donnees-personnelles
- INSEE, fichier des prénoms : https://www.insee.fr/fr/statistiques/8595130
- gliner_multi_pii-v1 : https://huggingface.co/urchade/gliner_multi_pii-v1
- distilcamembert-base-ner : https://huggingface.co/cmarkea/distilcamembert-base-ner
- python-calamine : https://pypi.org/project/python-calamine/
- Limites des sorties MCP dans Claude Code : https://code.claude.com/docs/en/mcp
- Claude for Excel via passerelle : https://claude.com/docs/office-agents/third-party-platforms
- Tous les autres liens, et le détail des vérifications : [research/](research/README.md)
