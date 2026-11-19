import os
import unittest

from parser.parser import parse
from parser.symbol_table import build_symbol_table

HEADER = "package Teste\n"


def table_of(body):
    result, errors = parse(HEADER + body)
    assert result is not None, f"erro fatal no parser: {errors}"
    return build_symbol_table(result)


def names(symbols):
    return [s["name"] for s in symbols]


class TestEscopoGlobal(unittest.TestCase):

    def test_pacote_e_registrado(self):
        t = table_of("kind A\n")
        pacote = [s for s in t.global_scope.symbols["Teste"]]
        self.assertEqual(pacote[0].kind, "package")

    def test_classes_datatypes_enums_gensets(self):
        t = table_of(
            "kind A\n"
            "datatype D {\n x: string\n}\n"
            "enum E { X01, Y02 }\n"
            "genset G where A specializes A\n"
        )
        self.assertEqual(t.global_scope.lookup_local("A")[0].kind, "class")
        self.assertEqual(t.global_scope.lookup_local("D")[0].kind, "datatype")
        self.assertEqual(t.global_scope.lookup_local("E")[0].kind, "enum")
        self.assertEqual(t.global_scope.lookup_local("G")[0].kind, "genset")

    def test_import_registrado(self):
        t = table_of("import bar\nkind A\n")
        self.assertEqual(t.global_scope.lookup_local("bar")[0].kind, "import")

    def test_relacao_externa_no_global(self):
        t = table_of("kind A\nkind B\nrelation A [1] -- liga -- [1] B\n")
        sym = t.global_scope.lookup_local("liga")[0]
        self.assertEqual(sym.kind, "relation")
        self.assertEqual(sym.references["source"], "A")
        self.assertEqual(sym.references["target"], "B")

    def test_linha_preservada(self):
        t = table_of("kind A\n")
        self.assertEqual(t.global_scope.lookup_local("A")[0].line, 2)


class TestEscoposDeClasse(unittest.TestCase):

    def setUp(self):
        self.t = table_of(
            "kind Pessoa {\n"
            "  nome: string\n"
            "  idade: number\n"
            "  @componentOf [1] <>-- [1..*] Endereco\n"
            "}\n"
        )
        self.scope = self.t.get_scope("Pessoa")

    def test_classe_gera_escopo(self):
        self.assertIsNotNone(self.scope)
        self.assertEqual(self.scope.kind, "class")
        self.assertEqual(self.scope.parent.name, "<global>")

    def test_atributos_no_escopo_da_classe(self):
        self.assertEqual(self.scope.lookup_local("nome")[0].kind, "attribute")
        self.assertEqual(self.scope.lookup_local("idade")[0].kind, "attribute")

    def test_relacao_interna_no_escopo_da_classe(self):
        rels = [s for name, group in self.scope.symbols.items()
                for s in group if s.kind == "relation"]
        self.assertEqual(len(rels), 1)
        self.assertTrue(rels[0].anonymous)
        self.assertEqual(rels[0].references["owner"] if "owner" in rels[0].references
                         else rels[0].references["source"], "Pessoa")
        self.assertEqual(rels[0].references["target"], "Endereco")

    def test_membros_nao_vazam_para_o_global(self):
        self.assertEqual(self.t.global_scope.lookup_local("nome"), [])
        self.assertEqual(self.t.global_scope.lookup_local("idade"), [])

    def test_duas_classes_podem_ter_o_mesmo_atributo(self):
        t = table_of(
            "kind A {\n  nome: string\n}\n"
            "kind B {\n  nome: string\n}\n"
        )
        self.assertEqual(t.get_scope("A").lookup_local("nome")[0].kind, "attribute")
        self.assertEqual(t.get_scope("B").lookup_local("nome")[0].kind, "attribute")


class TestEscoposDeDatatypeEEnum(unittest.TestCase):

    def test_atributos_do_datatype(self):
        t = table_of("datatype Endereco {\n  rua: string\n  numero: number\n}\n")
        scope = t.get_scope("Endereco")
        self.assertEqual(scope.kind, "datatype")
        self.assertEqual(scope.lookup_local("rua")[0].kind, "attribute")
        self.assertEqual(scope.lookup_local("numero")[0].kind, "attribute")

    def test_itens_do_enum(self):
        t = table_of("enum Cor { Azul01, Verde02 }\n")
        scope = t.get_scope("Cor")
        self.assertEqual(scope.kind, "enum")
        self.assertEqual(scope.lookup_local("Azul01")[0].kind, "enum_item")
        self.assertEqual(scope.lookup_local("Verde02")[0].kind, "enum_item")


class TestReferenciasSemResolucao(unittest.TestCase):

    def test_pai_preservado_sem_validar(self):
        t = table_of("phase B specializes Inexistente\n")
        sym = t.global_scope.lookup_local("B")[0]
        self.assertEqual(sym.references["parent"], ["Inexistente"])

    def test_tipo_preservado_sem_validar(self):
        t = table_of("kind A {\n  x: TipoInexistente\n}\n")
        sym = t.get_scope("A").lookup_local("x")[0]
        self.assertEqual(sym.references["type"], "TipoInexistente")

    def test_destino_preservado_sem_validar(self):
        t = table_of("kind A {\n  @mediation [1] -- [1] Inexistente\n}\n")
        rels = [s for group in t.get_scope("A").symbols.values()
                for s in group if s.kind == "relation"]
        self.assertEqual(rels[0].references["target"], "Inexistente")

    def test_duplicidade_preservada_sem_erro(self):
        t = table_of("kind A\nkind A\n")
        self.assertEqual(len(t.global_scope.lookup_local("A")), 2)


class TestSerializacao(unittest.TestCase):

    def test_to_dict(self):
        t = table_of("kind A {\n  nome: string\n}\n")
        d = t.to_dict()
        self.assertIn("global", d)
        self.assertIn("scopes", d)
        self.assertEqual(
            [s["name"] for s in d["global"]["symbols"] if s["kind"] == "class"], ["A"])
        self.assertEqual(d["scopes"][0]["name"], "A")
        self.assertEqual(names(d["scopes"][0]["symbols"]), ["nome"])

    def test_arquivo_sem_resultado_nao_quebra(self):
        self.assertEqual(build_symbol_table(None).to_dict()["scopes"], [])


class TestIntegracao(unittest.TestCase):

    def test_parser_example(self):
        caminho = os.path.join(os.path.dirname(__file__), "..", "..",
                               "dataset-test", "ParserExample", "src", "parser.tonto")
        with open(caminho, encoding="utf-8") as f:
            result, errors = parse(f.read())
        self.assertEqual(errors, [])
        t = build_symbol_table(result)
        self.assertEqual(len(t.scopes), 21 + 2 + 1)  # classes + datatypes + enum
        self.assertIsNotNone(t.get_scope("Person"))
        self.assertIsNotNone(t.get_scope("Address"))
        self.assertIsNotNone(t.get_scope("EyeColor"))


if __name__ == "__main__":
    unittest.main()
