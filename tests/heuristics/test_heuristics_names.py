"""Détection des personnes : vrais positifs, négatifs difficiles, coréférence / person detection."""

from __future__ import annotations

import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor

import pytest

from gdprguardian import Anonymizer
from gdprguardian.heuristics.fr_names import FrenchNameDetector
from gdprguardian.packs import parse_pack
from gdprguardian.types import PRIORITY_HEURISTIC

PLACEHOLDER = re.compile(r"\[PERSONNE_\d+\]")

POSITIVES = [
    ("Jean Dupont a signé le contrat.", ["Jean Dupont"]),
    ("DUPONT Jean, né le 3 mars 1985.", ["DUPONT Jean"]),
    ("Jean-Pierre Martin est arrivé.", ["Jean-Pierre Martin"]),
    ("La séance est présidée par Mme Claire Martin-Dubois.", ["Claire Martin-Dubois"]),
    ("M. et Mme Durand sont venus.", ["Durand"]),
    ("MM. Dupont et Petit sont absents.", ["Dupont", "Petit"]),
    ("Présents : Jean Dupont, Marie Curie et Rose Petit.", ["Jean Dupont", "Marie Curie", "Rose Petit"]),
    ("Bonjour Pierre, voici le dossier.", ["Pierre"]),
    ("Cordialement,\nThomas Moreau\nChargé d'affaires", ["Thomas Moreau"]),
    ("M. de Villepin a pris la parole.", ["de Villepin"]),
    ("Charles de Gaulle et Jean de La Fontaine.", ["Charles de Gaulle", "Jean de La Fontaine"]),
    ("Yann Le Goff et Lucas Da Silva sont arrivés.", ["Yann Le Goff", "Lucas Da Silva"]),
    ("Rapport rédigé par J. Dupont.", ["J. Dupont"]),
    ("Le juge Renard a statué. Maître Durand plaide.", ["Renard", "Durand"]),
    ("Le consortium réunit Hans Müller et Giuseppe Rossi.", ["Hans Müller", "Giuseppe Rossi"]),
    ("Nom : DUPONT\nPrénom : Jean", ["DUPONT", "Jean"]),
    ("De : Julien Fabre <julien.fabre@exemple.fr>", ["Julien Fabre"]),
    ("Mme N'Diaye est convoquée.", ["N'Diaye"]),
    ("KOWALSKI Anna, née le 2 mai 1990.", ["KOWALSKI Anna"]),
    ("Bonjour Nath, merci pour ton retour.", ["Nath"]),
    ("Le patient Ansgar Davids présente une toux.", ["Ansgar Davids"]),
    ("Salut Léa ! Tu peux rappeler Enzo demain ?", ["Léa", "Enzo"]),
    ("La séance est ouverte par Mme Claire\nMartin-Dubois, présidente.", ["Claire\nMartin-Dubois"]),
    # Guillemet ou tiret collé au nom / closing quote or hyphen glued to the name.
    ("Il a dit ‘Kowalczyk’ hier.", ["Kowalczyk"]),
    ("M. Kowalczyk’ a signé.", ["Kowalczyk"]),
    ("Réf. Dupont- Martin", ["Dupont", "Martin"]),
    ("Mr. Johnson's car", ["Johnson"]),
    # Prénom composé coupé en fin de ligne / compound given name split by a line break.
    ("La patiente Mme Anne-\nSophie Martin est sortie.", ["Anne-\nSophie Martin"]),
    # Formules de fin et fins de ligne Windows / closings and CRLF line endings.
    ("Merci,\nClaire", ["Claire"]),
    ("Cordialement,\r\nClaire", ["Claire"]),
    # Valeurs de champ en minuscules, étiquettes de fonction / lowercase field values, job-title labels.
    ("Nom : dupont\nPrénom : jean", ["dupont", "jean"]),
    ("Nom : jean Dupont", ["jean Dupont"]),
    ("Nom : wagenknecht", ["wagenknecht"]),
    ("- Assistante : Rose", ["Rose"]),
    ("Signature : Rose Blanc", ["Rose Blanc"]),
    # Nom inconnu seul confirmé par une adresse e-mail / lone unknown surname confirmed by an e-mail.
    ("Wagenknecht répondra. Contact : detlev.wagenknecht@exemple.de", ["Wagenknecht"]),
    # « NÉE » n'est pas un nom de la liste / "NÉE" is not a list item.
    ("MADAME ROSE BLANC, NÉE LE 3 MARS 1980", ["ROSE BLANC"]),
    # Nom sûr et fréquent en capitales dans la prose / frequent unambiguous surname in capitals within prose.
    ("Selon DUPONT, le budget est insuffisant.", ["DUPONT"]),
    # Intitulés de dossiers : un mot courant capitalisé ne protège pas un nom sûr / file titles.
    ("Dossier Dupont : pièces reçues.", ["Dupont"]),
    ("Affaire Delacroix c/ Société Générale.", ["Delacroix"]),
    ("Contrat Martin-Dubois signé.", ["Martin-Dubois"]),
    ("Rapport Lefèvre 2024", ["Lefèvre"]),
    ("Paie Delacroix 2024", ["Delacroix"]),
]

