from __future__ import annotations

from semantic.core import (
    STATUS_COMPLETO,
    STATUS_INCOMPLETO,
    STATUS_INVALIDO,
    Coercion,
    Detection,
    PatternMatch,
)
from semantic.registry import register

PATTERN = "role"
DISJOINT = "disjoint"
MIXIN_STEREOTYPES = {"roleMixin", "historicalRoleMixin", "mixin"}


@register(PATTERN)
class RoleDetector:

    pattern = PATTERN

    def detect(self, ctx) -> Detection:
        detection = Detection()
        roles = ctx.by_stereotype(PATTERN)
        if not roles:
            return detection

        excluded = self._mixin_members(ctx)
        roles = [decl for decl in roles if decl.get("name") not in excluded]
        if not roles:
            return detection

        self._validate_parents(ctx, detection, roles)

        handled: set[str] = set()
        for genset in ctx.gensets:
            if not ctx.specifics(genset):
                continue
            if ctx.stereotype_of(genset.get("general")) in MIXIN_STEREOTYPES:
                continue
            if ctx.dominant_stereotype(genset) != PATTERN:
                continue
            detection.patterns.append(self._check_genset(ctx, detection, genset))
            handled.update(ctx.specifics(genset))

        detection.patterns.extend(self._uncovered_patterns(ctx, roles, handled))
        return detection


    @staticmethod
    def _mixin_members(ctx) -> set[str]:
        members: set[str] = set()
        for genset in ctx.gensets:
            if ctx.stereotype_of(genset.get("general")) in MIXIN_STEREOTYPES:
                members.update(ctx.specifics(genset))
        return members

    def _validate_parents(self, ctx, detection: Detection, classes: list[dict]) -> None:
        for decl in classes:
            name = decl.get("name")
            line = decl.get("line") or ctx.line_of(name)
            parents = ctx.parents_of(name)

            if not parents:
                detection.coercions.append(Coercion(
                    line=line,
                    code="ODP_ROLE_SEM_PAI",
                    message=f"O role {name} não especializa nenhuma classe.",
                    suggestion=(
                        f"Declare o role como 'role {name} specializes <ClassName>'."
                    ),
                ))
                continue

            for parent in parents:
                if not ctx.is_class(parent):
                    detection.coercions.append(Coercion(
                        line=line,
                        code="ODP_ROLE_PAI_DESCONHECIDO",
                        message=(
                            f"O role {name} especializa {parent}, que não foi "
                            "declarado na ontologia."
                        ),
                        suggestion=(
                            f"Declare '{parent}' antes ou corrija o nome em "
                            f"'role {name} specializes {parent}'."
                        ),
                    ))

    def _check_genset(self, ctx, detection: Detection, genset: dict) -> PatternMatch:
        general = genset.get("general")
        specifics = ctx.specifics(genset)
        genset_name = genset.get("name") or "(sem nome)"
        line = ctx.genset_line(genset)
        status = STATUS_COMPLETO

        if not ctx.is_class(general):
            status = STATUS_INVALIDO
            detection.coercions.append(Coercion(
                line=line,
                code="ODP_ROLE_GENERAL_DESCONHECIDO",
                message=(
                    f"O genset {genset_name} usa '{general}' como general, mas "
                    "essa classe não foi declarada."
                ),
                suggestion=(
                    f"Declare '{general}' ou corrija o campo 'general' do genset "
                    f"{genset_name}."
                ),
            ))

        invalid_members = [
            name for name in specifics
            if ctx.stereotype_of(name) != PATTERN or general not in ctx.parents_of(name)
        ]
        if invalid_members:
            status = STATUS_INVALIDO
            detection.coercions.append(Coercion(
                line=line,
                code="ODP_ROLE_GENSET_MEMBRO",
                message=(
                    f"O genset {genset_name} lista em 'specifics' nomes que não "
                    f"são roles de {general}: {', '.join(invalid_members)}."
                ),
                suggestion=(
                    "Mantenha em 'specifics' apenas roles declarados com "
                    f"'role <Nome> specializes {general}'."
                ),
            ))

        if ctx.has_modifier(genset, DISJOINT):
            status = STATUS_INVALIDO
            detection.coercions.append(Coercion(
                line=line,
                code="ODP_ROLE_DISJOINT",
                message=(
                    f"O genset {genset_name} declara 'disjoint', mas essa "
                    "restrição não se aplica a roles."
                ),
                suggestion=(
                    f"Remova 'disjoint' do genset {genset_name}. Se os roles "
                    "puderem se sobrepor, use 'overlapping'."
                ),
            ))

        return PatternMatch(
            pattern=PATTERN,
            status=status,
            lines=ctx.lines_for(general, *specifics),
            participants={
                "general": general,
                "specifics": specifics,
                "genset": genset.get("name"),
            },
        )

    def _uncovered_patterns(self, ctx, classes: list[dict], handled: set[str]) -> list[PatternMatch]:
        pending = [decl for decl in classes if decl.get("name") not in handled]
        groups: dict[str | None, list[str]] = {}

        for decl in pending:
            name = decl.get("name")
            for parent in (ctx.parents_of(name) or [None]):
                groups.setdefault(parent, []).append(name)

        patterns = []
        for general, names in groups.items():
            specifics = list(dict.fromkeys(names))
            patterns.append(PatternMatch(
                pattern=PATTERN,
                status=STATUS_INCOMPLETO,
                lines=ctx.lines_for(general, *specifics),
                participants={
                    "general": general,
                    "specifics": specifics,
                    "genset": None,
                },
            ))
        return patterns
