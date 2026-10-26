# GDPR Guardian on real corpus `mapa_de` (2026-10-25)

- Corpus: MAPA EUR-Lex legal NER (de). Language `de`. Licence: CC BY 4.0. Source: https://huggingface.co/datasets/joelniklaus/mapa (joelniklaus/mapa@bbb2a0157b760465002fd12a61af81b475cd387a).
- Real text: yes (EU legal texts and judgments, tokenised).
- Gold: manual, single annotator.
- Engine: gdprguardian 1.0.0 (native core: True), `Anonymizer(countries="DE", profile="standard")`.
- Documents: 12/12 evaluated, engine errors: 0; 450,315 characters; throughput 31098244 chars/s (one thread, shared machine).
- Personal gold mentions: 337; kept-by-policy mentions: 1,083.

## Headline (95% bootstrap intervals over documents)

| indicator | value [95% CI] |
|---|---|
| mention recall, strict (no character left) | 0.0% [0.0%–0.0%] |
| mention recall@80 (>= 80% of characters masked) | 0.0% [0.0%–0.0%] |
| character recall | 0.0% [0.0%–0.0%] |
| precision (characters, scored zone) | n/a |
| over-masking of non-gold text | 0.0% [0.0%–0.0%] |
| documents leaking a personal mention (strict) | 100.0% [100.0%–100.0%] |
| documents leaking a mention verbatim (literal) | 88.9% [66.7%–100.0%] |
| mentions found verbatim in the output | 100.0% [100.0%–100.0%] |

## Per family (strict mention recall)

| family | mentions | recall [95% CI] |
|---|---:|---|
| PERSON | 336 | 0.0% [0.0%–0.0%] |
| ADDRESS | 1 | 0.0% [0.0%–0.0%] |

## Per gold origin

| family:origin | mentions | strict recall |
|---|---:|---:|
| ADDRESS:manual | 1 | 0.0% |
| PERSON:manual | 336 | 0.0% |

## Kept by policy (share of mentions touched by a mask, for information)

| family | mentions | touched |
|---|---:|---:|
| DATE | 467 | 0.0% |
| LOCATION | 156 | 0.0% |
| ORG | 385 | 0.0% |
| OTHER | 75 | 0.0% |

## Reproduce

```
python tools/corpus/fetch_real.py --cache DIR --only mapa_de
python tools/corpus/evaluate_real.py --cache DIR --corpora mapa_de
```

No document text or gold value is stored in this report; the corpus stays in the local cache.