NEGATIVES = [
    "La France et Florence sont belles.",
    "Le mois d'Avril est doux à Paris, à Lyon et en Bretagne.",
    "Le lycée Victor Hugo est situé rue Jean Jaurès.",
    "La maladie de Charcot et le cycle de Krebs.",
    "Monsieur le Maire et Madame la Présidente, Mesdames et Messieurs.",
    "Louis XIV et Henri IV ont régné. Le XIXe siècle.",
    "Voir Tableau 3 et Annexe B.",
    "Le Moulin Rouge et le Mont Blanc attirent les touristes.",
    "## Rapport Annuel De La Direction Générale",
    "Rose des vents et Marine nationale sont des expressions courantes.",
    "La tour Eiffel et Notre-Dame de Paris.",
    "Saint-Martin et Saint-Denis sont des communes.",
    "Radio France et Air France communiquent.",
    "Microsoft Teams et Google Docs sont installés.",
    "La Société Générale publie ses résultats.",
    "Le CAC 40 progresse ; la BCE maintient ses taux.",
    "Sommaire\n1. Introduction\n2. Contexte et Enjeux\n3. Méthodologie Générale",
    "Fournisseurs : Ferrovia S.p.A., Telar S.L. et Bouwbedrijf B.V.",
    "L'Union européenne et l'Europe.",
    # Formes verbales homonymes de noms / verb forms that are also surnames.
    "Compte Rendu De La Réunion",
    "Rendu le 3 mars 2025 par la cour d'appel.",
    # Champs dont la valeur n'est pas un nom / fields whose value is not a name.
    "Patient : diabétique depuis 2010\nTitulaire : oui\nBénéficiaire : désigné",
    "Témoin : néant",
    # Sigles en capitales / acronyms in capitals.
    "Selon la CNIL, la SNCF et l'URSSAF, le numéro SIRET figure en annexe.",
    "RAPPORT ANNUEL DUPONT ET ASSOCIES",
    # Lieux nommés d'après une personne, modèles numérotés / places named after a person, numbered models.
    "L'Opéra Garnier, l'Avenue Delacroix et le Musée Delacroix sont fermés.",
    "Ariane 5 a décollé.",
]


def test_unknown_word_is_confirmed_only_by_a_cue(found):
    # Sans indice, un mot inconnu peut être un mot courant absent du lexique (« Facture Dupont ») : il n'est pas
    # propagé seul. Without a cue an unknown word may be a missing common word: it is not propagated alone.
    assert found("Ozrandel Dupont a signé. Ozrandel est clos.") == ["Ozrandel Dupont"]
    assert found("Le patient Ozrandel Dupont tousse. Ozrandel dort.") == ["Ozrandel Dupont", "Ozrandel"]


