import re
import ply.lex as lex

RESERVED = {
  'genset', 'disjoint', 'complete', 'general', 'specifics',
  'where', 'package', 'import', 'specializes',
  'type', 'datatype', 'enum', 'relation', 'powertype',
}

RELATION_STEREOTYPE = {
  'material', 'derivation', 'comparative', 'mediation',
  'characterization', 'externalDependence', 'componentOf', 'memberOf',
  'subCollectionOf', 'subQualityOf', 'instantiation', 'termination',
  'participational', 'participation', 'historicalDependence', 'creation',
  'manifestation', 'bringsAbout', 'triggers', 'composition', 'aggregation',
  'inherence', 'value', 'formal', 'constitution'
}

CLASS_STEREOTYPE = {
  'event', 'situation', 'process', 'category', 'mixin',
  'phaseMixin', 'roleMixin', 'historicalRoleMixin', 'kind', 'collective',
  'quantity', 'quality', 'mode', 'intrisicMode', 'extrinsicMode', 'subkind', 'phase',
  'role', 'historicalRole', 'relator'
}

NATIVE_TYPES = {
  'number', 'string', 'boolean', 'date', 'time', 'datetime'
}

META_ATTRIBUTES = {
  'ordered', 'const', 'derived', 'subsets', 'redefines'
}

tokens = (
    'RELATION_STEREOTYPE',
    'RESERVED',
    'CLASS_STEREOTYPE',
    'NATIVE_TYPE',
    'META_ATTRIBUTE',
    'CLASS_NAME',
    'RELATION_NAME',
    'INSTANCE_NAME',
    'DATATYPE_NAME',
    'PACKAGE_NAME',
    'DATETIME_LITERAL',
    'DATE_LITERAL',
    'TIME_LITERAL',
    'STRING',
    'NUMBER',
    'LBRACE', 'RBRACE',
    'LPAREN', 'RPAREN',
    'LBRACKET', 'RBRACKET',
    'RANGE',
    'COMPOSITION',
    'AGGREGATION',
    'STAR',
    'AT',
    'COLON',
    'ASSOCIATION'
)

# ---------- Classificação de identificador ----------

DATATYPE_RE = re.compile(r'^[A-Za-z]+DataType$')
INSTANCE_RE = re.compile(r'^[A-Za-z](?:_?[A-Za-z]+)*[0-9]+$')
CLASS_RE    = re.compile(r'^[A-Z][A-Za-z]*(?:_[A-Za-z]+)*$')
RELATION_RE = re.compile(r'^[a-z][A-Za-z]*(?:_[A-Za-z]+)*$')

def classify_id(value):
    if DATATYPE_RE.match(value):
        return 'DATATYPE_NAME'
    if INSTANCE_RE.match(value):
        return 'INSTANCE_NAME'
    if CLASS_RE.match(value):
        return 'CLASS_NAME'
    if RELATION_RE.match(value):
        return 'RELATION_NAME'
    return None

def suggest_fix(value):
    if re.search(r'[0-9]', value) and not INSTANCE_RE.match(value):
        return f"identificadores só aceitam dígito no final (ex: '{re.sub(r'[0-9]', '', value)}1')"
    if '_' in value and (value.startswith('_') or value.endswith('_') or '__' in value):
        return "sublinhado deve ser subcadeia própria (não pode iniciar, terminar, ou duplicar)"
    return ("verifique convenção de nomes (classe: MaiúsculaInicial; "
            "relação: minúsculaInicial; instância: termina em número; "
            "datatype: termina em 'DataType')")

def report_lex_error(t):
    line = t.lineno
    col = find_column(t, t.lexer)
    msg = f"Erro léxico na linha {line}, coluna {col}: identificador inválido '{t.value}'."
    msg += f" Sugestão: {suggest_fix(t.value)}"
    print(msg)

# ---------- Símbolos e literais ----------

def t_NUMBER(t):
    r'\d+'
    t.value = int(t.value)
    return t

t_LBRACE   = r'\{'
t_RBRACE   = r'\}'
t_LPAREN   = r'\('
t_RPAREN   = r'\)'
t_LBRACKET = r'\['
t_RBRACKET = r'\]'
t_COLON    = r':'
t_AT       = r'@'

def t_RANGE(t):
    r'\.\.'
    return t

def t_COMPOSITION(t):
    r'<>--'
    return t

def t_AGGREGATION(t):
    r'--<>'
    return t

def t_ASSOCIATION(t):
    r'--'
    return t

def t_STAR(t):
    r'\*'
    return t

def t_DATETIME_LITERAL(t):
    r"'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'"
    t.value = t.value[1:-1]
    return t

def t_DATE_LITERAL(t):
    r"'\d{4}-\d{2}-\d{2}'"
    t.value = t.value[1:-1]
    return t

def t_TIME_LITERAL(t):
    r"'\d{2}:\d{2}:\d{2}'"
    t.value = t.value[1:-1]
    return t

def t_STRING(t):
    r'("([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\')'
    t.value = t.value[1:-1]
    return t

def t_FUNCTIONAL_COMPLEXES(t):
    r'functional-complexes'
    t.type = 'RESERVED'
    return t

def t_PACKAGE(t):
    r'Package'
    return t

def t_ID(t):
    r'[a-zA-Z_][a-zA-Z_0-9]*'
    if t.value in CLASS_STEREOTYPE:
        t.type = 'CLASS_STEREOTYPE'
    elif t.value in RELATION_STEREOTYPE:
        t.type = 'RELATION_STEREOTYPE'
    elif t.value in RESERVED:
        t.type = 'RESERVED'
        if t.value == 'package':
            t.lexer.expect_package_name = True
        return t
    elif t.value in NATIVE_TYPES:
        t.type = 'NATIVE_TYPE'
    elif t.value in META_ATTRIBUTES:
        t.type = 'META_ATTRIBUTE'
    else:
        if getattr(t.lexer, 'expect_package_name', False):
            t.lexer.expect_package_name = False
            t.type = 'PACKAGE_NAME'
            return t
        kind = classify_id(t.value)
        if kind is None:
            report_lex_error(t)
            return None
        t.type = kind
    return t

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)
    t.lexer.line_start = t.lexpos + len(t.value)

def find_column(t, lexer):
    line_start = getattr(lexer, 'line_start', 0)
    return (t.lexpos - line_start) + 1

t_ignore = ' \t'

def t_COMMENT(t):
    r'//.*'
    pass

def t_COMMENT_BLOCK(t):
    r'/\*([^*]|\*+[^*/])*\*+/'
    t.lexer.lineno += t.value.count('\n')
    pass

def t_error(t):
    line = t.lineno
    col = find_column(t, t.lexer)
    print(f"Erro léxico na linha {line}, coluna {col}: caractere inválido '{t.value[0]}'")
    t.lexer.skip(1)

def build_lexer(**kwargs):
    lexer = lex.lex(**kwargs)
    lexer.line_start = 0
    lexer.expect_package_name = False
    return lexer