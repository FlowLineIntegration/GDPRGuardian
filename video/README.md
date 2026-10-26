# Vidéo de lancement · Launch video

Gardien RGPD / GDPR Guardian 1.0.0. Une vidéo muette sur fond blanc, en français et en anglais, en deux montages :
le **complet** (1920 × 1080, environ 2 min 48 s) et le **court** pour les fils de réseaux sociaux sur téléphone
(1080 × 1350, environ 1 min 23 s, texte plus gros, moins de mots). Tout sort d’une seule source, par une seule
commande. A silent video on a white background, in French and English, in two cuts: the **full** one (1920 × 1080,
about 2 min 50 s) and the **short** one for phone feeds (1080 × 1350, about 1 min 24 s, larger type, fewer words).

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
| 0:00 | Ouverture | Dès la première image : le nom et une ligne de document, « M. Jean Dupont, 06 12 34 56 78 ». Le geste de la marque : ses crochets se referment sur le nom, laissent la barre orange, puis s’ouvrent sur la balise, « M. [PERSONNE_1], [TEL_1] ». Puis « Anonymisez vos documents, irréversiblement, avant l’IA. », la phrase du propriétaire « Le meilleur outil open source pour le RGPD et l’IA ! À vous de juger. » et les deux adresses. |
| 0:12 | 01 · Le problème | Contrat, dossier RH, dossier médical, e-mail, chacun avec une donnée visible (nom, IBAN, diagnostic, adresse), partent vers un assistant d’IA : « Les données personnelles arrivent chez un tiers. » |
| 0:21 | 01 · Le problème | Les réponses actuelles : caviardage manuel, pseudonymisation réversible (la table de correspondance), « [CENSURÉ] » partout, boîtes noires. |
| 0:32 | 02 · Notre réponse | Un document fictif anonymisé ligne par ligne (sortie réelle, identique avec les paquets 1.0.0 publiés et avec le moteur du dépôt) ; sous le document, sa clé de 256 bits (32 octets) qui disparaît une fois la dernière balise posée : « Clé détruite : aucun retour possible. » Les personnes ont une balise pleine ou cerclée, le reste (e-mail, téléphone, IBAN) une balise simple. |
| 0:43 | 02 · Notre réponse | L’histoire du site : « Guillaume embête Nadège. Nadège frappe Guillaume. », masquage naïf contre balises cohérentes. |
| 0:54 | 02 · Notre réponse | Six principes : irréversible, cohérent (« une personne, une balise, le plus souvent » : 92,2 % des personnes fictives gardent une seule balise), vérifié, explicable, rapide (2 Ko en moins d’une milliseconde), rien de conservé. |
| 1:10 | 03 · Trois accès | Schéma : site web, MCP, API REST → Gardien RGPD (un processus neuf par requête) → Markdown anonymisé → votre IA ; les documents disparaissent en entrant dans le moteur et en ressortent balisés. « Par MCP, envoyez le fichier : il ne passe pas par le modèle. Un texte collé est déjà parti. » ; la voie 100 % locale. |
| 1:32 | 04 · Votre version | `git clone`, « Code publié sur GitHub. », licence MIT, vos règles (exemple réel `CLT-204518` → `[CLIENT_ID_1]`), votre serveur (`docker compose`), contribuer (`/issues`). |
| 1:45 | 05 · Les mesures | Campagne publique du 26 octobre 2026 (moteur déployé) : tests automatisés (lus dans `quality.json`), 91,9 % des 450 000 documents synthétiques sans fuite, 63,7 % des documents piégés sans fuite (51 façons de déguiser un identifiant), 14 jeux de textes réels annotés, dont 6 français, et 8 178 documents, 16,5 à 93 % des documents réels français sans fuite selon la famille, BODACC 89,9 % sans fuite et 97,8 % des mentions masquées. Les pourcentages sont tous des parts de documents sans fuite, la mesure de l’indice (sauf les 97,8 % de mentions du BODACC). |
| 2:07 | 05 · Les mesures | L’indice de confiance, 61,8 % [58,6–66,9] (lu dans `quality.json` ; « Mesure en cours » tant qu’il manque), mentions masquées, précision BODACC et BOAMP, texte neutre masqué à tort, la campagne du 26 octobre 2026 et ses 1 019 385 documents, quatre limites (presse ancienne et MAPA FR : un document sur six sans fuite ; BOAMP : 4 avis sur 10 gardent une mention lisible ; noms allemands, espagnols, italiens, néerlandais, portugais non détectés ; une première barrière), `gardienrgpd.fr/#protocole`. |
| 2:36 | Fin | « Le meilleur outil open source pour le RGPD et l’IA ! À vous de juger. », adresses, dépôt GitHub, « Offert par Flow Line Intégration », « Guillaume CLEMENT, CTO Data & IA », « Conception : Claude Design », licence MIT. |

