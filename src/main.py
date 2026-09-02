import sys
from lexer import build_lexer, find_column

def main():
    if len(sys.argv) != 2:
        print("uso: python main.py <arquivo.tonto>")
        sys.exit(1)

    path = sys.argv[1]
    with open(path, encoding='utf-8') as f:
        data = f.read()

    lexer = build_lexer()
    lexer.input(data)

    for tok in lexer:
        col = find_column(tok, lexer)
        print(f"{tok.type:20} {tok.value!r:30} linha={tok.lineno} col={col}")

if __name__ == '__main__':
    main()