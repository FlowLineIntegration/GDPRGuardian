# GDPR Guardian on public dataset `fr_pii_bench` (countries=FR)

- Records: 300/300 evaluated, errors: 0
- Throughput: 184468 chars/s, 505.7 docs/s (109433 chars in 0.593 s, single thread)
- Direct identifiers (policy-scored families): 1897 gold, masked 83.8%, exact-string leak 12.4%
- Over-masking: 335 detected chars outside gold / 67227 non-gold = 0.5%; 36 of 1852 detected spans touch no gold span
- Masked = detected spans cover >= 80% of the gold span characters. Leak = gold span text still present anywhere in the output (also true for repeated short strings).
- Source revision: JaqueBill/fr-pii-bench@5476b0a489249047a478083ac856a328d0e4d2c3 (CC-BY-4.0)

## Direct identifiers (expected to be masked)

| family | gold | masked | masked rate | exact leaks | leak rate |
|---|---:|---:|---:|---:|---:|
| PERSON | 488 | 486 | 99.6% | 2 | 0.4% |
| ADDRESS | 397 | 325 | 81.9% | 0 | 0.0% |
| EMAIL | 168 | 168 | 100.0% | 0 | 0.0% |
| PHONE | 169 | 167 | 98.8% | 2 | 1.2% |
| NATIONAL_ID | 131 | 131 | 100.0% | 0 | 0.0% |
| TAX_ID | 55 | 14 | 25.4% | 41 | 74.6% |
| IBAN | 131 | 131 | 100.0% | 0 | 0.0% |
| BIRTH_DATE | 113 | 78 | 69.0% | 35 | 31.0% |
| ID | 245 | 90 | 36.7% | 155 | 63.3% |

## Not expected to be masked by policy (generic dates, places, organisations, other)

| family | gold | masked | masked rate | exact leaks | leak rate |
|---|---:|---:|---:|---:|---:|
| ORG | 208 | 29 | 13.9% | 55 | 26.4% |

## Missed examples

Not published: the examples are values of the source dataset. A local run of `tools/corpus/evaluate_public.py` lists them.
