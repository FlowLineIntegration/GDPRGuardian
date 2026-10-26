# GDPR Guardian on real corpus `hipe_newseye_fr` (2026-10-26)

- Corpus: HIPE-2022 NewsEye French, historical newspapers. Language `fr`. Licence: CC BY 4.0. Source: https://github.com/hipe-eval/HIPE-2022-data (hipe-eval/HIPE-2022-data@147f5bc3c7fb7e5c6b024a9ffd6503cd019fb9ea (v2.1)).
- Real text: yes (historical OCR).
- Gold: manual (pers, loc, org, time, prod; coarse literal layer).
- Engine: gdprguardian 1.0.0 (native core: True), `Anonymizer(countries="FR", profile="standard")`.
- Documents: 140/140 evaluated, engine errors: 0; 1,574,597 characters; throughput 6039585 chars/s (one thread, shared machine).
- Personal gold mentions: 6,664; kept-by-policy mentions: 8,339.

## Headline (95% bootstrap intervals over documents)

| indicator | value [95% CI] |
|---|---|
| mention recall, strict (no character left) | 45.6% [43.7%–48.1%] |
| mention recall@80 (>= 80% of characters masked) | 47.2% [45.1%–49.5%] |
| character recall | 48.9% [47.2%–50.7%] |
| precision (characters, scored zone) | 74.3% [70.0%–78.6%] |
| over-masking of non-gold text | 0.5% [0.4%–0.6%] |
| documents leaking a personal mention (strict) | 96.7% [93.4%–99.2%] |
| documents leaking a mention verbatim (literal) | 84.4% [77.3%–90.5%] |
| mentions found verbatim in the output | 25.4% [22.0%–28.2%] |

## Per family (strict mention recall)

| family | mentions | recall [95% CI] |
|---|---:|---|
| PERSON | 6,664 | 45.6% [43.7%–48.1%] |

## Per gold origin

| family:origin | mentions | strict recall |
|---|---:|---:|
| PERSON:manual | 6,664 | 45.6% |

## Kept by policy (share of mentions touched by a mask, for information)

| family | mentions | touched |
|---|---:|---:|
| LOCATION | 6,099 | 9.8% |
| ORG | 1,975 | 9.0% |
| OTHER | 265 | 5.7% |

## Reproduce

```
python tools/corpus/fetch_real.py --cache DIR --only hipe_newseye_fr
python tools/corpus/evaluate_real.py --cache DIR --corpora hipe_newseye_fr --tag rules3
```

No document text or gold value is stored in this report; the corpus stays in the local cache.
