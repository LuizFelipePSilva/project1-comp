"""
    cd src && python -m unittest parser.test_types_enums -v
"""
import glob
import os
import unittest
import json
from parser.report import analisar_texto, analisar_arquivo, tabela_sintese, relatorio_erros

HEADER = "package Teste\n"
DATASET = os.path.join(os.path.dirname(__file__), "..", "..", "dataset-test")


def analisa(corpo):
    a = analisar_texto(HEADER + corpo)
    return a["resultado"], a["erros_sintaticos"]


class TestValidos(unittest.TestCase):

    def test_datatype(self):
        r, e = analisa("datatype Address {\n  street: string\n  number: number\n}\n")
        self.assertEqual(e, [])
        self.assertEqual(r["datatypes"][0]["name"], "Address")
        self.assertEqual(len(r["datatypes"][0]["attributes"]), 2)

    def test_datatype_vazio(self):
        r, e = analisa("datatype Vazio { }\n")
        self.assertEqual(e, [])

    def test_enum(self):
        r, e = analisa("enum EyeColor { Blue01, Green02, Brown03, Black04 }\n")
        self.assertEqual(e, [])
        self.assertEqual(r["enums"][0]["individuals"], ["Blue01", "Green02", "Brown03", "Black04"])

    def test_enum_multilinha(self):
        r, e = analisa("enum Sangue {\n  APlus01,\n  AMinus02\n}\n")
        self.assertEqual(e, [])


class TestInvalidos(unittest.TestCase):
    """(código, linha do erro, declarações esperadas depois da recuperação)"""
    CASOS = {
        "datatype sem nome":        ("datatype {\n street: string\n}\nkind A\n", 2, ["error", "class"]),
        "datatype sem chaves":      ("datatype Address\n street: string\nkind A\n", 3, ["error", "class"]),
        "datatype sem ':'":         ("datatype Address {\n street string\n}\nkind A\n", 3, ["error", "class"]),
        "datatype sem fechar":      ("datatype Address {\n street: string\nkind A\n", 4, ["error", "class"]),
        "enum sem chaves":          ("enum Cor Blue01, Green02\nkind A\n", 2, ["error", "class"]),
        "enum sem virgula":         ("enum Cor { Blue01 Green02 }\nkind A\n", 2, ["error", "class"]),
        "enum sem nome":            ("enum { Blue01 }\nkind A\n", 2, ["error", "class"]),
        "enum sem fechar":          ("enum Cor { Blue01, Green02\nkind A\n", 3, ["error", "class"]),
        "classe sem nome":          ("kind\nkind A\n", 3, ["error", "class"]),
        "genset sem corpo":         ("kind P\ngenset G\nkind A\n", 4, ["class", "error", "class"]),
        "relacao sem destino":      ("kind P\n@mediation relation P [1] -- [1]\nkind A\n", 4, ["class", "error", "class"]),
        "package duplicado":        ("package Outro\nkind A\n", 2, ["error", "class"]),
    }

    def test_cada_regra_gera_erro_com_sugestao_e_recupera(self):
        for nome, (codigo, linha, decls) in self.CASOS.items():
            with self.subTest(caso=nome):
                r, e = analisa(codigo)
                self.assertIn(linha, [x["line"] for x in e])
                self.assertTrue(all(x["suggestion"] for x in e))
                self.assertEqual([d["kind"] for d in r["declarations"]], decls)

    def test_package_ausente(self):
        a = analisar_texto("kind A\n")
        self.assertEqual(a["erros_sintaticos"][0]["line"], 1)
        self.assertEqual(a["erros_sintaticos"][0]["suggestion"],
                         "Todo modelo deve começar com package Nome")

    def test_package_duplicado_nao_usa_sugestao_de_package_ausente(self):
        r, e = analisa("package Outro\nkind A\n")
        self.assertNotIn("começar com package", e[0]["suggestion"])

    def test_arquivo_sem_resultado_aparece_na_sintese(self):
        a = analisar_texto("kind A\n", "x.tonto")
        self.assertIsNone(a["resultado"])
        self.assertIn("Arquivo x.tonto: sem síntese (erro fatal)", tabela_sintese([a]))
    def test_varios_erros_sincronizam_no_proximo_construto(self):
        r, e = analisa("enum Cor Blue01\ndatatype D {\n x string\n}\nenum Ok { A01, B02 }\nkind Fim\n")
        self.assertGreaterEqual(len(e), 2)
        self.assertEqual([d["name"] for d in r["enums"]], ["Ok"])
        self.assertEqual([c["name"] for c in r["classes"]], ["Fim"])


class TestDataset(unittest.TestCase):

    def arquivos(self):
        return sorted(glob.glob(os.path.join(DATASET, "**", "*.tonto"), recursive=True))

    def test_todos_os_arquivos_rodam_sem_excecao(self):
        arquivos = self.arquivos()
        self.assertGreater(len(arquivos), 0)
        for f in arquivos:
            with self.subTest(arquivo=os.path.basename(f)):
                self.assertIsNotNone(analisar_arquivo(f)["resultado"])

    def test_arquivos_limpos_sem_erros(self):
        for rel in ["CarExample/src/car.tonto", "CarExample/src/carRental.tonto",
                    "Hospital_Model/src/Pessoa.tonto", "Pizzaria_Model/src/Empresa.tonto"]:
            with self.subTest(arquivo=rel):
                a = analisar_arquivo(os.path.join(DATASET, rel))
                self.assertEqual(a["erros_lexicos"] + a["erros_sintaticos"], [])

    def test_saidas(self):
        analises = [analisar_arquivo(f) for f in self.arquivos()]
        self.assertIn("TABELA SÍNTESE", tabela_sintese(analises))
        self.assertIn("RELATÓRIO DE ERROS", relatorio_erros(analises))
        
    def test_json_marca_arquivo_sem_sintese(self):
        fatal = analisar_texto("kind A\n", "x.tonto")
        ok = analisar_texto("package P\nkind A\n", "y.tonto")
        d = json.loads(para_json([fatal, ok]))["files"]
        self.assertTrue(d[0]["fatal"])
        self.assertEqual(d[0]["message"], "sem síntese (erro fatal)")
        self.assertNotIn("package", d[0])
        self.assertFalse(d[1]["fatal"])
        self.assertNotIn("message", d[1])


if __name__ == "__main__":
    unittest.main()