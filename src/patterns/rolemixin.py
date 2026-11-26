from __future__ import annotations

from semantic.coercion import coerce, guarded
from semantic.core import STATUS_COMPLETO, STATUS_INCOMPLETO, STATUS_INVALIDO, Detection, PatternMatch
from semantic.registry import register


@register("rolemixin")
class RoleMixinDetector:
    pattern = "rolemixin"

    @guarded
    def detect(self, ctx) -> Detection:
        result = Detection()
        mixins = ctx.by_stereotype("roleMixin")
        for mixin in mixins:
            result.patterns.append(self._check(ctx, result, mixin))
        return result

    def _check(self, ctx, result: Detection, decl: dict) -> PatternMatch:
        name = decl.get("name")
        line = decl.get("line") or ctx.line_of(name)
        matching = [g for g in ctx.gensets if g.get("general") == name]
        # Sem genset, só há evidência suficiente quando existem pelo menos dois
        # roles diretamente ligados a kinds distintos. Não associamos ao mixin
        # todos os roles do pacote por mera coincidência.
        if matching:
            role_names = list(dict.fromkeys(
                r for g in matching for r in ctx.specifics(g)
                if ctx.stereotype_of(r) == "role"
            ))
        else:
            kind_by_role = {}
            for role in ctx.by_stereotype("role"):
                rname = role.get("name")
                kind = next((p for p in ctx.parents_of(rname) if ctx.is_kind(p)), None)
                if kind:
                    kind_by_role[rname] = kind
            role_names = list(kind_by_role)
        status = STATUS_COMPLETO if matching else STATUS_INCOMPLETO
        genset = matching[0] if matching else None
        specifics = ctx.specifics(genset) if genset else role_names

        if genset:
            bad = [r for r in specifics if ctx.stereotype_of(r) != "role"]
            if bad:
                status = STATUS_INVALIDO
                result.coercions.append(coerce(
                    "ODP_ROLEMIXIN_MEMBRO", ctx.genset_line(genset),
                    f"O genset do roleMixin {name} lista membros que não são roles: {', '.join(bad)}.",
                    "Liste apenas classes declaradas com estereótipo role.",
                ))
            role_specifics = [r for r in specifics if ctx.stereotype_of(r) == "role"]
            if len(set(role_specifics)) < 2:
                status = STATUS_INVALIDO
                result.coercions.append(coerce(
                    "ODP_ROLEMIXIN_QUANTIDADE", ctx.genset_line(genset),
                    f"O genset do roleMixin {name} deve agrupar ao menos dois roles distintos.",
                    "Acrescente pelo menos dois roles em 'specifics'.",
                ))
            if not ctx.has_modifier(genset, "disjoint"):
                status = STATUS_INVALIDO
                result.coercions.append(coerce(
                    "ODP_ROLEMIXIN_DISJOINT", ctx.genset_line(genset),
                    f"O genset do roleMixin {name} não declara 'disjoint'.",
                    "Acrescente 'disjoint' antes de 'genset'.",
                    fix={"op": "insert_modifier", "modifier": "disjoint"},
                ))
            if not ctx.has_modifier(genset, "complete"):
                status = STATUS_INVALIDO
                result.coercions.append(coerce(
                    "ODP_ROLEMIXIN_COMPLETE", ctx.genset_line(genset),
                    f"O genset do roleMixin {name} não declara 'complete'.",
                    "Acrescente 'complete' antes de 'genset'.",
                    fix={"op": "insert_modifier", "modifier": "complete"},
                ))

        role_parents = {r: ctx.parents_of(r) for r in specifics}
        parent_kinds = {r: next((p for p in role_parents[r] if ctx.is_kind(p)), None)
                        for r in specifics}
        invalid_parent_roles = [r for r, parent in parent_kinds.items() if parent is None]
        if invalid_parent_roles:
            status = STATUS_INVALIDO
            for role in invalid_parent_roles:
                result.coercions.append(coerce(
                    "ODP_ROLEMIXIN_ROLE_SEM_KIND", ctx.line_of(role),
                    f"O role {role} não especializa diretamente um kind.",
                    f"Faça {role} especializar um kind distinto dos demais roles do roleMixin.",
                ))
        known_parents = [p for p in parent_kinds.values() if p is not None]
        if len(specifics) >= 2 and (len(known_parents) < 2 or len(known_parents) != len(set(known_parents))):
            status = STATUS_INVALIDO
            result.coercions.append(coerce(
                "ODP_ROLEMIXIN_KINDS_DISTINTOS", line,
                f"Os roles do roleMixin {name} não especializam kinds distintos.",
                "Associe cada role a um kind diferente.",
            ))

        if not matching and len(role_names) >= 2:
            result.coercions.append(coerce(
                "ODP_ROLEMIXIN_SEM_GENSET", line,
                f"O roleMixin {name} não possui genset que agrupe os roles candidatos.",
                f"Acrescente um genset com general {name} e specifics {', '.join(role_names)}.",
                fix={"op": "append", "text": (
                    f"disjoint complete genset {name}Roles {{\n"
                    f"    general {name}\n    specifics {', '.join(role_names)}\n}}"
                )},
            ))
        elif not matching:
            result.coercions.append(coerce(
                "ODP_ROLEMIXIN_SEM_ROLES", line,
                f"O roleMixin {name} ainda não tem pelo menos dois roles candidatos.",
                "Declare pelo menos dois roles que especializem kinds distintos e agrupe-os em um genset.",
            ))

        lines = [line] if line is not None else []
        lines.extend(ctx.line_of(r) for r in specifics)
        if genset and ctx.genset_line(genset) is not None:
            lines.append(ctx.genset_line(genset))
        return PatternMatch(
            "rolemixin", status, sorted({n for n in lines if n is not None}),
            {"general": name, "specifics": specifics,
             "genset": genset.get("name") if genset else None,
             "role_kinds": parent_kinds},
        )