@pytest.mark.parametrize(("text", "expected"), POSITIVES)
def test_true_positives(found, text, expected):
    assert found(text) == expected


@pytest.mark.parametrize("text", NEGATIVES)
def test_hard_negatives(found, text):
    assert found(text) == []


@pytest.mark.parametrize(("text", "expected"), [
    # Messages, tickets, SMS : nom en minuscules juste après un indice / lowercase name right after a cue.
    ("La commande 152000 du client guillaume au tél 0650123456.",
     # 1.0.2 : un numéro après « commande » est masqué (filtre fort) / a number after "commande" is masked.
     "La commande [IDENTIFIANT_1] du client [PERSONNE_1] au tél [TEL_1]."),
    ("Bonjour guillaume, ta commande est prête.", "Bonjour [PERSONNE_1], ta commande est prête."),
    ("Le client guillaume martin a rappelé.", "Le client [PERSONNE_1] a rappelé."),
    ("M. dupont est absent.", "M. [PERSONNE_1] est absent."),
    # Mots courants ou ambigus après un indice : rien ne change / common or ambiguous words: unchanged.
    ("Le client fidèle a rappelé.", "Le client fidèle a rappelé."),
    ("Bonjour à tous, mon fils pierre arrive.", "Bonjour à tous, mon fils pierre arrive."),
    ("Bonjour madame, le patient blanc est sorti.", "Bonjour madame, le patient blanc est sorti."),
])
def test_lowercase_names_after_a_cue(fr, text, expected):
    assert fr.anonymize(text).text == expected


def test_honorifics_stay_outside_the_span(fr):
    result = fr.anonymize("M. Dupont, Mme Martin et Dr Antoine Mercier.")
    assert result.text == "M. [PERSONNE_1], Mme [PERSONNE_2] et Dr [PERSONNE_3]."


def test_name_variants_share_one_placeholder(fr):
    text = ("Jean Dupont a signé. M. Dupont a ensuite rappelé. DUPONT Jean est le titulaire. "
            "J. Dupont a paraphé. Claire Martin est témoin.")
    out = fr.anonymize(text).text
    assert out.count("[PERSONNE_1]") == 4
    assert "[PERSONNE_2]" in out
    assert "Dupont" not in out and "DUPONT" not in out and "Martin" not in out


def test_surname_first_order_is_canonicalised(fr):
    out = fr.anonymize("Les travaux de Blanchard Olivier. Plus tard, Olivier Blanchard confirme.").text
    assert out == "Les travaux de [PERSONNE_1]. Plus tard, [PERSONNE_1] confirme."


def test_two_people_sharing_a_surname_stay_distinct(fr):
    out = fr.anonymize("Jean Dupont et Marie Dupont sont frère et sœur.").text
    assert out == "[PERSONNE_1] et [PERSONNE_2] sont frère et sœur."


def test_ambiguous_surname_is_propagated_only_in_safe_positions(fr):
    text = "Pierre Blanc a signé. Ensuite, Blanc a appelé. Le vin blanc et le Mont Blanc."
    out = fr.anonymize(text).text
    assert out == "[PERSONNE_1] a signé. Ensuite, [PERSONNE_1] a appelé. Le vin blanc et le Mont Blanc."


def test_unambiguous_surname_form_is_propagated_by_the_engine(fr):
    out = fr.anonymize("Mme Kowalczyk est arrivée. KOWALCZYK a signé. Kowalczyk repart.").text
    assert "Kowalczyk" not in out and "KOWALCZYK" not in out
    assert out.count("[PERSONNE_1]") == 3


def test_email_local_part_confirms_ambiguous_names(fr):
    out = fr.anonymize("Écrire à rose.blanc@exemple.fr. Rose Blanc répondra ; Blanc est absente.").text
    assert "Rose" not in out and "Blanc" not in out


