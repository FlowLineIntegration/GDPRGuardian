# Banc de performance Gardien RGPD / GDPR Guardian benchmark

2026-10-25T15:59:55+00:00 · Python 3.12.11 · Windows-11-10.0.26300-SP0 · AMD64 Family 25 Model 80 Stepping 0, AuthenticAMD · 16 cœurs logiques · Gardien RGPD 1.0.0 · GC actif : True
Pays : FR ; packs chargés : INTL 2026.10.0, FR 2026.10.0.

Un seul cœur (appels séquentiels). Débits en millions de caractères par seconde (M car./s).

## Par type de document / per document kind

| Type | Taille moy. (car.) | standard p50 / p95 (ms) | standard M car./s |
|---|---|---|---|
| email | 445 | 0.18 / 0.27 | 2.40 M |
| minutes | 810 | 0.19 / 0.25 | 4.14 M |
| hr_record | 545 | 0.19 / 0.28 | 2.73 M |
| contract | 780 | 0.21 / 0.31 | 3.70 M |
| invoice | 570 | 0.17 / 0.29 | 3.13 M |
| ticket | 491 | 0.15 / 0.24 | 3.04 M |
| medical | 532 | 0.16 / 0.28 | 3.04 M |
| table | 706 | 0.33 / 0.54 | 2.08 M |
| letter | 379 | 0.13 / 0.22 | 2.68 M |

## Par taille d'entrée / per input size

Débit à la médiane des échantillons ; entre parenthèses, au meilleur échantillon (borne basse peu sensible à la charge de la machine).

| Entrée | Caractères | standard médiane (ms) | standard M car./s |
|---|---|---|---|
| mixed_1k | 1,000 | 0.29 | 3.45 M (3.81 M) |
| mixed_10k | 10,000 | 2.69 | 3.72 M (4.76 M) |
| mixed_100k | 100,000 | 20.29 | 4.93 M (5.52 M) |
| mixed_1m | 1,000,000 | 189.48 | 5.28 M (5.85 M) |
| pii_free_100k | 100,000 | 7.00 | 14.28 M (17.52 M) |
| pii_dense_100k | 100,000 | 30.35 | 3.30 M (3.92 M) |

## Répartition du temps (plus grosse entrée, ms) / stage breakdown

| Étape | standard |
|---|---|
| prepare | 16.7 |
| native | 64.2 |
| pack:INTL | 14.3 |
| pack:FR | 70.3 |
| resolve | 61.6 |
| total | 212.9 |

## Démarrage à froid (processus neuf, médiane) / cold start

| Profil | import (ms) | construction (ms) | premier appel (ms) | total (ms) |
|---|---|---|---|---|
| standard | 75.2 | 454.6 | 0.6 | 530.9 |

## Mémoire (entrée de 1 M car.) / memory

| Profil | pic tracemalloc (Mo) | octets alloués / car. | pic RSS avant → après (Mo) |
|---|---|---|---|
| standard | 2.7 | 3 | 145 → 158 |

## Motifs les plus coûteux (balayage brut, 100 k car., profil standard) / costliest patterns

Coût d'un balayage complet ; « sauté » : le préfiltre du moteur évite ce motif sur ce texte (les niveaux B/C sont aussi sautés sans mot de contexte).

| Pack | Motif | Niveau | Préfiltre | ms | Correspondances |
|---|---|---|---|---|---|
| INTL | URL_PERSONAL | A | sauté | 31.1 | 0 |
| INTL | EMAIL_OBFUSCATED | A | sauté | 28.7 | 0 |
| INTL | BIRTH_DATE_WORDS_EN | C | satisfait | 28.2 | 0 |
| INTL | IPV6 | A | satisfait | 10.1 | 0 |
| INTL | SECRET_PASSWORD | A | satisfait | 8.2 | 0 |
| FR | FR_PHONE_OVERSEAS | A | satisfait | 6.4 | 4 |
| INTL | BIRTH_DATE | C | satisfait | 6.3 | 133 |
| FR | FR_BIRTH_DATE_WORDS | C | satisfait | 6.2 | 291 |
| FR | FR_CONTEXTUAL_ID | A | aucun | 6.0 | 12 |
| INTL | MAC | A | aucun | 5.8 | 0 |
| INTL | IPV4 | A | satisfait | 5.6 | 11 |
| FR | FR_INE | C | satisfait | 5.4 | 114 |

## Entrées adverses (200,000 car., profil standard) / adversarial inputs

Alerte si moins de 100,000 car./s, ou si l'exposant de croissance (temps à 50,000 puis 200,000 car.) dépasse 1.3 (1 = linéaire, 2 = quadratique).

| Entrée | Durée (ms) | M car./s | Exposant | Verdict |
|---|---|---|---|---|
| digits_run | 10 | 20.72 M | 0.92 | ok |
| spaced_digits | 85 | 2.35 M | 0.97 | ok |
| digit_pairs | 20 | 9.94 M | 1.05 | ok |
| dotted_digits | 96 | 2.08 M | 0.96 | ok |
| dashed_digits | 91 | 2.20 M | 1.02 | ok |
| at_signs | 50 | 4.02 M | 1.02 | ok |
| at_words | 30 | 6.57 M | 0.97 | ok |
| email_like | 4 | 48.26 M | 1.16 | ok |
| plus_prefixes | 10 | 20.04 M | 1.05 | ok |
| uppercase_run | 5 | 36.41 M | 1.02 | ok |
| uppercase_words | 28 | 7.14 M | 1.07 | ok |
| capitalized_words | 32 | 6.21 M | 1.05 | ok |
| honorific_names | 52 | 3.86 M | 1.08 | ok |
| capital_lines | 82 | 2.43 M | 0.88 | ok |
| colon_labels | 42 | 4.73 M | 1.11 | ok |
| street_storm | 35 | 5.68 M | 0.97 | ok |
| address_lines | 50 | 3.97 M | 1.05 | ok |
| address_list | 28 | 7.02 M | 1.05 | ok |
| postcode_storm | 74 | 2.69 M | 1.05 | ok |
| legal_forms | 43 | 4.65 M | 1.07 | ok |
| sole_trader_ids | 21 | 9.32 M | 1.08 | ok |
| mrz_like | 6 | 32.83 M | 1.06 | ok |
| dashes | 12 | 16.97 M | 1.07 | ok |
| invisible | 7 | 28.56 M | 1.11 | ok |
| whitespace_run | 4 | 55.61 M | 1.10 | ok |
| newline_run | 5 | 43.72 M | 1.25 | ok |
| keyword_storm | 9 | 21.06 M | 1.11 | ok |
| single_token | 4 | 47.72 M | 0.98 | ok |
| hex_colons | 33 | 6.04 M | 1.03 | ok |
| brackets | 4 | 45.24 M | 1.11 | ok |
