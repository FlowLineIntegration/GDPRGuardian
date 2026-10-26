# GDPR Guardian on real corpus `meddocan_es` (2026-10-25)

- Corpus: MEDDOCAN, Spanish clinical case reports (de-identification task). Language `es`. Licence: CC BY 4.0. Source: https://zenodo.org/records/4279323 (Zenodo 10.5281/zenodo.4279323 (meddocan.zip)).
- Real text: yes (real published case reports) with SURROGATE identifiers added by the corpus authors.
- Gold: manual gold (29 PHI types), inter-annotator agreement reported at 98%.
- Engine: gdprguardian 1.0.0 (native core: True), `Anonymizer(countries="ES,FR", profile="standard")`.
- Documents: 1000/1000 evaluated, engine errors: 0; 2,887,969 characters; throughput 4852544 chars/s (one thread, shared machine).
- Personal gold mentions: 9,822; kept-by-policy mentions: 12,973.

## Headline (95% bootstrap intervals over documents)

| indicator | value [95% CI] |
|---|---|
| mention recall, strict (no character left) | 49.8% [49.4%–50.3%] |
| mention recall@80 (>= 80% of characters masked) | 52.1% [51.6%–52.6%] |
| character recall | 62.3% [61.9%–62.8%] |
| precision (characters, scored zone) | 60.1% [59.3%–60.8%] |
| over-masking of non-gold text | 1.0% [0.9%–1.0%] |
| documents leaking a personal mention (strict) | 100.0% [100.0%–100.0%] |
| documents leaking a mention verbatim (literal) | 100.0% [100.0%–100.0%] |
| mentions found verbatim in the output | 41.2% [40.7%–41.7%] |

## Per family (strict mention recall)

| family | mentions | recall [95% CI] |
|---|---:|---|
| PERSON | 4,012 | 95.3% [94.4%–96.0%] |
| ADDRESS | 1,709 | 0.4% [0.1%–0.8%] |
| EMAIL | 959 | 99.4% [98.9%–99.8%] |
| PHONE | 137 | 82.5% [74.5%–89.6%] |
| NATIONAL_ID | 783 | 0.0% [0.0%–0.0%] |
| ID | 2,222 | 0.0% [0.0%–0.1%] |

## Per gold origin

| family:origin | mentions | strict recall |
|---|---:|---:|
| ADDRESS:manual | 1,709 | 0.4% |
| EMAIL:manual | 959 | 99.4% |
| ID:manual | 2,222 | 0.0% |
| NATIONAL_ID:manual | 783 | 0.0% |
| PERSON:manual | 4,012 | 95.3% |
| PHONE:manual | 137 | 82.5% |

## Kept by policy (share of mentions touched by a mask, for information)

| family | mentions | touched |
|---|---:|---:|
| DATE | 2,566 | 61.6% |
| LOCATION | 5,241 | 36.4% |
| ORG | 776 | 58.6% |
| OTHER | 4,390 | 7.7% |

## Reproduce

```
python tools/corpus/fetch_real.py --cache DIR --only meddocan_es
python tools/corpus/evaluate_real.py --cache DIR --corpora meddocan_es --countries ES,FR --tag with-fr
```

No document text or gold value is stored in this report; the corpus stays in the local cache.
