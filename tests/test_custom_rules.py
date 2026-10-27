"""Règles personnalisées et explication / custom rule sets and explanations."""

from __future__ import annotations

import time

import pytest

from gdprguardian import Anonymizer, _native
from gdprguardian._text import fold
from gdprguardian.custom import MAX_RULES, RuleError, load_rules, parse_rules
from gdprguardian.labels import LABELS

NIR = "1 85 05 78 006 084 91"
ACME = {
    "name": "acme",
    "rules": [
        {"label": "CLIENT_ID", "pattern": "CLT-[0-9]{6}"},
        {"label": "COMMANDE", "pattern": "[0-9]{6}", "action": "keep", "context": ["commande"]},
    ],
    "deny": {"PROJET": ["Opération Phénix"]},
    "allow": ["support@acme.fr"],
}


def test_mask_keep_deny_and_allow():
    a = Anonymizer(countries="FR", rules=ACME)
    text = "Client CLT-204518, commande 152000, Opération Phénix ; écrire à support@acme.fr ou a@b.fr."
    assert a.anonymize(text).text == ("Client [CLIENT_ID_1], commande 152000, [PROJET_1] ; écrire à "
                                      "support@acme.fr ou [EMAIL_1].")


def test_keep_zone_never_unmasks_a_detection_that_sticks_out():
    # « 204518 » est gardé par la règle, mais « CLT-204518 » déborde : il reste masqué (rappel d'abord).
    # "204518" is kept by the rule, but "CLT-204518" sticks out: it stays masked (recall first).
    rules = {**ACME, "rules": [*ACME["rules"][:1], {"label": "COMMANDE", "pattern": "[0-9]{6}", "action": "keep"}]}
    assert Anonymizer(countries="FR", rules=rules).anonymize("Client CLT-204518.").text == "Client [CLIENT_ID_1]."


def test_keep_rule_unmasks_ordinary_detections_but_never_a_validated_identifier():
    rules = {"rules": [{"label": "REF", "pattern": "[0-9 ]{10,24}", "action": "keep", "whole_word": False}]}
    a = Anonymizer(countries="FR", rules=rules)
    # Un téléphone peut être conservé par choix ; un NIR validé par sa clé, jamais.
    # A phone may be kept by choice; a NIR validated by its key, never.
    assert "06 12 34 56 78" in a.anonymize("Réf 06 12 34 56 78").text
    assert NIR not in a.anonymize(f"Réf {NIR}").text


def test_context_words_gate_a_rule():
    rules = {"rules": [{"label": "DOSSIER", "pattern": "[A-Z]{2}[0-9]{5}", "context": ["dossier"]}]}
    a = Anonymizer(countries="FR", rules=rules)
    assert a.anonymize("Dossier AB12345 ouvert.").text == "Dossier [DOSSIER_1] ouvert."
    # Sans son mot de contexte la règle se tait ; depuis 1.0.2 la règle des codes masque le code, en identifiant
    # générique. Without its context word the rule stays off; since 1.0.2 the code rule masks it generically.
    assert a.anonymize("Modèle AB12345 en stock.").text == "Modèle [IDENTIFIANT_1] en stock."


def test_explain_gives_rule_and_reason_never_the_value():
    a = Anonymizer(countries="FR", rules=ACME, explain=True)
    report = a.anonymize(f"M. Jean Dupont, NIR {NIR}, client CLT-204518. Jean Dupont rappellera.").report
    lines = {(line.get("tag") or line.get("kept"), line["rule"], line["reason"]) for line in report["explain"]}
    assert ("[NIR_1]", "FR_NIR", "validated") in lines
    assert ("[CLIENT_ID_1]", "CUSTOM_1_CLIENT_ID", "custom_rule") in lines
    assert any(tag == "[PERSONNE_1]" and reason in ("name_lexicon", "propagation") for tag, _, reason in lines)
    assert "Dupont" not in repr(report) and "204518" not in repr(report)
    assert report["rules"] == "acme"


@pytest.mark.skipif(not _native.available(), reason="noyau Rust requis / Rust core required")
def test_untrusted_rules_run_in_linear_time():
    # Motif catastrophique pour un moteur à retour arrière : linéaire ici / catastrophic with backtracking.
    rules = parse_rules({"rules": [{"label": "X", "pattern": "(a+)+$", "whole_word": False}]}, trusted=False)
    a = Anonymizer(countries="FR", rules=rules)
    started = time.perf_counter()
    a.anonymize("a" * 50_000 + "!")
    assert time.perf_counter() - started < 2.0


