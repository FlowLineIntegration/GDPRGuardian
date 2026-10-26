<!-- Tests terrain du MCP en ligne, 26 octobre 2026 : six agents (trois Opus, trois Sonnet), environ 900 requêtes, documents entièrement fictifs. Moteur 1.0.0+0c3ff9fc1fb0. Field test of the online MCP, 26 October 2026: six agents, about 900 requests, fully fictitious documents. -->

# Gardien RGPD : verdict consolidé des tests terrain du MCP en ligne

Six testeurs ont travaillé sur des données fictives, chacun sous un angle différent :
- **Opus :** juridique/RH (opus-legal-hr), fichiers et envoi (opus-files-upload), expérience développeur MCP (opus-mcp-dx).
- **Sonnet :** médical/social (sonnet-medical-social), identifiants piégés (sonnet-identifiers-adversarial), multilingue (sonnet-multilingual).

Au total, environ 900 requêtes ont été envoyées une à une, d'après les comptes déclarés par chaque testeur. Aucune réponse 429 ou 503, aucun dépassement de délai.

**En bref.** Tout fonctionne de bout en bout, et vite : 35 à 46 ms par appel en médiane. Les identifiants directs français ne fuient presque jamais. **Note consolidée : 7/10.** Cinq points la retiennent :
- des identités fusionnées ou scindées quand un nom n'apparaît qu'en partie ;
- des dates d'événement transformées en dates de naissance ;
- le paramètre `countries`, qui laisse fuir facilement ;
- des identifiants sans format standard laissés en clair (matricule, RPPS, etc.) ;
- un contrat MCP qui peut faire perdre le résultat, ou le texte selon le client.

## 1. Est-ce que tout fonctionne ?

Oui. Les 4 outils répondent chez tous les testeurs qui les ont essayés. Rien n'est cassé, mais plusieurs points gênent.

