"""Trois modes du filtre 1.0.2 (docs/REGLES.md « Modes ») : fort, essentiel, personnalise, dans les deux moteurs.

Three filter modes (fort, essentiel, personnalise), in both engines. Données fictives seulement / fictitious data only.
"""

from __future__ import annotations

import pytest

from gdprguardian import Anonymizer, _native
from gdprguardian.categories import CATEGORIES, ESSENTIEL_OFF, functional_mailbox, personal_label_before, resolve_mode
from gdprguardian.engine import Settings

_ENGINES = [pytest.param(True, id="rust", marks=pytest.mark.skipif(not _native.available(),
                                                                    reason="noyau Rust absent / no Rust core")),
            pytest.param(False, id="python")]


def _nir() -> str:
    body = "1850575123456"
    return f"{body[0]} {body[1:3]} {body[3:5]} {body[5:7]} {body[7:10]} {body[10:13]} {97 - int(body) % 97:02d}"


# Formes de surface du pack d'évaluation du propriétaire (fictives) / the owner's pack surface forms (fictitious).
PACK = ("La personne concernée se nomme Sohan Clairclaire, née le 2010-01-01. Son email est "
        "sohan.clairclaire00@example.invalid et son téléphone est 06 39 98 00 11. La fiche de contact porte le "
        "pseudonyme s.clairclaire_000. Le compte client est CLT-000001-Q, et la référence RH éventuelle est "
        "EMP-100101.\nJ'ai ajouté une note de suivi à CLT-000001-Q.\nLe cookie de test est cookie-demo-00001-00000, "
        "et le gabarit biométrique est BIO-DEMO-000007 (référence vocale distincte : VOICE-TEST-00001).\n"
        "Une note tronquée ne conserve que la fin du numéro : 00 11.\n"
        "Le produit traité est SKU-ALPHA-0042; la référence du lot est BATCH-OPS-2026-042. Pour une question "
        "générale, l'équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel "
        "fictif est Atelier Exemple Fonctionnel SAS.\n"
        "| Client | CLT-000001-Q |\n| Incident | INC-2026-00017 |\n"
        "Suivez @awa.m sur le réseau ; le numéro 98765432 figure aussi ; dossier 696936 ouvert. Le véhicule "
        "mentionné est ZZ-000-ZZ.\n"
        "Mot de passe : Tigre!2024x\n")
PERSONAL = ("Sohan", "Clairclaire", "2010-01-01", "sohan.clairclaire00@example.invalid", "06 39 98 00 11",
            "s.clairclaire_000", "CLT-000001-Q", "EMP-100101", "cookie-demo-00001-00000", "BIO-DEMO-000007",
            "VOICE-TEST-00001", "INC-2026-00017", "696936", "ZZ-000-ZZ", "Tigre!2024x")
STRONG_ONLY = ("SKU-ALPHA-0042", "BATCH-OPS-2026-042", "support@atelier-exemple.invalid", "@awa.m", "98765432",
               "numéro : 00 11")


def _out(text: str, native: bool, **settings) -> str:
    return Anonymizer(countries=("FR",), native=native, **settings).anonymize(text).text


# --- Résolution du mode / mode resolution ---------------------------------------------------------------------------

@pytest.mark.parametrize("given, expected", [
    ({}, ("fort", ())), ({"mode": "strong"}, ("fort", ())), ({"mode": "Fort"}, ("fort", ())),
    ({"mode": "essentiel"}, ("essentiel", ())), ({"mode": "essential"}, ("essentiel", ())),
    ({"mode": "basique"}, ("essentiel", ())), ({"mode": "basic"}, ("essentiel", ())),
    ({"mode": "custom"}, ("personnalise", ())), ({"mode": "personnalisé"}, ("personnalise", ())),
    ({"disable": "codes"}, ("personnalise", ("codes",))),
    ({"disable": ["functional_mailboxes", "codes"]}, ("personnalise", ("boites_fonctionnelles", "codes"))),
    ({"mode": "custom", "disable": "long_numbers, Phone-Fragments"}, ("personnalise", ("fragments", "nombres_longs"))),
    # `profile` déprécié / deprecated `profile`.
    ({"profile": "strict"}, ("fort", ())), ({"profile": "standard"}, ("essentiel", ())),
    ({"profile": "fast"}, ("essentiel", ())), ({"profile": "strict", "mode": "strong"}, ("fort", ())),
])
def test_mode_resolution(given, expected):
    assert resolve_mode(given.get("mode"), given.get("profile"), given.get("disable")) == expected
    settings = Anonymizer(countries=("FR",), **given).settings
    assert (settings.mode, settings.disable) == expected


