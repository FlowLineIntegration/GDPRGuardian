# Évaluation Gardien RGPD – corpus synthétique / GDPR Guardian synthetic corpus evaluation

Généré le 2026-10-24T19:29:12+00:00 · Gardien RGPD 0.1.0 · Python 3.12.11 · Faker 40.43.0 · graine/seed 20261024
Corpus de base : 540 documents (310,289 caractères), corpus muté : 5652 documents (47 opérateurs). Données entièrement synthétiques ; à ne pas confondre avec une mesure sur documents réels.
Packs chargés : BE 2026.10.0, CH 2026.10.0, DE 2026.10.0, ES 2026.10.0, FR 2026.10.0, INTL 2026.10.0, IT 2026.10.0, LU 2026.10.0, MC 2026.10.0, NL 2026.10.0, PT 2026.10.0.

**Attention** : 58 document(s) du corpus `base` font lever une exception au moteur (profil fast) : {'AttributeError': 58} ; exclus des mesures.

**Attention** : 596 document(s) du corpus `mutated` font lever une exception au moteur (profil fast) : {'AttributeError': 596} ; exclus des mesures.

**Attention** : 58 document(s) du corpus `base` font lever une exception au moteur (profil standard) : {'AttributeError': 58} ; exclus des mesures.

**Attention** : 596 document(s) du corpus `mutated` font lever une exception au moteur (profil standard) : {'AttributeError': 596} ; exclus des mesures.

**Attention** : 58 document(s) du corpus `base` font lever une exception au moteur (profil strict) : {'AttributeError': 58} ; exclus des mesures.

**Attention** : 596 document(s) du corpus `mutated` font lever une exception au moteur (profil strict) : {'AttributeError': 596} ; exclus des mesures.

## Détecteurs déclarés / declared detectors

| Pack | Détecteur | Zones émises (corpus de base, standard) | État |
|---|---|---|---|
| FR | FR_NAMES | 2057 | actif |
| FR | FR_ADDRESS | 340 | actif |
| FR | ORGANIZATIONS | 43 | actif |
| INTL | EMAIL | 425 | actif |
| INTL | INTL_IBAN | 256 | actif |
| INTL | INTL_MRZ | 0 | inactif (aucune zone) |
| INTL | INTL_PHONE | 0 | inactif (aucune zone) |

## Indicateurs principaux (corpus de base) / headline metrics

Rappel et précision au caractère alphanumérique ; IC bootstrap 95 % sur les documents.

| Indicateur | fast | standard | strict |
|---|---|---|---|
| Rappel identifiants directs | 99.2 % [98.9–99.4] | 99.2 % [98.9–99.4] | 99.2 % [98.9–99.4] |
| … dont identifiants structurés (motifs, clés) | 98.9 % [98.4–99.3] | 98.9 % [98.4–99.3] | 98.9 % [98.4–99.3] |
| Rappel direct + quasi | 92.6 % [91.7–93.5] | 92.6 % [91.7–93.5] | 94.2 % [93.4–95.1] |
| Précision | 96.6 % [96.0–97.2] | 96.6 % [96.0–97.2] | 94.1 % [93.4–94.8] |
| F2 | 93.4 % [92.7–94.1] | 93.4 % [92.7–94.1] | 94.2 % [93.6–94.8] |
| Rappel entités directes (TAB) | 98.4 % [97.9–98.8] | 98.4 % [97.9–98.8] | 98.4 % [97.9–98.8] |
| Documents avec fuite (stricte, tout direct) | 11.8 % [8.9–14.7] | 11.8 % [8.9–14.7] | 11.8 % [8.9–14.7] |
| Documents avec fuite d'identifiant structuré | 4.6 % [2.9–6.4] | 4.6 % [2.9–6.4] | 4.6 % [2.9–6.4] |
| Sur-masquage texte neutre | 1.4 % [1.1–1.7] | 1.4 % [1.1–1.7] | 1.6 % [1.3–1.9] |
| Leurres masqués à tort | 4.0 % [3.1–5.0] | 4.0 % [3.1–5.0] | 11.2 % [10.0–12.6] |
| Fuite souple (≥ 4 car. consécutifs) | 9.8 % | 9.8 % | 9.8 % |
| Fuite littérale (valeur retrouvée) | 4.6 % | 4.6 % | 4.6 % |
| Débit (car./s, indicatif) | 277,102 | 275,989 | 263,002 |
| Documents en échec (exception du moteur) | 58 | 58 | 58 |