| Outil | Verdict | Preuves | Ce qui casse ou gêne |
|---|---|---|---|
| `list_packs` | Oui (6 testeurs sur 6) | 11 packs : INTL toujours actif, plus BE, CH, DE, ES, FR, IT, LU, MC, NL et PT. Version 2026.10.0. Réponse en 0,15 à 0,17 s, médiane 32 ms. | Pas de pack GB : `FR,GB` est refusé. |
| `anonymize_text` | Oui (6 sur 6) | **Latence :** médiane 46 ms (p90 66 ms) chez legal-hr, 35 ms (p90 38 ms) chez mcp-dx, 30 à 170 ms chez les Sonnet. 18 000 caractères en 73 ms, 103 000 en 206 ms, 45 Ko en 0,19 s. **Comportement :** sortie déterministe ; les balises déjà présentes sont conservées. `profile`, `countries`, `label_language`, `rules` et `explain` fonctionnent tous. | `fast` donne une sortie identique à `standard` octet pour octet (3 testeurs). `strict` ne rattrape aucun oubli. Un texte vide renvoie un résultat vide sans erreur (3 testeurs). Le texte anonymisé est absent de `structuredContent`. |
| `create_upload` | Oui (5 sur 5) | **Délai :** 0,17 à 0,9 s (un cas à 3,3 s sous charge). **Commandes :** bash, PowerShell `curl.exe` et Python fonctionnent telles quelles. **URL d'envoi :** usage unique (réutilisée, elle répond 404), valable 5 min (envoi accepté à 290 s, 404 à 310 s), 50 Mo maximum (51 Mo donnent un 413 sans qu'aucun octet parte avec curl), POST refusé en 405. Le format est détecté à partir des octets. | **Validation tardive :** `.exe`, `.zip`, `.png`, un fichier sans extension, `../../etc/passwd` et la règle invalide `(a)\1` sont acceptés. Le refus n'arrive qu'à l'envoi (415 ou 422), quand le fichier est déjà parti. **Hôte :** l'URL pointe vers `api.gdprguardian.com` alors que le MCP est sur `api.gardienrgpd.fr`. **Commande Python :** un `python -c` à plusieurs instructions, qui charge tout le fichier en mémoire, sans `Expect: 100-continue` ; un fichier de plus de 50 Mo est donc envoyé en entier avant le 413. |
| Envoi (PUT) | Oui | Traitement synchrone : 0,12 à 0,6 s pour un petit fichier, 3,5 s pour 6 Mo (5,2 millions de caractères en sortie). | La réponse contient un `result_url` qu'aucun outil ne documente (voir §2). |
| `get_anonymized` | Oui, avec réserves (5 sur 5) | **Avant l'envoi**, un message `pending` clair, qui anticipe même le cas 413. **Pagination :** pages d'environ 40 000 caractères, coupées en fin de ligne ou de paragraphe ; aucune des 22 266 lignes n'a été coupée. 0,03 à 0,5 s par page (moyenne 0,10 s sur 131 pages). **Sécurité :** le document arrive entre des marqueurs avec nonce. | **Suppression :** le résultat est supprimé à la lecture de la dernière page, alors que l'outil est annoté `destructiveHint:false`. La réponse dit `deleted:true` et en même temps `expires_in_seconds:573`. **Durée de vie :** 10 min à partir du traitement ; la lecture ne la prolonge pas (599 s tombés à 455 s pendant la pagination). **Erreur :** le même `not_found` pour un identifiant inconnu, un résultat expiré ou déjà lu. **Description :** mentionne `anonymize_file (local)`, qui n'existe pas en ligne. |
| Formats (opus-files-upload) | Oui | **Convertis :** DOCX avec en-tête, pied de page et tableau ; PDF texte de 2 pages ; XLSX à 3 feuilles ; CSV séparé par `;` ; EML (texte, HTML, pièce jointe) ; PPTX avec notes ; TXT ; `.xyz` lu comme texte. **Contrôles :** une extension trompeuse est signalée, un DOCX corrompu est refusé en 415. **Fuites par les métadonnées :** ni le nom de fichier ni l'auteur n'apparaissent dans la sortie. | **Pertes sans avertissement :** un PDF fait uniquement d'images ressort vide ; la pièce jointe d'un EML, les commentaires DOCX et XLSX et le texte masqué disparaissent aussi. **Fichier vide, désaccord :** opus-files-upload a reçu l'avertissement « no text extracted », opus-mcp-dx a obtenu `total_chars:0` sans aucun avertissement. |
| Session et protocole (opus-mcp-dx) | Oui, sans état | Protocoles négociés : 2024-11-05, 2025-03-26, 2025-06-18 et 2025-11-25. Aucun `Mcp-Session-Id` n'est émis. `tools/call` fonctionne sans `initialize`. DELETE répond 405. | Les capacités prompts, resources et logging sont annoncées, mais leurs listes sont vides. |
| Limitation de débit | Bien signalée | En-têtes `RateLimit-Policy: "req";q=30;w=3, "cpu";q=20000;qu="worker-ms";w=40`. Limite jamais atteinte. | — |

## 2. Remarques sur le MCP (dédoublonnées, par ordre d'importance)

1. **`countries` est un piège.** Vu par 3 testeurs (identifiers, mcp-dx, multilingual).
   - **Sans FR**, les noms, adresses, NIR et téléphones français ne sont plus détectés. Avec `countries="BE"`, "Gilles Marchetti" et un NIR restent en clair. Un avertissement est bien émis, et multilingual le juge clair, mais l'appel passe quand même.
   - **Avec le FR par défaut**, les identifiants étrangers valides restent en clair sans aucun avertissement (DNI, AVS, NISS, Steuer-ID), même quand `report.language` vaut `de`, `es` ou `nl`.
   - **Documentation :** la description ne liste pas les codes valides, et l'erreur renvoyée pour `FR;BE` ne parle pas de la virgule.
   - **`auto`, marqué expérimental, divise les testeurs.** Chez mcp-dx, il a bien détecté BE, CH, ES et FR. Chez multilingual, il a manqué BE, CH et LU.
   - **Suggestion :** toujours appliquer les lexiques de noms et d'adresses (ou refuser l'appel sans FR). Avertir quand un identifiant validé par un pack non activé, ou une langue non couverte, est détecté. Lister les codes dans le schéma. Ajouter un pack GB.
