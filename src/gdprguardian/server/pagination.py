"""Pages de caractères, sans couper une ligne ni une balise / character pages, no split line or placeholder.

Les clients MCP plafonnent la taille d'un résultat d'outil (environ 25 000 jetons pour Claude Code) :
le Markdown est servi par pages d'environ 40 000 caractères. MCP clients cap tool-result size, so the
Markdown is served in pages of about 40,000 characters.
"""

from __future__ import annotations

from bisect import bisect_left

# Plus longue balise plausible, ex. « [DATE_NAISSANCE_1234567] » / longest plausible placeholder.
_PLACEHOLDER_MAX = 48


def page_bounds(text: str, page_chars: int) -> list[int]:
    """Bornes `[0, b1, …, len(text)]` ; une coupe recule d'au plus un quart de page (ou d'une balise).

    Bounds `[0, b1, …, len(text)]`; a cut moves back by at most a quarter page (or one placeholder),
    preferably right after a newline, then after a space, and never inside a `[PLACEHOLDER_N]`.
    """
    if page_chars <= 0:
        raise ValueError("page_chars > 0")
    length = len(text)
    bounds = [0]
    start = 0
    slack = page_chars // 4
    while length - start > page_chars:
        end = start + page_chars
        floor = end - slack
        cut = text.rfind("\n", floor, end)
        if cut < 0:
            cut = text.rfind(" ", floor, end)
        if cut >= 0:
            end = cut + 1
        else:
            # Coupe franche : ne pas trancher une balise / hard cut: do not split a placeholder.
            opening = text.rfind("[", max(start + 1, end - _PLACEHOLDER_MAX), end)
            if opening > start and text.find("]", opening, end) < 0:
                end = opening
        bounds.append(end)
        start = end
    bounds.append(length)
    return bounds


def merge_interval(intervals: list[tuple[int, int]], start: int, end: int) -> list[tuple[int, int]]:
    """Ajoute [start, end) à une liste triée d'intervalles disjoints, sur place / adds [start, end) in place.

    Recherche dichotomique puis fusion des seuls voisins : O(log k) comparaisons, quel que soit l'ordre de
    lecture des pages. Binary search, then only neighbours are merged, whatever the page reading order.
    """
    first = bisect_left(intervals, (start, start))
    if first and intervals[first - 1][1] >= start:
        first -= 1
        start = intervals[first][0]
    last = first
    while last < len(intervals) and intervals[last][0] <= end:
        end = max(end, intervals[last][1])
        last += 1
    intervals[first:last] = [(start, end)]
    return intervals
