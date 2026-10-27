"""Filtre fort 1.0.2, tour de correction après la jonction : comptes Teams, Skype, Slack et WhatsApp, pseudonyme
capitalisé, dossier personnel d'un chemin, champ d'adresse et étiquette déjà posée, voie coupée en fin de ligne
(STREET_WRAP), sigles pointés, temps linéaire des noms coupés par un saut de ligne.

Strong filter 1.0.2, fix round after the join: Teams, Skype, Slack and WhatsApp accounts, a capitalised pseudonym,
the user folder of a path, the address field and an existing tag, a street cut at the line end (STREET_WRAP), dotted
acronyms, linear time for names split by a line break. Chaque cas tourne sur le noyau Rust (s'il est installé) et sur
la référence Python. Every case runs on the Rust core (when installed) and on the Python reference. Données fictives
/ fictitious data.
"""

from __future__ import annotations

import time

import pytest

from gdprguardian import Anonymizer, _native

_ENGINES = [pytest.param(True, id="rust", marks=pytest.mark.skipif(not _native.available(),
                                                                    reason="noyau Rust absent / no Rust core")),
            pytest.param(False, id="python")]
_MODES = ("fort", "essentiel")


@pytest.fixture(scope="module", params=_ENGINES)
def native(request) -> bool:
    return request.param


_CACHE: dict[tuple[bool, str], Anonymizer] = {}


def _out(native: bool, mode: str, text: str) -> str:
    key = (native, mode)
    if key not in _CACHE:
        _CACHE[key] = Anonymizer(countries=("FR",), native=native, mode=mode)
    return _CACHE[key].anonymize(text).text


# --- (1) Comptes de messagerie, pseudonymes, chemins / chat accounts, pseudonyms, paths ------------------------------


@pytest.mark.parametrize("mode", _MODES)
@pytest.mark.parametrize("text, secret", [
    ("Teams : jdupont", "jdupont"),
    ("Teams : j.dupont", "dupont"),
    ("Teams : jean.dupont", "dupont"),
    ("Teams : jean-pierre.dupont", "dupont"),
    ("Teams : Jdupont", "Jdupont"),
    ("Teams : jdupont42", "jdupont42"),
    ("Skype : jdupont", "jdupont"),
    ("Skype : jean.dupont", "dupont"),
    ("Slack : jdupont", "jdupont"),
    ("Slack: jean.dupont", "dupont"),
    ("WhatsApp : jean.dupont", "dupont"),
    ("Pseudo : Kryptonix", "Kryptonix"),
    ("Pseudo : NeoKraken.", "NeoKraken"),
    ("C:\\Users\\alegoff\\Desktop\\cv.docx", "alegoff"),
    ("/home/alegoff/Documents/cv.pdf", "alegoff"),
    ("/Users/alegoff/Downloads/a.txt", "alegoff"),
])
def test_cued_account_is_masked(native, mode, text, secret):
    out = _out(native, mode, text)
    assert secret not in out, out


@pytest.mark.parametrize("mode", _MODES)
@pytest.mark.parametrize("text", [
    "Teams : lundi",
    "Réunion Teams : lundi à 10 h.",
    "Teams : 14h30 avec l'équipe",
    "Teams : demain",
    "Teams : réunion lundi. Skype : indisponible.",
    "Zoom : 14h30. Google Meet : lien envoyé. Slack : #general.",
    "Slack : canal",
    "WhatsApp : Groupe",
    "Pseudo : Non renseigné.",
    "Pseudo : Aucun",
    "C:\\Users\\Public\\Documents",
    "C:\\Users\\Default\\AppData",
    "C:\\Users\\Administrator\\Desktop",
])
def test_ordinary_value_stays_readable(native, mode, text):
    assert _out(native, mode, text) == text


# --- (2) Champ d'adresse et étiquette déjà posée / address field and an existing tag --------------------------------


