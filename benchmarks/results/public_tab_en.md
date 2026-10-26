# GDPR Guardian on public dataset `tab_en` (countries=FR)

- Records: 127/127 evaluated, errors: 0
- Throughput: 462416 chars/s, 90.68 docs/s (647638 chars in 1.401 s, single thread)
- Direct identifiers (policy-scored families): 958 gold, masked 36.6%, exact-string leak 14.2%
- Over-masking: 1260 detected chars outside gold / 578900 non-gold = 0.2%; 107 of 971 detected spans touch no gold span
- Masked = detected spans cover >= 80% of the gold span characters. Leak = gold span text still present anywhere in the output (also true for repeated short strings).
- Source revision: NorskRegnesentral/text-anonymization-benchmark@558e09e26d6b36f5f78440074e6a233946d98bd9 (MIT)

## Direct identifiers (expected to be masked)

| family | gold | masked | masked rate | exact leaks | leak rate |
|---|---:|---:|---:|---:|---:|
| PERSON | 958 | 351 | 36.6% | 136 | 14.2% |

## Not expected to be masked by policy (generic dates, places, organisations, other)

| family | gold | masked | masked rate | exact leaks | leak rate |
|---|---:|---:|---:|---:|---:|
| DATE | 2487 | 0 | 0.0% | 2487 | 100.0% |
| LOCATION | 294 | 5 | 1.7% | 284 | 96.6% |
| ORG | 550 | 8 | 1.5% | 525 | 95.5% |
| OTHER | 857 | 1 | 0.1% | 853 | 99.5% |

## Missed examples

Not published: the examples are values of the source dataset. A local run of `tools/corpus/evaluate_public.py` lists them.
