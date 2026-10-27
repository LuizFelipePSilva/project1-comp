
import ply.yacc as yacc
import os
import sys

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

from lexer.lexer import tokens, build_lexer


# Resultado e erros da análise
syntax_errors = []

def p_ontology(p):
    """ontology : package_decl declaration_list"""
    
    declarations = p[2]

    imports = [
        declaration
        for declaration in declarations
        if declaration.get("kind") == "import"
    ]

    classes = [
        declaration
        for declaration in declarations
        if declaration.get("kind") == "class"
    ]

    p[0] = {
       "package": p[1],
       "imports": imports,
       "classes": classes,
       "declarations": declarations,
   }

def p_package_decl(p):
       """package_decl : PACKAGE PACKAGE_NAME SEMICOLON
                       | PACKAGE PACKAGE_NAME"""
       p[0] = {"kind": "package", "name": p[2], "line": p.lineno(1)}

def p_import_decl(p):
    """import_decl : IMPORT RELATION_NAME"""
    p[0] = {"kind": "import", "name": p[2], "line": p.lineno(1)}


def p_declaration_list_multiple(p):
    """declaration_list : declaration_list declaration"""
    p[0] = p[1] + [p[2]]

def p_declaration_list_empty(p):
    """declaration_list : empty"""
    p[0] = []

def p_declaration_import(p):
    """declaration : import_decl"""
    p[0] = p[1]

def p_declaration_class(p):
    """declaration : class_decl"""
    p[0] = p[1]

def p_identifier(p):
    """identifier : CLASS_NAME
                  | RELATION_NAME
                  | INSTANCE_NAME
                  | DATATYPE_NAME
                  | PACKAGE_NAME"""
    p[0] = p[1]


def p_class_identifier(p):
    """class_identifier : CLASS_NAME"""
    p[0] = p[1]

def p_class_decl(p):
    """class_decl : CLASS_STEREOTYPE CLASS_NAME inheritance attributes"""
    p[0] = {
        "kind": "class",
        "stereotype": p[1],
        "name": p[2],
        "parent": p[3],
        "attributes": p[4],
        "line": p.lineno(1),
    }

def p_inheritance(p):
    """inheritance : SPECIALIZES name_list"""
    p[0] = p[2]

def p_name_list_single(p):
    """name_list : class_identifier"""
    p[0] = [p[1]]


def p_name_list_multiple(p):
    """name_list : name_list COMMA class_identifier"""
    p[0] = p[1] + [p[3]]
    
def p_inheritance_empty(p):
    """inheritance : empty"""
    p[0] = None


def p_attributes_block(p):
    """attributes : LBRACE member_list RBRACE"""
    p[0] = p[2]

def p_member_list_multiple(p):
    """member_list : member_list member"""
    p[0] = p[1] + [p[2]]

def p_member_list_empty(p):
    """member_list : empty"""
    p[0] = []

def p_member_attribute(p):
    """member : attribute"""
    p[0] = p[1]

def p_attributes_empty(p):
    """attributes : empty"""
    p[0] = []

def p_attribute(p):
       """attribute : attribute_name COLON attribute_type cardinality meta_attribute"""
       p[0] = {
           "kind": "attribute",
           "name": p[1],
           "type": p[3],
           "cardinality": p[4],
           "meta_attribute": p[5],
           "line": p.lineno(1),
       }

def p_attribute_name(p):
       """attribute_name : RELATION_NAME
                         | NATIVE_TYPE"""
       p[0] = p[1]
       p.set_lineno(0, p.lineno(1))

def p_attribute_type(p):
       """attribute_type : NATIVE_TYPE
                         | DATATYPE_NAME
                         | CLASS_NAME
                         | RELATION_NAME"""
       p[0] = p[1]
       
def p_cardinality(p):
    """cardinality : LBRACKET NUMBER RBRACKET
                   | LBRACKET STAR RBRACKET
                   | LBRACKET NUMBER RANGE NUMBER RBRACKET
                   | LBRACKET NUMBER RANGE STAR RBRACKET
                   | LBRACKET NUMBER RANGE RBRACKET
                   | LBRACKET RBRACKET
                   | empty"""
    n = len(p)

    if n == 4:  # [N] ou [*]
        if p.slice[2].type == "NUMBER":
            p[0] = {"min": int(p[2]), "max": int(p[2])}
        else:
            p[0] = {"min": 0, "max": None}

    elif n == 5:  # [N..]
        p[0] = {"min": int(p[2]), "max": None}

    elif n == 6:  # [N..N] ou [N..*]
        upper = None if p.slice[4].type == "STAR" else int(p[4])
        p[0] = {"min": int(p[2]), "max": upper}

    elif n == 3:  # []
        p[0] = None  # ajuste aqui se decidir outro valor para []

    else:  # empty
        p[0] = None

# TODO PARTICIO VER SE É PARA SER {CONST} OU CONST e antes ou depois de cardinalidade
def p_meta_attribute(p):
    """meta_attribute : LBRACE META_ATTRIBUTE RBRACE
                      | LBRACE RBRACE
                      | empty"""
    if len(p) == 4:
        p[0] = p[2]
    # { }
    elif len(p) == 3:
        p[0] = None
    else:
        p[0] = None

def p_empty(p):
    """empty :"""
    p[0] = None

def report_syntax_error(line, msg, suggestion):
    syntax_errors.append({
        "line": line,
        "message": msg,
        "suggestion": suggestion,
    })

_lexer = None
def p_error(token):
    if token is None:
        report_syntax_error(
            line=_lexer.lineno if _lexer else 0,
            msg="Fim inesperado do arquivo.",
            suggestion="Verifique se todas as declarações foram finalizadas.",
        )
        return

    report_syntax_error(
        line=token.lineno,
        msg=f"Token inesperado '{token.value}' ({token.type}).",
        suggestion="Verifique a estrutura da declaração.",
    )


parser = yacc.yacc(start="ontology")



def parse(source):
    global _lexer
    syntax_errors.clear()
    _lexer = build_lexer()
    result = parser.parse(source, lexer=_lexer)
    return result, syntax_errors.copy()


if __name__ == "__main__":
    example = """
    package myPackage
    import bar
    subkind X specializes A, B
    """

    result, errors = parse(example)

    if errors:
        for error in errors:
            print(error)
    else:
        print("Análise sintática concluída.")
        print(result)
