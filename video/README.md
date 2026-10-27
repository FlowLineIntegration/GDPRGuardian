# Vidéo de lancement · Launch video

Gardien RGPD / GDPR Guardian 1.0.1. Une vidéo muette sur fond blanc, en français et en anglais, en deux montages :
le **complet** (1920 × 1080, environ 2 min 55 s) et le **court** pour les fils de réseaux sociaux sur téléphone
(1080 × 1350, environ 1 min 26 s, texte plus gros, moins de mots). Tout sort d’une seule source, par une seule
commande. A silent video on a white background, in French and English, in two cuts: the **full** one (1920 × 1080,
about 2 min 54 s) and the **short** one for phone feeds (1080 × 1350, about 1 min 27 s, larger type, fewer words).

| | Français | English |
|---|---|---|
| Complète / full | `out/gardien-rgpd-lancement-fr.mp4` | `out/gdpr-guardian-launch-en.mp4` |
| Courte / social | `out/gardien-rgpd-lancement-fr-social.mp4` | `out/gdpr-guardian-launch-en-social.mp4` |
| Affiches / posters | `out/gardien-rgpd-lancement-fr-poster.png`, `…-fr-social-poster.png` | `out/gdpr-guardian-launch-en-poster.png`, `…-en-social-poster.png` |
| Transcriptions / transcripts | `out/gardien-rgpd-lancement-fr-transcript.txt`, `…-fr-social-transcript.txt` | `out/gdpr-guardian-launch-en-transcript.txt`, `…-en-social-transcript.txt` |
| Chronologie, contrôle de lecture / timeline, reading check | `out/review/timeline-fr.txt`, `timeline-fr-social.txt` | `out/review/timeline-en.txt`, `timeline-en-social.txt` |
| Planches (une image toutes les 2 s) / contact sheets (one frame every 2 s) | `out/review/contact-fr-*.png`, `contact-fr-social-*.png` | `out/review/contact-en-*.png`, `contact-en-social-*.png` |

Format : 30 images/s, H.264 High (yuv420p, BT.709, CRF 17, `faststart`), sans piste audio. Les mêmes fichiers
servent au site et aux réseaux : CRF 17 est déjà sans perte visible (PSNR mesuré de 44 à 53 dB contre les captures
sans perte) ; le débit est bas parce que les images sont fixes et blanches. `--crf 14` donne un fichier plus lourd
si une plateforme l’exige. Format: 30 fps, H.264 High (yuv420p, BT.709, CRF 17, `faststart`), no audio track; the same
files serve the site and the networks (CRF 17 is already visually lossless, 44 to 53 dB PSNR against lossless
captures); `--crf 14` gives a heavier file if a platform asks for one.

Affiches : PNG à palette (coupe médiane, 32 couleurs, sans tramage ; moins si le fichier dépasse 30 000 octets),
car le site les charge avec la page : 19 à 29 Ko au lieu de 62 à 92 Ko, texte toujours net. Posters: palette PNG
(median cut, 32 colours, no dithering; fewer if the file is over 30,000 bytes), since the site loads them with the
page: 19 to 29 KB instead of 62 to 92 KB, text still sharp.

---

## Français

### Le montage complet

Les durées suivent le texte (voir « Règle de lecture ») ; celles-ci sont celles du rendu français, l’anglais est à
une seconde près (`out/review/timeline-en.txt`).

