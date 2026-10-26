"""Corpus de classeurs aléatoires et reproductibles / random, reproducible workbooks.

Chaque graine donne un classeur : tableaux (en-têtes simples ou sur deux lignes fusionnées, titres, notes,
totaux, tableaux Excel), formulaires, cellules isolées, feuilles larges, masquées, vides ; valeurs de tous les
types (textes Unicode retors, nombres, dates des systèmes 1900 et 1904, heures, durées, booléens, erreurs,
formules avec valeur en cache, textes enrichis). Données fictives uniquement. Sert aux tests différentiels
(noyau Rust contre référence Python) et aux mesures.
Each seed gives one workbook: tables, forms, isolated cells, wide, hidden and empty sheets; values of every type.
Fictitious data only. Used by the differential tests (Rust core against the Python reference) and benchmarks.
"""

from __future__ import annotations

import datetime as dt
import io
import random
from collections.abc import Callable
from typing import Any

import xlsxwriter

GIVEN = ["Hélène", "Mathis", "Zoé", "Baptiste", "Inès", "Gaspard", "Clémence", "Anatole", "Maëlle", "Théodore",
         "Jean-Luc", "Anne-Sophie", "Ève", "Noël", "Chloé", "Loïc"]
SURNAMES = ["Delacroix", "Fontaine", "Marchetti", "Nguyen", "Bertrand", "Lemoine", "Roussel", "Vasseur", "Guérin",
            "Blanchard", "Le Goff", "De La Tour", "O'Neil", "Müller", "Ibáñez", "Łukasik"]
CITIES = ["Paris", "Lyon", "Évreux", "Nîmes", "Orléans", "Saint-Étienne", "Aix-en-Provence", "Brest"]
NULLS = ["n/a", "-", "", "  ", "inconnu", "N/A", "?", "néant"]
# Textes retors : accents décomposés, astraux, invisibles, séparateurs U+001C-U+001F, CRLF, barres, crochets.
# Tricky texts: decomposed accents, astral, invisible, U+001C-U+001F separators, CRLF, pipes, brackets.
TRICKY = ["école", "😀 ok 𝔘𝔫𝔦", "zéro​espace", "a\u001cb\u001dc\u001ed\u001ff", "ligne 1\r\nligne 2",
          "a|b", "[PERSONNE_1] déjà", "  espaces  ", " insécable ", "_x000D_ échappé", "x" * 300,
          "# titre", "> cité", "1. liste", "=1+1", "@SUM(A1)", "Total partiel", "<b>&amp;</b>", "tab\tulé",
          " sep ", "Ǆ ǅ ǆ", "İstanbul ı", "ß straße", "ﬁ ligature"]
HEADERS = {
    "nom": "Nom", "prenom": "Prénom", "email": "Email", "tel": "Téléphone", "naissance": "Date de naissance",
    "nir": "N° SS", "cp": "Code postal", "ville": "Ville", "montant": "Montant", "commentaire": "Commentaire",
    "siret": "SIRET", "iban": "IBAN", "service": "Service", "quantite": "Quantité", "actif": "Actif",
    "heure": "Heure d'arrivée", "duree": "Durée", "date": "Date", "ref": "Référence dossier", "libre": "",
}


def _nir(rng: random.Random) -> str:
    body = f"{rng.choice('12')}{rng.randrange(40, 99):02d}{rng.randrange(1, 13):02d}{rng.randrange(1, 96):02d}" \
           f"{rng.randrange(1, 999):03d}{rng.randrange(1, 999):03d}"
    return f"{body}{97 - int(body) % 97:02d}"


