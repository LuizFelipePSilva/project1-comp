from __future__ import annotations

from semantic.coercion import coerce, guarded
from semantic.core import (
    STATUS_COMPLETO,
    STATUS_INCOMPLETO,
    STATUS_INVALIDO,
    Detection,
    PatternMatch,
)
from semantic.registry import register

PATTERN = "relator"
ROLE_LIKE = {"role", "roleMixin", "historicalRole", "historicalRoleMixin"}


@register(PATTERN)
class RelatorDetector:
    pattern = PATTERN

    @guarded
    def detect(self, ctx) -> Detection:
        detection = Detection()
        relators = ctx.by_stereotype(PATTERN)
        materials = [r for r in ctx.relations if r.get("stereotype") == "material"]
        for decl in relators:
            detection.patterns.append(self._check(ctx, detection, decl, materials))
        return detection

    def _check(self, ctx, detection, decl, materials) -> PatternMatch:
        name = decl.get("name")
        line = decl.get("line") or ctx.line_of(name)
        status = STATUS_COMPLETO

        mediations = [m for m in (decl.get("attributes") or [])
                      if m.get("kind") == "relation" and m.get("stereotype") == "mediation"]
        mediations += [r for r in ctx.relations
                       if r.get("stereotype") == "mediation" and r.get("source") == name]
        targets = list(dict.fromkeys(m.get("target") for m in mediations))
        lines = [line] + [m.get("line") for m in mediations]

        if len(targets) < 2:
            status = STATUS_INVALIDO
            falta = 2 - len(targets)
            detection.coercions.append(coerce(
                "ODP_RELATOR_MEDIACOES", line,
                f"O relator {name} tem {len(targets)} mediação(ões) para classes "
                "distintas; são necessárias ao menos 2.",
                f"Dentro de 'relator {name}', acrescente {falta} linha(s) como "
                "'@mediation [1..*] -- [1..*] <Role>'.",
            ))

        for m in mediations:
            target = m.get("target")
            mline = m.get("line") or line
            if not ctx.is_class(target):
                status = STATUS_INVALIDO
                detection.coercions.append(coerce(
                    "ODP_RELATOR_ALVO_DESCONHECIDO", mline,
                    f"A mediação de {name} aponta para {target}, que não foi declarado.",
                    f"Declare 'role {target} specializes <Kind>' ou corrija o nome.",
                ))
            elif ctx.stereotype_of(target) not in ROLE_LIKE:
                status = STATUS_INVALIDO
                detection.coercions.append(coerce(
                    "ODP_RELATOR_ALVO_NAO_ROLE", mline,
                    f"A mediação de {name} aponta para {target} "
                    f"({ctx.stereotype_of(target)}), mas deveria ser um role.",
                    f"Declare {target} como 'role {target} specializes <Kind>'.",
                ))

        material = self._find_material(targets, materials)
        if material is not None:
            lines.append(material.get("line"))
        elif len(targets) >= 2:
            if status == STATUS_COMPLETO:
                status = STATUS_INCOMPLETO
            a, b = targets[0], targets[1]
            text = f"@material relation {a} [1..*] -- relatedTo -- [1..*] {b}"
            detection.coercions.append(coerce(
                "ODP_RELATOR_SEM_MATERIAL", line,
                f"O relator {name} não tem @material relation entre {a} e {b}.",
                f"Acrescente:\n{text}",
                fix={"op": "append", "text": text},
            ))

        return PatternMatch(
            pattern=PATTERN,
            status=status,
            lines=sorted({n for n in lines if n is not None}),
            participants={
                "relator": name,
                "mediations": targets,
                "material": (material.get("name") or f"{material['source']}-{material['target']}")
                if material else None,
            },
        )

    @staticmethod
    def _find_material(targets, materials):
        wanted = set(targets)
        for rel in materials:
            ends = {rel.get("source"), rel.get("target")}
            if len(ends) == 2 and ends <= wanted:
                return rel
        return None