2. **Le résultat se perd facilement.** Signalé par 3 testeurs (legal-hr, files-upload, mcp-dx) ; la suppression a été constatée par 5.
   - La lecture détruit le résultat, ce que l'annotation ne dit pas. Si la réponse se perd et que le client relance, le résultat est perdu.
   - `not_found` ne dit pas pourquoi.
   - La durée de vie de 10 min n'est pas prolongée par la lecture. Lire 131 pages a pris 145 s à un script ; un vrai agent dépasserait les 10 min.
   - **Suggestion :** un délai de grâce après la dernière page, un `destructiveHint` honnête et des erreurs distinctes (`already_read`, `expired`, `unknown`). Prolonger la durée de vie à chaque lecture, ajouter une action d'annulation et proposer un téléchargement sur disque pour les gros fichiers.
3. **`result_url` n'est pas documenté.** Vu par 3 testeurs (legal-hr, files-upload, mcp-dx).
   - Un GET anonyme sur cette adresse renvoie le Markdown **sans** les marqueurs de contenu non fiable, et consomme le résultat : `get_anonymized` répond ensuite `not_found`.
   - **Suggestion :** en faire la voie officielle de téléchargement (avec marqueurs, par exemple `curl -o`), ou le retirer de la réponse.
4. **Chaque type de client perd une moitié de la sortie.** Vu par 2 testeurs (legal-hr, mcp-dx).
   - Le texte anonymisé n'est que dans le bloc texte. Avec fastmcp, `result.data` ne contient que `TextReport(report=…)`.
   - Le rapport (notice, explain, avertissements) n'est que dans `structuredContent`, et n'est pas typé.
   - Les avertissements sont ajoutés à la fin du texte anonymisé (`[GDPR Guardian] Warning: …`). Ils partiront donc dans le courriel ou le ticket.
   - **Suggestion :** ajouter `text` ou `markdown` au schéma de sortie, typer le rapport, mettre un résumé d'une ligne dans le bloc texte, et laisser les avertissements dans `report.warnings` seulement.
5. **Gains rapides : une mention fausse et deux domaines.** Chacun vu par 5 testeurs.
   - `get_anonymized` mentionne `anonymize_file (local)`, qui n'existe pas en ligne.
   - L'envoi se fait sur `api.gdprguardian.com`, pas sur `api.gardienrgpd.fr`. Cela surprend les listes d'autorisation et peut entamer la confiance d'un utilisateur français.
   - **Suggestion :** retirer la mention dans la version en ligne. Servir l'envoi sur le même domaine, ou l'annoncer dans la description.
6. **Les profils ne sont pas documentés et sont trompeurs.** Vu par les 6 testeurs.
   - **`fast` :** identique à `standard` chez legal-hr (10 documents), medical (10 documents) et mcp-dx. identifiers note toutefois que `fast` conserve SIREN, SIRET et TVA par politique d'entreprise, avec un `kept_by_policy` visible.
   - **`strict`, annoncé comme « rappel maximal » :**
     - Il masque seulement en plus les organisations et les SIREN/SIRET, avec de nouveaux faux positifs : "de la Société" devient `[ORG_2]`, "Chauffeur" devient `[ORG_2]` trois fois, "Entreprise" est classé ORG.
     - Il ne rattrape aucun oubli (constaté par legal-hr, files-upload et identifiers).
     - Avec `all`, il abîme les dates et les IBAN.
     - medical n'a vu aucune différence entre les trois profils sur ses documents.
   - **Suggestion :** décrire précisément l'effet de chaque profil et supprimer `fast` s'il n'apporte rien. Faire de `strict` un vrai mode rappel (initiales, matricules, minuscules) et corriger sa régression sur les dates et les IBAN.
7. **Des contenus disparaissent sans avertissement.** Vu par 1 testeur (files-upload).
   - Le résultat REST connaît `dropped: {comments:1, hidden_text:1, links:1, metadata:5}`, mais le PageMeta du MCP n'a pas ce champ et renvoie `warnings: []`.
   - **Suggestion :** exposer `dropped`. Avertir pour une page PDF sans couche texte, une pièce jointe non convertie et des commentaires supprimés.
