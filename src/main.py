import sys
from report import coletar_tokens, tabela_analitica, tabela_sintese


def main():
    if len(sys.argv) != 2:
        print("uso: python main.py <arquivo.tonto>")
        sys.exit(1)

    path = sys.argv[1]
    tokens = coletar_tokens(path)

    print('=== VISÃO ANALÍTICA ===')
    print(tabela_analitica(tokens))
    print()
    print('=== TABELA SÍNTESE ===')
    print(tabela_sintese(tokens))


if __name__ == '__main__':
    main()