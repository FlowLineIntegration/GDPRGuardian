# GDPR Guardian on real corpus `mapa_pt` (2026-10-25)

- Corpus: MAPA EUR-Lex legal NER (pt). Language `pt`. Licence: CC BY 4.0. Source: https://huggingface.co/datasets/joelniklaus/mapa (joelniklaus/mapa@bbb2a0157b760465002fd12a61af81b475cd387a).
- Real text: yes (EU legal texts and judgments, tokenised).
- Gold: manual, single annotator.
- Engine: gdprguardian 1.0.0 (native core: True), `Anonymizer(countries="PT", profile="standard")`.
- Documents: 12/12 evaluated, engine errors: 0; 440,808 characters; throughput 21928891 chars/s (one thread, shared machine).
- Personal gold mentions: 378; kept-by-policy mentions: 1,027.

## Headline (95% bootstrap intervals over documents)

| indicator | value [95% CI] |
|---|---|
| mention recall, strict (no character left) | 0.0% [0.0%–0.0%] |
| mention recall@80 (>= 80% of characters masked) | 0.0% [0.0%–0.0%] |
| character recall | 0.0% [0.0%–0.0%] |
| precision (characters, scored zone) | n/a |
| over-masking of non-gold text | 0.0% [0.0%–0.0%] |
| documents leaking a personal mention (strict) | 100.0% [100.0%–100.0%] |
| documents leaking a mention verbatim (literal) | 100.0% [100.0%–100.0%] |
| mentions found verbatim in the output | 100.0% [100.0%–100.0%] |

## Per family (strict mention recall)

| family | mentions | recall [95% CI] |
|---|---:|---|
| PERSON | 375 | 0.0% [0.0%–0.0%] |
| ADDRESS | 3 | 0.0% [0.0%–0.0%] |

## Per gold origin

| family:origin | mentions | strict recall |
|---|---:|---:|
| ADDRESS:manual | 3 | 0.0% |
| PERSON:manual | 375 | 0.0% |

## Kept by policy (share of mentions touched by a mask, for information)

| family | mentions | touched |
|---|---:|---:|
| DATE | 476 | 0.0% |
| LOCATION | 204 | 0.0% |
| ORG | 311 | 0.0% |
| OTHER | 36 | 0.0% |

## Reproduce

```
python tools/corpus/fetch_real.py --cache DIR --only mapa_pt
python tools/corpus/evaluate_real.py --cache DIR --corpora mapa_pt --tag rules2
```

No document text or gold value is stored in this report; the corpus stays in the local cache.
