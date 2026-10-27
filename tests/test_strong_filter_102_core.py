"""Filtre fort 1.0.2, voie « cœur » : propagation universelle des valeurs, fin de phrase après un courriel, boîtes
fonctionnelles masquées.

Strong filter 1.0.2, "core" lane: universal value propagation, end of sentence after an e-mail, functional mailboxes
masked. Chaque cas tourne sur le noyau Rust (s'il est installé) et sur la référence Python, qui doivent rendre le même
texte. Every case runs on the Rust core (when installed) and on the Python reference, which must render the same
text. Données fictives / fictitious data.
"""

from __future__ import annotations

import json
import re

import pytest

from gdprguardian import Anonymizer, _native, _text

_ENGINES = [pytest.param(True, id="rust", marks=pytest.mark.skipif(not _native.available(),
                                                                    reason="noyau Rust absent / no Rust core")),
            pytest.param(False, id="python")]
_TAG_RE = re.compile(r"\[[A-Z_]+_\d+\]")


@pytest.fixture(scope="module", params=_ENGINES)
def engine(request) -> Anonymizer:
    anonymizer = Anonymizer(countries=("FR",), native=request.param)
    assert anonymizer.native == request.param
    return anonymizer


@pytest.fixture(scope="module", params=_ENGINES)
def explaining(request) -> Anonymizer:
    return Anonymizer(countries=("FR",), native=request.param, explain=True)


def _masked(engine: Anonymizer, text: str) -> str:
    return engine.anonymize(text).text


def _tags(out: str, prefix: str) -> set[str]:
    return {tag for tag in _TAG_RE.findall(out) if tag.startswith(f"[{prefix}_")}


# --- Point 9 : fin de phrase après un courriel / end of sentence after an e-mail ------------------------------------


def test_email_ending_a_sentence_keeps_its_line_break(engine):
    out = _masked(engine, "Contact : l.ndiaye@exemple.fr.\nIBAN FR76 3000 6000 0112 3456 7890 189")
    assert out == "Contact : [EMAIL_1].\nIBAN [IBAN_1]", out


@pytest.mark.parametrize("text", [
    "Contact : l.ndiaye@exemple.fr.\nIBAN FR76 3000 6000 0112 3456 7890 189",   # courriel complet à gauche
    "Fin de la note.\nJean@exemple.fr répondra.",                               # pas de courriel à gauche
])
def test_full_stop_then_capital_is_never_joined(text):
    norm, _, _ = _text.prepare(text, native=False)
    assert "\n" in norm, norm


@pytest.mark.parametrize("text, joined", [
    ("x jean.du\npont@exemple.fr y", "jean.dupont@exemple.fr"),
    ("x jean@sous.exemple.\nfr y", "jean@sous.exemple.fr"),   # minuscule après le point : recollé / joined
])
def test_wrapped_email_is_still_joined(text, joined):
    norm, _, _ = _text.prepare(text, native=False)
    assert joined in norm, norm


@pytest.mark.parametrize("box", ["support", "contact", "noreply"])
def test_functional_mailboxes_stay_masked(engine, box):
    out = _masked(engine, f"Écrire à {box}@exemple-fictif.fr pour toute question.")
    assert f"{box}@" not in out and "[EMAIL_1]" in out, out


# --- Point 1 : propagation universelle des valeurs / universal value propagation -----------------------------------


def test_name_variants_share_one_tag(engine):
    out = _masked(engine, "Client : Mme Sohan Kervadec. Plus tard, sohan Kervadec a rappelé ; sohan kervadec et "
                          "Sohan KERVADEC aussi.")
    assert "sohan" not in out.lower() and "kervadec" not in out.lower(), out
    assert _tags(out, "PERSONNE") == {"[PERSONNE_1]"}, out


def test_code_variants_share_one_tag(engine):
    out = _masked(engine, "N° client : CLT-204518. Rappel : le dossier clt204518 et CLT 204518 sont les mêmes.")
    assert "204518" not in out, out
    assert _tags(out, "IDENTIFIANT") == {"[IDENTIFIANT_1]"}, out


def test_birth_date_found_far_from_its_cue_by_propagation(explaining):
    text = "Mme Lise Garnier, née le 12/03/1985.\n\n" + "Ligne neutre de remplissage.\n" * 30 + "Annexe 1985-03-12."
    result = explaining.anonymize(text)
    assert "1985" not in result.text, result.text
    assert any(line["reason"] == "propagation" and line["tag"] == "[DATE_NAISSANCE_1]"
               for line in result.report["explain"]), result.report["explain"]


