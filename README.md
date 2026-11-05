# Analisador Léxico e Sintático para TONTO

Analisadores léxico e sintático para a linguagem **TONTO** (*Textual Ontology Language*), desenvolvidos para a disciplina de Compiladores (UFERSA, Prof. Patrício de Alencar Silva).

O programa lê arquivos `.tonto`, verifica a estrutura das declarações e produz duas saídas: uma **síntese dos construtos encontrados** e um **relatório de erros com sugestões de correção**.

## Integrantes

- **Luiz Felipe**: setup, palavras reservadas, estereótipos, tipos nativos, meta-atributos, símbolos especiais, contador de linha/coluna
- **Gabriel Cleverton**: regras de nomes (classe, relação, instância, datatype), tratamento de erros no lexer. No parser: datatypes, enums, saídas (síntese, relatório de erros, JSON), recuperação de erro e testes
- **Rian Valentin**: tabela de tokens, tabela de síntese léxica, testes de integração do lexer, documentação

## Requisitos e instalação

- Python 3.10 ou superior
- PLY 3.11

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Como usar

Todos os comandos são executados dentro de `src/`.

```bash
cd src

# JSON (saída padrão) de um arquivo
python main.py ../dataset-test/CarExample/src/car.tonto

# JSON de todos os .tonto de uma pasta, salvo em arquivo
python main.py ../dataset-test > saida.json

# Tabela síntese e relatório de erros em texto
python main.py ../dataset-test/CarExample/src/car.tonto --texto
```

Para rodar só o parser em um exemplo fixo (imprime o resultado e os erros em JSON):

```bash
python -m parser.parser
```

Para a análise léxica isolada (tabela de tokens e síntese de tokens):

```bash
python -m lexer.report ../dataset-test/CarExample/src/car.tonto [--csv pasta]
```

## Estrutura do projeto

```
src/
├── main.py                  # ponto de entrada: arquivos ou pastas -> JSON ou texto
├── lexer/
│   ├── lexer.py             # analisador léxico (PLY lex)
│   └── report.py            # tabela de tokens e síntese léxica
└── parser/
    ├── parser.py            # núcleo da gramática: ontologia, pacote, import,
    │                        #   classe, atributo, cardinalidade, recuperação de erro
    ├── relations.py         # relações (internas e externas) e gensets
    ├── typedecls.py         # datatype e enum
    ├── report.py            # síntese, relatório de erros e JSON
    ├── test_types_enums.py  # testes de datatype, enum, erros e dataset
    └── test_relations.py    # testes de relações e gensets
dataset-test/                # arquivos .tonto de exemplo
└── ParserExample/src/parser_example.tonto   # modelo completo, cobre todas as construções
```

## O analisador sintático

### Visão geral

O fluxo de uma análise tem quatro etapas:

```
arquivo .tonto ──> lexer ──> tokens ──> parser ──> estrutura ──> report
                    (PLY lex)            (PLY yacc)  (dicionários)  (JSON / texto)
```

1. O **lexer** (`lexer/lexer.py`) transforma o texto em tokens (`CLASS_STEREOTYPE`, `CLASS_NAME`, `LBRACE` etc.) e reporta erros léxicos, como nomes inválidos.
2. O **parser** (`parser/parser.py`) consome os tokens e verifica se eles formam declarações válidas, de acordo com a gramática.
3. Cada regra da gramática devolve um dicionário Python. Juntos, eles formam a estrutura que representa a ontologia.
4. O **report** (`parser/report.py`) lê essa estrutura e gera a síntese e o relatório de erros.

### Ferramenta: PLY

A geração do parser usa o **PLY**, implementação em Python do modelo `lex`/`yacc`. Ele constrói um analisador **LALR(1) ascendente (bottom-up)**, o mesmo tipo de análise do Bison: os tokens são empilhados (*shift*) e as regras são aplicadas quando o lado direito de uma produção aparece no topo da pilha (*reduce*).

Cada produção é uma função Python cuja *docstring* é a regra da gramática:

```python
def p_declaration_enum(p):
    """declaration : ENUM class_identifier LBRACE enum_body RBRACE"""
    p[0] = {"kind": "enum", "name": p[2], "individuals": p[4], "line": p.lineno(1)}
```

`p[1]`, `p[2]`... são os símbolos do lado direito da regra, e `p[0]` é o valor que a regra devolve.

### Gramática

Resumo das construções aceitas. Os nomes em maiúsculas são tokens do lexer, `|` separa alternativas, `[ ]` indica opcional e `{ }` indica repetição.

