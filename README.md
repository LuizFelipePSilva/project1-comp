# Analisador Semântico para TONTO

Projeto da disciplina de Compiladores da UFERSA. O analisador semântico complementa as etapas léxica e sintática, verificando padrões de projeto de ontologias (ODPs) descritos em arquivos TONTO.

## Análise semântica

O analisador reconhece e valida seis padrões: **Subkind, Role, Phase, Relator, Mode e RoleMixin**.

- **Subkind:** deve especializar diretamente um `kind`; o genset deve ter um `kind` como `general` e declarar `disjoint`. `complete` é opcional.
- **Role:** deve especializar diretamente um `kind`; `disjoint` não se aplica ao genset de roles. `complete` é opcional.
- **Phase:** deve especializar diretamente um `kind` e ter ao menos uma phase irmã. O genset deve ser `disjoint`; `complete` é opcional.
- **Relator:** deve mediar pelo menos duas entidades declaradas e distintas com `@mediation`, além de possuir uma relação `@material` entre entidades mediadas.
- **Mode:** verifica a presença das relações `@characterization` e `@externalDependence`.
- **RoleMixin:** deve agrupar roles que especializam diretamente kinds distintos, em um genset `disjoint complete`.

Os diagnósticos semânticos incluem localização por linha e sugestões de coerção. O analisador também infere padrões incompletos, registrando confiança, evidências e elementos faltantes. A análise continua após erros léxicos ou sintáticos, e esses erros são apresentados junto com os resultados semânticos obtidos da estrutura recuperada.

## Execução

Na pasta `src/`, use `--semantico` para gerar o relatório no terminal:

```bash
python main.py caminho/arquivo.tonto --semantico
```

A saída JSON padrão inclui, para cada arquivo, o campo `semantic`, com `patterns`, `coercions` e `inferences`.

## Testes semânticos

```bash
cd src
python -m unittest semantic.test_semantic semantic.test_phase_relator semantic.test_mode_rolemixin_inference -v
```

Os exemplos do PDF são ilustrativos. Quando um exemplo usa nomes que não seguem as convenções aceitas pelo lexer/parser do projeto, esses nomes precisam ser adaptados para validar o padrão; os testes não alteram as regras do compilador.
