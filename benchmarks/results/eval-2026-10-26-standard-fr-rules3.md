# Évaluation Gardien RGPD – corpus synthétique / GDPR Guardian synthetic corpus evaluation

Généré le 2026-10-26T00:33:08+00:00 · Gardien RGPD 1.0.0 · Python 3.12.11 · Faker 40.43.0 · graine/seed 20261024
Corpus de base : 540 documents (310,289 caractères), corpus muté : 6192 documents (51 opérateurs). Données entièrement synthétiques ; à ne pas confondre avec une mesure sur documents réels.
Packs chargés : INTL 2026.10.0, FR 2026.10.0.

## Détecteurs déclarés / declared detectors

| Pack | Détecteur | Zones émises (corpus de base, standard) | État |
|---|---|---|---|
| INTL | EMAIL | 478 | actif |
| INTL | INTL_IBAN | 281 | actif |
| INTL | INTL_MRZ | 0 | inactif (aucune zone) |
| INTL | INTL_PHONE | 0 | inactif (aucune zone) |
| FR | FR_NAMES | 2086 | actif |
| FR | FR_ADDRESS | 402 | actif |
| FR | ORGANIZATIONS | 32 | actif |
| FR | FR_NIR_BIRTH_DATE | 206 | actif |

## Indicateurs principaux (corpus de base) / headline metrics

Rappel et précision au caractère alphanumérique ; IC bootstrap 95 % sur les documents.

| Indicateur | standard |
|---|---|
| Rappel identifiants directs | 99.2 % [99.0–99.5] |
| … dont identifiants structurés (motifs, clés) | 98.8 % [98.3–99.3] |
| Rappel direct + quasi | 93.5 % [92.7–94.3] |
| Précision | 98.8 % [98.6–99.1] |
| F2 | 94.5 % [93.9–95.2] |
| Rappel entités directes (TAB) | 98.8 % [98.5–99.1] |
| Documents avec fuite (stricte, tout direct) | 8.3 % [6.3–10.7] |
| Documents avec fuite d'identifiant structuré | 4.6 % [3.0–6.5] |
| Sur-masquage texte neutre | 0.1 % [0.0–0.1] |
| Leurres masqués à tort | 3.5 % [2.6–4.3] |
| Fuite souple (≥ 4 car. consécutifs) | 8.0 % |
| Fuite littérale (valeur retrouvée) | 5.2 % |
| Débit (car./s, indicatif) | 1,080,654 |
| Documents en échec (exception du moteur) | 0 |

## Par type d'identifiant (profil standard) / per label

| Libellé | Type | Mentions | Rappel mentions [IC 95 %] | Rappel car. | Précision | F2 | Docs avec fuite | Rappel (standard) |
|---|---|---|---|---|---|---|---|---|
| ADDRESS | DIRECT | 397 | 98.5 % [96.7–99.3] | 99.7 % | 100.0 % | 99.7 % | 1.7 % | 98.5 % |
| CAF | DIRECT | 7 | 100.0 % [64.6–100.0] | 100.0 % | 100.0 % | 100.0 % | 0.0 % | 100.0 % |
| CARD | DIRECT | 35 | 100.0 % [90.1–100.0] | 100.0 % | 97.7 % | 99.5 % | 0.0 % | 100.0 % |
| EMAIL | DIRECT | 478 | 100.0 % [99.2–100.0] | 100.0 % | 100.0 % | 100.0 % | 0.0 % | 100.0 % |
| FRANCE_TRAVAIL | DIRECT | 6 | 100.0 % [61.0–100.0] | 100.0 % | 100.0 % | 100.0 % | 0.0 % | 100.0 % |
| IBAN | DIRECT | 281 | 100.0 % [98.7–100.0] | 100.0 % | 100.0 % | 100.0 % | 0.0 % | 100.0 % |
| ID_CARD | DIRECT | 42 | 100.0 % [91.6–100.0] | 100.0 % | 100.0 % | 100.0 % | 0.0 % | 100.0 % |
| IP | DIRECT | 15 | 100.0 % [79.6–100.0] | 100.0 % | 100.0 % | 100.0 % | 0.0 % | 100.0 % |
| NIR | DIRECT | 273 | 100.0 % [98.6–100.0] | 100.0 % | 100.0 % | 100.0 % | 0.0 % | 100.0 % |
| PASSPORT | DIRECT | 47 | 100.0 % [92.4–100.0] | 100.0 % | 100.0 % | 100.0 % | 0.0 % | 100.0 % |
| PERSON | DIRECT | 2078 | 99.3 % [98.8–99.6] | 99.6 % | 99.6 % | 99.6 % | 2.8 % | 99.3 % |
| PHONE | DIRECT | 647 | 98.0 % [96.6–98.8] | 98.1 % | 100.0 % | 98.5 % | 3.4 % | 98.0 % |
| PLATE | DIRECT | 57 | 100.0 % [93.7–100.0] | 100.0 % | 100.0 % | 100.0 % | 0.0 % | 100.0 % |
| RIB | DIRECT | 42 | 100.0 % [91.6–100.0] | 100.0 % | 100.0 % | 100.0 % | 0.0 % | 100.0 % |
| RIB_SPLIT | DIRECT | 48 | 0.0 % [0.0–7.4] | 0.0 % | – | – | 100.0 % | 0.0 % |
| RPPS | DIRECT | 60 | 100.0 % [94.0–100.0] | 100.0 % | 100.0 % | 100.0 % | 0.0 % | 100.0 % |
| SIREN | DIRECT | 9 | 100.0 % [70.1–100.0] | 100.0 % | 37.5 % | 75.0 % | 0.0 % | 100.0 % |
| SIRET | DIRECT | 36 | 100.0 % [90.4–100.0] | 100.0 % | 63.2 % | 89.6 % | 0.0 % | 100.0 % |
| TAX_ID | DIRECT | 10 | 100.0 % [72.2–100.0] | 100.0 % | 100.0 % | 100.0 % | 0.0 % | 100.0 % |
| VAT | DIRECT | 21 | 100.0 % [84.5–100.0] | 100.0 % | 100.0 % | 100.0 % | 0.0 % | 100.0 % |
| BIRTH_DATE | QUASI | 337 | 100.0 % [98.9–100.0] | 100.0 % | 90.4 % | 97.9 % | 0.0 % | 100.0 % |
| ID | QUASI | 265 | 44.5 % [38.7–50.5] | 55.3 % | 100.0 % | 60.7 % | 0.0 % | 44.5 % |
| LOCATION | QUASI | 173 | 0.6 % [0.1–3.2] | 1.1 % | – | – | 0.0 % | 0.6 % |
| ORG | QUASI | 192 | 19.3 % [14.3–25.4] | 19.5 % | 97.1 % | 23.2 % | 0.0 % | 19.3 % |

