"""Moteur de bout en bout / end-to-end engine."""

from __future__ import annotations

import pytest

from gdprguardian import Anonymizer, anonymize
from gdprguardian.engine import resolve
from gdprguardian.types import PRIORITY_HEURISTIC, PRIORITY_VALIDATED, Span

NIR = "1 85 05 78 006 084 91"
IBAN = "FR76 3000 6000 0112 3456 7890 189"


def test_core_identifiers_are_replaced(anonymizer):
    text = (f"NIR {NIR}, IBAN {IBAN}, mail jean.dupont@exemple.fr, tél 06 12 34 56 78, "
            "carte 4111 1111 1111 1111, IP 192.168.1.42, clé AKIAABCDEFGHIJKLMNOP.")
    result = anonymizer.anonymize(text)
    for secret in (NIR, IBAN, "jean.dupont@exemple.fr", "06 12 34 56 78", "4111 1111 1111 1111",
                   "192.168.1.42", "AKIAABCDEFGHIJKLMNOP"):
        assert secret not in result.text
    for placeholder in ("[NIR_1]", "[IBAN_1]", "[EMAIL_1]", "[TEL_1]", "[CARTE_1]", "[IP_1]", "[SECRET_1]"):
        assert placeholder in result.text
    assert result.report["irreversible"] is True


def test_consistency_within_document(anonymizer):
    result = anonymizer.anonymize("a@b.fr écrit à c@d.fr, puis a@b.fr relance c@d.fr.")
    assert result.text == "[EMAIL_1] écrit à [EMAIL_2], puis [EMAIL_1] relance [EMAIL_2]."


def test_documents_are_not_linkable(anonymizer):
    # Même valeur, deux documents : deux clés indépendantes, aucun lien conservé.
    first = anonymizer.anonymize("Contact : z@y.fr et a@b.fr")
    second = anonymizer.anonymize("Contact : a@b.fr")
    assert first.text == "Contact : [EMAIL_1] et [EMAIL_2]"
    assert second.text == "Contact : [EMAIL_1]"


def test_company_ids_policy():
    text = "ACME SAS, SIREN 732 829 320, TVA FR44 732829320."
    kept = Anonymizer(countries="FR").anonymize(text)
    assert "732 829 320" in kept.text and kept.report["kept_by_policy"]
    masked = Anonymizer(countries="FR", company_ids="mask").anonymize(text)
    assert "732 829 320" not in masked.text
    sole_trader = Anonymizer(countries="FR").anonymize(
        "Jean Martin, entrepreneur individuel, SIREN 732 829 320.")
    assert "732 829 320" not in sole_trader.text


def test_weak_checksum_needs_context(anonymizer_fr):
    # Un nombre Luhn-valide de 9 chiffres sans contexte n'est pas un SIREN / no context, no SIREN.
    assert "732829320" in anonymizer_fr.anonymize("Commande 732829320 expédiée.").text
    strict = Anonymizer(countries="FR", profile="strict").anonymize("Commande 732829320 expédiée.")
    assert "732829320" not in strict.text


def test_context_only_identifiers():
    a = Anonymizer(countries="FR")
    assert "[PASSEPORT_1]" in a.anonymize("Passeport n° 12AB34567").text
    assert "12AB34567" in a.anonymize("Référence produit 12AB34567").text


def test_obfuscation_is_defeated(anonymizer):
    zero_width = "1 85​05 78 006 084 91"
    result = anonymizer.anonymize(f"NIR : {zero_width}.")
    assert result.text == "NIR : [NIR_1]."
    fullwidth = "１ ８５ ０５ ７８ ００６ ０８４ ９１"
    assert "[NIR_1]" in anonymizer.anonymize(f"Sécu {fullwidth}").text
    nbsp = NIR.replace(" ", " ")
    assert "[NIR_1]" in anonymizer.anonymize(f"NIR {nbsp}").text


def test_offsets_map_back_to_original(anonymizer):
    text = "x​y NIR 1 85​05 78 006 084 91 fin"
    analysis = anonymizer.analyze(text)
    nir_span = next(s for s in analysis.spans if s.label == "NIR")
    assert text[nir_span.start:nir_span.end] == "1 85​05 78 006 084 91"


def test_country_modes():
    # Par défaut : France explicite / default: explicit France.
    assert Anonymizer().analyze("x").countries == ("FR",)
    assert Anonymizer(countries="fr").analyze("x").countries == ("FR",)
    report = Anonymizer(countries=["FR"]).anonymize("x").report
    assert report["country_mode"] == "explicit" and "warnings" not in report
    # Multi-pays : tous les packs, sans deviner / every pack, no guessing.
    everything = Anonymizer(countries="all").analyze("x")
    assert "FR" in everything.countries
    # Auto : expérimental, signalé dans le rapport / experimental, flagged in the report.
    auto = Anonymizer(countries="auto")
    analysis = auto.analyze("Appelez le +33 6 12 34 56 78, IBAN " + IBAN)
    assert "FR" in analysis.countries
    assert any(r.startswith("phone:+33") for r in analysis.country_reasons["FR"])
    assert auto.anonymize("x").report["warnings"]


