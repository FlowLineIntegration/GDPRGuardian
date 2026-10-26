"""Débit sur un classeur de 100 000 cellules / throughput on a 100,000-cell workbook."""

from __future__ import annotations

import datetime as dt
import random
import time
from collections.abc import Callable

import xlsxwriter
from tabular_factories import xlsx_bytes

from gdprguardian.documents import DocumentResult

_ROWS = 10_000
_COLUMNS = 10
# Plancher très prudent (machines d'intégration lentes) ; la mesure réelle est affichée.
# Very conservative floor (slow CI machines); the real figure is printed.
_MIN_CELLS_PER_SECOND = 10_000

_GIVEN = ["Jean", "Marie", "Pierre", "Sophie", "Luc", "Anne", "Paul", "Julie", "Hugo", "Emma", "Louis", "Chloé"]
_SYLLABLES = ["ber", "nard", "du", "pont", "mar", "tin", "le", "fèvre", "ro", "bert", "ga", "ron", "pe", "tit",
              "mo", "reau", "fon", "taine", "cha", "vez", "gi", "rard", "bou", "cher"]


def _hr_export() -> bytes:
    rng = random.Random(7)
    surnames = sorted({"".join(rng.choice(_SYLLABLES) for _ in range(3)).capitalize() for _ in range(4000)})
    cities = ["Paris", "Lyon", "Marseille", "Toulouse", "Nantes", "Lille", "Rennes", "Nice", "Brest", "Dijon"]

    def build(wb: xlsxwriter.Workbook) -> None:
        date = wb.add_format({"num_format": "dd/mm/yyyy"})
        sheet = wb.add_worksheet("Personnel")
        sheet.write_row(0, 0, ["Nom", "Prénom", "Email", "Téléphone", "Code postal", "Ville", "Date de naissance",
                               "Salaire", "Service", "Commentaire"])
        for row in range(1, _ROWS + 1):
            surname, given = rng.choice(surnames), rng.choice(_GIVEN)
            sheet.write_row(row, 0, [surname, given, f"{given.lower()}.{surname.lower()}{row}@exemple.fr"])
            sheet.write_number(row, 3, 600000000 + rng.randrange(99_999_999))
            sheet.write_number(row, 4, rng.choice([1000, 75001, 69002, 13008, 6000]))
            sheet.write(row, 5, rng.choice(cities))
            sheet.write_datetime(row, 6, dt.datetime(1950 + rng.randrange(50), 1 + rng.randrange(12),
                                                     1 + rng.randrange(28)), date)
            sheet.write_number(row, 7, round(rng.uniform(1500, 6000), 2))
            sheet.write(row, 8, rng.choice(["RH", "Compta", "Ventes", "IT", "Achats"]))
            sheet.write(row, 9, rng.choice(["RAS", "À revoir", f"Entretien avec {rng.choice(surnames)} prévu",
                                            f"Rappeler au 06 {rng.randrange(10, 99)} 12 34 56", ""]))

    return xlsx_bytes(build)


def test_throughput_on_100k_cells(run: Callable[..., DocumentResult], capsys) -> None:
    data = _hr_export()
    run(data)  # préchauffage (compilations, caches) / warm-up (compilation, caches)
    started = time.perf_counter()
    result = run(data, "personnel.xlsx")
    elapsed = time.perf_counter() - started
    cells = _ROWS * _COLUMNS
    throughput = cells / elapsed
    with capsys.disabled():
        print(f"\n[tabular] {cells:,} cellules en {elapsed:.2f} s : {throughput:,.0f} cellules/s ; "
              f"étapes (ms) {result.report['timings_ms']}")
    assert throughput >= _MIN_CELLS_PER_SECOND
    assert result.report["entities"]["EMAIL"] == _ROWS
    assert "@exemple.fr" not in result.markdown
