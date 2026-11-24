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

PATTERN = "subkind"

DISJOINT = "disjoint"
OVERLAPPING = "overlapping"
COMPLETE = "complete"
INCOMPLETE = "incomplete"


@register(PATTERN)
class SubkindDetector:
    pattern = PATTERN

    def detect(self, ctx) -> Detection:
        detection = Detection()
        subkinds = ctx.by_stereotype(PATTERN)
        if not subkinds:
            return detection

        self._validate_parents(ctx, detection, subkinds)

        handled: set[str] = set()
        for genset in ctx.gensets:
            if not ctx.specifics(genset):
                continue
            if ctx.dominant_stereotype(genset) != PATTERN:
                continue
            detection.patterns.append(self._check_genset(ctx, detection, genset))
            handled.update(ctx.specifics(genset))

        detection.patterns.extend(self._uncovered_patterns(ctx, subkinds, handled))
        return detection

    
    def _validate_parents(self, ctx, detection: Detection, classes: list[dict]) -> None:
        for decl in classes:
            name = decl.get("name")
            line = decl.get("line") or ctx.line_of(name)
            parents = ctx.parents_of(name)

            if not parents:
                detection.coercions.append(Coercion(
                    line=line,
                    code="ODP_SUBKIND_SEM_PAI",
                    message=f"O subkind {name} não especializa nenhuma classe.",
                    suggestion=(
                        f"Declare o subkind como 'subkind {name} specializes "
                        "<ClassName>'."
                    ),
                ))
                continue

            for parent in parents:
                if not ctx.is_class(parent):
                    detection.coercions.append(Coercion(
                        line=line,
                        code="ODP_SUBKIND_PAI_DESCONHECIDO",
                        message=(
                            f"O subkind {name} especializa {parent}, que não foi "
                            "declarado na ontologia."
                        ),
                        suggestion=(
                            f"Declare '{parent}' antes ou corrija o nome em "
                            f"'subkind {name} specializes {parent}'."
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
                code="ODP_SUBKIND_GENERAL_DESCONHECIDO",
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
                code="ODP_SUBKIND_GENSET_MEMBRO",
                message=(
                    f"O genset {genset_name} lista em 'specifics' nomes que não "
                    f"são subkinds de {general}: {', '.join(invalid_members)}."
                ),
                suggestion=(
                    "Mantenha em 'specifics' apenas subkinds declarados com "
                    f"'subkind <Nome> specializes {general}'."
                ),
            ))

        if not ctx.has_modifier(genset, DISJOINT):
            status = STATUS_INVALIDO
            detection.coercions.append(Coercion(
                line=line,
                code="ODP_SUBKIND_DISJOINT",
                message=(
                    f"O genset {genset_name} agrupa subkinds mas não declara "
                    "'disjoint'."
                ),
                suggestion=(
                    f"Acrescente 'disjoint' antes de 'genset {genset_name}' "
                    f"(ex.: 'disjoint complete genset {genset_name} ...')."
                ),
            ))

        if ctx.has_modifier(genset, OVERLAPPING):
            status = STATUS_INVALIDO
            detection.coercions.append(Coercion(
                line=line,
                code="ODP_SUBKIND_OVERLAPPING",
                message=(
                    f"O genset {genset_name} declara 'overlapping', mas subkinds "
                    "devem ser disjuntos."
                ),
                suggestion=(
                    f"Troque 'overlapping' por 'disjoint' no genset {genset_name}."
                ),
            ))

        if ctx.has_modifier(genset, COMPLETE) and ctx.has_modifier(genset, INCOMPLETE):
            status = STATUS_INVALIDO
            detection.coercions.append(Coercion(
                line=line,
                code="ODP_SUBKIND_COMPLETUDE_CONFLITANTE",
                message=(
                    f"O genset {genset_name} declara 'complete' e 'incomplete' ao "
                    "mesmo tempo."
                ),
                suggestion=(
                    "Escolha apenas uma das opções: 'complete' ou 'incomplete'."
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