def test_many_identifiers_propagate_through_the_automaton(engine):
    # Plus de 8 clés : automate (chevauchements compris), même résultat qu'une recherche par clé.
    # More than 8 keys: automaton (overlaps included), same result as one search per key.
    ids = [f"{100000000 + 7919 * k:09d}" for k in range(12)]
    text = "".join(f"Dossier {i} ouvert.\n" for i in ids) + "".join(f"Relance {i[:3]} {i[3:6]} {i[6:]}.\n"
                                                                     for i in ids)
    out = _masked(engine, text)
    lines = out.splitlines()
    for k in range(12):
        assert lines[k].split()[1] == lines[12 + k].split()[1].rstrip("."), out


def test_birth_date_forms_share_one_tag(engine):
    out = _masked(engine, "Patiente née le 12 mars 1985.\nTableau : 12/03/1985 ; format ISO 1985-03-12 ; "
                          "autre 12.03.1985.")
    assert "1985" not in out, out
    assert _tags(out, "DATE_NAISSANCE") == {"[DATE_NAISSANCE_1]"}, out


def test_phone_forms_share_one_tag(engine):
    out = _masked(engine, "Tél. : 06 12 34 56 78. Autres écritures : +33 (0)6 12 34 56 78, 0033612345678 et "
                          "06.12.34.56.78.")
    assert "12 34" not in out and "612345678" not in out and "34.56" not in out, out
    assert _tags(out, "TEL") == {"[TEL_1]"}, out


@pytest.mark.parametrize("text, kept", [
    ("M. Blanc a commandé du vin blanc.", "vin blanc"),                               # nom d'un mot : pas replié
    ("Réf. 10612345678 ; tél. 06 12 34 56 78.", "Réf. [IDENTIFIANT_1] ;"),           # 9 chiffres dans une suite :
    # la suite reste sa propre valeur (ID_LONG_NUMBER), jamais le téléphone / the run keeps its own value, never TEL.
    ("IBAN FR76 3000 6000 0112 3456 7890 189, montant 3000 6000 euros.", "3000 6000 euros"),  # morceau d'IBAN
    ("Mme Lise Garnier, 29200 Brest. Code 29200 du lot.", "Code 29200 du lot"),       # code postal jamais propagé
])
def test_value_propagation_negatives(engine, text, kept):
    out = _masked(engine, text)
    assert kept in out, out


# --- Point 6 (c) : signature en minuscules / lowercase signature ----------------------------------------------------


@pytest.mark.parametrize("signature", ["noé", "garnier", "noé garnier"])
def test_lowercase_signature_of_a_named_person_gets_its_tag(explaining, signature):
    text = f"Bonjour,\nM. Noé Garnier a confirmé le rendez-vous.\nCordialement,\n{signature}\n"
    result = explaining.anonymize(text)
    assert result.text.splitlines()[-1] == "[PERSONNE_1]", result.text
    # Deux mots : la propagation des noms repliés passe d'abord / two words: folded name propagation comes first.
    expected = "propagation" if " " in signature else "signature"
    assert any(line["reason"] == expected for line in result.report["explain"]), result.report["explain"]


def test_last_line_signature(engine):
    out = _masked(engine, "Mme Alix Morvan,\nvoici le dossier demandé.\nalix")
    assert out.splitlines()[-1] == "[PERSONNE_1]", out


@pytest.mark.parametrize("text", [
    "Cordialement,\nL'équipe support",                                  # pas en minuscules / not lowercase
    "M. Pierre Garnier viendra.\nJ'ai vu pierre et marie hier au marché.\nBonne soirée",   # prose, pas signature
    "Mme Lise Garnier et M. Paul Garnier.\nCordialement,\ngarnier",      # deux personnes : ambigu / two persons
])
def test_signature_rule_negatives(engine, text):
    out = _masked(engine, text)
    assert out.splitlines()[-1] == text.splitlines()[-1] or "[PERSONNE" not in out.splitlines()[-1], out


# --- Point 6 (d) : initiales après un indice / initials after a cue -------------------------------------------------


