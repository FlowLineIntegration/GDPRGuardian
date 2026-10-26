# Vidéo de lancement · Launch video

Gardien RGPD / GDPR Guardian 1.0.0. Une vidéo muette sur fond blanc, en français et en anglais, en deux montages :
le **complet** (1920 × 1080, environ 2 min 40 s) et le **court** pour les fils de réseaux sociaux sur téléphone
(1080 × 1350, environ 1 min 15 s, texte plus gros, moins de mots). Tout sort d’une seule source, par une seule
commande. A silent video on a white background, in French and English, in two cuts: the **full** one (1920 × 1080,
about 2 min 40 s) and the **short** one for phone feeds (1080 × 1350, about 1 min 15 s, larger type, fewer words).

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
| 0:54 | 02 · Notre réponse | Six principes : irréversible, cohérent, vérifié, explicable, rapide, rien de conservé. |
| 1:09 | 03 · Trois accès | Schéma : site web, MCP, API REST → Gardien RGPD (un processus neuf par requête) → Markdown anonymisé → votre IA ; les documents disparaissent en entrant dans le moteur et en ressortent balisés. « Par MCP, envoyez le fichier : il ne passe pas par le modèle. Un texte collé est déjà parti. » ; la voie 100 % locale. |
| 1:31 | 04 · Votre version | `git clone`, « Code publié sur GitHub. », licence MIT, vos règles (exemple réel `CLT-204518` → `[CLIENT_ID_1]`), votre serveur (`docker compose`), contribuer (`/issues`). |
| 1:45 | 05 · Les mesures | Tests automatisés (lus dans `quality.json`), 51 façons de déguiser un identifiant, 99,2 % du texte à masquer (synthétique : le meilleur cas), 15 jeux de textes réels et 8 478 documents, 35 à 93 % des mentions masquées sur les textes réels français selon le corpus (1.0.0), BODACC 79 → 98 % (1.0.0, puis les règles du 25 octobre). |
| 2:06 | 05 · Les mesures | L’indice de confiance (« Mesure en cours » tant que `quality.json` ne l’a pas), le protocole écrit avant la mesure, trois limites connues, `gardienrgpd.fr/#protocole`. |
| 2:28 | Fin | « Le meilleur outil open source pour le RGPD et l’IA ! À vous de juger. », adresses, dépôt GitHub, « Offert par Flow Line Intégration », « Guillaume CLEMENT, CTO Data & IA », « Conception : Claude Design », licence MIT. |

Chaque titre arrive avec son contenu (0,35 s d’écart) et les scènes s’enchaînent sans image vide : la suivante
commence 0,4 s avant la fin du fondu de la précédente.

### Le montage court (réseaux sociaux)

1080 × 1350, texte courant de 42 à 66 px, soit 15 à 24 px sur un téléphone de 390 px de large, contre 7 à 8 px pour
le montage complet (adresses, commande et mentions de 28 à 40 px). Sept scènes : ouverture, problème, histoire, trois accès (« Par MCP, envoyez le fichier, pas un texte
collé. »), votre version, mesures et limites (99,2 % sur données synthétiques, 35 à 93 % sur textes réels français,
indice de confiance, deux limites), fin. Les textes plus courts sont dans la clé `social` de `facts.*.json`.

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
  (3 751 et 3 701 aujourd’hui → « 3 700+ ») ;
- `redteam_operators` (51), `recall_direct_pct` (99,2), `eval_docs` (540) ;
- **indice de confiance** : la valeur ne s’affiche que si `confidence_index`, `confidence_ci_low`,
  `confidence_ci_high`, `mention_recall_pct`, `precision_structured_pct` et `overmask_pct` sont tous des nombres
  (le protocole ne publie l’indice qu’avec son intervalle et à côté de la précision et du sur-masquage) ; elle
  s’affiche alors avec son intervalle, la ligne « Mentions masquées · précision · texte neutre masqué à tort » et
  « Campagne du 1er novembre 2026 : … documents » (`protocol_date` et `protocol_docs`, la date mise en toutes
  lettres ; sans date, la ligne s’en passe). Sinon : « Mesure en cours ».

### Quand l’indice de confiance sera publié

Après `python tools/protocol/merge_quality.py …` (docs/PROTOCOLE.md), relancer `python video/render.py` : les quatre
vidéos, leurs affiches et leurs transcriptions se refont avec la valeur. Regarder ensuite `out/review/timeline-*.txt`
(« problems: none », la ligne « read from site/data/quality.json ») et la planche de la scène « Comment nous nous
notons ». Le rendu a été essayé avec un `quality.json` rempli de valeurs fictives : tout tient dans le cadre.

Même chose quand `tests_windows` et `tests_linux` changent (les suites relancées les 25 et 26 octobre comptent
4 162 et 4 109 tests réussis, deux tests de script de skill en échec ; une fois ces deux tests réparés et les
chiffres reportés dans `quality.json`, la vidéo affichera « 4 100+ »).

### Avant de publier la vidéo

La vidéo dit ce qui est vrai aujourd’hui ; avant de la publier, vérifier :

- le dépôt `github.com/FlowLineIntegration/GDPRGuardian` est public (`git clone`, `/issues`) ;
- la voie 100 % locale (plugin Claude, paquet Python) : tant que le paquet n’est pas sur PyPI, le site renvoie
  au guide de la version locale (archives de `skills/`) ;