## Leurres (ne doivent pas être masqués) / decoys

| Leurre | Occurrences | masqués (standard) |
|---|---|---|
| AMOUNT | 593 | 0.0 % |
| BIC | 33 | 0.0 % |
| CASE_NUMBER | 30 | 0.0 % |
| COMPANY_ID | 132 | 27.3 % |
| EVENT_DATE | 836 | 4.8 % |
| FACILITY_ID | 32 | 0.0 % |
| INVOICE_NUMBER | 45 | 0.0 % |
| LEGAL_REF | 159 | 0.0 % |
| ORDER_NUMBER | 170 | 0.0 % |
| PRODUCT_REF | 66 | 1.5 % |
| TICKET | 60 | 0.0 % |
| VERSION | 72 | 0.0 % |

## Entités (TAB : toutes les mentions masquées) / entity recall

| Type | Entités | standard |
|---|---|---|
| DIRECT | 3844 | 98.8 % |
| QUASI | 947 | 49.9 % |

## Fuites par type de document (profil standard) / leaks per document kind

| Type de document | Documents | Fuite (tout direct) | Fuite (identifiant structuré) |
|---|---|---|---|
| contract | 60 | 1.7 % | 0.0 % |
| email | 60 | 10.0 % | 3.3 % |
| hr_record | 60 | 3.3 % | 0.0 % |
| invoice | 60 | 0.0 % | 0.0 % |
| letter | 60 | 25.0 % | 20.0 % |
| medical | 60 | 1.7 % | 0.0 % |
| minutes | 60 | 8.3 % | 3.3 % |
| table | 60 | 11.7 % | 11.7 % |
| ticket | 60 | 13.3 % | 3.3 % |

## Équipe rouge : survie aux mutations / red-team survival per operator

Survie = part des mentions masquées sans mutation qui le restent après mutation (n = ces mentions). « Structurés » : identifiants à motif ou à clé ; « textuels » : personnes, adresses, lieux, organisations (heuristiques, NER). Les libellés les plus touchés sont dans le JSON.

