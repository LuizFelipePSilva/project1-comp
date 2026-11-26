"""
Motor de coerção e tratamento de erros semânticos

o analisador transforma a entrada inválida em uma versão válida, ao invés de reclamar, isso acontece de 2 formas:

1. Cada erro vira uma Coercion com "suggestion" (texto) e, quando possível,
   um "fix" estruturado que descreve o conserto.
2. corrigir_fonte() aplica esses consertos ao código TONTO e devolve o
   texto corrigido, sem tocar no arquivo original.

Tratamento de erros: guarded() faz com que uma falha interna em um detector
vire uma Coercion e a análise continue.
"""
from __future__ import annotations

import functools
import re
from dataclasses import dataclass

from semantic.core import Coercion, Detection

@dataclass
class FixableCoercion(Coercion):
    # Exemplos: {"op": "insert_modifier", "modifier": "disjoint"}
    #           {"op": "append", "text": "..."}
    fix: dict | None = None

    def to_dict(self) -> dict:
        data = super().to_dict()
        data["corrigivel"] = self.fix is not None
        return data


def coerce(code: str, line, message: str, suggestion: str, fix: dict | None = None) -> Coercion:
    """Cria uma Coercion; usa FixableCoercion quando há conserto automático."""
    if fix is None:
        return Coercion(line=line, code=code, message=message, suggestion=suggestion)
    return FixableCoercion(line=line, code=code, message=message,
                           suggestion=suggestion, fix=fix)

def guarded(method):
    """Decorador para detect(): captura exceções e devolve uma Detection."""

    @functools.wraps(method)
    def wrapper(self, ctx):
        try:
            return method(self, ctx)
        except Exception as exc:  # noqa: BLE001 - queremos continuar a análise
            detection = Detection()
            detection.coercions.append(coerce(
                "ODP_ERRO_INTERNO", None,
                f"Falha ao analisar o padrão '{getattr(self, 'pattern', '?')}': {exc!r}.",
                "Verifique se a ontologia foi analisada sem erros sintáticos.",
            ))
            return detection

    return wrapper

STATIC_FIXES: dict[str, dict] = {
    "ODP_SUBKIND_DISJOINT": {"op": "insert_modifier", "modifier": "disjoint"},
    "ODP_SUBKIND_OVERLAPPING": {"op": "replace_modifier", "old": "overlapping", "new": "disjoint"},
    "ODP_SUBKIND_COMPLETUDE_CONFLITANTE": {"op": "remove_modifier", "modifier": "incomplete"},
    "ODP_ROLE_DISJOINT": {"op": "remove_modifier", "modifier": "disjoint"},
    "ODP_PHASE_DISJOINT": {"op": "insert_modifier", "modifier": "disjoint"},
    "ODP_PHASE_OVERLAPPING": {"op": "replace_modifier", "old": "overlapping", "new": "disjoint"},
    "ODP_PHASE_COMPLETUDE_CONFLITANTE": {"op": "remove_modifier", "modifier": "incomplete"},
}


def _fix_of(coercion) -> dict | None:
    return getattr(coercion, "fix", None) or STATIC_FIXES.get(coercion.code)


def _edit_genset_line(text: str, fix: dict) -> str | None:
    """Altera os modificadores na linha do genset. None se não conseguir."""
    m = re.match(r"^(\s*)(.*?)(\bgenset\b.*)$", text)
    if not m:
        return None
    indent, mods, rest = m.groups()
    words = mods.split()
    op = fix["op"]
    if op == "insert_modifier":
        if fix["modifier"] in words:
            return None
        words.insert(0, fix["modifier"])
    elif op == "remove_modifier":
        if fix["modifier"] not in words:
            return None
        words.remove(fix["modifier"])
    elif op == "replace_modifier":
        if fix["old"] not in words:
            return None
        words[words.index(fix["old"])] = fix["new"]
    else:
        return None
    prefix = " ".join(words)
    return f"{indent}{prefix + ' ' if prefix else ''}{rest}"


def corrigir_fonte(source: str, coercions) -> tuple[str, list[dict]]:
    """
    Aplica os consertos automáticos ao código TONTO.

    Devolve (novo_codigo, relatorio), onde relatorio lista cada coerção com
    "aplicado": True/False. O código original não é modificado.
    """
    lines = source.split("\n")
    report: list[dict] = []
    appends: list[str] = []
    done: set[tuple] = set()

    for c in coercions:
        fix = _fix_of(c)
        entry = {"code": c.code, "line": c.line, "aplicado": False}
        report.append(entry)
        if not fix:
            continue
        if fix["op"] == "append":
            if fix["text"] not in appends:
                appends.append(fix["text"])
            entry["aplicado"] = True
            continue
        if c.line is None or not 1 <= c.line <= len(lines):
            continue
        key = (c.line, tuple(sorted(fix.items())))
        if key in done:
            entry["aplicado"] = True
            continue
        new = _edit_genset_line(lines[c.line - 1], fix)
        if new is not None:
            lines[c.line - 1] = new
            done.add(key)
            entry["aplicado"] = True

    text = "\n".join(lines)
    if appends:
        text = text.rstrip("\n") + "\n\n" + "\n\n".join(appends) + "\n"
    return text, report