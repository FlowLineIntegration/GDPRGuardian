# Real corpora: rules2 -> rules3 (2026-10-26)

Strict mention recall, character precision on the scored zone, documents leaking a personal mention. Scores only; no text. Dev halves were used to design the rules; test halves and unseen sets were not looked at.

| corpus | split | docs | recall before | recall after | precision before | precision after | doc leak before | doc leak after | per family (after) |
|---|---|---:|---|---|---|---|---|---|---|
| boamp-fr | dev | 1523 | 90.8% | 90.9% | 86.6% | 86.5% | 39.4% | 39.1% | PERSON 88.6%→88.6%, ADDRESS 84.9%→85.2%, EMAIL 99.9%→99.9%, PHONE 88.9%→88.9% |
| bodacc-fr | dev | 1358 | 97.5% | 97.5% | 99.3% | 99.3% | 11.0% | 11.0% | PERSON 98.0%→98.0%, ADDRESS 95.1%→95.1%, ID 98.4%→98.4% |
| europeana-fr | dev | 270 | 71.9% | 72.0% | 77.0% | 76.8% | 71.6% | 71.6% | PERSON 71.9%→72.0% |
| german-ler-de | dev | 165 | 0.0% | 0.0% | 0.0% | 0.0% | 100.0% | 100.0% | PERSON 0.0%→0.0%, ADDRESS 0.0%→0.0% |
| hipe-newseye-fr | dev | 68 | 46.5% | 46.5% | 73.3% | 73.2% | 94.9% | 94.9% | PERSON 46.5%→46.5% |
| judilibre-fr | dev | 145 | n/a | n/a | n/a | n/a | n/a | n/a |  |
| mapa-de | dev | 6 | 0.0% | 0.0% | n/a | n/a | 100.0% | 100.0% | PERSON 0.0%→0.0% |
| mapa-es | dev | 4 | 0.0% | 0.0% | n/a | n/a | 100.0% | 100.0% | PERSON 0.0%→0.0% |
| mapa-fr | dev | 4 | 37.8% | 37.8% | 36.8% | 36.8% | 100.0% | 100.0% | PERSON 38.1%→38.1%, ADDRESS 0.0%→0.0% |
| mapa-it | dev | 5 | 0.0% | 0.0% | n/a | n/a | 100.0% | 100.0% | PERSON 0.0%→0.0% |
| mapa-nl | dev | 7 | 0.0% | 0.0% | 0.0% | 0.0% | 100.0% | 100.0% | PERSON 0.0%→0.0% |
| mapa-pt | dev | 8 | 0.0% | 0.0% | n/a | n/a | 100.0% | 100.0% | PERSON 0.0%→0.0%, ADDRESS 0.0%→0.0% |
| meddocan-es | dev | 531 | 11.0% | 11.0% | 61.1% | 61.1% | 100.0% | 100.0% | PERSON 0.0%→0.0%, ADDRESS 0.2%→0.2%, EMAIL 99.6%→99.6%, PHONE 82.0%→82.0%, ID 0.0%→0.0% |
| parlamint-fr | dev | 156 | 98.2% | 98.2% | n/a | n/a | 10.3% | 10.3% | PERSON 98.2%→98.2% |
| tab-en | dev | 72 | 83.6% | 83.6% | 77.2% | 77.2% | 41.7% | 41.7% | PERSON 83.6%→83.6% |
| boamp-fr | test | 1477 | 89.5% | 89.6% | 87.3% | 87.3% | 39.4% | 39.3% | PERSON 88.8%→88.8%, ADDRESS 82.2%→82.3%, EMAIL 100.0%→100.0%, PHONE 89.9%→89.9% |
| bodacc-fr | test | 1335 | 97.8% | 97.8% | 99.1% | 99.1% | 10.1% | 10.1% | PERSON 98.4%→98.4%, ADDRESS 94.6%→94.6%, ID 99.3%→99.3% |
| europeana-fr | test | 245 | 71.0% | 71.1% | 76.3% | 76.2% | 78.9% | 78.9% | PERSON 71.0%→71.1% |
| german-ler-de | test | 169 | 0.0% | 0.0% | n/a | n/a | 100.0% | 100.0% | PERSON 0.0%→0.0%, ADDRESS 0.0%→0.0% |
| hipe-newseye-fr | test | 72 | 44.8% | 44.8% | 75.2% | 75.1% | 98.4% | 98.4% | PERSON 44.8%→44.8% |
| judilibre-fr | test | 155 | n/a | n/a | n/a | n/a | n/a | n/a |  |
| mapa-de | test | 6 | 0.0% | 0.0% | n/a | n/a | 100.0% | 100.0% | PERSON 0.0%→0.0%, ADDRESS 0.0%→0.0% |
| mapa-es | test | 5 | 0.0% | 0.0% | n/a | n/a | 100.0% | 100.0% | PERSON 0.0%→0.0% |
| mapa-fr | test | 8 | 32.5% | 33.1% | 46.8% | 47.1% | 83.3% | 83.3% | PERSON 32.7%→33.3%, ADDRESS 0.0%→0.0% |
| mapa-it | test | 7 | 0.0% | 0.0% | n/a | n/a | 100.0% | 100.0% | PERSON 0.0%→0.0%, ADDRESS 0.0%→0.0% |
| mapa-nl | test | 5 | 0.0% | 0.0% | n/a | n/a | 100.0% | 100.0% | PERSON 0.0%→0.0% |
| mapa-pt | test | 4 | 0.0% | 0.0% | n/a | n/a | 100.0% | 100.0% | PERSON 0.0%→0.0% |
| meddocan-es | test | 469 | 10.7% | 10.7% | 61.1% | 61.1% | 100.0% | 100.0% | PERSON 0.0%→0.0%, ADDRESS 0.0%→0.0%, EMAIL 98.9%→98.9%, PHONE 83.3%→83.3%, ID 0.0%→0.0% |
| parlamint-fr | test | 144 | 98.5% | 98.5% | n/a | n/a | 7.0% | 7.0% | PERSON 98.5%→98.5% |
| tab-en | test | 55 | 82.6% | 82.8% | 78.3% | 77.9% | 32.7% | 32.7% | PERSON 82.6%→82.8% |
| boamp-fr | unseen-2021 | 1500 | 90.1% | 90.1% | 87.9% | 87.9% | 48.3% | 47.9% | PERSON 86.2%→86.2%, ADDRESS 83.9%→84.1%, EMAIL 100.0%→100.0%, PHONE 90.5%→90.5% |
| bodacc-fr | unseen-2026-08 | 2689 | 97.6% | 97.6% | 99.2% | 99.2% | 10.2% | 10.2% | PERSON 98.0%→98.0%, ADDRESS 95.0%→95.1%, ID 99.2%→99.2% |
| german-ler-de | with-fr | 334 | 20.8% | 22.3% | 5.4% | 5.4% | 86.4% | 85.9% | PERSON 21.7%→23.3%, ADDRESS 0.0%→0.0% |
| mapa-de | with-fr | 12 | 30.6% | 33.5% | 14.4% | 15.0% | 88.9% | 88.9% | PERSON 30.7%→33.6%, ADDRESS 0.0%→0.0% |
| mapa-es | with-fr | 9 | 31.7% | 31.7% | 55.2% | 54.9% | 83.3% | 83.3% | PERSON 31.7%→31.7% |
| mapa-it | with-fr | 12 | 38.2% | 40.9% | 23.5% | 24.9% | 88.9% | 88.9% | PERSON 38.5%→41.3%, ADDRESS 0.0%→0.0% |
| mapa-nl | with-fr | 12 | 31.1% | 32.0% | 37.9% | 38.3% | 88.9% | 88.9% | PERSON 31.1%→32.0% |
| mapa-pt | with-fr | 12 | 38.1% | 41.8% | 31.4% | 31.8% | 77.8% | 77.8% | PERSON 38.4%→42.1%, ADDRESS 0.0%→0.0% |
| meddocan-es | with-fr | 1000 | 49.8% | 49.8% | 60.2% | 60.1% | 100.0% | 100.0% | PERSON 95.3%→95.3%, ADDRESS 0.4%→0.4%, EMAIL 99.4%→99.4%, PHONE 82.5%→82.5%, ID 0.0%→0.0% |

Split rule: SHA-256('gdprguardian-rules2-2026-10-25|' + document id), first 32 bits even -> dev, odd -> test (tools/corpus/real_common.split_of).
