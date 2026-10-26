# GDPR Guardian on real corpus `mapa_es` (2026-10-25)

- Corpus: MAPA EUR-Lex legal NER (es). Language `es`. Licence: CC BY 4.0. Source: https://huggingface.co/datasets/joelniklaus/mapa (joelniklaus/mapa@bbb2a0157b760465002fd12a61af81b475cd387a).
- Real text: yes (EU legal texts and judgments, tokenised).
- Gold: manual, single annotator.
- Engine: gdprguardian 1.0.0 (native core: True), `Anonymizer(countries="ES,FR", profile="standard")`.
- Documents: 9/9 evaluated, engine errors: 0; 343,692 characters; throughput 12829450 chars/s (one thread, shared machine).
- Personal gold mentions: 271; kept-by-policy mentions: 787.

## Headline (95% bootstrap intervals over documents)

| indicator | value [95% CI] |
|---|---|
| mention recall, strict (no character left) | 31.7% [23.7%–44.5%] |
| mention recall@80 (>= 80% of characters masked) | 33.9% [25.8%–44.5%] |
| character recall | 48.0% [33.5%–60.4%] |
| precision (characters, scored zone) | 54.9% [34.5%–66.5%] |
| over-masking of non-gold text | 0.1% [0.1%–0.2%] |
| documents leaking a personal mention (strict) | 83.3% [50.0%–100.0%] |
| documents leaking a mention verbatim (literal) | 83.3% [50.0%–100.0%] |
| mentions found verbatim in the output | 50.3% [35.1%–60.9%] |

## Per family (strict mention recall)

| family | mentions | recall [95% CI] |
|---|---:|---|
| PERSON | 271 | 31.7% [23.7%–44.5%] |

## Per gold origin

| family:origin | mentions | strict recall |
|---|---:|---:|
| PERSON:manual | 271 | 31.7% |

## Kept by policy (share of mentions touched by a mask, for information)

| family | mentions | touched |
|---|---:|---:|
| DATE | 460 | 0.0% |
| LOCATION | 113 | 1.8% |
| ORG | 156 | 11.5% |
| OTHER | 58 | 19.0% |

## Reproduce

```
python tools/corpus/fetch_real.py --cache DIR --only mapa_es
python tools/corpus/evaluate_real.py --cache DIR --corpora mapa_es --countries ES,FR --tag with-fr
```

No document text or gold value is stored in this report; the corpus stays in the local cache.
