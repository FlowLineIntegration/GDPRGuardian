"""Définitions pré-enregistrées du protocole (25 octobre 2026) / pre-registered protocol definitions.

Tout ce qui décide d'un chiffre publié est ici, figé AVANT la campagne et recopié dans docs/PROTOCOLE.md :
familles, graines, tailles, identifiants directs, définition de la fuite, formule de l'indice, pondération,
bootstrap, garde-fous. Changer une valeur = nouvelle version du protocole, datée, jamais une retouche silencieuse.
Everything that decides a published figure lives here, frozen BEFORE the campaign and copied into
docs/PROTOCOLE.md. Changing a value means a new, dated protocol version, never a silent edit.
"""

from __future__ import annotations

from dataclasses import dataclass

PROTOCOL_VERSION = "1.0"
# Date d'écriture de cette version. L'enregistrement lui-même = la publication, avant le lancement, des empreintes de
# ce fichier, de docs/PROTOCOLE.md et du paquet (`python -m tools.protocol registration`), que chaque résultat recopie.
# Date this version was written. The registration itself = publishing, before the launch, the digests of this file,
# docs/PROTOCOLE.md and the bundle, which every result copies.
PROTOCOL_REGISTERED = "2026-10-25"

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
)
# Campagnes standard déjà publiées sur ces moitiés test : après la première, elles ne sont plus aveugles. Une campagne
# suivante les liste ici (nouvelle version datée du protocole) ; le report vers le site refuse une campagne répétée
# qui omet celle qu'il remplace. Standard campaigns already published on these test halves: after the first one they
# are no longer blind. A later campaign lists them here (new dated protocol version); the merge into the site refuses
# a repeat campaign that omits the one it replaces. Entrée / entry: {"date": "AAAA-MM-JJ", "engine": "1.0.0+<12 hex>"}.
EARLIER_CAMPAIGNS: tuple[dict[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class Family:
    """Famille du périmètre français ; chacune pèse 1/7 dans l'indice / French-scope family, 1/7 of the index."""

    name: str
    kind: str                       # "synthetic", "redteam" ou "real"
    corpora: tuple[str, ...] = ()   # corpus réels regroupés / pooled real corpora
    title_fr: str = ""
    title_en: str = ""


FAMILIES: tuple[Family, ...] = (
    Family("synthetic_fr", "synthetic", (), "Synthétique FR (10 graines, leurres)", "Synthetic FR (10 seeds, decoys)"),
    Family("redteam_fr", "redteam", (), "Équipe rouge FR (51 opérateurs)", "Red team FR (51 operators)"),
    Family("bodacc_fr", "real", ("bodacc_fr",), "BODACC", "BODACC"),
    Family("boamp_fr", "real", ("boamp_fr",), "BOAMP", "BOAMP"),
    Family("parlamint_fr", "real", ("parlamint_fr",), "ParlaMint-FR", "ParlaMint-FR"),
    Family("old_press_fr", "real", ("europeana_fr", "hipe_newseye_fr"), "Presse ancienne FR (Europeana + HIPE)",
           "Old French press (Europeana + HIPE)"),
    Family("mapa_fr", "real", ("mapa_fr",), "MAPA FR", "MAPA FR"),
)
FAMILY_OF_CORPUS: dict[str, str] = {c: f.name for f in FAMILIES for c in f.corpora}

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
