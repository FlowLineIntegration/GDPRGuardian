"""Définitions pré-enregistrées du protocole (1.0 : 25 octobre 2026 ; 1.1 : 26 octobre 2026) / pre-registered
protocol definitions.

Tout ce qui décide d'un chiffre publié est ici, figé AVANT la campagne et recopié dans docs/PROTOCOLE.md :
familles, graines, tailles, identifiants directs, définition de la fuite, formule de l'indice, pondération,
bootstrap, garde-fous. Changer une valeur = nouvelle version du protocole, datée, jamais une retouche silencieuse.
Everything that decides a published figure lives here, frozen BEFORE the campaign and copied into
docs/PROTOCOLE.md. Changing a value means a new, dated protocol version, never a silent edit.

Version 1.1 (26 octobre 2026, avant toute campagne 1.1) : un usage précis (textes que les organisations envoient à une
IA) et deux indices publiés, chacun avec son intervalle. « Documents normalisés » (l'indice principal, cible 95 % ou
plus) : moyenne à poids égal de quatre familles, synthétique FR, BODACC, BOAMP, ParlaMint-FR. « Documents difficiles » :
toute l'équipe rouge (51 opérateurs : formats du quotidien abîmés, déguisements volontaires, bruit d'OCR), chaque
document muté compte une fois, détail par groupe publié. Presse ancienne (OCR de mauvaise qualité), MAPA FR, autres
langues et témoin Judilibre publiés à part.
Version 1.1: one precise use case and two published indexes, each with its interval. "Normalised documents" (the
headline, target 95% or more): equal-weight mean of synthetic FR, BODACC, BOAMP, ParlaMint-FR. "Difficult documents":
the whole red team (51 operators: damaged everyday formats, deliberate obfuscations, OCR noise), every mutated document
counting once, per-group breakdown published. Old press, MAPA FR, other languages and the Judilibre control apart.

Version 1.2 (26 octobre 2026, avant toute mesure 1.2, mesurée sur le moteur 1.0.2 après sa sortie) : deux modes du
filtre déclarés par le plan, « fort » (le défaut du produit) et « essentiel » ; chaque document est noté une fois par
mode, le mode est envoyé au service. Par mode, deux chiffres : « anonymisation » (les deux indices 1.1, mêmes
définitions) et « codes utiles perdus » (leurres masqués, famille synthétique ; plus bas, mieux c'est). Le garde-fou des
leurres (≤ 10 %) ne vaut plus que pour le mode essentiel : le mode fort masque tous les codes par choix du produit, sa
perte est publiée sans garde-fou. Les autres garde-fous valent pour les deux modes. Le résultat 1.1 reste publié.
Version 1.2: two filter modes declared by the plan, "fort" (the product default) and "essentiel"; every document is
scored once per mode, the mode is sent to the service. Per mode, two numbers: "anonymisation" (the two 1.1 indexes,
same definitions) and "useful codes lost" (decoys masked, synthetic family; lower is better). The decoy guard (≤ 10%)
only applies to essentiel: fort masks every code by the product's choice, its loss is published without a guard. The
other guards apply to both modes. The 1.1 result stays published.
"""

from __future__ import annotations

from dataclasses import dataclass

PROTOCOL_VERSION = "1.2"
# Versions dont l'outil relit encore les points de reprise et les plans (un plan sans modes = 1.1) / versions whose
# checkpoints and plans the tool still reads (a plan without modes = 1.1).
SUPPORTED_VERSIONS: tuple[str, ...] = ("1.1", "1.2")
# Date d'écriture de cette version. L'enregistrement lui-même = la publication, avant le lancement, des empreintes de
# ce fichier, de docs/PROTOCOLE.md et du paquet (`python -m tools.protocol registration`), que chaque résultat recopie.
# Date this version was written. The registration itself = publishing, before the launch, the digests of this file,
# docs/PROTOCOLE.md and the bundle, which every result copies.
PROTOCOL_REGISTERED = "2026-10-26"
# Version précédente et son résultat, qui reste publié tel quel / previous version and its result, kept published.
PREVIOUS_VERSIONS: tuple[dict[str, str], ...] = (
    {"version": "1.0", "registered": "2026-10-25", "campaign": "2026-10-26", "engine": "1.0.0+0c3ff9fc1fb0",
     "confidence_index": "61.8 % [58.6-66.9]", "families": "7",
     "results": "benchmarks/results/protocol-2026-10-26.md",
     # Ses empreintes (PROTOCOL-REGISTRATION.json, recopiées dans le résultat 1.0) sont celles des fichiers à
     # l'enregistrement 1.0, dans l'historique du dépôt, pas des fichiers 1.1. Its digests are those of the files at
     # the 1.0 registration (repository history), not of the 1.1 files.
     "registration": "PROTOCOL-REGISTRATION.json"},
    {"version": "1.1", "registered": "2026-10-26", "campaign": "2026-10-26", "engine": "1.0.1+4bb5c465425e",
     "confidence_index": "96.9 % [96.2-97.6]", "families": "4",
     "results": "benchmarks/results/protocol-1.1-2026-10-26.md",
     "registration": "PROTOCOL-REGISTRATION-1.1.json"},
)