@pytest.mark.parametrize("given, message", [
    ({"mode": "turbo"}, "unknown mode"), ({"mode": "fort", "disable": "codes"}, "personnalise"),
    ({"mode": "essentiel", "disable": ["codes"]}, "personnalise"), ({"disable": "nimporte"}, "unknown category"),
    ({"profile": "strict", "mode": "essentiel"}, "contradicts"), ({"profile": "paranoid"}, "profile"),
])
def test_mode_errors_are_clear(given, message):
    with pytest.raises(ValueError, match=message):
        Anonymizer(countries=("FR",), **given)


def test_unknown_category_lists_every_name():
    with pytest.raises(ValueError) as error:
        resolve_mode(None, None, ["nimporte"])
    for category in CATEGORIES:
        if category.name == "secrets":  # jamais coupée, donc hors de la liste / never disabled, so not listed
            continue
        assert category.name in str(error.value) and category.alias in str(error.value)


def test_settings_default_is_fort():
    assert Anonymizer(Settings()).settings.mode == "fort"
    assert ESSENTIEL_OFF == ("boites_fonctionnelles", "fragments", "codes", "nombres_longs")


# --- Les trois modes sur les formes du pack / the three modes on the pack's forms -------------------------------------

@pytest.mark.parametrize("native", _ENGINES)
def test_fort_masks_everything(native):
    out = _out(PACK, native)
    for value in (*PERSONAL, *STRONG_ONLY):
        assert value not in out, value
    assert "Atelier Exemple Fonctionnel SAS" in out


@pytest.mark.parametrize("native", _ENGINES)
@pytest.mark.parametrize("mode", ["essentiel", "essential", "basique"])
def test_essentiel_keeps_what_no_label_proves(native, mode):
    out = _out(PACK, native, mode=mode)
    for value in PERSONAL:
        assert value not in out, value  # libellé, format ou propagation / label, format or propagation
    for value in STRONG_ONLY:
        assert value in out, value
    assert "Atelier Exemple Fonctionnel SAS" in out


@pytest.mark.parametrize("native", _ENGINES)
def test_personnalise_codes_and_mailboxes(native):
    out = _out(PACK, native, mode="personnalise", disable=["codes", "boites_fonctionnelles"])
    for value in ("SKU-ALPHA-0042", "BATCH-OPS-2026-042", "support@atelier-exemple.invalid"):
        assert value in out, value
    # Un code annoncé par un libellé personnel reste un identifiant annoncé / an announced code stays masked.
    for value in ("sohan.clairclaire00@example.invalid", "06 39 98 00 11", "98765432", "Tigre!2024x", "Clairclaire",
                  "CLT-000001-Q", "EMP-100101", "INC-2026-00017", "ZZ-000-ZZ", "numéro : 00 11", "@awa.m"):
        assert value not in out, value