def test_unknown_country_is_rejected():
    import pytest

    with pytest.raises(ValueError):
        Anonymizer(countries=["ZZ"])
    with pytest.raises(ValueError):
        Anonymizer(countries="sometimes")


def test_secrets_always_replaced_even_with_keep_operator():
    a = Anonymizer(operators={"SECRET": "keep"})
    assert "AKIAABCDEFGHIJKLMNOP" not in a.anonymize("AKIAABCDEFGHIJKLMNOP").text


def test_deny_and_allow_lists():
    a = Anonymizer(deny_list={"Projet": ["Opération Phénix"]}, allow_list=["support@acme.fr"])
    result = a.anonymize("L'Opération Phénix démarre ; écrire à support@acme.fr ou jean@acme.fr.")
    assert "[PROJET_1]" in result.text
    assert "support@acme.fr" in result.text
    assert "jean@acme.fr" not in result.text


def test_generalize_birth_date():
    a = Anonymizer(countries="FR", operators={"BIRTH_DATE": "generalize"})
    assert a.anonymize("Née le 3 mars 1985 à Lyon.").text == "Née le 1985 à Lyon."


def test_resolution_prefers_validated_and_trims_composites():
    text = "Jean Dupont 06 12 34 56 78"
    spans = [
        Span(0, 26, "PERSON", "PERSON", "ner", 0.6, PRIORITY_HEURISTIC),
        Span(12, 26, "PHONE", "PHONE", "re", 0.95, PRIORITY_VALIDATED),
    ]
    resolved = sorted(resolve(spans, text), key=lambda s: s.start)
    assert [(s.entity, text[s.start:s.end]) for s in resolved] == [
        ("PERSON", "Jean Dupont"), ("PHONE", "06 12 34 56 78")]


def _valid_siret(prefix13: str) -> str:
    from gdprguardian.validators.fr import siret

    return next(prefix13 + d for d in "0123456789" if siret(prefix13 + d))


def test_segments_with_forced_header_context(anonymizer_fr):
    value = _valid_siret("7328293200007")
    groups = anonymizer_fr.context_groups("N° SIRET")
    assert "FR:siret" in groups
    per_cell, _ = anonymizer_fr.analyze_segments([value, value], [groups, frozenset()])
    assert [s.label for s in per_cell[0]] == ["SIRET"]
    assert per_cell[1] == []


def test_markdown_table_header_is_context_for_its_column(anonymizer_fr):
    # L'en-tête « Date de naissance » vaut pour toute la colonne, même loin ; pas pour les autres colonnes.
    # The "Date de naissance" header covers its whole column, however far; not the other columns.
    rows = "".join(f"| Agent {i} | {i % 28 + 1:02d}/04/1990 | 1{i % 9}/05/2024 |\n" for i in range(15))
    text = "| Nom | Date de naissance | Arrivée |\n|:---|:---:|---|\n" + rows + "\nRéunion le 12/06/2024."
    lines = anonymizer_fr.anonymize(text).text.splitlines()
    assert all("/04/1990" not in line for line in lines)
    # Loin de l'en-tête, les autres colonnes restent intactes (tout près, la proximité joue : rappel d'abord).
    # Away from the header, other columns stay intact (right next to it, proximity applies: recall first).
    assert all(line.count("/05/2024") == 1 for line in lines[4:17])
    assert lines[-1] == "Réunion le 12/06/2024."


def test_markdown_table_zones_edge_cases():
    from gdprguardian.engine import markdown_table_zones

    def groups_of(header: str) -> frozenset[str]:
        return frozenset({"dob"}) if "naissance" in header else frozenset()

    def cells(text: str) -> list[str]:
        return [text[start:end] for start, end, _ in markdown_table_zones(text, groups_of)]

    # Barre échappée, délimitation à un tiret, fin de ligne CRLF, fin du tableau à la ligne vide.
    # Escaped pipe, one-dash delimiter, CRLF line end, table ends at the blank line.
    text = "Nom \\| alias | Date de naissance\n-|-\nA \\| B | 03/03/1985\r\nC | 04/04/1990\n\nfin | 05/05/2005"
    assert cells(text) == ["03/03/1985", "04/04/1990"]
    # Barres de bord et première cellule d'en-tête vide / edge pipes and an empty first header cell.
    assert cells("|  | Date de naissance |\n|---|:---:|\n| x | 03/03/1985 |") == ["03/03/1985"]
    # Deux délimitations à la suite : la seconde est une ligne du premier tableau (GFM).
    # Two delimiters in a row: the second is a row of the first table (GFM).
    assert cells("| a | naissance |\n|---|---|\n| b | 1 |\n|---|---|\n| c | 2 |") == ["1", "---", "2"]
    assert cells("Pas de tableau | ici\n---") == []


