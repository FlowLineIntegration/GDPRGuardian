# GDPR Guardian on real corpus `bodacc_fr` (2026-10-25)

- Corpus: BODACC, commercial announcements naming natural persons. Language `fr`. Licence: Licence Ouverte / Open Licence (Etalab), DILA. Source: https://www.data.gouv.fr/datasets/bodacc (Opendatasoft API, publications of 2026-09-01..2026-09-30, fetched 2026-10-25).
- This build: publications 2026-08-01..2026-08-31 (cache manifest).
- Real text: yes (record values and free text are real; line layout rendered by us after bodacc.fr).
- Gold: exact by construction: values of the structured fields (surname, given names, address, RCS/RM number) are rendered at known positions; exact repeats of a person's name elsewhere in the notice are added; owner addresses in the fixed 'Adresse de l'ancien/du nouveau propriétaire :' phrase are added.
- Engine: gdprguardian 1.0.0 (native core: True), `Anonymizer(countries="FR", profile="standard")`.
- Documents: 2689/2689 evaluated, engine errors: 0; 2,102,929 characters; throughput 1961639 chars/s (one thread, shared machine).
- Personal gold mentions: 14,195; kept-by-policy mentions: 9,012.

## Headline (95% bootstrap intervals over documents)

| indicator | value [95% CI] |
|---|---|
| mention recall, strict (no character left) | 79.3% [78.8%–79.7%] |
| mention recall@80 (>= 80% of characters masked) | 80.0% [79.6%–80.4%] |
| character recall | 85.7% [85.3%–86.0%] |
| precision (characters, scored zone) | 90.1% [89.6%–90.5%] |
| over-masking of non-gold text | 1.5% [1.4%–1.6%] |
| documents leaking a personal mention (strict) | 91.9% [90.8%–92.9%] |
| documents leaking a mention verbatim (literal) | 89.9% [88.8%–91.1%] |
| mentions found verbatim in the output | 18.5% [18.2%–18.9%] |

## Per family (strict mention recall)

| family | mentions | recall [95% CI] |
|---|---:|---|
| PERSON | 8,733 | 98.0% [97.7%–98.4%] |
| ADDRESS | 2,830 | 90.1% [88.9%–91.2%] |
| ID | 2,632 | 5.2% [4.4%–6.1%] |

## Per gold origin

| family:origin | mentions | strict recall |
|---|---:|---:|
| ADDRESS:field | 2,553 | 90.6% |
| ADDRESS:phrase | 277 | 85.9% |
| ID:field | 2,632 | 5.2% |
| PERSON:field | 8,371 | 98.1% |
| PERSON:repeat | 164 | 95.7% |
| PERSON:trade_name | 198 | 94.9% |

## Kept by policy (share of mentions touched by a mask, for information)

| family | mentions | touched |
|---|---:|---:|
| DATE | 3,023 | 0.0% |
| LOCATION | 2,611 | 0.9% |
| ORG | 2,778 | 1.0% |
| ORG_ID | 89 | 1.1% |
| OTHER | 511 | 0.0% |

## Reproduce

```
python tools/corpus/build_bodacc.py --cache DIR --per-family 500
python tools/corpus/evaluate_real.py --cache DIR --corpora bodacc_fr --tag unseen-2026-08-base
```

No document text or gold value is stored in this report; the corpus stays in the local cache.
