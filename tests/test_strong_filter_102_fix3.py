"""Filtre fort 1.0.2, troisième tour : corrections des revues du 26/10 (fuites, faux positifs, intégrité).

Strong filter 1.0.2, third round: fixes from the 26/10 reviews (leaks, false positives, integrity). Chaque cas tourne
sur le noyau Rust (s'il est installé) et sur la référence Python / every case runs on the Rust core (when installed)
and on the Python reference. Données fictives / fictitious data.
"""

from __future__ import annotations

import pytest

from gdprguardian import Anonymizer, _native

_ENGINES = [pytest.param(True, id="rust", marks=pytest.mark.skipif(not _native.available(),
                                                                    reason="noyau Rust absent / no Rust core")),
            pytest.param(False, id="python")]
_MODES = ["fort", "essentiel"]


def _out(text: str, native: bool, **settings) -> str:
    return Anonymizer(countries=("FR",), native=native, **settings).anonymize(text).text


@pytest.mark.parametrize("native", _ENGINES)
@pytest.mark.parametrize("mode", _MODES)
@pytest.mark.parametrize("text, expected", [
    # Un numéro de TVA compact en fin de ligne ne prend jamais le début du téléphone de la ligne d'après.
    # A compact VAT number ending a line never takes the start of the next line's phone number.
    ("TVA FR44732829320\n06 12 34 56 78", "TVA FR44732829320\n[TEL_1]"),
    # Un UUID après « identifiant » est masqué entier, jamais coupé / a UUID after "identifiant" is masked whole.
    ("identifiant 12345678-1234-4000-a000-0123456789ab", "identifiant [IDENTIFIANT_1]"),
    # Un courriel complet en tête de ligne ne prend jamais la fin de la ligne d'avant.
    # A complete address at a line start never takes the end of the previous line.
    ("Bonjour M.\npaul@exemple.fr", "Bonjour M.\n[EMAIL_1]"),
    # Un morceau en minuscules reste recollé, CRLF compris / a lowercase piece is still joined back, CRLF too.
    ("x michele.\r\nvallee57@exemple.fr y", "x [EMAIL_1] y"),
    # Un numéro après un libellé ne franchit jamais la ligne d'un code postal et de sa ville.
    # A labelled number never crosses into a postcode-and-town line.
    ("Dossier 56 78\n75011 Paris", "Dossier [IDENTIFIANT_1]\n75011 Paris"),
    # Le contrôle de sortie ne masque jamais un montant / the output self-check never masks an amount.
    ("Contrat 100000 signé ; capital 100000 € ; 2 x 100000 EUR.",
     "Contrat [IDENTIFIANT_1] signé ; capital 100000 € ; 2 x 100000 EUR."),
    # Jeton affecté hors d'une URL : un secret, dans tous les modes / an assigned token: a secret in every mode.
    ("token=abcDEF123456ghi", "token=[SECRET_1]"),
    # « # » relie un code et son numéro / "#" joins a code and its number.
    ("Client CLT#204518 a appelé.", "Client [IDENTIFIANT_1] a appelé."),
])
def test_third_round_fixes(native, mode, text, expected):
    assert _out(text, native, mode=mode) == expected


@pytest.mark.parametrize("native", _ENGINES)
@pytest.mark.parametrize("text", [
    "DUPONT Jean réglera la facture n° 2026-0042",
    "commande 123456",
    "Ticket de caisse 0001234567",
    "n° de commande 20260042",
])
def test_business_numbers_stay_readable_in_essentiel_only(native, text):
    """Facture, commande, ticket de caisse : pas des libellés personnels ; le mode fort masque le numéro.

    Invoice, order, till receipt: not personal labels; mode fort masks the number."""
    number = text.split()[-1]
    assert number in _out(text, native, mode="essentiel")
    assert number not in _out(text, native, mode="fort")


@pytest.mark.parametrize("native", _ENGINES)
def test_code_line_never_glued_to_the_next_line_address(native):
    assert _out("Code SKU-123456\nsupport@ex.fr", native) == "Code [IDENTIFIANT_1]\n[EMAIL_1]"
    assert _out("Code SKU-123456\nsupport@ex.fr", native, mode="essentiel") == "Code SKU-123456\nsupport@ex.fr"


@pytest.mark.parametrize("native", _ENGINES)
def test_nearer_personal_label_wins_over_business_label(native):
    assert "123456" not in _out("facture du client 123456", native, mode="essentiel")


@pytest.mark.parametrize("native", _ENGINES)
def test_secret_assignment_is_never_disabled(native):
    assert "abcDEF123456ghi" not in _out("api_key: abcDEF123456ghi", native, disable=["codes"])
    # Un mot sans chiffre n'est pas un jeton / a word without a digit is not a token.
    assert _out("secret: professionnel", native) == "secret: professionnel"