def test_date_matching_a_nir_is_a_birth_date(anonymizer_fr):
    # Le NIR encode l'année et le mois de naissance (ici 85 et 05) / the NIR encodes birth year and month.
    text = f"Pour moi c'est le 12/05/1985 et {NIR}. Livraison le 12/06/1985, puis le 3 mai 1985."
    result = anonymizer_fr.anonymize(text).text
    assert "12/05/1985" not in result and "3 mai 1985" not in result
    assert "12/06/1985" in result
    assert "12/05/1985" in anonymizer_fr.anonymize("Pour moi c'est le 12/05/1985.").text


def test_nearest_cue_wins_for_birth_dates(anonymizer_fr):
    # « réunion » est plus proche de la date que « né le » : ce n'est pas une date de naissance.
    # "réunion" is closer to the date than "né le": not a birth date.
    result = anonymizer_fr.anonymize("Je suis né le 24 juillet 1953. Pour la réunion du 12/02/2026, merci.").text
    assert "24 juillet 1953" not in result and "12/02/2026" in result
    # Le mot-clé après le veto reste le plus proche / a keyword after the veto is still the nearest cue.
    assert "03/03/1985" not in anonymizer_fr.anonymize("Réunion avec Jean, né le 03/03/1985.").text


def test_wrong_key_is_masked_next_to_an_explicit_keyword(anonymizer_fr):
    # Faute de frappe ou erreur d'OCR : la clé est fausse mais le mot-clé ne laisse aucun doute.
    # Typo or OCR error: the key is wrong but the keyword leaves no doubt.
    typo_nir = NIR[:-1] + "2"
    typo_iban = IBAN[:-1] + "8"
    text = (f"N° de sécurité sociale : {typo_nir}. Numéro fiscal de référence (0535211664078). "
            f"IBAN : {typo_iban}. Carte bancaire 4111 1111 1111 1112.")
    result = anonymizer_fr.anonymize(text).text
    for value in (typo_nir, "0535211664078", typo_iban, "4111 1111 1111 1112"):
        assert value not in result
    # Format imprimé (NIR 1-2-2-2-3-3-2, IBAN et carte par blocs de 4) : la forme suffit, sans mot-clé.
    # Printed layout (NIR 1-2-2-2-3-3-2, IBAN and card in blocks of 4): the shape is enough, no keyword.
    result = anonymizer_fr.anonymize(f"Numéro {typo_nir}, compte {typo_iban}, la carte 4720 7547 3548 6438.")
    assert result.text == "Numéro [NIR_1], compte [IBAN_1], la carte [CARTE_1]."
    assert anonymizer_fr.anonymize(f"Voir {typo_iban}.").text == "Voir [IBAN_1]."
    # Forme compacte, clé fausse, sans mot-clé : pas un identifiant / compact, wrong key, no keyword: kept.
    compact = typo_nir.replace(" ", "")
    assert compact in anonymizer_fr.anonymize(f"Référence {compact}.").text


def test_conversion_artefacts_do_not_hide_values(anonymizer_fr):
    # Gras Markdown, remplissage hangul et césure PDF : la valeur reste détectée, le gras reste en place.
    # Markdown bold, Hangul filler and PDF hyphenation: the value is still found, bold stays in place.
    result = anonymizer_fr.anonymize("**N° client :** CLT-2024-0098\nNIR 1 85 05 78ㅤ 006 084 91").text
    assert "CLT-2024-0098" not in result and "006" not in result
    assert result.startswith("**N° client :** [")


def test_english_month_birth_dates(anonymizer_fr):
    result = anonymizer_fr.anonymize("Salarié : Maître Chauveau, né(e) le 06 October 1950, n° de sécu.").text
    assert "06 October 1950" not in result


def test_sole_trader_mention_covers_the_whole_document():
    siren = "732 829 320"
    far = "Jean Martin exerce comme entrepreneur individuel." + " Texte sans rapport." * 30 + f" SIREN {siren}."
    assert siren not in Anonymizer(countries="FR").anonymize(far).text
    assert siren in Anonymizer(countries="FR").anonymize(f"ACME SAS, SIREN {siren}.").text


