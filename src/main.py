import sys

from parser.report import (arquivos_tonto, analisar_arquivo, tabela_sintese,
                           relatorio_erros, para_json)


def main():
    args = sys.argv[1:]
    em_texto = "--texto" in args
    arquivos = arquivos_tonto([a for a in args if a != "--texto"])
    if not arquivos:
        sys.exit("uso: python main.py arquivo.tonto|pasta [...] [--texto]")
    analises = [analisar_arquivo(a) for a in arquivos]

    if em_texto:
        print(tabela_sintese(analises))
        print()
        print(relatorio_erros(analises))
    else:
        print(para_json(analises))


if __name__ == "__main__":
    main()