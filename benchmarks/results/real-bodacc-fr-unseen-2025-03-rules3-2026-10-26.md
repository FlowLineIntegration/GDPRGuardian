# GDPR Guardian on real corpus `bodacc_fr` (2026-10-26)

- Corpus: BODACC, commercial announcements naming natural persons. Language `fr`. Licence: Licence Ouverte / Open Licence (Etalab), DILA. Source: https://www.data.gouv.fr/datasets/bodacc (Opendatasoft API, publications of 2026-09-01..2026-09-30, fetched 2026-10-25).
- This build: publications 2025-03-01..2025-03-31 (cache manifest).
- Real text: yes (record values and free text are real; line layout rendered by us after bodacc.fr).
- Gold: exact by construction: values of the structured fields (surname, given names, address, RCS/RM number) are rendered at known positions; exact repeats of a person's name elsewhere in the notice are added; owner addresses in the fixed 'Adresse de l'ancien/du nouveau propriétaire :' phrase are added.
- Engine: gdprguardian 1.0.0 (native core: True), `Anonymizer(countries="FR", profile="standard")`.
- Documents: 1761/1761 evaluated, engine errors: 0; 1,473,556 characters; throughput 2358034 chars/s (one thread, shared machine).
- Personal gold mentions: 9,521; kept-by-policy mentions: 6,393.

## Headline (95% bootstrap intervals over documents)

| indicator | value [95% CI] |
|---|---|
| mention recall, strict (no character left) | 97.6% [97.3%–98.0%] |
| mention recall@80 (>= 80% of characters masked) | 98.3% [97.9%–98.6%] |
| character recall | 98.3% [98.0%–98.7%] |
| precision (characters, scored zone) | 99.0% [98.8%–99.2%] |
| over-masking of non-gold text | 0.1% [0.1%–0.1%] |
| documents leaking a personal mention (strict) | 10.8% [9.4%–12.4%] |
| documents leaking a mention verbatim (literal) | 5.6% [4.6%–6.6%] |
| mentions found verbatim in the output | 1.3% [1.0%–1.5%] |

## Per family (strict mention recall)

| family | mentions | recall [95% CI] |
|---|---:|---|
| PERSON | 5,645 | 98.1% [97.6%–98.5%] |
| ADDRESS | 2,123 | 95.5% [94.6%–96.3%] |
| ID | 1,753 | 98.9% [98.4%–99.4%] |

## Per gold origin

| family:origin | mentions | strict recall |
|---|---:|---:|
| ADDRESS:field | 1,716 | 95.3% |
| ADDRESS:phrase | 407 | 96.3% |
| ID:field | 1,753 | 98.9% |
| PERSON:field | 5,469 | 98.1% |
| PERSON:repeat | 103 | 97.1% |
| PERSON:trade_name | 73 | 95.9% |

## Kept by policy (share of mentions touched by a mask, for information)

| family | mentions | touched |
|---|---:|---:|
| DATE | 2,086 | 0.0% |
| LOCATION | 1,830 | 0.4% |
| ORG | 1,867 | 1.1% |
| ORG_ID | 105 | 5.7% |
| OTHER | 505 | 0.0% |

## Reproduce

```
python tools/corpus/build_bodacc.py --cache DIR --per-family 500
python tools/corpus/evaluate_real.py --cache DIR --corpora bodacc_fr --tag unseen-2025-03-rules3
```

No document text or gold value is stored in this report; the corpus stays in the local cache.
