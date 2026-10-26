# gdprguardian-site

Démon du site de [Gardien RGPD](../README.md) : <https://gardienrgpd.fr> (français) et <https://gdprguardian.com>
(anglais). Un binaire Rust d'environ 1 Mo sert la page, ses fichiers et ses statistiques en direct ; aucun
cookie, aucun traceur, aucune ressource tierce, aucun journal de requêtes.

Website daemon of GDPR Guardian. One Rust binary of about 1 MB serves the page, its files and its live statistics;
no cookie, no tracker, no third-party resource, no request log.

## La page : un poste de travail / the page: a workspace

Le site est l'outil. Premier écran, plein écran en paysage, sans page de présentation à traverser ; un titre `h1`
dit ce qu'il fait (« Gardien RGPD, anonymisation irréversible avant l'IA »). À gauche la saisie (coller, taper, ou
déposer des documents n'importe où dans la page, plusieurs à la fois) et la file de la session ; au centre le
résultat du document choisi (texte anonymisé, inspection des balises, une ligne par type, explications ; vide, c'est
la zone de dépôt visible) ; à droite les instruments en blocs carrés (qui grandissent avec leur texte sous 1 700 px
de large) : d'abord l'indice de confiance du protocole public, en clair (documents normalisés en grand, documents
difficiles à côté, chacun avec son intervalle, puis trois lignes vérifiables, dont les scans de mauvaise qualité
publiés à part, et le lien vers le protocole ; le tableau par famille est dans le panneau « Protocole et scores »),
puis le service en direct (compteurs depuis la mise en ligne ; processeur et mémoire affichés toutes les 10 s) et
votre session (documents, mentions masquées, volume, temps). Un témoin permanent dit « Aucun document conservé, ni ici
ni sur le serveur » et mène à la confidentialité.
« En savoir plus » est un choix : des boutons ouvrent des panneaux (la vidéo de lancement, le défi, l'histoire,
l'architecture, le protocole et les scores avec les faiblesses, l'usage par MCP public, API et poste local, l'appel
aux établissements publics, les remerciements, les mentions légales, la confidentialité). Signature : « Conception :
Claude Design ».

**Vidéo** (`#video`) : `<video controls preload="none" playsinline>` de la langue de la page, son affiche, le lien
vers sa transcription (la vidéo est muette : c'est son équivalent texte), le montage court 4:5 à télécharger, et une
ligne : l'indice de confiance de la vidéo est celui du jour de son rendu. Fichiers servis par Nginx sous `/media/`
(plages d'octets pour Safari ; `deploy/server/nginx-site.conf`), jamais par le démon, copiés de `video/out` par
`install.sh site` ; chaque lien porte l'empreinte du fichier (`?v=` : 8 premiers chiffres hexadécimaux du SHA-256),
car Nginx les garde un an. Un nouveau rendu de la vidéo change donc les `?v=` des deux gabarits, et la taille du
montage court si elle bouge (`tests/server/test_deploy_config.py` le vérifie). Fermer le panneau met la vidéo en
pause (cachée, elle continuerait). Chromium charge l'affiche (85 à 92 Ko) avec la page même panneau fermé, une fois
(gardée un an). Video panel: the page's language, poster, transcript link (the video is silent), the 4:5 cut to
download; files served by Nginx under `/media/` with their digest in the link (`?v=`), cached a year; a new render
changes the `?v=` in both templates.

- **File** (`static/cockpit.js`) : chaque texte envoyé (bouton ou Ctrl/⌘ + Entrée) et chaque document déposé, choisi
  ou collé devient une ligne de la file, avec son état : en attente, en cours (secondes écoulées), nouvel essai dans
  N s, terminé (mentions, durée), refusé (cause exacte), annulé. Un seul envoi à la fois (le service accepte 1 en
  cours et 2 en attente par client) ; 429 et 503 : `Retry-After` (secondes) respecté et file reprise seule, trois
  essais par document, puis pause et bouton « Reprendre » ; 502, 504 ou réseau coupé : pause. 403, 408, 413, 415,
  422 (cause par code), 501 : refus du document, avec la cause exacte ; 413 et 415 sont refusés ici avant tout envoi
  (50 Mo, un million de caractères comptés en points de code comme le service, extensions acceptées ; le message 415
  donne la liste des formats). Chaque document est anonymisé séparément : la page le dit. L'en-tête de la file et le
  message de fin donnent le bilan (« 4 terminés · 2 refusés · 3 en file ») ; la liste suit l'envoi en cours sans
  faire défiler la page ; une ligne par document sur les écrans bas (≤ 820 px de haut). Après trois 429, la pause dit
  que c'est la limite de votre adresse ou de votre réseau ; après trois 503, que le service est saturé.
- **Brouillon protégé** : Échap ne vide la saisie que depuis la saisie, et Ctrl/⌘ + Z la rend ; un texte collé hors
  de la saisie s'insère au curseur ; « Exemple » part directement dans la file ; « Reprendre le texte » refuse
  d'écraser un brouillon. Quitter la page avec une session en cours (langue, rechargement) passe par la question du
  navigateur (`beforeunload`), sauf pour un lien e-mail ; les liens extérieurs s'ouvrent dans un nouvel onglet.
- **Rien n'est gardé dans le navigateur** : ni cookie, ni `localStorage`, ni `sessionStorage`, ni IndexedDB, même
  pour les réglages ; textes et résultats ne vivent que dans la mémoire de l'onglet. « Tout effacer » la vide (file,
  dernier rapport, bandeau, ligne d'inspection, table des explications ; et le dit) ; fermer l'onglet aussi. Le vrai
  nom d'un fichier ne part jamais (`document.<extension>`) et ne nomme aucun téléchargement.
- **Sorties** : copier (Ctrl/⌘ + Maj + C), télécharger le .md (Ctrl/⌘ + S, `03-pdf-anonymise-2026-10-25-1432.md`),
  tout télécharger en .zip écrit dans le navigateur, sans bibliothèque (entrées « stored », CRC-32, noms UTF-8).
  Échap ferme un panneau, ou vide la saisie quand elle a le focus. Collage d'un texte n'importe où : il s'insère au
  curseur de la saisie, sans envoi ; une copie depuis Word ou Excel, qui porte aussi une image d'elle-même, reste un
  texte (seuls des fichiers collés sans texte, ou autres que des images, deviennent des lignes de la file).
- **Panneaux** : sections `.pn` affichées par `:target`, donc une URL par panneau (`#protocole`, `#utiliser`…) et une
  lecture sans JavaScript ; en grand écran ils couvrent le résultat et les instruments, sur tablette le résultat
  seul, jamais la saisie (on continue de déposer). Ce qu'un panneau couvre est masqué (`visibility:hidden`, CSS
  seule) : ni focus clavier ni lecteur d'écran derrière lui (WCAG 2.4.11). Le script ajoute le focus sur le titre,
  Échap, et rend le focus au bouton d'origine ; fermer (ou le nom du site dans la barre) remplace l'entrée
  d'historique du panneau.
- **Sans JavaScript** : seuls restent ce qui marche (panneaux, chiffres du service, pointeurs vers l'API et le MCP) ;
  saisie, réglages et instruments de session sont cachés (`@media (scripting:none)`).
- **Focus** : la saisie au chargement (pointeur fin), la saisie après chaque envoi, la ligne suivante après
  « Retirer », la ligne choisie après « Reprendre » ou « Annuler l'envoi ».
- Balises : impaires pleines, paires cerclées ; survol pour voir, clic ou toucher pour épingler, boutons du tableau des
  explications au clavier ; ligne d'inspection (balise, mentions, règle, raison en clair).
- Couleur de signal (`--sig`) : balises et focus seulement ; `--err` : document refusé.
- Textes de l'interface : liste `#i18n` de chaque page ; raisons (`r`) et éléments écartés (`d`) en une ligne
  `clé=texte|clé=texte`. Éléments du script : attribut `data-r`.

The site is the tool: a full-screen landscape workspace (input and session queue, result, square instrument tiles),
learn-more panels shown with `:target` (one URL each, readable without JavaScript). One request at a time;
`Retry-After` honoured and the queue resumed by itself; exact causes for 403, 408, 413, 415, 422, 501; nothing
stored in the browser (no cookie, no Web Storage, no IndexedDB); the real file name never leaves the browser;
copy, .md and a browser-written .zip; keyboard shortcuts Ctrl/⌘ + Enter, Ctrl/⌘ + Shift + C, Ctrl/⌘ + S, Esc.

**Polices / fonts** : Red Hat Text (interface, variable 400 à 600, chiffres tabulaires) et Red Hat Mono (données,
balises), sous-ensembles latins (Latin-1 et Latin étendu A, plus Ș ș Ț ț, pour les noms des documents européens)
renommés « GR Sans » et « GR Mono », OFL ; `static/fonts/LICENSE.txt` et les textes de licence à côté. Aucune police à
empattements. 2 fichiers, 36 292 octets.

**Chiffres des textes réels** : le tableau par corpus du panneau « Protocole et scores » et la ligne « Textes réels »
des instruments sont écrits dans les deux gabarits, recopiés de `benchmarks/results/real-summary-2026-10-25.json`
(`mention_recall`, `doc_leak_rate`, `documents` des six corpus français et de TAB). Une nouvelle mesure des corpus
réels doit les mettre à jour dans `index.fr.html` et `index.en.html`. Real-corpus figures are written in both
templates, copied from that file; a new real-corpus run must update them there.

**Contrat D, valeurs du protocole public** : `confidence_index`, `confidence_ci_low`, `confidence_ci_high`,
`mention_recall_pct` (pourcentages), `protocol_docs`, `protocol_families`, `real_corpora`, `real_docs` (entiers),
`protocol_date` (date ISO) et `protocol_engine` (version) valent la chaîne `"—"` dans `data/quality.json` tant que la
campagne n'est pas publiée ; la page les affiche « pas encore mesuré » / « not measured yet » (CSS sur `data-v`,
sans JavaScript), jamais comme un nombre. La construction refuse une valeur mal formée, un indice publié sans son
intervalle (qui doit l'encadrer), ses nombres de documents et de familles, sa date et sa version, et
`real_corpora` sans `real_docs` (`template::contract_errors`). Pending values are "—" and show as "not measured
yet"; the build refuses malformed values and an index published without its companions.

`docs_leak_direct_pct` (9,1 le 25 octobre 2026) : documents gardant au moins un identifiant direct lisible, noms et
adresses compris ; c'est le chiffre de fuite affiché dans les instruments, avec `docs_leak_structured_pct` (4,6, les
identifiants structurés seuls). Une valeur de qualité qui est une date ISO seule s'écrit en toutes lettres dans la
langue de la page (« 25 octobre 2026 »).

## Ce qu'il fait / what it does

| Route | Réponse / answer |
|---|---|
| `GET /` | page `templates/index.fr.html` pour l'hôte `gardienrgpd.fr`, `index.en.html` pour tout autre ; valeurs en direct écrites dans la page ; `Cache-Control: no-cache` |
| `GET /assets/<chemin>`, `/favicon.svg` | fichiers de `static/`, brotli ou gzip selon `Accept-Encoding`, `ETag` et `304`, `Cache-Control: public, max-age=3600` |
| `GET /api/stats` | JSON des statistiques (ci-dessous), `no-store` |
| `GET /api/live` | Server-Sent Events : événement `stats` aussitôt puis toutes les 2 s, commentaire de maintien toutes les 15 s ; 2000 flux au plus (au-delà `503`), chacun clos après 20 à 30 min (le navigateur se reconnecte 5 s plus tard) |
| `GET /robots.txt`, `/.well-known/security.txt` | tout permis ; `Contact: mailto:contact@gardienrgpd.fr`, `Expires` un an plus tard, `Preferred-Languages: fr, en` |
| `GET /media/<nom>` | jamais le démon : Nginx sert la vidéo de lancement (liste fermée de 8 fichiers, plages d'octets, mêmes en-têtes de sécurité, un an de cache) ; le démon, lui, y répond `404` |
| autre chemin / other path | `404` (corps de 4 octets) ; méthode autre que GET et HEAD : `405` |

```json
{"uses_hour":12,"uses_hour_protocol":4,"bytes_hour":48211,"docs_total":3751,"docs_protocol":1200,
 "bytes_total":13002342,"visitors_total":980,"visitors_today":41,"cpu_percent":3.2,"ram_used_bytes":2147483648,
 "ram_total_bytes":34359738368,"since":"2026-10-25","updated":1793016000}
```

Chaque réponse porte la CSP du contrat (`media-src 'self'` et `img-src 'self' data:` pour la vidéo et son affiche ;
`default-src 'none'` sur `/api/*`), HSTS, `nosniff`,
`Referrer-Policy: no-referrer`, `Permissions-Policy`, COOP et CORP `same-origin` ; jamais `Set-Cookie`, jamais
d'en-tête `Server`. Every response carries the contract's CSP, HSTS, nosniff, no-referrer, Permissions-Policy,
COOP and CORP; never Set-Cookie, never a Server header.

- **Usage du service** : le service envoie un datagramme Unix par opération terminée
  (`{"v":1,"kind":K,"fmt":F,"bytes":N,"ms":M,"ok":B,"src":S}`, 512 octets au plus, sortes et formats du contrat,
  `S` facultatif : `public` (défaut si absent) ou `protocol` pour les essais du protocole public lancés sur le
  serveur même, aucun autre champ, `N` ≤ 256 Mio, `M` ≤ une heure) sur `/run/gdprguardian-stats/usage.sock` (0660,
  groupe 10001). `docs_protocol` compte les documents réussis d'origine `protocol` ; ils restent compris dans
  `docs_total` et dans l'heure écoulée, où `uses_hour_protocol` en donne la part (une campagne ne passe pas pour du
  trafic) ; minutes de l'heure enregistrées `[minute, nombre, octets, protocole]`, l'ancienne forme à trois nombres
  restant lue. Optional `src` ("public" when missing, or "protocol"); protocol documents are counted apart in
  `docs_protocol` and, for the last hour, `uses_hour_protocol`, and stay inside the totals.
  **Seul compte l'expéditeur qui tient le nom abstrait `gdprguardian-usage:<chemin du socket>`** : le processus
  d'accueil du service le prend avant tout travailleur et le garde, le noyau refuse un second détenteur ; un
  travailleur compromis ne peut donc ni gonfler les chiffres ni s'en servir de canal. Tout autre datagramme, mal
  formé ou hors bornes est ignoré ; 2000 bons par seconde au plus (les mauvais n'usent pas ce débit). Seules les
  opérations réussies sont des documents ; l'heure écoulée est une fenêtre de 60 minutes glissante, minute par
  minute. Tailles publiées (page et JSON) arrondies à la précision affichée : une variation ne donne jamais la
  taille exacte d'un document. Service usage: one Unix datagram per finished operation, counted only when sent by
  the holder of the abstract name (the service's front process, never a worker); invalid or out-of-bounds ones
  ignored, at most 2000 valid ones per second; only successful operations count as documents; rolling 60-minute
  window; published sizes rounded to the shown precision.
- **Visiteurs** : comptés sur `GET /` seulement (ni HEAD, ni fichiers, ni API), robots évidents et agent absent
  exclus. Nginx transmet l'adresse déjà tronquée (`X-GG-IP` : /24 en IPv4, /48 au plus en IPv6) ; le démon calcule
  une empreinte SipHash-2-4 de (adresse tronquée, agent) avec une clé de 128 bits tirée au démarrage et à chaque
  changement de jour UTC. L'ensemble des empreintes du jour ne vit qu'en mémoire (200 000 au plus) et disparaît avec
  la clé ; seul le nombre est gardé. Huit agents distincts au plus par adresse tronquée et par jour : un hôte qui
  change d'agent à chaque requête ne gonfle pas le compte, qui reste une borne basse. Un redémarrage oublie les
  empreintes du jour : un visiteur déjà venu ce jour-là est recompté (voulu : rien ne sort du processus). Visitors:
  GET / only, robots excluded; keyed digest of (truncated address, user agent), key redrawn every UTC day, digests
  in memory only, only the count is kept; at most eight user agents per truncated address per day; a restart
  forgets today's digests, so a returning visitor counts again that day.
- **Serveur** : charge du processeur par écarts de `/proc/stat` toutes les 2 s, mémoire utilisée = `MemTotal -
  MemAvailable`. Server load from `/proc/stat` deltas and `/proc/meminfo`.
- **État** : `state.json` (date de lancement, totaux, comptes par sorte et par format, minutes de l'heure écoulée,
  visiteurs), que des nombres ; écrit atomiquement toutes les 60 s (hors du fil du moteur : un disque lent ne fige
  ni pages ni flux) et à l'arrêt (SIGTERM, SIGINT), relu au démarrage, mis de côté (`.corrupt`) s'il est illisible.
  State: numbers only, atomic writes every 60 s (off the runtime thread) and at stop.
- **Journal** : une ligne au démarrage, puis seulement les erreurs, sans aucune donnée de requête. Log: one line at
  start, then errors only, never request data.

## Mise en forme / formatting

Les valeurs écrites par le démon et celles que le JavaScript du site met à jour sont identiques
(`Intl.NumberFormat` « fr-FR » / « en-GB ») : 286 078 comparaisons sans écart contre Node 22. Rules, identical to
the site's JavaScript (`Intl.NumberFormat` fr-FR / en-GB), checked on 286,078 values against Node 22.

| Valeur / value | Français | English |
|---|---|---|
| entier / integer | `3 751` (U+202F) | `3,751` |
| une décimale / one decimal (`cpu_percent`, `ram_percent`) | `12,4` | `12.4` |
| taille / size (base 1024, U+00A0 avant l'unité) | `512 o`, `12,4 Mo`, `1,2 Go` | `512 B`, `12.4 MB`, `1.2 GB` |
| date de lancement / launch date | `25 octobre 2026`, `1er mai 2027` | `25 October 2026` |

Une décimale : écriture la plus courte du nombre (`String(x)`), arrondie moitié vers l'extérieur. Tailles : unité
suivante dès que `Math.round(x * 10) / 10 >= 1024`, octets en entier. Mémoire en pourcentage : `used / total * 100`.

## Gabarits / templates

`build.rs` lit `templates/index.{fr,en}.html`, `static/**` et `data/quality.json`, les découpe, les contrôle et
les embarque : `{{q.<clé>}}` est remplacée à la construction (nombres mis en forme dans la langue de la page,
décimales gardées, chaînes échappées, date ISO seule en toutes lettres) ; `{{live.<nom>}}` (`uses_hour`,
`uses_hour_protocol`, `bytes_hour`, `docs_total`, `docs_protocol`, `bytes_total`,
`visitors_total`, `visitors_today`, `cpu_percent`, `ram_used`, `ram_total`, `ram_percent`, `since`) l'est à chaque
requête ; tout autre `{{...}}` fait échouer la construction, avec sa ligne. Les fichiers statiques textuels sont
précompressés (brotli 11, gzip 9) quand ils y gagnent 5 %. Les essais vérifient aussi les pages rendues : aucune
balise `<script>` en ligne ni `style=`, ni gestionnaire `on*`, ni ressource tierce, chaque `/assets/…` cité
présent, chaque `data-live` connu.

The build splits, checks and embeds the templates, static files (precompressed) and quality numbers; any unknown
placeholder fails the build. Tests also check the rendered pages against the CSP and the embedded files.

Fichier absent : en construction de mise au point, son jeu d'essai (`tests/fixtures/site/`) le remplace avec un
avertissement ; en « release », la construction échoue (sauf `GDPRGUARDIAN_SITE_FIXTURES=1`).
`GDPRGUARDIAN_SITE_FIXTURES=force` impose les jeux d'essai (essais du démon seul). Missing source: fixture in
debug builds, error in release builds unless `GDPRGUARDIAN_SITE_FIXTURES=1`; `=force` always uses the fixtures.

## Construire et essayer / build and test

Cible Linux x86_64 (sockets Unix). Sous WSL, la cible de construction hors de `/mnt` :

```bash
export CARGO_TARGET_DIR=/root/site-target
cd site
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo test                                   # 57 essais : unitaires, routes sans socket, sockets réels
GDPRGUARDIAN_SITE_FIXTURES=force CARGO_TARGET_DIR=/root/site-target-fixtures cargo test   # jeux d'essai
cargo build --release                        # /root/site-target/release/gdprguardian-site
```

Aperçu sans le démon, bibliothèque standard seule / preview without the daemon, standard library only:

```bash
python site/tools/preview.py --check              # gabarits, contrat D, budgets (HTML 45 Ko, CSS 32 Ko, JS 30 Ko
                                                  # bruts, taille gzip affichée ; polices : 3 fichiers et 90 Ko au
                                                  # plus, licence à côté), règles de mise en page gardées
GDPRGUARDIAN_PUBLIC=1 gdprguardian serve --host 127.0.0.1 --port 8000 &   # Linux ou WSL, mode public
python site/tools/preview.py                      # http://127.0.0.1:8099/ et /en ; POST /v1/... vers --api ;
                                                  # /media/ depuis video/out, sans plages d'octets (Safari : Nginx)
python site/tools/preview.py --force-status 429 --force-times 2   # deux 429 + Retry-After, puis le service
curl 'http://127.0.0.1:8099/__force?status=422&code=encrypted_document&times=1'   # à chaud (aperçu seulement)
curl 'http://127.0.0.1:8099/__force?status=0&delay=1.5'                           # plus de forçage, file ralentie
python site/tools/preview.py --quality COPIE.json # aperçu avec un autre quality.json (copie remplie, essai)
```

Après une campagne du protocole public / after a public protocol run (one command: headline keys through
`tools/protocol/merge_quality.py` with all its refusals, then the per-family table keys of the site, `f_*`, `g_*`,
`protocol_version`, then the values between the `<!--q:…-->` markers of `README.md`) :

```bash
python site/tools/protocol_table.py benchmarks/results/protocol-1.1-<date>.json
python site/tools/protocol_table.py --pending                  # tableau et README à « — » (aucune campagne)
python site/tools/protocol_table.py --pending --pending-index   # l'indice aussi : « pas encore mesuré »
```

`merge_quality.py` seul ne suffit pas / alone is not enough: it writes neither `protocol_version` nor the table.
`preview.py --check` refuses a measured index whose `protocol_version` is not `PROTOCOL_VERSION` of
`tools/protocol/spec.py` (the version the site text describes), or whose five index-family rates are "—", and names
the command above.

Essai local / local run:

```bash
GDPRGUARDIAN_STATS_GID= ./gdprguardian-site --socket /tmp/gg/site.sock --stats-socket /tmp/gg/usage.sock \
  --state /tmp/gg/state.json
curl --unix-socket /tmp/gg/site.sock -H 'Host: gardienrgpd.fr' http://localhost/
```

Réglages / settings: `--socket` (`GDPRGUARDIAN_SITE_SOCKET`, défaut `/run/gdprguardian-site/site.sock`),
`--stats-socket` (`GDPRGUARDIAN_STATS_SOCKET`, défaut `/run/gdprguardian-stats/usage.sock`), `--state`
(`GDPRGUARDIAN_SITE_STATE`, défaut `/var/lib/gdprguardian-site/state.json`), `GDPRGUARDIAN_STATS_GID` (groupe du
socket d'usage, défaut 10001, vide : inchangé). Aucune écoute TCP. No TCP listener at all.

Mesures (WSL 2, Ubuntu 24.04, binaire « release ») : binaire 1,06 Mo (1 111 536 octets le 26 octobre 2026 avec le
panneau de la vidéo, polices et pages comprises ; la vidéo elle-même est servie par Nginx), mémoire résidente
1,2 Mo au repos et 6,2 Mo avec 300 flux ouverts, un seul fil ; page servie en 0,29 ms (médiane, client Python
compris) ; premier événement SSE en 21 ms (médiane) pour 300 flux ouverts ensemble ; 26,2 Mo avec 2000 flux (le
plafond). Measured: 1.06 MB binary,
1.2 MB resident at rest, 6.2 MB with 300 open streams, 26.2 MB with 2000 (the cap), one thread; page in 0.29 ms
(median).

## Déploiement / deployment

`deploy/server/install.sh site <binaire>` : groupe `gdprguardian` (gid 10001, celui du conteneur), utilisateur
système `gdprguardian-site` (groupe principal `www-data`), binaire dans `/usr/local/bin`, unité
`deploy/server/gdprguardian-site.service` (bac à sable systemd : aucun réseau, système en lecture seule, aucune
capacité, 128 Mo au plus, socket et réglages du service cachés ; `systemd-analyze security` : 0,6 SAFE), dossier en
mémoire `/run/gdprguardian-stats` (`gdprguardian-site.tmpfiles`). Nginx (`nginx-site.conf`) passe `Host` et
l'adresse tronquée, sans tampon pour `/api/live`, 10 flux par adresse IPv4 ou /64 IPv6 et 64 par /24 ou /48 ; aucun
journal d'accès, journal d'erreurs au niveau `emerg` (jamais d'adresse). Le conteneur du service reçoit
`GDPRGUARDIAN_USAGE_SOCKET=/run/gdprguardian-stats/usage.sock` (`compose.yaml`), au même chemin que le démon. Mise
à jour : `install.sh site <binaire> <dossier video/out>` avant `install.sh base`. La phase `site` contrôle d'abord que
chaque `/media/…?v=<empreinte>` des pages du binaire désigne un fichier fourni de même empreinte, copie les 8 fichiers
de la vidéo dans `/var/www/gdprguardian-media` (seulement ceux qui changent, par renommage), puis installe le démon ;
`base` installe la configuration de Nginx qui sert `/media/` ; `verify` demande à chaque site une plage d'octets de
chaque fichier (206). Update: `site <binary> <video/out folder>` checks every cited digest, copies the video files, then
installs the daemon; `base` installs the Nginx configuration serving `/media/`.

## Licences

MIT. Dépendances (MIT, Apache-2.0 ou BSD) / dependencies: `tokio`, `hyper`, `hyper-util`, `http`, `http-body`,
`httparse`, `httpdate`, `bytes`, `mio`, `socket2`, `libc`, `pin-project-lite`, `futures-core`, `atomic-waker`,
`smallvec`, `signal-hook-registry`, `errno` (MIT ou MIT/Apache-2.0) ; `serde_json`, `serde_core`, `itoa`, `zmij`,
`memchr` (MIT/Apache-2.0, `memchr` Unlicense/MIT) ; `siphasher`, `getrandom`, `cfg-if` (MIT/Apache-2.0).
Construction seulement / build only: `brotli` (BSD-3-Clause et MIT), `alloc-no-stdlib`, `alloc-stdlib`
(BSD-3-Clause), `brotli-decompressor` (BSD-3-Clause/MIT), `flate2`, `crc32fast` (MIT/Apache-2.0), `miniz_oxide`
(MIT/Zlib/Apache-2.0), `adler2` (0BSD/MIT/Apache-2.0), `simd-adler32` (MIT) ; macros `tokio-macros` (MIT), `syn`,
`quote`, `proc-macro2`, `unicode-ident` (MIT/Apache-2.0). `cargo tree -e normal,build --format '{p} | {l}'`.