Chaque titre arrive avec son contenu (0,35 s d’écart) et les scènes s’enchaînent sans image vide : la suivante
commence 0,4 s avant la fin du fondu de la précédente.

### Le montage court (réseaux sociaux)

1080 × 1350, texte courant de 42 à 66 px, soit 15 à 24 px sur un téléphone de 390 px de large, contre 7 à 8 px pour
le montage complet (adresses, commande et mentions de 28 à 40 px). Sept scènes : ouverture, problème, histoire, trois accès (« Par MCP, envoyez le fichier, pas un texte
collé. »), votre version, mesures et limites (91,9 % des documents synthétiques sans fuite ; 16,5 % de la presse ancienne
sans fuite, notre pire cas, même mesure ; l’indice de confiance avec son intervalle, sa définition et la date de la
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
- `redteam_operators` (51), `real_corpora` (14), `real_docs` (8 178) ;
- **indice de confiance** : la valeur ne s’affiche que si `confidence_index`, `confidence_ci_low`,
  `confidence_ci_high` et `mention_recall_pct` sont tous des nombres (le protocole ne publie l’indice qu’avec son
  intervalle et à côté de la précision et du sur-masquage de la campagne, écrits dans `index.guards`) ; elle
  s’affiche alors avec son intervalle, la ligne des garde-fous et « Campagne du 26 octobre 2026 : 1 019 385
  documents » (`protocol_date` et `protocol_docs`, la date mise en toutes lettres ; sans date, la ligne s’en passe).
  Sinon : « Mesure en cours ».

Les autres chiffres des mesures viennent de la campagne publique du 26 octobre 2026
(`benchmarks/results/protocol-2026-10-26.md`) et sont écrits dans `facts.*.json` : 91,9 % des documents
synthétiques sans fuite, 63,7 % des documents piégés sans fuite, 16,5 à 93 % des documents réels français sans
fuite selon la famille, BODACC 89,9 % sans fuite (97,8 % des mentions), presse ancienne 16,5 % (montage court),
BOAMP 4 avis sur 10 avec une mention lisible (limites), et la ligne des
garde-fous (`index.guards` : mentions masquées lues dans `quality.json`, précision BODACC 99,1 % et BOAMP 87,3 %,
texte neutre masqué à tort 0,07 %). Le montage court a sa propre ligne de garde-fous, plus courte
(`social.index.guards`), et une définition datée (`social.index.definition`, où `{date}` devient la date de la
campagne).

### Après une nouvelle campagne

Après `python tools/protocol/merge_quality.py …` (docs/PROTOCOLE.md), reporter les chiffres de la nouvelle campagne
dans `facts.*.json` (figures des mesures, `index.guards`, `social.index.guards`, limites, sources), puis relancer
`python video/render.py` : les quatre vidéos, leurs affiches et leurs transcriptions se refont. Regarder ensuite
`out/review/timeline-*.txt` (« problems: none », la ligne « read from site/data/quality.json ») et les planches des
scènes « Testé, mesuré, publié » et « Comment nous nous notons ». Même chose quand `tests_windows` et `tests_linux`
changent. Le site cite chaque fichier avec son empreinte (`?v=`) : la reporter dans les deux pages après le rendu
(tests/server/test_deploy_config.py le vérifie, avec la taille affichée du montage 4:5).

### Avant de publier la vidéo

La vidéo dit ce qui est vrai aujourd’hui ; avant de la publier, vérifier :

- le dépôt `github.com/FlowLineIntegration/GDPRGuardian` est public (`git clone`, `/issues`) ;
- la voie 100 % locale (plugin Claude, paquet Python) : tant que le paquet n’est pas sur PyPI, le site renvoie
  au guide de la version locale (archives de `skills/`) ;
- le protocole est « écrit avant la mesure » (vrai depuis le 25 octobre) et ses empreintes ont été publiées avant la
  campagne (`PROTOCOL-REGISTRATION.json`) ;
- les chiffres des mesures sont ceux de la campagne du 26 octobre 2026, sur le moteur déployé
  (`1.0.0+0c3ff9fc1fb0`) ; si un autre moteur est déployé, ils ne valent plus pour lui : nouvelle campagne, puis
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
| Tests, 51, 14 jeux de textes réels annotés, 8 178 documents | `site/data/quality.json`, lu à chaque rendu |
| 91,9 % (synthétique), 63,7 % (équipe rouge), 16,5 à 93 % (textes réels français, par famille), BODACC 89,9 % et 97,8 %, presse ancienne 16,5 % | campagne du 26 octobre 2026, `benchmarks/results/protocol-2026-10-26.md` |
| Indice de confiance, intervalle, mentions masquées, campagne | `site/data/quality.json`, lu à chaque rendu |
| Précision BODACC 99,1 %, BOAMP 87,3 % ; texte neutre masqué à tort 0,07 % | garde-fous de la campagne du 26 octobre 2026 |
| Limites | campagne du 26 octobre 2026 (presse ancienne 16,5 %, MAPA FR 16,7 % ; BOAMP 60,7 % sans fuite ; hors périmètre 0 %) ; `README.md`, « Avertissement » |

Rien d’autre n’est affirmé : ni hébergement, ni certification, ni nombre d’utilisateurs.

---

## English

### The full cut

Durations follow the text (see “Reading rule”); English timings are within a second of the French table above
(`out/review/timeline-en.txt`).

1. **Opening (0:00)**: from the very first frame, the name and a line of a document, “Mr Jean Dupont, 06 12 34 56
   78”. The brand’s move: its brackets close over the name, leave the orange bar, then open on the tag, “Mr
   [PERSON_1], [PHONE_1]”. Then “Anonymise your documents, irreversibly, before they reach an AI.”, the owner’s line
   “The best open-source tool for GDPR and AI! You be the judge.” and both addresses.
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
6. **The numbers (1:45)**, all from the public run of 26 October 2026 on the deployed engine: tests (from
   `quality.json`), 91.9% of 450,000 synthetic documents with no leak, 63.7% of adversarial documents with no leak
   (51 ways to disguise an identifier), 14 annotated real-text datasets, 6 of them French, and 8,178 documents,
   16.5–93% of real French documents with no leak by family, BODACC 89.9% with no leak and 97.8% of mentions
   masked; the confidence index, 61.8% [58.6–66.9] (from `quality.json`), the guards, the run and its 1,019,385
   documents, four known limits (old newspapers and MAPA FR: one document in six with no leak; BOAMP: 4 notices in
   10 keep a readable mention; German, Spanish, Italian, Dutch, Portuguese names not detected; a first barrier),
   `gdprguardian.com/#protocol`. Every percentage is a share of documents with no leak, the index’s own measure
   (except BODACC’s 97.8% of mentions).
7. **Closing (2:38)**: the owner’s line, addresses, GitHub repository, “Offered by Flow Line Intégration”, “Guillaume
   CLEMENT, CTO Data & AI”, “Design: Claude Design”, MIT licence.

### The short cut (social)

1080 × 1350, body text from 42 to 66 px (15 to 24 px on a 390 px wide phone; addresses, command and credits 28 to
40 px), seven scenes: opening, problem, story,
three ways in, your own version, numbers with limits (91.9% of synthetic documents with no leak against 16.5% of
old newspapers, the same measure; the index card with its definition and the run’s date), closing. Its shorter texts
live in the `social` key of `facts.*.json`.

### Re-render

Once: `pip install -r video/requirements.txt` in a virtual environment, then `python -m playwright install chromium`.
Then `python video/render.py` (all four videos), or `--lang fr|en|all` and `--format wide|social|all`. Options:
`--check`, `--frame 42.5 60`, `--quality FILE`, `--crf N`, `--tmp DIR` (see the French section).

**What the video reads from `site/data/quality.json`** at every render: the test count (the smaller of
`tests_windows` and `tests_linux`, rounded down to the hundred, then “+”), `redteam_operators`, `real_corpora`,
`real_docs`, and the confidence index. The index value shows only when `confidence_index`, `confidence_ci_low`,
`confidence_ci_high` and `mention_recall_pct` are all numbers, with its
interval, the guards line and the run (`protocol_date` written out, `protocol_docs`); otherwise “Being measured”.
The other figures come from the run of 26 October 2026 (`benchmarks/results/protocol-2026-10-26.md`) and are
written in `facts.*.json`, the guards line included (`index.guards`, and `social.index.guards` for the short cut).
**After a new run**, update those figures in `facts.*.json`, re-run `python video/render.py`, check
`out/review/timeline-*.txt` and the contact sheets, then the pages' `?v=` digests and the 4:5 cut's size.

**Before posting**, see the French checklist: the local install available (PyPI), and the figures still those of the
deployed engine.

### Reading rule, technique, sources

Every text stays on screen at least 0.35 s per word (short labels count half) and at least 2.5 s; a scene lasts until
everything it shows could have been read in order. The rule sets the length; to shorten, cut words. One HTML/CSS/SVG
page with the site’s fonts, rendered by headless Chromium from a private origin (no network), encoded by ffmpeg.
Every figure has its source in the `sources` key of `facts.en.json`; nothing else is claimed (no hosting claim, no
certification, no user numbers).
