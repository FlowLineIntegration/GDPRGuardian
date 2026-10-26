# Recherche Gardien RGPD (24/10/2026)

Synthèses brutes de la recherche web multi-agents qui a servi à écrire [../PLAN.md](../PLAN.md).
Chaque axe a été vérifié par un agent contradicteur ; les affirmations réfutées ou non vérifiées
sont listées dans la section *Verification* de chaque fichier `*.digest.md`.
Les fichiers `*.detail.md` contiennent les tableaux (bibliothèques, licences, identifiants avec regex et clés de contrôle).

Langue : anglais (sortie des agents). Limite connue : le quota de recherche web partagé a été épuisé
en cours de route ; beaucoup de vérifications ont été faites par lecture directe des sources primaires.

| Axe | Synthèse | Détails |
|---|---|---|
| Moteurs open source existants, passerelles LLM, serveurs MCP PII, prior art juridique FR | [oss-engines.digest.md](oss-engines.digest.md) | [oss-engines.detail.md](oss-engines.detail.md) |
| Identifiants France (NIR, SPI, SIREN/SIRET, TVA, RIB, CNI, MRZ, RPPS, FINESS...) | [ids-france.digest.md](ids-france.digest.md) | [ids-france.detail.md](ids-france.detail.md) |
| Identifiants Europe de l'Ouest et du Sud + UK/CH | [ids-europe-west.digest.md](ids-europe-west.digest.md) | [ids-europe-west.detail.md](ids-europe-west.detail.md) |
| Identifiants Europe du Nord et de l'Est + TVA UE | [ids-europe-north-east.digest.md](ids-europe-north-east.digest.md) | [ids-europe-north-east.detail.md](ids-europe-north-east.detail.md) |
| Identifiants universels, hors UE, et conception du mode 'auto' | [ids-intl-universal.digest.md](ids-intl-universal.digest.md) | [ids-intl-universal.detail.md](ids-intl-universal.detail.md) |
| Audit de licences (code, modèles, jeux de données, gazetteers) | [licenses.digest.md](licenses.digest.md) | [licenses.detail.md](licenses.detail.md) |
| Modèles NER CPU pour PII (FR + UE) | [ner-models.digest.md](ner-models.digest.md) | [ner-models.detail.md](ner-models.detail.md) |
| Ingénierie de performance CPU (ONNX Runtime, quantification, regex multi-motifs) | [cpu-perf.digest.md](cpu-perf.digest.md) | [cpu-perf.detail.md](cpu-perf.detail.md) |
| MCP / FastMCP et architecture (le LLM voit les arguments) | [mcp-arch.digest.md](mcp-arch.digest.md) | [mcp-arch.detail.md](mcp-arch.detail.md) |
| Analyse RGPD / juridique | [gdpr-legal.digest.md](gdpr-legal.digest.md) | [gdpr-legal.detail.md](gdpr-legal.detail.md) |
| Conversion documents -> Markdown sur CPU | [doc-to-md.digest.md](doc-to-md.digest.md) | [doc-to-md.detail.md](doc-to-md.detail.md) |
| Stratégie Excel / CSV | [tabular-excel.digest.md](tabular-excel.digest.md) | [tabular-excel.detail.md](tabular-excel.detail.md) |
| Détection noms / adresses / organisations sans ML, catégories particulières | [name-address-heuristics.digest.md](name-address-heuristics.digest.md) | [name-address-heuristics.detail.md](name-address-heuristics.detail.md) |
| Opérateurs de remplacement, clé éphémère, réhydratation | [pseudo-ops.digest.md](pseudo-ops.digest.md) | [pseudo-ops.detail.md](pseudo-ops.detail.md) |
| Évaluation, jeux de test, métriques, red-team | [eval-bench.digest.md](eval-bench.digest.md) | [eval-bench.detail.md](eval-bench.detail.md) |
| Angle mort : par où les fichiers arrivent aux LLM | [gap-llm-file-channels.digest.md](gap-llm-file-channels.digest.md) | [gap-llm-file-channels.detail.md](gap-llm-file-channels.detail.md) |
| Angle mort : format de sortie des tableurs et limites des clients MCP | [gap-excel-output-representation.digest.md](gap-excel-output-representation.digest.md) | [gap-excel-output-representation.detail.md](gap-excel-output-representation.detail.md) |
| Angle mort : structure réelle des tableurs et typage de colonnes | [gap-spreadsheet-structure-column-typing.digest.md](gap-spreadsheet-structure-column-typing.digest.md) | [gap-spreadsheet-structure-column-typing.detail.md](gap-spreadsheet-structure-column-typing.detail.md) |
| Angle mort : formules, opérateurs typés, réhydratation tabulaire | [gap-excel-roundtrip-rehydration-formulas.digest.md](gap-excel-roundtrip-rehydration-formulas.digest.md) | [gap-excel-roundtrip-rehydration-formulas.detail.md](gap-excel-roundtrip-rehydration-formulas.detail.md) |
| Angle mort : concurrents commerciaux | [gap-competitor-landscape-spreadsheets.digest.md](gap-competitor-landscape-spreadsheets.digest.md) | [gap-competitor-landscape-spreadsheets.detail.md](gap-competitor-landscape-spreadsheets.detail.md) |
| Critique de complétude (contradictions entre axes) | [critic.md](critic.md) | |
