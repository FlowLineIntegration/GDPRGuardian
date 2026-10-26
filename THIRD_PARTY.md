# Tiers : données, polices et composants / Third party: data, fonts and components

[Français](#français) · [English](#english)

Le code de Gardien RGPD / GDPR Guardian est sous licence MIT ([LICENSE](LICENSE)). Ce dépôt contient aussi des
fichiers issus de tiers, chacun sous sa propre licence ; tous permettent la redistribution, sous réserve des
attributions ci-dessous. GDPR Guardian's code is MIT-licensed; the third-party files below keep their own licences,
all of which allow redistribution with the attributions given here.

## Français

### Fichiers de tiers présents dans le dépôt

| Fichier | Source | Licence | Attribution exigée |
|---|---|---|---|
| `src/gdprguardian/heuristics/data/names.tsv.gz` | Insee, *Fichier des prénoms*, édition 2025 (naissances 1900-2025) ; Insee, *Fichier des noms de famille*, édition 2008 (naissances 1891-2000) ; agrégats seulement (rangs de fréquence), aucune donnée individuelle | Licence Ouverte / Open Licence 2.0 (Etalab) | « Source : Insee » et date de dernière mise à jour (16/07/2026 pour les prénoms, 22/05/2018 pour les noms) |
| `src/gdprguardian/heuristics/data/postal.tsv.gz` | La Poste, *Base officielle des codes postaux* (08/09/2026) ; Insee, *Code officiel géographique* au 1er janvier 2026 | Licence Ouverte 2.0 | « Source : La Poste » ; « Source : Insee » |
| `src/gdprguardian/heuristics/data/words.txt.gz` | Wikidata, lexèmes français et anglais (formes), extraits le 24/10/2026 | CC0 1.0 | aucune (citée par courtoisie) |
| `site/static/fonts/gr-sans.woff2` (« GR Sans ») | Red Hat Text, sous-ensemble modifié (axe 400-600, latin, renommée) | SIL Open Font License 1.1, sans nom de fonte réservé | Copyright 2024 The Red Hat Project Authors ; texte complet : `site/static/fonts/LICENSE-red-hat-text.txt` ; modifications : `site/static/fonts/LICENSE.txt` |
| `site/static/fonts/gr-mono.woff2` (« GR Mono ») | Red Hat Mono, instance 400, sous-ensemble modifié, renommée | SIL Open Font License 1.1, sans nom de fonte réservé | Copyright 2024 The Red Hat Project Authors ; `site/static/fonts/LICENSE-red-hat-mono.txt` |
| `skills/gdprguardian-local.zip`, `skills/gdprguardian-local-windows-macos.zip` (dossier `wheels/`) | 18 roues Python (pypdfium2 avec PDFium et FreeType, pypdf, mammoth, cobble, beautifulsoup4, python-calamine…) et 42 crates Rust compilées dans les roues `gdprguardian_core` | MIT, BSD-2/3-Clause, Apache-2.0, PSF-2.0, Zlib, Unicode-3.0, CC-BY-4.0 (une partie de pypdfium2)… | listes, textes manquants et crédit FreeType : [`skills/THIRD_PARTY_NOTICES.md`](skills/THIRD_PARTY_NOTICES.md), copié dans chaque archive lourde ; chaque roue garde ses textes dans son `.dist-info` |

Les vidéos et affiches de `video/out/` sont rendues par ce projet avec les polices ci-dessus (OFL : l'usage dans
une image ou une vidéo est libre) ; les icônes (`integrations/claude/plugin/.claude-plugin/icon.png`,
`site/static/favicon.svg`) sont dessinées pour ce projet (MIT).

Les listes manuelles (mois, fêtes, types de voie, formes juridiques, prénoms européens, mots-clés et motifs des
packs `src/gdprguardian/packs/data/*.toml`) sont rédigées pour ce projet, sous licence MIT ; les formats
d'identifiants qu'elles décrivent viennent des spécifications officielles citées dans les fichiers. Le corpus `datasets/fr/` et les phrases de `tests/ner/data/` sont **fictifs**, écrits pour ce projet
(MIT) ; les identifiants y sont calculés, les noms et rues tirés de Faker, seuls les codes postaux et communes sont
réels.

### Ce que le dépôt ne redistribue pas

| Élément | Où il est décrit | Licence | Comment l'obtenir |
|---|---|---|---|
| Modèle NER DistilCamemBERT-NER (optionnel) | `models/MODEL_LICENSES.yaml`, `models/README.md` | MIT (poids) ; entraîné sur WikiNER (CC BY 4.0) | `tools/download_models.py` (révision figée, SHA-256 vérifié) ; attribution recommandée : « DistilCamemBERT-NER par Crédit Mutuel Arkéa (MIT), entraîné sur WikiNER (Nothman et al., CC BY 4.0) » |
| Jeux publics d'évaluation (FR-PII-Bench, MAPA, Gretel, OpenPII, TAB) | `datasets/public/SOURCES.md` | CC BY 4.0, Apache-2.0, MIT | `tools/corpus/fetch_public.py`, dans un cache ignoré par git |
| Corpus réels (BODACC, BOAMP, Judilibre, ParlaMint, Europeana, HIPE NewsEye, MAPA, MEDDOCAN, German LER, TAB) | `docs/CORPUS_REELS.md` § 3 | Licence Ouverte (DILA), CC BY 4.0, CC0, MIT | `tools/corpus/fetch_real.py`, dans un cache hors du dépôt ; seuls les **scores** sont publiés (`benchmarks/results/`) |
| Dépendances Python et crates Rust (paquet, service, démon du site) | `pyproject.toml`, `uv.lock`, `rust/Cargo.lock`, `site/Cargo.lock` | leurs licences respectives | installées par `uv`/`pip`/`cargo` ; les roues publiées n'embarquent que le code du projet, sauf les roues du noyau (crates listées dans `skills/THIRD_PARTY_NOTICES.md`) |

Aucune donnée sous licence non commerciale, ODbL, CC BY-SA, LGPL ou GPL n'est incluse (jeux écartés pour cette
raison : `datasets/public/SOURCES.md`, `docs/CORPUS_REELS.md` § 3).