8. **La validation de l'envoi arrive trop tard.** Vu par 2 testeurs (files-upload, mcp-dx).
   - Le refus 415 ne liste pas les formats acceptés.
   - **Suggestion :** valider l'extension et les règles dès `create_upload`, et lister les formats dans la description comme dans le message 415.
9. **Messages d'erreur : bons et bilingues dans l'ensemble, avec des trous.**
   - Un paramètre inattendu est signalé `? (unexpected_keyword_argument)`, sans son nom (legal-hr, mcp-dx).
   - `rules: "not-a-list"` reçoit le message trompeur « list of at most 20 rules » (legal-hr).
   - `rules` passé en chaîne JSON est refusé avec `dict_type` (mcp-dx).
   - `literal_error` ne liste pas les valeurs permises, et `string_too_long` ne donne ni la limite ni de renvoi vers `create_upload` (mcp-dx).
   - Un texte vide ne lève pas d'erreur (3 testeurs).
   - `anonymise_text` donne `Unknown tool` sans suggestion, alors que les descriptions écrivent « anonymise » (mcp-dx).
   - La notice n'est qu'en français (mcp-dx). Les descriptions sont bilingues dans une même chaîne, ce qui est bruyant (medical).
   - **Suggestion :** nommer la clé fautive, lister les valeurs et les limites, accepter `rules` en chaîne JSON, et proposer un alias ou un « vouliez-vous dire ».
10. **`explain` et étiquettes.**
    - `explain` donne la règle, la raison et le nombre par balise, sans jamais la valeur. Mais il ne dit pas quelle occurrence est concernée (legal-hr, medical).
    - **Éléments conservés, désaccord :** ils sont visibles avec `explain` selon legal-hr, files-upload, mcp-dx et multilingual. identifiers ne les a vus qu'en `fast`.
    - **Raisons fausses :** le SIRET d'une SARL a la raison `sole_trader` (identifiers). Le SIRET d'une société a été masqué pour la même raison à cause d'un « EI » ailleurs dans le texte (mcp-dx).
    - **Étiquettes fausses :**
      - `[ADRESSE_1]` pour un article de loi, `[CARTE_1]` pour un fragment d'IBAN, `[TEL_1]` pour un SSN, `[NIPC_1]` pour un passeport britannique (identifiers) ;
      - FINESS étiqueté `[ADELI_2]` (medical) ;
      - `DATE_NAISSANCE` pour des dates d'événement.
    - **`label_language=en` :** le préambule cite toujours `[PERSONNE_1]` (files-upload) ; `[STEUER_ID_1]`, `[NIE_1]`, `[NISS_1]` et `[CBE_1]` ne sont pas traduits (multilingual) ; la valeur `auto` n'est pas documentée (4 testeurs).
    - **Suggestion :** donner les positions des passages (sans les valeurs), toujours lister les éléments conservés, et corriger les libellés.
11. **Pièges de `rules`** (legal-hr), alors que la validation est par ailleurs jugée excellente par 5 testeurs :
    - `allow: ["Lyon"]` démasque aussi la personne "M. Lyon".
    - Une règle `keep` avec le contexte « signé » a conservé une vraie date de naissance 40 caractères plus loin.
    - `(?<=matricule )` est refusé, alors que la description dit les assertions en tête acceptées.
    - **Suggestion :** limiter `allow` au type d'entité, documenter (ou rendre réglable) la fenêtre de contexte, et corriger la description.
12. **Détails cosmétiques.**
    - La ligne `Replaced: {...}` est une représentation Python d'un dictionnaire (files-upload, mcp-dx).
    - `warnings` vaut `[]` en page 1 et `null` ensuite (files-upload).
    - Le rapport n'apparaît qu'en page 1 (mcp-dx).
    - `report.language` vaut `"und"` sur les textes courts (medical, multilingual).
    - Les commandes contiennent des `FILE_PATH` à remplacer à la main (medical).
    - `explain` passé à `create_upload` n'apparaît que dans le rapport de `get_anonymized` (medical).

## 3. Qualité de l'anonymisation

**Par testeur**