- le protocole est « écrit avant la mesure » (vrai depuis le 25 octobre) ; l’enregistrement public de ses empreintes
  (docs/PROTOCOLE.md § 15) reste à faire ;
- BODACC 79 → 98 % : le 98 % vient des règles du 25 octobre, qui sont dans le dépôt mais pas dans les paquets 1.0.0
  publiés ; l’écran le dit. Si ces règles sortent sous un nouveau numéro de version, remplacer « les règles du
  25 octobre » par ce numéro dans `facts.*.json`.

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
| Clés de contrôle officielles ; une règle par balise ; 2 Ko en 0,5 ms | `README.md` ; `site/data/quality.json` (`ms_per_doc` 0,56) |
| Par MCP, le fichier ne passe pas par le modèle ; un texte collé est déjà parti | `site/templates/index.fr.html`, « Utiliser » |
| `CLT-204518` → `[CLIENT_ID_1]` | `README.md`, « Vos règles en plus », vérifié avec le moteur |
| Tests, 51, 99,2 %, 540 | `site/data/quality.json`, lu à chaque rendu |
| 15 jeux de textes réels, 8 478 documents | `docs/CORPUS_REELS.md` § 1 |
| 35 à 93 % des mentions masquées, textes réels français (1.0.0) | `site/templates/index.fr.html` ; `docs/CORPUS_REELS.md` § 1 |
| BODACC 79 → 98 %, données inédites | `docs/CORPUS_REELS.md` § 12.1 et § 12.4 (moitié test 78,9 → 97,8 % ; août 2026 inédit 79,3 → 97,6 %) |
| Indice de confiance | `site/data/quality.json`, lu à chaque rendu |
| Protocole écrit avant la mesure : 1 019 385 documents, dont 8 478 réels | `docs/PROTOCOLE.md`, résumé et en-tête |
| Limites | `docs/CORPUS_REELS.md` § 1 et § 12.8 ; `README.md`, « Avertissement » |

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
   place; the site’s story “Guillaume annoys Nadège”; six principles. People get a filled or outlined tag, anything
   else a plain one.
4. **Three ways in (1:09)**: website, MCP, REST API → GDPR Guardian → anonymised Markdown → your AI; “Over MCP, send
   the file: it never goes through the model. Pasted text has already left.”; the 100% local path.
5. **Your own version (1:31)**: `git clone`, “Code published on GitHub.”, MIT licence, your
   rules (`CLT-204518` → `[CLIENT_ID_1]`), your server (`docker compose`), contribute (`/issues`).
6. **The numbers (1:45)**: tests (from `quality.json`), 51 ways to disguise an identifier, 99.2% (synthetic: the best
   case), 15 real-text datasets and 8,478 documents, 35–93% of mentions masked in real French texts by corpus
   (1.0.0), BODACC 79 → 98% (1.0.0, then the 25 October rules); the confidence index (“Being measured” until
   `quality.json` has it), the protocol written before measuring, three known limits, `gdprguardian.com/#protocol`.
7. **Closing (2:28)**: the owner’s line, addresses, GitHub repository, “Offered by Flow Line Intégration”, “Guillaume
   CLEMENT, CTO Data & AI”, “Design: Claude Design”, MIT licence.

### The short cut (social)

1080 × 1350, body text from 42 to 66 px (15 to 24 px on a 390 px wide phone; addresses, command and credits 28 to
40 px), seven scenes: opening, problem, story,
three ways in, your own version, numbers with limits, closing. Its shorter texts live in the `social` key of
`facts.*.json`.

### Re-render

Once: `pip install -r video/requirements.txt` in a virtual environment, then `python -m playwright install chromium`.
Then `python video/render.py` (all four videos), or `--lang fr|en|all` and `--format wide|social|all`. Options:
`--check`, `--frame 42.5 60`, `--quality FILE`, `--crf N`, `--tmp DIR` (see the French section).

**What the video reads from `site/data/quality.json`** at every render: the test count (the smaller of
`tests_windows` and `tests_linux`, rounded down to the hundred, then “+”), `redteam_operators`, `recall_direct_pct`,
`eval_docs`, and the confidence index. The index value shows only when `confidence_index`, `confidence_ci_low`,
`confidence_ci_high`, `mention_recall_pct`, `precision_structured_pct` and `overmask_pct` are all numbers, with its
interval, the recall, precision and over-masking line and the run (`protocol_date` written out, `protocol_docs`);
otherwise “Being measured”. **Once the index is published**, re-run `python video/render.py`: the four videos, their
posters and transcripts follow; check `out/review/timeline-*.txt` and the contact sheet of “How we grade ourselves”.

**Before posting**, see the French checklist: the local install available (PyPI), the
protocol’s digests registered, and the BODACC label updated if the 25 October rules ship under a new version number.

### Reading rule, technique, sources

Every text stays on screen at least 0.35 s per word (short labels count half) and at least 2.5 s; a scene lasts until
everything it shows could have been read in order. The rule sets the length; to shorten, cut words. One HTML/CSS/SVG
page with the site’s fonts, rendered by headless Chromium from a private origin (no network), encoded by ffmpeg.
Every figure has its source in the `sources` key of `facts.en.json`; nothing else is claimed (no hosting claim, no
certification, no user numbers).
