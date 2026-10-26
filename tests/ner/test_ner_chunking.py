"""Découpage en phrases, filtre de signaux et fenêtres / sentence splitting, gating and windows."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from gdprguardian._text import fold
from gdprguardian.ner.chunking import has_signal, plan_windows, skip_line, split_units


def units(text: str, segments: list[tuple[int, int]] | None = None) -> list[str]:
    return [text[s:e] for s, e in split_units(text, segments or [(0, len(text))])]


def signal(text: str) -> bool:
    return has_signal(text, fold(text), 0, len(text))


# --- phrases / sentences


def test_sentences_split_on_strong_punctuation():
    assert units("Il pleut. Nous restons ici ! Et toi ? Oui…") == ["Il pleut.", "Nous restons ici !", "Et toi ?",
                                                                  "Oui…"]


def test_abbreviations_and_initials_do_not_split():
    text = "M. Dupont et Mme Durand ont vu J. Martin. Voir art. 12 et Dr. Leroy."
    assert units(text) == ["M. Dupont et Mme Durand ont vu J. Martin.", "Voir art. 12 et Dr. Leroy."]


def test_no_split_before_lowercase_or_inside_numbers():
    assert units("Prix 3.5 euros, etc. puis rien.") == ["Prix 3.5 euros, etc. puis rien."]


def test_lowercase_continuation_line_is_joined():
    text = "Le rapport de Jean\nest prêt et Marie\nDupont le relira."
    assert units(text) == ["Le rapport de Jean\nest prêt et Marie", "Dupont le relira."]


def test_terminated_line_is_not_joined():
    assert units("Merci Paul.\nla suite demain") == ["Merci Paul.", "la suite demain"]


def test_long_unfinished_line_continues_on_next_line():
    line = "Le rapport rédigé par la directrice des ressources humaines, Mme Isabelle"
    assert len(line) >= 50
    assert units(f"{line}\nMarchand, a été validé.") == [f"{line}\nMarchand, a été validé."]
    # Ligne courte (signature, liste) ou puce : pas de jonction / short line or bullet: no join.
    assert units("Cordialement,\nSophie Marchand\nDirectrice") == ["Cordialement,", "Sophie Marchand", "Directrice"]
    assert units(f"{line}\n- Marchand") == [line, "- Marchand"]
    assert units(f"{line}\n| Marchand |") == [line, "| Marchand |"]


def test_blank_lines_split_paragraphs_and_crlf_is_trimmed():
    assert units("Jean Dupont\r\n\r\nPaul Martin\r\n") == ["Jean Dupont", "Paul Martin"]


def test_code_statements_are_skipped_but_strings_comments_and_data_are_read():
    text = ("Avant Jean.\n```python\nname = 'Jean Dupont'\nimport numpy as np\nprint(name)\n```\nAprès Paul.\n"
            "def f(x):\nconst user = getUser();\n{\"name\": \"Jean Dupont\"}\n\"nom\": \"Dupont\",\n"
            "// Auteur : Claire Vasseur.\nconst who = \"Léa Martin\";\nFin Marie.")
    assert units(text) == ["Avant Jean.", "name = 'Jean Dupont'", "print(name)", "Après Paul.",
                           "{\"name\": \"Jean Dupont\"}", "\"nom\": \"Dupont\",", "// Auteur : Claire Vasseur.",
                           "const who = \"Léa Martin\";", "Fin Marie."]


def test_unclosed_fence_hides_nothing_and_its_lines_stay_apart():
    text = "Bonjour.\n```\nLe dossier de Jean\nest prêt.\nMerci Claire Vasseur."
    assert units(text) == ["Bonjour.", "Le dossier de Jean", "est prêt.", "Merci Claire Vasseur."]


def skip(line: str) -> bool:
    return skip_line(line, 0, len(line))


@pytest.mark.parametrize("line", [
    "12 345,67 € | 89 %",
    "|---|:---:|",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0",
    "https://exemple.fr/equipe/2024/rapport-annuel-final.pdf",
    "if (a[i] == b[j]) { x = y; }",
    "if (x.isEmpty()) {",
    "while (true)",
    "SELECT nom, prenom FROM clients WHERE id = 3",
    "def f(x):",
    "class UserService:",
    "@dataclass(frozen=True)",
    "import numpy as np",
    "from os.path import join",
    "const user = getUser();",
    "public static void main(String[] args) {",
    "#include <stdio.h>",
    "} else {",
    "use std::io;",
    "package main",
    "return total;",
])
def test_lines_without_anything_to_read_are_skipped(line: str):
    assert skip(line)


@pytest.mark.parametrize("line", [
    # E-mails, liens et balises : le nom est à côté d'un jeton opaque / names next to opaque tokens.
    "De : Jean Dupont <jean.dupont@entreprise-exemple.fr>",
    "Contact : Claire Vasseur - claire.vasseur@cabinet-vasseur-avocats.fr",
    "[Jean Dupont](https://www.linkedin.com/in/jean-dupont-a1b2c3d4)",
    "[Jean Dupont](/u/1)",
    "<b>Jean Dupont</b>",
    "<p>Bonjour Jean Dupont,</p>",
    "Charles-Édouard-de-La-Rochefoucauld",
    # Données et commentaires / data and comments.
    "{\"name\": \"Jean Dupont\", \"city\": \"Lyon\"}",
    "{\"a\": {\"b\": {\"nom\": \"Dupont\"}}}",
    "  \"nom\": \"Dupont\",",
    "// Auteur : Jean Dupont",
    "x = 1  # revu par Jean Dupont",
    "SELECT * FROM clients WHERE nom = 'Dupont'",
    "const who = \"Léa Martin\";",
    "if (name == \"Jean Dupont\") {",
    "return \"Jean Dupont\";",
    "def notify(user):  # écrit par Jean Dupont",
    # Prose qui commence par un mot-clé de code / prose starting with a code keyword.
    "from Jean Dupont about the contract signed in Lyon.",
    "let me know if Jean Dupont can come to Paris.",
    "public visé : les clients de Renault à Lyon",
    "private equity firm Ardian bought the stake.",
    "Select the file sent by John Smith from the folder.",
    "for (more details) contact Jean Dupont",
    "for (Jean Dupont)",
    "interface client : Jean Dupont",
    "string theory (physics) by Jean Dupont",
    "| Jean Dupont | 06 12 34 56 78 | Lyon |",
    "Voir [le site de Jean Dupont](https://exemple.fr/jean) pour le détail.",
    "Dupont;Jean;12 rue des Lilas;75012;Paris",
    "From the desk of Jane Doe",
])
def test_lines_that_may_hold_a_name_are_read(line: str):
    assert not skip(line)


def test_units_never_cross_segments():
    first, second = "Jean Dupont habite", "à Lyon depuis peu"
    text = f"{first}\n\n{second}"
    segments = [(0, len(first)), (len(first) + 2, len(text))]
    assert units(text, segments) == [first, second]
    assert units("abc def", [(0, 0), (0, 3)]) == ["abc"]


@given(st.lists(st.text(alphabet="ab C.\n|M", max_size=12), min_size=1, max_size=5))
def test_units_are_trimmed_and_inside_their_segment(pieces: list[str]):
    text = "\n\n".join(pieces)
    segments, cursor = [], 0
    for piece in pieces:
        segments.append((cursor, cursor + len(piece)))
        cursor += len(piece) + 2
    for start, end in split_units(text, segments):
        assert any(lo <= start < end <= hi for lo, hi in segments)
        assert text[start:end] == text[start:end].strip()


# --- signaux / gating


def test_gate_opens_on_names_and_honorifics():
    assert signal("Le dossier a été transmis à Dupont.")
    assert signal("Martin a signé le contrat.")
    assert signal("DUPONT Jean, matricule 12.")
    assert signal("rendez-vous avec l'Élysée demain")
    assert signal("j'ai vu madame dupont hier")
    # Le modèle trouve « dupont » et « martin » en minuscules derrière ces civilités (mesuré).
    # The model finds lowercase "dupont" and "martin" after these honorifics (measured).
    assert signal("rdv avec m. dupont demain")
    assert signal("rdv avec dr martin demain")
    assert signal("call mr smith asap")


def test_gate_stays_closed_without_cue():
    assert not signal("Le contrat est conclu pour une durée indéterminée.")
    assert not signal("Merci de bien vouloir nous retourner le formulaire.")
    assert not signal("il pleut sur la ville depuis ce matin")
    assert not signal("12 345,67")
    assert not signal("Cordialement,")


# --- fenêtres / windows


def test_short_sequence_is_one_window():
    assert plan_windows(10, None, 64, 8) == [(0, 10, 0, 10)]


def test_windows_start_on_word_boundaries():
    word_starts = [i % 3 == 0 for i in range(40)]
    windows = plan_windows(40, word_starts, 12, 4)
    assert all(word_starts[start] for start, _, _, _ in windows)


@given(st.integers(1, 400), st.integers(4, 64), st.data())
def test_windows_partition_tokens(length: int, width: int, data: st.DataObject):
    overlap = data.draw(st.integers(0, max(0, width // 4)))
    word_starts = data.draw(st.lists(st.booleans(), min_size=length, max_size=length))
    windows = plan_windows(length, word_starts, width, overlap)
    owned = 0
    for start, end, own_start, own_end in windows:
        assert 0 <= start < end <= length and end - start <= width
        assert start <= own_start <= own_end <= end
        assert own_start == owned
        owned = own_end
    assert owned == length
    assert windows[-1][1] == length
