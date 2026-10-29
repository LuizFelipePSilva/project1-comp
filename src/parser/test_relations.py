"""
comando de teste:
    python -m unittest parser.test_relations -v
"""
import unittest

from parser.parser import parse

HEADER = "package Teste\n"


def parse_ok(testcase, body):
    """Faz o parse e garante que não houve erro sintático."""
    result, errors = parse(HEADER + body)
    testcase.assertEqual(errors, [], f"erros inesperados: {errors}")
    return result


def declarations_of(result, kind):
    return [d for d in result["declarations"] if d["kind"] == kind]


class TestRelacaoInterna(unittest.TestCase):

    def test_nomeada_com_cardinalidade_so_no_destino(self):
        # forma do car.tonto: @mediation / -- nome -- [1] Classe
        r = parse_ok(self, "relator Contrato {\n  @mediation\n  -- involvesOwner -- [1] Agency\n}\n")
        rel = r["classes"][0]["attributes"][0]
        self.assertEqual(rel["kind"], "relation")
        self.assertTrue(rel["internal"])
        self.assertEqual(rel["stereotype"], "mediation")
        self.assertEqual(rel["name"], "involvesOwner")
        self.assertEqual(rel["operator"], "--")
        self.assertIsNone(rel["source_cardinality"])
        self.assertEqual(rel["target_cardinality"], {"min": 1, "max": 1})
        self.assertEqual(rel["target"], "Agency")

    def test_anonima_com_duas_cardinalidades(self):
        r = parse_ok(self, "relator R {\n  @mediation [1..*] -- [1] Paciente\n}\n")
        rel = r["classes"][0]["attributes"][0]
        self.assertIsNone(rel["name"])
        self.assertEqual(rel["source_cardinality"], {"min": 1, "max": None})
        self.assertEqual(rel["target_cardinality"], {"min": 1, "max": 1})

    def test_composicao(self):
        r = parse_ok(self, "kind Item {\n  @memberOf [0..*] <>-- [1..*] Outro\n}\n")
        rel = r["classes"][0]["attributes"][0]
        self.assertEqual(rel["operator"], "<>--")
        self.assertEqual(rel["stereotype"], "memberOf")

    def test_agregacao(self):
        r = parse_ok(self, "kind A {\n  @componentOf [1] --<> [1..*] B\n}\n")
        self.assertEqual(r["classes"][0]["attributes"][0]["operator"], "--<>")

    def test_atributo_e_relacao_na_mesma_classe(self):
        r = parse_ok(self, "kind A {\n  nome: string [1]\n  @componentOf [1] <>-- [1..*] B\n}\n")
        kinds = [m["kind"] for m in r["classes"][0]["attributes"]]
        self.assertEqual(kinds, ["attribute", "relation"])

    def test_duas_relacoes_seguidas(self):
        r = parse_ok(self, "relator R {\n @mediation\n -- a -- [1] X\n @mediation\n -- b -- [1] Y\n}\n")
        self.assertEqual(len(r["classes"][0]["attributes"]), 2)

    def test_sem_espaco_antes_da_cardinalidade(self):
        # carRental.tonto tem "-- involvesCustomer --[1] Customer"
        r = parse_ok(self, "relator R {\n @mediation\n -- involvesCustomer --[1] Customer\n}\n")
        self.assertEqual(r["classes"][0]["attributes"][0]["target"], "Customer")


class TestRelacaoInternaSemEstereotipo(unittest.TestCase):

    def test_segunda_relacao_sem_arroba_como_no_carrental(self):
        body = ("relator CarRental {\n"
                "  @mediation\n  -- involvesRental -- [1] RentalCar\n\n"
                "  -- involvesMediator -- [1] ResponsibleEmployee\n"
                "}\n")
        r = parse_ok(self, body)
        rels = r["classes"][0]["attributes"]
        self.assertEqual(len(rels), 2)
        self.assertEqual(rels[1]["name"], "involvesMediator")
        self.assertIsNone(rels[1]["stereotype"])
        self.assertEqual(rels[1]["line"], 6)

    def test_sem_arroba_com_composicao(self):
        r = parse_ok(self, "kind A {\n  <>-- [1..*] B\n}\n")
        rel = r["classes"][0]["attributes"][0]
        self.assertEqual(rel["operator"], "<>--")
        self.assertIsNone(rel["name"])

    def test_atributo_seguido_de_relacao_sem_arroba(self):
        r = parse_ok(self, "kind A {\n  nome: string [1]\n  -- tem -- [1] B\n}\n")
        self.assertEqual([m["kind"] for m in r["classes"][0]["attributes"]], ["attribute", "relation"])


