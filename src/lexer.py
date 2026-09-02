import ply.lex as lex

RESERVED = {
  'genset', 
  'disjoint', 
  'complete', 
  'general', 
  'specifics',
  'where', 
  'package', 
  'import', 
  'specializes',
  'type',
  'datatype',
  'enum',
  'relation',
  'powertype',
  #'functional-complexes' tem que tratar isso depois, pois tem hiffen
}

RELATION_STEREOTYPE = {
  'material',
   'derivation', 'comparative', 'mediation',
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
    'ID', # ISSO AQUI É TU GABRIEL QUE VAI FAZER, A PARTE DE CLASSIFICAR CLASSES RELATION, INSTACE E DATATYPE

  'NUMBER',
  'LBRACE', 'RBRACE',
  'LPAREN', 'RPAREN',
  'LBRACKET', 'RBRACKET',
  'RANGE', # ..
  'COMPOSITION', # <>--
  'AGGREGATION', # --<>
  'ASS'
  'STAR',# *
  'AT', # @
  'COLON', # :
  'ASSOCIATION' # --
)

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


# Caso tratado do 'functional-complexes'
def t_FUNCTIONAL_COMPLEXES(t):
    r'functional-complexes'
    t.type = 'RESERVED'
    return t

# Gabriel tu faz o ID aqui, então basicamente eu só fiz o genérico tu refina
# Aqui tu vai fazer para diferenciar CLASS_NAME,INSTANCE_NAME, RELATION_NAME, DATATYPE_NAME 

def t_ID(t):
    r'[a-zA-Z_][a-zA-Z_0-9]*'
    if t.value in CLASS_STEREOTYPE:
        t.type = 'CLASS_STEREOTYPE'
    elif t.value in RELATION_STEREOTYPE:
        t.type = 'RELATION_STEREOTYPE'
    elif t.value in RESERVED:
        t.type = 'RESERVED'
    elif t.value in NATIVE_TYPES:
        t.type = 'NATIVE_TYPE'
    elif t.value in META_ATTRIBUTES:
        t.type = 'META_ATTRIBUTE'
    else:
        t.type = 'ID'  # Gabriel aqui que vai ficar o identificador
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

def t_error(t):
    line = t.lineno
    col = find_column(t, t.lexer)
    print(f"Erro léxico na linha {line}, coluna {col}: caractere inválido '{t.value[0]}'")
    t.lexer.skip(1)

def build_lexer(**kwargs):
    lexer = lex.lex(**kwargs)
    lexer.line_start = 0
    return lexer