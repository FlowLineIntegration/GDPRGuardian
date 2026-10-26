# Real corpora: base -> rules2 (2026-10-25)

Strict mention recall, character precision on the scored zone, documents leaking a personal mention. Scores only; no text. Dev halves were used to design the rules; test halves and unseen sets were not looked at.

| corpus | split | docs | recall before | recall after | precision before | precision after | doc leak before | doc leak after | per family (after) |
|---|---|---:|---|---|---|---|---|---|---|
| boamp-fr | dev | 1523 | 85.5% | 90.8% | 80.8% | 86.6% | 54.2% | 39.4% | PERSON 88.6%→88.6%, ADDRESS 71.2%→84.9%, EMAIL 99.9%→99.9%, PHONE 88.9%→88.9% |
| bodacc-fr | dev | 1358 | 79.0% | 97.5% | 90.4% | 99.3% | 92.3% | 11.0% | PERSON 98.0%→98.0%, ADDRESS 89.8%→95.1%, ID 5.4%→98.4% |
| europeana-fr | dev | 270 | 71.9% | 71.9% | 77.1% | 77.0% | 71.6% | 71.6% | PERSON 71.9%→71.9% |
| german-ler-de | dev | 165 | 0.0% | 0.0% | 0.0% | 0.0% | 100.0% | 100.0% | PERSON 0.0%→0.0%, ADDRESS 0.0%→0.0% |
| hipe-newseye-fr | dev | 68 | 46.5% | 46.5% | 73.2% | 73.3% | 94.9% | 94.9% | PERSON 46.5%→46.5% |
| judilibre-fr | dev | 145 | n/a | n/a | n/a | n/a | n/a | n/a |  |
| mapa-de | dev | 6 | 0.0% | 0.0% | n/a | n/a | 100.0% | 100.0% | PERSON 0.0%→0.0% |
| mapa-es | dev | 4 | 0.0% | 0.0% | n/a | n/a | 100.0% | 100.0% | PERSON 0.0%→0.0% |
| mapa-fr | dev | 4 | 37.8% | 37.8% | 36.8% | 36.8% | 100.0% | 100.0% | PERSON 38.1%→38.1%, ADDRESS 0.0%→0.0% |
| mapa-it | dev | 5 | 0.0% | 0.0% | n/a | n/a | 100.0% | 100.0% | PERSON 0.0%→0.0% |
| mapa-nl | dev | 7 | 0.0% | 0.0% | 0.0% | 0.0% | 100.0% | 100.0% | PERSON 0.0%→0.0% |
| mapa-pt | dev | 8 | 0.0% | 0.0% | n/a | n/a | 100.0% | 100.0% | PERSON 0.0%→0.0%, ADDRESS 0.0%→0.0% |
| meddocan-es | dev | 531 | 11.0% | 11.0% | 61.1% | 61.1% | 100.0% | 100.0% | PERSON 0.0%→0.0%, ADDRESS 0.2%→0.2%, EMAIL 99.6%→99.6%, PHONE 82.0%→82.0%, ID 0.0%→0.0% |
| parlamint-fr | dev | 156 | 92.9% | 98.2% | n/a | n/a | 32.7% | 10.3% | PERSON 92.9%→98.2% |
| tab-en | dev | 72 | 83.6% | 83.6% | 77.3% | 77.2% | 41.7% | 41.7% | PERSON 83.6%→83.6% |
| boamp-fr | test | 1477 | 84.4% | 89.5% | 81.2% | 87.3% | 52.8% | 39.4% | PERSON 88.8%→88.8%, ADDRESS 69.8%→82.2%, EMAIL 100.0%→100.0%, PHONE 89.9%→89.9% |
| bodacc-fr | test | 1335 | 78.9% | 97.8% | 89.8% | 99.1% | 93.0% | 10.1% | PERSON 98.3%→98.4%, ADDRESS 88.4%→94.6%, ID 5.1%→99.3% |
| europeana-fr | test | 245 | 71.0% | 71.0% | 76.1% | 76.3% | 78.9% | 78.9% | PERSON 71.0%→71.0% |
| german-ler-de | test | 169 | 0.0% | 0.0% | n/a | n/a | 100.0% | 100.0% | PERSON 0.0%→0.0%, ADDRESS 0.0%→0.0% |
| hipe-newseye-fr | test | 72 | 44.7% | 44.8% | 75.1% | 75.2% | 98.4% | 98.4% | PERSON 44.7%→44.8% |
| judilibre-fr | test | 155 | n/a | n/a | n/a | n/a | n/a | n/a |  |
| mapa-de | test | 6 | 0.0% | 0.0% | n/a | n/a | 100.0% | 100.0% | PERSON 0.0%→0.0%, ADDRESS 0.0%→0.0% |
| mapa-es | test | 5 | 0.0% | 0.0% | n/a | n/a | 100.0% | 100.0% | PERSON 0.0%→0.0% |
| mapa-fr | test | 8 | 32.5% | 32.5% | 46.8% | 46.8% | 83.3% | 83.3% | PERSON 32.7%→32.7%, ADDRESS 0.0%→0.0% |
| mapa-it | test | 7 | 0.0% | 0.0% | n/a | n/a | 100.0% | 100.0% | PERSON 0.0%→0.0%, ADDRESS 0.0%→0.0% |
| mapa-nl | test | 5 | 0.0% | 0.0% | n/a | n/a | 100.0% | 100.0% | PERSON 0.0%→0.0% |
| mapa-pt | test | 4 | 0.0% | 0.0% | n/a | n/a | 100.0% | 100.0% | PERSON 0.0%→0.0% |
| meddocan-es | test | 469 | 10.7% | 10.7% | 61.1% | 61.1% | 100.0% | 100.0% | PERSON 0.0%→0.0%, ADDRESS 0.0%→0.0%, EMAIL 98.9%→98.9%, PHONE 83.3%→83.3%, ID 0.0%→0.0% |
| parlamint-fr | test | 144 | 93.7% | 98.5% | n/a | n/a | 27.3% | 7.0% | PERSON 93.7%→98.5% |
| tab-en | test | 55 | 82.8% | 82.6% | 77.9% | 78.3% | 32.7% | 32.7% | PERSON 82.8%→82.6% |
| boamp-fr | unseen-2021 | 1500 | 83.8% | 90.1% | 83.3% | 87.9% | 66.1% | 48.3% | PERSON 86.2%→86.2%, ADDRESS 68.8%→83.9%, EMAIL 100.0%→100.0%, PHONE 90.5%→90.5% |
| bodacc-fr | unseen-2026-08 | 2689 | 79.3% | 97.6% | 90.1% | 99.2% | 91.9% | 10.2% | PERSON 98.0%→98.0%, ADDRESS 90.1%→95.0%, ID 5.2%→99.2% |
| german-ler-de | with-fr | 334 | 22.3% | 20.8% | 5.4% | 5.4% | 85.9% | 86.4% | PERSON 23.3%→21.7%, ADDRESS 0.0%→0.0% |
| mapa-de | with-fr | 12 | 32.0% | 30.6% | 14.1% | 14.4% | 88.9% | 88.9% | PERSON 32.1%→30.7%, ADDRESS 0.0%→0.0% |
| mapa-es | with-fr | 9 | 31.7% | 31.7% | 54.9% | 55.2% | 83.3% | 83.3% | PERSON 31.7%→31.7% |
| mapa-it | with-fr | 12 | 38.2% | 38.2% | 23.5% | 23.5% | 88.9% | 88.9% | PERSON 38.5%→38.5%, ADDRESS 0.0%→0.0% |
| mapa-nl | with-fr | 12 | 31.1% | 31.1% | 37.9% | 37.9% | 88.9% | 88.9% | PERSON 31.1%→31.1% |
| mapa-pt | with-fr | 12 | 40.2% | 38.1% | 31.0% | 31.4% | 77.8% | 77.8% | PERSON 40.5%→38.4%, ADDRESS 0.0%→0.0% |
| meddocan-es | with-fr | 1000 | 49.8% | 49.8% | 60.1% | 60.2% | 100.0% | 100.0% | PERSON 95.3%→95.3%, ADDRESS 0.4%→0.4%, EMAIL 99.4%→99.4%, PHONE 82.5%→82.5%, ID 0.0%→0.0% |

Split rule: SHA-256('gdprguardian-rules2-2026-10-25|' + document id), first 32 bits even -> dev, odd -> test (tools/corpus/real_common.split_of).
