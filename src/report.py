"""visão analítica e tabela síntese do analisador léxico.
"""
import sys
import os
import argparse
import csv
from collections import Counter

from lexer import build_lexer, find_column


def coletar_tokens(caminho):
    """Roda o lexer sobre o arquivo e devolve uma lista de
    (tipo, lexema, linha, coluna) — um item por token reconhecido."""
    with open(caminho, encoding='utf-8') as f:
        dados = f.read()

    lexer = build_lexer()
    lexer.input(dados)

    tokens = []
    for tok in lexer:
        col = find_column(tok, lexer)
        tokens.append((tok.type, tok.value, tok.lineno, col))
    return tokens


def tabela_analitica(tokens):
    header = f"{'TOKEN':<22}{'LEXEMA':<30}{'LINHA':>7}{'COLUNA':>8}"
    linhas = [header, '-' * len(header)]
    for tipo, valor, linha, col in tokens:
        lexema = str(valor)
        if len(lexema) > 28:
            lexema = lexema[:25] + '...'
        linhas.append(f"{tipo:<22}{lexema:<30}{linha:>7}{col:>8}")
    return '\n'.join(linhas)


CATEGORIAS_SINTESE = {
    'Classes': {'CLASS_NAME'},
    'Relações': {'RELATION_NAME'},
    'Palavras-chave': {'CLASS_STEREOTYPE', 'RELATION_STEREOTYPE', 'NATIVE_TYPE'},
    'Indivíduos (instâncias)': {'INSTANCE_NAME'},
    'Palavras reservadas': {'RESERVED'},
    'Meta-atributos': {'META_ATTRIBUTE'},
}


def tabela_sintese(tokens):
    """Tabela síntese conforme exigido: quantidades de
    classes, relações, palavras-chave, indivíduos, palavras reservadas
    e meta-atributos."""
    contagem = Counter(tipo for tipo, *_ in tokens)

    header = f"{'CATEGORIA':<28}{'QUANTIDADE':>12}"
    linhas = [header, '-' * len(header)]

    usados = set()
    for categoria, tipos in CATEGORIAS_SINTESE.items():
        qtd = sum(contagem[t] for t in tipos)
        linhas.append(f"{categoria:<28}{qtd:>12}")
        usados |= tipos

    # tokens que não se encaixam nas 6 categorias pedidas (símbolos,
    # literais, DATATYPE_NAME, PACKAGE_NAME) — exibidos à parte, para
    # não sumirem da contagem total
    outros = sum(qtd for tipo, qtd in contagem.items() if tipo not in usados)
    if outros:
        linhas.append('-' * len(header))
        linhas.append(f"{'Outros (símbolos, literais...)':<28}{outros:>12}")

    total = sum(contagem.values())
    linhas.append('-' * len(header))
    linhas.append(f"{'TOTAL':<28}{total:>12}")
    return '\n'.join(linhas)


def exportar_csv(tokens, pasta_saida):
    os.makedirs(pasta_saida, exist_ok=True)

    with open(os.path.join(pasta_saida, 'visao_analitica.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['token', 'lexema', 'linha', 'coluna'])
        for tipo, valor, linha, col in tokens:
            w.writerow([tipo, valor, linha, col])

    with open(os.path.join(pasta_saida, 'tabela_sintese.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['categoria', 'quantidade'])
        for tipo, qtd in Counter(t for t, *_ in tokens).most_common():
            w.writerow([tipo, qtd])


def main():
    parser = argparse.ArgumentParser(
        description='Gera a visão analítica e a tabela síntese do analisador léxico TONTO.'
    )
    parser.add_argument('arquivo', help='caminho para o arquivo .tonto')
    parser.add_argument('--csv', metavar='PASTA', help='exporta as tabelas como CSV nessa pasta')
    args = parser.parse_args()

    tokens = coletar_tokens(args.arquivo)

    print('=== VISÃO ANALÍTICA ===')
    print(tabela_analitica(tokens))
    print()
    print('=== TABELA SÍNTESE ===')
    print(tabela_sintese(tokens))

    if args.csv:
        exportar_csv(tokens, args.csv)
        print(f'\nCSV exportado em {args.csv}/')


if __name__ == '__main__':
    main()