"""Structure des feuilles : zones, en-têtes, formulaires, totaux / sheet structure: regions, headers, forms, totals.

Heuristiques déterministes : tableaux Excel d'abord, puis blocs séparés par des lignes ou des colonnes vides.
Deterministic heuristics: Excel tables first, then blocks split by empty rows or columns.
"""

from __future__ import annotations

import itertools
import re
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from .._text import fold
from ._package import TableSpec
from ._values import kind_of

# Fusions horizontales indexées par ligne du haut : (gauche, droite) / horizontal merges by top row.
Parents = Mapping[int, list[tuple[int, int]]]
_DIGIT_RE = re.compile(r"[0-9]")
_MAX_TITLE_ROWS = 3
_MAX_NOTE_ROWS = 5
_HEADER_SAMPLE = 20
_MAX_HEADER_LEN = 80
_MAX_LABEL_LEN = 60
# Au-delà de 2 colonnes vides consécutives, deux zones distinctes / beyond 2 empty columns, two regions.
_COLUMN_GAP = 2
_TOTAL_WORDS = ("total", "totaux", "sous-total", "sous total", "somme", "moyenne", "grand total", "subtotal",
                "summe", "gesamt", "totale")
_TOTAL_INITIALS = frozenset("tTsSmMgG")  # préfiltre avant repliement / prefilter before folding
# `fold` replie caractère par caractère, sans changer la longueur : le repli d'un préfixe court suffit à écarter
# une ligne. `fold` maps character by character, keeping the length: folding a short prefix rules a row out.
_TOTAL_PREFIX = re.compile("|".join(re.escape(word) for word in sorted(_TOTAL_WORDS, key=len, reverse=True)))
_TOTAL_HEAD = max(map(len, _TOTAL_WORDS)) + 1
_FORM_CHUNK = 4_096


@dataclass(slots=True)
class Region:
    """Zone d'une feuille ; lignes et colonnes en coordonnées de grille / region in grid coordinates.

    kind : 'table', 'form' (libellé -> valeur) ou 'text' (cellules isolées) / or isolated cells.
    """

    kind: str
    top: int
    bottom: int
    columns: list[int]
    headers: list[str] = field(default_factory=list)
    header_rows: list[int] = field(default_factory=list)
    data_rows: list[int] = field(default_factory=list)
    title_rows: list[int] = field(default_factory=list)
    note_rows: list[int] = field(default_factory=list)
    total_rows: set[int] = field(default_factory=set)
    pairs: list[tuple[int, int, int]] = field(default_factory=list)


def detect_regions(texts: list[list[str]], raws: list[list[Any]], merged: Sequence[tuple[int, int, int, int]],
                   tables: Sequence[TableSpec], is_label: Callable[[str], bool]) -> list[Region]:
    """Zones d'une grille, de haut en bas puis de gauche à droite / regions, top to bottom then left to right.

    Coût linéaire en cellules et en fusions, même pour des fusions ou tableaux forgés en grand nombre.
    Linear in cells and merges, even with crafted merges or tables in large numbers.
    """
    height = len(texts)
    width = len(texts[0]) if height else 0
    regions: list[Region] = []
    masks: list[tuple[int, int, int, int]] = []
    for spec in tables:
        bottom, right = min(spec.bottom, height - 1), min(spec.right, width - 1)
        if spec.top < 0 or spec.left < 0 or spec.top > bottom or spec.left > right:
            continue
        # Tableaux qui se chevauchent (fichier forgé) : le premier seul, sinon cellules traitées plusieurs fois.
        # Overlapping tables (forged file): the first only, else cells would be processed several times.
        if any(m_top <= bottom and spec.top <= m_bottom and m_left <= right and spec.left <= m_right
               for m_top, m_left, m_bottom, m_right in masks):
            continue
        regions.append(_table_region(texts, spec, bottom, right))
        masks.append((spec.top, spec.left, bottom, right))
    view = _masked(texts, masks) if masks else texts
    counts = [width - row.count("") for row in view]
    # Une fusion verticale relie les lignes qu'elle couvre (balayage par différences) / a vertical merge links
    # the rows it covers (difference sweep).
    delta = [0] * (height + 1)
    parents: dict[int, list[tuple[int, int]]] = {}
    for top, left, bottom, right in merged:
        first, last = max(top, 0), min(bottom, height - 1)
        if first <= last:
            delta[first] += 1
            delta[last + 1] -= 1
        if right > left:
            parents.setdefault(top, []).append((left, right))
    for row, covered in enumerate(itertools.accumulate(delta[:height])):
        if covered and not counts[row]:
            counts[row] = 1
    for top, bottom in _runs(counts):
        regions.extend(_split_block(view, raws, top, bottom, parents, is_label))
    regions.sort(key=lambda region: (region.top, region.columns[0] if region.columns else 0))
    return _attach_titles(regions)