@pytest.mark.parametrize("mode", _MODES)
@pytest.mark.parametrize("text", ["Adresse : voir [EMAIL_1].", "Adresse : chez [PERSONNE_1]"])
def test_address_field_never_cuts_a_tag(native, mode, text):
    out = _out(native, mode, text)
    assert "]]" not in out, out
    assert _out(native, mode, out) == out


# --- (3) STREET_WRAP : la ligne suivante doit ressembler à un nom de voie / the next line must look like a street ---


@pytest.mark.parametrize("mode", _MODES)
@pytest.mark.parametrize("text", [
    "Kilomètre 12 route\nbarrée jusqu'à lundi.",
    "Point 12 rue\nÀ revoir avec le BE.",
    "12 avenue\nles résultats sont bons.",
    "12 avenue\nLes résultats sont bons.",
    "12 rue\nMerci de rappeler.",
])
def test_street_wrap_does_not_swallow_a_sentence(native, mode, text):
    assert _out(native, mode, text) == text


@pytest.mark.parametrize("mode", _MODES)
def test_street_wrap_keeps_the_next_label(native, mode):
    out = _out(native, mode, "Adresse : 12 avenue\nTéléphone : 01 44 55 66 77")
    assert "\nTéléphone : [TEL_1]" in out, out


@pytest.mark.parametrize("mode", _MODES)
@pytest.mark.parametrize("text, secret", [
    ("84 rue\ndes Lilas\n75011 Paris", "Lilas"),
    ("12 rue\r\ndes Lilas\r\n75011 Paris", "Lilas"),
    ("Mme Durand\n84 rue\nVictor Hugo\n75011 Paris", "Hugo"),
    ("12 avenue\nde la République\n69003 Lyon", "République"),
    ("4 impasse\n> des Camélias", "Camélias"),
    ("12 boulevard\nLe Peletier", "Peletier"),
    ("12 rue\nd'Alsace", "Alsace"),
    ("logement situé 103 rue\r\ndu 8 Mai 1945 – 75011 Paris.", "Mai"),
    ("Paul Durand, 14 rue\ndu 8 Mai 1945, 75011 Paris", "Mai"),
])
def test_street_wrap_still_joins_a_street_name(native, mode, text, secret):
    out = _out(native, mode, text)
    assert secret not in out, out


# --- (4) Initiales : jamais lues comme un sigle à côté d'une personne / initials next to a person stay masked ---------
# Ajouter RG, AJ, LR… à `DOTTED_NOT_INITIALS` laissait lisibles « Martin (A.J.) » et « Présents : …, …, LR » (corpus
# d'essai et corpus réservé) : retiré. Adding them left real initials readable; reverted.


@pytest.mark.parametrize("mode", _MODES)
@pytest.mark.parametrize("text, secret", [
    ("Rédigé par J.D. hier", "J.D."),
    ("Votre conseiller Paul Martin (A.J.) vous rappellera.", "A.J."),
    ("Votre conseiller Paul Martin (L.R.) vous rappellera.", "L.R."),
])
def test_dotted_initials_still_masked(native, mode, text, secret):
    assert secret not in _out(native, mode, text)


# --- (5) Noms coupés par un saut de ligne : temps linéaire / names split by a line break: linear time -------------


@pytest.mark.parametrize("unit", ["Jean LE\nGALL, ", "Contact : Yann LE\nGALL\n"])
def test_split_name_time_is_linear(native, unit):
    small = unit * (20_000 // len(unit))
    large = unit * (80_000 // len(unit))
    _out(native, "fort", small)  # échauffement / warm-up
    t0 = time.perf_counter()
    _out(native, "fort", small)
    t1 = time.perf_counter()
    _out(native, "fort", large)
    t2 = time.perf_counter()
    # Quatre fois plus de texte : bien moins que seize fois plus de temps / 4x the text: far less than 16x the time.
    assert (t2 - t1) < 10 * max(t1 - t0, 0.01), (t1 - t0, t2 - t1)