| Début | Partie | Contenu |
|---:|---|---|
| 0:00 | Ouverture | Dès la première image : le nom et une ligne de document, « M. Jean Dupont, 06 12 34 56 78 ». Le geste de la marque : ses crochets se referment sur le nom, laissent la barre orange, puis s’ouvrent sur la balise, « M. [PERSONNE_1], [TEL_1] ». Puis « Anonymisez vos documents, irréversiblement, avant l’IA. », « Outil expérimental et open source, pour contribuer au respect du RGPD. », « Un filtre à intégrer aux outils d’IA du marché. » et les deux adresses. |
| 0:12 | 01 · Le problème | Contrat, dossier RH, dossier médical, e-mail, chacun avec une donnée visible (nom, IBAN, diagnostic, adresse), partent vers un assistant d’IA : « Les données personnelles arrivent chez un tiers. » |
| 0:21 | 01 · Le problème | Les réponses actuelles : caviardage manuel, pseudonymisation réversible (la table de correspondance), « [CENSURÉ] » partout, boîtes noires. |
| 0:32 | 02 · Notre réponse | Un document fictif anonymisé ligne par ligne (sortie réelle, identique avec les paquets 1.0.0 publiés et avec le moteur du dépôt) ; sous le document, sa clé de 256 bits (32 octets) qui disparaît une fois la dernière balise posée : « Clé détruite : aucun retour possible. » Les personnes ont une balise pleine ou cerclée, le reste (e-mail, téléphone, IBAN) une balise simple. |
| 0:43 | 02 · Notre réponse | L’histoire du site : « Guillaume embête Nadège. Nadège frappe Guillaume. », masquage naïf contre balises cohérentes. |
| 0:54 | 02 · Notre réponse | Six principes : irréversible, cohérent (« une personne, une balise, le plus souvent » : 92,2 % des personnes fictives gardent une seule balise), vérifié, explicable, rapide (2 Ko en moins d’une milliseconde), rien de conservé. |
| 1:10 | 03 · Trois accès | Schéma : site web, MCP, API REST → Gardien RGPD (un processus neuf par requête) → Markdown anonymisé → votre IA ; les documents disparaissent en entrant dans le moteur et en ressortent balisés. « Par MCP, envoyez le fichier : il ne passe pas par le modèle. Un texte collé est déjà parti. » ; la voie 100 % locale. |
| 1:32 | 04 · Votre version | `git clone`, « Code publié sur GitHub. », licence MIT, vos règles (exemple réel `CLT-204518` → `[CLIENT_ID_1]`), votre serveur (`docker compose`), contribuer (`/issues`). |
| 1:45 | 05 · Les mesures | Campagne publique du protocole 1.1 (moteur déployé), chiffres lus dans `quality.json` : tests automatisés, part des documents synthétiques sans fuite (et leur nombre), part des documents difficiles sans fuite (toute l’équipe rouge, 51 façons de piéger un texte), 14 jeux de textes réels annotés, dont 6 français, et leurs documents, BOAMP puis BODACC sans fuite avec leurs mentions masquées. Les pourcentages sont des parts de documents sans fuite, la mesure de l’indice, sauf ceux des mentions. |
| 2:07 | 05 · Les mesures | L’indice de confiance, protocole 1.1 (lu dans `quality.json` ; « Mesure en cours » tant qu’il manque), mentions masquées, précision BODACC et BOAMP, texte neutre masqué à tort, la campagne et ses documents, quatre limites (publiés à part : déguisements volontaires, OCR de mauvaise qualité, MAPA FR ; corpus réels déjà vus pendant la mise au point : chiffres optimistes ; noms allemands, espagnols, italiens, néerlandais, portugais surtout manqués, aucun sans la France ; une première barrière), `gardienrgpd.fr/#protocole`. |
| 2:36 | Fin | « Outil expérimental et open source, pour contribuer au respect du RGPD. », « Testez-le, améliorez-le. », adresses, dépôt GitHub, « Offert par Flow Line Intégration », « Guillaume CLEMENT, CTO Data & IA », « Conception : Claude Design », licence MIT, sans garantie. |

Chaque titre arrive avec son contenu (0,35 s d’écart) et les scènes s’enchaînent sans image vide : la suivante
commence 0,4 s avant la fin du fondu de la précédente.

### Le montage court (réseaux sociaux)