| Testeur | Angle | Rappel mesuré | Précision mesurée | Note |
|---|---|---|---|---|
| opus-legal-hr | 10 documents juridiques et RH, 323 occurrences | **90,4 %** au sens strict (292 sur 323). 98,7 % sur les noms hors initiales. 100 % sur les identifiants structurés (66 sur 66). 99,0 % hors initiales et matricules. | **97,4 %** (304 sur 312). 97,7 % des éléments à garder sont restés intacts. | 7 |
| sonnet-medical-social | 10 documents médicaux et sociaux, 146 éléments | **91,8 %** hors âges (134 sur 146). Environ 84 % en comptant les âges. | Environ 96 à 98 % | 7 |
| opus-files-upload | 9 fichiers, dont un de 6 Mo | **98,8 %** sur 6 petits documents (5 fuites sur 408). 92,6 % en comptant les 25 années de naissance. 99,6 % avec le fichier de 6 Mo (1 314 éléments). Aucune fuite d'identifiant direct. | Environ **99 %** (4 erreurs sur 540). Aucune erreur sur 106 892 remplacements dans le gros fichier. | 7,5 (flux d'envoi : 9) |
| sonnet-identifiers-adversarial | 12 documents piégés, environ 130 éléments | Environ **70 %**, environ 78 % hors identifiants étrangers sous FR | Environ **93 %** | 6,5 |
| opus-mcp-dx | 6 textes métier, plus des sondes | **90 %** par défaut (56 sur 62). 95 % des mentions (145 sur 153). 96 % sur les 5 textes français (46 sur 48). 95 % avec `all` (59 sur 62). | **100 %** en standard (78 sur 78), environ 87 % en `strict` | 7,5 |
| sonnet-multilingual | 8 documents, chacun avec 3 réglages de pays | Environ **79 %** avec FR par défaut (81 sur 102). Environ 88 % avec FR plus le pays du document. Environ 89 % avec `all`. Environ 93 % hors les 4 numéros à clé invalide inventés par le testeur. | Environ **96 %** | 6,5 |

**Par famille de données**
- **Identifiants français à clé de contrôle (NIR, IBAN, carte, téléphone, e-mail) : quasi parfait.**
  - 66 sur 66 chez legal-hr ; aucune fuite d'identifiant direct sur environ 107 000 mentions chez files-upload.
  - Le NIR est reconnu sous 7 formes, Corse (2A) comprise (medical). identifiers compte 8 NIR sur 9, et 7 cartes sur 7, y compris une carte à clé Luhn invalide et une Amex.
  - **Faiblesses :**
    - un IBAN en minuscules (13 IBAN sur 14) ;
    - le téléphone `0298 55 21 76` (13 formats sur 14 chez medical) ;
    - des téléphones collés à un mot ou britanniques (13 sur 18 sur le jeu piégé) ;
    - les e-mails obfusqués, seuls `[at]`/`[dot]` et `(at)`/`(dot)` passent la détection (11 sur 19) ;
    - un RIB écrit en morceaux, et le BIC (0 sur 4).
- **Noms complets : environ 99 %.**
  - 98,7 % hors initiales (legal-hr) ; 0 fuite dans d1 à d8 et 13 noms d'origines variées masqués (multilingual) ; 300 noms sur 300 sous une balise unique dans le fichier de 6 Mo (files-upload) ; environ 32 sur 35 sur le jeu piégé (identifiers).
  - **Fuites :** noms en minuscules, initiales (16 chez legal-hr), lettres espacées, certains contextes.
- **Cohérence des balises : c'est le point faible.**
  - legal-hr : 64 personnes sur 81 ont exactement une balise.
  - files-upload : noms complets toujours cohérents, mais les mentions partielles sont mal attribuées, 13 362 sur 13 431 dans le journal de 6 Mo et 14 sur 16 dans le CSV.
  - mcp-dx : parfait sur les textes courts ; une seule dérive dans le texte de 103 000 caractères.
- **Dates de naissance.**
  - Bien masquées, et recoupées avec le NIR.
  - **Fuites :** une date écrite en toutes lettres et `DDN 08/04/79` (medical), « née Guillou le 4 mai 1938 » (mcp-dx).
  - Dans les tableurs et les CSV, la date est réduite à l'année (files-upload, legal-hr).
  - Des dates d'événement sont masquées à tort (legal-hr, medical).
