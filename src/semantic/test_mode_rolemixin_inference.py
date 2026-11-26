import glob
import os
import unittest

import patterns
from parser.parser import parse
from parser.report import analisar_texto, para_json, relatorio_semantico
from semantic.core import STATUS_COMPLETO, STATUS_INCOMPLETO, STATUS_INVALIDO, analyze


HEADER = "package ODPTest\n"
MODE_OK = (
    "kind Person\nkind Color\n"
    "mode Mood {\n"
    "  @characterization [1..*] -- [1] Person\n"
    "  @externalDependence [1..*] -- [1] Color\n"
    "}\n"
)
MIXIN_OK = (
    "kind Person\nkind Organization\n"
    "role Customer specializes Person\n"
    "role Supplier specializes Organization\n"
    "roleMixin Client\n"
    "disjoint complete genset ClientRoles {\n"
    "  general Client\n  specifics Customer, Supplier\n}\n"
)


def analyze_body(body):
    ontology, errors = parse(HEADER + body)
    if errors:
        raise AssertionError(errors)
    return analyze(ontology)


def by_name(result, name):
    return [p for p in result.patterns if p.pattern == name]


def codes(result):
    return [c.code for c in result.coercions]


class TestMode(unittest.TestCase):
    def test_completo(self):
        result = analyze_body(MODE_OK)
        self.assertEqual(by_name(result, "mode")[0].status, STATUS_COMPLETO)
        self.assertEqual(codes(result), [])

    def test_falta_dependencia_e_inferida(self):
        result = analyze_body(MODE_OK.replace("  @externalDependence [1..*] -- [1] Color\n", ""))
        self.assertEqual(by_name(result, "mode")[0].status, STATUS_INCOMPLETO)
        self.assertIn("ODP_MODE_SEM_EXTERNALDEPENDENCE", codes(result))
        inference = next(i for i in result.inferences if i.pattern == "mode")
        self.assertIn("@externalDependence", " ".join(inference.missing))

    def test_valida_apenas_presenca_das_duas_relacoes(self):
        source = MODE_OK.replace("[1..*] -- [1] Person", "[0..*] -- [2] Person")
        source = source.replace("@externalDependence [1..*] -- [1] Color",
                                "@externalDependence [0] -- [3] Color")
        result = analyze_body(source)
        self.assertEqual(by_name(result, "mode")[0].status, STATUS_COMPLETO)
        self.assertEqual(codes(result), [])

    def test_mode_nao_exige_alvo_kind_ou_relacoes_unicas(self):
        source = ("kind Person\nrole Occupant specializes Person\nkind Color\n"
                  "mode Mood {\n"
                  "  @characterization [1] -- [2] Occupant\n"
                  "  @characterization [1] -- [2] Person\n"
                  "  @externalDependence [1] -- [2] Color\n}\n")
        result = analyze_body(source)
        self.assertEqual(by_name(result, "mode")[0].status, STATUS_COMPLETO)
        self.assertEqual(codes(result), [])