@pytest.mark.parametrize("text, secret", [
    ("Note rédigée par NB le 3 mars.", "NB"),
    ("Compte rendu établi par : F.L.", "F.L"),
    ("Visa : R. G.", "R. G"),
    ("Document validé par JMD.", "JMD"),
])
def test_initials_after_a_cue_are_masked(explaining, text, secret):
    result = explaining.anonymize(text)
    assert secret not in result.text and "[PERSONNE_1]" in result.text, result.text
    assert any(line["reason"] == "initials_after_cue" for line in result.report["explain"]), result.report["explain"]


@pytest.mark.parametrize("text", [
    "Note rédigée par la DRH.",
    "Dossier validé par RH puis par le DSI.",
    "Paiement par carte, visa CB accepté.",
    "Rédigé par Jean, relu par l'équipe.",
])
def test_initials_negatives(engine, text):
    assert "[PERSONNE" not in _masked(engine, text) or "Jean" in text, _masked(engine, text)


# --- Point 4 (b) : tableaux CSV et TSV / CSV and TSV tables ---------------------------------------------------------


@pytest.mark.parametrize("sep", [";", "\t", ","])
def test_delimited_table_header_masks_its_columns(engine, sep):
    rows = [["id", "nom", "prenom", "date_naissance", "tel"],
            ["1", "Kervadec", "Sohan", "16-04-1981", "06 12 34 56 78"],
            ["2", "Garnier", "Lise", "16.09.1965", "06 98 76 54 32"],
            ["3", "Morvan", "Yann", "21/02/1972", "07 11 22 33 44"]]
    text = "Export du CRM :\n" + "\n".join(sep.join(row) for row in rows) + "\n"
    out = _masked(engine, text)
    for secret in ("Kervadec", "Sohan", "Garnier", "Lise", "Morvan", "Yann", "1981", "1965", "1972", "12 34"):
        assert secret not in out, out
    assert out.splitlines()[1] == sep.join(rows[0]), out          # l'en-tête reste / the header stays
    # Chaque ligne garde ses colonnes (une cellule, une balise) / every row keeps its columns (one cell, one tag).
    assert all(line.count(sep) == 4 for line in out.splitlines()[1:]), out
    assert len(set(out.splitlines()[2].split(sep)[1:3])) == 1, out   # nom et prénom : une personne / one person


def test_delimited_tables_follow_the_rules():
    text = "x\nid;nom;date_naissance\n1;A;2\n2;B;3\n\nfin, et, plus\n"
    tables = _text.delimited_tables(text)
    assert len(tables) == 1 and len(tables[0]) == 3
    a, b = tables[0][0][2]
    assert text[a:b] == "date_naissance"
    assert _text.delimited_tables("a;b1;c\n1;2;3\n4;5;6") == []          # chiffre dans l'en-tête / digit in header
    assert _text.delimited_tables("a;b;c\n1;2;3\n4;5\n") == []           # une seule ligne de même forme / one row
    assert _text.delimited_tables("Bonjour, merci, à bientôt.\nIl pleut, il vente, il neige.\nOui, non.\n") == []


def test_prose_with_commas_is_unchanged(engine):
    text = "Bonjour, merci, à bientôt.\nIl pleut, il vente, il neige.\nOui, non, peut-être.\n"
    assert _masked(engine, text) == text


def test_propagation_is_idempotent(engine):
    text = ("N° client : CLT-204518, Mme Sohan Kervadec, née le 12/03/1985, tél. 06 12 34 56 78.\n"
            "Relance : sohan kervadec (clt204518), 1985-03-12, +33 6 12 34 56 78.")
    once = _masked(engine, text)
    assert _masked(engine, once) == once


def test_explain_names_propagation_without_values(explaining):
    text = ("Mme Sohan Kervadec, née le 12/03/1985, n° client : CLT-204518.\nRelance : sohan kervadec, "
            "dossier du 1985-03-12, rappel clt204518, tél. 06 12 34 56 78, soit 0612345678.")
    result = explaining.anonymize(text)
    lines = result.report["explain"]
    # « sohan kervadec » : prénom + nom en minuscules, trouvé directement depuis la jonction 1.0.2 (raison
    # name_lexicon), même balise ; sinon par propagation. Found directly by the lowercase-pair rule, same tag.
    assert result.text.count("[PERSONNE_1]") == 2, result.text
    assert any(line["reason"] in ("propagation", "name_lexicon") and line["tag"] == "[PERSONNE_1]"
               for line in lines), lines
    dump = json.dumps(result.report, ensure_ascii=False)
    for secret in ("204518", "clt204518", "0612345678", "12 34 56", "1985", "ervadec"):
        assert secret not in dump