class TestRelacaoExterna(unittest.TestCase):

    def test_material_nomeada(self):
        r = parse_ok(self, "@material relation Pizza [1..*] -- tem_Massa -- [1..*] Massa\n")
        rel = declarations_of(r, "relation")[0]
        self.assertFalse(rel["internal"])
        self.assertEqual(rel["stereotype"], "material")
        self.assertEqual(rel["source"], "Pizza")
        self.assertEqual(rel["name"], "tem_Massa")
        self.assertEqual(rel["target"], "Massa")

    def test_sem_estereotipo(self):
        r = parse_ok(self, "relation Pessoa [1] -- conhece -- [0..*] Pessoa\n")
        rel = declarations_of(r, "relation")[0]
        self.assertIsNone(rel["stereotype"])

    def test_duas_relacoes_externas_seguidas(self):
        body = ("@material relation A [1] -- liga -- [1] B\n"
                "@material relation B [1] -- contem -- [1] C\n")
        r = parse_ok(self, body)
        self.assertEqual(len(declarations_of(r, "relation")), 2)

    def test_relacao_depois_de_classe_sem_corpo(self):
        r = parse_ok(self, "kind A\nkind B\n@material relation A [1] -- r -- [1] B\n")
        self.assertEqual(len(r["classes"]), 2)
        self.assertEqual(len(declarations_of(r, "relation")), 1)


class TestGensetLongo(unittest.TestCase):

    def test_disjoint_complete(self):
        body = "disjoint complete genset Tipo {\n  general Item\n  specifics Pizza, Bebida, Petisco\n}\n"
        g = declarations_of(parse_ok(self, body), "genset")[0]
        self.assertEqual(g["form"], "long")
        self.assertEqual(g["name"], "Tipo")
        self.assertEqual(g["modifiers"], ["disjoint", "complete"])
        self.assertEqual(g["general"], "Item")
        self.assertEqual(g["specifics"], ["Pizza", "Bebida", "Petisco"])
        self.assertIsNone(g["categorizer"])

    def test_sem_modificadores(self):
        g = declarations_of(parse_ok(self, "genset G {\n general A\n specifics B\n}\n"), "genset")[0]
        self.assertEqual(g["modifiers"], [])

    def test_modificador_unico(self):
        g = declarations_of(parse_ok(self, "complete genset G {\n general A\n specifics B, C\n}\n"), "genset")[0]
        self.assertEqual(g["modifiers"], ["complete"])

    def test_overlapping_incomplete(self):
        g = declarations_of(parse_ok(self, "overlapping incomplete genset G {\n general A\n specifics B, C\n}\n"), "genset")[0]
        self.assertEqual(g["modifiers"], ["overlapping", "incomplete"])

    def test_categorizer(self):
        body = "disjoint genset G {\n general A\n categorizer Cat\n specifics B, C\n}\n"
        g = declarations_of(parse_ok(self, body), "genset")[0]
        self.assertEqual(g["categorizer"], "Cat")

    def test_nome_em_minusculo_como_no_dataset(self):
        # alergiaalimentar.tonto usa "genset disjoint_complete {"
        g = declarations_of(parse_ok(self, "genset disjoint_complete {\n general A\n specifics B, C\n}\n"), "genset")[0]
        self.assertEqual(g["name"], "disjoint_complete")


class TestGensetCurto(unittest.TestCase):

    def test_forma_curta(self):
        g = declarations_of(parse_ok(self, "disjoint complete genset G where A, B specializes P\n"), "genset")[0]
        self.assertEqual(g["form"], "short")
        self.assertEqual(g["specifics"], ["A", "B"])
        self.assertEqual(g["general"], "P")
        self.assertEqual(g["modifiers"], ["disjoint", "complete"])

    def test_forma_curta_sem_modificadores(self):
        g = declarations_of(parse_ok(self, "genset G where A specializes P\n"), "genset")[0]
        self.assertEqual(g["specifics"], ["A"])


class TestErros(unittest.TestCase):
    """Entradas inválidas: devem gerar erro sintático com linha, sem travar."""

    def assert_error(self, body, line=None):
        result, errors = parse(HEADER + body)
        self.assertTrue(errors, "deveria ter gerado erro sintático")
        if line is not None:
            self.assertEqual(errors[0]["line"], line)

    def test_genset_sem_general(self):
        self.assert_error("genset G {\n specifics A, B\n}\n", line=3)

    def test_genset_sem_specifics(self):
        self.assert_error("genset G {\n general A\n}\n", line=4)

    def test_genset_sem_nome(self):
        self.assert_error("genset {\n general A\n specifics B\n}\n", line=2)

    def test_genset_virgula_sobrando(self):
        self.assert_error("genset G {\n general A\n specifics B,\n}\n", line=5)

    def test_genset_curto_sem_specializes(self):
        self.assert_error("genset G where A, B\n")

    def test_relacao_sem_classe_destino(self):
        self.assert_error("@material relation A [1] -- r -- [1]\n")

    def test_relacao_sem_segundo_traco(self):
        self.assert_error("@material relation A [1] -- r [1] B\n")

    def test_relacao_externa_sem_origem(self):
        self.assert_error("relation [1] -- r -- [1] B\n", line=2)

    def test_relacao_interna_sem_arrow(self):
        self.assert_error("kind A {\n  @mediation [1] B\n}\n")

    def test_erro_nao_levanta_excecao(self):
        # o parser deve reportar e voltar normalmente, nunca estourar
        try:
            parse(HEADER + "genset G {\n general\n}\n")
        except Exception as exc:  # pragma: no cover
            self.fail(f"parse() levantou {exc!r}")


if __name__ == "__main__":
    unittest.main()