# GDPR Guardian on real corpus `mapa_it` (2026-10-25)

- Corpus: MAPA EUR-Lex legal NER (it). Language `it`. Licence: CC BY 4.0. Source: https://huggingface.co/datasets/joelniklaus/mapa (joelniklaus/mapa@bbb2a0157b760465002fd12a61af81b475cd387a).
- Real text: yes (EU legal texts and judgments, tokenised).
- Gold: manual, single annotator.
- Engine: gdprguardian 1.0.0 (native core: True), `Anonymizer(countries="IT,FR", profile="standard")`.
- Documents: 12/12 evaluated, engine errors: 0; 458,822 characters; throughput 14036190 chars/s (one thread, shared machine).
- Personal gold mentions: 110; kept-by-policy mentions: 805.

## Headline (95% bootstrap intervals over documents)

| indicator | value [95% CI] |
|---|---|
| mention recall, strict (no character left) | 38.2% [30.5%–48.2%] |
| mention recall@80 (>= 80% of characters masked) | 42.7% [32.7%–56.4%] |
| character recall | 51.3% [43.8%–68.2%] |
| precision (characters, scored zone) | 23.5% [9.8%–41.2%] |
| over-masking of non-gold text | 0.5% [0.3%–0.6%] |
| documents leaking a personal mention (strict) | 88.9% [66.7%–100.0%] |
| documents leaking a mention verbatim (literal) | 77.8% [50.0%–100.0%] |
| mentions found verbatim in the output | 20.7% [15.0%–34.0%] |

## Per family (strict mention recall)

| family | mentions | recall [95% CI] |
|---|---:|---|
| PERSON | 109 | 38.5% [31.4%–48.5%] |
| ADDRESS | 1 | 0.0% [0.0%–0.0%] |

## Per gold origin

| family:origin | mentions | strict recall |
|---|---:|---:|
| ADDRESS:manual | 1 | 0.0% |
| PERSON:manual | 109 | 38.5% |

## Kept by policy (share of mentions touched by a mask, for information)

| family | mentions | touched |
|---|---:|---:|
| DATE | 470 | 0.0% |
| LOCATION | 163 | 4.9% |
| ORG | 116 | 2.6% |
| OTHER | 56 | 76.8% |

## Reproduce

```
python tools/corpus/fetch_real.py --cache DIR --only mapa_it
python tools/corpus/evaluate_real.py --cache DIR --corpora mapa_it --countries IT,FR --tag with-fr
```

No document text or gold value is stored in this report; the corpus stays in the local cache.
