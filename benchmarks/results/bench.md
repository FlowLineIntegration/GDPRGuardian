# Banc de performance Gardien RGPD / GDPR Guardian benchmark

2026-10-24T19:18:00+00:00 · Python 3.12.11 · Windows-11-10.0.26300-SP0 · AMD64 Family 25 Model 80 Stepping 0, AuthenticAMD · 16 cœurs logiques · Gardien RGPD 0.1.0 · GC actif : True

Un seul cœur (appels séquentiels). Débits en millions de caractères par seconde (M car./s).

## Par type de document / per document kind

| Type | Taille moy. (car.) | fast p50 / p95 (ms) | standard p50 / p95 (ms) | strict p50 / p95 (ms) | fast M car./s | standard M car./s | strict M car./s |
|---|---|---|---|---|---|---|---|
| email | 445 | 0.48 / 0.77 | 0.50 / 0.88 | 0.55 / 0.92 | 0.91 M | 0.85 M | 0.79 M |
| minutes | 810 | 0.65 / 0.96 | 0.68 / 0.98 | 0.75 / 1.33 | 1.17 M | 1.13 M | 0.90 M |
| hr_record | 545 | 0.60 / 1.04 | 0.66 / 1.02 | 0.75 / 1.16 | 0.84 M | 0.76 M | 0.64 M |
| contract | 780 | 0.85 / 1.02 | 0.84 / 1.24 | 0.90 / 1.85 | 1.01 M | 0.98 M | 0.76 M |
| invoice | 570 | 0.55 / 0.94 | 0.55 / 0.87 | 0.89 / 1.68 | 0.88 M | 0.90 M | 0.63 M |
| ticket | 491 | 0.48 / 0.62 | 0.45 / 0.54 | 0.54 / 0.96 | 1.01 M | 1.08 M | 0.86 M |
| medical | 532 | 0.66 / 1.01 | 0.65 / 1.12 | 0.70 / 1.30 | 0.83 M | 0.81 M | 0.64 M |
| table | 706 | 0.78 / 1.35 | 0.86 / 1.42 | 1.04 / 2.31 | 0.83 M | 0.73 M | 0.62 M |
| letter | 379 | 0.44 / 0.78 | 0.50 / 0.75 | 0.68 / 0.90 | 0.76 M | 0.75 M | 0.60 M |

## Par taille d'entrée / per input size

Débit à la médiane des échantillons ; entre parenthèses, au meilleur échantillon (borne basse peu sensible à la charge de la machine).

| Entrée | Caractères | fast médiane (ms) | standard médiane (ms) | strict médiane (ms) | fast M car./s | standard M car./s | strict M car./s |
|---|---|---|---|---|---|---|---|
| mixed_1k | 1,000 | 0.98 | 1.02 | 1.38 | 1.02 M (1.06 M) | 0.98 M (1.07 M) | 0.72 M (0.96 M) |
| mixed_10k | 10,000 | 8.35 | 8.85 | 9.64 | 1.20 M (1.24 M) | 1.13 M (1.21 M) | 1.04 M (1.12 M) |
| mixed_100k | 100,000 | 97.07 | 108.29 | 127.45 | 1.03 M (1.09 M) | 0.92 M (1.05 M) | 0.78 M (0.94 M) |
| mixed_1m | 1,000,000 | 1314.68 | 1353.09 | 1664.46 | 0.76 M (0.88 M) | 0.74 M (0.83 M) | 0.60 M (0.71 M) |
| pii_free_100k | 100,000 | 29.91 | 35.10 | 36.90 | 3.34 M (3.38 M) | 2.85 M (3.39 M) | 2.71 M (3.23 M) |
| pii_dense_100k | 100,000 | 105.54 | 135.01 | 112.96 | 0.95 M (1.02 M) | 0.74 M (0.97 M) | 0.89 M (0.94 M) |

## Répartition du temps (plus grosse entrée, ms) / stage breakdown