def test_markdown_table_columns(fr):
    table = ("| Nom | Prénom | Service |\n|---|---|---|\n| DUPONT | Jean | Comptabilité |\n"
             "| Bernard | Rose | Ressources humaines |\n| inconnu | - | Achats |")
    out = fr.anonymize(table).text
    rows = out.splitlines()
    assert rows[2] == "| [PERSONNE_1] | [PERSONNE_1] | Comptabilité |"  # prénom et nom d'une ligne : même balise
    assert rows[3] == "| [PERSONNE_2] | [PERSONNE_2] | Ressources humaines |"
    assert rows[4] == "| inconnu | - | Achats |"


def test_spans_follow_the_detector_contract(fr):
    text = "Bonjour Pierre, M. Jean Dupont et Mme Rose Petit vous saluent."
    spans = [s for s in fr.analyze(text).spans if s.entity == "PERSON"]
    assert spans
    for span in spans:
        assert span.label == "PERSON" and span.personal
        assert span.priority == PRIORITY_HEURISTIC
        assert not text[span.start:span.end].startswith(("M.", "Mme", "Bonjour"))
    full = next(s for s in spans if text[s.start:s.end] == "Jean Dupont")
    assert full.propagate and full.forms == ("Dupont",)


def test_ambiguous_single_word_is_not_propagated_by_the_engine(context):
    detector = FrenchNameDetector(None)
    ctx = context("Selon Mme Rose, le projet avance.")
    (span,) = detector.detect(ctx)
    assert ctx.text[span.start:span.end] == "Rose"
    assert not span.propagate and span.forms == ()


def test_segments_are_never_crossed():
    a = Anonymizer(countries="FR")
    per_cell, _ = a.analyze_segments(["Bonjour Jean", "Dupont est là", "M.", "Durand"])
    for spans, cell in zip(per_cell, ["Bonjour Jean", "Dupont est là", "M.", "Durand"], strict=True):
        for span in spans:
            assert 0 <= span.start < span.end <= len(cell)


def test_person_header_tag_marks_a_whole_segment(context):
    # Les en-têtes de tableur peuvent marquer une colonne « personne » / spreadsheet headers may tag a column.
    pack = parse_pack({"pack": {"id": "XX"}, "context": {"person": {"fr": ["prénom"]}}})
    detector = FrenchNameDetector(pack)
    a = Anonymizer(countries="FR")
    texts = ["Rose", "Marine", "comptabilité"]
    forced = [frozenset({"XX:person"}), frozenset({"XX:person"}), frozenset()]
    per_cell, _ = a.analyze_segments(texts)  # sans en-tête : « Rose », « Marine » sont ambigus
    assert all(not [s for s in spans if s.entity == "PERSON"] for spans in per_cell)
    ctx = context("Rose\n\nMarine\n\ncomptabilité")
    ctx.seg_starts, ctx.seg_ends, ctx.forced = [0, 6, 14], [4, 12, 26], forced
    spans = detector.detect(ctx)
    assert sorted(ctx.text[s.start:s.end] for s in spans) == ["Marine", "Rose"]


def test_detector_is_thread_safe(context):
    detector = FrenchNameDetector(None)
    texts = [f"Bonjour Pierre, M. Dupont et Mme Rose Petit (dossier {i})." for i in range(64)]
    contexts = [context(t) for t in texts]
    expected = [[(s.start, s.end, s.value) for s in detector.detect(c)] for c in contexts]
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda c: [(s.start, s.end, s.value) for s in detector.detect(c)], contexts))
    assert results == expected


def test_no_document_state_is_kept(context):
    detector = FrenchNameDetector(None)
    before = dict(vars(detector)) if hasattr(detector, "__dict__") else {}
    detector.detect(context("Jean Dupont et Rose Petit."))
    after = dict(vars(detector)) if hasattr(detector, "__dict__") else {}
    assert before == after


def test_markdown_table_with_windows_line_endings(fr):
    table = "| Nom | Prénom |\r\n|---|---|\r\n| Kowalczyk | Gwendal |\r\n| Bernard | Rose |\r\n"
    rows = fr.anonymize(table).text.split("\r\n")
    assert rows[2] == "| [PERSONNE_1] | [PERSONNE_1] |"
    assert rows[3] == "| [PERSONNE_2] | [PERSONNE_2] |"  # « Rose » dans une colonne Prénom / in a given-name column