1080 × 1350, texte courant de 42 à 66 px, soit 15 à 24 px sur un téléphone de 390 px de large, contre 7 à 8 px pour
le montage complet (adresses, commande et mentions de 28 à 40 px). Sept scènes : ouverture, problème, histoire, trois accès (« Par MCP, envoyez le fichier, pas un texte
collé. »), votre version, mesures et limites (part des documents synthétiques sans fuite ; part de la presse ancienne
sans fuite, OCR de mauvaise qualité publié à part, même mesure ; l’indice de confiance avec son intervalle, sa définition et la date de la
campagne ; deux limites), fin. Les textes plus courts sont dans la clé `social` de `facts.*.json`.

### Refaire le rendu

Une fois :

```bash
python -m venv .venv-video
.venv-video/Scripts/python -m pip install -r video/requirements.txt     # Linux, macOS : .venv-video/bin/python
.venv-video/Scripts/python -m playwright install chromium
```

Puis :

```bash
python video/render.py                                  # les quatre vidéos (fr, en ; complète, courte)
python video/render.py --lang fr --format wide          # une seule
python video/render.py --lang all --format social --workers 6
```

- `--check` : chronologie, contrôle de lecture et transcriptions seulement, sans vidéo (quelques secondes).
- `--frame 42.5 60` : images PNG à ces instants dans `out/review/`, pour vérifier une retouche.
- `--quality FICHIER` : rendu avec un autre `quality.json` (essai de l’affichage de l’indice mesuré).
- `--crf N` : qualité x264 (17 par défaut). `--tmp DOSSIER` : segments temporaires (effacés à la fin).

Durée de rendu mesurée le 26 octobre 2026 sur ce poste (Windows 11, 16 cœurs logiques, `--workers 6`) : environ
1 min par vidéo complète, 25 s par vidéo courte, moins de 3 min pour les quatre.

### Ce que la vidéo lit dans `site/data/quality.json`

À chaque rendu, comme le site :

- **tests** : le plus petit de `tests_windows` et `tests_linux`, arrondi à la centaine inférieure, suivi de « + »
  (4 347 et 4 294 aujourd’hui → « 4 200+ ») ;
- `real_corpora` (14), `real_docs` (8 178) ;
- **chiffres par famille du dernier protocole**, écrits par `site/tools/protocol_table.py` (« — » tant qu’ils
  manquent ; la figure montre alors « — » et son texte sans chiffre) : `f_syn_nl` et `f_syn_docs` (synthétique),
  `hard_index` (documents difficiles, toute l’équipe rouge), `f_boa_nl`, `f_boa_mr`, `f_bod_nl`, `f_bod_mr` (BOAMP, BODACC),
  `f_old_nl` (presse ancienne, montage court) ;
- **indice de confiance** : la valeur ne s’affiche que si `confidence_index`, `confidence_ci_low`,
  `confidence_ci_high` et `mention_recall_pct` sont tous des nombres ; elle s’affiche alors avec son intervalle, la
  ligne des garde-fous (`index.guards` : mentions masquées, précision BODACC `f_bod_pr` et BOAMP `f_boa_pr`, texte
  neutre masqué à tort `g_overmask` ; sans ces clés, `index.guards_nodata`, les mentions seules) et « Campagne du
  … : … documents » (`protocol_date` et `protocol_docs`, la date mise en toutes lettres ; sans date, la ligne s’en
  passe). Sinon : « Mesure en cours ». Le montage court a sa propre ligne de garde-fous, plus courte
  (`social.index.guards`), et une définition datée (`social.index.definition`, où `{date}` devient la date de la
  campagne).

Dans `facts.*.json`, `{q.clé}` est une valeur de `quality.json` (une ou deux décimales, comme elle y est écrite) ;
`fallback_fig` et `fallback_label` la remplacent quand elle manque. Aucun chiffre d’une campagne n’y est écrit en dur.

### Après une nouvelle campagne

Lancer `python site/tools/protocol_table.py benchmarks/results/protocol-<version>-<date>.json` (indice, tableau par
famille du site, README), puis `python video/render.py` : les quatre vidéos, leurs affiches et leurs transcriptions
se refont avec les nouveaux chiffres. Relire les limites de `index.limits` si le protocole change. Regarder ensuite
`out/review/timeline-*.txt` (« problems: none », la ligne « read from site/data/quality.json ») et les planches des
scènes « Testé, mesuré, publié » et « Comment nous nous notons ». Même chose quand `tests_windows` et `tests_linux`
changent. Le site cite chaque fichier avec son empreinte (`?v=`) : la reporter dans les deux pages après le rendu
(tests/server/test_deploy_config.py le vérifie, avec la taille affichée du montage 4:5).

