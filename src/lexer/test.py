import io
import unittest
from contextlib import redirect_stdout

from lexer import classify_id, build_lexer, find_column


class TestLexerExtras(unittest.TestCase):

    def tokenize(self, source):
        lexer = build_lexer()
        lexer.input(source)
        return list(lexer)

    def test_package_declaration_tokens(self):
        result = self.tokenize("package demo;")

        self.assertEqual(
            [(t.type, t.value) for t in result],
            [
                ("PACKAGE", "package"),
                ("PACKAGE_NAME", "demo"),
                ("SEMICOLON", ";"),
            ],
        )

    def test_import_tokens(self):
        result = self.tokenize("import bar")

        self.assertEqual(
            [(t.type, t.value) for t in result],
            [
                ("RESERVED", "import"),
                ("RELATION_NAME", "bar"),
            ],
        )

    def test_class_declaration_tokens(self):
        result = self.tokenize("kind Person")

        self.assertEqual(
            [(t.type, t.value) for t in result],
            [
                ("CLASS_STEREOTYPE", "kind"),
                ("CLASS_NAME", "Person"),
            ],
        )

    def test_specializes_tokens(self):
        result = self.tokenize("kind Student specializes Person")

        self.assertEqual(
            [t.type for t in result],
            [
                "CLASS_STEREOTYPE",
                "CLASS_NAME",
                "RESERVED",
                "CLASS_NAME",
            ],
        )

    def test_attribute_tokens(self):
        result = self.tokenize("name: string")

        self.assertEqual(
            [(t.type, t.value) for t in result],
            [
                ("RELATION_NAME", "name"),
                ("COLON", ":"),
                ("NATIVE_TYPE", "string"),
            ],
        )

    def test_all_native_types(self):
        result = self.tokenize(
            "number string boolean date time datetime"
        )

        self.assertEqual(
            [t.type for t in result],
            ["NATIVE_TYPE"] * 6,
        )

    def test_datatype_as_attribute_type(self):
        result = self.tokenize("address: AddressDataType")

        self.assertEqual(
            [t.type for t in result],
            ["RELATION_NAME", "COLON", "DATATYPE_NAME"],
        )

    def test_class_as_attribute_type(self):
        result = self.tokenize("address: Address")

        self.assertEqual(
            [t.type for t in result],
            ["RELATION_NAME", "COLON", "CLASS_NAME"],
        )

    def test_cardinality_one(self):
        result = self.tokenize("[1]")

        self.assertEqual(
            [(t.type, t.value) for t in result],
            [
                ("LBRACKET", "["),
                ("NUMBER", 1),
                ("RBRACKET", "]"),
            ],
        )

    def test_cardinality_range(self):
        result = self.tokenize("[1..]")

        self.assertEqual(
            [(t.type, t.value) for t in result],
            [
                ("LBRACKET", "["),
                ("NUMBER", 1),
                ("RANGE", ".."),
                ("RBRACKET", "]"),
            ],
        )

    def test_empty_cardinality(self):
        result = self.tokenize("[]")

        self.assertEqual(
            [t.type for t in result],
            ["LBRACKET", "RBRACKET"],
        )

    def test_meta_attributes(self):
        result = self.tokenize("{ ordered const derived subsets redefines }")

        self.assertEqual(
            [t.type for t in result],
            [
                "LBRACE",
                "META_ATTRIBUTE",
                "META_ATTRIBUTE",
                "META_ATTRIBUTE",
                "META_ATTRIBUTE",
                "META_ATTRIBUTE",
                "RBRACE",
            ],
        )

    def test_string_literal(self):
        result = self.tokenize('"hello world"')

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, "STRING")
        self.assertEqual(result[0].value, "hello world")

    def test_date_literal(self):
        result = self.tokenize("'2025-04-23'")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, "DATE_LITERAL")
        self.assertEqual(result[0].value, "2025-04-23")

    def test_time_literal(self):
        result = self.tokenize("'14:30:00'")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, "TIME_LITERAL")
        self.assertEqual(result[0].value, "14:30:00")

    def test_datetime_literal(self):
        result = self.tokenize("'2025-04-23T14:30:00'")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, "DATETIME_LITERAL")
        self.assertEqual(result[0].value, "2025-04-23T14:30:00")

    def test_line_comment_is_ignored(self):
        result = self.tokenize("kind // comment\nPerson")

        self.assertEqual(
            [t.type for t in result],
            ["CLASS_STEREOTYPE", "CLASS_NAME"],
        )

    def test_block_comment_is_ignored(self):
        result = self.tokenize("kind /* comment */ Person")

        self.assertEqual(
            [t.type for t in result],
            ["CLASS_STEREOTYPE", "CLASS_NAME"],
        )

    def test_line_numbers_after_comment(self):
        result = self.tokenize("kind Person\nrole Student")

        self.assertEqual(
            [t.lineno for t in result],
            [1, 1, 2, 2],
        )

    def test_token_columns(self):
        lexer = build_lexer()
        lexer.input("kind Person")

        result = list(lexer)

        self.assertEqual(
            [find_column(t, lexer) for t in result],
            [1, 6],
        )

    def test_invalid_character_is_reported(self):
        output = io.StringIO()

        with redirect_stdout(output):
            result = self.tokenize("kind $ Person")

        self.assertIn("caractere inválido", output.getvalue())
        self.assertEqual(
            [t.type for t in result],
            ["CLASS_STEREOTYPE", "CLASS_NAME"],
        )


if __name__ == "__main__":
    unittest.main()