# --- Usage mesuré et périmètre d'une fuite (1.1) / measured use and scope of a leak (1.1) ---------------------------
USE_CASE = ("textes que les organisations envoient à une IA : courriels (en-têtes, signatures, fils cités), demandes "
            "collées dans une conversation, documents internes (comptes rendus, courriers RH, contrats, factures, "
            "notes CRM, tickets), en français, en texte ou en fichiers bureautiques, écrits de bonne foi",
            "texts organisations send to an AI: e-mails (headers, signatures, quoted threads), requests pasted into a "
            "chat, internal documents (minutes, HR letters, contracts, invoices, CRM notes, tickets), in French, as "
            "text or office files, written in good faith")
# Une fuite = un caractère lisible d'une adresse postale, d'un téléphone, d'un courriel ou d'un autre identifiant
# direct, quel qu'en soit le titulaire, ou du nom d'une personne physique. Les noms de sociétés ne comptent pas (ni
# fuite, ni sur-masquage du texte neutre ; la précision publiée compte un nom de société masqué comme un masquage
# inutile, comme en 1.0) : considérant 14 du RGPD ; CJUE 9 nov. 2010, Volker und Markus Schecke et Eifert, C-92/09 et
# C-93/09. Un entrepreneur individuel est une personne. Une ville nommée seule, comme lieu, n'est pas une adresse.
# A leak = a readable character of a postal address, phone, e-mail or other direct identifier, whoever it belongs
# to, or of a natural person's name. Company names do not count (neither leak nor over-masking of neutral text; the
# published precision counts a masked company name as an unneeded mask, as in 1.0). A sole trader is a person. A
# town named alone, as a place, is not an address. Le gold le code ainsi : aucune organisation ni ville seule dans
# REAL_DIRECT_LABELS ; l'identifiant d'une société (SIREN, SIRET, RCS) n'y compte que pour un entrepreneur individuel
# (libellé du corpus). The gold encodes it: no organisation or bare town in REAL_DIRECT_LABELS; a company identifier
# counts only for a sole trader (corpus labelling).

# Nom des fichiers de résultats : la version y figure, pour qu'aucune campagne n'écrase le résultat d'une autre
# version publié le même jour (protocol-2026-10-26 = 1.0). Results file stem: carries the version, so no campaign
# overwrites another version's published result of the same day.
RESULTS_STEM = "protocol-" + PROTOCOL_VERSION + "-{date}"

# --- Service ---------------------------------------------------------------------------------------------------
PROFILE = "standard"
LABEL_LANGUAGE = "fr"
FRENCH_COUNTRIES = "FR"           # pays explicite par défaut du produit / the product's explicit default country
TEXT_ROUTE = "/v1/anonymize/text"

# --- Corpus synthétique / synthetic corpus ----------------------------------------------------------------------
# Graines jamais utilisées pour concevoir les règles (l'évaluation de développement utilise 20261024).
# Seeds never used to design rules (the development evaluation uses 20261024).
SYNTHETIC_SEEDS: tuple[int, ...] = tuple(range(2026102501, 2026102511))      # 10 graines / seeds
SYNTHETIC_DOCS_PER_SEED = 45_000                                              # 450 000 documents
REDTEAM_SEEDS: tuple[int, ...] = tuple(range(2026102521, 2026102531))        # 10 graines / seeds
REDTEAM_BASES_PER_SEED = 1_200     # documents de base par graine, chacun passé par les 51 opérateurs
DEV_SEED = 20261024                # graine de développement, exclue de la campagne / development seed, excluded

