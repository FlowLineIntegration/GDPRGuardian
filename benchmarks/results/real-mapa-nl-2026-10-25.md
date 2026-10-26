# GDPR Guardian on real corpus `mapa_nl` (2026-10-25)

- Corpus: MAPA EUR-Lex legal NER (nl). Language `nl`. Licence: CC BY 4.0. Source: https://huggingface.co/datasets/joelniklaus/mapa (joelniklaus/mapa@bbb2a0157b760465002fd12a61af81b475cd387a).
- Real text: yes (EU legal texts and judgments, tokenised).
- Gold: manual, single annotator.
- Engine: gdprguardian 1.0.0 (native core: True), `Anonymizer(countries="NL", profile="standard")`.
- Documents: 12/12 evaluated, engine errors: 0; 451,012 characters; throughput 34842248 chars/s (one thread, shared machine).
- Personal gold mentions: 363; kept-by-policy mentions: 805.

## Headline (95% bootstrap intervals over documents)

| indicator | value [95% CI] |
|---|---|
| mention recall, strict (no character left) | 0.0% [0.0%–0.0%] |
| mention recall@80 (>= 80% of characters masked) | 0.0% [0.0%–0.0%] |
| character recall | 0.0% [0.0%–0.0%] |
| precision (characters, scored zone) | 0.0% [0.0%–0.0%] |
| over-masking of non-gold text | 0.0% [0.0%–0.0%] |
| documents leaking a personal mention (strict) | 100.0% [100.0%–100.0%] |
| documents leaking a mention verbatim (literal) | 88.9% [66.7%–100.0%] |
| mentions found verbatim in the output | 100.0% [100.0%–100.0%] |

## Per family (strict mention recall)

| family | mentions | recall [95% CI] |
|---|---:|---|
| PERSON | 363 | 0.0% [0.0%–0.0%] |

## Per gold origin

| family:origin | mentions | strict recall |
|---|---:|---:|
| PERSON:manual | 363 | 0.0% |

## Kept by policy (share of mentions touched by a mask, for information)

| family | mentions | touched |
|---|---:|---:|
| DATE | 484 | 0.2% |
| LOCATION | 84 | 0.0% |
| ORG | 222 | 0.0% |
| OTHER | 15 | 0.0% |

## Reproduce

```
python tools/corpus/fetch_real.py --cache DIR --only mapa_nl
python tools/corpus/evaluate_real.py --cache DIR --corpora mapa_nl
```

No document text or gold value is stored in this report; the corpus stays in the local cache.
