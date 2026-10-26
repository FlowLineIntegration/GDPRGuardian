# Banc de performance Gardien RGPD / GDPR Guardian benchmark

2026-10-26T00:55:09+00:00 · Python 3.12.11 · Windows-11-10.0.26300-SP0 · AMD64 Family 25 Model 80 Stepping 0, AuthenticAMD · 16 cœurs logiques · Gardien RGPD 1.0.0 · GC actif : True
Pays : FR ; packs chargés : INTL 2026.10.0, FR 2026.10.0.

Un seul cœur (appels séquentiels). Débits en millions de caractères par seconde (M car./s).

## Par type de document / per document kind

| Type | Taille moy. (car.) | standard p50 / p95 (ms) | standard M car./s |
|---|---|---|---|
| email | 445 | 0.22 / 0.34 | 1.93 M |
| minutes | 810 | 0.20 / 0.27 | 3.82 M |
| hr_record | 545 | 0.22 / 0.33 | 2.37 M |
| contract | 780 | 0.21 / 0.30 | 3.54 M |
| invoice | 570 | 0.18 / 0.30 | 2.91 M |
| ticket | 491 | 0.15 / 0.28 | 3.06 M |
| medical | 532 | 0.18 / 0.27 | 2.82 M |
| table | 706 | 0.32 / 0.44 | 2.20 M |
| letter | 379 | 0.11 / 0.18 | 3.11 M |

## Par taille d'entrée / per input size

Débit à la médiane des échantillons ; entre parenthèses, au meilleur échantillon (borne basse peu sensible à la charge de la machine).

| Entrée | Caractères | standard médiane (ms) | standard M car./s |
|---|---|---|---|
| mixed_1k | 1,000 | 0.30 | 3.34 M (3.56 M) |
| mixed_10k | 10,000 | 2.20 | 4.54 M (4.92 M) |
| mixed_100k | 100,000 | 20.80 | 4.81 M (5.30 M) |
| mixed_1m | 1,000,000 | 182.94 | 5.47 M (5.75 M) |
| pii_free_100k | 100,000 | 6.53 | 15.32 M (16.40 M) |
| pii_dense_100k | 100,000 | 25.53 | 3.92 M (4.25 M) |

## Répartition du temps (plus grosse entrée, ms) / stage breakdown

| Étape | standard |
|---|---|
| prepare | 12.4 |
| native | 52.8 |
| pack:INTL | 10.2 |
| pack:FR | 66.7 |
| resolve | 55.1 |
| total | 202.8 |

## Démarrage à froid (processus neuf, médiane) / cold start

| Profil | import (ms) | construction (ms) | premier appel (ms) | total (ms) |
|---|---|---|---|---|
| standard | 90.0 | 555.3 | 0.9 | 646.2 |

## Mémoire (entrée de 1 M car.) / memory

| Profil | pic tracemalloc (Mo) | octets alloués / car. | pic RSS avant → après (Mo) |
|---|---|---|---|
| standard | 2.7 | 3 | 151 → 173 |

## Motifs les plus coûteux (balayage brut, 100 k car., profil standard) / costliest patterns

Coût d'un balayage complet ; « sauté » : le préfiltre du moteur évite ce motif sur ce texte (les niveaux B/C sont aussi sautés sans mot de contexte).

| Pack | Motif | Niveau | Préfiltre | ms | Correspondances |
|---|---|---|---|---|---|
| INTL | EMAIL_OBFUSCATED | A | sauté | 20.6 | 0 |
| INTL | BIRTH_DATE_WORDS_EN | C | satisfait | 18.5 | 0 |
| INTL | URL_PERSONAL | A | sauté | 18.4 | 0 |
| INTL | IPV6 | A | satisfait | 7.4 | 0 |
| FR | FR_CONTEXTUAL_ID | A | aucun | 5.6 | 12 |
| INTL | SECRET_PASSWORD | A | satisfait | 5.2 | 0 |
| FR | FR_INE | C | satisfait | 5.1 | 114 |
| INTL | BIRTH_DATE | C | satisfait | 4.6 | 133 |
| INTL | MAC | A | aucun | 3.9 | 0 |
| FR | FR_BIRTH_DATE_WORDS | C | satisfait | 3.6 | 291 |
| INTL | IPV4 | A | satisfait | 3.5 | 11 |
| FR | FR_PHONE_OVERSEAS | A | satisfait | 3.3 | 4 |

## Entrées adverses (200,000 car., profil standard) / adversarial inputs

Alerte si moins de 100,000 car./s, ou si l'exposant de croissance (temps à 50,000 puis 200,000 car.) dépasse 1.3 (1 = linéaire, 2 = quadratique).

| Entrée | Durée (ms) | M car./s | Exposant | Verdict |
|---|---|---|---|---|
| digits_run | 10 | 20.01 M | 0.99 | ok |
| spaced_digits | 89 | 2.25 M | 1.02 | ok |
| digit_pairs | 20 | 9.79 M | 1.03 | ok |
| dotted_digits | 103 | 1.95 M | 1.02 | ok |
| dashed_digits | 93 | 2.15 M | 0.90 | ok |
| at_signs | 50 | 3.98 M | 0.95 | ok |
| at_words | 34 | 5.95 M | 1.01 | ok |
| email_like | 4 | 47.70 M | 1.09 | ok |
| plus_prefixes | 11 | 18.02 M | 1.10 | ok |
| uppercase_run | 6 | 31.26 M | 1.12 | ok |
| uppercase_words | 32 | 6.23 M | 1.15 | ok |
| capitalized_words | 35 | 5.68 M | 1.08 | ok |
| honorific_names | 57 | 3.52 M | 1.13 | ok |
| capital_lines | 87 | 2.29 M | 1.10 | ok |
| colon_labels | 40 | 4.99 M | 0.99 | ok |
| street_storm | 41 | 4.85 M | 1.16 | ok |
| address_lines | 43 | 4.61 M | 1.07 | ok |
| address_list | 31 | 6.53 M | 1.09 | ok |
| postcode_storm | 82 | 2.43 M | 1.05 | ok |
| legal_forms | 43 | 4.70 M | 1.03 | ok |
| sole_trader_ids | 20 | 9.94 M | 1.10 | ok |
| mrz_like | 7 | 30.38 M | 1.07 | ok |
| dashes | 12 | 16.60 M | 0.88 | ok |
| invisible | 6 | 34.36 M | 1.08 | ok |
| whitespace_run | 4 | 48.30 M | 1.13 | ok |
| newline_run | 5 | 38.90 M | 1.23 | ok |
| keyword_storm | 10 | 20.01 M | 1.13 | ok |
| single_token | 4 | 48.36 M | 1.12 | ok |
| hex_colons | 36 | 5.61 M | 1.07 | ok |
| brackets | 6 | 32.01 M | 1.05 | ok |
