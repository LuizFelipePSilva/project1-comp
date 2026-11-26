"""Dedução heurística de padrões incompletos a partir das evidências semânticas."""
from __future__ import annotations

from semantic.core import Inference, STATUS_INCOMPLETO


_MISSING_BY_CODE = {
    "ODP_SUBKIND_DISJOINT": "modificador disjoint no genset",
    "ODP_PHASE_DISJOINT": "modificador disjoint no genset",
    "ODP_PHASE_SEM_GENSET": "genset disjoint para as phases",
    "ODP_PHASE_SEM_IRMA": "ao menos uma phase irmã que especialize o mesmo kind",
    "ODP_RELATOR_MEDIACOES": "ao menos duas mediações para roles distintos",
    "ODP_RELATOR_SEM_MATERIAL": "relação @material entre os roles mediados",
    "ODP_MODE_SEM_CHARACTERIZATION": "relação @characterization",
    "ODP_MODE_SEM_EXTERNALDEPENDENCE": "relação @externalDependence",
    "ODP_ROLEMIXIN_SEM_GENSET": "genset disjoint complete com general roleMixin",
    "ODP_ROLEMIXIN_SEM_ROLES": "ao menos dois roles que especializem kinds distintos",
    "ODP_ROLEMIXIN_QUANTIDADE": "ao menos dois roles distintos no genset",
}


def infer(ctx, result) -> list[Inference]:
    """Cria uma inferência por padrão incompleto, com confiança baseada em evidências.

    A confiança é uma heurística simples: 0.9 para padrão nomeado explicitamente
    na ontologia e 0.75 para agrupamentos inferidos sem genset.
    """
    by_pattern: dict[str, list] = {}
    for diagnostic in result.coercions:
        code = diagnostic.code
        for prefix, pattern in (
            ("ODP_SUBKIND_", "subkind"), ("ODP_ROLE_", "role"),
            ("ODP_PHASE_", "phase"), ("ODP_RELATOR_", "relator"),
            ("ODP_MODE_", "mode"), ("ODP_ROLEMIXIN_", "rolemixin"),
        ):
            if code.startswith(prefix):
                by_pattern.setdefault(pattern, []).append(diagnostic)
                break

    inferred = []
    for match in result.patterns:
        diagnostics = by_pattern.get(match.pattern, [])
        missing = list(dict.fromkeys(
            _MISSING_BY_CODE[d.code] for d in diagnostics if d.code in _MISSING_BY_CODE
        ))
        # Alguns padrões parciais também são estruturalmente inválidos (por
        # exemplo, Relator com uma mediação). Ainda assim cabe inferir o ODP
        # candidato quando o diagnóstico aponta componentes obrigatórios ausentes.
        if match.status != STATUS_INCOMPLETO and not missing:
            continue
        participants = match.participants
        if not missing:
            if match.pattern in {"subkind", "role", "phase"} and not participants.get("genset"):
                missing = ["genset que agrupe o general e os specifics"]
            elif match.pattern == "mode":
                missing = ["relações obrigatórias do padrão mode"]
            elif match.pattern == "rolemixin":
                missing = ["genset disjoint complete para o roleMixin"]
            else:
                missing = ["elementos obrigatórios do padrão"]
        evidence = [f"padrão {match.pattern} parcial detectado nas linhas {', '.join(map(str, match.lines)) or '?'}"]
        inferred.append(Inference(
            pattern=match.pattern,
            confidence=0.9 if participants.get("genset") else 0.75,
            missing=missing,
            lines=list(match.lines),
            evidence=evidence,
        ))
    return inferred
