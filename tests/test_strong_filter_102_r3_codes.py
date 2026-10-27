"""Filtre fort 1.0.2, dernier tour, voie « codes » : codes coupés par une espace, pseudonymes « @… » et indices de
plateforme, comptes « DOMAINE\\utilisateur » et indices de connexion, indices « avatar » / « nickname » / « pseudo »,
balise jamais relue.

Strong filter 1.0.2, last round, "codes" lane: codes split by a space, "@" handles and platform cues,
"DOMAIN\\user" accounts and login cues, "avatar" / "nickname" / "pseudo" cues, a tag never read again. Chaque cas
tourne sur le noyau Rust (s'il est installé) et sur la référence Python. Every case runs on the Rust core (when
installed) and on the Python reference. Données fictives / fictitious data.
"""

from __future__ import annotations

import pytest

from gdprguardian import Anonymizer, _native
from gdprguardian.detectors.codes import split_code_spans

_ENGINES = [pytest.param(True, id="rust", marks=pytest.mark.skipif(not _native.available(),
                                                                    reason="noyau Rust absent / no Rust core")),
            pytest.param(False, id="python")]


@pytest.fixture(scope="module", params=_ENGINES)
def native(request) -> bool:
    return request.param


_CACHE: dict[tuple[bool, str], Anonymizer] = {}


def _out(native: bool, mode: str, text: str) -> str:
    key = (native, mode)
    if key not in _CACHE:
        _CACHE[key] = Anonymizer(countries=("FR",), native=native, mode=mode)
    return _CACHE[key].anonymize(text).text


# --- (1) Codes coupés par une espace / split codes ------------------------------------------------------------------


@pytest.mark.parametrize("text, secrets", [
    ("Référence CLT\u00a0204518 transmise.", ["CLT", "204518"]),
    ("Voir DOS 164520 pour la suite.", ["DOS", "164520"]),
    ("Code d'activation AB12 CD34 EF56 envoyé.", ["AB12", "CD34", "EF56"]),
    ("Badge X7K2\u202fP9Q4\u202fZZ81 désactivé", ["X7K2", "P9Q4", "ZZ81"]),
])
def test_split_code_is_masked_whole_in_fort(native, text, secrets):
    out = _out(native, "fort", text)
    for secret in secrets:
        assert secret not in out, out


@pytest.mark.parametrize("text, kept", [
    ("Référence CLT 204518 transmise.", "CLT 204518"),
    ("Code d'activation AB12 CD34 EF56 envoyé.", "AB12 CD34 EF56"),
])
def test_split_code_without_personal_label_stays_readable_in_essentiel(native, text, kept):
    assert kept in _out(native, "essentiel", text)


@pytest.mark.parametrize("text", [
    "Envoyer à PARIS 75011 avant lundi.",          # code postal : 5 chiffres / postcode
    "Code CPV 452331 et NAF 4711 pour le lot.",    # nomenclature
    "Site Natura 2000 FR 4211811 - ZPS Vallée",    # site Natura 2000
    "Norme ISO 900120 appliquée.",                 # norme / standard
    "Montant EUR 125000 réglé.",                   # devise / currency
    "Séance du 12 MARS 2026 à 10h",                # date
    "FORMAT A4 A3 A2 seulement",                   # groupes trop courts / groups too short
    "LOT 1234 5678 9012",                          # aucun groupe mixte / no mixed group
])
def test_not_split_codes(text):
    assert split_code_spans(text) == []


def test_split_code_glued_to_a_token_is_not_read():
    assert split_code_spans("ref-CLT 204518") == []
    assert split_code_spans("CLT 204518-2") == []
    assert split_code_spans("CLT 204518.5") == []
    assert split_code_spans("Voir CLT 204518.") == [(5, 15, "CLT204518")]


# --- (2) Pseudonymes « @… » et plateformes / handles and platforms ---------------------------------------------------


@pytest.mark.parametrize("text, secrets", [
    ("Contact : @jean-pierre.dupont sur le forum.", ["jean", "pierre", "dupont"]),
    ("Écrire à @k.lambert demain.", ["lambert"]),
])
def test_handle_with_hyphen_or_initial_is_masked_whole_in_fort(native, text, secrets):
    out = _out(native, "fort", text)
    for secret in secrets:
        assert secret not in out, out


@pytest.mark.parametrize("mode", ["fort", "essentiel"])
@pytest.mark.parametrize("text, secret", [
    ("Instagram : jp_dupont75", "jp_dupont75"),
    ("insta : lune.noire", "lune.noire"),
    ("Son compte GitHub : kdupont", "kdupont"),
    ("LinkedIn : jean-pierre-dupont-4a5b6c", "jean-pierre"),
    ("Discord : lune#1234", "lune"),
    ("Teams : jdupont42", "jdupont42"),
])
def test_platform_cue_masks_the_account_in_every_mode(native, mode, text, secret):
    out = _out(native, mode, text)
    assert secret not in out, out
    assert text.split(":")[0] in out, out  # l'indice reste lisible / the cue stays readable