| Étape | fast | standard | strict |
|---|---|---|---|
| prepare | 135.6 | 164.6 | 141.8 |
| pack:BE | 69.7 | 95.3 | 93.9 |
| pack:CH | 13.1 | 18.4 | 12.3 |
| pack:FR | 502.6 | 676.8 | 555.6 |
| pack:INTL | 386.4 | 552.2 | 467.0 |
| resolve | 22.7 | 40.5 | 27.4 |
| total | 1187.7 | 1660.6 | 1331.6 |

## Démarrage à froid (processus neuf, médiane) / cold start

| Profil | import (ms) | construction (ms) | premier appel (ms) | total (ms) |
|---|---|---|---|---|
| fast | 68.2 | 61.1 | 0.5 | 130.1 |
| standard | 71.6 | 289.4 | 0.7 | 361.9 |
| strict | 69.3 | 288.1 | 0.9 | 357.1 |

## Mémoire (entrée de 1 M car.) / memory

| Profil | pic tracemalloc (Mo) | octets alloués / car. | pic RSS avant → après (Mo) |
|---|---|---|---|
| fast | 9.6 | 10 | 41 → 53 |
| standard | erreur : AttributeError: 'NoneType' object has no attribute 'end' |  |  |
| strict | erreur : AttributeError: 'NoneType' object has no attribute 'end' |  |  |

## Motifs les plus coûteux (balayage brut, 100 k car., profil fast) / costliest patterns

Coût d'un balayage complet ; « sauté » : le préfiltre du moteur évite ce motif sur ce texte (les niveaux B/C sont aussi sautés sans mot de contexte).

| Pack | Motif | Niveau | Préfiltre | ms | Correspondances |
|---|---|---|---|---|---|
| INTL | URL_PERSONAL | A | sauté | 22.0 | 0 |
| INTL | EMAIL_OBFUSCATED | A | sauté | 21.5 | 0 |
| INTL | IPV6 | A | satisfait | 6.8 | 0 |
| INTL | IPV4 | A | satisfait | 5.8 | 11 |
| FR | FR_CONTEXTUAL_ID | A | aucun | 5.2 | 12 |
| INTL | SECRET_PASSWORD | A | satisfait | 5.0 | 0 |
| INTL | BIRTH_DATE | C | satisfait | 4.9 | 133 |
| FR | FR_INE | C | satisfait | 4.8 | 114 |
| FR | FR_PHONE_OVERSEAS | A | satisfait | 2.9 | 4 |
| FR | FR_PHONE | A | satisfait | 2.8 | 118 |
| INTL | MAC | A | aucun | 2.7 | 0 |
| FR | FR_AGDREF | C | satisfait | 2.3 | 139 |

## Entrées adverses (200,000 car., profil standard) / adversarial inputs

Alerte si moins de 100,000 car./s, ou si l'exposant de croissance (temps à 50,000 puis 200,000 car.) dépasse 1.3 (1 = linéaire, 2 = quadratique).

| Entrée | Durée (ms) | M car./s | Exposant | Verdict |
|---|---|---|---|---|
| digits_run | 650 | 0.31 M | 1.24 | ok |
| spaced_digits | 563 | 0.36 M | 0.90 | ok |
| digit_pairs | 296 | 0.68 M | 1.08 | ok |
| dotted_digits | 540 | 0.37 M | 0.86 | ok |
| dashed_digits | 545 | 0.37 M | 1.08 | ok |
| at_signs | 638 | 0.31 M | 1.03 | ok |
| at_words | 396 | 0.50 M | 1.11 | ok |
| email_like | 71 | 2.83 M | 0.99 | ok |
| plus_prefixes | 193 | 1.04 M | 0.97 | ok |
| uppercase_run | 49 | 4.09 M | 0.85 | ok |
| uppercase_words | 671 | 0.30 M | 1.34 | SUPER-LINÉAIRE |
| capitalized_words | 635 | 0.32 M | 0.96 | ok |
| mrz_like | 70 | 2.86 M | 0.98 | ok |
| dashes | 49 | 4.10 M | 0.94 | ok |
| invisible | 142 | 1.41 M | 1.07 | ok |
| keyword_storm | 80 | 2.50 M | 0.90 | ok |
| single_token | 40 | 5.02 M | 0.91 | ok |
| hex_colons | 273 | 0.73 M | 1.18 | ok |
| brackets | 61 | 3.25 M | 1.10 | ok |