# Une valeur par catégorie : masquée en fort, en clair quand sa catégorie est coupée.
# One value per category: masked in fort, in clear when its category is switched off.
SAMPLES = {
    "personnes": ("Rendez-vous avec Mme Claire Fontanel demain.", "Fontanel"),
    "emails": ("Écrire à jean.fontanel@example.fr aujourd'hui.", "jean.fontanel@example.fr"),
    "boites_fonctionnelles": ("Écrire à contact@atelier-exemple.invalid demain.", "contact@atelier-exemple.invalid"),
    "telephones": ("Son téléphone est 06 39 98 00 11.", "06 39 98 00 11"),
    "fragments": ("Son téléphone est 06 39 98 00 11. Une note tronquée ne conserve que la fin du numéro : 00 11.",
                  "numéro : 00 11"),
    "adresses": ("Il habite 12 rue des Lilas, 75011 Paris.", "rue des Lilas"),
    "dates_naissance": ("Mme Claire Fontanel, née le 12/03/1985, est arrivée.", "12/03/1985"),
    "iban": ("IBAN : FR76 3000 6000 0112 3456 7890 189", "FR76 3000 6000 0112 3456 7890 189"),
    "cartes": ("Carte bancaire : 4242 4242 4242 4242", "4242 4242 4242 4242"),
    "numeros_nationaux": (f"Numéro de sécurité sociale : {_nir()}", _nir()),
    "ip": ("Connexion depuis 192.0.2.1 hier.", "192.0.2.1"),
    "identifiants_techniques": ("Le poste porte l'identifiant 12345678-1234-4000-a000-0123456789ab.",
                                "12345678-1234-4000-a000-0123456789ab"),
    "codes": ("Le produit traité est SKU-ALPHA-0042.", "SKU-ALPHA-0042"),
    "nombres_longs": ("Le chiffre 98765432 figure en clair.", "98765432"),
    "plaques": ("Le véhicule immatriculé AB-123-CD est garé.", "AB-123-CD"),
    "pseudonymes": ("La fiche porte le pseudonyme s.clairclaire_000.", "s.clairclaire_000"),
    "secrets": ("Mot de passe : Tigre!2024x", "Tigre!2024x"),
}


def test_every_category_has_a_sample():
    assert set(SAMPLES) == {c.name for c in CATEGORIES}


@pytest.mark.parametrize("native", _ENGINES)
@pytest.mark.parametrize("category", [c for c in SAMPLES if c != "secrets"])
def test_disable_each_category(native, category):
    text, value = SAMPLES[category]
    assert value not in _out(text, native), "masqué en fort / masked in fort"
    alias = next(c.alias for c in CATEGORIES if c.name == category)
    anonymizer = Anonymizer(countries=("FR",), native=native, disable=[alias])
    result = anonymizer.anonymize(text)
    assert value in result.text
    assert result.report["mode"] == "personnalise" and result.report["disable"] == [category]
    assert any(category in warning for warning in result.report["warnings"])
    if category == "personnes":
        assert any("not anonymised" in warning for warning in result.report["warnings"])


@pytest.mark.parametrize("name", ["secrets", "Secrets", "secrets,codes"])
def test_secrets_can_never_be_disabled(name):
    """Étude de l'état de l'art (26/10) : un mot de passe ou une clé divulgués ne sont jamais acceptables."""
    with pytest.raises(ValueError, match="never be disabled"):
        Anonymizer(countries=("FR",), disable=name)
    text, value = SAMPLES["secrets"]
    assert value not in _out(text, False, disable=["codes"])


# --- Règles de l'organisation dans tous les modes / the organisation's rules in every mode ----------------------------

KEEP = {"rules": [{"label": "SKU", "pattern": "SKU-[0-9]{6}", "action": "keep"}]}
MASK = {"rules": [{"label": "PROJET", "pattern": "PRJ-[0-9]{3}", "action": "mask"}]}


@pytest.mark.parametrize("native", _ENGINES)
@pytest.mark.parametrize("modes", [{}, {"mode": "essentiel"}, {"disable": ["codes"]}, {"disable": ["personnes"]}])
def test_keep_and_mask_rules_apply_in_every_mode(native, modes):
    text = "Article SKU-123456 pour le compte client CLT-204518, projet PRJ-123."
    out = _out(text, native, rules=KEEP, **modes)
    assert "SKU-123456" in out
    assert "CLT-204518" not in out  # libellé « compte client » / "compte client" label
    assert "PRJ-123" not in _out(text, native, rules=MASK, **modes)


@pytest.mark.parametrize("native", _ENGINES)
@pytest.mark.parametrize("modes", [{}, {"mode": "essentiel"}])
def test_allow_list_applies_in_every_mode(native, modes):
    text = "Écrire à jean.fontanel@example.fr."
    assert "jean.fontanel@example.fr" in _out(text, native, rules={"allow": ["jean.fontanel@example.fr"]}, **modes)


# --- Rapport et explain / report and explain --------------------------------------------------------------------------