@pytest.mark.skipif(not _native.available(), reason="noyau Rust requis / Rust core required")
def test_untrusted_rules_refuse_backtracking_constructs():
    # Look-behind après une répétition : hors des formes exactes du moteur linéaire (en tête, il est accepté).
    # Look-behind after a repetition: outside the linear engine's exact forms (at the start, it is accepted).
    for pattern in ("a+(?<=x)bc", "(a)\\1"):
        rules = parse_rules({"rules": [{"label": "X", "pattern": pattern}]}, trusted=False)
        with pytest.raises(RuleError, match=r"linéaire|linear"):
            Anonymizer(countries="FR", rules=rules)


@pytest.mark.parametrize(("data", "message"), [
    ({"rules": [{"label": "x", "pattern": "a"}]}, "MAJUSCULES"),
    ({"rules": [{"label": "X", "pattern": ""}]}, "motif"),
    ({"rules": [{"label": "X", "pattern": "a" * 501}]}, "motif"),
    ({"rules": [{"label": "X", "pattern": "a", "action": "drop"}]}, "action"),
    ({"rules": [{"label": "X", "pattern": "a", "colour": "red"}]}, "inconnues"),
    ({"rules": [{"label": "X", "pattern": "a"}] * (MAX_RULES + 1)}, "au plus"),
    ({"rules": [{"label": "X", "pattern": "("}]}, "invalide"),
    ({"deny": {"projet": ["x"]}}, "MAJUSCULES"),
    ({"allow": ["x" * 65]}, "termes"),
    ({"surprise": 1}, "inconnues"),
])
def test_rule_sets_are_strictly_validated(data, message):
    with pytest.raises(RuleError, match=message):
        Anonymizer(countries="FR", rules=parse_rules(data, trusted=True))


def test_rules_from_a_toml_file(tmp_path):
    path = tmp_path / "acme.toml"
    path.write_text('name = "acme"\n[[rule]]\nlabel = "CLIENT_ID"\npattern = "CLT-[0-9]{6}"\n'
                    '[deny]\nPROJET = ["Opération Phénix"]\n', encoding="utf-8")
    a = Anonymizer(countries="FR", rules=str(path))
    assert a.anonymize("CLT-204518, Opération Phénix").text == "[CLIENT_ID_1], [PROJET_1]"
    assert load_rules(path).name == "acme"


def test_custom_labels_leave_no_global_state():
    # Un libellé d'une requête ne doit pas survivre dans le registre partagé / no shared-registry residue.
    Anonymizer(countries="FR", rules={"rules": [{"label": "CLIENT_DUPONT", "pattern": "X[0-9]{4}"}]}).anonymize("X1234")
    assert "CLIENT_DUPONT" not in LABELS


def test_rules_respect_segments():
    a = Anonymizer(countries="FR", rules=ACME)
    per_cell, _ = a.analyze_segments(["CLT-204518", "rien"])
    assert [s.label for s in per_cell[0]] == ["CLIENT_ID"] and per_cell[1] == []


# --- Compilation bornée des règles non sûres / bounded compile of untrusted rules ---------------------------------

def _set(patterns: list[str], **extra: object) -> dict:
    return {"rules": [{"label": f"R{i}", "pattern": pattern, **extra} for i, pattern in enumerate(patterns)]}


# Jeux hostiles des revues (20 règles, 500 caractères au plus) : autrefois 0,4 à 1,8 Go et plusieurs secondes.
# The reviews' hostile sets (20 rules, 500 characters at most): formerly 0.4-1.8 GB and several seconds.
HOSTILE = {
    "w600_b": [r"\b\w{600}"] * 20,
    "w700_b": [r"\b\w{700}"] * 20,
    "la_pos": [r"[A-Z]{2}(?=\w{500})"] * 20,
    "neg_products": [r"\b\w{200}(?!(?:[\w\-]\W|\s[\d\.]|[\d\s]\w){3}(?:\W\w|\w\s){2})"] * 20,
    "p9": [r"x(?!(?:\w\W|\W\w){9})"] * 20,
    "f14lb": [r"(?<![x])\w(?:\w{40}){14}"] * 20,
    "opt32": ["\\w?" * 31 + r"\b\w{300}"] * 20,
    "nested": [r"\b(?:\w{40}\W{40}){40}"] * 20,
}


@pytest.mark.skipif(not _native.available(), reason="noyau Rust requis / Rust core required")
@pytest.mark.parametrize("name", HOSTILE)
def test_hostile_untrusted_rule_sets_are_refused_quickly(name):
    rules = parse_rules(_set(HOSTILE[name]), trusted=False)
    started = time.perf_counter()
    with pytest.raises(RuleError, match="construction refusée par le moteur linéaire / refused by the linear-time "
                                        "engine"):
        Anonymizer(countries="FR", rules=rules)
    assert time.perf_counter() - started < 10