```
ontology      : package_decl declaration_list
package_decl  : PACKAGE PACKAGE_NAME [SEMICOLON]

declaration   : import_decl
              | class_decl
              | datatype_decl
              | enum_decl
              | genset_decl
              | external_relation
              | error                                  # recuperação de erro

import_decl   : IMPORT RELATION_NAME

class_decl    : CLASS_STEREOTYPE CLASS_NAME [SPECIALIZES name_list] [ "{" {member} "}" ]
member        : attribute | internal_relation
attribute     : nome ":" tipo [cardinality] [meta_attribute]

datatype_decl : DATATYPE (CLASS_NAME | DATATYPE_NAME) "{" {attribute} "}"
enum_decl     : ENUM CLASS_NAME "{" [ individuo {"," individuo} [","] ] "}"

genset_decl   : {DISJOINT | OVERLAPPING | COMPLETE | INCOMPLETE} GENSET nome genset_body
genset_body   : "{" GENERAL Classe [CATEGORIZER Classe] SPECIFICS name_list "}"   # forma longa
              | WHERE name_list SPECIALIZES Classe                                # forma curta

external_relation : ["@" RELATION_STEREOTYPE] RELATION Classe
                    cardinality link cardinality Classe
internal_relation : "@" RELATION_STEREOTYPE cardinality link cardinality Classe
                  | link cardinality Classe     # sem estereótipo: começa pela seta,
                                                # sem cardinalidade de origem

link          : "--" | "<>--" | "--<>"
              | ("--" | "<>--" | "--<>") RELATION_NAME "--"
```

Onde cada parte está:

| Construção | Arquivo |
|---|---|
| ontologia, pacote, import, classe, atributo, cardinalidade, meta-atributo, recuperação de erro | `parser/parser.py` |
| relações internas e externas, genset (forma longa e curta) | `parser/relations.py` |
| `datatype` e `enum` | `parser/typedecls.py` |

### Exemplo de código aceito

```tonto
package Exemplo

datatype Address {
    street: string
    number: number
}

enum EyeColor { Blue01, Green02, Brown03, Black04 }

kind Person {
    name: string
    birthDate: date {const}
}
phase Child specializes Person

disjoint complete genset PersonAgeGroup where Child, Adult specializes Person

kind University {
    @componentOf [1] <>-- [1..*] Department
}
@mediation relation EmploymentContract [1..*] -- [1] Employee
```

Um exemplo completo, com 21 classes, 2 datatypes, 1 enum, 3 gensets e 7 relações, está em `dataset-test/ParserExample/src/parser_example.tonto`.

### Representação interna

Cada declaração vira um dicionário com o campo `kind`:

| `kind` | Campos principais |
|---|---|
| `package` | `name`, `line` |
| `import` | `name`, `line` |
| `class` | `stereotype`, `name`, `parent`, `attributes`, `line` |
| `attribute` | `name`, `type`, `cardinality`, `meta_attribute`, `line` |
| `datatype` | `name`, `attributes`, `line` |
| `enum` | `name`, `individuals`, `line` |
| `genset` | `name`, `modifiers`, `form`, `general`, `categorizer`, `specifics`, `line` |
| `relation` | `internal`, `stereotype`, `source`, `source_cardinality`, `operator`, `name`, `target_cardinality`, `target`, `line` |
| `error` | `line` (declaração descartada pela recuperação de erro) |

A cardinalidade é um dicionário `{"min": N, "max": N}`, em que `max: null` significa ilimitado (`*`). Assim, `[1..*]` vira `{"min": 1, "max": null}`.

O campo `internal` da relação diz se ela está dentro de uma classe (`true`) ou é uma declaração de topo (`false`). O campo `form` do genset diz se foi usada a forma longa (`"long"`) ou a curta (`"short"`).

**Decisão de projeto:** a relação interna com estereótipo (`@componentOf`) é aceita com cardinalidade de origem, mas a relação interna sem estereótipo só é aceita quando começa direto pela seta. Isso evita ambiguidade com a cardinalidade opcional no final de um atributo, que geraria conflito na gramática.

### Tratamento de erros

Quando o parser encontra um token que não cabe em nenhuma regra, a função `p_error` registra o erro com **linha, coluna, mensagem e sugestão**, e a análise continua. A recuperação funciona assim:

1. `p_error` guarda o erro e devolve o controle ao PLY.
2. O PLY desempilha estados até achar um onde o símbolo especial `error` possa ser lido. Esse estado é a produção `declaration : error`.
3. Os tokens seguintes são descartados até aparecer um que possa iniciar uma nova declaração: estereótipo de classe, `datatype`, `enum`, `genset`, `relation`, `@`, `import` ou modificador de genset.
4. A análise segue a partir daí. A declaração com problema aparece na estrutura como `{"kind": "error"}`.

