# GDPR Guardian on real corpus `bodacc_fr` (2026-10-25)

- Corpus: BODACC, commercial announcements naming natural persons. Language `fr`. Licence: Licence Ouverte / Open Licence (Etalab), DILA. Source: https://www.data.gouv.fr/datasets/bodacc (Opendatasoft API, publications of 2026-09-01..2026-09-30, fetched 2026-10-25).
- This build: publications 2026-09-01..2026-09-30 (cache manifest).
- Real text: yes (record values and free text are real; line layout rendered by us after bodacc.fr).
- Gold: exact by construction: values of the structured fields (surname, given names, address, RCS/RM number) are rendered at known positions; exact repeats of a person's name elsewhere in the notice are added; owner addresses in the fixed 'Adresse de l'ancien/du nouveau propriétaire :' phrase are added.
- Engine: gdprguardian 1.0.0 (native core: True), `Anonymizer(countries="FR", profile="standard")`.
- Documents: 2693/2693 evaluated, engine errors: 0; 2,163,537 characters; throughput 1441894 chars/s (one thread, shared machine).
- Personal gold mentions: 14,207; kept-by-policy mentions: 9,110.

## Headline (95% bootstrap intervals over documents)

| indicator | value [95% CI] |
|---|---|
| mention recall, strict (no character left) | 78.9% [78.5%–79.3%] |
| mention recall@80 (>= 80% of characters masked) | 79.6% [79.2%–80.0%] |
| character recall | 85.2% [84.9%–85.5%] |
| precision (characters, scored zone) | 90.1% [89.6%–90.5%] |
| over-masking of non-gold text | 1.4% [1.3%–1.5%] |
| documents leaking a personal mention (strict) | 92.6% [91.6%–93.6%] |
| documents leaking a mention verbatim (literal) | 90.8% [89.8%–91.9%] |
| mentions found verbatim in the output | 18.7% [18.4%–19.0%] |

## Per family (strict mention recall)

| family | mentions | recall [95% CI] |
|---|---:|---|
| PERSON | 8,728 | 98.1% [97.8%–98.5%] |
| ADDRESS | 2,812 | 89.1% [88.0%–90.3%] |
| ID | 2,667 | 5.3% [4.4%–6.2%] |

## Per gold origin

| family:origin | mentions | strict recall |
|---|---:|---:|
| ADDRESS:field | 2,534 | 89.5% |
| ADDRESS:phrase | 278 | 86.0% |
| ID:field | 2,667 | 5.3% |
| PERSON:field | 8,447 | 98.2% |
| PERSON:repeat | 127 | 94.5% |
| PERSON:trade_name | 154 | 97.4% |

## Kept by policy (share of mentions touched by a mask, for information)

| family | mentions | touched |
|---|---:|---:|
| DATE | 3,096 | 0.0% |
| LOCATION | 2,592 | 1.0% |
| ORG | 2,769 | 1.4% |
| ORG_ID | 74 | 1.4% |
| OTHER | 579 | 0.0% |

## Manual review of a sample

- Gold reviewed by hand on two random samples of 50 announcements (spotcheck_real.py, seeds 20261025 and 20261026). The first review found errors that were fixed by rule; the second, fresh sample measures the gold used here.
- sample_1_before_fixes: seed 20261025: 8 of 50 documents with a personal-gold error; 8 errors for about 263 personal mentions (3.0%): 2 boundaries ('(EI)' marker inside the name span), 6 names written inside a trade name and missing from the gold. Fixed: '(EI)' excluded, names and given names searched inside trade names.
- sample_2_after_fixes: seed 20261026: 0 of 50 documents with an error in the scored zone (0 of 274 personal mentions; 95% Wilson upper bound 1.4%). One owner address written 'Adresse ancien propriétaire' (no 'de l'') was missed in free text (ignored zone, outside precision); the phrase rule was widened afterwards.
- documents_reviewed: 100
- gold_error_rate_documents: 0/50 (final), 8/50 (before fixes)
- gold_error_rate_mentions: 0/274 (final), 8/263 (before fixes)

## Reproduce

```
python tools/corpus/build_bodacc.py --cache DIR --per-family 500
python tools/corpus/evaluate_real.py --cache DIR --corpora bodacc_fr --tag base
```

No document text or gold value is stored in this report; the corpus stays in the local cache.