### Avant de publier la vidéo

La vidéo dit ce qui est vrai aujourd’hui ; avant de la publier, vérifier :

- le dépôt `github.com/FlowLineIntegration/GDPRGuardian` est public (`git clone`, `/issues`) ;
- la voie 100 % locale (plugin Claude, paquet Python) : tant que le paquet n’est pas sur PyPI, le site renvoie
  au guide de la version locale (archives de `skills/`) ;
- le protocole 1.1 et ses empreintes ont été publiés avant la campagne (`PROTOCOL-REGISTRATION-1.1.json`) ;
- les chiffres des mesures sont ceux de la dernière campagne du protocole 1.1, sur le moteur déployé (`protocol_engine`
  dans `quality.json`) ; si un autre moteur est déployé, ils ne valent plus pour lui : nouvelle campagne, puis
  nouveaux chiffres.

### Retoucher

- **Tout le texte** est dans `facts.fr.json` et `facts.en.json` (balises permises : `<b>`, `<m>` pour le
  monospace, `<p1>` `<p2>` pour deux personnes, `<p3>` pour une balise qui n’est pas une personne, `<p0>` pour un
  masque naïf, `<n1>` `<n2>` pour les noms d’origine, `<arrow/>`, et `\n`). La clé `social` remplace des textes
  pour le montage court (`null` retire une ligne). Rien n’est à recaler à la main : la chronologie se recalcule.
- **Typographie française**, comme le site (`site/src/format.rs`) : espace fine insécable U+202F, écrite ` `,
  avant « : ; ! ? % » et entre les milliers ; espace insécable U+00A0 (` `) avant une unité (« 2 Ko »).
- **Mise en page et animation** : `scene.html`, `scene.css`, `scene.js` ; une fonction `render(t)` déterministe
  (aucune horloge, aucune transition CSS), donc chaque image est identique quel que soit le moment ou la machine.
- **Aperçu** : depuis la racine du dépôt, `python -m http.server 8000`, puis
  `http://localhost:8000/video/scene.html?lang=fr` (`&fmt=social` pour le montage court, `&t=42` pour sauter à
  42 s ; espace : lecture, flèches : ±1 s).

### Règle de lecture

Chaque texte reste à l’écran au moins 0,35 s par mot (les courtes étiquettes comptent pour moitié ; une suite de
nombres compte pour un mot) et au moins 2,5 s, et une scène dure jusqu’à ce que tout ce qu’elle montre ait pu être
lu dans l’ordre depuis son début. `render.py` vérifie la règle et l’écrit dans `out/review/timeline-*.txt`
(« problems: none »). C’est elle qui fixe la durée : pour raccourcir, retirer des mots (environ 3 s pour 8 mots).

### Technique

Une page HTML/CSS/SVG aux polices du site (`site/static/fonts` : « GR Sans » = Red Hat Text, « GR Mono » = Red Hat
Mono, licence OFL), chargée par Chromium sans tête (Playwright) depuis une origine privée servie par `render.py`
depuis le dépôt : aucune requête réseau. Images capturées en parallèle par tranches (une image identique à la
précédente n’est capturée qu’une fois), encodées par ffmpeg (libx264, `-tune animation`, sans images B pour que les
tranches se joignent sans réencodage), réunies avec `faststart`. ffmpeg : `$GR_FFMPEG`, sinon le binaire
d’`imageio-ffmpeg`, sinon celui du `PATH`. Les planches sont extraites de la vidéo finale elle-même.

### Sources des chiffres

Chaque chiffre affiché a sa source dans la clé `sources` de `facts.fr.json` et `facts.en.json`. En bref :