## Par type d'identifiant (profil standard) / per label

| Libellé | Type | Mentions | Rappel mentions [IC 95 %] | Rappel car. | Précision | F2 | Docs avec fuite | Rappel (fast / standard / strict) |
|---|---|---|---|---|---|---|---|---|
| ADDRESS | DIRECT | 340 | 98.2 % [96.2–99.2] | 99.6 % | 100.0 % | 99.7 % | 2.0 % | 98.2 % / 98.2 % / 98.2 % |
| CAF | DIRECT | 6 | 100.0 % [61.0–100.0] | 100.0 % | 100.0 % | 100.0 % | 0.0 % | 100.0 % / 100.0 % / 100.0 % |
| CARD | DIRECT | 33 | 100.0 % [89.6–100.0] | 100.0 % | 78.4 % | 94.8 % | 0.0 % | 100.0 % / 100.0 % / 100.0 % |
| EMAIL | DIRECT | 425 | 100.0 % [99.1–100.0] | 100.0 % | 100.0 % | 100.0 % | 0.0 % | 100.0 % / 100.0 % / 100.0 % |
| FRANCE_TRAVAIL | DIRECT | 6 | 100.0 % [61.0–100.0] | 100.0 % | 100.0 % | 100.0 % | 0.0 % | 100.0 % / 100.0 % / 100.0 % |
| IBAN | DIRECT | 256 | 100.0 % [98.5–100.0] | 100.0 % | 100.0 % | 100.0 % | 0.0 % | 100.0 % / 100.0 % / 100.0 % |
| ID_CARD | DIRECT | 39 | 100.0 % [91.0–100.0] | 100.0 % | 100.0 % | 100.0 % | 0.0 % | 100.0 % / 100.0 % / 100.0 % |
| IP | DIRECT | 15 | 100.0 % [79.6–100.0] | 100.0 % | 100.0 % | 100.0 % | 0.0 % | 100.0 % / 100.0 % / 100.0 % |
| NIR | DIRECT | 257 | 100.0 % [98.5–100.0] | 100.0 % | 100.0 % | 100.0 % | 0.0 % | 100.0 % / 100.0 % / 100.0 % |
| PASSPORT | DIRECT | 44 | 100.0 % [92.0–100.0] | 100.0 % | 100.0 % | 100.0 % | 0.0 % | 100.0 % / 100.0 % / 100.0 % |
| PERSON | DIRECT | 1920 | 98.5 % [97.8–98.9] | 99.4 % | 92.8 % | 98.0 % | 6.0 % | 98.5 % / 98.5 % / 98.5 % |
| PHONE | DIRECT | 583 | 97.9 % [96.4–98.8] | 98.0 % | 100.0 % | 98.4 % | 3.4 % | 97.9 % / 97.9 % / 97.9 % |
| PLATE | DIRECT | 38 | 100.0 % [90.8–100.0] | 100.0 % | 100.0 % | 100.0 % | 0.0 % | 100.0 % / 100.0 % / 100.0 % |
| RIB | DIRECT | 39 | 100.0 % [91.0–100.0] | 100.0 % | 100.0 % | 100.0 % | 0.0 % | 100.0 % / 100.0 % / 100.0 % |
| RIB_SPLIT | DIRECT | 40 | 0.0 % [0.0–8.8] | 0.0 % | – | – | 100.0 % | 0.0 % / 0.0 % / 2.5 % |
| RPPS | DIRECT | 55 | 100.0 % [93.5–100.0] | 100.0 % | 100.0 % | 100.0 % | 0.0 % | 100.0 % / 100.0 % / 100.0 % |
| SIREN | DIRECT | 6 | 100.0 % [61.0–100.0] | 100.0 % | 31.6 % | 69.8 % | 0.0 % | 100.0 % / 100.0 % / 100.0 % |
| SIRET | DIRECT | 29 | 100.0 % [88.3–100.0] | 100.0 % | 70.6 % | 92.3 % | 0.0 % | 100.0 % / 100.0 % / 100.0 % |
| TAX_ID | DIRECT | 8 | 100.0 % [67.6–100.0] | 100.0 % | 100.0 % | 100.0 % | 0.0 % | 100.0 % / 100.0 % / 100.0 % |
| VAT | DIRECT | 16 | 100.0 % [80.6–100.0] | 100.0 % | 100.0 % | 100.0 % | 0.0 % | 100.0 % / 100.0 % / 100.0 % |
| BIRTH_DATE | QUASI | 313 | 60.4 % [54.9–65.6] | 63.8 % | 91.6 % | 67.9 % | 0.0 % | 60.4 % / 60.4 % / 60.4 % |
| ID | QUASI | 249 | 44.6 % [38.5–50.8] | 55.3 % | 100.0 % | 60.7 % | 0.0 % | 44.6 % / 44.6 % / 44.6 % |
| LOCATION | QUASI | 164 | 0.6 % [0.1–3.4] | 1.2 % | – | – | 0.0 % | 0.6 % / 0.6 % / 0.6 % |
| ORG | QUASI | 155 | 29.0 % [22.5–36.6] | 31.3 % | 86.5 % | 35.9 % | 0.0 % | 29.0 % / 29.0 % / 76.1 % |

