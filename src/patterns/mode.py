from __future__ import annotations

from semantic.coercion import coerce, guarded
from semantic.core import STATUS_COMPLETO, STATUS_INCOMPLETO, Detection, PatternMatch
from semantic.registry import register


@register("mode")
class ModeDetector:
    pattern = "mode"

    @guarded
    def detect(self, ctx) -> Detection:
        result = Detection()
        for decl in ctx.by_stereotype("mode"):
            result.patterns.append(self._check(ctx, result, decl))
        return result

    def _check(self, ctx, result: Detection, decl: dict) -> PatternMatch:
        name = decl.get("name")
        line = decl.get("line") or ctx.line_of(name)
        expected = {"characterization": [], "externalDependence": []}
        lines = [line] if line is not None else []

        # Para este requisito, a validação do Mode limita-se à presença das
        # duas relações intrínsecas requeridas. Cardinalidade, alvo, duplicatas
        # e outras relações não determinam a validade do padrão.
        for member in (decl.get("attributes") or []):
            if member.get("kind") != "relation":
                continue
            stereotype = member.get("stereotype")
            if stereotype not in expected:
                continue
            expected[stereotype].append(member)
            mline = member.get("line") or line
            if mline is not None:
                lines.append(mline)

        missing = [st for st, found in expected.items() if not found]
        status = STATUS_INCOMPLETO if missing else STATUS_COMPLETO
        for stereotype in missing:
            result.coercions.append(coerce(
                f"ODP_MODE_SEM_{stereotype.upper()}", line,
                f"A mode {name} não declara @{stereotype}.",
                f"Acrescente uma relação @{stereotype} dentro do bloco de {name}.",
            ))

        participants = {
            "mode": name,
            "characterization": [m.get("target") for m in expected["characterization"]],
            "externalDependence": [m.get("target") for m in expected["externalDependence"]],
        }
        lines.extend(ctx.line_of(target) for target in participants["characterization"] + participants["externalDependence"])
        return PatternMatch("mode", status, sorted({n for n in lines if n is not None}), participants)
