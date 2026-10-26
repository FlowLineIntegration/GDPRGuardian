# GDPR Guardian on public dataset `mapa_fr` (countries=FR)

- Records: 12/12 evaluated, errors: 0
- Throughput: 716621 chars/s, 18.12 docs/s (474640 chars in 0.662 s, single thread)
- Direct identifiers (policy-scored families): 282 gold, masked 20.9%, exact-string leak 76.6%
- Over-masking: 92 detected chars outside gold / 457711 non-gold = 0.0%; 15 of 152 detected spans touch no gold span
- Masked = detected spans cover >= 80% of the gold span characters. Leak = gold span text still present anywhere in the output (also true for repeated short strings).
- Source revision: joelniklaus/mapa@bbb2a0157b760465002fd12a61af81b475cd387a (CC-BY-4.0)

## Direct identifiers (expected to be masked)

| family | gold | masked | masked rate | exact leaks | leak rate |
|---|---:|---:|---:|---:|---:|
| PERSON | 280 | 59 | 21.1% | 215 | 76.8% |
| ADDRESS | 2 | 0 | 0.0% | 1 | 50.0% |

## Not expected to be masked by policy (generic dates, places, organisations, other)

| family | gold | masked | masked rate | exact leaks | leak rate |
|---|---:|---:|---:|---:|---:|
| DATE | 491 | 1 | 0.2% | 489 | 99.6% |
| LOCATION | 201 | 0 | 0.0% | 201 | 100.0% |
| ORG | 343 | 17 | 5.0% | 325 | 94.8% |
| OTHER | 126 | 1 | 0.8% | 95 | 75.4% |

## Missed examples

Not published: the examples are values of the source dataset. A local run of `tools/corpus/evaluate_public.py` lists them.
