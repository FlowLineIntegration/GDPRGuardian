# GDPR Guardian on real corpus `bodacc_fr` (2026-10-26)

- Corpus: BODACC, commercial announcements naming natural persons. Language `fr`. Licence: Licence Ouverte / Open Licence (Etalab), DILA. Source: https://www.data.gouv.fr/datasets/bodacc (Opendatasoft API, publications of 2026-09-01..2026-09-30, fetched 2026-10-25).
- This build: publications 2026-09-01..2026-09-30 (cache manifest).
- Real text: yes (record values and free text are real; line layout rendered by us after bodacc.fr).
- Gold: exact by construction: values of the structured fields (surname, given names, address, RCS/RM number) are rendered at known positions; exact repeats of a person's name elsewhere in the notice are added; owner addresses in the fixed 'Adresse de l'ancien/du nouveau propriétaire :' phrase are added.
- Engine: gdprguardian 1.0.0 (native core: True), `Anonymizer(countries="FR", profile="standard")`.
- Documents: 2693/2693 evaluated, engine errors: 0; 2,163,537 characters; throughput 2561550 chars/s (one thread, shared machine).
- Personal gold mentions: 14,207; kept-by-policy mentions: 9,110.

## Headline (95% bootstrap intervals over documents)

| indicator | value [95% CI] |
|---|---|
| mention recall, strict (no character left) | 97.6% [97.4%–97.9%] |
| mention recall@80 (>= 80% of characters masked) | 98.2% [97.9%–98.4%] |
| character recall | 98.1% [97.8%–98.3%] |
| precision (characters, scored zone) | 99.2% [99.1%–99.3%] |
| over-masking of non-gold text | 0.1% [0.1%–0.1%] |
| documents leaking a personal mention (strict) | 10.5% [9.4%–11.7%] |
| documents leaking a mention verbatim (literal) | 6.2% [5.3%–7.0%] |
| mentions found verbatim in the output | 1.5% [1.3%–1.7%] |

## Per family (strict mention recall)

| family | mentions | recall [95% CI] |
|---|---:|---|
| PERSON | 8,728 | 98.2% [97.8%–98.5%] |
| ADDRESS | 2,812 | 94.8% [94.0%–95.6%] |
| ID | 2,667 | 98.8% [98.4%–99.2%] |

## Per gold origin

| family:origin | mentions | strict recall |
|---|---:|---:|
| ADDRESS:field | 2,534 | 94.9% |
| ADDRESS:phrase | 278 | 93.9% |
| ID:field | 2,667 | 98.8% |
| PERSON:field | 8,447 | 98.2% |
| PERSON:repeat | 127 | 94.5% |
| PERSON:trade_name | 154 | 97.4% |

## Kept by policy (share of mentions touched by a mask, for information)

| family | mentions | touched |
|---|---:|---:|
| DATE | 3,096 | 0.0% |
| LOCATION | 2,592 | 0.5% |
| ORG | 2,769 | 1.0% |
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
python tools/corpus/evaluate_real.py --cache DIR --corpora bodacc_fr --tag rules3
```

No document text or gold value is stored in this report; the corpus stays in the local cache.
