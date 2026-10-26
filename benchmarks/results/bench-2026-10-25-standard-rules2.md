# Banc de performance Gardien RGPD / GDPR Guardian benchmark

2026-10-25T22:32:53+00:00 · Python 3.12.11 · Windows-11-10.0.26300-SP0 · AMD64 Family 25 Model 80 Stepping 0, AuthenticAMD · 16 cœurs logiques · Gardien RGPD 1.0.0 · GC actif : True
Pays : FR ; packs chargés : INTL 2026.10.0, FR 2026.10.0.

Un seul cœur (appels séquentiels). Débits en millions de caractères par seconde (M car./s).

## Par type de document / per document kind

| Type | Taille moy. (car.) | standard p50 / p95 (ms) | standard M car./s |
|---|---|---|---|
| email | 445 | 0.19 / 0.32 | 2.18 M |
| minutes | 810 | 0.26 / 0.57 | 2.80 M |
| hr_record | 545 | 0.24 / 0.39 | 2.25 M |
| contract | 780 | 0.21 / 0.37 | 3.27 M |
| invoice | 570 | 0.17 / 0.36 | 2.90 M |
| ticket | 491 | 0.17 / 0.25 | 2.84 M |
| medical | 532 | 0.18 / 0.45 | 2.39 M |
| table | 706 | 0.43 / 0.75 | 1.47 M |
| letter | 379 | 0.17 / 0.23 | 2.34 M |

## Par taille d'entrée / per input size

Débit à la médiane des échantillons ; entre parenthèses, au meilleur échantillon (borne basse peu sensible à la charge de la machine).

| Entrée | Caractères | standard médiane (ms) | standard M car./s |
|---|---|---|---|
| mixed_1k | 1,000 | 0.30 | 3.36 M (3.68 M) |
| mixed_10k | 10,000 | 3.18 | 3.14 M (4.01 M) |
| mixed_100k | 100,000 | 26.68 | 3.75 M (4.14 M) |
| mixed_1m | 1,000,000 | 244.58 | 4.09 M (4.40 M) |
| pii_free_100k | 100,000 | 8.58 | 11.66 M (12.39 M) |
| pii_dense_100k | 100,000 | 33.00 | 3.03 M (3.27 M) |

## Répartition du temps (plus grosse entrée, ms) / stage breakdown

| Étape | standard |
|---|---|
| prepare | 18.5 |
| native | 61.2 |
| pack:INTL | 12.9 |
| pack:FR | 87.0 |
| resolve | 65.5 |
| total | 240.9 |

## Démarrage à froid (processus neuf, médiane) / cold start

| Profil | import (ms) | construction (ms) | premier appel (ms) | total (ms) |
|---|---|---|---|---|
| standard | 93.0 | 515.2 | 0.7 | 606.3 |

## Mémoire (entrée de 1 M car.) / memory

| Profil | pic tracemalloc (Mo) | octets alloués / car. | pic RSS avant → après (Mo) |
|---|---|---|---|
| standard | 2.7 | 3 | 145 → 160 |

## Motifs les plus coûteux (balayage brut, 100 k car., profil standard) / costliest patterns

Coût d'un balayage complet ; « sauté » : le préfiltre du moteur évite ce motif sur ce texte (les niveaux B/C sont aussi sautés sans mot de contexte).

| Pack | Motif | Niveau | Préfiltre | ms | Correspondances |
|---|---|---|---|---|---|
| INTL | EMAIL_OBFUSCATED | A | sauté | 27.9 | 0 |
| INTL | BIRTH_DATE_WORDS_EN | C | satisfait | 27.0 | 0 |
| INTL | URL_PERSONAL | A | sauté | 25.6 | 0 |
| INTL | SECRET_PASSWORD | A | satisfait | 8.7 | 0 |
| INTL | IPV6 | A | satisfait | 8.3 | 0 |
| FR | FR_BIRTH_DATE_WORDS | C | satisfait | 7.1 | 291 |
| INTL | IPV4 | A | satisfait | 6.7 | 11 |
| INTL | MAC | A | aucun | 6.6 | 0 |
| FR | FR_CONTEXTUAL_ID | A | aucun | 6.3 | 12 |
| FR | FR_PHONE | A | satisfait | 6.3 | 118 |
| INTL | BIRTH_DATE | C | satisfait | 5.2 | 133 |
| FR | FR_INE | C | satisfait | 4.8 | 114 |

## Entrées adverses (200,000 car., profil standard) / adversarial inputs

Alerte si moins de 100,000 car./s, ou si l'exposant de croissance (temps à 50,000 puis 200,000 car.) dépasse 1.3 (1 = linéaire, 2 = quadratique).

| Entrée | Durée (ms) | M car./s | Exposant | Verdict |
|---|---|---|---|---|
| digits_run | 11 | 18.89 M | 1.10 | ok |
| spaced_digits | 98 | 2.04 M | 1.00 | ok |
| digit_pairs | 23 | 8.59 M | 1.04 | ok |
| dotted_digits | 111 | 1.80 M | 0.99 | ok |
| dashed_digits | 111 | 1.80 M | 0.92 | ok |
| at_signs | 54 | 3.69 M | 1.01 | ok |
| at_words | 36 | 5.62 M | 1.04 | ok |
| email_like | 5 | 36.89 M | 1.19 | ok |
| plus_prefixes | 13 | 14.96 M | 1.13 | ok |
| uppercase_run | 7 | 26.71 M | 0.88 | ok |
| uppercase_words | 33 | 6.02 M | 1.09 | ok |
| capitalized_words | 43 | 4.62 M | 1.19 | ok |
| honorific_names | 58 | 3.42 M | 0.99 | ok |
| capital_lines | 98 | 2.04 M | 1.03 | ok |
| colon_labels | 53 | 3.79 M | 1.05 | ok |
| street_storm | 41 | 4.90 M | 1.04 | ok |
| address_lines | 53 | 3.79 M | 1.15 | ok |
| address_list | 34 | 5.88 M | 1.19 | ok |
| postcode_storm | 98 | 2.04 M | 1.14 | ok |
| legal_forms | 59 | 3.40 M | 1.12 | ok |
| sole_trader_ids | 28 | 7.23 M | 1.25 | ok |
| mrz_like | 7 | 28.72 M | 1.00 | ok |
| dashes | 16 | 12.81 M | 1.10 | ok |
| invisible | 7 | 27.41 M | 1.11 | ok |
| whitespace_run | 4 | 44.76 M | 1.14 | ok |
| newline_run | 6 | 33.31 M | 1.25 | ok |
| keyword_storm | 11 | 18.49 M | 1.08 | ok |
| single_token | 6 | 32.03 M | 1.17 | ok |
| hex_colons | 49 | 4.12 M | 1.04 | ok |
| brackets | 5 | 39.14 M | 1.11 | ok |
