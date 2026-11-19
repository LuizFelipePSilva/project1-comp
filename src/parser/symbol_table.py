class Symbol:
    """Uma declaração individual registrada em um escopo."""

    def __init__(self, name, kind, line=None, declaration=None,
                 internal_id=None, references=None):
        self.name = name
        self.kind = kind
        self.line = line
        self.declaration = declaration
        # Identificador técnico para membros anônimos (ex.: relações sem nome).
        # Não é um identificador declarado pelo usuário.
        self.internal_id = internal_id
        self.references = references or {}

    @property
    def key(self):
        """Chave usada para armazenar o símbolo no escopo."""
        return self.name if self.name is not None else self.internal_id

    @property
    def anonymous(self):
        return self.name is None

    def to_dict(self):
        data = {
            "name": self.name,
            "kind": self.kind,
            "line": self.line,
        }
        if self.anonymous:
            data["anonymous"] = True
            data["internal_id"] = self.internal_id
        if self.references:
            data["references"] = dict(self.references)
        return data

    def __repr__(self):
        label = self.name if self.name is not None else self.internal_id
        return f"Symbol({label!r}, {self.kind!r}, line={self.line!r})"


class Scope:
    """Ambiente de declarações (global, classe, datatype ou enum)."""

    def __init__(self, name, kind, parent=None, line=None):
        self.name = name
        self.kind = kind
        self.parent = parent
        self.line = line
        # name -> lista de Symbol (lista preserva declarações repetidas).
        self.symbols = {}
        self.children = []

        if parent is not None:
            parent.children.append(self)

    def declare(self, symbol):
        self.symbols.setdefault(symbol.key, []).append(symbol)
        return symbol

    def lookup_local(self, name):
        """Retorna todos os símbolos com esse nome neste escopo."""
        return list(self.symbols.get(name, []))

    def has(self, name):
        return name in self.symbols

    def to_dict(self, include_children=False):
        data = {
            "name": self.name,
            "kind": self.kind,
            "parent": self.parent.name if self.parent is not None else None,
            "line": self.line,
            "symbols": [s.to_dict() for group in self.symbols.values() for s in group],
        }
        if include_children:
            data["children"] = [c.to_dict(include_children=True) for c in self.children]
        return data

    def __repr__(self):
        return f"Scope({self.name!r}, {self.kind!r}, symbols={len(self.symbols)})"


# ----------------------------------------------------------------------
# Tabela de símbolos
# ----------------------------------------------------------------------


GLOBAL_SCOPE_NAME = "<global>"


class SymbolTable:
    """Conjunto de escopos do modelo, com o escopo global como raiz."""

    def __init__(self):
        self.global_scope = Scope(GLOBAL_SCOPE_NAME, "global")
        self.current_scope = self.global_scope
        self._stack = [self.global_scope]
        self.scopes = []

    def enter_scope(self, name, kind, line=None):
        scope = Scope(name, kind, parent=self.current_scope, line=line)
        self._stack.append(scope)
        self.current_scope = scope
        self.scopes.append(scope)
        return scope

    def leave_scope(self):
        if len(self._stack) <= 1:
            return self.current_scope
        self._stack.pop()
        self.current_scope = self._stack[-1]
        return self.current_scope

    def declare(self, symbol, scope=None):
        return (scope or self.current_scope).declare(symbol)

    def get_scope(self, name):
        for scope in self.scopes:
            if scope.name == name:
                return scope
        return None

    def to_dict(self):
        return {
            "global": self.global_scope.to_dict(include_children=False),
            "scopes": [scope.to_dict(include_children=False) for scope in self.scopes],
        }

    def __repr__(self):
        return f"SymbolTable(global={len(self.global_scope.symbols)}, scopes={len(self.scopes)})"


# ----------------------------------------------------------------------
# Construção da tabela a partir da estrutura do parser
# ----------------------------------------------------------------------