Isso permite que **vários erros sejam reportados na mesma execução** e que as declarações corretas continuem aparecendo na síntese.

As sugestões mudam conforme o caso:

- primeiro token do arquivo diferente de `package`: "Todo modelo deve começar com package Nome";
- vírgula fora de lista: manda remover;
- segundo `package`: explica que só pode haver um;
- início de nova declaração dentro de bloco aberto: indica que provavelmente falta `}`;
- demais casos: mostra a forma correta de `datatype`, `enum` e `kind`.

Exemplo, com um `enum` sem chaves:

```tonto
package Demo
enum Cor Blue01, Green02
datatype Endereco {
  rua: string
}
kind Pessoa {
  nome: string
}
```

```
[sintático] linha 2:10 - Token inesperado 'Blue01' (INSTANCE_NAME).
    Sugestão: Verifique a estrutura da declaração: datatype Nome { atributo: tipo },
              enum Nome { Ind01, Ind02 }, kind Nome { ... }.
```

O `enum` é descartado, mas `Endereco` e `Pessoa` continuam na síntese.

## Saídas

### JSON (padrão)

```json
{
  "files": [
    {
      "file": "demo.tonto",
      "lexical_errors": [],
      "syntax_errors": [
        { "line": 2, "column": 10, "message": "...", "suggestion": "..." }
      ],
      "fatal": false,
      "package": "Demo",
      "imports": [],
      "classes": [
        { "name": "Pessoa", "stereotype": "kind", "parent": null, "internal_relations": [] }
      ],
      "external_relations": [],
      "datatypes": ["Endereco"],
      "enums": [],
      "gensets": []
    }
  ]
}
```

Cada arquivo traz seu pacote, imports, classes (com estereótipo, pai e relações internas), relações externas, datatypes, enums (com indivíduos), gensets e as listas de erros léxicos e sintáticos.

O campo `fatal` indica se o parser não conseguiu produzir a estrutura da ontologia. Nesse caso o arquivo traz `"fatal": true` e `"message": "sem síntese (erro fatal)"`, e os campos `package`, `classes` etc. não aparecem. Exemplo: um arquivo que começa direto por `kind A`, sem `package`.

### Texto (`--texto`)

Gera a **tabela síntese** (pacotes; classes por pacote; relações internas por classe; relações externas; quantidade e nomes de datatypes, enums e gensets; totais) e o **relatório de erros** (léxicos e sintáticos, com linha, coluna e sugestão). Arquivos sem resultado aparecem na tabela com o aviso:

```
Arquivo X: sem síntese (erro fatal)
```

## Testes

```bash
cd src
python -m unittest parser.test_types_enums parser.test_relations -v
```

`test_types_enums.py` cobre:

- `datatype` e `enum` válidos, incluindo vazios e em várias linhas;
- um caso inválido para cada regra (datatype sem nome, sem chaves, sem `:` ou sem `}`; enum sem chaves, sem vírgula, sem nome ou sem `}`; classe sem nome; genset sem corpo; relação sem destino; `package` duplicado e ausente), verificando a linha do erro, a existência de sugestão e o que sobra depois da recuperação;
- a saída em JSON e o aviso de arquivo sem síntese;
- a execução sobre todos os `.tonto` de `dataset-test/`, confirmando que nenhum arquivo trava, que os arquivos corretos não geram erro e que o modelo `parser_example.tonto` passa sem erros e com as contagens esperadas.

`test_relations.py` cobre relações e gensets.

## Limitações conhecidas

- **`import` antes de `package`.** Vários arquivos do `dataset-test/` começam com `import`, mas a gramática exige `package` como primeira declaração, conforme o enunciado. Esses arquivos geram um erro na linha 1.
- **Erros léxicos geram erros sintáticos em cascata.** O lexer descarta um token inválido, e o parser reclama da lacuna. Exemplo: `Methylphenidate_` (sublinhado no final) é rejeitado, e o parser acusa erro no `specializes` seguinte.
- **Indivíduos de enum com sublinhado** (`A_Plus01`) são rejeitados pela regra de nomes do lexer, e o enum correspondente não entra na síntese.
- **Tipo `int`.** O enunciado lista seis tipos nativos (`number`, `string`, `boolean`, `date`, `time`, `datetime`). O exemplo de `datatype` do PDF usa `int`, que não está na lista e portanto é rejeitado.
- **Bloco `{` sem `}`.** A declaração aberta é descartada pela recuperação de erro e não aparece na síntese; o erro aparece no relatório.

#Exemplos Teste
Retirados de: <https://github.com/patricioalencar/Compiladores_UFERSA>