def test_decomposed_unicode_is_detected_with_its_combining_marks(fr):
    # Texte NFD (macOS, certains PDF) : les diacritiques restent dans la zone / marks stay inside the span.
    text = unicodedata.normalize("NFD", "Mme Zélie Lefèvre a signé. Zélie est partie. José Ménard aussi.")
    out = fr.anonymize(text).text  # égalité exacte : aucun diacritique orphelin / exact: no orphan mark
    assert out == unicodedata.normalize("NFD", "Mme [PERSONNE_1] a signé. [PERSONNE_1] est partie. "
                                                "[PERSONNE_2] aussi.")


def test_decomposed_segments_are_never_crossed():
    cells = [unicodedata.normalize("NFD", c) for c in ("Mme Hélène Gérard", "Zoé", "Bonjour Frédéric")]
    per_cell, _ = Anonymizer(countries="FR").analyze_segments(cells)
    found = [[cell[s.start:s.end] for s in spans if s.entity == "PERSON"] for cell, spans in zip(cells, per_cell,
                                                                                               strict=True)]
    assert found[0] == [unicodedata.normalize("NFD", "Hélène Gérard")]
    assert found[2] == [unicodedata.normalize("NFD", "Frédéric")]


def test_confirmed_surname_is_masked_inside_a_kept_organisation(fr):
    # L'organisation conservée ne doit pas protéger un nom vu ailleurs / a kept organisation never shields a name.
    out = fr.anonymize("Mme Ferhati est cliente. Ferhati Solutions a livré.").text
    assert out == "Mme [PERSONNE_1] est cliente. [PERSONNE_1] Solutions a livré."
    out = fr.anonymize("Dr Zylberstein exerce au Cabinet Zylberstein.").text
    assert out == "Dr [PERSONNE_1] exerce au Cabinet [PERSONNE_1]."


def test_hyphen_wrapped_name_shares_the_placeholder(fr):
    out = fr.anonymize("Mme Anne-\nSophie Martin est sortie. Anne-Sophie Martin va mieux.").text
    assert out == "Mme [PERSONNE_1] est sortie. [PERSONNE_1] va mieux."


def test_common_word_in_a_person_column_is_masked_but_not_propagated(fr):
    out = fr.anonymize("| Nom | Service |\n|---|---|\n| Direction | Achats |\n\nLa Direction valide.").text
    assert out.splitlines()[2] == "| [PERSONNE_1] | Achats |"
    assert out.endswith("La Direction valide.")


def test_lowercase_field_value_spans(context):
    ctx = context("Nom : dupont jean\nPrénom : rose")
    spans = {ctx.text[s.start:s.end]: s for s in FrenchNameDetector(None).detect(ctx)}
    assert set(spans) == {"dupont jean", "rose"}
    assert spans["dupont jean"].value == "jean dupont"  # ordre Prénom Nom pour la coréférence / given name first
    assert spans["dupont jean"].propagate is False  # « jean » est aussi un mot / "jean" is also a word
    assert spans["rose"].propagate is False


def test_signature_after_thanks_on_its_own_line(found):
    # « Claire » est aussi un mot courant : seule la signature en fait un nom / only the signature makes it a name.
    assert found("Merci,\r\n\r\nClaire\r\n") == ["Claire"]
    assert found("Bonne fin de journée,\nClaire\nAssistante") == ["Claire"]


def test_output_never_contains_detected_names(fr):
    text = "Mme Isabelle Fournier, patiente du Dr Antoine Mercier, est suivie par Mme Fournier mère."
    out = fr.anonymize(text).text
    for name in ("Isabelle", "Fournier", "Antoine", "Mercier"):
        assert name not in out
    assert PLACEHOLDER.search(out)