## Leurres (ne doivent pas être masqués) / decoys

| Leurre | Occurrences | masqués (fast) | masqués (standard) | masqués (strict) |
|---|---|---|---|---|
| AMOUNT | 519 | 0.0 % | 0.0 % | 0.0 % |
| BIC | 26 | 0.0 % | 0.0 % | 0.0 % |
| CASE_NUMBER | 29 | 0.0 % | 0.0 % | 0.0 % |
| COMPANY_ID | 119 | 26.1 % | 26.1 % | 100.0 % |
| EVENT_DATE | 754 | 2.7 % | 2.7 % | 2.7 % |
| FACILITY_ID | 30 | 0.0 % | 0.0 % | 100.0 % |
| INVOICE_NUMBER | 38 | 0.0 % | 0.0 % | 0.0 % |
| LEGAL_REF | 132 | 18.2 % | 18.2 % | 18.2 % |
| ORDER_NUMBER | 155 | 0.0 % | 0.0 % | 16.1 % |
| PRODUCT_REF | 54 | 7.4 % | 7.4 % | 7.4 % |
| TICKET | 56 | 0.0 % | 0.0 % | 0.0 % |
| VERSION | 68 | 0.0 % | 0.0 % | 0.0 % |

## Entités (TAB : toutes les mentions masquées) / entity recall

| Type | Entités | fast | standard | strict |
|---|---|---|---|---|
| DIRECT | 3458 | 98.4 % | 98.4 % | 98.4 % |
| QUASI | 861 | 37.9 % | 37.9 % | 46.3 % |

## Fuites par type de document (profil standard) / leaks per document kind

| Type de document | Documents | Fuite (tout direct) | Fuite (identifiant structuré) |
|---|---|---|---|
| contract | 51 | 2.0 % | 0.0 % |
| email | 56 | 10.7 % | 1.8 % |
| hr_record | 57 | 1.8 % | 0.0 % |
| invoice | 52 | 0.0 % | 0.0 % |
| letter | 41 | 29.3 % | 24.4 % |
| medical | 55 | 1.8 % | 0.0 % |
| minutes | 59 | 16.9 % | 3.4 % |
| table | 55 | 12.7 % | 12.7 % |
| ticket | 56 | 33.9 % | 3.6 % |

## Équipe rouge : survie aux mutations / red-team survival per operator

Survie = part des mentions masquées sans mutation qui le restent après mutation (n = ces mentions). « Structurés » : identifiants à motif ou à clé ; « textuels » : personnes, adresses, lieux, organisations (heuristiques, NER). Les libellés les plus touchés sont dans le JSON.

