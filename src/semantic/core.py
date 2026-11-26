from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from parser.symbol_table import SymbolTable, build_symbol_table

STATUS_COMPLETO = "completo"        # estrutura completa e regras satisfeitas
STATUS_INCOMPLETO = "incompleto"    # falta uma parte (ex.: genset ausente)
STATUS_INVALIDO = "invalido"        # estrutura presente, mas viola uma regra



@dataclass
class PatternMatch:
    pattern: str
    status: str
    lines: list[int] = field(default_factory=list)
    participants: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "pattern": self.pattern,
            "status": self.status,
            "lines": list(self.lines),
            "participants": dict(self.participants),
        }


@dataclass
class Coercion:
    line: int | None
    code: str
    suggestion: str
    message: str = ""

    def to_dict(self) -> dict:
        return {
            "line": self.line,
            "code": self.code,
            "message": self.message,
            "suggestion": self.suggestion,
        }


@dataclass
class Inference:
    pattern: str
    confidence: float
    missing: list[str] = field(default_factory=list)
    lines: list[int] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "pattern": self.pattern,
            "confidence": self.confidence,
            "missing": list(self.missing),
            "lines": list(self.lines),
            "evidence": list(self.evidence),
        }


@dataclass
class Detection:
    patterns: list[PatternMatch] = field(default_factory=list)
    coercions: list[Coercion] = field(default_factory=list)
    inferences: list[Inference] = field(default_factory=list)


@dataclass
class SemanticResult:
    patterns: list[PatternMatch] = field(default_factory=list)
    coercions: list[Coercion] = field(default_factory=list)
    inferences: list[Inference] = field(default_factory=list)

    def extend(self, other: Detection | "SemanticResult") -> "SemanticResult":
        self.patterns.extend(getattr(other, "patterns", []))
        self.coercions.extend(getattr(other, "coercions", []))
        self.inferences.extend(getattr(other, "inferences", []))
        return self

    def sort(self) -> "SemanticResult":
        """Ordena por linha, mantendo a ordem dos detectores em empates."""
        self.patterns.sort(key=lambda p: p.lines[0] if p.lines else 0)
        self.coercions.sort(key=lambda c: c.line if c.line is not None else 0)
        self.inferences.sort(key=lambda i: i.pattern)
        return self

    def to_dict(self) -> dict:
        return {
            "patterns": [p.to_dict() for p in self.patterns],
            "coercions": [c.to_dict() for c in self.coercions],
            "inferences": [i.to_dict() for i in self.inferences],
        }


# ----------------------------------------------------------------------
# Contexto semântico
# ----------------------------------------------------------------------


