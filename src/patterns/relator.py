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
        materials = [
            relation for relation in ctx.relations
            if relation.get("stereotype") == "material"
        ]

        for declaration in relators:
            detection.patterns.append(
                self._check(ctx, detection, declaration, materials)
            )
        return detection

    def _check(self, ctx, detection, declaration, materials) -> PatternMatch:
        name = declaration.get("name")
        line = declaration.get("line") or ctx.line_of(name)
        status = STATUS_COMPLETO

        mediations = [
            relation
            for relation in (declaration.get("attributes") or [])
            if relation.get("kind") == "relation"
            and relation.get("stereotype") == "mediation"
        ]
        mediations.extend(
            relation for relation in ctx.relations
            if relation.get("stereotype") == "mediation"
            and relation.get("source") == name
        )

        all_targets = list(dict.fromkeys(
            mediation.get("target") for mediation in mediations
        ))
        valid_targets: list[str] = []
        lines = [line]

        for mediation in mediations:
            target = mediation.get("target")
            mediation_line = mediation.get("line") or line
            if mediation.get("line") is not None:
                lines.append(mediation["line"])

            if not ctx.is_class(target):
                status = STATUS_INVALIDO
                detection.coercions.append(coerce(
                    "ODP_RELATOR_ALVO_DESCONHECIDO", mediation_line,
                    f"A mediação de {name} aponta para {target}, que não foi declarado.",
                    f"Declare a entidade {target} ou corrija o nome da mediação.",
                ))
                continue

            if ctx.stereotype_of(target) not in ROLE_LIKE:
                status = STATUS_INVALIDO
                detection.coercions.append(coerce(
                    "ODP_RELATOR_ALVO_NAO_ROLE", mediation_line,
                    f"A mediação de {name} aponta para {target} "
                    f"({ctx.stereotype_of(target)}), mas deveria ser um role.",
                    f"Declare {target} com um estereótipo de role.",
                ))
                continue

            if target not in valid_targets:
                valid_targets.append(target)

        if len(valid_targets) < 2:
            status = STATUS_INVALIDO
            missing = 2 - len(valid_targets)
            detection.coercions.append(coerce(
                "ODP_RELATOR_MEDIACOES", line,
                f"O relator {name} possui {len(valid_targets)} mediação(ões) "
                "para roles distintos e declarados; são necessárias ao menos 2.",
                f"Acrescente {missing} mediação(ões) para role(s) declarado(s) "
                "e distinto(s), usando '@mediation [1..*] -- [1..*] <Role>'.",
            ))

        material = (
            self._find_material(valid_targets, materials)
            if len(valid_targets) >= 2 else None
        )
        if material is not None:
            if material.get("line") is not None:
                lines.append(material["line"])
        elif len(valid_targets) >= 2:
            if status == STATUS_COMPLETO:
                status = STATUS_INCOMPLETO
            first, second = valid_targets[:2]
            text = (
                f"@material relation {first} [1..*] -- relatedTo -- [1..*] {second}"
            )
            detection.coercions.append(coerce(
                "ODP_RELATOR_SEM_MATERIAL", line,
                f"O relator {name} não tem @material relation entre "
                f"roles mediados válidos.",
                f"Acrescente:\n{text}",
                fix={"op": "append", "text": text},
            ))

        return PatternMatch(
            pattern=PATTERN,
            status=status,
            lines=sorted({number for number in lines if number is not None}),
            participants={
                "relator": name,
                "mediations": valid_targets,
                "material": (
                    material.get("name")
                    or f"{material['source']}-{material['target']}"
                ) if material else None,
            },
        )

    @staticmethod
    def _find_material(targets, materials):
        wanted = set(targets)
        for relation in materials:
            endpoints = {relation.get("source"), relation.get("target")}
            if len(endpoints) == 2 and endpoints <= wanted:
                return relation
        return None
