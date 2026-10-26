# GDPR Guardian on public dataset `gretel_fr` (countries=FR)

- Records: 4426/4426 evaluated, errors: 0
- Throughput: 484056 chars/s, 403.24 docs/s (5313013 chars in 10.976 s, single thread)
- Direct identifiers (policy-scored families): 11986 gold, masked 51.5%, exact-string leak 33.1%
- Over-masking: 38137 detected chars outside gold / 4974836 non-gold = 0.8%; 2472 of 11087 detected spans touch no gold span
- Masked = detected spans cover >= 80% of the gold span characters. Leak = gold span text still present anywhere in the output (also true for repeated short strings).
- Source revision: gretelai/synthetic_pii_finance_multilingual@7b844d16738527a04264f50214cb426a4cea0897 (Apache-2.0)

## Direct identifiers (expected to be masked)

| family | gold | masked | masked rate | exact leaks | leak rate |
|---|---:|---:|---:|---:|---:|
| PERSON | 5624 | 3649 | 64.9% | 1049 | 18.6% |
| ADDRESS | 3575 | 990 | 27.7% | 1667 | 46.6% |
| EMAIL | 432 | 382 | 88.4% | 45 | 10.4% |
| PHONE | 688 | 576 | 83.7% | 112 | 16.3% |
| NATIONAL_ID | 243 | 10 | 4.1% | 233 | 95.9% |
| IBAN | 178 | 133 | 74.7% | 40 | 22.5% |
| BANK_ACCOUNT | 261 | 2 | 0.8% | 259 | 99.2% |
| CARD | 100 | 36 | 36.0% | 64 | 64.0% |
| BIRTH_DATE | 212 | 148 | 69.8% | 64 | 30.2% |
| ID | 484 | 59 | 12.2% | 428 | 88.4% |
| IP | 189 | 187 | 98.9% | 3 | 1.6% |

## Not expected to be masked by policy (generic dates, places, organisations, other)

| family | gold | masked | masked rate | exact leaks | leak rate |
|---|---:|---:|---:|---:|---:|
| DATE | 1281 | 4 | 0.3% | 1278 | 99.8% |
| LOCATION | 61 | 0 | 0.0% | 61 | 100.0% |
| ORG | 3669 | 145 | 4.0% | 3368 | 91.8% |
| OTHER | 822 | 30 | 3.6% | 791 | 96.2% |

## Missed examples

Not published: the examples are values of the source dataset. A local run of `tools/corpus/evaluate_public.py` lists them.