# Opérateurs de l'équipe rouge (tools/eval/mutate.py), en trois groupes (1.1). Tous passent par le service, comme en
# 1.0 (même plan) ; tous comptent dans l'indice « documents difficiles », jamais dans l'indice « documents normalisés ».
# Red-team operators in three groups (1.1): all still go through the service (same plan); all count in the "difficult
# documents" index, never in the "normalised documents" index.
# Formats du quotidien : ce que produisent Word, Outlook, un PDF copié, un tableur, Windows ou une saisie pressée.
# Everyday formats: what Word, Outlook, a copied PDF, a spreadsheet, Windows or hurried typing produce.
REDTEAM_EVERYDAY: tuple[str, ...] = (
    # retour à la ligne (LF ou CRLF) À L'INTÉRIEUR de l'identifiant (« 06 12 34⏎56 78 », « 12 rue⏎des Lilas ») ; un
    # document entier aux fins de ligne Windows n'est pas concerné. A line break (LF or CRLF) INSIDE the identifier;
    # a whole document with Windows line endings is not what these operators test.
    "crlf", "line_break",
    # lettres espacées d'un PDF copié (« J e a n ») / letter spacing from a copied PDF (tools/eval/mutate.py: layout)
    "letter_spacing",
    # espaces de toutes sortes et tabulations / spaces of all kinds and tabs
    "nbsp", "narrow_nbsp", "thin_space", "figure_space", "ideographic_space", "tab", "double_space",
    # séparateurs et regroupements de chiffres / separators and digit grouping
    "dots", "hyphens", "slashes", "compact", "regroup", "en_dash_groups", "nb_hyphen",
    # coupure de mots (PDF, trait d'union conditionnel de Word) / hyphenation (PDF, Word's optional hyphen)
    "pdf_hyphenation", "soft_hyphen",
    # casse et ordre « NOM Prénom » / case and surname-first order
    "upper", "lower", "surname_first",
    # accents et formes de normalisation Unicode / accents and Unicode normalisation forms
    "strip_accents", "nfd",
    # Markdown
    "markdown_bold",
)
# Déguisements volontaires : indice « documents difficiles » / deliberate obfuscations: "difficult documents" index.
REDTEAM_OBFUSCATION: tuple[str, ...] = (
    # alphabets et chiffres de substitution / substitute alphabets and digits
    "math_bold", "fullwidth", "superscript", "arabic_indic", "devanagari",
    # sosies d'autres écritures / homoglyph scripts
    "cyrillic", "greek",
    # caractères invisibles insérés dans la valeur / invisible characters inserted in the value
    "zero_width_space", "zero_width_joiner", "word_joiner", "bom", "bidi_mark", "bidi_isolate", "tag_chars",
    "variation_selector", "grapheme_joiner", "hangul_filler",
    # courriels maquillés : entités HTML, encodage pour cent, arobase et point écrits en toutes lettres
    # disguised e-mails: HTML entities, percent-encoding, "at" and "dot" spelled out
    "at_entity", "at_percent", "at_fullwidth", "at_brackets", "at_parens", "arobase", "dot_brackets", "dot_point",
)
# Bruit d'OCR (une confusion 0/O, 1/l, 5/S, 8/B) : « OCR de mauvaise qualité, performance dégradée », indice
# « documents difficiles ». OCR noise: "low-quality OCR, degraded performance", "difficult documents" index.
REDTEAM_OCR: tuple[str, ...] = ("ocr",)
REDTEAM_GROUPS: dict[str, tuple[str, ...]] = {"everyday": REDTEAM_EVERYDAY, "obfuscation": REDTEAM_OBFUSCATION,
                                               "ocr": REDTEAM_OCR}

# Décompte à blanc du plan standard (`python -m tools.protocol plan --count`), enregistré AVANT la campagne : le
# rapport compare ce qui a été envoyé à ces valeurs, et le report vers le site refuse une campagne qui en diffère.
# Dry-run count of the standard plan, registered BEFORE the campaign: the report compares what was sent with these
# values, and the merge into the site refuses a campaign that differs.
REGISTERED_PLAN: dict[str, object] = {
    "faker": "40.43.0",
    "documents": {"synthetic_fr": 450_000, "redteam_bases": 12_000, "redteam_fr": 548_907},
    "synthetic_sha256": "0b91be78435e5434ee5a3b136ab8f08dd10a2c3673dad56fc6dca469c87a955b",
    "redteam_sha256": "d984ee1bf9dba70bf2ccf32957cab9da9bbf1fdf02adf5b7444956fa0137760b",
}