def _attach_titles(regions: list[Region]) -> list[Region]:
    """Une cellule seule juste au-dessus d'un tableau en devient le titre / a lone cell above a table is its title."""
    attached: list[Region] = []
    for region in regions:
        previous = attached[-1] if attached else None
        if (previous is not None and region.kind == "table" and previous.kind == "text"
                and len(previous.data_rows) == 1 and 0 < region.top - previous.bottom <= 2
                and set(previous.columns) <= set(region.columns) and len(region.title_rows) < _MAX_TITLE_ROWS):
            attached.pop()
            region.title_rows = previous.data_rows + region.title_rows
        attached.append(region)
    return attached


def _runs(counts: Sequence[int]) -> list[tuple[int, int]]:
    """Suites de lignes non vides / runs of non-empty rows."""
    runs: list[tuple[int, int]] = []
    start = None
    for index, count in enumerate(counts):
        if count and start is None:
            start = index
        elif not count and start is not None:
            runs.append((start, index - 1))
            start = None
    if start is not None:
        runs.append((start, len(counts) - 1))
    return runs


def _masked(texts: list[list[str]], masks: Sequence[tuple[int, int, int, int]]) -> list[list[str]]:
    """Copie où les cellules des tableaux Excel sont vidées / copy with Excel-table cells blanked."""
    view = list(texts)
    for top, left, bottom, right in masks:
        blank = [""] * (right - left + 1)
        for row in range(top, bottom + 1):
            if view[row] is texts[row]:
                view[row] = list(texts[row])
            view[row][left:right + 1] = blank
    return view


def _split_block(view: list[list[str]], raws: list[list[Any]], top: int, bottom: int, parents: Parents,
                 is_label: Callable[[str], bool]) -> list[Region]:
    block = view[top:bottom + 1]
    filled = [index for index, column in enumerate(zip(*block, strict=True)) if column.count("") < len(column)]
    groups: list[list[int]] = []
    for column in filled:
        if groups and column - groups[-1][-1] <= _COLUMN_GAP:
            groups[-1].append(column)
        else:
            groups.append([column])
    regions: list[Region] = []
    for columns in groups:
        if len(groups) == 1:
            regions.append(_classify(view, raws, top, bottom, columns, parents, is_label))
            continue
        counts = _filled(view, range(top, bottom + 1), columns)
        for start, end in _runs(counts):
            regions.append(_classify(view, raws, top + start, top + end, columns, parents, is_label))
    return regions


def _filled(view: list[list[str]], rows: Iterable[int], columns: Sequence[int]) -> list[int]:
    """Cellules non vides par ligne ; les colonnes intercalaires sont vides par construction, d'où un
    décompte en C sur la tranche. Non-empty cells per row; gap columns are empty by construction, so a
    C-level count over the slice is exact."""
    first, last = columns[0], columns[-1] + 1
    span = last - first
    return [span - view[row][first:last].count("") for row in rows]


def _table_region(texts: list[list[str]], spec: TableSpec, bottom: int, right: int) -> Region:
    columns = list(range(spec.left, right + 1))
    rows = list(range(spec.top, bottom + 1))
    header_rows = rows[:spec.header_rows]
    if header_rows and len(spec.columns) == len(columns):
        headers = [name.strip() for name in spec.columns]
    elif header_rows:
        headers = [texts[header_rows[0]][column].strip() for column in columns]
    else:
        headers = [""] * len(columns)
    data_rows = rows[spec.header_rows:]
    totals = set(data_rows[-spec.totals_rows:]) if spec.totals_rows and data_rows and bottom == spec.bottom else set()
    return Region("table", spec.top, bottom, columns, headers, header_rows, data_rows, total_rows=totals)