- **Identifiants sans format standard : en clair par défaut.**
  - Exemples : 12 matricules (legal-hr), RPPS, IPP et numéros de contrat (medical), numéro de poste et numéro de recommandé (files-upload), numéro client (mcp-dx).
  - Une règle `rules` suffit à les corriger : testé avec `[0-9]{11}` pour le RPPS et `MAT-[0-9]{5}` pour les matricules.
- **SIREN et SIRET : conservés par politique d'entreprise.** Le SIRET d'un entrepreneur individuel est pourtant conservé quand il apparaît dans du JSON ou dans « en nom propre » (identifiers, files-upload).
- **Identifiants étrangers.**
  - Avec FR par défaut, ils restent en clair.
  - Avec le bon pack, les NISS, Steuer-ID, NIE, AVS et DNI valides sont détectés.
  - Les numéros de TVA allemands, belges et espagnols et le BIC fuient même en `strict`. Les passeports allemands et britanniques fuient même avec `all`.
- **Adresses.**
  - Les adresses françaises sont bien traitées.
  - Les adresses non françaises ne sont jamais masquées, sauf `Avenue Louise 54, 1050 Ixelles` (multilingual).
  - Les lieux-dits ne sont masqués qu'en partie (medical).
- **Âges : désaccord.** Ils ne sont jamais masqués. medical compte cela comme une fuite ; legal-hr y voit un quasi-identifiant faible, laissé visible exprès.

**Par type de document**
- **Juridique et RH :** 90,4 % au sens strict, 99 % hors initiales et matricules, précision 97,4 %. Les défauts dominants sont les dates d'événement et les couples confondus. Le procès-verbal de CSE à 20 personnes est parfait.
- **Médical et social :** 91,8 % hors âges. Le contenu médical n'est jamais masqué à tort. Le RPPS, l'IPP et les âges fuient.
- **Textes métier français :** 96 %, avec une précision de 100 %.
- **Fichiers bureautiques :** 98,8 %, structure préservée. En revanche, le contenu non textuel est perdu sans avertissement.
- **Gros volume (6 Mo, 131 pages) :** ni fuite ni masquage à tort, mais la cohérence des mentions partielles s'effondre.
- **Tableaux :**
  - Un CSV propre est lu avec ses en-têtes.
  - Le même tableau en Markdown donne des balises séparées pour le nom et le prénom, et laisse les matricules visibles (legal-hr). identifiers n'a vu aucune fuite sur son tableau Markdown.
  - Un CSV avec des lignes vides a laissé fuir 4 noms sur 9.
- **Multilingue :** 79 % avec FR par défaut, 88 à 89 % avec les packs, et des faux positifs sur des mots non français.
- **Jeu piégé :** environ 70 %.

**Note globale : 7/10**, la moyenne exacte des six notes (7 ; 7 ; 7,5 ; 6,5 ; 7,5 ; 6,5).
- **Ce qui la porte :** les identifiants directs français sont quasi parfaits, les noms complets atteignent environ 99 %, la précision va de 93 à 100 % et le sens reste exploitable par une IA.
- **Ce qui la retient :**
  - des identités fusionnées ou scindées ;
  - des dates d'événement corrompues ;
  - des identifiants sans format standard qui fuient ;
  - la couverture hors France, qui fuit avec le FR par défaut ;
  - un contrat MCP qui peut faire perdre le résultat.

**Écart entre Opus et Sonnet.** Les Opus donnent en moyenne 7,33 (7 ; 7,5 ; 7,5), les Sonnet 6,67 (7 ; 6,5 ; 6,5), soit environ 0,7 point d'écart. Cet écart tient à l'angle de test plutôt qu'au modèle :
- À angle comparable, sur des documents métier français (legal-hr pour Opus, medical pour Sonnet), les deux notes sont de 7/10, avec des rappels proches (90,4 % et 91,8 %).
- Les deux notes de 6,5 viennent des angles les plus durs (jeu piégé, multilingue). Les deux notes de 7,5 viennent du flux de fichiers et de textes métier.
- Les Opus ont fait plus d'appels : environ 180 à 307 chacun, contre environ 37 à 90 pour les Sonnet. identifiers n'a pas testé l'envoi de fichiers.
- Les règles de comptage diffèrent : medical compte les âges comme des fuites, legal-hr non.

