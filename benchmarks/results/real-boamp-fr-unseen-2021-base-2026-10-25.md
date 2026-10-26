# GDPR Guardian on real corpus `boamp_fr` (2026-10-25)

- Corpus: BOAMP, public procurement notices 2022-2023 (IDENTITE schema). Language `fr`. Licence: Licence Ouverte / Open Licence (Etalab), DILA. Source: https://www.data.gouv.fr/datasets/boamp (Opendatasoft API, publications of 2022-01..2023-12 (125 per month), fetched 2026-10-25).
- This build: publications 2021-01..2021-12 (cache manifest).
- Real text: yes (values and free text are real; 'Label : value' layout rendered by us).
- Gold: exact by construction: e-mail, phone, fax and street address fields of every party block; contact person names extracted from the CONTACT/CORRESPONDANT fields by a rule (civility and role removed).
- Engine: gdprguardian 1.0.0 (native core: True), `Anonymizer(countries="FR", profile="standard")`.
- Documents: 1500/1500 evaluated, engine errors: 0; 9,919,139 characters; throughput 4725476 chars/s (one thread, shared machine).
- Personal gold mentions: 15,022; kept-by-policy mentions: 19,397.

## Headline (95% bootstrap intervals over documents)

| indicator | value [95% CI] |
|---|---|
| mention recall, strict (no character left) | 83.8% [82.8%–85.0%] |
| mention recall@80 (>= 80% of characters masked) | 88.4% [87.5%–89.3%] |
| character recall | 87.0% [86.0%–88.1%] |
| precision (characters, scored zone) | 83.3% [80.7%–85.5%] |
| over-masking of non-gold text | 0.5% [0.3%–0.6%] |
| documents leaking a personal mention (strict) | 66.1% [63.6%–68.5%] |
| documents leaking a mention verbatim (literal) | 10.9% [9.5%–12.5%] |
| mentions found verbatim in the output | 2.5% [2.0%–2.9%] |

## Per family (strict mention recall)

| family | mentions | recall [95% CI] |
|---|---:|---|
| PERSON | 390 | 86.2% [81.5%–90.3%] |
| ADDRESS | 6,223 | 68.8% [66.4%–71.4%] |
| EMAIL | 3,834 | 100.0% [99.9%–100.0%] |
| PHONE | 4,575 | 90.5% [88.7%–92.3%] |

## Per gold origin

| family:origin | mentions | strict recall |
|---|---:|---:|
| ADDRESS:field | 6,223 | 68.8% |
| EMAIL:field | 3,786 | 100.0% |
| EMAIL:repeat | 48 | 97.9% |
| PERSON:field | 372 | 88.7% |
| PERSON:repeat | 18 | 33.3% |
| PHONE:field | 4,570 | 90.5% |
| PHONE:repeat | 5 | 100.0% |

## Kept by policy (share of mentions touched by a mask, for information)

| family | mentions | touched |
|---|---:|---:|
| DATE | 7,727 | 0.0% |
| LOCATION | 2,630 | 40.3% |
| ORG | 8,610 | 53.9% |
| ORG_ID | 430 | 0.0% |

## Reproduce

```
python tools/corpus/build_boamp.py --cache DIR --per-month 125
python tools/corpus/evaluate_real.py --cache DIR --corpora boamp_fr --tag unseen-2021-base
```

No document text or gold value is stored in this report; the corpus stays in the local cache.
