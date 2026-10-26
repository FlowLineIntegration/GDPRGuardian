# GDPR Guardian on real corpus `german_ler_de` (2026-10-25)

- Corpus: German LER, federal court decisions (test split). Language `de`. Licence: CC BY 4.0. Source: https://huggingface.co/datasets/elenanereiss/german-ler (elenanereiss/german-ler@405b6923dfd2299da3d76a68220ee15a95bc1eab).
- Real text: yes (court decisions, tokenised).
- Gold: manual (19 fine classes: person, judge, lawyer, street, city, country, organisation, court, law...).
- Engine: gdprguardian 1.0.0 (native core: True), `Anonymizer(countries="DE,FR", profile="standard")`.
- Documents: 334/334 evaluated, engine errors: 0; 1,365,559 characters; throughput 7355746 chars/s (one thread, shared machine).
- Personal gold mentions: 337; kept-by-policy mentions: 4,979.

## Headline (95% bootstrap intervals over documents)

| indicator | value [95% CI] |
|---|---|
| mention recall, strict (no character left) | 22.3% [17.6%–26.7%] |
| mention recall@80 (>= 80% of characters masked) | 22.6% [17.9%–27.1%] |
| character recall | 31.9% [24.9%–38.8%] |
| precision (characters, scored zone) | 5.4% [4.0%–7.0%] |
| over-masking of non-gold text | 0.6% [0.5%–0.7%] |
| documents leaking a personal mention (strict) | 85.9% [81.1%–90.3%] |
| documents leaking a mention verbatim (literal) | 48.7% [41.4%–55.6%] |
| mentions found verbatim in the output | 65.1% [58.1%–72.2%] |

## Per family (strict mention recall)

| family | mentions | recall [95% CI] |
|---|---:|---|
| PERSON | 322 | 23.3% [18.3%–27.9%] |
| ADDRESS | 15 | 0.0% [0.0%–0.0%] |

## Per gold origin

| family:origin | mentions | strict recall |
|---|---:|---:|
| ADDRESS:manual | 15 | 0.0% |
| PERSON:manual | 322 | 23.3% |

## Kept by policy (share of mentions touched by a mask, for information)

| family | mentions | touched |
|---|---:|---:|
| LOCATION | 233 | 4.3% |
| ORG | 795 | 2.5% |
| OTHER | 3,951 | 7.3% |

## Reproduce

```
python tools/corpus/fetch_real.py --cache DIR --only german_ler_de
python tools/corpus/evaluate_real.py --cache DIR --corpora german_ler_de --countries DE,FR --tag with-fr
```

No document text or gold value is stored in this report; the corpus stays in the local cache.
