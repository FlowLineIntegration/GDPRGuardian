# Déployer Gardien RGPD / Deploying GDPR Guardian

[Français](#français) · [English](#english)

## Français

Le service expose dans **un seul processus d'accueil** l'API REST (`/v1/...`) et le serveur MCP en ligne (`/mcp`).
Tout est traité **en mémoire** : aucun fichier temporaire, aucune base, aucun journal de contenu. Le service officiel
est **réservé aux détenteurs d'une clé d'API** (une par organisation, remise sur demande avec un accord de
sous-traitance, art. 28 RGPD) ; un limiteur en mémoire, par client, contient les abus (voir « Accès par clé »
ci-dessous).

### Une requête, un processus

Chaque requête (texte ou document, REST ou MCP, envoi hors bande) est traitée **de bout en bout** (compilation
des règles de l'organisation, conversion, anonymisation, portée des balises) dans un **processus isolé à usage
unique**, détruit après sa réponse. Le processus d'accueil ne fait que HTTP, l'admission, l'ordonnancement et le
dépôt des résultats : il ne lit, ne compile ni n'anonymise jamais un contenu, et des règles de l'organisation il
ne contrôle que la structure (nombre, longueurs, libellés). Son empreinte ne dépend donc pas des règles reçues.

- **Linux** : un *zygote* est lancé au démarrage, durci, puis préchargé une fois (packs, automates de mots-clés,
  noyau Rust, lexique des noms, convertisseurs, moteurs par défaut). Chaque travailleur en naît par `fork` en
  quelques millisecondes et partage sa mémoire (copie à l'écriture) ; le zygote ne voit jamais de document et
  tue lui-même ses enfants. Une réserve de travailleurs neufs (`GDPRGUARDIAN_PREWARM_WORKERS`) attend les requêtes :
  une requête ne paie que l'échange. Mesures (16 cœurs) : texte de 2 Ko de bout en bout **p50 7,5 ms, p95
  9,2 ms** ; environ 300 textes de 2 Ko par seconde avec 8 travailleurs ; 100 PDF de 10 Mo envoyés d'un coup,
  tous traités (17,5 s avec 4 travailleurs).
- **Windows, macOS** : chaque travailleur est un interpréteur neuf (« spawn », ~1,5 s de CPU) ; la réserve masque
  ce coût pour des requêtes espacées (p50 12 ms), mais le débit soutenu plafonne à quelques requêtes par seconde.
  Usage poste de travail ; en production, Linux.
- Chaque travailleur, avant tout document : sorties standard vers `/dev/null`, aucune variable `GDPRGUARDIAN_*`
  (l'accueil les retire de son environnement avant de lancer le zygote : ni clé ni réglage, même dans le bloc
  d'environnement initial ; seul l'interrupteur du moteur `GDPRGUARDIAN_PURE_PYTHON` est transmis), non lisible
  (`PR_SET_DUMPABLE=0`), sans core dump, sans droit de créer un processus, mémoire plafonnée
  (`GDPRGUARDIAN_WORKER_MEMORY_MB` au-delà de son empreinte au repos), tué à l'échéance. Il ne garde aucun canal
  vers le zygote. Ses réponses sont du JSON vérifié et du texte UTF-8, jamais du pickle.
- **Règles de l'organisation** (`rules`) : compilées dans le travailleur de la requête, avant tout contenu, sur
  un seul fil et sous un budget (2 Mo par motif, 16 Mo par jeu) ; au-delà, ou hors des formes exactes du moteur
  linéaire, la règle est refusée avant d'allouer : 422 `invalid_request` avec la raison du moteur (voir
  `docs/REGLES.md`). Pour un envoi hors bande, `POST /v1/uploads` (et `create_upload`) compile les motifs dans
  un travailleur avant que le fichier parte : le 422 tombe dès la création de l'envoi.
- **Admission** : chaque requête qui porte un contenu réserve sa taille (`Content-Length`) **avant** la lecture
  du corps, dans un budget mémoire (`GDPRGUARDIAN_QUEUE_MB`). Une clé au-delà de sa part équitable ne peut pas
  prendre le dernier quart du budget, gardé pour les autres clés. Les requêtes admises attendent un travailleur
  libre : une place libérée va à la clé en attente qui en occupe le moins, puis à celle qui attend depuis le
  plus longtemps (depuis son arrivée ou la fin de son dernier travail ; ordre d'arrivée pour une même clé). Une
  clé qui arrive passe donc avant une clé qui inonde le service et attend **au plus une libération de place**
  (derrière les seules clés arrivées avant elle) ; aucune clé n'est affamée. Le service ne répond
  `503` (avec `Retry-After`) que si le budget est épuisé ; un client qui annonce `Expect: 100-continue` (curl,
  au-delà de 1 Mo) est refusé sans avoir envoyé son corps. Un client qui se déconnecte pendant l'attente ou le
  traitement d'une requête synchrone libère sa place : son travailleur est tué.
- **Envoi hors bande** : un fichier reçu n'expire pas tant qu'il attend son travailleur, même derrière une
  longue file ; son délai de traitement part de l'attribution du travailleur.

### Accès par clé, limites par client, résultats isolés

**Mode à clés**, celui du service officiel : REST, MCP, envois hors bande et cockpit du site exigent l'en-tête
`Authorization: Bearer <clé>` (seul accepté) ; sans clé valide, 401 avant toute lecture du corps. Les clés sont
données **seulement par leurs empreintes SHA-256** (`GDPRGUARDIAN_API_KEY_SHA256`, calculées par
`printf '%s' "$cle" | sha256sum`) : une clé en clair dans l'environnement se lirait par `/proc/<pid>/environ`, et
`GDPRGUARDIAN_API_KEYS` est donc refusé au démarrage. Chaque clé est un principal isolé (ses envois lui restent liés).
`GDPRGUARDIAN_PUBLIC=1` (autre déploiement) : **aucune authentification** ; une clé valide y donne son propre
principal, une clé absente, fausse ou ancienne est ignorée.

**Identité d'un client, sans rien garder.** Nginx pose `X-GG-Client = $remote_addr` en écrasant toute valeur envoyée
par le client ; le service ne lit cet en-tête que s'il est nommé par `GDPRGUARDIAN_CLIENT_IP_HEADER` (sinon, il prend
l'adresse du pair TCP, jamais un en-tête). L'adresse devient aussitôt un **pseudonyme** : les 8 premiers octets de
HMAC-SHA256(secret, préfixe), avec un secret de 32 octets tiré au démarrage, en mémoire seulement, renouvelé toutes
les 24 h (le précédent reste reconnu 10 minutes pour que l'état d'un client survive à la bascule). Deux niveaux :
IPv4 /32 et /24, IPv6 /64 et /48 (une IPv4 mappée compte comme IPv4). L'en-tête est retiré de la requête dès sa
lecture : l'adresse n'atteint ni les routes, ni MCP, ni les journaux, ni les datagrammes d'usage, ni un message
d'erreur, ni une réponse. Une requête qui arrive sur le socket **sans** cet en-tête vient du serveur lui-même (sonde
de santé, protocole de mesure) : principal **LOCAL**, hors des budgets par client, mais deux traitements à la fois au
plus et jamais sur la place réservée aux petites requêtes ; ses datagrammes portent `"src":"protocol"`. Avec
`GDPRGUARDIAN_LOCAL_TOKEN_SHA256` (le service officiel : `install.sh base` crée le jeton), elle doit en plus présenter
le jeton local dans `X-GG-Local` : `curl -H @/etc/gdprguardian/local-header --unix-socket /run/gdprguardian/app.sock
…` (fichier root 0600, jamais en argument de commande). Sans lui, elle tombe dans le seau commun des adresses
illisibles : un travailleur compromis, qui joint le même socket, ne passe ni pour le serveur ni pour le protocole.
Nginx efface `X-GG-Local` ; un essai du protocole public lancé sur le serveur passe donc par le socket avec ce fichier.

**Limiteur** (`server/limiter.py`, mémoire seule, décision **avant toute lecture du corps**) :

| Couche | Valeur par défaut | Réglage |
|---|---|---|
| Requêtes bon marché (santé, `/status`, packs, résultats, création d'envoi, chaque message MCP) | 10 par seconde, rafale de 30, par client | `GDPRGUARDIAN_LIMIT_CHEAP_RATE`, `_CHEAP_BURST` |
| Coût des requêtes à contenu (texte, fichier, envoi, MCP), en secondes de travailleur (GCRA à coût variable) | recharge 0,5 s par seconde, rafale de 20 s, par client ; dette jusqu'à l'échéance du plus long travail (60 s + 4 s/Mo : environ 270 s pour 50 Mo) | `_COST_RATE`, `_COST_BURST`, `_COST_DEBT` (plancher) |
| Niveau préfixe (/24 IPv4, /48 IPv6) | 2 fois le budget d'un client | `_PREFIX_FACTOR` |
| Estimation avant lecture (`Content-Length` ; corps « chunked » : le plafond de la route) | texte 0,005 s + 0,15 s/Mo ; fichier 0,05 s + 0,4 s/Mo ; 0,005 s au moins ; multipliée par la lenteur observée du client ou de son préfixe (moyenne glissante mesure / estimation, de 1 à 100) | `_TEXT_BASE_S`, `_TEXT_PER_MB_S`, `_FILE_BASE_S`, `_FILE_PER_MB_S`, `_FLOOR_S`, `_MAX_SLOWNESS` |
| Correction | temps de travailleur mesuré (occupation de la place, ou temps processeur rapporté par le travailleur s'il est plus grand) ; sans travailleur (corps trop lent, trop gros, client parti), l'estimation reste due ; seul un refus de capacité (503) la rend | — |
| Concurrence | 3 requêtes à contenu en vol par client (1 en cours, 2 en attente), 12 par préfixe ; en cours, au plus la moitié des places non réservées par préfixe (1 sur 3 places) ; LOCAL : 2 en cours | `_MAX_RUNNING`, `_MAX_QUEUED`, `_MAX_INFLIGHT_PREFIX`, `_MAX_RUNNING_PREFIX` (plafond), `_LOCAL_RUNNING` |
| Place réservée | 1 place de travailleur pour les requêtes estimées sous 0,2 s ; une petite requête qui dure plus de 5 s compte alors comme grosse (la place libérée suivante revient aux petites) | `_RESERVED_SLOTS`, `_SMALL_S` |
| Délestage | 503 quand l'attente estimée dépasse 10 s : simulation de la file (fins estimées des travaux en cours, puis les requêtes servies avant celle-ci, chacune sur la première place qu'elle a le droit de prendre) ; une place utilisable libre et personne devant : 0, si bien qu'un petit texte n'est jamais délesté à cause de gros documents tant que la place réservée est libre. Un travail au-delà de son estimation est supposé durer encore autant, jamais au-delà de son échéance | `_MAX_WAIT_S` |
| État | 100 000 clés par niveau ; clés reposées (sans lenteur retenue) ou inactives 10 min retirées ; débordement à la Space-Saving (une clé nouvelle hérite de l'état de la moins chargée d'un échantillon : jamais de budget neuf pendant une inondation) | `_MAX_KEYS`, `_IDLE_S` |
| Pseudonymes | secret renouvelé toutes les 24 h, grâce de 10 min | `_ROTATE_S`, `_GRACE_S` |
| Mode | `enforce` (défaut), `dry-run` (les seaux comptent sans refuser ; requêtes en vol, plafonds de l'ordonnanceur et délestage restent appliqués), `off` (interrupteur d'arrêt) | `GDPRGUARDIAN_LIMITS` |

(Les réglages s'écrivent `GDPRGUARDIAN_LIMIT_<NOM>`. En mode à clés, chaque clé est un client du limiteur, avec les
mêmes réglages, sans niveau préfixe ; un appel `/mcp` sans clé valide reçoit son 401 sous les limites de son adresse.)
Concrètement : un client peut faire traiter à la suite quatre documents de 10 Mo, puis un toutes les 8 secondes ; des
centaines de petits textes par minute (le bord Nginx plafonne à 20 requêtes par seconde) ; un document de 50 Mo passe
toujours sur un budget plein (son estimation, 20,1 s, dépasse la rafale de 20 s : elle passe seau vide), puis le
suivant de même taille attend deux fois le temps de travailleur consommé (mesuré : 4 s après un DOCX illustré de
50 Mo traité en 3 s) ; un document qui occupe un travailleur jusqu'à son échéance (270 s) se paie en entier (environ
9 minutes d'attente).
Une erreur interne du limiteur laisse passer la requête (fail open) ; le balayage le signale en WARNING agrégé (total,
nouvelles) au plus une fois par minute, et `install.sh verify` échoue si le compteur n'est pas nul. Compteurs
**agrégés seulement** (acceptées, limitées, délestées, débordements, clés suivies, en cours) sur `GET /status`, jamais
par client.

**Corps.** Chaque corps doit arriver en entier en 15 s plus sa taille (annoncée, sinon le plafond de la route) à
128 Kio/s (une ligne montante de 1 Mbit/s ; `GDPRGUARDIAN_MIN_BODY_RATE_KIB`) : au-delà, 408 `upload_timeout`,
connexion fermée, mémoire rendue. Le délai de Nginx entre deux lectures (15 s) ne suffit pas : un octet toutes les
14 s tiendrait une connexion sans fin. Création d'un envoi (`POST /v1/uploads`) : 256 Kio au plus, comptée en vol et
dans le budget mémoire comme toute requête à corps.

**Mémoire.** Tout corps réserve sa taille avant d'être lu dans le budget du processus d'accueil
(`GDPRGUARDIAN_QUEUE_MB`) ; quand un travailleur prend la requête, elle réserve aussi deux fois la plus grande réponse
possible, ramenées à la taille réelle du résultat jusqu'à la fin de la réponse (un lecteur lent tient donc sa part du
budget, pas davantage). L'équité du budget suit le **préfixe** d'un client public (/24, /48) : tourner ses /64 n'ouvre
aucune part neuve ; une clé au-delà de sa part n'entame jamais la dernière réserve. Un résultat (texte ou Markdown)
ne dépasse jamais 1/8 de `GDPRGUARDIAN_MAX_STORE_CHARS` (12,5 M caractères pour le service officiel) : au-delà, le
travailleur répond 413 sans rien envoyer ; un document converti en plus du double est refusé dès la conversion,
avant le moteur (voir « Gros documents »).

**Envois différés.** En attente du fichier : 40 par préfixe du créateur (`GDPRGUARDIAN_MAX_UPLOADS_PER_PREFIX`),
10 000 en tout (`GDPRGUARDIAN_MAX_PENDING_UPLOADS`), 10 par clé ou principal sans réseau. Reçus et non lus : 10 par
client du **PUT** (`GDPRGUARDIAN_MAX_ACTIVE_UPLOADS`) et 40 par son préfixe, 1 000 en tout ; leurs caractères : 1/8 du
dépôt par client du PUT, 1/4 par préfixe (429 `too_many_unread_results`, jeton intact si refusé avant le travail). Le
PUT part de la machine de l'utilisateur : un connecteur MCP distant ou un NAT partagé par beaucoup ne fait pas
partager à tous le quota d'un seul.

**Pages tierces.** Une requête qu'un navigateur envoie depuis une autre page (`Sec-Fetch-Site` autre que
`same-origin` ou `none`) reçoit 403 `cross_site_request`, de Nginx puis du service, sans rien compter : un formulaire
multipart d'un site tiers passe sans contrôle CORS préalable et ferait sinon de ses visiteurs une source de charge.
Le cockpit (même origine) et les clients hors navigateur (en-tête absent) ne sont pas concernés.

**Réponses.** 429 `rate_limited` (budget d'un client) ou 503 `service_busy` (délestage), corps JSON fermé, toujours
avec `Retry-After` en secondes entières, plus 0 à 20 % d'aléa pour que les clients refusés ne reviennent pas ensemble,
et au mieux `RateLimit-Policy` / `RateLimit` (brouillon IETF httpapi-ratelimit-headers-11 :
`"req";q=30;w=3`, `"cpu";q=20000;qu="worker-ms";w=40` ; « worker-ms » n'est pas une unité enregistrée, seul
`Retry-After` fait foi). Le corps donne aussi l'attente en secondes (`retry_after_s`). Sur `/mcp`, un client MCP ne
lit jamais le corps d'une réponse HTTP 4xx/5xx (il n'affiche que « Server returned an error response ») : une requête
JSON-RPC refusée (429, 503, 408, 413) y reçoit donc HTTP 200 et une erreur JSON-RPC (`-32000`, message
`code: message … retry_after_s=N`, `data` : `code`, `http_status`, `retry_after_s`), avec le même `Retry-After` ;
sans identifiant JSON-RPC (notification, lot), le statut HTTP reste. L'identifiant est cherché dans les 8 premiers Kio
et les 512 derniers octets du corps lu à vide, rien d'autre n'est gardé. Aux clients (scripts, agents MCP) : une
requête à la fois, respecter `Retry-After`, trois essais au plus, des reprises sous 10 % des requêtes.

**Bord Nginx** (garde grossière, avant le service) : 20 requêtes par seconde (rafale 40) et 16 connexions par
adresse IPv4 ou /64 IPv6, 48 par /24 ou /48, 1 500 en tout (API et `/v1/` des sites) ; en-têtes lus en 10 s, corps
sans pause de plus de 15 s ; requêtes inter-sites refusées (403) ; HTTP clair fermé (444) pour le service, `/v1/` et
`/mcp` des sites compris, sans redirection. La clé /64 est écrite sous une forme unique quelle que soit la compression
de l'adresse (testé : `tests/server/test_deploy_config.py` et le banc de bout en bout). Zones en mémoire partagée de
Nginx seulement, jamais en swap (`MemorySwapMax=0`).

**Vie privée et base légale.** Une adresse IP est une donnée personnelle, même pseudonymisée tant que le secret existe.
Son traitement transitoire pour la sécurité du service et la lutte contre les abus repose sur l'intérêt légitime
(RGPD art. 6.1.f, considérant 49) et répond à l'art. 32 : pseudonyme en mémoire seulement, 24 h au plus (renouvellement
du secret ; un redémarrage efface tout), rien sur disque, aucun journal d'accès ni d'activité (le service tourne au
niveau `warning` : aucun événement par requête ou par document), journal d'erreurs de Nginx au seul niveau `emerg`
(jamais d'adresse), journal du pare-feu coupé (`ufw logging off`), pas de swap ni de vidage mémoire. Nginx garde
l'adresse binaire dans ses zones de limite (mémoire partagée, LRU), jamais sur disque. Restent hors de ce service : la
base de fail2ban (clients SSH seulement) et les anciennes entrées du journal du noyau, qui tournent seules.

**Isolation des résultats, par conception.** Jamais le résultat d'un autre :
- chemins synchrones (`/v1/anonymize/text`, `/v1/anonymize/file`, `/v1/detect`, `anonymize_text`) : le résultat ne
  part que dans la réponse, **rien n'est stocké** ; chaque requête a son processus neuf ;
- chemin différé (`POST /v1/uploads` ou `create_upload`, puis `PUT`, puis `GET /v1/results/{id}` ou `get_anonymized`) :
  joignable **seulement par capacité**. Jeton d'envoi et identifiant de résultat sont des valeurs aléatoires de
  256 bits (le second dérivé du premier par HMAC sous une clé en mémoire : qui voit l'URL d'envoi, dans un historique
  ou une ligne de commande, n'en déduit pas l'identifiant), remises au seul demandeur, gardées en **empreintes** SHA-256,
  comparées en temps constant ; le jeton sert une fois ; le résultat est effacé 2 minutes après sa lecture complète
  (une réponse perdue se relit) ou à son échéance, 30 minutes au plus après sa publication ; un jeton faux,
  expiré ou d'une autre clé donne **la même réponse** (404 `not_found`) ; un jeton déjà utilisé le dit à son seul
  détenteur (404 `upload_used` : demander une nouvelle URL) ; un résultat disparu donne un motif
  distinct (`already_read`, `expired`, `deleted`, toujours 404) au seul détenteur de son identifiant ; aucune route ne
  liste quoi que ce soit ; MCP est sans état (aucun identifiant de session, qui ne donnerait de toute façon aucun
  droit). En mode public, la capacité suffit (l'adresse d'un agent change entre ses appels) ; avec une clé (le
  service officiel), il faut en plus la clé ;
- `Cache-Control: no-store` imposé sur toute réponse (le service, puis Nginx), aucun `proxy_cache`, aucune réponse
  partagée.

### Gros documents : limites publiées, chaîne, mesures

**Limites publiées** (site, ce document, messages d'erreur ; vérifiées par `tests/server/test_big_documents.py`) :

- **50 Mo par fichier** (50 Mio, 52 428 800 octets), tous formats, par le site, REST et MCP : au-delà, 413
  `payload_too_large` « Fichier trop volumineux : 50 Mo au plus », dès la taille annoncée quand il y en a une (Nginx
  au-delà de 51m, le service au-delà de 50 Mio plus 64 Kio d'enveloppe multipart, un `PUT` hors bande au-delà de
  50 Mio, sans le lire), sinon à la lecture. Le poste de travail du site refuse un tel fichier sans l'envoyer ;
- **un million de caractères par texte** (`/v1/anonymize/text`, `anonymize_text`) : 413 « Texte trop long :
  1 000 000 caractères au plus » ;
- par document, **12,5 millions de caractères de résultat** (Markdown anonymisé, 1/8 de
  `GDPRGUARDIAN_MAX_STORE_CHARS`) : 413 `document_too_large` « Résultat trop long : 12 500 000 caractères au plus par
  document ». Un texte converti en plus du double est refusé dès la conversion, avant le moteur ; entre les deux, le
  moteur tourne et le résultat est mesuré (les balises raccourcissent les tableaux d'identifiants) ;
- **10 000 pages ou diapositives** par document (`GDPRGUARDIAN_MAX_PAGES` ; la bibliothèque seule garde 500) : 413
  « Document trop long : 10 000 pages au plus » ;
- **un million de balises HTML (ouvrantes et fermantes)** (HTML, courriels HTML, sortie de mammoth), comptées avant
  l'analyse, un « < » isolé du texte n'en étant pas une : 413 « HTML trop complexe : 1 000 000 balises au plus,
  ouvrantes et fermantes » (l'arbre de BeautifulSoup pèse environ 600 octets et 27 µs par balise) ; et **256 niveaux
  d'imbrication**, vérifiés juste après l'analyse : 413 « HTML trop imbriqué : 256 niveaux au plus » (markdownify
  descend récursivement, deux appels par niveau) ;
- **100 000 paragraphes Word (cellules de tableau comprises)** et un million d'éléments XML, comptés avant mammoth
  dans le document, ses notes et ses commentaires, quel que soit le préfixe d'espace de noms : 413 « Document Word
  trop long : 100 000 paragraphes au plus, cellules de tableau comprises » ou « Document Word trop complexe :
  1 000 000 éléments au plus » (même message si la sortie de mammoth dépasse le million de balises HTML). mammoth, puis
  l'arbre HTML et markdownify coûtent environ 0,27 ms par cellule et 20 µs par autre élément : au pire, un tableau
  juste sous la limite, moins de la moitié de l'échéance d'un petit document (mesures plus bas) ;
- tableurs : 2 millions de cellules lues (au-delà, contenu tronqué et signalé), 200 Mio décompressés, parties XML de
  64 Mio ;
- durée : corps reçu en 15 s plus sa taille à 128 Kio/s (408) ; traitement en 60 s plus 1 s par 250 Ko (422
  `conversion_timeout`), soit 270 s pour 50 Mio, pour tous les convertisseurs, tableurs compris.

En pratique, un document illustré (PDF, Word, PowerPoint, OpenDocument, RTF, courriel avec pièces jointes) passe
jusqu'à 50 Mo ; un texte très dense atteint 12,5 millions de caractères avant : vers 13 Mo de texte brut ou de
Markdown, 16 Mo de CSV, 4 Mo de cellules de tableur, 16 Mo de HTML en tableaux. Un tableau Word s'arrête vers
100 000 cellules (14 000 lignes de 7 colonnes, quelques centaines de Ko compressés).

**La chaîne pour un fichier de 50 Mio** (service officiel), avant et après ce tour :

| Couche | Avant | Après |
|---|---|---|
| Nginx `client_max_body_size` (API et `/v1/` des sites) | 60m | 51m : 50 Mio + 1 Mio de marge, qui couvre l'enveloppe multipart (64 Kio) ; entre les deux, le service refuse avec le même message |
| Nginx `client_body_timeout`, `send_timeout`, `limit_conn` | 15 s entre deux lectures, 60 s, 16 par adresse | inchangé |
| Nginx `proxy_read_timeout` | 300 s, sous échéance plus attente | 600 s : deux échéances maximales |
| Service, taille | 50 Mio + 64 Kio ; `PUT` lu jusqu'à 50 Mio avant refus ; message générique | idem ; `PUT` refusé dès `Content-Length` ; limite nommée |
| Service, corps | 15 s + 400 s à 128 Kio/s | inchangé |
| Service, échéance | 60 s + 210 s ; délai interne des tableurs fixé à 60 s | 270 s pour tout |
| Pages ou diapositives | 500 : un PDF illustré de 541 pages était refusé | 10 000 |
| HTML | aucune limite de balises : un HTML de 50 Mo épuisait la mémoire du travailleur après 22 s | un million de balises, refus en 0,1 à 0,3 s |
| HTML imbriqué | aucune limite : 400 000 `<div>` imbriqués (4,4 Mo) tenaient un travailleur jusqu'à son échéance (77,7 s) ; le nettoyage était quadratique (`Tag.decomposed` cherche dans tout le sous-arbre) | 256 niveaux : refus en 3,6 s ; nettoyage linéaire |
| Word | rien avant mammoth : un tableau de 30 000 lignes (0,8 Mo) passait en 59 s, 40 000 lignes donnaient « HTML trop complexe » après 50 s, plus gros 422 ou mémoire épuisée (1,5 Gio) | 100 000 paragraphes et un million d'éléments comptés avant mammoth : refus en 0,1 à 0,3 s, message Word |
| Délestage | attente = travail restant de toutes les places / 3 : pendant deux documents de 50 Mo, 10 petits textes sur 29 délestés (503), une place libre | simulation de la file, place par place : 0 petit texte délesté (mesures plus bas) |
| Plafond de sortie | 12,5 M caractères, vérifié après le moteur (un texte de 50 Mo : 11,5 s, ou 422 « illisible » quand le travailleur mourait) | idem, plus un refus avant le moteur au-delà de 25 M caractères convertis (1,0 s) |
| Limiteur | estimation 0,05 s + 0,4 s/Mo = 20,1 s, au-dessus de la rafale de 20 s : admis sur un budget plein | inchangé, vérifié |
| Mémoire | 3 travailleurs de 1 280 Mio, file de 1 024 Mio, 100 M caractères de résultats | inchangé ; pics ci-dessous |
| Poste du site | délai 120 s + 12 s par Mio, pas de progression | délai 165 s + taille × (1/131 072 + 2/250 000) s, progression de l'envoi, « en cours » compté depuis la fin de l'envoi ; un élément de 1 Mio au plus sans réponse à temps : « réessayez », plus gros : « découpez » ; la version locale n'est plus conseillée pour un 413 ou un délai |
| MCP, fichier trop gros | `get_anonymized` répétait « envoyez-le avec la commande » après un 413 de Nginx | la réponse en attente rappelle la limite de 50 Mo et dit de ne pas renvoyer le fichier |

**Mesures** (octobre 2026, WSL2, 16 cœurs : le service du dépôt en mode public avec les réglages de `compose.yaml`
dans un cgroup mémoire de 6 Gio, derrière Nginx `stable` dans Docker avec les fichiers de `deploy/server` ; boucle
locale, temps d'envoi exclu ; documents fictifs de `tools/eval/generate.py`, images ou pièces jointes de pixels
aléatoires). Temps vu du client, pic de RSS du travailleur, taille du résultat :

| Format | 50 Mo illustré (≈ 1,24 M caractères) | 50 Mo au plafond (11,2 à 11,7 M caractères) |
|---|---|---|
| PDF | 1,3 s, 322 Mio, 541 pages (avant : 413, plus de 500 pages) | 9,3 s, 604 Mio, 3 377 pages |
| DOCX | 3,4 s, 309 Mio | 5,4 s, 563 Mio |
| PPTX | 1,4 s, 335 Mio, 400 diapositives | 3,8 s, 583 Mio |
| ODT / ODP | 0,6 s, 302 / 298 Mio | 3,3 / 3,1 s, 526 / 528 Mio |
| RTF | 1,0 s, 322 Mio | 4,2 s, 554 Mio |
| EML / MSG (pièces jointes) | 1,5 / 0,5 s, 568 / 316 Mio | 4,3 / 2,9 s, 574 / 553 Mio |

| Format texte | Accepté | Refusé (413, limite nommée) |
|---|---|---|
| TXT, MD | 12 Mio : 2,8 s, 11,3 M caractères | 15 Mio : 3,4 s ; 50 Mio : 1,0 s (avant : 11,5 s, ou 422 pour un TXT) |
| CSV, TSV | 15 Mio : 3,4 s, 11,4 M caractères | 18 Mio : 3,4 s ; 50 Mio : 9 à 10 s (pipeline tableur) |
| XLSX (cellules de texte) | 3,9 Mio : 2,9 s, 11,1 M caractères | 11,9 Mio : 8,7 s ; 15 Mio et plus : 0,2 s (partie XML de plus de 64 Mio) |
| ODS | 5 Mio : 3,0 s, 7,6 M caractères | 20 Mio et plus : 0,1 à 0,2 s |
| HTML (tableaux) | 16 Mio, 954 000 balises : 29,8 s, 763 Mio ; 9,4 Mio, 990 000 balises : 24,5 s, 678 Mio | 20 Mio : 0,1 s (avant : accepté en 38 s à 1 173 Mio) ; 50 Mio : 0,3 s (avant : mémoire épuisée après 22 s) |
| HTML imbriqué | — | 400 000 niveaux (4,4 Mo) : 3,6 s (avant : travailleur tenu jusqu'à l'échéance, 77,7 s) |
| Word (tableaux, passages) | 99 995 cellules (0,39 Mo) : 25,6 s, 498 Mio (par le site 24,2 s ; deux à la fois 27,9 s) ; un paragraphe de 499 000 passages (998 000 éléments) : 23,9 s, 968 Mio | 100 100 cellules : 0,11 s ; 30 000 lignes : 0,17 s (avant : 200 en 59 s) ; 100 000 lignes : 0,18 s (avant : 422 à 71 s) ; 600 000 paragraphes : 0,17 s (avant : 422 à 66,7 s) ; 0,37 Mo portant 60 Mio de XML : 0,2 à 0,4 s (avant : 422 après 40,9 s, place réservée tenue) |

Même issue par le `/v1/` du site, REST et MCP. MCP : le `PUT` lancé avec la commande curl que rend `create_upload`,
puis `get_anonymized` : 31 à 32 pages lues en 0,4 s pour 50 Mo illustrés, 295 pages en 27 s au plafond (au rythme
du seau des requêtes bon marché, 10 par seconde), bien dans les 10 minutes du résultat. 50 Mio + 1 octet : 413
« Fichier trop volumineux : 50 Mo au plus » par tous les chemins, le `PUT` MCP refusé sans lecture en 0,05 s (avant :
0,4 s, après lecture des 50 Mo) ; un `PUT` MCP de 51 Mio, refusé par Nginx : `get_anonymized` répond ensuite
« pending » en rappelant la limite de 50 Mo et en disant de ne pas renvoyer le fichier. Un même client : un PDF de 50 Mo 200 en 1,4 s, aussitôt après 429
`Retry-After: 2`, 2 s plus tard 200. Trois documents de 50 Mo au plafond en même temps, de trois clients : tous 200 en
13,3 s (deux à la fois, une place reste aux petites requêtes), pic du service 1 043 Mio sur 6 Gio. Plus haut pic d'un
travailleur : 921 Mio (un TSV de 50 Mo refusé) ; du service : 1 279 Mio. Les documents les plus lents sous les
limites : le HTML à la limite de balises (30 s), loin de son échéance (127 s), et le tableau Word juste sous les
100 000 paragraphes (25,6 s ; 27,9 s à deux en même temps), sous la moitié de la sienne (61,6 s).

Délestage, mesuré avec une sonde (un petit texte toutes les 0,5 s, chacun d'un client neuf) : pendant deux PDF de
50 Mo au plafond, 27 textes servis sur 27 (avant : 10 délestés sur 29 pendant 5,3 s) ; pendant deux tableaux Word à
la limite et le Word compressé de 60 Mio de XML, 53 sur 53 ; un client lent (un PDF de 12 Mo jusqu'à son échéance,
108,9 s, renvoyé après `Retry-After: 223`) : pendant son second passage, 204 sur 204, aucun délesté (avant : 51 sur
207). Deux de ces PDF en cours, puis un PDF de 50 Mo 25 s plus tard et un texte de 12 Mo 30 s plus tard : les deux
délestés aussitôt (503, `Retry-After` 19 et 23 s), car un travail au-delà de son estimation est supposé durer encore
autant (avant : le PDF admis sur une attente estimée de 6,7 s, puis 84 s d'attente réelle ; le texte délesté avec
`Retry-After: 1`) ; sonde : 206 sur 206.

### Construire et lancer

```bash
docker build -f deploy/Dockerfile -t gdprguardian .        # depuis la racine du dépôt

# Une clé par client (organisation) : seule son empreinte va dans l'environnement.
cle=$(python -c "import secrets; print(secrets.token_urlsafe(32))")      # à remettre au client
printf '%s' "$cle" | sha256sum | cut -d' ' -f1                            # -> GDPRGUARDIAN_API_KEY_SHA256

# Service à clés (mode du service officiel), derrière un proxy qui pose X-GG-Client = adresse du client :
docker run -d --name gdprguardian \
  --read-only --cap-drop ALL --security-opt no-new-privileges \
  --memory 2g --memory-swap 2g --ulimit core=0 --pids-limit 256 \
  --log-driver local --log-opt max-size=10m --log-opt max-file=2 \
  -e GDPRGUARDIAN_API_KEY_SHA256="<empreinte1>,<empreinte2>" -e GDPRGUARDIAN_CLIENT_IP_HEADER=X-GG-Client \
  -e GDPRGUARDIAN_PUBLIC_URL="https://rgpd.example.eu" \
  -e GDPRGUARDIAN_ALLOWED_HOSTS="rgpd.example.eu" \
  -p 127.0.0.1:8000:8000 gdprguardian

# Ou service public, sans clé : -e GDPRGUARDIAN_PUBLIC=1 à la place de GDPRGUARDIAN_API_KEY_SHA256.
```

- `--log-driver local` : journal tourné et borné (le pilote `json-file` par défaut ne tourne jamais).
- **Un processus neuf par requête**, détruit ensuite et jamais réutilisé pour une autre requête ni un autre
  client. Par défaut, autant de travailleurs neufs attendent en réserve que de places (`GDPRGUARDIAN_MAX_CONCURRENCY`) :
  sous Linux ils partagent la mémoire du zygote et ne coûtent chacun que quelques Mo.
- `--pids-limit` : prévoir au moins `3 × GDPRGUARDIAN_MAX_CONCURRENCY + 32` (travailleurs occupés, réserve, zygote,
  fils d'exécution du processus d'accueil).

- `--memory-swap` égal à `--memory` : **pas de swap**, les documents ne quittent jamais la RAM.
- `--ulimit core=0` : **pas de vidage mémoire** (il contiendrait des documents).
- `--read-only` : le service n'écrit rien ; le multipart est lu en mémoire (jamais de fichier temporaire).
- Sans mode choisi (`GDPRGUARDIAN_PUBLIC=1`, `GDPRGUARDIAN_API_KEY_SHA256` ou, en local, `GDPRGUARDIAN_DEV_NO_AUTH=1`),
  le service **refuse de démarrer** (échec fermé). En mode à clés, la clé est vérifiée **avant** toute lecture du
  corps : un client sans clé n'obtient qu'un 401. Une clé en clair dans l'environnement (`GDPRGUARDIAN_API_KEYS`) est
  refusée.
- Les **noms de fichiers ne sont jamais conservés** : seule l'extension sert à choisir le format, et le
  Markdown commence par `# document.pdf` (un nom comme `CV_Jean_Dupont.pdf` est une donnée personnelle).
- Mémoire : chaque requête, règles de l'organisation comprises, tourne dans un processus isolé (2 Gio au plus
  au-delà de son empreinte au repos ; un fichier de 10 Mo en demande 0,3 à 0,6) ; l'accueil ne compile aucun
  motif. Avec `--memory 2g`, fixer `GDPRGUARDIAN_MAX_CONCURRENCY=2` ; le budget
  des requêtes en attente vaut alors 512 Mo (un quart de la limite du conteneur), soit une cinquantaine de
  fichiers de 10 Mo avant le premier 503.

### Sans réseau, pour les plus prudents

La même image anonymise un dossier du poste **sans aucun réseau** (`--network none` : la seule interface est la
boucle locale `lo`, sans aucune route vers l'extérieur), système de fichiers en lecture seule, dossier monté en
lecture seule. Rien n'écoute, rien ne sort : le Markdown anonymisé va sur la sortie standard, un fichier à la fois.

```bash
mkdir -p anonymises
for f in dossiers/*; do
  docker run --rm --network none --read-only --cap-drop ALL --security-opt no-new-privileges \
    -v "$PWD/dossiers:/data:ro" gdprguardian gdprguardian anonymize "/data/$(basename "$f")" \
    > "anonymises/$(basename "$f").md"
done
```

Le serveur MCP local tourne aussi dans ce conteneur : un client MCP (Claude Desktop, VS Code…) le lance avec la
commande `docker` et les arguments `run -i --rm --network none --read-only --cap-drop ALL -v
<dossier>:/data:ro -e GDPRGUARDIAN_ALLOWED_DIRS=/data gdprguardian gdprguardian mcp --stdio` ; les chemins à donner sont
alors ceux du conteneur (`/data/contrat.pdf`).

Vérifié par `tests/test_offline.py` (`GDPRGUARDIAN_OFFLINE_IMAGE=gdprguardian`) : PDF, Word, Excel, CSV, e-mail et HTML
(ses images et feuilles de style distantes ne sont jamais chargées), aucune interface hors `lo` dans le conteneur.
Sans Docker, le même test interdit toute connexion, résolution de nom et tout lancement de programme imprévu au
moteur, aux convertisseurs et au serveur MCP local (`pip install "gdprguardian[local]"`, ou `uvx --offline gdprguardian-mcp@<version>`
après une première installation).

### Noyau Rust : optimisation par profil (PGO)

`tools/pgo.py` construit le noyau en trois temps : noyau instrumenté (`-Cprofile-generate`) ; charge
représentative sur des données **fictives** seulement (les 1 000 documents de `datasets/fr/docs` deux fois en
pays « FR », une fois en « all », un tiers en profil strict avec explications et règles d'organisation, un texte
de 1,9 Mo, un tableau Markdown de 3 000 lignes, des segments de tableur, un CSV et un TSV de 5 000 lignes) ;
fusion des profils par le `llvm-profdata` de la chaîne épinglée, puis construction finale (`-Cprofile-use`). Le
profil ne contient que des compteurs de branches, jamais de texte, et ne quitte pas l'étape de construction.
Chaque variante a son étape (`core-1`, `core-0`) et BuildKit ne construit que celle choisie. Le PGO est
**activé par défaut**. `--build-arg PGO=0` construit le noyau directement : il ne dépend alors que de `rust/` (une
modification du Python ne le reconstruit pas, le corpus n'est pas requis) et la roue est reproductible au bit près.

```bash
docker build -f deploy/Dockerfile -t gdprguardian .                          # noyau PGO (défaut)
docker build -f deploy/Dockerfile --build-arg PGO=0 -t gdprguardian:plain .  # noyau direct, reproductible
rustup component add llvm-tools-preview                                      # en local, une fois
python tools/pgo.py --out dist/                 # roue PGO ; --plain : référence ; --target-cpu : essai
```

Mesures sur le noyau final (octobre 2026, WSL2 Ubuntu 24.04, rustc 1.99.1) : 12 tours entrelacés, processus
épinglé sur un cœur, chaque variante dans un processus neuf. Le tableau donne le rapport des temps PGO / normal
(médiane appariée au sein d'un même tour). Un témoin A/A, deux copies identiques du noyau mesurées de la même façon,
donne l'ampleur du bruit.

| Charge | Temps PGO / normal | Gain | Témoin A/A |
|---|---|---|---|
| 1 000 documents du corpus, pays FR | 0,883 | −11,7 % | 1,023 |
| 1 000 documents du corpus, tous pays | 0,902 | −9,8 % | 0,979 |
| textes hors profil, pays FR | 0,981 | −2 % (dans le bruit) | — |
| textes hors profil, tous pays | 0,945 | −5,5 % | — |

Depuis que toute la détection tourne en Rust (deux appels par document), le PGO pèse nettement plus qu'aux
premières mesures (environ 4 %, quand une part du temps restait en Python) : il est donc **retenu par défaut**.
Le gain est plus faible sur des textes éloignés du corpus de profil, sans jamais devenir une perte.
`-Ctarget-cpu=x86-64-v2` n'apporte rien de mesurable (médiane −0,3 %, 7 tours ; avec PGO, moins bien que PGO
seul) : l'image garde le jeu d'instructions x86-64 de base et tourne sur toute VM x86-64. Un profil dépend
légèrement de l'exécution (tables de hachage à graine aléatoire) : la roue PGO n'est pas identique bit à bit d'une
construction à l'autre, alors qu'avec `PGO=0` la roue ne dépend que de la chaîne épinglée et des sources. Les
roues `gdprguardian-core` destinées à PyPI sont construites sans PGO (sept plateformes, dont certaines en compilation
croisée, où le profil ne peut pas être joué). Image : 103 Mo de contenu (441 Mo sur disque) avec ou sans PGO,
noyau de 3,6 Mo ; construction complète sans cache en 3 min 49 s avec PGO, 2 min 26 s sans (16 cœurs, octobre
2026).

### Variables d'environnement

| Variable | Défaut | Rôle |
|---|---|---|
| `GDPRGUARDIAN_PUBLIC` | 0 | `1` : service public, **aucune authentification** (REST, MCP, envois), limiteur par client. |
| `GDPRGUARDIAN_API_KEY_SHA256` | — | Empreintes SHA-256 (hexadécimal) des clés acceptées, séparées par des virgules ; jamais la clé elle-même. Chaque clé est un principal isolé. Mode du service officiel. `GDPRGUARDIAN_API_KEYS` (clés en clair) est refusé. |
| `GDPRGUARDIAN_CLIENT_IP_HEADER` | — (pair TCP) | En-tête de confiance portant l'adresse du client, posé par le proxy en écrasant toute valeur reçue (production : `X-GG-Client`). Sans lui, une requête vient du serveur lui-même (LOCAL). |
| `GDPRGUARDIAN_LOCAL_TOKEN_SHA256` | — (aucun) | Empreinte SHA-256 du jeton exigé, dans `X-GG-Local`, d'une requête sans en-tête d'adresse pour qu'elle soit LOCAL ; sinon seau commun. Production : créée par `install.sh base` (`/etc/gdprguardian/local.env`, jeton dans `/etc/gdprguardian/local-header`, root 0600). |
| `GDPRGUARDIAN_LIMITS` | `enforce` | Limiteur : `enforce`, `dry-run` (les seaux comptent sans refuser ; requêtes en vol et délestage restent appliqués), `off`. Réglages : `GDPRGUARDIAN_LIMIT_<NOM>` (tableau « Accès par clé »). |
| `GDPRGUARDIAN_PUBLIC_URL` | — | URL publique (`https://…`) utilisée pour les URL d'envoi. **À définir en production.** Active HSTS si https. |
| `GDPRGUARDIAN_ALLOWED_HOSTS` | — | Noms d'hôte acceptés (en-tête `Host`, motifs `*.exemple.eu`) sur **toutes** les routes, contre le DNS rebinding. `localhost`/`127.0.0.1` restent acceptés (sonde). Sans réglage, le contrôle ne s'applique que si le service écoute sur `127.0.0.1`. |
| `GDPRGUARDIAN_MAX_UPLOAD_MB` | 50 | Taille maximale d'un document, en Mio (Nginx : cette taille plus une marge d'au moins 64 Kio pour l'enveloppe multipart, `client_max_body_size 51m`). |
| `GDPRGUARDIAN_MAX_PAGES` | 10 000 | Pages (PDF) ou diapositives (PPTX, ODP) d'un document ; au-delà, 413 nommant la limite. |
| `GDPRGUARDIAN_MAX_TEXT_CHARS` | 1 000 000 | Taille maximale d'un texte (`/v1/anonymize/text`, `anonymize_text`). |
| `GDPRGUARDIAN_UPLOAD_TTL_S` | 300 | Durée de validité d'une URL d'envoi (usage unique), jusqu'au début du `PUT`. |
| `GDPRGUARDIAN_MIN_BODY_RATE_KIB` | 128 | Débit minimal d'un corps, en Kio/s : chaque corps doit arriver en 15 s plus sa taille à ce débit (client trop lent : 408). |
| `GDPRGUARDIAN_RESULT_TTL_S` | 600 | Durée de vie d'un résultat non lu, prolongée par chaque lecture partielle jusqu'à 3 fois cette durée depuis sa publication ; effacé 2 minutes après sa lecture complète. |
| `GDPRGUARDIAN_PAGE_CHARS` | 40 000 | Taille d'une page de résultat (adaptée aux clients MCP). |
| `GDPRGUARDIAN_MAX_ACTIVE_UPLOADS` | 10 | Envois reçus et résultats non lus par client du `PUT` ; envois en attente du fichier par clé ou principal sans réseau. |
| `GDPRGUARDIAN_MAX_UPLOADS_PER_PREFIX` | 40 | Envois en attente par préfixe réseau du créateur (/24, /48), et envois reçus non lus par préfixe du `PUT`. |
| `GDPRGUARDIAN_MAX_PENDING_UPLOADS` | 10 000 | Envois en attente du fichier, pour tout le service (les reçus non lus : 1 000). |
| `GDPRGUARDIAN_MAX_STORE_CHARS` | 200 000 000 | Budget mémoire total des résultats, en caractères ; 1/8 par client du `PUT`, 1/4 par préfixe ; un résultat (texte ou Markdown) n'en dépasse jamais 1/8 (413). |
| `GDPRGUARDIAN_MAX_CONCURRENCY` | CPU utilisables | Travailleurs occupés en même temps, un cœur chacun (affinité et quota cgroup v2 pris en compte, donc `--cpus`). |
| `GDPRGUARDIAN_CONVERSION_TIMEOUT_S` | 60 | Échéance d'une requête : ce délai, plus une seconde par 250 Ko reçus pour l'anonymisation (270 s pour 50 Mio) ; c'est aussi le délai interne des convertisseurs et des tableurs. Au-delà, le travailleur est tué (422 `conversion_timeout` ou `processing_timeout`). |
| `GDPRGUARDIAN_PREWARM_WORKERS` | `GDPRGUARDIAN_MAX_CONCURRENCY` (4 au plus hors Linux) | Travailleurs neufs gardés prêts en réserve (0 = création à la demande). |
| `GDPRGUARDIAN_QUEUE_MB` | un quart de la mémoire (limite cgroup, sinon mémoire physique), 256 au moins, jamais moins que la plus grosse requête | Budget des corps de requêtes tenus en mémoire, en attente ou en cours. Doit contenir la plus grosse requête. Épuisé : 503 + `Retry-After`. |
| `GDPRGUARDIAN_WORKER_MEMORY_MB` | 2048 | Mémoire accordée à un document dans son travailleur, au-delà de l'empreinte au repos. |
| `GDPRGUARDIAN_DOCS` | 0 | `1` publie `/docs` et `/openapi.json`. |
| `GDPRGUARDIAN_DEV_NO_AUTH` | 0 | `1` : **aucune authentification**, refusé hors `127.0.0.1`. Usage local uniquement. |
| `GDPRGUARDIAN_USAGE_SOCKET` | — (désactivé) | Socket Unix en datagrammes du compteur d'usage de la page publique (production : `/run/gdprguardian-stats/usage.sock`). Chemin absolu de 107 octets au plus. Un datagramme de métadonnées par anonymisation, voir « Compteur d'usage » ci-dessous. |

Lues au démarrage, ces variables sont retirées de l'environnement avant le lancement du zygote (avec
`gdprguardian serve`, `gdprguardian mcp` ou `uvicorn --factory gdprguardian.server:create_app`) : aucun travailleur
ne les voit, clés comprises. Seul `GDPRGUARDIAN_PURE_PYTHON=1` (moteur Python seul, la référence) reste transmis
aux travailleurs, qui le lisent à leur démarrage.

Rotation des clés (mode à clés) : ajouter l'empreinte de la nouvelle clé, redémarrer (en conteneur : le recréer),
migrer les clients, retirer l'ancienne empreinte. Révocation : retirer l'empreinte, puis recréer le conteneur.

### Compteur d'usage (page publique)

Avec `GDPRGUARDIAN_USAGE_SOCKET`, le processus d'accueil envoie à la fin de chaque anonymisation, réussie ou non,
un datagramme JSON d'au plus 256 octets sur ce socket Unix local :

```json
{"v":1,"kind":"upload","fmt":"pdf","bytes":20480,"ms":6,"ok":true,"src":"public"}
```

| Champ | Contenu |
|---|---|
| `v` | `1`, version du format. |
| `kind` | Origine : `text` (`/v1/anonymize/text`, `/v1/detect`), `file` (`/v1/anonymize/file`), `upload` (envoi hors bande REST, compté au `PUT`), `mcp_text` (outil `anonymize_text`), `mcp_file` (document reçu par MCP : `create_upload` puis `PUT`, ou `anonymize_file`). |
| `fmt` | `text`, `pdf`, `docx`, `doc`, `xlsx`, `xls`, `pptx`, `odt`, `ods`, `odp`, `rtf`, `eml`, `msg`, `html`, `csv`, `tsv`, `md` ou `other`. Réussite : le format détecté (`.xlsm` et `.xlsb` comptent pour `xlsx`) ; échec : celui de l'extension déclarée ; texte : `text`. |
| `bytes` | Taille reçue, en octets (texte en UTF-8, fichier tel quel), 256 Mio au plus. |
| `ms` | Durée du traitement en millisecondes, entière, attente d'un travailleur comprise, une heure au plus. |
| `ok` | `true` si l'anonymisation a réussi ; `false` sinon (document refusé, règles refusées, échéance, service saturé, client parti). |
| `src` | `public` pour le trafic normal ; `protocol` pour une requête du serveur lui-même (arrivée sur le socket sans en-tête d'adresse, avec le jeton local s'il est configuré : protocole de mesure lancé sur le serveur, contrôles de `install.sh verify`). Le démon accepte aussi un datagramme sans ce champ (`public`). |

**Jamais envoyé** : ni contenu, ni nom de fichier, ni adresse IP, ni clé, ni principal, ni identifiant d'envoi ou
de résultat, ni jeton. Chaque champ est un nombre, un booléen ou une valeur d'un ensemble fermé : rien de ce que
le client envoie ne peut y passer. Une requête refusée à l'entrée (authentification, débit, option invalide,
corps trop gros ou mal formé) n'est pas une anonymisation et n'envoie rien ; créer un envoi ou lire un résultat
non plus.

**Seul le processus d'accueil compte, et le démon du site le vérifie.** Sous Linux, son socket prend dès le
démarrage, avant tout travailleur, le nom abstrait `gdprguardian-usage:<chemin du socket>` (107 octets au plus) et
le garde ; le démon ignore tout datagramme venu d'un autre nom. Les travailleurs ont le même utilisateur et voient
le même dossier, mais le noyau refuse un second détenteur du nom : un travailleur, même compromis par un document
piégé, ne peut ni compter de faux documents ni faire passer quoi que ce soit par les chiffres publiés. Le démon
refuse aussi toute valeur hors bornes et arrondit les tailles publiées à la précision affichée (« 12,4 Mo »).

Envoi sans attente : socket non bloquant, ouvert dans le seul processus d'accueil, jamais hérité. Démon absent,
file pleine ou droit refusé : la statistique est perdue, sans erreur ni journal, et la requête n'est jamais
ralentie. Variable absente ou vide : compteur désactivé. Sous Windows (pas de socket Unix en datagrammes), le
compteur ne fait rien. Le serveur MCP local (`gdprguardian mcp --stdio`) ne lit pas cette variable : rien ne
quitte le poste. En conteneur, monter le dossier du socket **au même chemin**
(`-v /run/gdprguardian-stats:/run/gdprguardian-stats` : le nom attendu en dépend) et permettre à l'utilisateur du
service d'écrire sur le socket ; un socket Unix ne passe pas par le réseau, le conteneur reste sans réseau
(`--network none`).

### Codes d'erreur

Toute erreur a la forme `{"error": {"code": "…", "message": "…"}}` : code stable, message fixe (en français et
en anglais ; en anglais seul pour `not_found` et `method_not_allowed` d'une route inconnue), jamais un extrait du
contenu ; un 422 de validation liste aussi les noms des champs (`fields`) ; un refus temporaire ajoute
`retry_after_s`. Les outils MCP renvoient `code: message` (avec `retry_after_s=N` pour un refus temporaire) ; un refus
de la porte d'entrée sur `/mcp` arrive en erreur JSON-RPC (voir « Réponses »).

| HTTP | `code` | Cause | Que faire |
|---|---|---|---|
| 400 | `invalid_request` | en-tête `Content-Length` invalide | corriger la requête |
| 401 | `unauthorized` | mode à clés seulement : clé d'API absente ou invalide | vérifier la clé |
| 403 | `cross_site_request` | requête envoyée par un navigateur depuis une autre page (`Sec-Fetch-Site`) | appeler depuis un script, un agent ou le cockpit |
| 404 | `not_found`, `upload_used`, `page_not_found`, `already_read`, `expired`, `deleted` | envoi ou résultat faux, d'une autre clé (`not_found`) ; URL d'envoi déjà utilisée (`upload_used`, pour son seul détenteur) ; résultat lu puis effacé, expiré ou supprimé (motif distinct, pour le seul détenteur de l'identifiant) ; page inexistante | recréer l'envoi (`create_upload` ou `POST /v1/uploads`) |
| 405 | `method_not_allowed` | méthode non prise en charge | — |
| 408 | `upload_timeout` | corps reçu trop lentement (15 s plus sa taille à `GDPRGUARDIAN_MIN_BODY_RATE_KIB`) | réessayer une fois ; avec une URL d'envoi, en demander une nouvelle (elle ne sert qu'une fois) |
| 413 | `payload_too_large`, `document_too_large` | au-delà d'une limite, que le message nomme : fichier de plus de 50 Mo, texte de plus d'un million de caractères, résultat de plus de 12,5 millions de caractères, plus de 10 000 pages ou diapositives, plus d'un million de balises HTML ou de 256 niveaux d'imbrication, plus de 100 000 paragraphes Word ou d'un million d'éléments, mémoire du travailleur épuisée (voir « Gros documents ») | découper le document ; `gdprguardian anonymize` (ligne de commande locale) n'a pas le plafond de résultat, mais garde 50 Mo par fichier, 500 pages et 60 s |
| 415 | `unsupported_format` | format de document non pris en charge | exporter en PDF ou DOCX |
| 421 | `misdirected_request` | nom d'hôte non autorisé (`GDPRGUARDIAN_ALLOWED_HOSTS`) | corriger l'hôte |
| 422 | `invalid_request`, `invalid_text`, `upload_interrupted`, `too_many_page_sizes` | champ ou option invalide (noms des champs seuls), règle de l'organisation refusée par le moteur linéaire (numéro, libellé et raison ; pour un envoi hors bande, dès sa création), texte à substitut UTF-16 isolé, envoi interrompu, trop de tailles de page | corriger la requête |
| 422 | `rules_too_costly` | travailleur arrêté pendant un texte traité avec des règles de l'organisation (filet de sécurité derrière le budget de compilation) | simplifier les règles |
| 422 | `document_error`, `encrypted_document`, `malicious_document` | document illisible, chiffré, refusé par les contrôles | fournir une copie lisible |
| 422 | `conversion_timeout` | document au-delà de son échéance (conversion + anonymisation) | découper le document |
| 422 | `processing_timeout` | texte au-delà de son échéance d'anonymisation | découper le texte |
| 429 | `rate_limited`, `too_many_active_uploads`, `too_many_unread_results` | budget du client ou de son réseau dépassé (requêtes, coût, requêtes simultanées), au service ou au bord Nginx ; trop d'envois en cours ; résultats non lus trop volumineux ; `Retry-After`, `RateLimit` | attendre `Retry-After`, lire, supprimer ou laisser expirer les résultats |
| 500 | `internal_error` | défaut du service ou du travailleur (journalisé sans contenu) | signaler |
| 501 | `converter_unavailable` | convertisseur absent pour ce format | exporter en PDF ou DOCX |
| 503 | `service_busy` | attente estimée au-delà de 10 s (délestage), budget mémoire épuisé, dépôt des résultats plein, travailleur impossible à démarrer, service injoignable derrière Nginx ; `Retry-After` | réessayer après le délai |

Une échéance dépassée donne la même réponse au prochain essai : 422, jamais 5xx.

### Terminaison TLS (proxy inverse)

Placer un proxy (Caddy, nginx, Traefik, HAProxy) **hébergé chez vous ou chez l'hébergeur européen**,
jamais un CDN qui déchiffre le trafic hors UE. Points de configuration indispensables :

- **Aucun corps de requête ni de réponse dans les journaux**, WAF et APM compris.
- **Le jeton d'envoi est dans le chemin** (`PUT /v1/uploads/{jeton}`) : retirer `$request`/`$request_uri`
  des formats de journal du proxy, ou journaliser seulement la méthode et le code de statut.
- Taille maximale du corps alignée sur `GDPRGUARDIAN_MAX_UPLOAD_MB`, plus une marge d'au moins 64 Kio pour
  l'enveloppe multipart (`51m` pour 50 Mio) ; réponse
  attendue au moins deux échéances du plus gros document (2 × 270 s pour 50 Mio : `proxy_read_timeout 600s`).
- nginx : `proxy_request_buffering off;` sinon les gros corps sont **écrits sur disque** par nginx.
- `GDPRGUARDIAN_PUBLIC_URL` défini : les URL renvoyées ne dépendent pas des en-têtes `X-Forwarded-*`.
- Si le proxy transmet l'hôte d'origine (`proxy_set_header Host $host;`) à un service qui écoute sur
  `127.0.0.1`, déclarer ce nom dans `GDPRGUARDIAN_ALLOWED_HOSTS`, sinon la réponse est 421.
- Limites par client : le proxy pose l'adresse du client dans l'en-tête nommé par `GDPRGUARDIAN_CLIENT_IP_HEADER`
  (`proxy_set_header X-GG-Client $remote_addr;`, qui écrase toute valeur envoyée par le client), et
  `proxy_redirect http:// https://;` (aucune redirection vers http://).

Exemple nginx (1.25.1 ou plus récent) :

```nginx
# Contexte http : dès le niveau crit, le journal d'erreurs de nginx cite l'IP complète et la requête (jeton
# compris) ; son format ne se change pas, seul son niveau : emerg n'en cite jamais (le redire dans chaque server,
# serveur par défaut compris, et pour error_log de nginx.conf). http context: from crit on, nginx's error log quotes
# the full IP and the request; only its level changes: emerg never quotes them (repeat it in every server).
error_log /var/log/nginx/error.log emerg;
log_format gdprguardian '$time_iso8601 $request_method $status $body_bytes_sent $request_time';
server {
    listen 443 ssl;
    http2 on;
    server_name rgpd.example.eu;
    access_log /var/log/nginx/gdprguardian.log gdprguardian;   # sans IP, sans URL, sans corps
    client_max_body_size 51m;
    client_body_temp_path /run/nginx-body 1 2;         # sur tmpfs : filet de sécurité / on tmpfs: backstop
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;                        # sans lui, un envoi « chunked » passe par le disque
        proxy_set_header X-GG-Client $remote_addr;     # limites par client : adresse du client, écrasée ici
        proxy_redirect http:// https://;
        proxy_request_buffering off;
        proxy_buffering off;
        proxy_read_timeout 600s;                       # deux échéances d'un document de 50 Mio / two deadlines
    }
}
```

`proxy_request_buffering off` ne tient qu'avec un amont HTTP/1.1 : sans `proxy_http_version 1.1`, nginx écrit
les envois « chunked » sur disque.

### Serveur dédié : l'installation du service officiel (`deploy/server/`)

Le service de `api.gdprguardian.com` et `api.gardienrgpd.fr` et le site (`gardienrgpd.fr`, `gdprguardian.com`)
sont installés par `deploy/server/install.sh`, sur un serveur Ubuntu déjà durci (pare-feu, fail2ban, mises à jour
automatiques, aucun vidage mémoire), en sept phases idempotentes : `base`, `image <archive>`, `cert`, `https`,
`site <binaire> <vidéos>`, `start`, `verify`. Mise à jour d'un serveur en place : `site <binaire> <vidéos>`, `base`,
`image <archive>`, `start`, `verify` (le démon du site d'abord : la configuration de Nginx installée par `base`
pointe vers lui). `<vidéos>` : un dossier qui contient les fichiers de `video/out` du dépôt (par défaut
`../../video/out` depuis `install.sh`, quand il est lancé d'une copie du dépôt).

- **Service à clés** (`compose.yaml`, depuis le 27 octobre 2026) : plus de `GDPRGUARDIAN_PUBLIC`,
  `GDPRGUARDIAN_CLIENT_IP_HEADER=X-GG-Client` ; les empreintes `GDPRGUARDIAN_API_KEY_SHA256`, une clé par organisation,
  sont dans `/etc/gdprguardian/gdprguardian.env`, jamais une clé en clair ; `base` retire la ligne
  `GDPRGUARDIAN_API_KEYS` d'un ancien fichier de réglages. Mémoire : 3 travailleurs de 1 280 Mio, file de 1 024 Mio
  (corps et sorties des travailleurs), 100 millions de caractères de résultats, 12,5 millions par résultat au plus (environ 5,5 Gio sous les 6 Gio du
  conteneur) ; chaque travailleur est la victime préférée du tueur OOM (`oom_score_adj` 1000) : une saturation coûte
  une requête, jamais le service. Journal au niveau `warning` : aucun événement par requête ni par document.
- **Jeton local** : `base` crée `/etc/gdprguardian/local-header` (l'en-tête `X-GG-Local` prêt pour `curl -H @…`) et
  `/etc/gdprguardian/local.env` (son empreinte, lue par le conteneur), root 0600, sans jamais passer le jeton en
  argument de commande. Seules les requêtes du serveur qui le présentent sur le socket sont LOCAL (sonde, `verify`,
  protocole de mesure) ; un travailleur compromis qui joint le socket tombe dans le seau commun.
- **Conteneur sans réseau** (`network_mode: none`) : `gdprguardian serve --uds /run/gdprguardian/app.sock`
  n'écoute que sur un socket Unix, dans un **tmpfs dédié de 64 Kio** (`run-gdprguardian.mount`, monté avant Docker)
  lisible par nginx seul : le conteneur ne peut ni remplir le `/run` de l'hôte ni y viser un autre socket. Le service
  ne peut ni être joint directement ni appeler l'extérieur.
- Conteneur en lecture seule, `/tmp` en mémoire, sans privilège ni capacité, mémoire sans swap, pas de vidage
  mémoire, nombre de processus borné, utilisateur 10001, **sans init** (le service durci est le PID 1),
  `pull_policy: never` ; `image` et `start` vérifient que l'image attendue par `compose.yaml` est chargée, `start`
  recrée le conteneur et exige la bonne version sur `/health`.
- **Sonde de santé côté hôte** : `gdprguardian-watchdog.timer` interroge `/health/deep` par le socket toutes les
  2 minutes (jeton local : hors des limites) : un travail minuscule dans un vrai travailleur, hors file et hors
  compteur d'usage, si bien qu'une réserve de travailleurs cassée (zygote, processus épuisés) est vue, pas seulement
  la boucle d'événements. Trois échecs : redémarrage du conteneur ; aucune commande n'est lancée dedans.
  `/health/deep` n'existe pas pour une autre requête (404).
- **Mises à jour automatiques** (`install.sh updates`, heure de Paris) : la sécurité chaque nuit à 2 h (1 h 45 le
  lundi), avec redémarrage aussitôt si elle l'exige ; les correctifs stables d'Ubuntu (`-updates` : docker.io, nginx…)
  le samedi à 2 h, même règle ; un redémarrage chaque lundi à 2 h, une fois toute mise à jour en cours terminée
  (jamais au milieu de dpkg). Après un redémarrage, Docker relance le conteneur (`unless-stopped`) et systemd le
  démon du site, Nginx et les sondes. `verify` contrôle que le passage de chaque nuit ne prend que la sécurité et que
  les minuteries sont actives.
- **nginx** : configuration principale dédiée (`nginx-main.conf`, lue par `nginx -c` via
  `nginx.service.d/gdprguardian.conf`) ; le `nginx.conf` du paquet est rétabli s'il avait été modifié, pour que les
  mises à jour automatiques de Nginx ne bloquent jamais. Chaque fichier est sauvegardé, testé et rétabli en cas
  d'échec. TLS 1.2 et 1.3 (certificat Let's Encrypt ECDSA, renouvelé seul ; `cert` ne retire jamais un nom), nom
  TLS inconnu refusé dès la poignée de main, Host inconnu fermé (444), HTTP des noms api.* réduit au défi ACME (444
  sinon, aucune redirection), HTTP des sites : pages redirigées, `/v1/` et `/mcp` fermés (444), `server_tokens off`
  dans chaque server, corps transmis sans tampon et fichiers temporaires en mémoire, **aucun journal d'accès**,
  journal d'erreurs au seul niveau `emerg` (jamais d'adresse ; `base` vide les journaux écrits avant), en-têtes de
  sécurité et erreurs JSON aussi sur les réponses que Nginx produit lui-même, `X-GG-Client = $remote_addr` et
  `X-GG-Local` effacé vers le service, requêtes inter-sites refusées (403), limites du bord (ci-dessus), jamais en
  swap (`MemorySwapMax=0`). `base` coupe aussi le journal du pare-feu (`ufw logging off`) et vide `ufw.log`.
- **Site** : démon Rust `gdprguardian-site` (`site/`, unité systemd sans réseau), ni cookie ni journal ; Nginx lui
  passe l'adresse tronquée (/24, /48) pour compter les visiteurs du jour, et le service lui envoie ses comptes
  d'usage (ci-dessus). Le cockpit du site appelle `/v1/` **sur la même origine** : Nginx le renvoie au service comme
  depuis api.* (Host réécrit, adresse du client posée, mêmes limites et en-têtes).
- **Vidéo de lancement** (`/media/`, panneau `#video` des deux sites) : servie par Nginx, pas par le démon (qui
  embarque ses fichiers dans son binaire et ne sert pas de plages d'octets, que Safari exige pour une vidéo) : plages
  (206), ETag, `sendfile`. Liste fermée de 8 fichiers (`$gdprguardian_media` dans `nginx-http.conf`, `MEDIA_FILES`
  dans `install.sh`), tout autre nom 404 ; types fixés (`video/mp4`, `image/png`, `text/plain; charset=utf-8`) ;
  mêmes en-têtes de sécurité que le démon, sa CSP comprise (`media-src 'self'`) ; `Cache-Control: public,
  max-age=31536000, immutable` sur les seules réponses réussies, car les pages citent chaque fichier avec son
  empreinte (`?v=`). `site <binaire> <vidéos>` vérifie avant tout changement que chaque lien des pages du binaire
  désigne un fichier fourni de même empreinte (SHA-256), puis copie les fichiers changés dans
  `/var/www/gdprguardian-media` (nom temporaire puis renommage ; tout autre fichier retiré). Un binaire d'avant la
  vidéo (retour en arrière) laisse `/media/` tel quel.
- **Réglages** : `/etc/gdprguardian/gdprguardian.env` (root, 0600) : empreintes `GDPRGUARDIAN_API_KEY_SHA256`
  (séparées par des virgules), mode du limiteur et `GDPRGUARDIAN_LIMIT_*` au besoin, jamais de clé en clair. Nouvelle
  clé ou révocation : ajouter ou retirer l'empreinte, puis `install.sh start` (qui recrée le conteneur).
- `verify`, qui attend encore le mode public (ses contrôles passent sans clé) et reste **à adapter** au service à
  clés, échoue au premier défaut : écoutes, version, jeton local configuré, Nginx hors swap et pare-feu sans
  journal, passage par Nginx jusqu'au service sans clé (corps de 10 octets et de 2 Mo refusés par le service après
  lecture : rien d'anonymisé, donc rien de compté comme trafic public ; MCP `initialize`), en-têtes, aucune
  redirection, refus inter-sites, puis par le socket avec le jeton local (comptés « protocol ») : anonymisation, envoi
  de 2 Mo aller et retour, sonde profonde ; cockpit (`/v1/` même origine, refus inter-sites, HTTP clair fermé), flux
  du site, vidéo (une plage d'octets de chaque fichier sur chaque site : 206, type, en-têtes, cache ; nom inconnu :
  404), Host et SNI inconnus refusés, 429 sous une rafale d'une adresse, aucun cookie, aucune adresse dans les
  journaux de Nginx, aucune erreur interne du limiteur, sonde active.
- Mise à jour : `install.sh image <archive>` puis `install.sh start` (voir [`docs/PUBLISHING.md`](../docs/PUBLISHING.md)).

### Hébergement dans l'UE

- Hébergeur européen **sans société mère ni présence aux États-Unis** (portée du CLOUD Act) ; offre
  qualifiée SecNumCloud pour le secteur public et les données sensibles.
- Les adresses IP sont des données personnelles : **ni Gardien RGPD ni la configuration ci-dessus n'en
  journalisent**. La lutte contre les abus ne les voit qu'en mémoire : zones de limite de Nginx et pseudonyme du
  service (secret renouvelé toutes les 24 h, rien sur disque), sur la base de l'intérêt légitime (art. 6.1.f,
  considérant 49) et de l'art. 32 ; voir « Accès par clé » ci-dessus.
- Le service hébergé agit comme **sous-traitant (art. 28 RGPD)** pour les contenus : chaque clé est remise avec un
  accord de sous-traitance ; publier la liste des sous-traitants ultérieurs (voir `docs/PLAN.md`, §13).
- Données de santé : préférer l'édition auto-hébergée tant que la question HDS n'est pas tranchée.

### Effacement et isolation : ce que garantit le code, ce que doit garantir l'hôte

Le code garantit :
- un processus neuf par requête (règles de l'organisation, conversion et anonymisation), jamais réutilisé, tué
  après sa réponse, mort avec le service ; le processus d'accueil ne lit, ne compile ni n'anonymise jamais un
  contenu ;
- dans ce processus, avant tout document : sorties standard vers `/dev/null`, aucune variable `GDPRGUARDIAN_*`
  (hormis l'interrupteur `GDPRGUARDIAN_PURE_PYTHON`), et sous Linux processus non lisible (`PR_SET_DUMPABLE=0` : ni
  `/proc/<pid>/mem`, ni `environ`, ni `ptrace`), sans core dump, sans droit de créer un processus, sans canal
  vers le zygote ;
- le service lui-même : réglages et clés retirés de l'environnement une fois lus, avant tout processus enfant
  (`gdprguardian serve`, `gdprguardian mcp`, `uvicorn --factory`), non lisible, sans core dump ;
- aucun cache partagé de contenu (pas même des numéros de téléphone), aucune mesure interne renvoyée aux
  clients, aucune erreur qui retienne le document ;
- résultats en mémoire 10 minutes au plus, effacés dès la lecture complète ; rien sur disque.

Python ne peut pas effacer une chaîne immuable : la garantie forte est la **fin du processus**. L'hôte doit
donc fournir :
- aucune sortie réseau pour le conteneur hors du proxy (un convertisseur exploité ne peut rien exfiltrer) ;
- pas de swap (`--memory-swap` = `--memory`, swap de l'hôte coupé ou chiffré), pas de core dump
  (`fs.suid_dumpable=0`, `core_pattern` qui ne passe pas par `systemd-coredump`), pas de kdump, pas
  d'hibernation, pas d'instantané mémoire de la VM ;
- `kernel.yama.ptrace_scope>=1`, `--cap-drop ALL`, `no-new-privileges`, système de fichiers en lecture seule ;
- de préférence `init_on_free=1` (pages libérées remises à zéro) ;
- pour se protéger de l'hébergeur lui-même : une VM confidentielle (AMD SEV-SNP, Intel TDX). Sans elle,
  la garantie vis-à-vis de l'hébergeur est contractuelle (art. 28 RGPD), pas technique.

### Exploitation

- **Un seul processus d'accueil par instance** (les travailleurs sont ses enfants) : les résultats et l'état du
  limiteur vivent dans la mémoire du processus qui a reçu la requête. Pour plusieurs instances, router de façon
  stable (par adresse du client, ou par l'identifiant d'envoi pour `/v1/uploads/…` et `/v1/results/…`) ; ne pas
  lancer plusieurs workers uvicorn dans un même conteneur.
- Journaux : **aucun journal d'accès ni d'activité au niveau par défaut de production** (`--log-level warning`) :
  seuls les avertissements et erreurs (réponse 5xx, erreur interne du limiteur, sonde profonde en échec). En
  développement (`--log-level debug`), chaque traitement indique le PID de son travailleur (`worker=…`) et son
  attente (`wait_ms=…`) ; un refus d'admission donne `event=service_busy`, un client parti `event=request_abandoned`,
  un contenu refusé `event=document_rejected` ou `event=text_rejected` avec son `code` (`code=invalid_rules` pour
  des règles refusées : ni motif ni raison au journal, un motif peut contenir un nom).
- Sonde : `GET /health` (sans authentification, sans donnée) ; `GET /health/deep` pour le serveur lui-même (un vrai
  travailleur) ; état agrégé : `GET /status` (places, file, attente estimée, compteurs du limiteur ; rien d'un
  client).
- Journaux : une ligne par événement, métadonnées seulement (`event=request route=/v1/uploads/{token}
  status=503 ms=12.3`). Aucune valeur, aucun nom de fichier, aucun jeton, aucune clé, aucune adresse.
- MCP : `https://rgpd.example.eu/mcp`, HTTP « streamable » sans état ; mode à clés (le service officiel) :
  `Authorization: Bearer <clé>` ; service public : sans en-tête.
- Builds reproductibles : `uv export --frozen --no-dev --extra office --extra phone --extra api --extra mcp
  --no-emit-project > requirements.lock`, puis `pip install --require-hashes -r requirements.lock` et
  `pip install --no-deps .` dans l'étape de construction.

## English

The service runs the REST API (`/v1/...`) and the online MCP server (`/mcp`) in **one front process**.
Everything is processed **in memory**: no temporary file, no database, no content in logs. The official service is
**reserved for API key holders** (one per organisation, given on request with a data processing agreement, GDPR
art. 28); an in-memory per-client limiter contains abuse (see "Key access" below).

### One request, one process

Every request (text or document, REST or MCP, out-of-band upload) is processed **end to end** (organisation
rules compiled, conversion, anonymisation, placeholder scope) in a **single-use isolated process**, destroyed
after its reply. The front process only does HTTP, admission, scheduling and the result store: it never parses,
compiles nor anonymises content, and only checks the structure of organisation rules (count, lengths, labels),
so its footprint does not depend on the rules it receives.

- **Linux**: a *zygote* is started at boot, hardened, then preloaded once (packs, keyword automata, Rust core,
  name lexicon, converters, default engines). Every worker is forked from it in milliseconds and shares its
  memory copy-on-write; the zygote never sees a document and kills its own children. A reserve of pristine
  workers (`GDPRGUARDIAN_PREWARM_WORKERS`) awaits requests, so a request only pays the exchange. Measured (16
  cores): a 2 KB text end to end **p50 7.5 ms, p95 9.2 ms**; about 300 2 KB texts per second with 8 workers;
  100 simultaneous 10 MB PDFs all processed (17.5 s with 4 workers).
- **Windows, macOS**: every worker is a fresh interpreter ("spawn", ~1.5 s of CPU); the reserve hides that cost
  for spaced requests (p50 12 ms), but sustained throughput tops out at a few requests per second. Workstation
  use; run Linux in production.
- Every worker, before any document: standard streams to `/dev/null`, no `GDPRGUARDIAN_*` variable (the front
  removes them from its environment before starting the zygote: no key nor setting, even in the initial
  environment block; only the engine switch `GDPRGUARDIAN_PURE_PYTHON` is passed on), non-dumpable, no core dump, no
  right to create processes, capped memory (`GDPRGUARDIAN_WORKER_MEMORY_MB` on top of its idle footprint), killed at
  the deadline, no channel back to the zygote. Replies are checked JSON plus UTF-8 text, never pickle.
- **Organisation rules** (`rules`): compiled in the request's worker, before any content, on one thread and under
  a budget (2 MB per pattern, 16 MB per set); beyond it, or outside the linear-time engine's exact forms, the rule
  is refused before allocating: 422 `invalid_request` with the engine's reason (see `docs/REGLES.md`). For an
  out-of-band upload, `POST /v1/uploads` (and `create_upload`) compiles the patterns in a worker before the file
  leaves: the 422 comes at upload creation. A worker that dies while a text is processed with rules
  gives 422 `rules_too_costly` (safety net behind the budget), never 5xx. Since 1.0.2 every letter-and-digit code
  of 6 characters or more and every bare run of 8 digits or more is masked by default; an organisation keeps codes
  of a precise structure readable with a `keep` rule, which wins over the code rule, long numbers and value
  propagation: `{"rules": [{"label": "SKU", "pattern": "SKU-[0-9]{6}", "action": "keep"}]}` keeps `SKU-123456`
  while `CLT-204518` is masked (`docs/REGLES.md` § 3).
- **Admission**: every request carrying content reserves its size (`Content-Length`) **before** its body is
  read, in a memory budget (`GDPRGUARDIAN_QUEUE_MB`). A key beyond its fair share cannot take the last quarter of
  the budget, kept for other keys. Admitted requests wait for a free worker: a freed slot goes to the waiting
  key holding the fewest slots, then to the one waiting the longest (since its arrival or the end of its last
  job; arrival order within a key), so a newly arrived key goes before a key flooding the service and waits
  **at most one slot release** (behind only the keys that arrived before it); no key is starved. The service
  answers `503` (with `Retry-After`) only when the budget is
  exhausted; a client sending `Expect: 100-continue` (curl, above 1 MB) is refused before sending its body. A
  client that disconnects while a synchronous request waits or runs frees its place: its worker is killed.
- **Out-of-band upload**: a received file never expires while it waits for its worker, however long the queue;
  its processing delay starts when the worker is granted.
- **Errors**: stable codes, fixed messages, never content (table above; bilingual, except the English-only
  `not_found` and `method_not_allowed` of an unknown route). A request past its deadline gets 422
  `conversion_timeout` (document) or 422 `processing_timeout` (text): retrying gives the same outcome, so never
  5xx. A refused organisation rule gets 422 `invalid_request` whose message carries the rule number, label and
  the engine's reason (never document content); `rules_too_costly` (422) covers a worker dying on a text
  processed with rules.
- New variables: `GDPRGUARDIAN_QUEUE_MB` (default: a quarter of the cgroup memory limit, else of physical memory,
  at least 256 and never below the largest request), `GDPRGUARDIAN_WORKER_MEMORY_MB` (2048). `GDPRGUARDIAN_PREWARM_WORKERS` now sizes the reserve
  (default `GDPRGUARDIAN_MAX_CONCURRENCY`, at most 4 outside Linux). `GDPRGUARDIAN_CONVERSION_TIMEOUT_S` bounds a whole
  request: that delay plus one second per 250 KB received. Plan `--pids-limit` ≥ `3 × concurrency + 32` (busy
  workers, reserve, zygote, front-process threads).

### Key access, per-client limits, isolated results

**Keyed mode**, the official service's: REST, MCP, out-of-band uploads and the site's cockpit require the
`Authorization: Bearer <key>` header (the only one accepted); without a valid key, 401 before any body is read. Keys
are given **only as SHA-256 digests** (`GDPRGUARDIAN_API_KEY_SHA256`, computed with `printf '%s' "$key" | sha256sum`):
a plaintext key in the environment would be readable through `/proc/<pid>/environ`, so `GDPRGUARDIAN_API_KEYS` is
refused at start-up. Every key is an isolated principal (its uploads stay bound to it). `GDPRGUARDIAN_PUBLIC=1`
(another deployment): **no authentication**; a valid key gets its own principal there, a missing, wrong or old key
is ignored.

**Client identity, keeping nothing.** Nginx sets `X-GG-Client = $remote_addr`, overwriting any value the client sent;
the service only reads that header when `GDPRGUARDIAN_CLIENT_IP_HEADER` names it (otherwise it takes the TCP peer
address, never a header). The address becomes a **pseudonym** at once: the first 8 bytes of HMAC-SHA256(secret,
prefix), with a 32-byte secret drawn at start-up, kept in memory only, renewed every 24 h (the previous one is still
recognised for 10 minutes so a client's state survives the switch). Two tiers: IPv4 /32 and /24, IPv6 /64 and /48
(an IPv4-mapped address counts as IPv4). The header is removed from the request as soon as it is read: the address
reaches no route, no MCP tool, no log, no usage datagram, no error message and no response. A request reaching the
socket **without** that header comes from the server itself (health probe, measurement protocol): the **LOCAL**
principal, outside the per-client budgets but limited to two jobs at once and never on the slot reserved for small
requests; its usage datagrams carry `"src":"protocol"`. With `GDPRGUARDIAN_LOCAL_TOKEN_SHA256` (the official service:
`install.sh base` creates the token), it must also present the local token in `X-GG-Local`:
`curl -H @/etc/gdprguardian/local-header --unix-socket /run/gdprguardian/app.sock …` (root 0600 file, never a command
argument). Without it, the request lands in the shared bucket of unreadable addresses: a compromised worker, which
reaches the same socket, passes neither for the server nor for the protocol. Nginx clears `X-GG-Local`; a public
protocol run launched on the server therefore goes through the socket with that file.

**Limiter** (`server/limiter.py`, memory only, decided **before any body is read**), settings
`GDPRGUARDIAN_LIMIT_<NAME>`:

| Layer | Default | Setting |
|---|---|---|
| Cheap requests (health, `/status`, packs, results, upload creation, every MCP message) | 10 per second, burst 30, per client | `CHEAP_RATE`, `CHEAP_BURST` |
| Cost of content requests (text, file, upload, MCP) in worker-seconds (variable-cost GCRA) | refill 0.5 s per second, burst 20 s, per client; debt down to the longest job's deadline (60 s + 4 s/MB: about 270 s for 50 MB) | `COST_RATE`, `COST_BURST`, `COST_DEBT` (floor) |
| Prefix tier (IPv4 /24, IPv6 /48) | 2 times a client's budget | `PREFIX_FACTOR` |
| Estimate before reading (`Content-Length`; chunked body: the route's cap) | text 0.005 s + 0.15 s/MB; file 0.05 s + 0.4 s/MB; at least 0.005 s; multiplied by the observed slowness of the client or its prefix (moving average of measured / estimate, 1 to 100) | `TEXT_BASE_S`, `TEXT_PER_MB_S`, `FILE_BASE_S`, `FILE_PER_MB_S`, `FLOOR_S`, `MAX_SLOWNESS` |
| True-up | measured worker time (slot occupancy, or the CPU time the worker reports when larger); without a worker (body too slow, too large, client gone) the estimate stays due; only a capacity refusal (503) refunds it | — |
| Concurrency | 3 content requests in flight per client (1 running, 2 queued), 12 per prefix; running, at most half of the non-reserved slots per prefix (1 of 3 slots); LOCAL: 2 running | `MAX_RUNNING`, `MAX_QUEUED`, `MAX_INFLIGHT_PREFIX`, `MAX_RUNNING_PREFIX` (ceiling), `LOCAL_RUNNING` |
| Reserved slot | 1 worker slot for requests estimated under 0.2 s; a small request lasting over 5 s then counts as large (the next freed slot goes back to small ones) | `RESERVED_SLOTS`, `SMALL_S` |
| Shedding | 503 when the estimated wait exceeds 10 s: a simulation of the queue (estimated ends of the running jobs, then the requests served before this one, each on the first slot it may take); a usable slot free and nobody ahead: 0, so a small text is never shed because of large documents while the reserved slot is free. A job past its estimate is assumed to last as long again, never past its deadline | `MAX_WAIT_S` |
| State | 100,000 keys per tier; rested keys (no slowness kept) or keys idle for 10 min dropped; Space-Saving-style overflow (a new key inherits the state of the least loaded key of a sample: never a fresh budget during a flood) | `MAX_KEYS`, `IDLE_S` |
| Pseudonyms | secret renewed every 24 h, 10-minute grace | `ROTATE_S`, `GRACE_S` |
| Mode | `enforce` (default), `dry-run` (the buckets count without refusing; in-flight caps, scheduler caps and shedding still apply), `off` (kill switch) | `GDPRGUARDIAN_LIMITS` |

In keyed mode every key is a limiter client with the same settings, without the prefix tier; a `/mcp` call without a
valid key gets its 401 under its address's limits. In practice a client can have four 10 MB documents processed in a
row, then one every 8 seconds; hundreds of small texts per minute (the Nginx edge caps at 20 requests per second); a
50 MB document always goes through on a full budget (its estimate, 20.1 s, exceeds the 20 s burst: it passes on an
empty bucket), then the next one of the same size waits twice the worker time used (measured: 4 s after an
illustrated 50 MB DOCX processed in 3 s); a document holding a worker up to its deadline (270 s) is paid in full
(about 9 minutes of waiting). An internal limiter error lets the request
through (fail open); the sweep reports it as an aggregate WARNING (total, new) at most once a minute, and
`install.sh verify` fails while the counter is not zero. Counters are **aggregates only** (accepted, limited, shed,
overflows, tracked keys, in flight) on `GET /status`, never per client.

**Bodies.** Each body must arrive whole within 15 s plus its size (declared, else the route's cap) at 128 KiB/s (a
1 Mbit/s uplink; `GDPRGUARDIAN_MIN_BODY_RATE_KIB`): beyond, 408 `upload_timeout`, connection closed, memory freed.
Nginx's between-reads timeout (15 s) is not enough: one byte every 14 s would hold a connection forever. Creating an
upload (`POST /v1/uploads`): 256 KiB at most, counted in flight and in the memory budget like any request with a body.

**Memory.** Every body reserves its size before being read in the front process's budget (`GDPRGUARDIAN_QUEUE_MB`);
when a worker takes the request, it also reserves twice the largest possible reply, brought down to the real result
size until the response ends (a slow reader thus holds its share of the budget, no more). Budget fairness follows a
public client's **prefix** (/24, /48): rotating /64s opens no new share; a key beyond its share never digs into the
last reserve. A result (text or Markdown) never exceeds 1/8 of `GDPRGUARDIAN_MAX_STORE_CHARS` (12.5 M characters for
the official service): beyond, the worker answers 413 without sending anything; a document converted into more than
twice that is refused right after conversion, before the engine (see "Big documents").

**Deferred uploads.** Waiting for the file: 40 per creator prefix (`GDPRGUARDIAN_MAX_UPLOADS_PER_PREFIX`), 10,000 in
all (`GDPRGUARDIAN_MAX_PENDING_UPLOADS`), 10 per key or network-less principal. Received and unread: 10 per **PUT**
client (`GDPRGUARDIAN_MAX_ACTIVE_UPLOADS`) and 40 per its prefix, 1,000 in all; their characters: 1/8 of the store
per PUT client, 1/4 per prefix (429 `too_many_unread_results`, token kept when refused before the work). The PUT
comes from the user's machine: a remote MCP connector or a NAT shared by many does not make everyone share one
client's quota.

**Third-party pages.** A request a browser sends from another page (`Sec-Fetch-Site` other than `same-origin` or
`none`) gets 403 `cross_site_request`, from Nginx and then the service, with nothing counted: a third-party site's
multipart form needs no CORS preflight and would otherwise turn its visitors into a load source. The cockpit (same
origin) and non-browser clients (no header) are unaffected.

**Answers.** 429 `rate_limited` (a client's budget) or 503 `service_busy` (shedding), closed JSON body, always with
`Retry-After` in whole seconds plus 0-20% jitter so refused clients do not come back together, and, best effort,
`RateLimit-Policy` / `RateLimit` (IETF draft httpapi-ratelimit-headers-11: `"req";q=30;w=3`,
`"cpu";q=20000;qu="worker-ms";w=40`; "worker-ms" is not a registered unit, `Retry-After` is authoritative). The body
also gives the wait in seconds (`retry_after_s`). On `/mcp`, an MCP client never reads the body of an HTTP 4xx/5xx
(it only shows "Server returned an error response"): a refused JSON-RPC request (429, 503, 408, 413) therefore gets
HTTP 200 and a JSON-RPC error there (`-32000`, message `code: message … retry_after_s=N`, `data`: `code`,
`http_status`, `retry_after_s`), with the same `Retry-After`; without a JSON-RPC id (notification, batch) the HTTP
status stays. The id is looked for in the first 8 KiB and last 512 bytes of the drained body, nothing else is kept.
For clients (scripts, MCP agents): one request at a time, honour `Retry-After`, at most three attempts, retries under
10% of requests.

**Nginx edge** (coarse guard in front of the service): 20 requests per second (burst 40) and 16 connections per IPv4
address or IPv6 /64, 48 per /24 or /48, 1,500 in all (API and the sites' `/v1/`); headers read within 10 s, no body
pause over 15 s; cross-site requests refused (403); plain HTTP closed (444) for the service, the sites' `/v1/` and
`/mcp` included, with no redirect. The /64 key is written in one single form whatever the address compression (tested
by `tests/server/test_deploy_config.py` and the end-to-end bench). Nginx shared-memory zones only, never swapped out
(`MemorySwapMax=0`).

**Privacy and legal basis.** An IP address is personal data, even pseudonymised while the secret exists. Its
transient processing for the security of the service and abuse prevention rests on legitimate interest (GDPR
art. 6(1)(f), recital 49) and serves art. 32: in-memory pseudonym only, 24 h at most (secret renewal; a restart
erases everything), nothing on disk, no access or activity log (the service runs at `warning` level: no per-request or
per-document event), Nginx error log at `emerg` only (never an address), firewall log off (`ufw logging off`), no swap
nor core dump. Nginx keeps the binary address in its limit zones (shared memory, LRU), never on disk. Outside this
service remain fail2ban's database (SSH clients only) and older kernel journal entries, which rotate out on their own.

**Result isolation, by design.** Never another user's result:
- synchronous paths (`/v1/anonymize/text`, `/v1/anonymize/file`, `/v1/detect`, `anonymize_text`): the result only
  travels in the response, **nothing is stored**; every request gets its own fresh process;
- deferred path (`POST /v1/uploads` or `create_upload`, then `PUT`, then `GET /v1/results/{id}` or `get_anonymized`):
  reachable **only through a capability**. The upload token and the result id are 256-bit random values (the second
  derived from the first by HMAC under an in-memory key: whoever sees the upload URL, in a shell history or a command
  line, cannot derive the id), handed to the requester alone, stored as SHA-256 **digests**, compared in constant
  time; the token works once; the result is deleted 2 minutes after a full read (a lost answer can be read again)
  or at expiry, 30 minutes at most after publication; a wrong or expired token, or another key's, gets **the same
  answer** (404 `not_found`); a used token tells its holder alone (404 `upload_used`: request a new URL); a vanished
  result gets a distinct reason (`already_read`, `expired`, `deleted`, always
  404), told only to the holder of its id; no route lists anything; MCP is stateless (no session
  id, which would grant nothing anyway). In public mode the capability is enough (an agent's address changes
  between calls); with a key (the official service), the key is required too;
- `Cache-Control: no-store` forced on every response (by the service, then Nginx), no `proxy_cache`, no shared
  response.

### Big documents: published limits, chain, measurements

**Published limits** (site, this document, error messages; checked by `tests/server/test_big_documents.py`):

- **50 MB per file** (50 MiB, 52,428,800 bytes), every format, through the site, REST and MCP: beyond, 413
  `payload_too_large` "file too large: 50 MB at most", from the declared size when there is one (Nginx above 51m,
  the service above 50 MiB plus the 64 KiB multipart envelope, an out-of-band `PUT` above 50 MiB, unread), else while
  reading. The site's workspace refuses such a file without sending it;
- **one million characters per text** (`/v1/anonymize/text`, `anonymize_text`): 413 "text too long: 1,000,000
  characters at most";
- per document, **12.5 million characters of result** (anonymised Markdown, 1/8 of `GDPRGUARDIAN_MAX_STORE_CHARS`):
  413 `document_too_large` "result too long: 12,500,000 characters at most per document". A text converted into more
  than twice that is refused right after conversion, before the engine; in between, the engine runs and the result
  is measured (placeholders shorten tables of identifiers);
- **10,000 pages or slides** per document (`GDPRGUARDIAN_MAX_PAGES`; the library alone keeps 500): 413 "document too
  long: 10,000 pages at most";
- **one million HTML tags (opening and closing)** (HTML, HTML e-mails, mammoth's output), counted before parsing, a
  lone "<" in the text not being one: 413 "HTML too complex: 1,000,000 tags at most, opening and closing" (the
  BeautifulSoup tree weighs about 600 bytes and 27 µs per tag); and **256 nesting levels**, checked right after
  parsing: 413 "HTML nested too deeply: 256 levels at most" (markdownify recurses, two calls per level);
- **100,000 Word paragraphs (table cells included)** and one million XML elements, counted before mammoth in the
  document, its notes and its comments, whatever the namespace prefix: 413 "Word document too long: 100,000
  paragraphs at most, table cells included" or "Word document too complex: 1,000,000 elements at most" (the same
  message when mammoth's output goes over one million HTML tags). mammoth, then the HTML tree and markdownify cost
  about 0.27 ms per cell and 20 µs per other element: at worst, a table just under the limit, under half a small
  document's deadline (measurements below);
- spreadsheets: 2 million cells read (beyond, content cut and reported), 200 MiB uncompressed, 64 MiB XML parts;
- time: the body within 15 s plus its size at 128 KiB/s (408); processing within 60 s plus 1 s per 250 KB (422
  `conversion_timeout`), 270 s for 50 MiB, for every converter, spreadsheets included.

In practice an illustrated document (PDF, Word, PowerPoint, OpenDocument, RTF, e-mail with attachments) goes through
up to 50 MB; very dense text reaches 12.5 million characters first: around 13 MB of plain text or Markdown, 16 MB of
CSV, 4 MB of spreadsheet text cells, 16 MB of HTML tables. A Word table stops around 100,000 cells (14,000 rows of 7
columns, a few hundred KB compressed).

**The chain for a 50 MiB file** (official service), before and after this round:

| Layer | Before | After |
|---|---|---|
| Nginx `client_max_body_size` (API and the sites' `/v1/`) | 60m | 51m: 50 MiB + a 1 MiB margin covering the multipart envelope (64 KiB); in between, the service refuses with the same message |
| Nginx `client_body_timeout`, `send_timeout`, `limit_conn` | 15 s between reads, 60 s, 16 per address | unchanged |
| Nginx `proxy_read_timeout` | 300 s, under deadline plus queue | 600 s: two maximal deadlines |
| Service, size | 50 MiB + 64 KiB; `PUT` read up to 50 MiB before refusing; generic message | the same; `PUT` refused from `Content-Length`; limit named |
| Service, body | 15 s + 400 s at 128 KiB/s | unchanged |
| Service, deadline | 60 s + 210 s; spreadsheets' inner deadline fixed at 60 s | 270 s for everything |
| Pages or slides | 500: an illustrated 541-page PDF was refused | 10,000 |
| HTML | no tag limit: a 50 MB HTML used up the worker memory after 22 s | one million tags, refused in 0.1-0.3 s |
| Nested HTML | no limit: 400,000 nested `<div>` (4.4 MB) held a worker up to its deadline (77.7 s); the cleanup was quadratic (`Tag.decomposed` searches the whole subtree) | 256 levels: refused in 3.6 s; linear cleanup |
| Word | nothing before mammoth: a 30,000-row table (0.8 MB) went through in 59 s, 40,000 rows gave "HTML too complex" after 50 s, bigger ones a 422 or memory exhausted (1.5 GiB) | 100,000 paragraphs and one million elements counted before mammoth: refused in 0.1-0.3 s, Word message |
| Shedding | wait = remaining work of all slots / 3: during two 50 MB documents, 10 small texts of 29 shed (503) with a slot free | queue simulation, slot by slot: no small text shed (measurements below) |
| Output cap | 12.5 M characters, checked after the engine (a 50 MB text: 11.5 s, or 422 "unreadable" when the worker died) | the same, plus a refusal before the engine beyond 25 M converted characters (1.0 s) |
| Limiter | estimate 0.05 s + 0.4 s/MB = 20.1 s, above the 20 s burst: admitted on a full budget | unchanged, checked |
| Memory | 3 workers of 1,280 MiB, 1,024 MiB queue, 100 M result characters | unchanged; peaks below |
| Site workspace | timeout 120 s + 12 s per MiB, no progress | timeout 165 s + size × (1/131,072 + 2/250,000) s, upload progress shown, "running" counted from the end of the upload; a timed-out item up to 1 MiB is told to try again later, a bigger one to split; the local version is no longer advised for 413 or timeouts |
| MCP, file too big | `get_anonymized` kept saying "send it with the upload command" after a 413 from Nginx | the pending answer recalls the 50 MB limit and says not to send the file again |

**Measurements** (October 2026, WSL2, 16 cores: the repo's service in public mode with the `compose.yaml` settings
inside a 6 GiB memory cgroup, behind Nginx `stable` in Docker with the files of `deploy/server`; loopback, so upload
time excluded; fictitious documents from `tools/eval/generate.py`, with random-pixel images or attachments). Time
seen by the client, the worker's peak RSS, result size:

| Format | 50 MB illustrated (~1.24 M characters) | 50 MB at the ceiling (11.2-11.7 M characters) |
|---|---|---|
| PDF | 1.3 s, 322 MiB, 541 pages (before: 413, over 500 pages) | 9.3 s, 604 MiB, 3,377 pages |
| DOCX | 3.4 s, 309 MiB | 5.4 s, 563 MiB |
| PPTX | 1.4 s, 335 MiB, 400 slides | 3.8 s, 583 MiB |
| ODT / ODP | 0.6 s, 302 / 298 MiB | 3.3 / 3.1 s, 526 / 528 MiB |
| RTF | 1.0 s, 322 MiB | 4.2 s, 554 MiB |
| EML / MSG (attachments) | 1.5 / 0.5 s, 568 / 316 MiB | 4.3 / 2.9 s, 574 / 553 MiB |

| Text format | Accepted | Refused (413, limit named) |
|---|---|---|
| TXT, MD | 12 MiB: 2.8 s, 11.3 M characters | 15 MiB: 3.4 s; 50 MiB: 1.0 s (before: 11.5 s, or 422 for TXT) |
| CSV, TSV | 15 MiB: 3.4 s, 11.4 M characters | 18 MiB: 3.4 s; 50 MiB: 9-10 s (spreadsheet pipeline) |
| XLSX (text cells) | 3.9 MiB: 2.9 s, 11.1 M characters | 11.9 MiB: 8.7 s; 15 MiB and more: 0.2 s (XML part over 64 MiB) |
| ODS | 5 MiB: 3.0 s, 7.6 M characters | 20 MiB and more: 0.1-0.2 s |
| HTML (tables) | 16 MiB, 954,000 tags: 29.8 s, 763 MiB; 9.4 MiB, 990,000 tags: 24.5 s, 678 MiB | 20 MiB: 0.1 s (before: accepted in 38 s at 1,173 MiB); 50 MiB: 0.3 s (before: out of memory after 22 s) |
| Nested HTML | — | 400,000 levels (4.4 MB): 3.6 s (before: worker held up to its deadline, 77.7 s) |
| Word (tables, runs) | 99,995 cells (0.39 MB): 25.6 s, 498 MiB (through the site 24.2 s; two at once 27.9 s); one paragraph of 499,000 runs (998,000 elements): 23.9 s, 968 MiB | 100,100 cells: 0.11 s; 30,000 rows: 0.17 s (before: 200 in 59 s); 100,000 rows: 0.18 s (before: 422 at 71 s); 600,000 paragraphs: 0.17 s (before: 422 at 66.7 s); 0.37 MB carrying 60 MiB of XML: 0.2-0.4 s (before: 422 after 40.9 s, holding the reserved slot) |

Same outcome through the site's `/v1/`, REST and MCP. MCP: the `PUT` run with the curl command `create_upload`
returns, then `get_anonymized`: 31-32 pages read in 0.4 s for an illustrated 50 MB, 295 pages in 27 s at the
ceiling (paced by the cheap-request bucket, 10 per second), far within the result's 10 minutes. 50 MiB + 1 byte: 413
"file too large: 50 MB at most" through every path, the MCP `PUT` refused unread in 0.05 s (before: 0.4 s, after
reading 50 MB); a 51 MiB MCP `PUT`, refused by Nginx: `get_anonymized` then answers "pending", recalling the 50 MB
limit and saying not to send the file again. One client: a 50 MB PDF 200 in 1.4 s, at once again 429 `Retry-After: 2`, 2 s later 200. Three
50 MB documents at the ceiling at once from three clients: all 200 in 13.3 s (two at a time, one slot is kept for
small requests), service peak 1,043 MiB of 6 GiB. Largest worker peak seen: 921 MiB (a refused 50 MB TSV); largest
service peak: 1,279 MiB. The slowest documents under the limits: the HTML at the tag limit (30 s), well within its
deadline (127 s), and the Word table just under 100,000 paragraphs (25.6 s; 27.9 s two at once), under half of its
own (61.6 s).

Shedding, measured with a probe (one small text every 0.5 s, each from a new client): during two 50 MB PDFs at the
ceiling, 27 texts served of 27 (before: 10 of 29 shed over 5.3 s); during two Word tables at the limit and the
compressed Word carrying 60 MiB of XML, 53 of 53; a slow client (a 12 MB PDF up to its deadline, 108.9 s, sent again
after `Retry-After: 223`): during its second run, 204 of 204, none shed (before: 51 of 207). Two of those PDFs
running, then a 50 MB PDF 25 s later and a 12 MB text 30 s later: both shed at once (503, `Retry-After` 19 and 23 s),
since a job past its estimate is assumed to last as long again (before: the PDF admitted on an estimated wait of
6.7 s, then 84 s of real waiting; the text shed with `Retry-After: 1`); probe: 206 of 206.

### Build and run

```bash
docker build -f deploy/Dockerfile -t gdprguardian .        # from the repository root
# One key per client (organisation): only its digest goes into the environment.
key=$(python -c "import secrets; print(secrets.token_urlsafe(32))")   # give it to the client
printf '%s' "$key" | sha256sum | cut -d' ' -f1                        # -> GDPRGUARDIAN_API_KEY_SHA256
# Keyed service (the official service's mode), behind a proxy that sets X-GG-Client = the client address:
docker run -d --read-only --cap-drop ALL --security-opt no-new-privileges \
  --memory 2g --memory-swap 2g --ulimit core=0 \
  -e GDPRGUARDIAN_API_KEY_SHA256="<digest1>,<digest2>" -e GDPRGUARDIAN_CLIENT_IP_HEADER=X-GG-Client \
  -e GDPRGUARDIAN_PUBLIC_URL="https://rgpd.example.eu" -p 127.0.0.1:8000:8000 gdprguardian
# Or a public service, no key: -e GDPRGUARDIAN_PUBLIC=1 instead of GDPRGUARDIAN_API_KEY_SHA256.
```

- No swap (`--memory-swap` = `--memory`) and no core dumps: documents never leave RAM.
- Without a chosen mode (`GDPRGUARDIAN_PUBLIC=1`, `GDPRGUARDIAN_API_KEY_SHA256` or, locally,
  `GDPRGUARDIAN_DEV_NO_AUTH=1`) the service refuses to start (fail closed). In keyed mode each key is an isolated
  principal (uploads and results are bound to it) and is checked **before** any body is read: a client without a key
  only ever gets a 401. A plaintext key in the environment (`GDPRGUARDIAN_API_KEYS`) is refused.
- **File names are never kept**: only the extension selects the format, and the Markdown starts with
  `# document.pdf` (a name such as `CV_Jean_Dupont.pdf` is personal data).
- Memory: every request, organisation rules included, runs in an isolated process (at most 2 GiB on top of its
  idle footprint; a 10 MB file needs 0.3 to 0.6); the front compiles no pattern. With `--memory 2g`, set
  `GDPRGUARDIAN_MAX_CONCURRENCY=2`; the queue budget is then 512 MB (a quarter of the container limit), about fifty
  10 MB files before the first 503. The default concurrency honours CPU affinity and the cgroup v2 quota
  (`--cpus`).
- `GDPRGUARDIAN_ALLOWED_HOSTS` now guards **every** route (DNS rebinding); loopback names stay accepted for the
  health probe. Without it, the check only applies when the service listens on `127.0.0.1`.
- `GDPRGUARDIAN_UPLOAD_TTL_S` bounds the upload URL until the `PUT` starts; every body must then arrive within 15 s
  plus its size at `GDPRGUARDIAN_MIN_BODY_RATE_KIB` (128 KiB/s; 408 for slow clients).
- `GDPRGUARDIAN_LOCAL_TOKEN_SHA256` (digest of the token a request without the address header must present in
  `X-GG-Local` to be LOCAL), `GDPRGUARDIAN_MAX_UPLOADS_PER_PREFIX` (40), `GDPRGUARDIAN_MAX_PENDING_UPLOADS` (10,000):
  see above. `GDPRGUARDIAN_MAX_ACTIVE_UPLOADS` (10) now counts received uploads and unread results per PUT client,
  and pending ones per key; `GDPRGUARDIAN_MAX_STORE_CHARS` also caps one result at 1/8 of it.
- `GDPRGUARDIAN_MAX_PAGES` (10,000): pages (PDF) or slides (PPTX, ODP) of one document, 413 naming the limit beyond
  (the library alone keeps 500). `GDPRGUARDIAN_CONVERSION_TIMEOUT_S` is also the converters' and spreadsheets' inner
  deadline: the request's whole deadline (60 s + 1 s per 250 KB, 270 s for 50 MiB), no longer a fixed 60 s.
- Environment variables: see the table above (same names). Set `GDPRGUARDIAN_PUBLIC_URL` in production. Once read
  at start-up they are removed from the environment before the zygote starts (with `gdprguardian serve`,
  `gdprguardian mcp` or `uvicorn --factory gdprguardian.server:create_app`): no worker sees them, keys included. Only
  `GDPRGUARDIAN_PURE_PYTHON=1` (Python engine alone, the reference) is passed on to the workers, which read it at
  start-up.

### Usage counter (public page)

`GDPRGUARDIAN_USAGE_SOCKET` (default: unset, disabled; production: `/run/gdprguardian-stats/usage.sock`, an
absolute path of at most 107 bytes) names a local Unix datagram socket. The front process sends one JSON datagram
of at most 256 bytes at the end of each anonymisation, successful or not:

```json
{"v":1,"kind":"upload","fmt":"pdf","bytes":20480,"ms":6,"ok":true,"src":"public"}
```

- `v`: `1`, the format version.
- `kind`: origin, `text` (`/v1/anonymize/text`, `/v1/detect`), `file` (`/v1/anonymize/file`), `upload` (REST
  out-of-band upload, counted at the `PUT`), `mcp_text` (`anonymize_text` tool), `mcp_file` (document received
  through MCP: `create_upload` then `PUT`, or `anonymize_file`).
- `fmt`: `text`, `pdf`, `docx`, `doc`, `xlsx`, `xls`, `pptx`, `odt`, `ods`, `odp`, `rtf`, `eml`, `msg`, `html`,
  `csv`, `tsv`, `md` or `other`. On success the detected format (`.xlsm` and `.xlsb` count as `xlsx`), on failure
  the declared extension's format; texts are `text`.
- `bytes`: size received, in bytes (texts in UTF-8, files as sent), 256 MiB at most.
- `ms`: processing time in whole milliseconds, waiting for a worker included, one hour at most.
- `ok`: `true` when the anonymisation succeeded, `false` otherwise (document refused, rules refused, deadline,
  service busy, client gone).
- `src`: `public` for normal traffic; `protocol` for a request from the server itself (reaching the socket without
  the address header: a measurement protocol run on the server). The daemon also accepts datagrams without this
  field (`public`).

**Never sent**: no content, file name, IP address, key, principal, upload or result identifier, nor token. Every
field is a number, a boolean or a value from a closed set, so nothing the client sends can travel in it. A request
refused at the door (authentication, rate limit, invalid option, oversized or malformed body) is not an
anonymisation and sends nothing; neither does creating an upload or reading a result.

**Only the front process counts, and the site daemon checks it.** On Linux its socket takes at start, before any
worker exists, the abstract name `gdprguardian-usage:<socket path>` (107 bytes at most) and keeps it; the daemon
ignores any datagram from another name. Workers share the user and see the same folder, but the kernel refuses a
second holder of the name: a worker, even one compromised by a booby-trapped document, can neither count fake
documents nor pass anything through the published figures. The daemon also refuses out-of-bounds values and
rounds the published sizes to the shown precision ("12.4 MB").

Fire and forget: a non-blocking socket, opened in the front process only, never inherited. Daemon gone, full queue
or permission denied: the statistic is lost, with no error and no log line, and the request is never slowed down.
Unset or empty: the counter is off. On Windows (no Unix datagram sockets) it does nothing. The local MCP server
(`gdprguardian mcp --stdio`) does not read the variable: nothing leaves the computer. In a container, mount the
socket's folder **at the same path** (`-v /run/gdprguardian-stats:/run/gdprguardian-stats`: the expected name
depends on it) and let the service user write to the socket; a Unix socket does not use the network, so the
container keeps `--network none`.

### Without network, for the most cautious

The same image anonymises a local folder with **no network at all** (`--network none`: the loopback `lo` is the
only interface, with no route out), a read-only file system and a read-only mount; nothing listens, nothing leaves, the anonymised Markdown goes
to standard output (same loop as above: `docker run --rm --network none --read-only --cap-drop ALL --security-opt
no-new-privileges -v "$PWD/dossiers:/data:ro" gdprguardian gdprguardian anonymize /data/<file>`). The local MCP server
runs there too: an MCP client launches `docker run -i --rm --network none --read-only --cap-drop ALL -v
<folder>:/data:ro -e GDPRGUARDIAN_ALLOWED_DIRS=/data gdprguardian gdprguardian mcp --stdio` (paths are then container
paths, `/data/...`). Checked by `tests/test_offline.py` (`GDPRGUARDIAN_OFFLINE_IMAGE=gdprguardian`); without Docker,
the same test forbids any connection, name lookup or unexpected program launch to the engine, the converters and the
local MCP server.

### Rust core: profile-guided optimisation (PGO)

`tools/pgo.py` builds the core in three steps: an instrumented core (`-Cprofile-generate`); a representative
workload on **fictitious** data only (the 1,000 documents of `datasets/fr/docs` twice with countries "FR", once
with "all", a third in the strict profile with explanations and organisation rules, a 1.9 MB text, a 3,000-row
Markdown table, spreadsheet segments, a 5,000-row CSV and TSV); the profiles are merged by the pinned
toolchain's `llvm-profdata`, then the final build uses them (`-Cprofile-use`). The profile only holds branch
counters, never text, and never leaves the build stage. Each variant has its own stage (`core-1`, `core-0`) and
BuildKit only builds the selected one. PGO is **on by default**; `docker build --build-arg PGO=0 …` builds the
core directly, which then only depends on `rust/` (a Python edit does not rebuild it, and the corpus is not
required) and gives a bit-for-bit reproducible wheel. Locally: `rustup component add llvm-tools-preview` then
`python tools/pgo.py --out dist/` (`--plain` for the reference build, `--target-cpu` to try another instruction
set).

Measured on the final core (October 2026, WSL2 Ubuntu 24.04, rustc 1.99.1; 12 interleaved rounds, process pinned
to one core, each variant in a fresh process; PGO / plain time ratio, paired median within a round; an A/A control,
two identical copies of the core measured the same way, gives the size of the noise):

| Workload | PGO / plain time | Gain | A/A control |
|---|---|---|---|
| 1,000 corpus documents, countries FR | 0.883 | −11.7% | 1.023 |
| 1,000 corpus documents, all countries | 0.902 | −9.8% | 0.979 |
| held-out texts, countries FR | 0.981 | −2% (within noise) | — |
| held-out texts, all countries | 0.945 | −5.5% | — |

Since the whole detection runs in Rust (two calls per document), PGO weighs much more than in the first
measurements (about 4%, when part of the time was still spent in Python), so it is **the default**. The gain is
smaller on texts far from the profile corpus, and never turns into a loss. `-Ctarget-cpu=x86-64-v2` brings nothing
measurable (median −0.3% over 7 rounds; with PGO, worse than PGO alone), so the image keeps the baseline x86-64
instruction set and runs on any x86-64 VM. A profile depends slightly on the run (randomly seeded hash tables):
the PGO wheel is not bit-for-bit reproducible across builds, whereas with `PGO=0` the wheel only depends on the
pinned toolchain and the sources. The `gdprguardian-core` wheels meant for PyPI are built without PGO (seven
platforms, some cross-compiled, where the profile cannot be run). Image: 103 MB of content (441 MB on disk) with
or without PGO, 3.6 MB core; a full uncached build takes 3 min 49 s with PGO, 2 min 26 s without (16 cores,
October 2026).

### TLS termination

Use a reverse proxy hosted by you or your EU provider, never a CDN that decrypts traffic outside the EU.
Never log request or response bodies (proxy, WAF, APM). The single-use upload token is part of the URL
path, so drop `$request`/`$request_uri` from proxy log formats. Align the body-size limit with
`GDPRGUARDIAN_MAX_UPLOAD_MB` plus a margin of at least 64 KiB for the multipart envelope (`51m` for 50 MiB), wait for
the answer at least two deadlines of the largest
document (2 × 270 s for 50 MiB: `proxy_read_timeout 600s`) and, with nginx, set `proxy_request_buffering off;` so
large bodies are not spooled to disk. For per-client limits, set `proxy_set_header X-GG-Client $remote_addr;` (it overwrites any
client value) with `GDPRGUARDIAN_CLIENT_IP_HEADER=X-GG-Client`, and `proxy_redirect http:// https://;`.

**Dedicated server: the official service's install (`deploy/server/`).** `api.gdprguardian.com`,
`api.gardienrgpd.fr` and the website (`gardienrgpd.fr`, `gdprguardian.com`) are installed by
`deploy/server/install.sh` on an already hardened Ubuntu server, in seven idempotent phases (`base`,
`image <archive>`, `cert`, `https`, `site <binary> <videos>`, `start`, `verify`); to upgrade a running server: `site
<binary> <videos>`, `base`, `image <archive>`, `start`, `verify` (the site daemon first: the nginx configuration
installed by `base` points at it). `<videos>`: a folder holding the files of the repository's `video/out` (by default
`../../video/out` from `install.sh`, when it runs from a repository checkout).
- Keyed service (`compose.yaml`, since 27 October 2026): no more `GDPRGUARDIAN_PUBLIC`,
  `GDPRGUARDIAN_CLIENT_IP_HEADER=X-GG-Client`; the `GDPRGUARDIAN_API_KEY_SHA256` digests, one key per organisation, are
  in `/etc/gdprguardian/gdprguardian.env`, never a plaintext key (`base` removes the `GDPRGUARDIAN_API_KEYS` line from
  an old settings file). Memory:
  3 workers of 1,280 MiB, 1,024 MiB queue (bodies and worker outputs), 100 million result characters, 12.5 million
  per result at most (about 5.5 GiB under the container's 6 GiB); every worker is the OOM killer's preferred victim
  (`oom_score_adj` 1000), so a saturation costs one request, never the service. Log level `warning`: no per-request
  or per-document event.
- Local token: `base` creates `/etc/gdprguardian/local-header` (the `X-GG-Local` header ready for `curl -H @…`) and
  `/etc/gdprguardian/local.env` (its digest, read by the container), root 0600, never passing the token as a command
  argument. Only the server's requests presenting it on the socket are LOCAL (probe, `verify`, measurement protocol);
  a compromised worker reaching the socket lands in the shared bucket.
- The container has no network (`network_mode: none`): `gdprguardian serve --uds /run/gdprguardian/app.sock` only
  listens on a Unix socket in a **dedicated 64 KiB tmpfs** (`run-gdprguardian.mount`, mounted before Docker)
  readable by nginx alone, so the container can neither fill the host's `/run` nor point at another socket. It runs
  read-only, with `/tmp` in memory, no privilege or capability, memory without swap, no core dump, a bounded process
  count, as user 10001, **without init** (the hardened service is PID 1), `pull_policy: never`; `image` and `start`
  check that the image `compose.yaml` expects is loaded, `start` recreates the container and requires the right
  version on `/health`.
- Host-side health probe: `gdprguardian-watchdog.timer` queries `/health/deep` through the socket every 2 minutes
  (local token: outside the limits): a tiny job in a real worker, outside the queue and the usage counter, so a
  broken worker pool (zygote, processes used up) is seen, not just the event loop. Three failures: the container is
  restarted; nothing runs inside it. `/health/deep` does not exist for any other request (404).
- Automatic updates (`install.sh updates`, Paris time): security every night at 2 am (1:45 on Monday), with a reboot
  right after when it requires one; Ubuntu's stable updates (`-updates`: docker.io, nginx…) on Saturday at 2 am, same
  rule; a reboot every Monday at 2 am, once any running update is over (never in the middle of dpkg). After a reboot,
  Docker restarts the container (`unless-stopped`) and systemd the site daemon, Nginx and the probes. `verify` checks
  that the nightly run takes security only and that the timers are active.
- nginx: a dedicated main configuration (`nginx-main.conf`, read by `nginx -c` through
  `nginx.service.d/gdprguardian.conf`); the packaged `nginx.conf` is restored if it had been modified, so unattended
  Nginx upgrades never stall. Every file is backed up, tested and restored on failure. TLS 1.2 and 1.3 (ECDSA Let's
  Encrypt certificate, renewed automatically; `cert` never drops a name), unknown TLS names refused at the handshake,
  unknown Host closed (444), plain HTTP for the api.* names reduced to the ACME challenge (444 otherwise, no
  redirect), plain HTTP for the sites: pages redirected, `/v1/` and `/mcp` closed (444), `server_tokens off` in every
  server, bodies passed unbuffered with temporary files in memory, **no access log**, error log at `emerg` only (never
  an address; `base` empties the logs written before), security headers and JSON errors on the responses Nginx
  produces itself, `X-GG-Client = $remote_addr` and `X-GG-Local` cleared towards the service, cross-site requests
  refused (403), edge limits (above), never swapped out (`MemorySwapMax=0`). `base` also turns the firewall log off
  (`ufw logging off`) and empties `ufw.log`.
- The website is the Rust daemon `gdprguardian-site` (`site/`, a systemd unit without network), with no cookie and
  no log; nginx passes it the truncated address (/24, /48) to count today's visitors. The site's cockpit calls `/v1/`
  **on the same origin**: nginx forwards it to the service as from api.* (Host rewritten, client address set, same
  limits and headers).
- The launch video (`/media/`, the `#video` panel of both sites) is served by nginx, not by the daemon (which embeds
  its files in its binary and serves no byte ranges, which Safari requires for video): ranges (206), ETag, `sendfile`.
  A closed list of 8 files (`$gdprguardian_media` in `nginx-http.conf`, `MEDIA_FILES` in `install.sh`), any other name
  404; fixed types (`video/mp4`, `image/png`, `text/plain; charset=utf-8`); the daemon's security headers, its CSP
  included (`media-src 'self'`); `Cache-Control: public, max-age=31536000, immutable` on successful responses only,
  as the pages cite every file with its digest (`?v=`). `site <binary> <videos>` first checks that every link in the
  binary's pages names a provided file with that digest (SHA-256), then copies the changed files into
  `/var/www/gdprguardian-media` (temporary name, then rename; any other file removed). A binary from before the video
  (rollback) leaves `/media/` as it is.
- Settings: `/etc/gdprguardian/gdprguardian.env` (root, 0600): `GDPRGUARDIAN_API_KEY_SHA256` digests (comma-separated),
  limiter mode and `GDPRGUARDIAN_LIMIT_*` if needed, never a plaintext key. New key or revocation: add or remove the
  digest, then `install.sh start` (which recreates the container).
- `verify`, which still expects public mode (its checks run without a key) and is **yet to be adapted** to the keyed
  service, fails at the first defect: listeners, version, local token configured, nginx out of swap and firewall
  without a log, the path through Nginx to the service without a key (10-byte and 2 MB bodies refused by the service
  after reading: nothing anonymised, hence nothing counted as public traffic; MCP `initialize`), headers, no redirect,
  cross-site refusal, then through the socket with the local token (counted as "protocol"): anonymisation, 2 MB upload
  round trip, deep probe; cockpit (same-origin `/v1/`, cross-site refusal, plain HTTP closed), site stream, video (a
  byte range of every file on each site: 206, type, headers, cache; unknown name: 404), unknown Host and SNI refused,
  429 under a burst from one address, no cookie, no client address in the Nginx logs, no internal limiter error,
  active probe.

### EU hosting and operations

Choose an EU provider with no US parent or presence (CLOUD Act). The hosted service is a GDPR art. 28
processor for content: every key comes with a data processing agreement; publish the list of sub-processors. Neither
GDPR Guardian nor the example proxy configuration logs IP addresses; abuse handling only sees them in memory (Nginx
limit zones and the service's pseudonym, secret renewed every 24 h, nothing on disk), under legitimate interest
(art. 6(1)(f), recital 49) and art. 32; see "Key access" above.

Erasure and isolation. The code guarantees: a fresh process per request (organisation rules, conversion and
anonymisation), never reused, killed after its reply, dying with the service, while the front process never
parses, compiles nor anonymises content; inside it, before any document, standard streams to `/dev/null`, no
`GDPRGUARDIAN_*` variable (bar the `GDPRGUARDIAN_PURE_PYTHON` switch), and on Linux a non-dumpable process (no
`/proc/<pid>/mem`, `environ` or `ptrace`) with no core dump, no right to create processes and no channel to the
zygote; the service drops its settings and keys from the environment once read, before any child process
(`gdprguardian serve`, `gdprguardian mcp`, `uvicorn --factory`), and is non-dumpable; no shared
content cache, no internal timings returned to clients, no error retaining the document; results in RAM for
30 minutes at most after publication, wiped 2 minutes after a complete read. Python cannot wipe immutable strings, so the strong guarantee is
process exit. The host must provide: no network egress for the container besides the proxy; no swap, no core
dumps (`fs.suid_dumpable=0`, no `systemd-coredump`), no kdump, no hibernation, no VM memory snapshots;
`kernel.yama.ptrace_scope>=1`, `--cap-drop ALL`, `no-new-privileges`, read-only filesystem; ideally
`init_on_free=1`; and, against the provider itself, a confidential VM (AMD SEV-SNP, Intel TDX). Use
`--log-driver local` (the default `json-file` driver never rotates) and add `proxy_http_version 1.1;` and
`error_log ... emerg;` to nginx (from `crit` on, nginx logs full client addresses). Run **one front process per instance**
(results and the limiter's state live in that process's memory; workers are its children); with several instances,
route consistently (by client address, or by upload id for `/v1/uploads/…` and `/v1/results/…`). Health probe:
`GET /health`; `GET /health/deep` for the server itself (a real worker); aggregate state: `GET /status` (slots,
queue, estimated wait, limiter counters; nothing about any client). MCP: stateless streamable HTTP at `/mcp`,
`Authorization: Bearer <key>` in keyed mode (the official service), no header in public mode. Logs hold metadata only: no values, file
names, tokens, keys or addresses; **no access or activity log at the production level** (`--log-level warning`):
only warnings and errors (a 5xx answer, an internal limiter error, a failed deep probe). In development
(`--log-level debug`), each processing line carries its worker's PID (`worker=`) and queue wait (`wait_ms=`),
refusals log `event=service_busy`, abandoned requests `event=request_abandoned`, rejected content
`event=document_rejected` or `event=text_rejected` with its `code` (`code=invalid_rules` for refused rules: neither
pattern nor reason in the log, a pattern may contain a name).
