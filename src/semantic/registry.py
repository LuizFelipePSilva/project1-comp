
from __future__ import annotations

import itertools

DEFAULT_ORDER = {
    "subkind": 10,
    "role": 20,
    "phase": 30,
    "relator": 40,
    "mode": 50,
    "rolemixin": 60,
}

_DETECTORS: dict[str, tuple[int, int, object]] = {}
_counter = itertools.count()


def register(pattern: str, order: int | None = None):
    """Decorador que registra a classe do detector sob o nome do padrão."""

    def decorator(cls):
        cls.pattern = pattern
        priority = DEFAULT_ORDER.get(pattern, 100) if order is None else order
        _DETECTORS[pattern] = (priority, next(_counter), cls())
        return cls

    return decorator


def ordered() -> list:
    """Detectores na ordem de execução (prioridade + ordem de registro)."""
    return [detector for _, _, detector in sorted(_DETECTORS.values())]


def get(pattern: str):
    entry = _DETECTORS.get(pattern)
    return entry[2] if entry else None


def registered_names() -> list[str]:
    ordered_items = sorted(_DETECTORS.items(), key=lambda item: item[1][:2])
    return [pattern for pattern, _ in ordered_items]
