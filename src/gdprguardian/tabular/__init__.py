"""Tableurs (xlsx, xlsm, xls, xlsb, ods, csv, tsv) -> Markdown anonymisé / spreadsheets -> anonymised Markdown.

Valeurs en cache seulement (aucune formule évaluée), feuilles masquées exclues par défaut, une seule portée
irréversible pour tout le classeur. Cached values only (no formula evaluated), hidden sheets excluded by
default, one irreversible scope for the whole workbook.
"""

from ._pipeline import anonymize_workbook

__all__ = ["anonymize_workbook"]