## English

### Third-party files in this repository

| File | Source | Licence | Required attribution |
|---|---|---|---|
| `src/gdprguardian/heuristics/data/names.tsv.gz` | Insee, *Fichier des prénoms* 2025 edition (births 1900-2025); Insee, *Fichier des noms de famille* 2008 edition (births 1891-2000); aggregates only (frequency ranks), no individual record | Licence Ouverte / Open Licence 2.0 (Etalab) | "Source : Insee" and the last-update date (16/07/2026 for given names, 22/05/2018 for surnames) |
| `src/gdprguardian/heuristics/data/postal.tsv.gz` | La Poste, *Base officielle des codes postaux* (08/09/2026); Insee, *Code officiel géographique* at 1 January 2026 | Licence Ouverte 2.0 | "Source : La Poste"; "Source : Insee" |
| `src/gdprguardian/heuristics/data/words.txt.gz` | Wikidata French and English lexemes (forms), extracted 24/10/2026 | CC0 1.0 | none (credited as a courtesy) |
| `site/static/fonts/gr-sans.woff2` ("GR Sans") | Red Hat Text, modified subset (400-600 axis, Latin, renamed) | SIL Open Font License 1.1, no Reserved Font Name | Copyright 2024 The Red Hat Project Authors; full text `site/static/fonts/LICENSE-red-hat-text.txt`; changes in `site/static/fonts/LICENSE.txt` |
| `site/static/fonts/gr-mono.woff2` ("GR Mono") | Red Hat Mono, weight 400 instance, modified subset, renamed | SIL Open Font License 1.1, no Reserved Font Name | Copyright 2024 The Red Hat Project Authors; `site/static/fonts/LICENSE-red-hat-mono.txt` |
| `skills/gdprguardian-local.zip`, `skills/gdprguardian-local-windows-macos.zip` (`wheels/` folder) | 18 Python wheels (pypdfium2 with PDFium and FreeType, pypdf, mammoth, cobble, beautifulsoup4, python-calamine…) and 42 Rust crates compiled into the `gdprguardian_core` wheels | MIT, BSD-2/3-Clause, Apache-2.0, PSF-2.0, Zlib, Unicode-3.0, CC-BY-4.0 (part of pypdfium2)… | lists, missing texts and the FreeType credit: [`skills/THIRD_PARTY_NOTICES.md`](skills/THIRD_PARTY_NOTICES.md), copied into each heavy archive; every wheel keeps its own texts in its `.dist-info` |

The videos and posters in `video/out/` are rendered by this project with the fonts above (the OFL leaves images and
videos made with a font free); the icons (`integrations/claude/plugin/.claude-plugin/icon.png`,
`site/static/favicon.svg`) were drawn for this project (MIT).

The hand-written lists (months, holidays, street types, legal forms, European given names, the keywords and
patterns of the `src/gdprguardian/packs/data/*.toml` packs) were written for this project, under MIT; the
identifier formats they encode come from the official specifications cited in the files. The
`datasets/fr/` corpus and the sentences in `tests/ner/data/` are **fictitious**, written for this project (MIT):
identifiers are computed, names and streets come from Faker, only postcodes and towns are real.

### What this repository does not redistribute

| Item | Described in | Licence | How to get it |
|---|---|---|---|
| DistilCamemBERT-NER model (optional) | `models/MODEL_LICENSES.yaml`, `models/README.md` | MIT (weights); trained on WikiNER (CC BY 4.0) | `tools/download_models.py` (pinned revision, SHA-256 checked); recommended attribution: "DistilCamemBERT-NER by Crédit Mutuel Arkéa (MIT), trained on WikiNER (Nothman et al., CC BY 4.0)" |
| Public evaluation datasets (FR-PII-Bench, MAPA, Gretel, OpenPII, TAB) | `datasets/public/SOURCES.md` | CC BY 4.0, Apache-2.0, MIT | `tools/corpus/fetch_public.py`, into a git-ignored cache |
| Real corpora (BODACC, BOAMP, Judilibre, ParlaMint, Europeana, HIPE NewsEye, MAPA, MEDDOCAN, German LER, TAB) | `docs/CORPUS_REELS.md` § 3 | Licence Ouverte (DILA), CC BY 4.0, CC0, MIT | `tools/corpus/fetch_real.py`, into a cache outside the repository; only **scores** are published (`benchmarks/results/`) |
| Python dependencies and Rust crates (package, service, site daemon) | `pyproject.toml`, `uv.lock`, `rust/Cargo.lock`, `site/Cargo.lock` | their own licences | installed by `uv`/`pip`/`cargo`; the published wheels hold only the project's code, except the core wheels (crates listed in `skills/THIRD_PARTY_NOTICES.md`) |

No data under a non-commercial, ODbL, CC BY-SA, LGPL or GPL licence is included (datasets rejected for that reason:
`datasets/public/SOURCES.md`, `docs/CORPUS_REELS.md` § 3).
