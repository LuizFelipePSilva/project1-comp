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

> análise léxica bruta -> `src/main.py`
> Imprime a lista de tokens reconhecidos (tipo, valor, linha, coluna), reportando erros léxicos por linha sem interromper a análise.

Para gerar a tabela de tokens e a tabela síntese:

```bash
cd src
python report.py caminho/para/arquivo.tonto [--csv pasta]
```

Exemplo:

```bash
python report.py ../dataset-test/CarExample/src/car.tonto
```

> geração de relatórios -> `src/report.py`
> Usa o lexer para montar a tabela de tokens e a tabela síntese (contagem por categoria). O `--csv pasta` é opcional e exporta as duas tabelas como CSV.

Para rodar os testes de integração:

```bash
cd src
python -m unittest testintegration -v
```

> teste de integração -> `src/testintegration.py`
> Roda o lexer sobre os arquivos de exemplo em `dataset-test/` e valida se a análise léxica se comporta como esperado (tokens gerados, tratamento de erros como vírgulas fora da especificação, etc.).

## Estrutura do projeto

```
projeto1/
├── src/
│   ├── lexer.py          # regras léxicas (PLY)
│   ├── main.py            # ponto de entrada
│   ├── report.py          # geração da tabela de tokens e da tabela síntese
│   └── testintegration.py # testes de integração (roda o lexer sobre os arquivos de dataset-test)
├── dataset-test/           # exemplos de teste (.tonto)
├── requirements.txt
└── README.md
```

## Descrição dos arquivos

- **`src/lexer.py`** — define as regras léxicas usando PLY: estereótipos, palavras reservadas, tipos nativos, meta-atributos, símbolos especiais e as convenções de nomes (classe, relação, instância, datatype). É o núcleo do analisador: transforma o texto `.tonto` em uma sequência de tokens, já com linha e coluna.
- **`src/main.py`** — ponto de entrada da aplicação. Recebe o caminho de um arquivo `.tonto`, chama o `lexer.py` e imprime a lista de tokens reconhecidos (tipo, valor, linha, coluna), reportando erros léxicos sem interromper a análise.
- **`src/report.py`** — usa o `lexer.py` para gerar as saídas do projeto: a tabela de tokens e a tabela síntese (contagem de tokens por categoria pedida no enunciado). Também suporta exportar essas tabelas em CSV.
- **`src/testintegration.py`** — testes de integração do projeto. Roda o lexer sobre os arquivos de exemplo em `dataset-test/` e valida se a análise léxica se comporta como esperado (tokens gerados, tratamento de erros como vírgulas fora da especificação, etc.).
- **`dataset-test/`** — arquivos `.tonto` de exemplo usados tanto para testes manuais (`main.py`/`report.py`) quanto pelos testes de integração.
- **`requirements.txt`** — dependências do projeto (principalmente o PLY).

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

Ver comandos em [Uso](#uso) (`python report.py ...`).

## Rodando os testes de integração

Ver comando em [Uso](#uso) (`python -m unittest testintegration -v`).

## Comportamento esperado com vírgulas

A especificação do TONTO não inclui vírgula
entre os símbolos especiais aceitos. Vários arquivos de exemplo usam vírgula para separar itens em listas (ex.:
`specifics Pizza, Bebida, Petisco`). Isso gera erro
— o analisador reporta a linha/coluna e uma sugestão, sem travar a análise,
conforme exigido pelo enunciado.

## Como o projeto funciona

O fluxo geral do analisador é:

1. **Leitura do arquivo** — `main.py` (ou `report.py`) recebe o caminho de um arquivo `.tonto` como argumento de linha de comando e lê seu conteúdo.
2. **Análise léxica** — o conteúdo é passado para o `lexer.py`, construído com PLY. O lexer varre o texto caractere a caractere/palavra a palavra, casando cada trecho com uma regra (estereótipo, palavra reservada, tipo nativo, meta-atributo, símbolo especial, nome de classe/relação/instância/datatype, número, etc.) e emitindo um token para cada correspondência, sempre acompanhado da linha e coluna onde ocorre.
3. **Tratamento de erros** — quando um trecho do texto não corresponde a nenhuma regra léxica válida (por exemplo, uma vírgula fora do padrão aceito pela especificação do TONTO), o lexer reporta o erro (linha, coluna e uma sugestão) e continua a análise a partir do próximo caractere, em vez de interromper o processo.
4. **Saída bruta (`main.py`)** — imprime a lista de tokens reconhecidos, útil para depuração e para conferir o comportamento do lexer sobre um arquivo específico.
5. **Relatórios (`report.py`)** — consome a mesma lista de tokens e a organiza em duas visões: a tabela completa de tokens e a tabela síntese, que soma os tokens por categoria conforme pedido no enunciado. Opcionalmente, exporta essas tabelas como CSV.
6. **Validação (`testintegration.py`)** — roda o pipeline completo (lexer + geração de saídas) sobre os arquivos de exemplo em `dataset-test/`, garantindo que mudanças no lexer não quebrem o comportamento esperado, incluindo os casos de erro (como o das vírgulas).

## Exemplos de teste

Retirados de: <https://github.com/patricioalencar/Compiladores_UFERSA>