| Opérateur | Famille | n structurés | survie fast | survie standard | survie strict | n textuels | survie fast | survie standard | survie strict |
|---|---|---|---|---|---|---|---|---|---|
| nbsp | unicode-space | 248 | 100.0 % | 100.0 % | 100.0 % | 408 | 100.0 % | 100.0 % | 100.0 % |
| narrow_nbsp | unicode-space | 248 | 100.0 % | 100.0 % | 100.0 % | 408 | 100.0 % | 100.0 % | 100.0 % |
| thin_space | unicode-space | 248 | 100.0 % | 100.0 % | 100.0 % | 408 | 100.0 % | 100.0 % | 100.0 % |
| figure_space | unicode-space | 248 | 100.0 % | 100.0 % | 100.0 % | 408 | 100.0 % | 100.0 % | 100.0 % |
| ideographic_space | unicode-space | 248 | 100.0 % | 100.0 % | 100.0 % | 408 | 100.0 % | 100.0 % | 100.0 % |
| zero_width_space | invisible | 533 | 100.0 % | 100.0 % | 100.0 % | 568 | 100.0 % | 100.0 % | 100.0 % |
| zero_width_joiner | invisible | 533 | 100.0 % | 100.0 % | 100.0 % | 568 | 100.0 % | 100.0 % | 100.0 % |
| word_joiner | invisible | 533 | 100.0 % | 100.0 % | 100.0 % | 568 | 100.0 % | 100.0 % | 100.0 % |
| bom | invisible | 533 | 100.0 % | 100.0 % | 100.0 % | 568 | 100.0 % | 100.0 % | 100.0 % |
| soft_hyphen | invisible | 533 | 100.0 % | 100.0 % | 100.0 % | 568 | 100.0 % | 100.0 % | 100.0 % |
| bidi_mark | invisible | 533 | 100.0 % | 100.0 % | 100.0 % | 568 | 100.0 % | 100.0 % | 100.0 % |
| bidi_isolate | invisible | 533 | 100.0 % | 100.0 % | 100.0 % | 568 | 100.0 % | 100.0 % | 100.0 % |
| tag_chars | invisible | 533 | 100.0 % | 100.0 % | 100.0 % | 568 | 100.0 % | 100.0 % | 100.0 % |
| variation_selector | invisible | 492 | 0.0 % | 0.0 % | 0.0 % | 521 | 0.4 % | 0.4 % | 0.4 % |
| grapheme_joiner | invisible | 487 | 0.0 % | 0.0 % | 0.0 % | 525 | 0.2 % | 0.2 % | 0.2 % |
| fullwidth | digits | 489 | 100.0 % | 100.0 % | 100.0 % | 568 | 100.0 % | 100.0 % | 100.0 % |
| math_bold | digits | 489 | 55.6 % | 55.6 % | 55.6 % | 568 | 15.8 % | 15.8 % | 15.4 % |
| arabic_indic | digits | 412 | 100.0 % | 100.0 % | 100.0 % | 80 | 100.0 % | 100.0 % | 100.0 % |
| devanagari | digits | 412 | 100.0 % | 100.0 % | 100.0 % | 80 | 100.0 % | 100.0 % | 100.0 % |
| superscript | digits | 412 | 6.8 % | 6.8 % | 6.8 % | 80 | 0.0 % | 0.0 % | 0.0 % |
| cyrillic | homoglyph | 114 | 100.0 % | 100.0 % | 100.0 % | 567 | 86.1 % | 86.1 % | 85.4 % |
| greek | homoglyph | 104 | 100.0 % | 100.0 % | 100.0 % | 505 | 100.0 % | 100.0 % | 100.0 % |
| nb_hyphen | unicode-dash | 56 | 100.0 % | 100.0 % | 100.0 % | 27 | 100.0 % | 100.0 % | 100.0 % |
| en_dash_groups | unicode-dash | 382 | 84.0 % | 84.0 % | 84.0 % | 0 | – | – | – |
| dots | ascii-separator | 370 | 63.0 % | 63.0 % | 63.2 % | 0 | – | – | – |
| hyphens | ascii-separator | 366 | 82.0 % | 82.0 % | 82.0 % | 0 | – | – | – |
| slashes | ascii-separator | 382 | 6.0 % | 6.0 % | 6.0 % | 0 | – | – | – |
| double_space | ascii-separator | 382 | 7.3 % | 7.3 % | 7.3 % | 0 | – | – | – |
| compact | ascii-separator | 276 | 99.3 % | 99.3 % | 100.0 % | 0 | – | – | – |
| regroup | ascii-separator | 380 | 42.1 % | 42.1 % | 41.6 % | 0 | – | – | – |
| line_break | layout | 453 | 5.1 % | 5.1 % | 5.1 % | 467 | 49.3 % | 49.3 % | 48.1 % |
| crlf | layout | 468 | 3.2 % | 3.2 % | 3.2 % | 458 | 43.4 % | 43.4 % | 42.2 % |
| tab | layout | 248 | 0.0 % | 0.0 % | 0.0 % | 408 | 99.0 % | 99.0 % | 98.8 % |
| ocr | ocr | 375 | 6.7 % | 6.7 % | 7.5 % | 0 | – | – | – |
| upper | case | 105 | 100.0 % | 100.0 % | 100.0 % | 521 | 95.0 % | 95.0 % | 95.2 % |
| lower | case | 0 | – | – | – | 568 | 28.2 % | 28.2 % | 27.4 % |
| surname_first | case | 0 | – | – | – | 239 | 97.1 % | 97.1 % | 97.1 % |
| strip_accents | accents | 0 | – | – | – | 153 | 100.0 % | 100.0 % | 100.0 % |
| nfd | accents | 0 | – | – | – | 131 | 8.4 % | 8.4 % | 9.5 % |
| at_brackets | email | 105 | 100.0 % | 100.0 % | 100.0 % | 0 | – | – | – |
| at_parens | email | 105 | 100.0 % | 100.0 % | 100.0 % | 0 | – | – | – |
| arobase | email | 105 | 100.0 % | 100.0 % | 100.0 % | 0 | – | – | – |
| at_entity | email | 105 | 0.0 % | 0.0 % | 0.0 % | 0 | – | – | – |
| at_percent | email | 105 | 0.0 % | 0.0 % | 0.0 % | 0 | – | – | – |
| at_fullwidth | email | 105 | 100.0 % | 100.0 % | 100.0 % | 0 | – | – | – |
| dot_brackets | email | 105 | 0.0 % | 0.0 % | 0.0 % | 0 | – | – | – |
| dot_point | email | 105 | 0.0 % | 0.0 % | 0.0 % | 0 | – | – | – |