# --- Corpus réels / real corpora ---------------------------------------------------------------------------------
# Identifiants directs des corpus réels : familles personnelles de tools.corpus, sauf la date de naissance
# (quasi-identifiant, comme dans le schéma synthétique). Direct identifiers of the real corpora: the personal
# families of tools.corpus except the birth date (a quasi-identifier, as in the synthetic schema).
REAL_DIRECT_LABELS = frozenset({"PERSON", "ADDRESS", "EMAIL", "PHONE", "NATIONAL_ID", "TAX_ID", "IBAN",
                                "BANK_ACCOUNT", "CARD", "ID", "URL", "IP"})
# Moitié « test » (jamais vue par la conception des règles) : tools.corpus.real_common.split_of.
# "test" half (never seen by rule design): tools.corpus.real_common.split_of.
HEADLINE_SPLIT = "test"

# Pays envoyés au service pour chaque corpus réel (registre de tools.corpus) / countries sent per real corpus.
REAL_CORPORA: dict[str, str] = {
    "bodacc_fr": "FR", "boamp_fr": "FR", "parlamint_fr": "FR", "europeana_fr": "FR", "hipe_newseye_fr": "FR",
    "mapa_fr": "FR",
    "mapa_de": "DE", "mapa_es": "ES", "mapa_it": "IT", "mapa_nl": "NL", "mapa_pt": "PT", "meddocan_es": "ES",
    "german_ler_de": "DE", "tab_en": "FR",
    "judilibre_fr": "FR",
}
OUT_OF_SCOPE = ("mapa_de", "mapa_es", "mapa_it", "mapa_nl", "mapa_pt", "meddocan_es", "german_ler_de", "tab_en")
NEGATIVE_CONTROL = ("judilibre_fr",)
# Précision non mesurable (gold partiel) / precision not measurable (partial gold).
PARTIAL_GOLD = frozenset({"parlamint_fr"})