def test_company_number_next_to_a_natural_persons_civil_status_is_personal():
    siren = "732 829 320"
    fr = Anonymizer(countries="FR")
    # Fiche de registre d'une personne physique (BODACC) / registry record of a natural person.
    record = f"n° RCS : {siren} RCS Testville\nNom : TESTIX\nPrénom : Paule\nActivité : vente"
    assert siren not in fr.anonymize(record).text
    assert siren not in fr.anonymize(f"n° RM : {siren} RM 99\nNom : TESTIX\nPrénom : Paule").text
    # Société : dénomination ou forme juridique tout près, état civil d'un autre / a company: the civil status nearby
    # belongs to someone else.
    assert siren in fr.anonymize(f"n° RCS : {siren} RCS Testville\nDénomination : ACME SAS").text
    contract = (f"Entre la société ACME SAS, SIRET {siren} 00012, représentée par M. Paul Testix, et Mme Jeanne "
                "Essai, née le 3 mars 1980 à Lyon.")
    assert f"{siren} 00012" in fr.anonymize(contract).text
    # Hors de la fenêtre de 120 caractères : conservé / beyond the 120-character window: kept.
    far = f"SIREN {siren}." + " Texte sans rapport." * 10 + " Prénom : Paule"
    assert siren in fr.anonymize(far).text


@pytest.mark.parametrize("native", [True, False], ids=["native", "python"])
def test_civil_status_is_read_on_the_number_line_then_its_paragraph(native: bool):
    siren, other = "732 829 320", "412 857 369"
    fr = Anonymizer(countries="FR", native=native)
    # Employeur sur la ligne du numéro : personne morale, l'état civil du salarié est celui d'un autre.
    # Employer on the number's line: a legal entity; the employee's civil status belongs to someone else.
    payslip = (f"BULLETIN DE PAIE\nEmployeur : TESTIVO, 12 rue des Essais 69003 Lyon – SIREN {siren}\n"
               "Code APE : 6202A\nSalarié : Prénom : Lucas Nom : Testix")
    assert siren in fr.anonymize(payslip).text
    assert siren in fr.anonymize(f"TESTIVO, SIREN {siren}, employeur de M. Jean Testix, né le 3 mars 1970.").text
    # La société de la ligne précédente ne couvre pas le numéro d'une personne / the company line above does not
    # cover a person's number.
    out = fr.anonymize(f"Société Testivo SAS, RCS Paris {siren}.\nM. Jean Testix, né le 3 mars 1970, RM {other}.").text
    assert siren in out and other not in out
    # Jamais au-delà d'une ligne vide / never past a blank line.
    assert siren in fr.anonymize(f"Prénom : Paule\nNom : Testix\n\nSIREN : {siren}").text
    assert siren not in fr.anonymize(f"Prénom : Paule\nNom : Testix\nSIREN : {siren}").text


@pytest.mark.parametrize("native", [True, False], ids=["native", "python"])
def test_explain_names_the_company_number_rule(native: bool):
    siren = "732 829 320"
    fr = Anonymizer(countries="FR", explain=True, native=native)

    def reasons(text: str) -> list[tuple[str, str]]:
        return [(line["rule"], line["reason"]) for line in fr.anonymize(text).report["explain"]
                if line["rule"] == "FR_SIREN"]

    assert reasons(f"Prénom : Paule\nSIREN : {siren}") == [("FR_SIREN", "civil_status_nearby")]
    assert reasons(f"Entrepreneur individuel, SIREN {siren}.") == [("FR_SIREN", "sole_trader")]
    strict = Anonymizer(countries="FR", explain=True, native=native, profile="strict")
    explain = strict.anonymize(f"ACME SAS, SIREN {siren}.").report["explain"]
    assert [line["reason"] for line in explain if line["rule"] == "FR_SIREN"] == ["validated_and_keyword"]


def test_report_warns_when_france_is_not_requested():
    warning = "Names and addresses are detected by the French lexicons only"
    assert not any(warning in w for w in Anonymizer(countries="FR").anonymize("x").report.get("warnings", []))
    report = Anonymizer(countries="DE").anonymize("x").report
    assert any(warning in w and "Noms et adresses" in w for w in report["warnings"])
    assert not any(warning in w for w in Anonymizer(countries="all").anonymize("x").report.get("warnings", []))


def test_fourteen_digit_cards_need_a_card_keyword(anonymizer):
    diners = "3056 9309 0259 04"
    assert "[CARTE_1]" in anonymizer.anonymize(f"Carte bancaire Diners {diners}").text
    assert diners in anonymizer.anonymize(f"Référence {diners}").text


def test_output_sanitized(anonymizer):
    out = anonymizer.anonymize("Voir ![x](https://evil.example/leak?d=1) et a‮b").text
    assert "evil.example" not in out and "‮" not in out


def test_shortcut():
    assert anonymize("mail: a@b.fr").text == "mail: [EMAIL_1]"
