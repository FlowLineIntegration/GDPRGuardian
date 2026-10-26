# GDPR Guardian on real corpus `judilibre_fr` (2026-10-25)

- Corpus: Judilibre (Cour de cassation, cours d'appel, tribunaux judiciaires), negative control. Language `fr`. Licence: Licence Ouverte 2.0 (etalab-2.0). Source: https://huggingface.co/datasets/antoinejeannot/jurisprudence (antoinejeannot/jurisprudence@8019db1080cf6dc8a34d73ee44d704a8e90b558e (mirror of the Judilibre API)).
- Real text: yes (decisions pseudonymised by the courts before publication).
- Gold: none: parties are already replaced by '[X]'-style placeholders; detections are reviewed by hand.
- Engine: gdprguardian 1.0.0 (native core: True), `Anonymizer(countries="FR", profile="standard")`.
- Documents: 300/300 evaluated, engine errors: 0; 3,296,812 characters; throughput 5023035 chars/s (one thread, shared machine).
- Personal gold mentions: 0; kept-by-policy mentions: 0.

## Negative control (no gold)

| indicator | value [95% CI] |
|---|---|
| masked spans per 10,000 characters | 12.51 [11.20–14.09] |
| documents with at least one masked span | 100.0% [100.0%–100.0%] |
| masked spans | 4,124 |

Masked labels: PERSON 3630, ORG 227, BIRTH_DATE 156, ADDRESS 90, PHONE 9, IP 4, EMAIL 4, ID 2, PLATE 1, IBAN 1


## Manual review of a sample

- No gold: 120 masked spans drawn at random over the 300 decisions (4,153 masked spans in all; spotcheck_real.py --detections --detection-contexts 120, seed 20261025) and classified by hand with their context.
- residual_personal_data_correctly_masked: 82/120 (68.3%): 78 names of magistrates, court clerks and lawyers (left in clear by the court pseudonymisation), 3 birth dates of parties written 'né(e) le <date>' next to a pseudonymised name, 1 residence name next to a street address
- false_positives: 38/120 (31.7%, 95% Wilson interval 24.0-40.4%): 27 company, brand or law-firm names masked as a person or organisation (international brands, insurers, SCI and SAS names, 3 law firms), 6 capitalised common words taken for a name ('doit' twice, 'Faisant', 'Premier', 'Constitué', 'de Chambre'), 2 restaurant name mentions, 1 grape variety, 1 hiring date taken for a birth date, 1 legal reference ('R. 3211-18, R. 3211') masked as an address. Recounted by an independent reviewer: same totals (82/38); two law-firm names made of lawyers' surnames are counted here as false positives, while SCP names are counted as residual data, a debatable boundary worth +-2 spans
- placeholders: No court placeholder ('[E]', '[Adresse 1]', '[Localité 4]') was masked in the 120 drawn spans

## Reproduce

```
python tools/corpus/fetch_real.py --cache DIR --only judilibre_fr
python tools/corpus/evaluate_real.py --cache DIR --corpora judilibre_fr --tag rules2
```

No document text or gold value is stored in this report; the corpus stays in the local cache.