class SymbolTableBuilder:
    """Constrói a tabela de símbolos em uma única travessia organizada.

    Ordem:
        1. escopo global (pacote, imports, classes, datatypes, enums,
           gensets e relações externas);
        2. escopo de cada classe (atributos e relações internas);
        3. escopo de cada datatype (atributos);
        4. escopo de cada enum (itens).
    """

    def __init__(self):
        self.table = SymbolTable()
        self._anonymous_counter = 0

    def build(self, ontology):
        self.table = SymbolTable()
        if not ontology:
            return self.table

        self.visit_package(ontology.get("package"))
        self.visit_imports(ontology.get("imports", []))
        self.visit_declarations(ontology.get("declarations", []))
        self.visit_class_members(ontology.get("classes", []))
        self.visit_datatype_members(ontology.get("datatypes", []))
        self.visit_enum_members(ontology.get("enums", []))
        return self.table

    # -- declarações globais -------------------------------------------

    def visit_package(self, package):
        if not package:
            return
        self.table.declare(Symbol(
            name=package.get("name"),
            kind="package",
            line=package.get("line"),
            declaration=package,
        ))

    def visit_imports(self, imports):
        for imp in imports:
            self.table.declare(Symbol(
                name=imp.get("name"),
                kind="import",
                line=imp.get("line"),
                declaration=imp,
            ))

    def visit_declarations(self, declarations):
        for decl in declarations:
            kind = decl.get("kind")
            if kind == "class":
                self.visit_class(decl)
            elif kind == "datatype":
                self.visit_datatype(decl)
            elif kind == "enum":
                self.visit_enum(decl)
            elif kind == "genset":
                self.visit_genset(decl)
            elif kind == "relation":
                self.visit_external_relation(decl)
            # "error" e "import" (já tratado) são ignorados aqui.

    def visit_class(self, decl):
        self.table.declare(Symbol(
            name=decl.get("name"),
            kind="class",
            line=decl.get("line"),
            declaration=decl,
            references={"parent": decl.get("parent")},
        ))

    def visit_datatype(self, decl):
        self.table.declare(Symbol(
            name=decl.get("name"),
            kind="datatype",
            line=decl.get("line"),
            declaration=decl,
        ))

    def visit_enum(self, decl):
        self.table.declare(Symbol(
            name=decl.get("name"),
            kind="enum",
            line=decl.get("line"),
            declaration=decl,
        ))

    def visit_genset(self, decl):
        self.table.declare(Symbol(
            name=decl.get("name"),
            kind="genset",
            line=decl.get("line"),
            declaration=decl,
            references={
                "general": decl.get("general"),
                "categorizer": decl.get("categorizer"),
                "specifics": list(decl.get("specifics") or []),
            },
        ))

    def visit_external_relation(self, decl):
        self.table.declare(Symbol(
            name=decl.get("name"),
            kind="relation",
            line=decl.get("line"),
            declaration=decl,
            internal_id=self._anonymous_id(decl) if decl.get("name") is None else None,
            references={
                "source": decl.get("source"),
                "target": decl.get("target"),
            },
        ))

    # -- escopos de classe ---------------------------------------------

    def visit_class_members(self, classes):
        for decl in classes:
            name = decl.get("name")
            if name is None:
                continue
            scope = self.table.enter_scope(name, "class", line=decl.get("line"))
            for member in decl.get("attributes", []):
                if member.get("kind") == "attribute":
                    self.visit_attribute(scope, member, owner=name)
                elif member.get("kind") == "relation":
                    self.visit_internal_relation(scope, member, owner=name)
            self.table.leave_scope()

    def visit_attribute(self, scope, member, owner):
        scope.declare(Symbol(
            name=member.get("name"),
            kind="attribute",
            line=member.get("line"),
            declaration=member,
            references={"type": member.get("type"), "owner": owner},
        ))

    def visit_internal_relation(self, scope, member, owner):
        name = member.get("name")
        scope.declare(Symbol(
            name=name,
            kind="relation",
            line=member.get("line"),
            declaration=member,
            internal_id=None if name is not None else self._anonymous_id(member),
            references={
                "source": owner,
                "target": member.get("target"),
            },
        ))

    # -- escopos de datatype e enum ------------------------------------

    def visit_datatype_members(self, datatypes):
        for decl in datatypes:
            name = decl.get("name")
            if name is None:
                continue
            scope = self.table.enter_scope(name, "datatype", line=decl.get("line"))
            for member in decl.get("attributes", []):
                if member.get("kind") == "attribute":
                    self.visit_attribute(scope, member, owner=name)
            self.table.leave_scope()

    def visit_enum_members(self, enums):
        for decl in enums:
            name = decl.get("name")
            if name is None:
                continue
            scope = self.table.enter_scope(name, "enum", line=decl.get("line"))
            for item in decl.get("individuals", []):
                scope.declare(Symbol(
                    name=item,
                    kind="enum_item",
                    line=decl.get("line"),
                    references={"owner": name},
                ))
            self.table.leave_scope()

    # -- auxiliares ----------------------------------------------------

    def _anonymous_id(self, decl):
        self._anonymous_counter += 1
        line = decl.get("line")
        return f"<relation@{line}:{self._anonymous_counter}>"


def build_symbol_table(ontology):
    """Atalho: constrói e retorna a tabela de símbolos de uma ontologia."""
    return SymbolTableBuilder().build(ontology)
