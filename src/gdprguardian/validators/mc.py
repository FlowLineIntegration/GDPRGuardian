"""Validateurs Monaco : TVA (régime français), RCI, téléphones / Monaco validators: VAT, RCI, phones.

Chaque fonction renvoie la valeur canonique (sans séparateurs) ou None / each function returns the
canonical value or None.
"""

from __future__ import annotations

import re

from .._text import strip_separators
from .fr import tva as _french_tva

_NON_DIGITS = re.compile(r"[^0-9]")
# RCI : année (2 chiffres), type (S société, C ou SC civile, P personne physique), rang (5 chiffres).
# RCI: year (2 digits), type (S company, C or SC civil, P natural person), serial (5 digits).
_RCI_RE = re.compile(r"[0-9]{2}(?:SC|[CPS])[0-9]{5}")


def tva(candidate: str) -> str | None:
    """TVA monégasque : numéro français FR + clé + 9 chiffres commençant par 000 / French scheme, 000 prefix."""
    value = strip_separators(candidate).upper()
    if not value.startswith("FR"):
        value = "FR" + value
    if len(value) != 13 or value[4:7] != "000":
        return None
    return _french_tva(value)


def rci(candidate: str) -> str | None:
    """Numéro du Répertoire du commerce et de l'industrie, ex. 99 S 03847 -> 99S03847."""
    value = strip_separators(candidate).upper()
    return value if _RCI_RE.fullmatch(value) else None


def phone(candidate: str) -> str | None:
    """Téléphone monégasque, forme E.164 : fixe 8 chiffres (9…), mobile 8 (4…) ou 9 (6…).

    Monaco phone, E.164 form. Source : https://en.wikipedia.org/wiki/Telephone_numbers_in_Monaco
    """
    digits = _NON_DIGITS.sub("", candidate)
    if candidate.lstrip().startswith("+") or digits.startswith("00"):
        digits = digits.removeprefix("00")
        if not digits.startswith("377"):
            return None
        digits = digits[3:]
    # Le 0 ne précède que les mobiles 6… / the trunk 0 only precedes 6… mobiles.
    digits = digits.removeprefix("0")
    if (len(digits) == 8 and digits[0] in "3489") or (len(digits) == 9 and digits[0] in "67"):
        return "+377" + digits
    return None
