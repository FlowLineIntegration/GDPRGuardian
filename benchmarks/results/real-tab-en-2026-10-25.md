# GDPR Guardian on real corpus `tab_en` (2026-10-25)

- Corpus: TAB, Text Anonymization Benchmark (ECHR, English, test split). Language `en`. Licence: MIT. Source: https://github.com/NorskRegnesentral/text-anonymization-benchmark (NorskRegnesentral/text-anonymization-benchmark@558e09e26d6b36f5f78440074e6a233946d98bd9).
- Real text: yes (ECHR judgments).
- Gold: manual, DIRECT and QUASI mentions of the first annotator.
- Engine: gdprguardian 1.0.0 (native core: True), `Anonymizer(countries="FR", profile="standard")`.
- Documents: 127/127 evaluated, engine errors: 0; 647,638 characters; throughput 8514304 chars/s (one thread, shared machine).
- Personal gold mentions: 958; kept-by-policy mentions: 4,188.

## Headline (95% bootstrap intervals over documents)

| indicator | value [95% CI] |
|---|---|
| mention recall, strict (no character left) | 83.3% [77.3%–88.9%] |
| mention recall@80 (>= 80% of characters masked) | 84.4% [78.5%–89.6%] |
| character recall | 90.6% [86.0%–94.2%] |
| precision (characters, scored zone) | 77.5% [72.7%–81.9%] |
| over-masking of non-gold text | 0.2% [0.2%–0.3%] |
| documents leaking a personal mention (strict) | 37.8% [29.9%–46.5%] |
| documents leaking a mention verbatim (literal) | 20.5% [13.4%–27.6%] |
| mentions found verbatim in the output | 8.8% [5.2%–13.5%] |

## Per family (strict mention recall)

| family | mentions | recall [95% CI] |
|---|---:|---|
| PERSON | 958 | 83.3% [77.3%–88.9%] |

## Per gold origin

| family:origin | mentions | strict recall |
|---|---:|---:|
| PERSON:manual | 958 | 83.3% |

## Kept by policy (share of mentions touched by a mask, for information)

| family | mentions | touched |
|---|---:|---:|
| DATE | 2,487 | 2.4% |
| LOCATION | 294 | 5.8% |
| ORG | 550 | 5.1% |
| OTHER | 857 | 0.5% |

## Reproduce

```
python tools/corpus/fetch_real.py --cache DIR --only tab_en
python tools/corpus/evaluate_real.py --cache DIR --corpora tab_en
```

No document text or gold value is stored in this report; the corpus stays in the local cache.
