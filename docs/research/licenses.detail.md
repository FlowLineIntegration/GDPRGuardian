# licenses details

### Items
| name | license | verdict | reco | status | notes |
|---|---|---|---|---|---|
| presidio-analyzer | MIT | ok | optional | 2.2.364, uploaded 2026-07-22, active | Core deps are permissive: phonenumbers (Apache-2.0), regex, tldextract, spaCy (MIT). Do not install the 'langextract' extra (pulls openai, so an LLM). Its default spaCy model choice would bring in non-permissive fr/es/it models. Useful as a recognizer framework or reference. |
| presidio-anonymizer | MIT | ok | optional | 2.2.364, 2026-07-22 | Requires cryptography<49 while the latest is 50.0.2, a likely resolver conflict. Its operators (replace, hash, encrypt) are simple; probably easier to write our own indexed-placeholder engine. |
| presidio-structured | MIT | ok | borrow-ideas | 0.0.8, 2026-07-22, alpha | Column-level anonymization of tables (pandas). Relevant to Excel/CSV: detect the PII type per column from header and samples, then apply it to the whole column. Too immature to depend on. |
| spaCy | MIT | ok | optional | 3.8.16 | Library is MIT, but each model has its own licence (see the model items). Needed only if Presidio's NLP engine or spaCy tokenization is used. |
| spaCy fr_core_news_sm/md/lg | LGPLLR | caution | avoid | 3.8.0 | Lesser GPL for Linguistic Resources (trained on Sequoia and WikiNER). Redistributing it means shipping the licence and the resource source, and changes must stay LGPLLR. Do not bundle. Use the MIT CamemBERT NER models or GLiNER instead. |
| spaCy es_core_news_* | GPL-3.0 | avoid | avoid | 3.8.0 | GNU GPL 3.0 (trained on AnCora and WikiNER). Incompatible with the MIT distribution goal. |
| spaCy it_core_news_* | CC-BY-NC-SA-3.0 | avoid | avoid | 3.8.0 | Non-commercial and share-alike (trained on ISDT and WikiNER). Unusable for a commercial SaaS. |
| spaCy de_core_news_* | MIT | caution | optional | 3.7.0 card (3.8.0 released) | Weights are MIT but trained on the TIGER corpus, Tiger2Dep and WikiNER; TIGER corpus terms were not verified (data provenance risk). Fine as a user-downloaded optional model. |
| spaCy en_core_web_* | MIT | caution | optional | 3.7.0 card | Weights MIT; trained on OntoNotes 5 (an LDC-licensed corpus), ClearNLP and WordNet. It is Presidio's default model, so the risk is widely accepted in practice, but the provenance caveat should be recorded. |
| spaCy xx_ent_wiki_sm | MIT | ok | optional | 3.7.0 card | Trained on WikiNER only (CC-BY-4.0 per figshare). Multilingual PER/LOC/ORG/MISC; low accuracy. Small fallback. |
| python-stdnum | LGPL-2.1-or-later | caution | borrow-ideas | 2.2, 2026-01-04 | Covers FR NIR, SIREN, SIRET, TVA, NIF, RCS and excise numbers, plus about 200 other formats. Use its format list as a checklist and re-implement from official specs. If used as a dependency instead, do not vendor it; include it in Docker only with the LGPL licence and source. |
| stdnum-js | MIT | ok | borrow-ideas | no GitHub releases visible; 525 commits | MIT (Copyright 2020 David Koblas), but its README credits python-stdnum for 'many of the checksum algorithm sources', so lineage is ambiguous. Use as a cross-check only. |
| django-localflavor | BSD-3-Clause | ok | borrow-ideas | 5.1, 2026-08-01 | BSD validators for many countries. Requires Django, so do not depend on it. Logic can be copied with the BSD notice kept. |
| Faker | MIT | ok | adopt | 40.43.0 | For synthetic test corpora and optional surrogate values. Also an LLM-free way to build clean NER training data (templates plus INSEE names). |
| phonenumbers | Apache-2.0 | ok | adopt | 9.0.41 | Port of Google libphonenumber, per-region metadata. Keep its LICENSE/NOTICE in the Docker image. Memory: lazy-loads metadata. |
| schwifty | MIT | caution | optional | 2026.10.0 | MIT itself, but requires pycountry (LGPL-2.1-only) and bundles a bank registry whose data licence was not stated. IBAN mod-97 (ISO 13616) is easy to write ourselves. |
| pycountry | LGPL-2.1-only | caution | avoid | 26.2.16, 2026-02-17 | Wraps Debian iso-codes. Replace with iso3166 (MIT) plus Babel/CLDR names to keep LGPL out of the tree; watch transitive imports (schwifty). |
| iso3166 | MIT | ok | adopt | 3.0.0, 2026-09-03 | Country codes for per-country config and 'auto' mode; drop-in for pycountry's country lookup. |
| babel | BSD-3-Clause | ok | adopt | 2.18.0 | Localized territory and language names, number and date formats from CLDR. The CLDR (Unicode licence) notice was not shown in the LICENSE file; check the wheel's notices. |
| lingua-language-detector | Apache-2.0 | ok | adopt | 2.2.0 | Rust core with bundled n-gram models; accurate on short texts. Load only the needed languages to cap memory. Good choice for 'auto' language/country detection. |
| fastText lid.176 | CC-BY-SA-3.0 | caution | optional | fastText repo archived 2024-03-19 (code MIT) | Shipping it unmodified next to MIT code is aggregation and needs attribution. A quantized or converted copy is adapted material and must stay CC-BY-SA. Unmaintained. Prefer lingua or py3langid. |
| py3langid | BSD-3-Clause | ok | adopt | 0.4.0 | Tiny, fast fallback language ID with a bundled model. Training-data provenance of the original langid.py model is not documented in metadata. |
| google-re2 | BSD-3-Clause | ok | adopt | 1.1.20251105 | Linear-time matching with no ReDoS, which matters for an untrusted multi-tenant service. Lacks lookarounds and backreferences, so design patterns for it and validate with checksums afterwards. |
| pyre2 | BSD-3-Clause | ok | optional | 0.3.14, 2026-09-25 | Cython RE2 binding (andreasvc) with re-module compatibility. An alternative to google-re2; pick one. |
| hyperscan (python) / Vectorscan | MIT (binding); BSD-3-Clause (Vectorscan, plus BSL-1.0 Boost headers) | ok | optional | 0.9.1 | Wheels statically link Vectorscan. Intel Hyperscan 5.5 and later is proprietary, so never build against Intel's releases. Worth it only for hundreds of patterns at once. |
| Intel Hyperscan >=5.5 | LicenseRef-Intel-Proprietary | avoid | avoid | closed since 5.5; last BSD release 5.4.2 | Use Vectorscan (BSD) instead. |
| pyahocorasick | BSD-3-Clause (parts public domain) | ok | adopt | 2.3.1 | C Aho-Corasick automaton for large gazetteers (first names, communes, organizations). Pickle-able; memory-efficient. |
| flashtext | MIT | ok | avoid | 2.7, 2018-02-16 (abandoned) | Unmaintained for 8 years; pure Python. pyahocorasick replaces it. |
| regex (mrab) | Apache-2.0 AND CNRI-Python | ok | adopt | 2026.9.29 | Unicode properties (\p{Lu}) and fuzzy matching. Backtracking engine, so use timeouts or bounded patterns for untrusted input. Already a Presidio dependency. |
| gliner (library) | Apache-2.0 | ok | adopt | 0.2.29, 2026-09-08 | Core requires torch and transformers; extras exist for onnx and openvino. For CPU, export to ONNX and int8-quantize, then run with onnxruntime only. |
| urchade/gliner_multi-v2.1 | Apache-2.0 | ok | adopt | v2.1 (v0/v1 were CC-BY-NC-4.0) | Base microsoft/mdeberta-v3-base (MIT, CC100). Trained on urchade/pile-mistral-v0.1 (Apache-2.0 tag, empty card; presumably Pile text annotated by Mistral). Never use the older CC-BY-NC gliner_multi. |
| urchade/gliner_multi_pii-v1 | Apache-2.0 | ok | adopt | v1 | Fine-tuned from gliner_multi-v2.1 on urchade/synthetic-pii-ner-mistral-v1 (Apache-2.0; covers en, fr, it and 2 others; generator not documented). Best-provenance baseline PII model. Pin the HF revision SHA. |
| knowledgator gliner-pii-* (v1.0) | Apache-2.0 | caution | optional | created 2025-09-24 | Card names no base model and no training data; only the evaluation set is given. Licence fine, provenance unknown; benchmark it but record the gap. |
| knowledgator gliner-bi-*-v2.0 | Apache-2.0 | caution | optional | v2.0 | Text encoder ettin-encoder-150m; pre-trained on 8M FineFineWeb samples annotated with GPT-4o (OpenAI terms chain). English only. Bi-encoder caches label embeddings, which helps throughput. |
| knowledgator gliner-stream-pii-v1.0 | Apache-2.0 | ok | avoid | eval dated 2026-07-24 | Uses a Qwen3-0.6B causal (decoder LLM) backbone, which breaks the 'no LLM' constraint and is heavy on CPU. Training data not stated. |
| fastino GLiNER2 (gliner2 lib + gliner2-multi-v1) | Apache-2.0 | caution | optional | gliner2 2.1.0 (2026-10-09); multi-v1 updated 2026-09-28 | Covers fr, en, es, de, it, pt. Per the paper, all 254k training examples were annotated or generated by GPT-4o (https://arxiv.org/pdf/2507.18546), so OpenAI terms provenance is a risk. Library itself is clean. |
| nvidia/gliner-PII | LicenseRef-NVIDIA-Open-Model-License | avoid | borrow-ideas | OML version 2025-10-24 | Custom licence: required NOTICE text, rights end if safety guardrails are bypassed, NVIDIA may update the terms, Delaware law. English only; base gliner_large-v2.1. Reuse its CC-BY-4.0 training data instead. |
| nvidia/Nemotron-PII (dataset) | CC-BY-4.0 | ok | adopt | modified 2025-12-17 | Synthetic persona-based data made with NeMo Data Designer; English only. Usable for fine-tuning or eval with attribution. Not suitable for French national IDs. |
| E3-JSI/gliner-multi-pii-domains-v1 | Apache-2.0 | caution | optional | last updated 2024-12-06 | Fine-tuned from gliner_multi_pii-v1 on E3-JSI/synthetic-multi-pii-ner-v1 (MIT; 7 languages incl. fr/de; healthcare, finance and legal domains). Generator LLM not documented. Stale. |
| microsoft/mdeberta-v3-base | MIT | ok | adopt | stable | Base encoder of GLiNER multi; trained on CC100. Good base for our own fine-tuning. |
| onnxruntime | MIT | ok | adopt | 1.31.0 | Recommended CPU runtime: int8 quantization and thread control, and it avoids shipping torch. |
| optimum | Apache-2.0 | ok | optional | 2.3.0 | For ONNX export and quantization at build time. Keep it out of the runtime image. |
| openvino | Apache-2.0 | ok | optional | 2026.4.1 | Possibly faster on Intel Xeon; benchmark it against onnxruntime. |
| transformers | Apache-2.0 | ok | optional | 5.20.2 | Needed at export or training time. At runtime, the 'tokenizers' package (Rust) plus onnxruntime is lighter. |
| torch | BSD-3-Clause AND Apache-2.0 AND BSL-1.0 AND MIT (+others) | ok | optional | 2.14.1 | Default Linux PyPI wheels depend on nvidia-* packages (e.g. nvidia-cublas-cu12 = LicenseRef-NVIDIA-Proprietary, https://pypi.org/project/nvidia-cublas-cu12/). Use the download.pytorch.org CPU index or drop torch from runtime. |
| cmarkea/distilcamembert-base-ner | MIT | ok | adopt | stable | French PER/LOC/ORG/MISC; trained on wikiner_fr (WikiNER is CC-BY-4.0 on figshare: https://api.figshare.com/v2/articles/5462500). Distilled, about 2x faster than CamemBERT on CPU. |
| Jean-Baptiste/camembert-ner | MIT | ok | optional | stable | Full CamemBERT-base, trained on WikiNER-fr. More accurate, slower than the distilled model. |
| almanach/camembert-base | MIT | ok | borrow-ideas | stable | Pretrained on OSCAR (OSCAR licence not verified). A base for our own French PII fine-tune. |
| flair + classic models | MIT (lib); models: non-commercial | avoid | avoid | 0.15.1, 2025-02-05 | The 'Flair 1.0 - All Classic Models' collection says 'Noncommercial use only'. ner-german is trained on CoNLL-03; ner-french has no licence tag. Library also pulls boto3, gensim and similar. |
| stanza + models | Apache-2.0 (code); models follow UD treebank licences | caution | avoid | 1.15.0 | UD treebanks are licensed one by one and some are CC-BY-NC-SA. Would need a model-by-model audit; heavy on CPU anyway. |
| ai4privacy datasets (pii-masking-200k/300k/400k etc.) | LicenseRef-ai4privacy (non-commercial) | avoid | avoid | updated 2026-06-03 | Academic and non-commercial only; redistribution and derivative works need a written licence. open-pii-masking-500k shows CC-BY-4.0 on its card but 'other' in the API, an inconsistency. |
| ai4privacy *-anonymiser-openpii models | MIT | caution | avoid | 2025-03/06 | ModernBERT-base encoder despite the 'llama' name. Trained on open-pii-masking-500k, whose licence metadata is inconsistent. Treat the licence chain as unclear. |
| piiranha-v1 | CC-BY-NC-ND-4.0 | avoid | avoid | v1 | Non-commercial, no derivatives; trained on ai4privacy 400k. |
| OpenMed PII French models | Apache-2.0 | avoid | avoid | v1 | Weights tagged Apache-2.0 but trained on ai4privacy/pii-masking-400k (non-commercial; derivatives need written licence). The licence chain conflicts; do not redistribute. |
| fastmcp | Apache-2.0 | ok | adopt | 4.1.3 | MCP server framework. Keep its LICENSE in the Docker notices. |
| mcp (Python SDK) | MIT | ok | adopt | 2.3.0 | Official SDK; fastmcp builds on it. |
| pydantic | MIT | ok | adopt | 2.14.1 (2026-10-11) | Request and config schemas (country packs). |
| MarkItDown | MIT | ok | adopt | 0.1.9, 2026-10-21, Beta | Light. Core deps are bs4, markdownify, magika (Apache-2.0) and defusedxml. Excel: pandas+openpyxl, all sheets including hidden, one table per sheet; comments and merged cells are ignored. Source: https://raw.githubusercontent.com/microsoft/markitdown/main/packages/markitdown/src/markitdown/converters/_xlsx_converter.py |
| Docling | MIT | ok | optional | 2.142.1 | The standard extra pulls torch, torchvision, rapidocr, docling-ibm-models, pypdfium2 and openpyxl, which is heavy for CPU. The Excel backend is the best found: merged cells, several tables per sheet, comments, hidden sheets kept apart (INVISIBLE layer); .xls goes through LibreOffice (MPL-2.0). |
| Docling models (docling-models, layout-heron) | Apache-2.0 / CDLA-Permissive-2.0 | caution | optional | current | Repo is tagged with both licences without saying which applies to which model; layout-heron is Apache-2.0. CDLA-Permissive-2.0 is permissive but outside the listed ok set. Training sets (DocLayNet etc.) not verified. |
| pypdf | BSD-3-Clause | ok | adopt | 6.21.2 | Pure Python text extraction; minimal footprint. |
| pdfminer.six | MIT | ok | adopt | 20260107 | Layout-aware text extraction; used by MarkItDown and pdfplumber. |
| pdfplumber | MIT | ok | adopt | 0.11.10, 2026-06-15 | Table extraction from PDFs; depends on pdfminer.six and pypdfium2. |
| PyMuPDF / pymupdf4llm | AGPL-3.0-only OR LicenseRef-Artifex-Commercial | avoid | avoid | PyMuPDF 2.0; pymupdf4llm 2.0 = empty placeholder | AGPL network clause would force publishing the source of the whole hosted service, or buying a commercial licence. |
| pypdfium2 | Apache-2.0 OR BSD-3-Clause (+ PDFium BSD-style and bundled deps) | ok | adopt | 5.14.0 | Fast C++ PDF engine. Binary distributions must ship the PDFium and dependency licences (BUILD_LICENSES); some builds link libgcc. |
| python-docx | MIT | ok | adopt | 1.2.0 | DOCX parsing including headers/footers and comments (to anonymize too). |
| mammoth | BSD-2-Clause | ok | adopt | 1.13.0 | Semantic DOCX to HTML, then markdownify. Used by MarkItDown. |
| openpyxl | MIT | ok | adopt | 3.1.5, 2024-06-28 (no release in ~28 months) | Needed for xlsx metadata: comments, hidden sheets, merged cells, docProps (author), named ranges, headers/footers. Use read_only mode for big files. Pair with defusedxml. Release cadence is a maintenance risk. |
| python-calamine | MIT | ok | adopt | 0.9.0 (Beta) | Rust calamine (MIT) reads xls, xlsx, xlsm, xlsb, xla, xlam and ods with one engine, much faster and lighter than openpyxl. Reads cell values; the crate also exposes formulas and VBA. Recommended primary Excel reader. |
| fastexcel | MIT | ok | optional | 0.21.0 | calamine plus Arrow; pyarrow (Apache-2.0) and polars/pandas are optional extras. Useful for very large sheets and column-wise detection. |
| xlrd | BSD-3-Clause | ok | optional | 2.0.2, 2025-06-14 | Reads legacy .xls only. Not needed if calamine is adopted. |
| odfpy | Apache-2.0 OR GPL OR LGPL (tri-licence classifiers) | ok | avoid | 1.4.1, 2020-01-18 (stale) | Choose the Apache-2.0 option if used. calamine already reads ODS; odfpy only needed for ODT. |
| pandas | BSD-3-Clause | ok | optional | 3.1.0 | Pulled in by MarkItDown and presidio-structured. Large memory footprint; avoid in the hot path. |
| XlsxWriter | BSD-2-Clause | ok | optional | 3.3.0 | Only if an anonymized .xlsx output option is ever offered (spec says Markdown output). |
| msoffcrypto-tool | MIT | ok | optional | 6.0.0 | Decrypts password-protected Office files when the caller supplies the password. Otherwise reject encrypted files explicitly. |
| defusedxml | PSF-2.0 | ok | adopt | 0.7.1, 2021-03-08 (stale but stable) | Hardens openpyxl and other OOXML parsing against XML bombs and XXE in untrusted uploads. |
| pycel | GPL-3.0 | avoid | avoid | 1.0b30, 2021-10-13; CVE-2024-53924 unfixed | Formula evaluation with GPL plus code execution from a crafted formula. Use the stored formula results instead. |
| formulas | EUPL-1.1+ | caution | avoid | 1.3.4, 2026-03-11 | EUPL copyleft. Formula evaluation is not needed for anonymization. |
| LibreOffice (headless, for .xls/.doc conversion) | MPL-2.0 | caution | optional | current | Docling uses it for .xls. Weak, file-level copyleft: bundling an unmodified binary in Docker only needs notices and source availability. Adds about 500 MB to the image; calamine makes it unnecessary for .xls. |
| python-pptx | MIT | ok | adopt | 1.0.2 | Includes notes slides (often holding PII). |
| extract-msg | GPL (per PyPI field) | avoid | avoid | 0.56.1 | Use python-oxmsg (MIT, 0.0.2 alpha, https://pypi.org/project/python-oxmsg/), which Docling uses. |
| beautifulsoup4 | MIT | ok | adopt | 4.15.0 | HTML handling. |
| markdownify | MIT | ok | adopt | 1.2.3, 2026-06-30 | HTML to Markdown; replaces html2text. |
| html2text | GPL-3.0-or-later | avoid | avoid | 2025.4.15 | GPL; use markdownify. |
| trafilatura | Apache-2.0 | ok | optional | 2.3.1 | Main-content extraction from web pages. Apache-2.0 in current versions (older ones were GPL); pin it at 2.x or later. |
| Tesseract | Apache-2.0 | ok | optional | 5.x | System binary for scanned documents; good French support. Slow on CPU. |
| RapidOCR | Apache-2.0 (code and bundled PP-OCRv6 ONNX models) | ok | optional | 3.10.0, 2026-10-08 | ONNX OCR suited to CPU. Depends on opencv-python-headless, whose wheels bundle FFmpeg (LGPL-2.1, https://github.com/opencv/opencv-python), so Docker notices are needed. |
| docTR | Apache-2.0 | ok | optional | 1.1.0, 2026-08-21 | Deep-learning OCR; heavier than RapidOCR on CPU. |
| libpostal | MIT (code); model data derived from ODbL/CC-BY/mixed sources | avoid | avoid | no visible recent release | Trained on OSM (ODbL), OpenAddresses (various) and GeoPlanet (CC-BY). Model data is roughly 2 GB and needs a lot of RAM. Use regex plus BAN/COG gazetteers for French addresses. |
| INSEE Fichier des prénoms | etalab-2.0 | ok | adopt | July 2026 edition, births 1900–2025 | French first-name gazetteer with frequencies (helps filter ambiguous names like 'Pierre' or 'Rose'). Attribute Insee plus the update date. |
| INSEE Fichier des personnes décédées (surname source) | etalab-2.0 | caution | optional | monthly | No dedicated INSEE surname file was found. This file contains personal data; redistributors must exclude entries on the opposition list. Build and ship only an aggregated surname-frequency list, never the raw records. |
| Base Adresse Nationale (BAN) | etalab-2.0 | ok | optional | continuous | Street-name and commune gazetteer for address detection. Large, so ship it as a download-on-demand data pack. |
| INSEE COG | etalab-2.0 | ok | adopt | updated 2026-10-06 | Communes and départements; also validates the birthplace code inside the NIR. |
| GeoNames | CC-BY-4.0 | ok | adopt | daily dumps | Multi-country place names for country packs. Needs attribution plus a modification notice. |
| OpenStreetMap | ODbL-1.0 | avoid | avoid | n/a | Share-alike on derived databases; do not bundle extracts or gazetteers built from OSM. |
| Wikidata | CC0-1.0 | ok | adopt | n/a | Structured data is CC0: multilingual given and family names, organizations, cities. Text namespaces are CC-BY-SA, so do not use those. |
| cryptography | Apache-2.0 OR BSD-3-Clause | ok | adopt | 50.0.2 | HMAC-SHA256 with an ephemeral key, AES-GCM/SIV for the reversible mapping vault. |
| ff3 | Apache-2.0 | ok | avoid | 1.0.3, 2026-01-26 | Package README states NIST withdrew FF3 (SP 800-38G Rev.1 Draft 2, Feb 2025) and the code is not independently reviewed. Use FF1 or keyed tokens. |
| LLM Guard | MIT | ok | borrow-ideas | 0.3.16, 2025-05-19; pins presidio 2.2.358, transformers 4.51.3, Python<3.13 | Its Anonymize/Deanonymize vault design is worth studying. Do not depend on it: stale pins and heavy torch. |
| ARX | Apache-2.0 | ok | borrow-ideas | active (copyright 2012–2025) | Java tool for k-anonymity on tabular data. Ideas for an optional anonymization mode for Excel/CSV, beyond pseudonymization. |
| anjana | Apache-2.0 | ok | optional | 1.2.3, 2026-08-13 | Python k-anonymity, l-diversity and t-closeness for tables. Pins numpy==2.0.2 and pandas==2.3.3 exactly, a resolver risk; isolate it in an extra. |
| pycanon | Apache-2.0 | ok | optional | 1.3.6, 2026-08-13 | Measures k-anonymity and similar metrics of output tables; could report residual risk on Excel exports. |
| pip-licenses | MIT | ok | adopt | 5.5.5 | CI gate with --allow-only or --fail-on. Use --with-license-file and --with-notice-file to generate THIRD_PARTY_NOTICES. |
| liccheck | Apache-2.0 | ok | optional | 0.9.2, 2023-09-22 (stale) | Strategy file of authorized and unauthorized licences. Stale; pip-licenses is preferred. |
| reuse | GPL-3.0-or-later (code) + Apache-2.0/CC0/CC-BY-SA-4.0 parts | ok | adopt | 6.2.0 | Dev/CI-only tool, never shipped, so its GPL does not matter. 'reuse lint' enforces SPDX headers in our own repo. |
| ScanCode toolkit | Apache-2.0 AND CC-BY-4.0 (+ LicenseRef data) | ok | adopt | 32.5.0 | Deep scan of the built Docker image and vendored files (it reads licence text, not only metadata). Catches GPL inside wheels such as FFmpeg in opencv. |