def _luhn(prefix: str) -> str:
    for digit in "0123456789":
        candidate = prefix + digit
        total = sum(int(c) for c in candidate[-1::-2])
        total += sum((2 * int(c)) // 10 + (2 * int(c)) % 10 for c in candidate[-2::-2])
        if total % 10 == 0:
            return candidate
    raise AssertionError("unreachable")


def _iban(rng: random.Random) -> str:
    bban = "".join(rng.choice("0123456789") for _ in range(23))
    numeric = int("".join(str(int(c, 36)) for c in bban + "FR00"))
    return f"FR{98 - numeric % 97:02d}{bban}"


class _Writer:
    """Écrit une cellule selon son genre / writes one cell according to its kind."""

    def __init__(self, workbook: xlsxwriter.Workbook, rng: random.Random) -> None:
        self.rng = rng
        self.formats = {
            "date": workbook.add_format({"num_format": rng.choice(["dd/mm/yyyy", "yyyy-mm-dd", "d mmm yyyy"])}),
            "datetime": workbook.add_format({"num_format": "dd/mm/yyyy hh:mm:ss"}),
            "time": workbook.add_format({"num_format": "hh:mm:ss"}),
            "duration": workbook.add_format({"num_format": "[h]:mm:ss"}),
            "money": workbook.add_format({"num_format": "#,##0.00 €"}),
            "bold": workbook.add_format({"bold": True}),
        }

    def value(self, kind: str, row: int) -> tuple[str, Any]:
        rng = self.rng
        if rng.random() < 0.06:
            return "string", rng.choice(NULLS)
        if rng.random() < 0.03:
            return "string", rng.choice(TRICKY)
        given, surname = rng.choice(GIVEN), rng.choice(SURNAMES)
        match kind:
            case "nom":
                return "string", surname.upper() if rng.random() < 0.3 else surname
            case "prenom":
                return "string", given
            case "email":
                return "string", f"{given.lower()}.{surname.lower().replace(' ', '')}{row}@exemple.fr"
            case "tel":
                number = 600000000 + rng.randrange(99_999_999)
                return ("number", number) if rng.random() < 0.5 else ("string", f"0{number}")
            case "naissance":
                born = dt.datetime(1940 + rng.randrange(60), 1 + rng.randrange(12), 1 + rng.randrange(28))
                return ("date", born) if rng.random() < 0.8 else ("string", born.strftime("%d/%m/%Y"))
            case "nir":
                nir = _nir(rng)
                return ("number", float(nir)) if rng.random() < 0.4 else ("string", nir)
            case "cp":
                return "number", rng.choice([1000, 75001, 69002, 13008, 6000, 97411])
            case "ville":
                return "string", rng.choice(CITIES)
            case "montant":
                return "money", round(rng.uniform(-500, 50_000), rng.choice([0, 2, 5]))
            case "commentaire":
                return "string", rng.choice([f"RDV avec Mme {surname}", f"Appeler {given} {surname} au 06 12 34 "
                                             f"56 {rng.randrange(10, 99)}", "RAS", "À revoir", "", "Total"])
            case "siret":
                return "number", float(_luhn(f"7328293200{rng.randrange(100, 999)}"))
            case "iban":
                return "string", _iban(rng)
            case "service":
                return "string", rng.choice(["RH", "Compta", "IT", "Ventes"])
            case "quantite":
                return "number", rng.choice([0, 1, 2.5, -3, 1e15, 1e-7, 123456789012345678, 0.1 + 0.2])
            case "actif":
                return "bool", rng.random() < 0.5
            case "heure":
                return "time", rng.random()
            case "duree":
                return "duration", rng.uniform(0, 5)
            case "date":
                return "datetime", dt.datetime(2000 + rng.randrange(25), 1 + rng.randrange(12), 1 + rng.randrange(28),
                                               rng.randrange(24), rng.randrange(60), rng.randrange(60))
            case "ref":
                return "string", f"D-{rng.randrange(10**6, 10**7)}"
            case _:
                return "string", rng.choice([*TRICKY, f"{given} {surname}", "texte libre"])

    def write(self, sheet: Any, row: int, col: int, kind: str) -> None:
        typ, value = self.value(kind, row)
        rng = self.rng
        if typ == "string":
            if value and rng.random() < 0.05:
                sheet.write_rich_string(row, col, self.formats["bold"], value[:3] or "x", value[3:] or "y")
            else:
                sheet.write_string(row, col, value)
        elif typ == "number":
            if rng.random() < 0.05:
                sheet.write_formula(row, col, f"={value}+0", None, value)
            else:
                sheet.write_number(row, col, value)
        elif typ == "money":
            sheet.write_number(row, col, value, self.formats["money"])
        elif typ == "bool":
            sheet.write_boolean(row, col, value)
        elif typ == "date":
            sheet.write_datetime(row, col, value, self.formats["date"])
        elif typ == "datetime":
            sheet.write_datetime(row, col, value, self.formats["datetime"])
        elif typ == "time":
            sheet.write_number(row, col, value, self.formats["time"])
        else:
            sheet.write_number(row, col, value, self.formats["duration"])


def _table(writer: _Writer, sheet: Any, top: int, left: int, rows: int) -> int:
    """Tableau : titre, en-têtes (une ou deux lignes), données, totaux, notes ; renvoie la ligne suivante."""
    rng = writer.rng
    kinds = rng.sample(list(HEADERS), rng.randrange(2, 9))
    row = top
    if rng.random() < 0.3:
        sheet.write_string(row, left, rng.choice(["Liste du personnel", "Export clients", "Dossier"]))
        row += 2
    if rng.random() < 0.25 and len(kinds) >= 4:
        sheet.merge_range(row, left, row, left + 1, "Identité", None)
        sheet.write_string(row, left + 2, "Coordonnées")
        row += 1
    if rng.random() < 0.85:
        sheet.write_row(row, left, [HEADERS[kind] for kind in kinds])
        row += 1
    for _ in range(rows):
        for offset, kind in enumerate(kinds):
            if rng.random() < 0.95:
                writer.write(sheet, row, left + offset, kind)
        row += 1
    if rng.random() < 0.2:
        sheet.write_string(row, left, rng.choice(["Total", "Sous-total", "TOTAL général", "Moyenne"]))
        sheet.write_number(row, left + len(kinds) - 1, 1234.5)
        row += 1
    if rng.random() < 0.2:
        sheet.write_string(row, left, "Source : export du 12/03/2024")
        row += 1
    return row + rng.randrange(1, 4)


def _form(writer: _Writer, sheet: Any, top: int) -> int:
    labels = [("Nom :", "nom"), ("Prénom :", "prenom"), ("Date de naissance :", "naissance"),
              ("Téléphone :", "tel"), ("Ville :", "ville"), ("Email :", "email")]
    for offset, (label, kind) in enumerate(writer.rng.sample(labels, writer.rng.randrange(2, 6))):
        sheet.write_string(top + offset, 0, label)
        writer.write(sheet, top + offset, 1, kind)
    return top + 8


def workbook_bytes(seed: int, rows: int = 30) -> bytes:
    """Classeur xlsx de la graine `seed` (xlsxwriter) / xlsx workbook for `seed`."""
    rng = random.Random(seed)
    buffer = io.BytesIO()
    workbook = xlsxwriter.Workbook(buffer, {"in_memory": True, "date_1904": rng.random() < 0.15,
                                            "strings_to_numbers": False, "strings_to_formulas": False,
                                            "strings_to_urls": False})
    writer = _Writer(workbook, rng)
    for index in range(rng.randrange(1, 4)):
        sheet = workbook.add_worksheet(rng.choice(["Feuil", "Données", "RH Dupont", "Clients"]) + str(index))
        shape = rng.random()
        if shape < 0.55:
            row = 0
            for _ in range(rng.randrange(1, 3)):
                row = _table(writer, sheet, row, rng.choice([0, 0, 1, 3]), rng.randrange(1, rows))
            if rng.random() < 0.3:
                _table(writer, sheet, 0, 12, rng.randrange(1, rows))
        elif shape < 0.7:
            _form(writer, sheet, 0)
        elif shape < 0.8:
            sheet.write_row(0, 0, ["Nom"] + [f"Mesure {i}" for i in range(rng.randrange(20, 40))])
            for row in range(1, rng.randrange(2, 12)):
                writer.write(sheet, row, 0, "nom")
                for col in range(1, 25):
                    writer.write(sheet, row, col, "quantite")
        elif shape < 0.9:
            for _ in range(rng.randrange(1, 6)):
                writer.write(sheet, rng.randrange(0, 40), rng.randrange(0, 30), rng.choice(list(HEADERS)))
        elif shape < 0.95 and rng.random() < 0.5:
            pass  # feuille vide / empty sheet
        else:
            sheet.add_table(0, 0, rng.randrange(2, 10), 3, {
                "name": f"Table{index}", "columns": [{"header": h} for h in ("Nom", "Email", "IBAN", "Montant")]})
            for row in range(1, 6):
                for col, kind in enumerate(("nom", "email", "iban", "montant")):
                    writer.write(sheet, row, col, kind)
        if rng.random() < 0.15:
            sheet.hide()
    workbook.close()
    return buffer.getvalue()


def csv_bytes(seed: int, rows: int = 30) -> bytes:
    """CSV de la graine `seed`, séparateur et encodage variés / CSV for `seed`, varied delimiter and encoding."""
    rng = random.Random(seed)
    delimiter = rng.choice([";", ",", "\t"])
    writer = _Writer.__new__(_Writer)
    writer.rng = rng
    kinds = rng.sample(list(HEADERS), rng.randrange(2, 7))
    lines = [delimiter.join(HEADERS[kind] for kind in kinds)]
    for row in range(rows):
        values = []
        for kind in kinds:
            _, value = writer.value(kind, row)
            text = value.strftime("%d/%m/%Y") if isinstance(value, dt.datetime) else str(value)
            values.append(text.replace(delimiter, " ").replace("\n", " ").replace("\r", " ").replace('"', "'"))
        lines.append(delimiter.join(values))
    text = "\n".join(lines) + "\n"
    return text.encode(rng.choice(["utf-8", "cp1252", "utf-8-sig"]), errors="replace")


CORPUS: list[tuple[str, Callable[[int], bytes]]] = [("xlsx", workbook_bytes), ("csv", csv_bytes)]