| Chiffre affiché | Source |
|---|---|
| « M. Jean Dupont, 06 12 34 56 78 » → « M. [PERSONNE_1], [TEL_1] » ; document de démonstration | exemple de l’API du site ; sortie identique des paquets `dist/1.0.0` et du moteur du dépôt, vérifiée le 26 octobre 2026 |
| Données des cartes du problème | fictives (mêmes personnes que le document de démonstration) |
| Clé de 256 bits par document, détruite ; aucune table | `site/templates/index.fr.html` (Architecture) ; `README.md` |
| « Guillaume embête Nadège » | `site/templates/index.fr.html`, « L’histoire », repris tel quel ; sortie vérifiée |
| Une personne, une balise, le plus souvent | `tools/corpus/evaluate.py`, moteur déployé (empreinte de sonde vérifiée), 26 octobre 2026 : 92,2 % de 2 463 personnes fictives |
| Clés de contrôle officielles ; une règle par balise ; 2 Ko en moins d’une milliseconde | `README.md` ; `site/data/quality.json` (`ms_per_doc` 0,56) ; `benchmarks/results/bench-2026-10-26-standard-rules3.md` |
| Par MCP, le fichier ne passe pas par le modèle ; un texte collé est déjà parti | `site/templates/index.fr.html`, « Utiliser » |
| `CLT-204518` → `[CLIENT_ID_1]` | `README.md`, « Vos règles en plus », vérifié avec le moteur |
| Tests, 14 jeux de textes réels annotés et leurs documents | `site/data/quality.json`, lu à chaque rendu |
| Synthétique, documents difficiles (toute l’équipe rouge), BOAMP, BODACC (sans fuite, mentions), presse ancienne | dernière campagne du protocole 1.1 (`benchmarks/results/protocol-1.1-<date>.md`), via `site/data/quality.json` (`f_*`, `hard_index`), lu à chaque rendu |
| Indice de confiance, intervalle, mentions masquées, campagne | `site/data/quality.json`, lu à chaque rendu |
| Précision BODACC, BOAMP ; texte neutre masqué à tort | garde-fous de la même campagne, via `site/data/quality.json` (`f_bod_pr`, `f_boa_pr`, `g_overmask`) |
| Limites | `docs/PROTOCOLE.md`, « Version 1.1 » (familles publiées à part, moitiés test non aveugles) ; hors périmètre, 0 % des mentions à la campagne 1.0 (`benchmarks/results/`) ; `README.md`, « Avertissement » |

Rien d’autre n’est affirmé : ni hébergement, ni certification, ni nombre d’utilisateurs.

---

## English

### The full cut

Durations follow the text (see “Reading rule”); English timings are within a second of the French table above
(`out/review/timeline-en.txt`).

1. **Opening (0:00)**: from the very first frame, the name and a line of a document, “Mr Jean Dupont, 06 12 34 56
   78”. The brand’s move: its brackets close over the name, leave the orange bar, then open on the tag, “Mr
   [PERSON_1], [PHONE_1]”. Then “Anonymise your documents, irreversibly, before they reach an AI.”, “An experimental,
   open-source tool to help respect the GDPR.”, “A filter to plug into the AI tools on the market.” and both addresses.
2. **The problem (0:12)**: a contract, an HR file, a medical record and an e-mail, each with a visible piece of data,
   go to an AI assistant: “Personal data ends up with a third party.” Then today’s answers: manual redaction,
   reversible pseudonymisation, “[REDACTED]” everywhere, black boxes.
3. **Our answer (0:32)**: a fictitious document anonymised line by line (real output, identical with the published
   1.0.0 packages and the repository engine), its 256-bit key shown as 32 bytes and destroyed once the last tag is in
   place; the site’s story “Guillaume annoys Nadège”; six principles (“one person, one tag, most of the time”: 92.2%
   of fictitious people keep a single tag; 2 KB in under a millisecond). People get a filled or outlined tag, anything
   else a plain one.
