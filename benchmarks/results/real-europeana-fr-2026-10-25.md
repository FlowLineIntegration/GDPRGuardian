# GDPR Guardian on real corpus `europeana_fr` (2026-10-25)

- Corpus: Europeana Newspapers NER, French (BnF), historical OCR press. Language `fr`. Licence: CC0 1.0. Source: https://github.com/EuropeanaNewspapers/ner-corpora (EuropeanaNewspapers/ner-corpora@6bf838d23112c255fd81431b1187ab30ef6c2d90).
- Real text: yes (noisy 19th-20th c. OCR).
- Gold: manual (PER, LOC, ORG, IO tags).
- Engine: gdprguardian 1.0.0 (native core: True), `Anonymizer(countries="FR", profile="standard")`.
- Documents: 515/515 evaluated, engine errors: 0; 1,005,936 characters; throughput 4551040 chars/s (one thread, shared machine).
- Personal gold mentions: 4,272; kept-by-policy mentions: 5,571.

## Headline (95% bootstrap intervals over documents)

| indicator | value [95% CI] |
|---|---|
| mention recall, strict (no character left) | 71.4% [68.7%–73.8%] |
| mention recall@80 (>= 80% of characters masked) | 71.7% [69.0%–74.1%] |
| character recall | 74.8% [72.1%–77.1%] |
| precision (characters, scored zone) | 76.6% [73.9%–79.3%] |
| over-masking of non-gold text | 0.5% [0.4%–0.5%] |
| documents leaking a personal mention (strict) | 75.1% [71.2%–79.1%] |
| documents leaking a mention verbatim (literal) | 69.2% [64.9%–73.6%] |
| mentions found verbatim in the output | 25.3% [23.0%–28.0%] |

## Per family (strict mention recall)

| family | mentions | recall [95% CI] |
|---|---:|---|
| PERSON | 4,272 | 71.4% [68.7%–73.8%] |

## Per gold origin

| family:origin | mentions | strict recall |
|---|---:|---:|
| PERSON:manual | 4,272 | 71.4% |

## Kept by policy (share of mentions touched by a mask, for information)

| family | mentions | touched |
|---|---:|---:|
| LOCATION | 4,228 | 9.1% |
| ORG | 1,343 | 10.6% |

## Reproduce

```
python tools/corpus/fetch_real.py --cache DIR --only europeana_fr
python tools/corpus/evaluate_real.py --cache DIR --corpora europeana_fr
```

No document text or gold value is stored in this report; the corpus stays in the local cache.