class SemanticContext:
    def __init__(self, ontology: dict | None, symbols: Any = None):
        self.ontology = ontology or {}
        if isinstance(symbols, SymbolTable):
            self.symbols = symbols
        else:
            self.symbols = build_symbol_table(self.ontology or None)

        self.classes: list[dict] = list(self.ontology.get("classes") or [])
        self.relations: list[dict] = list(self.ontology.get("relations") or [])
        self.gensets: list[dict] = list(self.ontology.get("gensets") or [])

        self._class_by_name: dict[str, dict] = {}
        for decl in self.classes:
            name = decl.get("name")
            if name is not None:
                self._class_by_name.setdefault(name, decl)

        self._genset_by_name: dict[str, dict] = {}
        for decl in self.gensets:
            name = decl.get("name")
            if name is not None:
                self._genset_by_name.setdefault(name, decl)

    # -- classes -------------------------------------------------------

    def class_decl(self, name: str | None) -> dict | None:
        return self._class_by_name.get(name) if name is not None else None

    def is_class(self, name: str | None) -> bool:
        return self.class_decl(name) is not None

    def stereotype_of(self, name: str | None) -> str | None:
        decl = self.class_decl(name)
        return decl.get("stereotype") if decl else None

    def is_kind(self, name: str | None) -> bool:
        """``True`` se a classe foi declarada com estereótipo ``kind``.

        Subkind e Role exigem que a classe-mãe (e o ``general`` do genset)
        seja um kind, e não outro sortal (collective, quantity, relator...).
        """
        return self.stereotype_of(name) == "kind"

    def by_stereotype(self, *stereotypes: str) -> list[dict]:
        wanted = set(stereotypes)
        return [c for c in self.classes if c.get("stereotype") in wanted]

    def parents_of(self, name: str | None) -> list[str]:
        decl = self.class_decl(name)
        if not decl:
            return []
        parent = decl.get("parent")
        if parent is None:
            return []
        if isinstance(parent, str):
            return [parent]
        return list(parent)

    # -- tabela de símbolos -------------------------------------------

    def symbol_of(self, name: str | None):
        if name is None:
            return None
        found = self.symbols.global_scope.lookup_local(name)
        return found[0] if found else None

    def kind_of(self, name: str | None) -> str | None:
        symbol = self.symbol_of(name)
        return symbol.kind if symbol else None

    def line_of(self, name: str | None) -> int | None:
        symbol = self.symbol_of(name)
        if symbol is not None and symbol.line is not None:
            return symbol.line
        decl = self.class_decl(name)
        if decl is not None:
            return decl.get("line")
        genset = self._genset_by_name.get(name) if name is not None else None
        return genset.get("line") if genset else None

    def lines_for(self, *names: str | None) -> list[int]:
        lines = {self.line_of(name) for name in names if name is not None}
        return sorted(line for line in lines if line is not None)

    # -- gensets -------------------------------------------------------

    def genset_decl(self, name: str | None) -> dict | None:
        return self._genset_by_name.get(name) if name is not None else None

    @staticmethod
    def specifics(genset: dict) -> list[str]:
        return list(genset.get("specifics") or [])

    def gensets_with_general(self, name: str | None) -> list[dict]:
        return [g for g in self.gensets if g.get("general") == name]

    def gensets_covering(self, names, general: str | None = None) -> list[dict]:
        wanted = set(names)
        found = [g for g in self.gensets if wanted & set(self.specifics(g))]
        if general is not None:
            found = [g for g in found if g.get("general") == general]
        return found

    def genset_line(self, genset: dict) -> int | None:
        line = genset.get("line")
        return line if line is not None else self.line_of(genset.get("general"))

    def mediated_roles(self) -> set[str]:
        """Roles alvo de ``@mediation`` de um ``relator``.

        Considera as duas formas aceitas pelo parser:

        - mediação interna: ``relator R { @mediation ... Role }``;
        - mediação externa: ``@mediation relation R ... Role``.

        Esses roles participam do padrão **Relator**. O detector de Role usa
        esse conjunto para não duplicar o padrão, mas nunca descarta um role
        que também participe de um genset de Role válido.
        """
        roles: set[str] = set()
        relator_names = {
            decl.get("name")
            for decl in self.classes
            if decl.get("stereotype") == "relator"
        }

        for decl in self.classes:
            if decl.get("stereotype") != "relator":
                continue
            for member in decl.get("attributes") or []:
                if (member.get("kind") == "relation"
                        and member.get("stereotype") == "mediation"):
                    target = member.get("target")
                    if self.stereotype_of(target) == "role":
                        roles.add(target)

        for relation in self.relations:
            if (relation.get("stereotype") == "mediation"
                    and relation.get("source") in relator_names):
                target = relation.get("target")
                if self.stereotype_of(target) == "role":
                    roles.add(target)

        return roles

    @staticmethod
    def has_modifier(genset: dict, modifier: str) -> bool:
        modifiers = [str(m).lower() for m in (genset.get("modifiers") or [])]
        return modifier in modifiers

    def dominant_stereotype(self, genset: dict) -> str | None:
        
        specifics = self.specifics(genset)
        if not specifics:
            return None
        counts = Counter(self.stereotype_of(name) for name in specifics)
        best = max(counts.values())
        candidates = {st for st, count in counts.items() if count == best}
        first = self.stereotype_of(specifics[0])
        if first in candidates:
            return first
        ranked = sorted(st for st in candidates if st is not None)
        return ranked[0] if ranked else None

# ----------------------------------------------------------------------
# Ponto de entrada
# ----------------------------------------------------------------------


def analyze(ontology: dict | None, symbols: Any = None) -> SemanticResult:
    result = SemanticResult()
    if not ontology:
        return result

    import patterns  
    from semantic.registry import ordered

    ctx = SemanticContext(ontology, symbols)
    for detector in ordered():
        result.extend(detector.detect(ctx))
    from semantic.inference import infer
    result.inferences.extend(infer(ctx, result))
    return result.sort()


def analyze_text(source: str) -> SemanticResult:
    from parser.parser import parse

    ontology, _ = parse(source)
    return analyze(ontology)
