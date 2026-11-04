import sys

from parser.report import (arquivos_tonto, analisar_arquivo, tabela_sintese,
                           relatorio_erros, para_json)


def main():
    args = sys.argv[1:]
    em_json = "--json" in args
    arquivos = arquivos_tonto([a for a in args if a != "--json"])
    if not arquivos:
        sys.exit("uso: python main.py arquivo.tonto|pasta [...] [--json]")
    analises = [analisar_arquivo(a) for a in arquivos]
    if em_json:
        print(para_json(analises))
        return
    print(tabela_sintese(analises))
    print()
    print(relatorio_erros(analises))


if __name__ == "__main__":
    main()