# Mesures des moitiés « test » faites AVANT la campagne (docs/PROTOCOLE.md, section 3), recopiées dans chaque résultat.
# Toute autre mesure d'une moitié test avant le lancement s'ajoute ici et dans le texte, puis on enregistre à nouveau.
# Test-half measurements taken BEFORE the campaign (section 3), copied into every result. Any other one taken before
# the launch is added here and to the text, then the protocol is registered again. Heures UTC / UTC times.
TEST_HALVES_MEASURED_BEFORE: tuple[dict[str, str], ...] = (
    {"utc": "2026-10-25", "by": "corpus analysis", "engine": "1.0.0",
     "what": "whole-corpus analysis before the split (docs/CORPUS_REELS.md, sections 1 to 7)"},
    {"utc": "2026-10-25T20:21", "by": "engine tuning", "engine": "1.0.0",
     "what": "in-process evaluation of the dev and test halves (docs/CORPUS_REELS.md, section 12, 'before' column)"},
    {"utc": "2026-10-25T21:04", "by": "protocol tool trial", "engine": "sources of that moment",
     "what": "scaled plan, full real corpora: index 45.3%"},
    {"utc": "2026-10-25T21:18", "by": "protocol tool trial", "engine": "sources of that moment",
     "what": "scaled plan, full real corpora: index 45.2%"},
    {"utc": "2026-10-25T21:36/22:20", "by": "engine tuning", "engine": "rules2 iterations, and 1.0.0 at 21:53",
     "what": "in-process evaluations of the test halves and whole corpora at each of four rules2 iterations, and of "
             "1.0.0 on whole corpora; the last one published at 22:22 "
             "(benchmarks/results/real-rules2-comparison-2026-10-25)"},
    {"utc": "2026-10-25T21:42", "by": "independent audit of the tool", "engine": "sources of that moment",
     "what": "scaled plan, full real corpora: index 61.2%"},
    {"utc": "2026-10-25T22:59", "by": "independent review of the engine tuning", "engine": "1.0.0 and rules2",
     "what": "in-process evaluation of the test halves and whole corpora, same figures as 22:22, not published"},
    # Ajouts de la version 1.1 / added by version 1.1
    {"utc": "2026-10-26", "by": "engine tuning (independent review, rules3)", "engine": "rules2 and rules3",
     "what": "in-process evaluation of the dev and test halves and unseen sets, rules2 against rules3 "
             "(benchmarks/results/real-rules3-comparison-2026-10-26, docs/CORPUS_REELS.md section 13)"},
    {"utc": "2026-10-26", "by": "public protocol campaign 1.0", "engine": "1.0.0+0c3ff9fc1fb0",
     "what": "standard campaign, published: index 61.8% [58.6-66.9] under protocol 1.0, scores per family, corpus, "
             "label and red-team operator (benchmarks/results/protocol-2026-10-26)"},
    # Ajouts de la version 1.2 (« added_by » : un résultat 1.1 relu ne les montre pas) / added by version 1.2.
    {"utc": "2026-10-26", "by": "public protocol campaign 1.1", "engine": "1.0.1+4bb5c465425e",
     "what": "standard campaign, published: normalised 96.9% [96.2-97.6], difficult 84.0% under protocol 1.1, scores "
             "per family, corpus, label and red-team operator (benchmarks/results/protocol-1.1-2026-10-26)",
     "added_by": "1.2"},
)
# Campagnes standard déjà publiées sur ces moitiés test : après la première, elles ne sont plus aveugles. Une campagne
# suivante les liste ici (nouvelle version datée du protocole) ; le report vers le site refuse une campagne répétée
# qui omet celle qu'il remplace. Standard campaigns already published on these test halves: after the first one they
# are no longer blind. A later campaign lists them here (new dated protocol version); the merge into the site refuses
# a repeat campaign that omits the one it replaces. Entrée / entry: {"date": "AAAA-MM-JJ", "engine": "1.0.0+<12 hex>"}.
EARLIER_CAMPAIGNS: tuple[dict[str, str], ...] = (
    {"date": "2026-10-26", "engine": "1.0.0+0c3ff9fc1fb0", "protocol": "1.0",
     "confidence_index": "61.8 % [58.6-66.9]"},
    {"date": "2026-10-26", "engine": "1.0.1+4bb5c465425e", "protocol": "1.1",
     "confidence_index": "96.9 % [96.2-97.6]"},
)

# --- Modes du filtre (1.2) / filter modes (1.2) ----------------------------------------------------------------------
# Modes déclarés par le plan standard 1.2, le premier est le défaut du produit (clés confidence_* et hard_* du site).
# Chaque document est noté une fois par mode ; le service reçoit « mode » (et plus « profile », dont « standard »
# vaut désormais « essentiel »). Modes declared by the 1.2 standard plan, the first one is the product default (site
# keys confidence_* and hard_*). Every document is scored once per mode; the service gets "mode" (no longer "profile").
MODES: tuple[str, ...] = ("fort", "essentiel")
MODE_TITLES: dict[str, tuple[str, str]] = {"fort": ("Mode fort", "Strong mode"),
                                           "essentiel": ("Mode essentiel", "Essential mode")}
# Préfixe des clés du site par mode / site key prefix per mode.
MODE_SITE_PREFIX: dict[str, str] = {"fort": "fort", "essentiel": "ess"}
# Séparateur mode / cellule dans le point de reprise (« fort::synthetic_fr/seed=… ») / mode-cell key separator.
MODE_SEP = "::"
# Garde-fou des leurres : mode essentiel seulement. En mode fort, la perte de codes utiles est publiée sans garde-fou
# (le mode fort masque tous les codes par choix du produit). Decoy guard: essentiel only; in fort the loss of useful
# codes is published without a guard (fort masks every code by the product's choice).
DECOY_GUARD_MODES: tuple[str, ...] = ("essentiel",)


@dataclass(frozen=True, slots=True)
class Family:
    """Famille de l'indice (poids égal) ou publiée à part / index family (equal weight) or published apart."""

    name: str
    kind: str                       # "synthetic", "redteam" ou "real"
    corpora: tuple[str, ...] = ()   # corpus réels regroupés / pooled real corpora
    title_fr: str = ""
    title_en: str = ""
    operators: tuple[str, ...] = ()  # opérateurs d'équipe rouge retenus / red-team operators kept ("redteam" only)


