# GDPR Guardian on real corpus `mapa_de` (2026-10-25)

- Corpus: MAPA EUR-Lex legal NER (de). Language `de`. Licence: CC BY 4.0. Source: https://huggingface.co/datasets/joelniklaus/mapa (joelniklaus/mapa@bbb2a0157b760465002fd12a61af81b475cd387a).
- Real text: yes (EU legal texts and judgments, tokenised).
- Gold: manual, single annotator.
- Engine: gdprguardian 1.0.0 (native core: True), `Anonymizer(countries="DE,FR", profile="standard")`.
- Documents: 12/12 evaluated, engine errors: 0; 450,315 characters; throughput 10733209 chars/s (one thread, shared machine).
- Personal gold mentions: 337; kept-by-policy mentions: 1,083.

## Headline (95% bootstrap intervals over documents)

| indicator | value [95% CI] |
|---|---|
| mention recall, strict (no character left) | 32.0% [21.6%–43.9%] |
| mention recall@80 (>= 80% of characters masked) | 34.1% [25.7%–45.6%] |
| character recall | 39.5% [32.7%–48.7%] |
| precision (characters, scored zone) | 14.1% [10.5%–17.5%] |
| over-masking of non-gold text | 1.5% [1.1%–2.0%] |
| documents leaking a personal mention (strict) | 88.9% [66.7%–100.0%] |
| documents leaking a mention verbatim (literal) | 77.8% [50.0%–100.0%] |
| mentions found verbatim in the output | 52.5% [37.7%–63.7%] |

## Per family (strict mention recall)

| family | mentions | recall [95% CI] |
|---|---:|---|
| PERSON | 336 | 32.1% [21.8%–43.9%] |
| ADDRESS | 1 | 0.0% [0.0%–0.0%] |

## Per gold origin

| family:origin | mentions | strict recall |
|---|---:|---:|
| ADDRESS:manual | 1 | 0.0% |
| PERSON:manual | 336 | 32.1% |

## Kept by policy (share of mentions touched by a mask, for information)

| family | mentions | touched |
|---|---:|---:|
| DATE | 467 | 0.2% |
| LOCATION | 156 | 0.6% |
| ORG | 385 | 4.2% |
| OTHER | 75 | 62.7% |

## Reproduce

```
python tools/corpus/fetch_real.py --cache DIR --only mapa_de
python tools/corpus/evaluate_real.py --cache DIR --corpora mapa_de --countries DE,FR --tag with-fr
```

No document text or gold value is stored in this report; the corpus stays in the local cache.
