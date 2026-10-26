# GDPR Guardian on public dataset `openpii_fr` (countries=all)

- Records: 3000/3000 evaluated, errors: 0
- Throughput: 191832 chars/s, 432.9 docs/s (1329406 chars in 6.93 s, single thread)
- Direct identifiers (policy-scored families): 12366 gold, masked 46.3%, exact-string leak 50.8%
- Over-masking: 1741 detected chars outside gold / 1048319 non-gold = 0.2%; 101 of 6356 detected spans touch no gold span
- Masked = detected spans cover >= 80% of the gold span characters. Leak = gold span text still present anywhere in the output (also true for repeated short strings).
- Source revision: ai4privacy/pii-masking-openpii-1m@ecfdc547f4a0955600cfe6ab98ba2a162207fcc0 (CC-BY-4.0)

## Direct identifiers (expected to be masked)

| family | gold | masked | masked rate | exact leaks | leak rate |
|---|---:|---:|---:|---:|---:|
| PERSON | 3299 | 2119 | 64.2% | 982 | 29.8% |
| ADDRESS | 2133 | 646 | 30.3% | 1457 | 68.3% |
| EMAIL | 1716 | 1694 | 98.7% | 2 | 0.1% |
| PHONE | 1299 | 307 | 23.6% | 912 | 70.2% |
| NATIONAL_ID | 1905 | 770 | 40.4% | 1119 | 58.7% |
| TAX_ID | 594 | 106 | 17.8% | 485 | 81.7% |
| CARD | 757 | 87 | 11.5% | 670 | 88.5% |
| ID | 663 | 2 | 0.3% | 655 | 98.8% |

## Not expected to be masked by policy (generic dates, places, organisations, other)

| family | gold | masked | masked rate | exact leaks | leak rate |
|---|---:|---:|---:|---:|---:|
| DATE | 2991 | 215 | 7.2% | 2774 | 92.7% |
| LOCATION | 1722 | 225 | 13.1% | 1398 | 81.2% |
| OTHER | 3991 | 248 | 6.2% | 3743 | 93.8% |

## Missed examples

Not published: the examples are values of the source dataset. A local run of `tools/corpus/evaluate_public.py` lists them.
