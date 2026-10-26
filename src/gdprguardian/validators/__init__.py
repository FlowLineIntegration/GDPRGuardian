"""Validateurs d'identifiants / identifier validators.

Contrat : `fn(candidate: str) -> str | None`, la valeur canonique si valide, sinon None.
Contract: `fn(candidate: str) -> str | None`, the canonical value if valid, else None.
Les packs les référencent par "module.fonction" (ex. "fr.nir") / packs reference them as "module.func".
"""

from __future__ import annotations

import importlib
from collections.abc import Callable
from functools import cache

Validator = Callable[[str], "str | None"]


@cache
def resolve(name: str) -> Validator:
    """'fr.nir' -> gdprguardian.validators.fr.nir ; 'pkg.mod:func' pour un module externe / external."""
    if ":" in name:
        module_name, func_name = name.split(":", 1)
    else:
        short_module, func_name = name.rsplit(".", 1)
        module_name = f"{__name__}.{short_module}"
    func = getattr(importlib.import_module(module_name), func_name, None)
    if not callable(func):
        raise ValueError(f"Validateur inconnu / unknown validator: {name}")
    return func