@pytest.mark.skipif(not _native.available(), reason="noyau Rust requis / Rust core required")
def test_realistic_untrusted_rules_stay_far_below_the_bounds():
    patterns = [r"CLT-[0-9]{6}", r"\bCLT-\d{4,6}\b", r"(?<![A-Z])DOS[0-9]{3}(?![0-9])", r"[A-Z]{2}[0-9]{5}",
                r"\b[A-Z][a-z]+-\d{2,4}\b", r"dossier\s?n°\s?\d{3,8}", r"[\w.+-]+@acme\.fr", r"\b\w{2,12}-\d{3}\b",
                r"XY[0-9]{3}(?=\s|$)", r"[0-9]{4}(?:$|\s)", r"(?<!\d)\d{2}[ .]?\d{2}[ .]?\d{2}(?!\d)",
                r"ref[ :]+[A-Z0-9]{8,12}", r"[A-Z]{3}-\d{4}-[A-Z]{2}", r"\bFR\d{2}[A-Z0-9]{11}\b",
                r"(?i)matricule\s*:?\s*\d{5,7}", r"https?://intranet\.acme\.fr/\S+", r"[A-Z][a-z]+ [A-Z]{2,}(?=,|$)",
                r"\bP\d{6}\b", r"\w+@\w+\.fr", r"(?:projet|opération) [A-Z][a-zé]+\b"]
    rules = parse_rules(_set(patterns), trusted=False)
    started = time.perf_counter()
    native = Anonymizer(countries="FR", rules=rules)
    assert time.perf_counter() - started < 5 and all(native._custom_native.flags)


@pytest.mark.skipif(not _native.available(), reason="noyau Rust requis / Rust core required")
def test_the_untrusted_set_shares_one_memory_budget():
    # Chaque règle tient seule ; vingt ensemble dépassent le budget du jeu : les dernières sont refusées.
    # Each rule fits alone; twenty together exceed the set's budget: the last ones are refused.
    scanner = _native.build(parse_rules(_set([r"\w{40}"] * 20), trusted=False).recognizers(), {}, fold,
                            untrusted=True)
    assert scanner.flags[0] and not scanner.flags[-1]
    assert "budget" in scanner.errors[-1]
    # Mêmes motifs de confiance (fichier local) : bornes inchangées / same trusted patterns: unchanged bounds.
    assert all(_native.build(parse_rules(_set([r"\w{40}"] * 20)).recognizers(), {}, fold).flags)


@pytest.mark.skipif(not _native.available(), reason="noyau Rust requis / Rust core required")
def test_suffixes_copied_for_optional_characters_are_charged():
    # Suffixe d'une branche finale, copié pour chacun des 32 chemins des caractères facultatifs de tête : refusé par
    # le budget de réécriture avant la copie (autrefois une centaine de Mo, puis la limite d'automate). A final
    # branch's suffix, copied for each of the 32 paths of the leading optional characters: refused by the rewrite
    # budget before copying (formerly about 100 MB, then the automaton limit).
    prefix = r"\d?" * 5 + r"(?<![x])y(?:a(?="
    pattern = prefix + r"\w\W" * ((500 - len(prefix) - 4) // 4) + ")|b)"
    scanner = _native.build(parse_rules(_set([pattern]), trusted=False).recognizers(), {}, fold, untrusted=True)
    assert not scanner.flags[0] and "too large to expand" in scanner.errors[0]


@pytest.mark.skipif(not _native.available(), reason="noyau Rust requis / Rust core required")
@pytest.mark.parametrize("pattern", [r"XY[0-9]{3}(?=\s|$)", r"XY[0-9]{3}(?=$)", r"XY[0-9]{3}(?:$|\s)",
                                     r"XY[0-9]{3}(?=[.,;]|$)", r"XY[0-9]{3}(?=\b)", r"XY[0-9]{3}(?!\S)",
                                     r"XY[0-9]{3}(?=\s|\Z)", r"XY[0-9]{3}$"])
def test_documented_trailing_forms_are_accepted_and_exact(pattern):
    data = _set([pattern], whole_word=False)
    native = Anonymizer(countries="FR", rules=parse_rules(data, trusted=False))
    python = Anonymizer(countries="FR", rules=parse_rules(data), native=False)
    for text in ("id XY123", "id XY123\n", "id XY123 ", "id XY123.", "XY123\n\n", "XY1234", "XY123;XY456\n"):
        assert native.anonymize(text).text == python.anonymize(text).text, (pattern, ascii(text))
