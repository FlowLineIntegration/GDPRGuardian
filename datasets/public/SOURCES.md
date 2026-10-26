# Public evaluation datasets / Jeux publics d'évaluation

Downloaded at evaluation time by `tools/corpus/fetch_public.py` into `datasets/public/cache/` (git-ignored, never redistributed). Dev tooling only.

| name | dataset | revision | licence | records | gold spans |
|---|---|---|---|---:|---:|
| fr_pii_bench | [FR-PII-Bench v0](https://huggingface.co/datasets/JaqueBill/fr-pii-bench) | `5476b0a48924` | CC-BY-4.0 | 300 | 2105 |
| mapa_fr | [MAPA EUR-Lex (French split)](https://huggingface.co/datasets/joelniklaus/mapa) | `bbb2a0157b76` | CC-BY-4.0 | 12 | 1443 |
| gretel_fr | [gretelai/synthetic_pii_finance_multilingual (French)](https://huggingface.co/datasets/gretelai/synthetic_pii_finance_multilingual) | `7b844d167385` | Apache-2.0 | 4426 | 17819 |
| openpii_fr | [ai4privacy pii-masking-openpii-1m (French, validation split sample)](https://huggingface.co/datasets/ai4privacy/pii-masking-openpii-1m) | `ecfdc547f4a0` | CC-BY-4.0 | 3000 | 21070 |
| tab_en | [TAB, Text Anonymization Benchmark (English, ECHR)](https://github.com/NorskRegnesentral/text-anonymization-benchmark) | `558e09e26d6b` | MIT | 127 | 5146 |

## Details and attribution

### fr_pii_bench

- URL: https://huggingface.co/datasets/JaqueBill/fr-pii-bench
- Revision (full): `5476b0a489249047a478083ac856a328d0e4d2c3`
- Licence: CC-BY-4.0
- Attribution: Xiao, H. (2026). FR-PII-Bench v0, 300 synthetic French documents. CC-BY-4.0. https://huggingface.co/datasets/JaqueBill/fr-pii-bench
- Notes: Synthetic (Faker fr_FR), exact offsets. Author used it to tune its own stop-list; not held-out for them.
- Fetched: 2026-10-24
- Spans per family: ADDRESS: 397, BIRTH_DATE: 113, EMAIL: 168, IBAN: 131, ID: 245, NATIONAL_ID: 131, ORG: 208, PERSON: 488, PHONE: 169, TAX_ID: 55

### mapa_fr

- URL: https://huggingface.co/datasets/joelniklaus/mapa
- Revision (full): `bbb2a0157b760465002fd12a61af81b475cd387a`
- Licence: CC-BY-4.0
- Attribution: de Gibert Bonet, O., Garcia Pablos, A., Cuadros, M., Melero, M. (2022). Spanish Datasets for Sensitive Entity Detection in the Legal Domain, LREC 2022; MAPA project; HF mirror by J. Niklaus. CC-BY-4.0.
- Notes: Manual annotations, legal text (EUR-Lex), tokenised: text rebuilt by joining tokens with spaces, one record per source document. Few direct identifiers (mostly legal-entity names, places, dates).
- Fetched: 2026-10-24
- Spans per family: ADDRESS: 2, DATE: 491, LOCATION: 201, ORG: 343, OTHER: 126, PERSON: 280

### gretel_fr

- URL: https://huggingface.co/datasets/gretelai/synthetic_pii_finance_multilingual
- Revision (full): `7b844d16738527a04264f50214cb426a4cea0897`
- Licence: Apache-2.0
- Attribution: Gretel.ai (2024). synthetic_pii_finance_multilingual. Apache-2.0. https://huggingface.co/datasets/gretelai/synthetic_pii_finance_multilingual
- Notes: SILVER labels (LLM-generated text, GLiNER-assisted spans): false positives and negatives in gold. Read from the pinned data/France_{train,test} parquet files (requires pyarrow).
- Fetched: 2026-10-24
- Spans per family: ADDRESS: 3575, BANK_ACCOUNT: 261, BIRTH_DATE: 212, CARD: 100, DATE: 1281, EMAIL: 432, IBAN: 178, ID: 484, IP: 189, LOCATION: 61, NATIONAL_ID: 243, ORG: 3669, OTHER: 822, PERSON: 5624, PHONE: 688

### openpii_fr

- URL: https://huggingface.co/datasets/ai4privacy/pii-masking-openpii-1m
- Revision (full): `ecfdc547f4a0955600cfe6ab98ba2a162207fcc0`
- Licence: CC-BY-4.0
- Attribution: Ai4Privacy / Ai Suisse SA (2026). OpenPII 1M. CC-BY-4.0 (c) 2026 Ai Suisse SA. https://huggingface.co/datasets/ai4privacy/pii-masking-openpii-1m
- Notes: Synthetic, generic labels (SOCIALNUM, TAXNUM, IDCARDNUM...). Card header says 'license: other' with license_name cc-by-4.0, and the card body states CC-BY-4.0 with commercial use allowed. Generator model undisclosed. Streamed (the file is 0.9 GB): first records with language=fr and region=FR only (fr-BE/CA/CH use non-French formats; --openpii-region any to keep them). GIVENNAME+SURNAME and STREET+BUILDINGNUM+ZIPCODE are merged into single PERSON / ADDRESS spans.
- Fetched: 2026-10-24
- Spans per family: ADDRESS: 2133, CARD: 757, DATE: 2991, EMAIL: 1716, ID: 663, LOCATION: 1722, NATIONAL_ID: 1905, OTHER: 3991, PERSON: 3299, PHONE: 1299, TAX_ID: 594

### tab_en

- URL: https://github.com/NorskRegnesentral/text-anonymization-benchmark
- Revision (full): `558e09e26d6b36f5f78440074e6a233946d98bd9`
- Licence: MIT
- Attribution: Pilan, I., Lison, P., Ovrelid, L., Papadopoulou, A., Sanchez, D., Batet, M. (2022). The Text Anonymization Benchmark (TAB). Copyright Norsk Regnesentral. MIT.
- Notes: English (optional, --tab). DIRECT and QUASI identifier mentions of the first annotator; NO_MASK mentions are dropped.
- Fetched: 2026-10-24
- Spans per family: DATE: 2487, LOCATION: 294, ORG: 550, OTHER: 857, PERSON: 958

## Rejected (licence)

ai4privacy pii-masking-200k/300k/400k/500k (non-commercial or Llama licence), WikiNEuRal and MultiNERD (CC-BY-NC-SA), CATIE-AQ frenchNER (inherits NC sets), piimb (CC-BY-NC), E3C, Meddies.