4. **Three ways in (1:10)**: website, MCP, REST API → GDPR Guardian → anonymised Markdown → your AI; “Over MCP, send
   the file: it never goes through the model. Pasted text has already left.”; the 100% local path.
5. **Your own version (1:31)**: `git clone`, “Code published on GitHub.”, MIT licence, your
   rules (`CLT-204518` → `[CLIENT_ID_1]`), your server (`docker compose`), contribute (`/issues`).
6. **The numbers (1:45)**, all from the latest public run of protocol 1.1 on the deployed engine, read from
   `quality.json`: tests, the share of synthetic documents with no leak (and their count), the share of difficult
   documents with no leak (the whole red team, 51 ways to trap a text), 14 annotated real-text datasets, 6 of them French, and their
   documents, BOAMP then BODACC with no leak and their mentions masked; the confidence index, protocol 1.1, the guards,
   the run and its documents, four known limits (published apart: deliberate obfuscations, low-quality OCR, MAPA FR;
   real corpora already seen while tuning: optimistic figures; German, Spanish, Italian, Dutch, Portuguese names not
   detected; a first barrier), `gdprguardian.com/#protocol`. Every percentage is a share of documents with no leak,
   the index’s own measure, except the mentions masked.
7. **Closing (2:38)**: the owner’s line, addresses, GitHub repository, “Offered by Flow Line Intégration”, “Guillaume
   CLEMENT, CTO Data & AI”, “Design: Claude Design”, MIT licence.

### The short cut (social)

1080 × 1350, body text from 42 to 66 px (15 to 24 px on a 390 px wide phone; addresses, command and credits 28 to
40 px), seven scenes: opening, problem, story,
three ways in, your own version, numbers with limits (the share of synthetic documents with no leak against that of
old newspapers, low-quality OCR published apart, the same measure; the index card with its definition and the run’s date), closing. Its shorter texts
live in the `social` key of `facts.*.json`.

### Re-render

Once: `pip install -r video/requirements.txt` in a virtual environment, then `python -m playwright install chromium`.
Then `python video/render.py` (all four videos), or `--lang fr|en|all` and `--format wide|social|all`. Options:
`--check`, `--frame 42.5 60`, `--quality FILE`, `--crf N`, `--tmp DIR` (see the French section).

**What the video reads from `site/data/quality.json`** at every render: the test count (the smaller of
`tests_windows` and `tests_linux`, rounded down to the hundred, then “+”), `real_corpora`, `real_docs`, the
per-family figures of the latest protocol written by `site/tools/protocol_table.py` (`f_syn_nl`, `f_syn_docs`,
`hard_index`, `f_boa_nl`, `f_boa_mr`, `f_bod_nl`, `f_bod_mr`, `f_old_nl`; “—” until measured, and the figure then shows
“—” with a text without a number), and the confidence index. The index value shows only when `confidence_index`,
`confidence_ci_low`, `confidence_ci_high` and `mention_recall_pct` are all numbers, with its interval, the guards line
(`f_bod_pr`, `f_boa_pr`, `g_overmask`; without them `index.guards_nodata`, mentions only) and the run (`protocol_date`
written out, `protocol_docs`); otherwise “Being measured”. No run figure is hard-coded in `facts.*.json`.
**After a new run**, run `python site/tools/protocol_table.py benchmarks/results/protocol-<version>-<date>.json`, then
`python video/render.py`; check `out/review/timeline-*.txt` and the contact sheets, then the pages' `?v=` digests
and the 4:5 cut's size.

**Before posting**, see the French checklist: the local install available (PyPI), and the figures still those of the
deployed engine.

### Reading rule, technique, sources

Every text stays on screen at least 0.35 s per word (short labels count half) and at least 2.5 s; a scene lasts until
everything it shows could have been read in order. The rule sets the length; to shorten, cut words. One HTML/CSS/SVG
page with the site’s fonts, rendered by headless Chromium from a private origin (no network), encoded by ffmpeg.
Every figure has its source in the `sources` key of `facts.en.json`; nothing else is claimed (no hosting claim, no
certification, no user numbers).
