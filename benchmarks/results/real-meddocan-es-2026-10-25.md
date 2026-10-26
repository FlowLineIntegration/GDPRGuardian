# GDPR Guardian on real corpus `meddocan_es` (2026-10-25)

- Corpus: MEDDOCAN, Spanish clinical case reports (de-identification task). Language `es`. Licence: CC BY 4.0. Source: https://zenodo.org/records/4279323 (Zenodo 10.5281/zenodo.4279323 (meddocan.zip)).
- Real text: yes (real published case reports) with SURROGATE identifiers added by the corpus authors.
- Gold: manual gold (29 PHI types), inter-annotator agreement reported at 98%.
- Engine: gdprguardian 1.0.0 (native core: True), `Anonymizer(countries="ES", profile="standard")`.
- Documents: 1000/1000 evaluated, engine errors: 0; 2,887,969 characters; throughput 11898062 chars/s (one thread, shared machine).
- Personal gold mentions: 9,822; kept-by-policy mentions: 12,973.

## Headline (95% bootstrap intervals over documents)

| indicator | value [95% CI] |
|---|---|
| mention recall, strict (no character left) | 10.9% [10.6%–11.1%] |
| mention recall@80 (>= 80% of characters masked) | 10.9% [10.6%–11.2%] |
| character recall | 14.4% [14.1%–14.8%] |
| precision (characters, scored zone) | 61.1% [60.3%–61.9%] |
| over-masking of non-gold text | 0.0% [0.0%–0.0%] |
| documents leaking a personal mention (strict) | 100.0% [100.0%–100.0%] |
| documents leaking a mention verbatim (literal) | 100.0% [100.0%–100.0%] |
| mentions found verbatim in the output | 89.1% [88.8%–89.3%] |

## Per family (strict mention recall)

| family | mentions | recall [95% CI] |
|---|---:|---|
| PERSON | 4,012 | 0.0% [0.0%–0.0%] |
| ADDRESS | 1,709 | 0.1% [0.0%–0.4%] |
| EMAIL | 959 | 99.3% [98.7%–99.8%] |
| PHONE | 137 | 82.5% [74.5%–89.6%] |
| NATIONAL_ID | 783 | 0.0% [0.0%–0.0%] |
| ID | 2,222 | 0.0% [0.0%–0.0%] |

## Per gold origin

| family:origin | mentions | strict recall |
|---|---:|---:|
| ADDRESS:manual | 1,709 | 0.1% |
| EMAIL:manual | 959 | 99.3% |
| ID:manual | 2,222 | 0.0% |
| NATIONAL_ID:manual | 783 | 0.0% |
| PERSON:manual | 4,012 | 0.0% |
| PHONE:manual | 137 | 82.5% |

## Kept by policy (share of mentions touched by a mask, for information)

| family | mentions | touched |
|---|---:|---:|
| DATE | 2,566 | 61.4% |
| LOCATION | 5,241 | 0.0% |
| ORG | 776 | 0.0% |
| OTHER | 4,390 | 0.0% |

## Reproduce

```
python tools/corpus/fetch_real.py --cache DIR --only meddocan_es
python tools/corpus/evaluate_real.py --cache DIR --corpora meddocan_es
```

No document text or gold value is stored in this report; the corpus stays in the local cache.