## 4. Problèmes à corriger en priorité

1. **Identités fusionnées ou scindées quand le nom est partiel.** Gravité : sens faussé et faux lien entre personnes. Vu par les **6** testeurs ; chez mcp-dx, une seule dérive, dans le texte long.
   - `M. Didier Le Floch et Mme Yvette Le Floch. M. Le Floch… Mme Le Floch…` : les deux dernières mentions deviennent toutes deux `[PERSONNE_3]`.
   - `Mme Solène Kervadec-Moulin … Mme Kervadec a été absente` → `Mme [PERSONNE_1] … Mme [PERSONNE_3] a été absente`.
   - `avec Mme Ondine Lafargue` → `Mme [PERSONNE_28] [PERSONNE_9]`, où `[PERSONNE_9]` désigne une autre salariée.
   - Dans un arrêt, un même bénéficiaire porte deux balises, si bien que la condamnation semble profiter à deux personnes.
2. **Dates d'événement masquées comme dates de naissance.** Gravité : sur-masquage, la chronologie juridique ou clinique est perdue. Vu par **2** testeurs (legal-hr : 8 sondes sur 8 et 3 documents ; medical).
   - Le motif « né le » est trouvé à l'intérieur de mots (signé, ordonné, désigné, etc.), et la fenêtre de mot-clé capture les dates suivantes.
   - `Le contrat a été signé le 4 mars 2024` → `signé le [DATE_NAISSANCE_1]`.
   - `Patient né le 01/07/1990. Hospitalisé le 14/09/2026.` → `… Hospitalisé le [DATE_NAISSANCE_2]`.
3. **Piège de `countries` et couverture hors France.** Gravité : fuite de données. Vu par **3** testeurs.
   - Avec `countries="BE"`, `Gilles Marchetti … 2 85 07 75 116 042 97` reste inchangé, avec seulement un avertissement.
   - Avec FR par défaut, `DNI 48213907L, AVS 756.1234.5678.97` reste inchangé, sans avertissement.
   - Avec n'importe quel réglage, `Lindenstraße 23, 10969 Berlin` et `QQ 12 34 56 C` restent inchangés.
4. **Identifiants sans format standard laissés en clair.** Gravité : fuite. Vu par **5** testeurs.
   - `(matricule 004587)` reste inchangé, alors que `N° de matricule 004588` est masqué.
   - `Dr Paul Auger, RPPS 10001234567` → `Dr [PERSONNE_1], RPPS 10001234567`.
   - `exploite en nom propre (SIRET 812 345 678 00013)` reste inchangé.
5. **Formes de noms qui fuient.** Gravité : fuite. Vu par **5** testeurs.
   - `j'ai vu jean dupont` reste inchangé, alors que `Jean Dupont` est masqué ailleurs dans le texte.
   - `Paraphes : FXLD / CN` et `M. J.-B. de La Fontaine` restent inchangés.
   - `Le témoin suisse Reto Brunschwiler a signé.` reste inchangé ; sans le mot « suisse », le nom est masqué.
6. **Lieux et mots courants pris pour des personnes.** Gravité : sur-masquage. Vu par **4** testeurs (legal-hr, medical, files-upload, multilingual).
   - `M. Lyon rappelle… Il veut quitter Lyon` → `quitter [PERSONNE_1]`.
   - `Ville: Meylan` → `[PERSONNE_26]`.
   - `Met vriendelijke groeten` → `[PERSONNE_4] vriendelijke groeten`.
   - Le titre `C. Loyer` devient une balise de personne.
7. **Résultat détruit à la lecture, sans reprise possible.** Gravité : ergonomie, il faut renvoyer le fichier. Signalé par **3** testeurs, constaté par 5.
   - Lire deux fois la dernière page avec `get_anonymized` donne `not_found: Introuvable ou expiré`, la même réponse que pour un identifiant inexistant.
   - Un GET sur `result_url` puis un appel à `get_anonymized` donne aussi `not_found`.
