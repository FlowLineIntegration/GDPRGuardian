"""Opérateurs de remplacement, tous irréversibles / replacement operators, all irreversible."""

from __future__ import annotations

import re
from collections.abc import Callable

from .scope import Scope
from .types import Span

_YEAR_RE = re.compile(r"(?:18|19|20)[0-9]{2}")

Operator = Callable[[Span, str, Scope], str]


def replace(span: Span, original: str, scope: Scope) -> str:
    """Balise typée numérotée, cohérente dans la portée / consistent typed placeholder."""
    return scope.placeholder(span.label, span.entity, span.value or original)


def redact(span: Span, original: str, scope: Scope) -> str:
    """Balise sans numéro (perd la cohérence) / placeholder without index."""
    return f"[{scope.label_text(span.label)}]"


def mask(span: Span, original: str, scope: Scope) -> str:
    """Garde les 4 derniers caractères alphanumériques / keeps the last 4 alphanumerics."""
    kept = 0
    chars = list(original)
    for i in range(len(chars) - 1, -1, -1):
        if chars[i].isalnum():
            if kept < 4:
                kept += 1
            else:
                chars[i] = "*"
    return "".join(chars)


def generalize(span: Span, original: str, scope: Scope) -> str:
    """Date -> année, code postal -> département ; sinon balise / date -> year, postcode -> department."""
    if span.entity in ("BIRTH_DATE", "DATE"):
        m = _YEAR_RE.search(span.value or original)
        if m:
            return m.group()
    if span.entity == "POSTAL_CODE":
        digits = "".join(c for c in original if c.isdigit())
        if len(digits) == 5:
            return digits[:3] + "xx" if digits.startswith("97") or digits.startswith("98") else digits[:2] + "xxx"
    return replace(span, original, scope)


def keep(span: Span, original: str, scope: Scope) -> str:
    return original


OPERATORS: dict[str, Operator] = {
    "replace": replace,
    "redact": redact,
    "mask": mask,
    "generalize": generalize,
    "keep": keep,
}

# Les secrets ne sont jamais conservés, même partiellement / secrets are never kept, even partially.
FORCED_REPLACE = frozenset({"SECRET"})

# Opérateurs que le noyau Rust reproduit à l'identique, par fonction ; tout autre reste rendu en Python.
# Operators the Rust core reproduces exactly, by function; any other keeps rendering in Python.
NATIVE_NAMES: dict[Operator, str] = {function: name for name, function in OPERATORS.items()}


def get_operator(name: str) -> Operator:
    try:
        return OPERATORS[name]
    except KeyError:
        raise ValueError(f"Opérateur inconnu / unknown operator: {name} ({sorted(OPERATORS)})") from None