def test_platform_cue_never_takes_a_web_address(native):
    out = _out(native, "fort", "LinkedIn : https://exemple.fr/profil")
    assert "[PSEUDO" not in out, out


@pytest.mark.parametrize("mode", ["fort", "essentiel"])
@pytest.mark.parametrize("text", ["Réunion Teams : lundi à 10 h.", "Teams : 14h30 avec l'équipe",
                                  "Lien Teams : demain matin"])
def test_teams_meeting_notes_stay_readable(native, mode, text):
    # « Teams » est d'abord un outil de réunion : sans chiffre ni « _ », la suite n'est pas un compte (jonction).
    # Teams is first a meeting tool: without a digit or "_", what follows is not an account.
    out = _out(native, mode, text)
    assert "[PSEUDO" not in out, out


# --- (3) Comptes et indices de connexion / accounts and login cues ---------------------------------------------------


@pytest.mark.parametrize("mode", ["fort", "essentiel"])
@pytest.mark.parametrize("text, secret, kept", [
    ("Connexion refusée pour CORP\\jdupont ce matin.", "jdupont", "CORP\\"),
    ("Compte ACME-FR\\k.lambert verrouillé.", "k.lambert", "ACME-FR\\"),
    ("Session CORP\\Jean.Dupont ouverte.", "Dupont", "CORP\\"),
    ("nom d'utilisateur jdupont", "jdupont", "nom d'utilisateur"),
    ("compte AD : jdupont", "jdupont", "compte AD"),
    ("compte AD jdupont", "jdupont", "compte AD"),
    ("sAMAccountName kdupont", "kdupont", "sAMAccountName"),
])
def test_login_cues_mask_the_user_part(native, mode, text, secret, kept):
    out = _out(native, mode, text)
    assert secret not in out, out
    assert kept in out, out


@pytest.mark.parametrize("text, kept", [
    ("Chaque utilisateur reste responsable de son poste.", "utilisateur reste"),
    ("Les utilisateurs restent connectés.", "restent"),
    ("Ouvrir C:\\WINDOWS\\Temp et \\\\SERVEUR\\partage", "SERVEUR\\partage"),
    ("Journal : ERROR\\nStackTrace suit", "ERROR\\nStackTrace"),   # échappement / escape sequence
])
def test_not_logins(native, text, kept):
    assert kept in _out(native, "essentiel", text)


# --- (4) Pseudonymes après « avatar », « nickname », « pseudo » / pseudonym cues -------------------------------------


@pytest.mark.parametrize("mode", ["fort", "essentiel"])
@pytest.mark.parametrize("text, secret", [
    ("avatar : darkvador", "darkvador"),
    ("Son avatar dark_vador42 apparaît.", "dark_vador42"),
    ("Son avatar darkvador apparaît.", "darkvador"),
    ("nickname: kiki", "kiki"),
    ("Nickname : Kiki", "Kiki"),
    ("pseudo : lunenoire", "lunenoire"),
])
def test_pseudonym_cues(native, mode, text, secret):
    out = _out(native, mode, text)
    assert secret not in out, out


@pytest.mark.parametrize("text, kept", [
    ("Changer l'avatar choisi.", "avatar choisi"),
    ("Son avatar animé bouge.", "avatar animé"),
])
def test_pseudonym_cue_needs_a_handle(native, text, kept):
    assert kept in _out(native, "fort", text)


# --- (6) Une balise produite n'est jamais relue / a produced tag is never read again ---------------------------------


@pytest.mark.parametrize("mode", ["fort", "essentiel"])
@pytest.mark.parametrize("text", [
    "mot de passe : [SECRET_1]",
    "mot de passe [SECRET_1]",
    "Le mot de passe est [SECRET_1].",
    "token=[SECRET_1]",
    "login : [PSEUDO_1]",
])
def test_tag_is_never_masked_again(native, mode, text):
    assert _out(native, mode, text) == text


@pytest.mark.parametrize("text", [
    "mot de passe : Zx9!kLm27pQ",
    "Le mot de passe est Soleil2024!",
    "Référence CLT 204518, avatar : darkvador, CORP\\jdupont",
])
def test_anonymising_twice_changes_nothing(native, text):
    once = _out(native, "fort", text)
    assert _out(native, "fort", once) == once


def test_password_starting_with_a_bracket_stays_masked(native):
    out = _out(native, "fort", "mot de passe : [x9!kLm27]")
    assert "x9!kLm27" not in out, out
