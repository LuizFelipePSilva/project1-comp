from __future__ import annotations

import importlib

_OPTIONAL_MODULES = (
    "subkind",
    "role",
    "phase",
    "relator",
    "mode",
    "rolemixin",
)

for _module in _OPTIONAL_MODULES:
    _full_name = f"{__name__}.{_module}"
    try:
        importlib.import_module(_full_name)
    except ModuleNotFoundError as exc:
        if exc.name != _full_name:
            raise