# Deux indices publiés (1.1), même mesure : part des documents où rien de ce que le produit promet de masquer ne reste
# lisible. Two published indexes (1.1), same measure: share of documents in which nothing the product promises to mask
# stays readable. Clé, titre français, titre anglais / key, French title, English title.
INDEXES: dict[str, tuple[str, str]] = {
    "normalised": ("Documents normalisés", "Normalised documents"),
    "hard": ("Documents difficiles", "Difficult documents"),
}
# Cible déclarée de l'indice « documents normalisés » : un objectif, jamais un garde-fou ni une condition de
# publication (le chiffre se publie quel qu'il soit). Declared target of the normalised index: a goal, never a guard
# nor a publication condition (the figure is published whatever it is).
NORMALISED_TARGET = 0.95

# Indice « documents normalisés » (l'indice principal, clés confidence_* du site) : poids égal, 1/4 par famille.
# "Normalised documents" index (the headline, site keys confidence_*): equal weight, 1/4 per family.
FAMILIES: tuple[Family, ...] = (
    Family("synthetic_fr", "synthetic", (), "Synthétique FR (10 graines, leurres)", "Synthetic FR (10 seeds, decoys)"),
    Family("bodacc_fr", "real", ("bodacc_fr",), "BODACC", "BODACC"),
    Family("boamp_fr", "real", ("boamp_fr",), "BOAMP", "BOAMP"),
    Family("parlamint_fr", "real", ("parlamint_fr",), "ParlaMint-FR", "ParlaMint-FR"),
)
# Indice « documents difficiles » (clés hard_* du site) : les trois groupes de l'équipe rouge, 51 opérateurs. Poids :
# chaque document muté compte une fois (tous les opérateurs mis en commun) ; un opérateur pèse donc le nombre de
# documents qu'il modifie (un opérateur qui ne trouve rien à changer dans un document n'en produit pas). Intervalle :
# bootstrap stratifié par groupe. La clé `redteam_fr` (formats du quotidien) garde son nom : le site la lit (f_red_*).
# "Difficult documents" index (site keys hard_*): the red team's three groups, 51 operators. Weights: every mutated
# document counts once (all operators pooled), so an operator weighs the number of documents it alters. Interval:
# bootstrap stratified by group. The `redteam_fr` key (everyday formats) keeps its name: the site reads it (f_red_*).
HARD_FAMILIES: tuple[Family, ...] = (
    Family("redteam_fr", "redteam", (),
           f"Équipe rouge FR, formats du quotidien abîmés ({len(REDTEAM_EVERYDAY)} opérateurs)",
           f"Red team FR, damaged everyday formats ({len(REDTEAM_EVERYDAY)} operators)", REDTEAM_EVERYDAY),
    Family("redteam_obfuscation_fr", "redteam", (),
           f"Équipe rouge FR, déguisements volontaires ({len(REDTEAM_OBFUSCATION)} opérateurs)",
           f"Red team FR, deliberate obfuscations ({len(REDTEAM_OBFUSCATION)} operators)", REDTEAM_OBFUSCATION),
    Family("redteam_ocr_fr", "redteam", (), "Équipe rouge FR, bruit d'OCR : performance dégradée",
           "Red team FR, OCR noise: degraded performance", REDTEAM_OCR),
)
# Groupe de l'équipe rouge -> famille de l'indice difficile / red-team group -> difficult-index family.
HARD_GROUP_FAMILY: dict[str, str] = {"everyday": "redteam_fr", "obfuscation": "redteam_obfuscation_fr",
                                     "ocr": "redteam_ocr_fr"}
# Publiées à part avec leurs chiffres, dans aucun des deux indices (1.1) / published apart, in neither index (1.1).
APART_FAMILIES: tuple[Family, ...] = (
    Family("old_press_fr", "real", ("europeana_fr", "hipe_newseye_fr"),
           "Presse ancienne FR (Europeana + HIPE), OCR de mauvaise qualité : performance dégradée",
           "Old French press (Europeana + HIPE), low-quality OCR: degraded performance"),
    Family("mapa_fr", "real", ("mapa_fr",), "MAPA FR (6 documents notés : sans valeur statistique)",
           "MAPA FR (6 scored documents: statistically meaningless)"),
)
FAMILY_OF_CORPUS: dict[str, str] = {c: f.name for f in FAMILIES + APART_FAMILIES for c in f.corpora}
INDEX_CORPORA: tuple[str, ...] = tuple(c for f in FAMILIES for c in f.corpora)

