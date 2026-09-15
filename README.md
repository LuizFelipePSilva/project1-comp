# Analisador Léxico para TONTO

Analisador léxico para a linguagem TONTO (Textual Ontology Language), desenvolvido para a disciplina de Compiladores (UFERSA).

## Integrantes

- Luiz Felipe — setup, palavras reservadas, estereótipos, tipos nativos, meta-atributos, símbolos especiais, contador de linha/coluna
- Gabriel Cleverton — regras de nomes (classe, relação, instância, datatype), tratamento de erros
- Rian Valentin — saídas (tabela de tokens, tabela de síntese), testes de integração, documentação

## Requisitos

- Python 3.10+
- PLY 3.11

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Uso

```bash
cd src
python main.py caminho/para/arquivo.tonto
```

Exemplo:

```bash
python main.py ../dataset-test/CarExample/src/car.tonto
```

## Estrutura do projeto

```
projeto1/
├── src/
│   ├── lexer.py   # regras léxicas (PLY)
│   └── main.py    # ponto de entrada
├── dataset-test/  # exemplos de teste (.tonto)
├── requirements.txt
└── README.md
```

## O que o lexer reconhece

- Estereótipos de classe (`kind`, `role`, `phase`, `relator`, etc.)
- Estereótipos de relação (`mediation`, `componentOf`, `characterization`, etc.)
- Palavras reservadas (`package`, `import`, `genset`, `specializes`, etc.)
- Tipos nativos (`number`, `string`, `boolean`, `date`, `time`, `datetime`)
- Meta-atributos (`ordered`, `const`, `derived`, `subsets`, `redefines`)
- Símbolos especiais (`{`, `}`, `(`, `)`, `[`, `]`, `..`, `<>--`, `--<>`, `--`, `*`, `@`, `:`)
- Nomes de classes, relações, instâncias e datatypes (convenções específicas)
- Números
- Linha e coluna de cada token

## Saída

Para cada token: tipo, valor, linha e coluna. Erros léxicos são reportados por linha, sem interromper a análise.

## Tabela síntese

Conforme especificado no enunciado, a tabela síntese soma os
tokens nas seguintes categorias:

| Categoria pedida         | Tokens do lexer                                    |
|---------------------------|----------------------------------------------------|
| Classes                   | `CLASS_NAME`                                       |
| Relações                  | `RELATION_NAME`                                    |
| Palavras-chave             | `CLASS_STEREOTYPE`, `RELATION_STEREOTYPE`, `NATIVE_TYPE` |
| Indivíduos (instâncias)   | `INSTANCE_NAME`                                    |
| Palavras reservadas       | `RESERVED`                                         |
| Meta-atributos            | `META_ATTRIBUTE`                                   |

Tokens fora dessas categorias (símbolos, literais, `DATATYPE_NAME`,
`PACKAGE_NAME`) aparecem agrupados em "Outros" para também serem incrementados na contagem
total.

## Gerando as saídas

python src/report.py caminho/arquivo.tonto [--csv pasta]

## Comportamento esperado com vírgulas

A especificação do TONTO não inclui vírgula
entre os símbolos especiais aceitos. Vários arquivos de exemplo usam vírgula para separar itens em listas (ex.:
`specifics Pizza, Bebida, Petisco`). Isso gera erro
— o analisador reporta a linha/coluna e uma sugestão, sem travar a análise,
conforme exigido pelo enunciado.

## Exemplos de teste

Retirados de: <https://github.com/patricioalencar/Compiladores_UFERSA>
