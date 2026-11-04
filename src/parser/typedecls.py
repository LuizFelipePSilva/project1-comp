"""
Declarações de tipos de dados (datatype) e classes enumeradas (enum).

Importado em parser.py (como relations.py). Reutiliza de parser.py:
    attribute, cardinality, meta_attribute, class_identifier

    datatype Nome { atributos }
    enum Nome { Ind1, Ind2, ... }
"""


# ----------------------------------------------------------------------
# datatype
# ----------------------------------------------------------------------

def p_datatype_name(p):
    """datatype_name : CLASS_NAME
                     | DATATYPE_NAME"""
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_datatype_attribute_list_multiple(p):
    """datatype_attribute_list : datatype_attribute_list attribute"""
    p[0] = p[1] + [p[2]]


def p_datatype_attribute_list_empty(p):
    """datatype_attribute_list : empty"""
    p[0] = []


def p_declaration_datatype(p):
    """declaration : DATATYPE datatype_name LBRACE datatype_attribute_list RBRACE"""
    p[0] = {
        "kind": "datatype",
        "name": p[2],
        "attributes": p[4],
        "line": p.lineno(1),
    }


# ----------------------------------------------------------------------
# enum
# ----------------------------------------------------------------------

def p_enum_item(p):
    """enum_item : INSTANCE_NAME
                 | CLASS_NAME"""
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_enum_items_single(p):
    """enum_items : enum_item"""
    p[0] = [p[1]]


def p_enum_items_multiple(p):
    """enum_items : enum_items COMMA enum_item"""
    p[0] = p[1] + [p[3]]


def p_enum_items_trailing_comma(p):
    """enum_items : enum_items COMMA"""
    p[0] = p[1]


def p_enum_body_empty(p):
    """enum_body : empty"""
    p[0] = []


def p_enum_body_items(p):
    """enum_body : enum_items"""
    p[0] = p[1]


def p_declaration_enum(p):
    """declaration : ENUM class_identifier LBRACE enum_body RBRACE"""
    p[0] = {
        "kind": "enum",
        "name": p[2],
        "individuals": p[4],
        "line": p.lineno(1),
    }