class TestRoleMixin(unittest.TestCase):
    def test_completo(self):
        result = analyze_body(MIXIN_OK)
        self.assertEqual(by_name(result, "rolemixin")[0].status, STATUS_COMPLETO)
        self.assertEqual(codes(result), [])
        self.assertEqual(by_name(result, "role"), [])

    def test_sem_genset_fica_incompleto_e_sugere(self):
        body = MIXIN_OK.split("disjoint complete genset")[0]
        result = analyze_body(body)
        self.assertEqual(by_name(result, "rolemixin")[0].status, STATUS_INCOMPLETO)
        self.assertIn("ODP_ROLEMIXIN_SEM_GENSET", codes(result))
        self.assertTrue(any(i.pattern == "rolemixin" for i in result.inferences))

    def test_modificadores_obrigatorios(self):
        body = MIXIN_OK.replace("disjoint complete genset", "genset")
        result = analyze_body(body)
        self.assertIn("ODP_ROLEMIXIN_DISJOINT", codes(result))
        self.assertIn("ODP_ROLEMIXIN_COMPLETE", codes(result))

    def test_genset_com_um_role_nao_e_completo(self):
        source = ("kind Person\nrole Customer specializes Person\nroleMixin Client\n"
                  "disjoint complete genset ClientRoles {\n"
                  "  general Client\n  specifics Customer\n}\n")
        result = analyze_body(source)
        self.assertEqual(by_name(result, "rolemixin")[0].status, STATUS_INVALIDO)
        self.assertIn("ODP_ROLEMIXIN_QUANTIDADE", codes(result))

    def test_rolemixin_exige_kinds_com_estereotipo_kind(self):
        source = ("collective People\ncollective Organizations\n"
                  "role Customer specializes People\n"
                  "role Supplier specializes Organizations\n"
                  "roleMixin Client\n"
                  "disjoint complete genset ClientRoles {\n"
                  "  general Client\n  specifics Customer, Supplier\n}\n")
        result = analyze_body(source)
        self.assertEqual(by_name(result, "rolemixin")[0].status, STATUS_INVALIDO)
        self.assertIn("ODP_ROLEMIXIN_ROLE_SEM_KIND", codes(result))


class TestExemplosOficiais(unittest.TestCase):
    @staticmethod
    def nomes_validos(source):
        # Os exemplos impressos no PDF usam sufixos numéricos em alguns nomes
        # de classe, embora a convenção do lexer proíba números em classes.
        # Preservamos a sintaxe do exemplo e trocamos somente esses nomes para
        # testar a semântica sem flexibilizar lexer/parser.
        replacements = {
            "ClassName1": "ClassOne", "ClassName2": "ClassTwo",
            "SubclassName1": "SubclassOne", "SubclassName2": "SubclassTwo",
            "Role_Name1": "Role_One", "Role_Name2": "Role_Two",
            "Phase_Name1": "Phase_One", "Phase_Name2": "Phase_Two",
            "Mode_Name1": "Mode_One",
        }
        for invalid, valid in replacements.items():
            source = source.replace(invalid, valid)
        return source

    def test_seis_odps_sintaticos_e_semanticos(self):
        root = os.path.join(os.path.dirname(__file__), "..", "..", "dataset-test",
                            "Ontology Design Patterns em Tonto")
        files = sorted(glob.glob(os.path.join(root, "*.tonto")))
        self.assertEqual(len(files), 6)
        for path in files:
            with self.subTest(file=os.path.basename(path)):
                with open(path, encoding="utf-8") as source:
                    ontology, errors = parse(self.nomes_validos(source.read()))
                self.assertEqual(errors, [])
                result = analyze(ontology)
                self.assertTrue(result.patterns)
                expected = os.path.basename(path).replace("_Pattern.tonto", "").lower()
                if expected == "rolemixin":
                    expected = "rolemixin"
                self.assertIn(expected, [p.pattern for p in result.patterns])

    def test_instancia_nao_e_aceita_como_nome_de_classe(self):
        ontology, errors = parse("package Names\nkind ClassName1\n")
        self.assertTrue(errors)
        self.assertFalse(any(c.get("name") == "ClassName1" for c in ontology["classes"]))

    def test_relatorio_json_e_texto_semantico(self):
        analysis = analisar_texto(HEADER + MODE_OK, "mode.tonto")
        self.assertIn("mode", [p["pattern"] for p in analysis["semantic"]["patterns"]])
        report = relatorio_semantico([analysis])
        self.assertIn("ANÁLISE SEMÂNTICA", report)
        data = para_json([analysis])
        self.assertIn('"semantic"', data)

    def test_relatorio_semantico_exibe_erros_de_parser(self):
        analysis = analisar_texto("package Demo\nkind ClassName1\n", "invalid.tonto")
        report = relatorio_semantico([analysis])
        self.assertIn("Erros léxicos/sintáticos", report)
        self.assertIn("Nenhum padrão ODP encontrado", report)


if __name__ == "__main__":
    unittest.main()
