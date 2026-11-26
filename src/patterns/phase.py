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

PATTERN = "phase"


@register(PATTERN)
class PhaseDetector:
    pattern = PATTERN

    @guarded
    def detect(self, ctx) -> Detection:
        detection = Detection()
        phases = ctx.by_stereotype(PATTERN)
        if not phases:
            return detection

        self._validate_parents(ctx, detection, phases)

        handled: set[str] = set()
        for genset in ctx.gensets:
            if not ctx.specifics(genset):
                continue
            if ctx.dominant_stereotype(genset) != PATTERN:
                continue
            detection.patterns.append(self._check_genset(ctx, detection, genset))
            handled.update(ctx.specifics(genset))

        self._uncovered(ctx, detection, phases, handled)
        return detection

    def _validate_parents(self, ctx, detection, phases) -> None:
        for decl in phases:
            name = decl.get("name")
            line = decl.get("line") or ctx.line_of(name)
            parents = ctx.parents_of(name)

            if not parents:
                detection.coercions.append(coerce(
                    "ODP_PHASE_SEM_PAI", line,
                    f"A phase {name} não especializa nenhuma classe.",
                    f"Declare como 'phase {name} specializes <Kind>'.",
                ))
                continue

            declared_parents = [parent for parent in parents if ctx.is_class(parent)]
            for parent in parents:
                if not ctx.is_class(parent):
                    detection.coercions.append(coerce(
                        "ODP_PHASE_PAI_DESCONHECIDO", line,
                        f"A phase {name} especializa {parent}, que não foi declarado.",
                        f"Declare 'kind {parent}' ou corrija o nome em "
                        f"'phase {name} specializes {parent}'.",
                    ))

            if declared_parents and not any(
                ctx.stereotype_of(parent) == "kind" for parent in declared_parents
            ):
                detection.coercions.append(coerce(
                    "ODP_PHASE_PAI_NAO_KIND", line,
                    f"A phase {name} precisa especializar diretamente um kind.",
                    f"Declare a phase com 'specializes <Kind>' usando um kind "
                    "como classe-mãe direta.",
                ))

    def _check_genset(self, ctx, detection, genset) -> PatternMatch:
        general = genset.get("general")
        specifics = list(dict.fromkeys(ctx.specifics(genset)))
        gname = genset.get("name") or "(sem nome)"
        line = ctx.genset_line(genset)
        status = STATUS_COMPLETO

        if not ctx.is_class(general):
            status = STATUS_INVALIDO
            detection.coercions.append(coerce(
                "ODP_PHASE_GENERAL_DESCONHECIDO", line,
                f"O genset {gname} usa '{general}' como general, mas ele não foi declarado.",
                f"Declare '{general}' ou corrija o campo 'general' do genset {gname}.",
            ))
        elif ctx.stereotype_of(general) != "kind":
            status = STATUS_INVALIDO
            detection.coercions.append(coerce(
                "ODP_PHASE_GENERAL_NAO_KIND", line,
                f"O general {general} do genset {gname} não é um kind.",
                f"Use um kind como general do genset {gname}.",
            ))

        valid_specifics = [
            name for name in specifics
            if ctx.stereotype_of(name) == PATTERN and general in ctx.parents_of(name)
        ]
        bad = [name for name in specifics if name not in valid_specifics]
        if bad:
            status = STATUS_INVALIDO
            detection.coercions.append(coerce(
                "ODP_PHASE_GENSET_MEMBRO", line,
                f"O genset {gname} lista em 'specifics' nomes que não são phases "
                f"de {general}: {', '.join(bad)}.",
                f"Mantenha só phases declaradas com 'phase <Nome> specializes {general}'.",
            ))

        if len(valid_specifics) < 2:
            status = STATUS_INVALIDO
            detection.coercions.append(coerce(
                "ODP_PHASE_SEM_IRMA", line,
                f"O genset {gname} precisa conter ao menos duas phases irmãs.",
                f"Acrescente outra phase que especialize {general} e liste-a em 'specifics'.",
            ))

        has_disjoint = ctx.has_modifier(genset, "disjoint")
        has_overlapping = ctx.has_modifier(genset, "overlapping")
        if has_overlapping:
            status = STATUS_INVALIDO
            detection.coercions.append(coerce(
                "ODP_PHASE_OVERLAPPING", line,
                f"O genset {gname} declara 'overlapping', mas phases são disjuntas.",
                f"Troque 'overlapping' por 'disjoint' no genset {gname}.",
            ))
        elif not has_disjoint:
            status = STATUS_INVALIDO
            detection.coercions.append(coerce(
                "ODP_PHASE_DISJOINT", line,
                f"O genset {gname} agrupa phases mas não declara 'disjoint'.",
                f"Acrescente 'disjoint' antes de 'genset {gname}'.",
            ))

        if ctx.has_modifier(genset, "complete") and ctx.has_modifier(genset, "incomplete"):
            status = STATUS_INVALIDO
            detection.coercions.append(coerce(
                "ODP_PHASE_COMPLETUDE_CONFLITANTE", line,
                f"O genset {gname} declara 'complete' e 'incomplete' ao mesmo tempo.",
                "Escolha apenas 'complete' ou 'incomplete'.",
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

    def _uncovered(self, ctx, detection, phases, handled) -> None:
        groups: dict[str, list[str]] = {}
        for decl in phases:
            name = decl.get("name")
            if name in handled:
                continue

            direct_kind_parents = [
                parent for parent in ctx.parents_of(name)
                if ctx.is_class(parent) and ctx.stereotype_of(parent) == "kind"
            ]
            for parent in direct_kind_parents:
                groups.setdefault(parent, []).append(name)

        for general, names in groups.items():
            specifics = list(dict.fromkeys(names))
            lines = ctx.lines_for(general, *specifics)
            line = lines[0] if lines else None

            if len(specifics) < 2:
                status = STATUS_INVALIDO
                detection.coercions.append(coerce(
                    "ODP_PHASE_SEM_IRMA", ctx.line_of(specifics[0]),
                    f"A phase {specifics[0]} não tem nenhuma phase irmã.",
                    f"Acrescente outra phase que especialize {general} e agrupe-as "
                    "em um 'disjoint genset'.",
                ))
            else:
                status = STATUS_INCOMPLETO
                gname = f"{general}_Phases"
                text = (
                    f"disjoint complete genset {gname} {{\n"
                    f"    general {general}\n"
                    f"    specifics {', '.join(specifics)}\n}}"
                )
                detection.coercions.append(coerce(
                    "ODP_PHASE_SEM_GENSET", line,
                    f"As phases {', '.join(specifics)} de {general} não têm genset.",
                    f"Acrescente:\n{text}",
                    fix={"op": "append", "text": text},
                ))

            detection.patterns.append(PatternMatch(
                pattern=PATTERN,
                status=status,
                lines=lines,
                participants={"general": general, "specifics": specifics, "genset": None},
            ))