def _classify(view: list[list[str]], raws: list[list[Any]], top: int, bottom: int, columns: list[int],
              parents: Parents, is_label: Callable[[str], bool]) -> Region:
    rows = list(range(top, bottom + 1))
    filled = _filled(view, rows, columns)
    if sum(filled) == 1 or (len(columns) == 1 and len(rows) < 3):
        return Region("text", top, bottom, columns, data_rows=rows)
    titles: list[int] = []
    if len(columns) >= 3:
        while len(titles) < _MAX_TITLE_ROWS and len(titles) < len(rows) - 1 and filled[len(titles)] == 1:
            titles.append(rows[len(titles)])
    body = rows[len(titles):]
    pairs = _form_pairs(view, raws, body, columns, is_label)
    if pairs is not None:
        return Region("form", top, bottom, columns, title_rows=titles, pairs=pairs)
    header_count = _header_count(view, raws, body, columns, parents, is_label)
    header_rows = body[:header_count]
    data = body[header_count:]
    notes: list[int] = []
    if len(columns) >= 3:
        while data and len(notes) < _MAX_NOTE_ROWS and sum(1 for c in columns if view[data[-1]][c]) == 1 \
                and not _is_total(view, data[-1], columns):
            notes.insert(0, data.pop())
    headers = _join_headers(view, header_rows, columns, parents) if header_rows else [""] * len(columns)
    known: dict[str, bool] = {}
    totals = {row for row in data if _is_total(view, row, columns, known)}
    return Region("table", top, bottom, columns, headers, header_rows, data, titles, notes, totals)


def _signature(text: str) -> tuple[bool, bool, bool, int]:
    stripped = text.strip()
    length = len(stripped)
    return ("@" in stripped, _DIGIT_RE.search(stripped) is not None, stripped.isupper() and length > 1,
            0 if length <= 12 else 1 if length <= 30 else 2)


def _header_like(view: list[list[str]], raws: list[list[Any]], row: int, below: Sequence[int],
                 columns: Sequence[int], is_label: Callable[[str], bool]) -> bool:
    """Ligne de libellés courts, uniques, au-dessus de données d'un autre type / short unique labels above data."""
    cells = [(column, view[row][column].strip()) for column in columns if view[row][column]]
    if not cells or any(len(text) > _MAX_HEADER_LEN for _, text in cells):
        return False
    kinds = [kind_of(raws[row][column], text) for column, text in cells]
    if kinds.count("t") < 0.8 * len(kinds):
        return False
    if len({fold(text) for _, text in cells}) < len(cells):
        return False
    if any(is_label(text) for _, text in cells):
        return True
    sample = below[:_HEADER_SAMPLE]
    typed = mismatched = compared = 0
    for column, text in cells:
        values = [(raws[r][column], view[r][column]) for r in sample if view[r][column]]
        if not values:
            continue
        data_kinds = [kind_of(raw, value) for raw, value in values]
        if 2 * data_kinds.count("t") < len(data_kinds):
            typed += 1
            continue
        compared += 1
        dominant = Counter(_signature(value) for _, value in values).most_common(1)[0][0]
        mismatched += _signature(text) != dominant
    return typed > 0 or (compared > 0 and 2 * mismatched >= compared)


def _header_count(view: list[list[str]], raws: list[list[Any]], body: Sequence[int], columns: Sequence[int],
                  parents: Parents, is_label: Callable[[str], bool]) -> int:
    if len(body) < 2 or not _header_like(view, raws, body[0], body[1:], columns, is_label):
        return 0
    if len(body) >= 3 and _is_parent_row(view, body[0], body[1], columns, parents) \
            and _header_like(view, raws, body[1], body[2:], columns, is_label):
        return 2
    return 1


def _is_parent_row(view: list[list[str]], row: int, child: int, columns: Sequence[int], parents: Parents) -> bool:
    """En-tête parent : fusion horizontale, ou cases vides que la ligne suivante remplit / parent header row."""
    if parents.get(row):
        return True
    gaps = [column for column in columns if not view[row][column]]
    return bool(gaps) and any(view[child][column] for column in gaps)


def _span_owners(spans: Sequence[tuple[int, int]], columns: Sequence[int]) -> dict[int, int]:
    """Colonne -> colonne de gauche de la fusion qui la couvre, en un balayage (colonnes croissantes).

    Column -> left column of the merge covering it, in one sweep (ascending columns).
    """
    ordered = sorted(spans)
    owners: dict[int, int] = {}
    best_left = best_right = -1
    index = 0
    for column in columns:
        while index < len(ordered) and ordered[index][0] <= column:
            left, right = ordered[index]
            if right > best_right:
                best_left, best_right = left, right
            index += 1
        if best_right >= column:
            owners[column] = best_left
    return owners


