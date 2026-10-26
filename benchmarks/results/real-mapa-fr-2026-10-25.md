# GDPR Guardian on real corpus `mapa_fr` (2026-10-25)

- Corpus: MAPA EUR-Lex legal NER (fr). Language `fr`. Licence: CC BY 4.0. Source: https://huggingface.co/datasets/joelniklaus/mapa (joelniklaus/mapa@bbb2a0157b760465002fd12a61af81b475cd387a).
- Real text: yes (EU legal texts and judgments, tokenised).
- Gold: manual, single annotator.
- Engine: gdprguardian 1.0.0 (native core: True), `Anonymizer(countries="FR", profile="standard")`.
- Documents: 12/12 evaluated, engine errors: 0; 453,160 characters; throughput 13683524 chars/s (one thread, shared machine).
- Personal gold mentions: 282; kept-by-policy mentions: 1,161.

## Headline (95% bootstrap intervals over documents)

| indicator | value [95% CI] |
|---|---|
| mention recall, strict (no character left) | 34.8% [23.7%–44.6%] |
| mention recall@80 (>= 80% of characters masked) | 37.6% [26.0%–47.7%] |
| character recall | 43.6% [33.0%–51.8%] |
| precision (characters, scored zone) | 42.7% [32.2%–53.4%] |
| over-masking of non-gold text | 0.0% [0.0%–0.1%] |
| documents leaking a personal mention (strict) | 88.9% [66.7%–100.0%] |
| documents leaking a mention verbatim (literal) | 88.9% [66.7%–100.0%] |
| mentions found verbatim in the output | 58.9% [43.7%–68.0%] |

## Per family (strict mention recall)

| family | mentions | recall [95% CI] |
|---|---:|---|
| PERSON | 280 | 35.0% [23.8%–44.8%] |
| ADDRESS | 2 | 0.0% [0.0%–0.0%] |

## Per gold origin

| family:origin | mentions | strict recall |
|---|---:|---:|
| ADDRESS:manual | 2 | 0.0% |
| PERSON:manual | 280 | 35.0% |

## Kept by policy (share of mentions touched by a mask, for information)

| family | mentions | touched |
|---|---:|---:|
| DATE | 491 | 0.8% |
| LOCATION | 201 | 1.0% |
| ORG | 343 | 7.3% |
| OTHER | 126 | 53.2% |

## Reproduce

```
python tools/corpus/fetch_real.py --cache DIR --only mapa_fr
python tools/corpus/evaluate_real.py --cache DIR --corpora mapa_fr
```

No document text or gold value is stored in this report; the corpus stays in the local cache.