# --- Statistiques / statistics ------------------------------------------------------------------------------------
BOOTSTRAP_RESAMPLES = 2_000
BOOTSTRAP_SEED = 20261025
CI_LEVEL = 0.95

# --- Garde-fous : l'indice ne mesure que les fuites ; masquer tout donnerait 100 %. Publié seulement si : ----------
# Guards: the index only measures leaks; masking everything would score 100%. Published only if:
GUARD_MAX_OVERMASK = 0.02          # sur-masquage du texte neutre, familles synthétiques / neutral-text over-masking
GUARD_MAX_DECOY_MASKED = 0.10      # leurres masqués à tort, famille synthétique / decoys wrongly masked
GUARD_MIN_PRECISION = 0.70         # précision au caractère, BODACC et BOAMP (moitié test) / char precision
GUARD_PRECISION_FAMILIES = ("bodacc_fr", "boamp_fr")

# --- Campagne / campaign -------------------------------------------------------------------------------------------
UNIT_SYNTHETIC_DOCS = 1_500        # documents par unité de travail (reprise) / documents per work unit (resume)
UNIT_REDTEAM_BASES = 30            # documents de base par unité (≈ 1 400 documents mutés) / base documents per unit
UNIT_REAL_DOCS = 100
CLIENT_THREADS = 3                 # 2 en cours au service (plafond LOCAL) + 1 en file / 2 running + 1 queued
MAX_DOC_RETRY_S = 1_800            # 429/503 plus longtemps pour un document : pause (jamais une fuite) / then pause
SERVICE_DOWN_S = 600               # service injoignable plus longtemps : pause de la campagne / campaign pauses
CHECKPOINT_S = 60.0                # point de reprise, après un contrôle du moteur / checkpoint, after an engine check

# --- Une campagne = un moteur / one campaign = one engine ------------------------------------------------------------
# Empreinte du moteur : image du conteneur du service (donnée par run-protocol.sh), version, catalogue des packs et
# empreinte des SORTIES du service sur une sonde fixe (documents de la graine de développement, jamais notés).
# Contrôlée au départ, à chaque point de reprise, après toute panne de connexion ou tout redémarrage du service, et
# à la fin : un écart arrête la campagne sans écrire ce qui a suivi le dernier contrôle réussi.
# Engine fingerprint: the service container's image, version, pack catalogue and the digest of the service's OUTPUTS on
# a fixed probe (development-seed documents, never scored). Checked at start, at every checkpoint, after any connection
# failure or service restart, and at the end: a difference stops the campaign without writing anything after the last
# passing check.
ENGINE_PROBE_SEED = DEV_SEED
ENGINE_PROBE_DOCS = 200

# --- Écarts à déclarer publiquement / departures to disclose publicly ------------------------------------------------
# `run --disclose CODE[:DÉTAIL]` ou `report --disclose …` (run-protocol.sh les passe) : gardés dans le point de reprise,
# recopiés dans les résultats et rappelés par le report vers le site. Kept in the checkpoint, copied into the results
# and recalled by the merge into the site.
DISCLOSURES: dict[str, tuple[str, str]] = {
    "allow_swap": ("swap actif pendant la campagne (GG_PROTOCOL_ALLOW_SWAP=1) : des pages des corpus réels ont pu "
                   "atteindre le disque",
                   "swap active during the campaign (GG_PROTOCOL_ALLOW_SWAP=1): pages of the real corpora may have "
                   "reached the disk"),
    "redeployed_after": ("service redéployé après la fin de la campagne : l'image du service au moment de `finish` "
                         "n'est plus celle de la campagne (GG_PROTOCOL_REDEPLOYED_AFTER=1)",
                         "service redeployed after the campaign ended: the service image at `finish` is no longer "
                         "the campaign's (GG_PROTOCOL_REDEPLOYED_AFTER=1)"),
}


def total_planned() -> dict[str, int]:
    """Nombre de documents de base prévus (les mutés se comptent au plan) / planned base documents."""
    return {"synthetic_fr": len(SYNTHETIC_SEEDS) * SYNTHETIC_DOCS_PER_SEED,
            "redteam_bases": len(REDTEAM_SEEDS) * REDTEAM_BASES_PER_SEED}