def _join_headers(view: list[list[str]], header_rows: Sequence[int], columns: Sequence[int],
                  parents: Parents) -> list[str]:
    """« Parent / Enfant » pour les en-têtes sur deux lignes / 'Parent / Child' for two-row headers."""
    last = header_rows[-1]
    if len(header_rows) == 1:
        return [view[last][column].strip() for column in columns]
    parent_row = header_rows[0]
    spans = parents.get(parent_row, [])
    owners = _span_owners(spans, columns) if spans else {}
    labels: dict[int, str] = {}
    current = ""
    for column in columns:
        value = view[parent_row][column].strip()
        if spans:
            owner = owners.get(column)
            labels[column] = view[parent_row][owner].strip() if owner is not None else value
        else:
            # Sans information de fusion (ODS, CSV) : report vers la droite / no merge info: forward fill.
            current = value or current
            labels[column] = current
    headers = []
    for column in columns:
        parent, child = labels[column], view[last][column].strip()
        headers.append(f"{parent} / {child}" if parent and child and parent != child else child or parent)
    return headers


def _form_pairs(view: list[list[str]], raws: list[list[Any]], rows: Sequence[int], columns: Sequence[int],
                is_label: Callable[[str], bool]) -> list[tuple[int, int, int]] | None:
    """Feuille formulaire : colonnes libellé / valeur alternées / form sheet: alternating label/value columns."""
    if len(columns) not in (2, 4, 6) or len(rows) < 2:
        return None
    for label_column in columns[0::2]:
        labels = [view[row][label_column].strip() for row in rows if view[row][label_column]]
        if len(labels) < max(2, 0.6 * len(rows)) or any(len(label) > _MAX_LABEL_LEN for label in labels):
            return None
        # Conditions pures, de la moins chère à la plus chère : même décision / pure tests, cheapest first.
        if not _mostly_distinct(labels):
            return None
        kinds = [kind_of(raws[row][label_column], view[row][label_column]) for row in rows if view[row][label_column]]
        if kinds.count("t") < 0.9 * len(kinds):
            return None
        colons = sum(label.endswith(":") for label in labels)
        hits = sum(is_label(label.rstrip(" :")) for label in labels)
        if 2 * colons < len(labels) and hits < 2:
            return None
    return [(row, columns[i], columns[i + 1]) for row in rows for i in range(0, len(columns), 2)
            if view[row][columns[i]] or view[row][columns[i + 1]]]


def _mostly_distinct(labels: list[str]) -> bool:
    """`len({fold(l) for l in labels}) >= 0.9 * len(labels)`, arrêté dès que l'issue est sûre : les libellés
    restants ne peuvent plus atteindre le seuil. Stops as soon as the outcome is certain: the remaining labels
    can no longer reach the threshold."""
    threshold = 0.9 * len(labels)
    seen: set[str] = set()
    for start in range(0, len(labels), _FORM_CHUNK):
        stop = min(start + _FORM_CHUNK, len(labels))
        seen.update(map(fold, labels[start:stop]))
        if len(seen) + (len(labels) - stop) < threshold:
            return False
    return len(seen) >= threshold


def _is_total(view: list[list[str]], row: int, columns: Sequence[int], known: dict[str, bool] | None = None) -> bool:
    """Ligne de total : sa première cellule non vide commence par un mot de total. `known` garde la réponse de
    chaque texte déjà vu (fonction pure). Total row: its first non-empty cell starts with a total word; `known`
    keeps the answer for each text already seen (pure function)."""
    cells = view[row]
    for column in columns:
        value = cells[column]
        if value:
            if known is None:
                return _total_text(value)
            answer = known.get(value)
            if answer is None:
                answer = known[value] = _total_text(value)
            return answer
    return False


def _total_text(value: str) -> bool:
    stripped = value.lstrip()
    if stripped[:1] not in _TOTAL_INITIALS or _TOTAL_PREFIX.match(fold(stripped[:_TOTAL_HEAD])) is None:
        return False
    folded = fold(stripped.rstrip())
    return any(folded.startswith(word) and (len(folded) == len(word) or not folded[len(word)].isalpha())
               for word in _TOTAL_WORDS)