## Confusions de libellé (profil standard) / label confusions

| Référence | Système | Mentions |
|---|---|---|
| PASSPORT | ID_CARD | 20 |
| ORG | PERSON | 12 |
| SIRET | CARD | 5 |
| LOCATION | PERSON | 1 |

## Masquages hors annotation (profil standard) / masks outside gold PII

| Libellé système | Source | Zones |
|---|---|---|
| PERSON | FR_NAMES | 156 |
| BIRTH_DATE | BIRTH_DATE | 20 |
| SIREN | FR_SIREN | 13 |
| CARD | CARD | 12 |
| SIRET | FR_SIRET | 10 |
| ORG | ORGANIZATIONS | 1 |

## Exemples (valeurs synthétiques, profil standard) / examples (synthetic values)

| Cas | Libellé | Valeur | Détail |
|---|---|---|---|
| faux négatif | BIRTH_DATE | `23/11/1989` | – |
| faux négatif | BIRTH_DATE | `15/01/2004` | – |
| faux négatif | BIRTH_DATE | `12/02/1987` | – |
| faux négatif | ID | `E73162` | – |
| faux négatif | ID | `E93416` | – |
| faux négatif | ID | `E49670` | – |
| faux négatif | PHONE | `0690 21 78 59` | – |
| faux négatif | PHONE | `0692 12 62 29` | – |
| faux négatif | PHONE | `0697 31 54 84` | – |
| faux négatif | RIB_SPLIT | `14445` | – |
| faux négatif | RIB_SPLIT | `63965` | – |
| faux négatif | RIB_SPLIT | `83286587466` | – |
| faux positif | BIRTH_DATE | `21/05/2020` | BIRTH_DATE |
| faux positif | BIRTH_DATE | `07/03/2021` | BIRTH_DATE |
| faux positif | BIRTH_DATE | `25/03/2022` | BIRTH_DATE |
| faux positif | CARD | `50044109200920` | CARD |
| faux positif | CARD | `46853948103187` | CARD |
| faux positif | CARD | `64002054100176` | CARD |
| faux positif | ORG | `Agence de Le Mans` | ORGANIZATIONS |
| faux positif | PERSON | `B du CGI` | FR_NAMES |
| faux positif | PERSON | `FACTURE N` | FR_NAMES |
| faux positif | PERSON | `Her French` | FR_NAMES |