@pytest.mark.parametrize("native", _ENGINES)
def test_report_and_explain_name_the_mode(native):
    fort = Anonymizer(countries=("FR",), native=native).anonymize(PACK).report
    assert (fort["mode"], fort["disable"]) == ("fort", [])
    assert "left_in_clear_by_mode" not in fort and not any("Mode" in w for w in fort.get("warnings", []))
    report = Anonymizer(countries=("FR",), native=native, mode="essentiel", explain=True).anonymize(PACK).report
    assert report["mode"] == "essentiel"
    assert set(report["left_in_clear_by_mode"]) <= set(ESSENTIEL_OFF) | {"pseudonymes"}
    assert report["left_in_clear_by_mode"]["codes"] >= 2
    assert any(w.startswith("Mode essentiel") for w in report["warnings"])
    lines = [line for line in report["explain"] if "left_in_clear" in line]
    assert {line["reason"] for line in lines} == {"mode_essentiel"}
    assert {"ID_CODE", "ID_LONG_NUMBER", "FR_PHONE_FRAGMENT", "HANDLE"} <= {line["rule"] for line in lines}
    assert all("SKU" not in str(line) for line in lines)  # jamais la valeur / never the value


@pytest.mark.parametrize("mode", [{}, {"mode": "essentiel"}, {"disable": ["codes", "boites_fonctionnelles"]},
                                  {"disable": ["personnes"]}])
def test_engines_identical_per_mode(mode):
    if not _native.available():
        pytest.skip("noyau Rust absent / no Rust core")
    native = Anonymizer(countries=("FR",), native=True, explain=True, **mode).anonymize(PACK)
    python = Anonymizer(countries=("FR",), native=False, explain=True, **mode).anonymize(PACK)
    assert native.text == python.text
    assert native.report["explain"] == python.report["explain"]


def test_segments_follow_the_mode():
    anonymizer = Anonymizer(countries=("FR",), mode="essentiel")
    scope = anonymizer.new_scope()
    outputs, report = anonymizer.anonymize_segments(["SKU-ALPHA-0042", "compte client CLT-000001-Q"], scope)
    scope.close()
    assert outputs[0] == "SKU-ALPHA-0042" and "CLT-000001-Q" not in outputs[1]
    assert report["mode"] == "essentiel"


# --- Ligne de commande / command line -------------------------------------------------------------------------------

@pytest.mark.parametrize("argv, code, mode, sku_kept", [
    ([], 0, "fort", False), (["--mode", "essentiel"], 0, "essentiel", True),
    (["--mode", "basic"], 0, "essentiel", True), (["--disable", "codes"], 0, "personnalise", True),
    (["--profile", "strict"], 0, "fort", False),
    (["--mode", "fort", "--disable", "codes"], 2, None, None), (["--mode", "turbo"], 2, None, None),
])
def test_cli_mode_and_disable(monkeypatch, capsysbinary, argv, code, mode, sku_kept):
    import io
    import json
    import sys

    from gdprguardian import cli

    text = "Le produit traité est SKU-ALPHA-0042 ; compte client CLT-000001-Q."
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(text.encode("utf-8"))))
    assert cli.main(["anonymize", "-", "--format", "json", *argv]) == code
    out, err = capsysbinary.readouterr()
    if code:
        assert b"mode" in err
        return
    payload = json.loads(out)
    assert payload["report"]["mode"] == mode
    assert ("SKU-ALPHA-0042" in payload["text"]) is sku_kept and "CLT-000001-Q" not in payload["text"]


# --- Aides / helpers ------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("surface, expected", [
    ("support@atelier-exemple.invalid", True), ("rh@exemple.fr", True), ("contact.paris@exemple.fr", True),
    ("no-reply@exemple.fr", True), ("cse.morez@exemple.fr", True), ("jean.dupont@exemple.fr", False),
    ("sohan.clairclaire00@example.invalid", False), ("info [at] exemple.fr", True),
])
def test_functional_mailbox(surface, expected):
    assert functional_mailbox(surface) is expected


@pytest.mark.parametrize("before, expected", [
    ("Le compte client est ", True), ("| Client | ", True), ("dossier fictif ", True), ("identifiant ", True),
    ("référence vocale distincte : ", True), ("le cookie de test est ", True), ("Le produit traité est ", False),
    ("| Référence catalogue non personnelle | ", False), ("la référence du lot est ", False),
    ("le client a appelé. Puis ", False),
])
def test_personal_label_before(before, expected):
    assert personal_label_before(before + "CODE-123456", len(before)) is expected
