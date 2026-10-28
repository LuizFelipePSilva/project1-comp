"""
Relações e generalizações (genset).

O arquivo será importado em
parser.py, 

Regras de outras pessoas que são reutilizadas aqui (definidas em parser.py):
    cardinality, name_list, class_identifier, identifier

    relation: relação interna (dentro de classe) ou externa
    genset:   conjunto de generalização (forma curta ou longa)
"""

def p_link_simple(p):
    """link : ASSOCIATION
            | COMPOSITION
            | AGGREGATION"""
    p[0] = {"operator": p[1], "name": None}
    p.set_lineno(0, p.lineno(1))


def p_link_named(p):
    """link : ASSOCIATION RELATION_NAME ASSOCIATION
            | COMPOSITION RELATION_NAME ASSOCIATION
            | AGGREGATION RELATION_NAME ASSOCIATION"""
    p[0] = {"operator": p[1], "name": p[2]}
    p.set_lineno(0, p.lineno(1))


def p_relation_ends(p):
    """relation_ends : cardinality link cardinality class_identifier"""
    p[0] = {
        "source_cardinality": p[1],
        "operator": p[2]["operator"],
        "name": p[2]["name"],
        "target_cardinality": p[3],
        "target": p[4],
    }


# Relação interna: aparece dentro do corpo de uma classe.
# Exige o '@estereótipo' para não conflitar com a cardinalidade de atributos.
def p_member_relation(p):
    """member : AT RELATION_STEREOTYPE relation_ends"""
    p[0] = {
        "kind": "relation",
        "internal": True,
        "stereotype": p[2],
        "source": None,  # a classe dona é a que contém este membro
        "line": p.lineno(1),
        **p[3],
    }


# Relação interna sem '@estereótipo' (ex.: a 2ª relação do CarRental em
# carRental.tonto). Só é aceita quando começa direto pela seta; começando por
# '[', ficaria ambígua com a cardinalidade de um atributo anterior.
def p_member_relation_no_stereotype(p):
    """member : link cardinality class_identifier"""
    p[0] = {
        "kind": "relation",
        "internal": True,
        "stereotype": None,
        "source": None,
        "source_cardinality": None,
        "operator": p[1]["operator"],
        "name": p[1]["name"],
        "target_cardinality": p[2],
        "target": p[3],
        "line": p.lineno(1),
    }


# Relação externa: declaração de topo, com a palavra 'relation'.
def p_declaration_relation_stereotyped(p):
    """declaration : AT RELATION_STEREOTYPE RELATION class_identifier relation_ends"""
    p[0] = {
        "kind": "relation",
        "internal": False,
        "stereotype": p[2],
        "source": p[4],
        "line": p.lineno(1),
        **p[5],
    }


def p_declaration_relation_plain(p):
    """declaration : RELATION class_identifier relation_ends"""
    p[0] = {
        "kind": "relation",
        "internal": False,
        "stereotype": None,
        "source": p[2],
        "line": p.lineno(1),
        **p[3],
    }


# ----------------------------------------------------------------------
# Generalizações (genset)
# ----------------------------------------------------------------------

def p_genset_modifier(p):
    """genset_modifier : DISJOINT
                       | OVERLAPPING
                       | COMPLETE
                       | INCOMPLETE"""
    p[0] = p[1]


def p_genset_modifiers_single(p):
    """genset_modifiers : genset_modifier"""
    p[0] = [p[1]]


def p_genset_modifiers_multiple(p):
    """genset_modifiers : genset_modifiers genset_modifier"""
    p[0] = p[1] + [p[2]]


def p_categorizer_opt(p):
    """categorizer_opt : CATEGORIZER class_identifier"""
    p[0] = p[2]


def p_categorizer_opt_empty(p):
    """categorizer_opt : empty"""
    p[0] = None


# Forma longa:  [modificadores] genset Nome { general X [categorizer C] specifics A, B }
def p_genset_long(p):
    """genset_body : LBRACE GENERAL class_identifier categorizer_opt SPECIFICS name_list RBRACE"""
    p[0] = {
        "form": "long",
        "general": p[3],
        "categorizer": p[4],
        "specifics": p[6],
    }


# Forma curta:  [modificadores] genset Nome where A, B specializes P
def p_genset_short(p):
    """genset_body : WHERE name_list SPECIALIZES class_identifier"""
    p[0] = {
        "form": "short",
        "general": p[4],
        "categorizer": None,
        "specifics": p[2],
    }


def p_declaration_genset(p):
    """declaration : GENSET identifier genset_body"""
    p[0] = {
        "kind": "genset",
        "name": p[2],
        "modifiers": [],
        "line": p.lineno(1),
        **p[3],
    }


def p_declaration_genset_modifiers(p):
    """declaration : genset_modifiers GENSET identifier genset_body"""
    p[0] = {
        "kind": "genset",
        "name": p[3],
        "modifiers": p[1],
        "line": p.lineno(2),
        **p[4],
    }