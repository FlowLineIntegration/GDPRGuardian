# GDPR Guardian on real corpus `boamp_fr` (2026-10-25)

- Corpus: BOAMP, public procurement notices 2022-2023 (IDENTITE schema). Language `fr`. Licence: Licence Ouverte / Open Licence (Etalab), DILA. Source: https://www.data.gouv.fr/datasets/boamp (Opendatasoft API, publications of 2022-01..2023-12 (125 per month), fetched 2026-10-25).
- Real text: yes (values and free text are real; 'Label : value' layout rendered by us).
- Gold: exact by construction: e-mail, phone, fax and street address fields of every party block; contact person names extracted from the CONTACT/CORRESPONDANT fields by a rule (civility and role removed).
- Engine: gdprguardian 1.0.0 (native core: True), `Anonymizer(countries="FR", profile="standard")`.
- Documents: 3000/3000 evaluated, engine errors: 0; 18,224,002 characters; throughput 5990321 chars/s (one thread, shared machine).
- Personal gold mentions: 24,404; kept-by-policy mentions: 35,133.

## Headline (95% bootstrap intervals over documents)

| indicator | value [95% CI] |
|---|---|
| mention recall, strict (no character left) | 84.5% [83.1%–85.8%] |
| mention recall@80 (>= 80% of characters masked) | 88.5% [87.2%–89.5%] |
| character recall | 89.0% [88.0%–90.0%] |
| precision (characters, scored zone) | 80.9% [79.1%–82.5%] |
| over-masking of non-gold text | 0.5% [0.5%–0.6%] |
| documents leaking a personal mention (strict) | 53.8% [52.0%–55.7%] |
| documents leaking a mention verbatim (literal) | 11.9% [10.7%–13.2%] |
| mentions found verbatim in the output | 3.2% [2.7%–3.6%] |

## Per family (strict mention recall)

| family | mentions | recall [95% CI] |
|---|---:|---|
| PERSON | 693 | 88.5% [85.4%–91.2%] |
| ADDRESS | 9,715 | 69.4% [66.9%–71.7%] |
| EMAIL | 7,230 | 99.9% [99.9%–100.0%] |
| PHONE | 6,766 | 89.4% [87.9%–91.0%] |

## Per gold origin

| family:origin | mentions | strict recall |
|---|---:|---:|
| ADDRESS:field | 9,715 | 69.4% |
| EMAIL:field | 7,125 | 100.0% |
| EMAIL:repeat | 105 | 96.2% |
| PERSON:field | 674 | 90.7% |
| PERSON:repeat | 19 | 10.5% |
| PHONE:field | 6,766 | 89.4% |

## Kept by policy (share of mentions touched by a mask, for information)

| family | mentions | touched |
|---|---:|---:|
| DATE | 13,093 | 0.0% |
| LOCATION | 5,399 | 50.5% |
| ORG | 14,439 | 50.6% |
| ORG_ID | 2,202 | 0.1% |

## Manual review of a sample

- Gold reviewed by hand on two random samples of 50 notices (seeds 20261025 and 20261026). The second sample was drawn after the contact-parsing fixes and is the estimate for the gold used here. Lines of codes, amounts, criteria and titles were hidden in the second review.
- sample_1_before_fixes: seed 20261025: 9 of 50 documents with a personal-gold error; 15 errors for about 481 personal mentions (3.1%): 12 missing (contact names written with a role or an e-mail, a lawyer awardee labelled as an organisation, street addresses typed inside a name or ID field), 2 wrong labels (a postcode-only line labelled as a street address), 1 boundary (a service name inside the address field). Fixed: contact parser (civilities, roles, several persons, e-mails and phones inside the field), awardee with a civility labelled PERSON, house-number rule for addresses, address typed in the ID field.
- sample_2_after_fixes: seed 20261026: 6 of 50 documents with an error; 6 errors for 287 personal mentions (2.1%, 95% Wilson interval 1.0-4.5%): 4 missing (a name after 'Monsieur le Président', a sole-trader awardee written 'Surname Given-name' without civility and labelled ORG, two street addresses typed in the city field or glued to 'Hôtel de Ville'), 1 wrong (a tunnel name with a department number labelled as a street address), 1 boundary (unit names inside the address field). Not fixed, to keep this sample an unbiased estimate.
- documents_reviewed: 100
- gold_error_rate_documents: 6/50 (final), 9/50 (before fixes)
- gold_error_rate_mentions: 6/287 (final), 15/481 (before fixes)

## Reproduce

```
python tools/corpus/build_boamp.py --cache DIR --per-month 125
python tools/corpus/evaluate_real.py --cache DIR --corpora boamp_fr
```

No document text or gold value is stored in this report; the corpus stays in the local cache.