8. **Texte ou rapport invisibles selon le client, avertissements injectés dans le texte.** Gravité : ergonomie, et l'avertissement part avec le texte. Vu par **2** testeurs.
   - `structuredContent` contient seulement `{report: …}`, sans le texte anonymisé.
   - La sortie texte se termine par `[GDPR Guardian] Warning: …`.
9. **Contenu supprimé sans avertissement.** Gravité : ergonomie, fausse assurance que tout a été traité. Vu par **1** testeur (files-upload).
   - Un `scan.pdf` fait uniquement d'images ressort sous la forme `<!-- page 1 -->`, avec `warnings: []`.
   - La pièce jointe d'un EML devient `- Pièce jointe 1 (text/plain)`, sans son contenu.
   - Un commentaire DOCX disparaît sans signalement.
10. **Numéros non personnels masqués et `strict` qui abîme le texte.** Gravité : sur-masquage, et fuite partielle en `strict`. Vu par **3** testeurs (identifiers, mcp-dx, multilingual).
    - `Articles L. 1221-3, R. 111-2 du code` → `Articles L. [ADRESSE_1]-2 du code`.
    - `3.14.159.26` → `[IP_3]`.
    - En `strict` avec `all` : `né le 12/03/1992` → `né le 12/[TEL_1]`, et `FR18 1027 8000 0100 0209 8765 4379` → `FR18 1027 8000 [TEL_1] 4379`.

## 5. Ce qui marche bien

- **Vitesse :** les 6 testeurs la saluent. 35 à 46 ms en médiane, 103 000 caractères en 206 ms, 6 Mo traités en 3,5 s.
- **Identifiants à clé de contrôle :**
  - Le NIR est reconnu sous toutes ses formes, Corse (2A) comprise, et même avec une clé invalide.
  - Les cartes sont détectées même avec une clé Luhn invalide, Amex comprise.
  - Les numéros des packs étrangers sont validés par leur clé.
  - Plusieurs formats d'un même numéro de téléphone ou d'un même IBAN reçoivent une seule balise.
  - Une date de naissance est masquée quand elle correspond au NIR (`matches_nir`).
- **Liens entre les formes d'un nom :**
  - `DUPONT Jean`, `P.-Y. Le Goff`, `@Mélanie`, `ROUSSEAU C.` et les noms coupés par un retour à la ligne sont tous rattachés à la bonne personne.
  - Les homoglyphes cyrilliques, les caractères invisibles, les espaces insécables et les caractères pleine chasse sont normalisés.
  - Le procès-verbal à 20 personnes est parfait.
- **Mots qui sont aussi des noms :** « M. Pierre Boulanger est boulanger », « La France connaît », « loi Badinter », Alzheimer, Parkinson et Down sont bien traités. Le contenu médical n'est jamais masqué à tort.
- **Fichiers :**
  - Le fichier de 6 Mo ne contient aucune fuite.
  - Les noms de fichier et les métadonnées d'auteur ne sortent jamais.
  - Une extension trompeuse est détectée.
  - Les en-têtes de tableur servent de contexte.
  - Dans les EML, en-têtes, réponse citée et signature sont traités.
- **Sécurité du flux d'envoi :**
  - L'URL d'envoi est à usage unique et le 413 arrive avant l'envoi du corps avec curl.
  - Les marqueurs à nonce et le texte d'injection de prompt sont restitués comme de simples données.
  - `explain` ne montre jamais de valeur.
  - Le message `pending` anticipe même le cas 413.
- **Règles d'organisation :** des règles précises et contextuelles, avec une validation excellente, comblent les manques (RPPS, `MAT-…`, liste de refus).
- **Politique d'entreprise auditable :** `company_policy` et `sole_trader` sont visibles. Les noms de société qui contiennent le nom d'une personne sont masqués.
- **Communication :** erreurs bilingues, en-têtes de limitation de débit standard, notice honnête sur le risque résiduel, avertissement clair quand FR manque, commandes prêtes à exécuter pour 3 shells.