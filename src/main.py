from parser.parser import parse


def main():
    with open("exemplo.tonto", "r", encoding="utf-8") as file:
        source = file.read()

    result, errors = parse(source)

    if errors:
        for error in errors:
            print(
                f"Linha {error['line']}: {error['message']}\n"
                f"Sugestão: {error['suggestion']}"
            )
        return

    print("Análise sintática concluída.")
    print(result)


if __name__ == "__main__":
    main()