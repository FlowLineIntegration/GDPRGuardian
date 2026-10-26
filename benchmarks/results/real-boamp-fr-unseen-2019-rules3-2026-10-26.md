# GDPR Guardian on real corpus `boamp_fr` (2026-10-26)

- Corpus: BOAMP, public procurement notices 2022-2023 (IDENTITE schema). Language `fr`. Licence: Licence Ouverte / Open Licence (Etalab), DILA. Source: https://www.data.gouv.fr/datasets/boamp (Opendatasoft API, publications of 2022-01..2023-12 (125 per month), fetched 2026-10-25).
- This build: publications 2019-01..2019-12 (cache manifest).
- Real text: yes (values and free text are real; 'Label : value' layout rendered by us).
- Gold: exact by construction: e-mail, phone, fax and street address fields of every party block; contact person names extracted from the CONTACT/CORRESPONDANT fields by a rule (civility and role removed).
- Engine: gdprguardian 1.0.0 (native core: True), `Anonymizer(countries="FR", profile="standard")`.
- Documents: 1200/1200 evaluated, engine errors: 0; 7,811,135 characters; throughput 5352829 chars/s (one thread, shared machine).
- Personal gold mentions: 11,525; kept-by-policy mentions: 15,725.

## Headline (95% bootstrap intervals over documents)

| indicator | value [95% CI] |
|---|---|
| mention recall, strict (no character left) | 90.7% [89.9%–91.6%] |
| mention recall@80 (>= 80% of characters masked) | 92.7% [92.0%–93.4%] |
| character recall | 91.2% [90.2%–92.1%] |
| precision (characters, scored zone) | 85.0% [80.2%–88.4%] |
| over-masking of non-gold text | 0.5% [0.3%–0.8%] |
| documents leaking a personal mention (strict) | 46.1% [43.0%–49.0%] |
| documents leaking a mention verbatim (literal) | 14.4% [12.5%–16.6%] |
| mentions found verbatim in the output | 2.8% [2.4%–3.3%] |

## Per family (strict mention recall)

| family | mentions | recall [95% CI] |
|---|---:|---|
| PERSON | 413 | 86.9% [83.2%–90.3%] |
| ADDRESS | 4,470 | 84.3% [82.6%–85.9%] |
| EMAIL | 2,895 | 100.0% [100.0%–100.0%] |
| PHONE | 3,747 | 91.6% [89.7%–93.5%] |

## Per gold origin

| family:origin | mentions | strict recall |
|---|---:|---:|
| ADDRESS:field | 4,470 | 84.3% |
| EMAIL:field | 2,874 | 100.0% |
| EMAIL:repeat | 21 | 100.0% |
| PERSON:field | 408 | 87.0% |
| PERSON:repeat | 5 | 80.0% |
| PHONE:field | 3,745 | 91.6% |
| PHONE:repeat | 2 | 100.0% |

## Kept by policy (share of mentions touched by a mask, for information)

| family | mentions | touched |
|---|---:|---:|
| DATE | 5,994 | 0.0% |
| LOCATION | 2,637 | 21.8% |
| ORG | 6,833 | 40.0% |
| ORG_ID | 261 | 0.0% |

## Reproduce

```
python tools/corpus/build_boamp.py --cache DIR --per-month 125
python tools/corpus/evaluate_real.py --cache DIR --corpora boamp_fr --tag unseen-2019-rules3
```

No document text or gold value is stored in this report; the corpus stays in the local cache.
