# gdprguardian-core

Noyau Rust optionnel de [Gardien RGPD](../README.md), exécuté sans le GIL Python. Le moteur Python reste la
référence : chaque module produit exactement les mêmes zones, valeurs, scores et textes (tests différentiels
sur le corpus et fuzzing Hypothesis). Les tables (classes de caractères, transcodage, lexiques, mots-clés)
viennent de Python au démarrage : une seule source de vérité.

| Module | Rôle |
|---|---|
| `prepare.rs`, `text.rs` | normalisation, repliement, table de positions, détection de la langue |
| `keywords.rs` | index de mots-clés (Aho-Corasick) |
| `scanner.rs`, `windows.rs` | motifs des packs à temps linéaire, recherche limitée aux fenêtres candidates |
| `unicode.rs` | table Unicode unique (classes de `str` et de `re`, casse, repliement), construite par Python, plans hors BMP chargés à la demande |
| `pattern/` | compilation exacte des motifs depuis l'arbre de `re` : `\w`, `\d`, `\s` et `re.IGNORECASE` de Python, look-arounds de tête et de fin |
| `validators/` | clés de contrôle de tous les packs (FR, INTL, BE, CH, DE, ES, IT, LU, MC, NL, PT), sémantique `str` de Python (`pystr.rs`) |
| `names/` | détecteur de noms de personnes français |
| `detectors/` | adresses, organisations, e-mails, IBAN, MRZ, dates de naissance du NIR |
| `finalize/` | résolution, propagation, rendu, portée irréversible (BLAKE2b à clé, clé effacée) |
| `engine/` | moteur fusionné : détection et finalisation d'un document en deux appels, zones gardées en Rust |
| `tabular/` | lecture des classeurs xlsx (ZIP strict, XML en flux, limites anti-bombe), identique à python-calamine |

Optional Rust core of GDPR Guardian, run without the Python GIL. The Python engine stays the reference: each
module yields exactly the same spans, values, scores and texts (differential tests on the corpus and
Hypothesis fuzzing). Tables (character classes, translation, lexicons, keywords) come from Python at start-up:
a single source of truth. Modules: text preparation and language, one shared Unicode table, keyword index,
exact compilation of `re` patterns (Python's `\w`/`\d`/`\s`, `re.IGNORECASE`, leading and trailing
look-arounds) into a linear-time scan with candidate windows, checksums of every country pack, French person
names, addresses/organisations/e-mails/IBAN/MRZ/NIR birth dates, finalisation (resolution, propagation,
rendering, irreversible keyed-BLAKE2b scope), the fused engine (detection, then finalisation: two Rust calls
per document, spans kept in Rust), and the xlsx reader. Organisation rules sent with a request are compiled with
`Scanner(..., untrusted=True)`: bounded automata and budget, one thread.

```bash
maturin build --release --manifest-path rust/Cargo.toml
pip install --force-reinstall --no-index --find-links rust/target/wheels gdprguardian-core
```

Désactivation / disable: `GDPRGUARDIAN_PURE_PYTHON=1` (ou / or `Settings(native=False)`).
