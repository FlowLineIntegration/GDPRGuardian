# GDPR Guardian on real corpus `parlamint_fr` (2026-10-26)

- Corpus: ParlaMint-FR 5.0, Assemblée nationale debates 2017-2022 (sample). Language `fr`. Licence: CC BY 4.0. Source: http://hdl.handle.net/11356/2004 (ParlaMint-FR.tgz (handle 11356/2004, version 5.0)).
- Real text: yes.
- Gold: speaker labels rendered from the TEI 'who' metadata (exact); in-text mentions = exact matches of the full name, or civility + surname, of the 1,000+ persons of the corpus person list.
- Engine: gdprguardian 1.0.0 (native core: True), `Anonymizer(countries="FR", profile="standard")`.
- Documents: 300/300 evaluated, engine errors: 0; 1,029,684 characters; throughput 5116694 chars/s (one thread, shared machine).
- Personal gold mentions: 3,006; kept-by-policy mentions: 0.

## Headline (95% bootstrap intervals over documents)

| indicator | value [95% CI] |
|---|---|
| mention recall, strict (no character left) | 98.3% [97.6%–99.0%] |
| mention recall@80 (>= 80% of characters masked) | 98.4% [97.7%–99.1%] |
| character recall | 99.1% [98.7%–99.5%] |
| precision (characters, scored zone) | n/a |
| over-masking of non-gold text | n/a |
| documents leaking a personal mention (strict) | 8.7% [5.7%–12.1%] |
| documents leaking a mention verbatim (literal) | 3.0% [1.3%–5.3%] |
| mentions found verbatim in the output | 0.3% [0.1%–0.6%] |

Precision and over-masking are not measurable here: the gold does not cover every person named in the text.

## Per family (strict mention recall)

| family | mentions | recall [95% CI] |
|---|---:|---|
| PERSON | 3,006 | 98.3% [97.6%–99.0%] |

## Per gold origin

| family:origin | mentions | strict recall |
|---|---:|---:|
| PERSON:mention | 995 | 97.7% |
| PERSON:speaker | 2,011 | 98.7% |

## Reproduce

```
python tools/corpus/fetch_real.py --cache DIR --only parlamint_fr
python tools/corpus/evaluate_real.py --cache DIR --corpora parlamint_fr --tag rules3
```

No document text or gold value is stored in this report; the corpus stays in the local cache.