| Opérateur | Famille | n structurés | survie standard | n textuels | survie standard |
|---|---|---|---|---|---|
| nbsp | unicode-space | 268 | 100.0 % | 455 | 100.0 % |
| narrow_nbsp | unicode-space | 268 | 100.0 % | 455 | 100.0 % |
| thin_space | unicode-space | 268 | 100.0 % | 455 | 100.0 % |
| figure_space | unicode-space | 268 | 100.0 % | 455 | 100.0 % |
| ideographic_space | unicode-space | 268 | 100.0 % | 455 | 100.0 % |
| zero_width_space | invisible | 616 | 100.0 % | 621 | 100.0 % |
| zero_width_joiner | invisible | 616 | 100.0 % | 621 | 100.0 % |
| word_joiner | invisible | 616 | 100.0 % | 621 | 100.0 % |
| bom | invisible | 616 | 100.0 % | 621 | 100.0 % |
| soft_hyphen | invisible | 616 | 100.0 % | 621 | 100.0 % |
| bidi_mark | invisible | 616 | 100.0 % | 621 | 100.0 % |
| bidi_isolate | invisible | 616 | 100.0 % | 621 | 100.0 % |
| tag_chars | invisible | 616 | 100.0 % | 621 | 100.0 % |
| variation_selector | invisible | 616 | 100.0 % | 621 | 100.0 % |
| grapheme_joiner | invisible | 616 | 100.0 % | 621 | 100.0 % |
| hangul_filler | invisible | 616 | 100.0 % | 621 | 100.0 % |
| fullwidth | digits | 538 | 100.0 % | 621 | 100.0 % |
| math_bold | digits | 538 | 55.2 % | 621 | 15.9 % |
| arabic_indic | digits | 456 | 100.0 % | 96 | 100.0 % |
| devanagari | digits | 456 | 100.0 % | 96 | 100.0 % |
| superscript | digits | 456 | 7.0 % | 96 | 0.0 % |
| cyrillic | homoglyph | 128 | 100.0 % | 620 | 92.7 % |
| greek | homoglyph | 116 | 100.0 % | 551 | 100.0 % |
| nb_hyphen | unicode-dash | 65 | 100.0 % | 28 | 100.0 % |
| en_dash_groups | unicode-dash | 422 | 83.6 % | 0 | – |
| dots | ascii-separator | 410 | 62.2 % | 0 | – |
| hyphens | ascii-separator | 401 | 81.0 % | 0 | – |
| slashes | ascii-separator | 422 | 5.9 % | 0 | – |
| double_space | ascii-separator | 422 | 7.1 % | 0 | – |
| compact | ascii-separator | 301 | 99.3 % | 0 | – |
| regroup | ascii-separator | 420 | 41.0 % | 0 | – |
| line_break | layout | 616 | 4.5 % | 579 | 59.4 % |
| crlf | layout | 616 | 3.9 % | 579 | 57.3 % |
| tab | layout | 268 | 0.0 % | 455 | 99.8 % |
| letter_spacing | layout | 536 | 2.2 % | 621 | 4.7 % |
| pdf_hyphenation | layout | 0 | – | 618 | 98.7 % |
| markdown_bold | layout | 616 | 100.0 % | 621 | 99.0 % |
| ocr | ocr | 414 | 24.2 % | 0 | – |
| upper | case | 114 | 100.0 % | 573 | 100.0 % |
| lower | case | 0 | – | 621 | 58.0 % |
| surname_first | case | 0 | – | 261 | 96.6 % |
| strip_accents | accents | 0 | – | 173 | 100.0 % |
| nfd | accents | 0 | – | 173 | 100.0 % |
| at_brackets | email | 114 | 100.0 % | 0 | – |
| at_parens | email | 114 | 100.0 % | 0 | – |
| arobase | email | 114 | 100.0 % | 0 | – |
| at_entity | email | 114 | 0.0 % | 0 | – |
| at_percent | email | 114 | 0.0 % | 0 | – |
| at_fullwidth | email | 114 | 100.0 % | 0 | – |
| dot_brackets | email | 114 | 0.0 % | 0 | – |
| dot_point | email | 114 | 0.0 % | 0 | – |

## Confusions de libellé (profil standard) / label confusions

| Référence | Système | Mentions |
|---|---|---|
| PASSPORT | ID_CARD | 20 |
| ORG | PERSON | 13 |
| LOCATION | PERSON | 1 |

## Masquages hors annotation (profil standard) / masks outside gold PII

| Libellé système | Source | Zones |
|---|---|---|
| BIRTH_DATE | BIRTH_DATE | 40 |
| PERSON | FR_NAMES | 24 |
| SIRET | FR_SIRET | 21 |
| SIREN | FR_SIREN | 15 |
| CARD | CARD | 1 |
| ORG | ORGANIZATIONS | 1 |

## Exemples (valeurs synthétiques, profil standard) / examples (synthetic values)

| Cas | Libellé | Valeur | Détail |
|---|---|---|---|
| faux négatif | ID | `E73162` | – |
| faux négatif | ID | `E93416` | – |
| faux négatif | ID | `E49670` | – |
| faux négatif | PHONE | `0690 21 78 59` | – |
| faux négatif | PHONE | `0692 12 62 29` | – |
| faux négatif | PHONE | `0697 31 54 84` | – |
| faux négatif | RIB_SPLIT | `14445` | – |
| faux négatif | RIB_SPLIT | `63965` | – |
| faux négatif | RIB_SPLIT | `83286587466` | – |
| faux positif | BIRTH_DATE | `20/05/2020` | BIRTH_DATE |
| faux positif | BIRTH_DATE | `21/05/2020` | BIRTH_DATE |
| faux positif | BIRTH_DATE | `26/08/2024` | BIRTH_DATE |
| faux positif | CARD | `3768508017551` | CARD |
| faux positif | ORG | `Agence de Le Mans` | ORGANIZATIONS |
| faux positif | PERSON | `Payé` | FR_NAMES |
| faux positif | PERSON | `Payé` | FR_NAMES |
| faux positif | PERSON | `Payé` | FR_NAMES |
| faux positif | SIREN | `681 438 990` | FR_SIREN |
| faux positif | SIREN | `136 631 694` | FR_SIREN |
