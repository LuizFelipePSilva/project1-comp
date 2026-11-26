import unittest

import patterns 
from parser.parser import parse
from semantic.coercion import FixableCoercion, corrigir_fonte, guarded
from semantic.core import (STATUS_COMPLETO, STATUS_INCOMPLETO, STATUS_INVALIDO,
                           Detection, analyze)

HEADER = "package Teste\n"


def analisar(body):
    onto, errors = parse(HEADER + body)
    assert not errors, errors
    return analyze(onto)


def padroes(result, nome):
    return [p for p in result.patterns if p.pattern == nome]


def codigos(result):
    return [c.code for c in result.coercions]


PHASE_OK = ("kind Person\n"
            "phase Child specializes Person\n"
            "phase Adult specializes Person\n"
            "disjoint complete genset PersonPhases {\n"
            "    general Person\n    specifics Child, Adult\n}\n")


class TestPhase(unittest.TestCase):

    def test_completo(self):
        r = analisar(PHASE_OK)
        p = padroes(r, "phase")
        self.assertEqual(len(p), 1)
        self.assertEqual(p[0].status, STATUS_COMPLETO)
        self.assertEqual(p[0].participants["specifics"], ["Child", "Adult"])
        self.assertEqual(codigos(r), [])

    def test_complete_opcional(self):
        r = analisar(PHASE_OK.replace("disjoint complete", "disjoint"))
        self.assertEqual(padroes(r, "phase")[0].status, STATUS_COMPLETO)

    def test_sem_disjoint(self):
        r = analisar(PHASE_OK.replace("disjoint complete", "complete"))
        self.assertEqual(padroes(r, "phase")[0].status, STATUS_INVALIDO)
        self.assertIn("ODP_PHASE_DISJOINT", codigos(r))

    def test_overlapping(self):
        r = analisar(PHASE_OK.replace("disjoint complete", "overlapping"))
        self.assertIn("ODP_PHASE_OVERLAPPING", codigos(r))
        self.assertNotIn("ODP_PHASE_DISJOINT", codigos(r))

    def test_sem_genset_incompleto(self):
        r = analisar("kind P\nphase A specializes P\nphase B specializes P\n")
        self.assertEqual(padroes(r, "phase")[0].status, STATUS_INCOMPLETO)
        self.assertIn("ODP_PHASE_SEM_GENSET", codigos(r))

    def test_phase_sem_irma(self):
        r = analisar("kind P\nphase A specializes P\n")
        self.assertEqual(padroes(r, "phase")[0].status, STATUS_INVALIDO)
        self.assertIn("ODP_PHASE_SEM_IRMA", codigos(r))

    def test_genset_com_uma_phase(self):
        r = analisar("kind P\nphase A specializes P\n"
                     "disjoint genset G {\n general P\n specifics A\n}\n")
        self.assertIn("ODP_PHASE_SEM_IRMA", codigos(r))

    def test_pai_nao_kind(self):
        r = analisar("role R specializes X\nphase A specializes R\nphase B specializes R\n"
                     "kind X\n")
        # A phase precisa especializar um kind diretamente; herança indireta não basta.
        self.assertIn("ODP_PHASE_PAI_NAO_KIND", codigos(r))
        r = analisar("relator Q\nphase A specializes Q\nphase B specializes Q\n")
        self.assertIn("ODP_PHASE_PAI_NAO_KIND", codigos(r))

    def test_kind_deve_ser_pai_direto(self):
        r = analisar("kind K\nrole R specializes K\n"
                     "phase A specializes R\nphase B specializes R\n")
        self.assertIn("ODP_PHASE_PAI_NAO_KIND", codigos(r))
        self.assertNotIn("ODP_PHASE_SEM_GENSET", codigos(r))

    def test_sem_pai_e_pai_desconhecido(self):
        r = analisar("phase A\nphase B specializes Nada\n")
        self.assertIn("ODP_PHASE_SEM_PAI", codigos(r))
        self.assertIn("ODP_PHASE_PAI_DESCONHECIDO", codigos(r))

    def test_membro_que_nao_e_phase(self):
        r = analisar("kind P\nphase A specializes P\nphase B specializes P\nsubkind S specializes P\n"
                     "disjoint genset G {\n general P\n specifics A, B, S\n}\n")
        self.assertIn("ODP_PHASE_GENSET_MEMBRO", codigos(r))


RELATOR_OK = ("kind KindA\nkind KindB\n"
              "role RoleA specializes KindA\nrole RoleB specializes KindB\n"
              "relator Rel {\n"
              "    @mediation [1..*] -- [1..*] RoleA\n"
              "    @mediation [1..*] -- [1..*] RoleB\n}\n"
              "@material relation RoleA [1..*] -- rn -- [1..*] RoleB\n")


class TestRelator(unittest.TestCase):

    def test_completo(self):
        r = analisar(RELATOR_OK)
        p = padroes(r, "relator")[0]
        self.assertEqual(p.status, STATUS_COMPLETO)
        self.assertEqual(p.participants["mediations"], ["RoleA", "RoleB"])
        self.assertEqual(p.participants["material"], "rn")
        self.assertEqual(codigos(r), [])

    def test_sem_material(self):
        r = analisar(RELATOR_OK.replace("@material relation RoleA [1..*] -- rn -- [1..*] RoleB\n", ""))
        self.assertEqual(padroes(r, "relator")[0].status, STATUS_INCOMPLETO)
        self.assertIn("ODP_RELATOR_SEM_MATERIAL", codigos(r))

    def test_uma_mediacao(self):
        r = analisar("kind C\nrole RoleA specializes C\nrelator Rel {\n"
                     "    @mediation [1..*] -- [1..*] RoleA\n}\n")
        self.assertEqual(padroes(r, "relator")[0].status, STATUS_INVALIDO)
        self.assertIn("ODP_RELATOR_MEDIACOES", codigos(r))

    def test_duas_mediacoes_mesmo_alvo(self):
        r = analisar("kind C\nrole RoleA specializes C\nrelator Rel {\n"
                     "    @mediation [1..*] -- [1..*] RoleA\n"
                     "    @mediation [1..*] -- [1..*] RoleA\n}\n")
        self.assertIn("ODP_RELATOR_MEDIACOES", codigos(r))

    def test_alvo_desconhecido_e_nao_role(self):
        r = analisar("kind C\nrelator Rel {\n"
                     "    @mediation [1..*] -- [1..*] C\n"
                     "    @mediation [1..*] -- [1..*] Nada\n}\n")
        self.assertIn("ODP_RELATOR_ALVO_NAO_ROLE", codigos(r))
        self.assertIn("ODP_RELATOR_ALVO_DESCONHECIDO", codigos(r))

    def test_material_entre_outros_papeis_nao_vale(self):
        r = analisar("kind K\nrole RoleA specializes K\nrole RoleB specializes K\n"
                     "role RoleC specializes K\n"
                     "relator Rel {\n    @mediation [1..*] -- [1..*] RoleA\n"
                     "    @mediation [1..*] -- [1..*] RoleB\n}\n"
                     "@material relation RoleA [1..*] -- rn -- [1..*] RoleC\n")
        self.assertIn("ODP_RELATOR_SEM_MATERIAL", codigos(r))

    def test_alvos_invalidos_nao_contam_como_mediacoes_validas(self):
        r = analisar("kind K\nrole RoleA specializes K\n"
                     "relator Rel {\n"
                     "    @mediation [1..*] -- [1..*] RoleA\n"
                     "    @mediation [1..*] -- [1..*] Nada\n"
                     "    @mediation [1..*] -- [1..*] K\n"
                     "}\n"
                     "@material relation RoleA [1..*] -- rn -- [1..*] K\n")
        codes = codigos(r)
        self.assertIn("ODP_RELATOR_ALVO_DESCONHECIDO", codes)
        self.assertIn("ODP_RELATOR_ALVO_NAO_ROLE", codes)
        self.assertIn("ODP_RELATOR_MEDIACOES", codes)
        self.assertNotIn("ODP_RELATOR_SEM_MATERIAL", codes)

    def test_material_deve_ligar_dois_roles_mediados(self):
        r = analisar("kind K\nrole RoleA specializes K\n"
                     "role RoleB specializes K\nrole RoleC specializes K\n"
                     "relator Rel {\n"
                     "    @mediation [1..*] -- [1..*] RoleA\n"
                     "    @mediation [1..*] -- [1..*] RoleB\n"
                     "}\n"
                     "@material relation RoleA [1..*] -- rn -- [1..*] RoleC\n")
        self.assertIn("ODP_RELATOR_SEM_MATERIAL", codigos(r))

    def test_mediacao_externa(self):
        r = analisar("kind K\nrole RoleA specializes K\nrole RoleB specializes K\n"
                     "relator Rel\n"
                     "@mediation relation Rel [1..*] -- [1] RoleA\n"
                     "@mediation relation Rel [1..*] -- [1] RoleB\n"
                     "@material relation RoleA [1..*] -- rn -- [1..*] RoleB\n")
        self.assertEqual(padroes(r, "relator")[0].status, STATUS_COMPLETO)
        self.assertEqual(codigos(r), [])


class TestCoercao(unittest.TestCase):

    def test_corrige_phase_sem_disjoint(self):
        src = HEADER + PHASE_OK.replace("disjoint complete", "complete")
        onto, _ = parse(src)
        res = analyze(onto)
        novo, rel = corrigir_fonte(src, res.coercions)
        self.assertIn("disjoint complete genset", novo)
        onto2, errs = parse(novo)
        self.assertEqual(errs, [])
        self.assertEqual(analyze(onto2).coercions, [])
        self.assertTrue(all(x["aplicado"] for x in rel))

    def test_corrige_role_disjoint_do_gabriel(self):
        src = (HEADER + "kind P\nrole A specializes P\nrole B specializes P\n"
               "disjoint genset G {\n general P\n specifics A, B\n}\n")
        res = analyze(parse(src)[0])
        novo, _ = corrigir_fonte(src, res.coercions)
        self.assertNotIn("disjoint", novo)
        self.assertEqual(analyze(parse(novo)[0]).coercions, [])

    def test_corrige_relator_sem_material(self):
        src = HEADER + RELATOR_OK.replace("@material relation RoleA [1..*] -- rn -- [1..*] RoleB\n", "")
        res = analyze(parse(src)[0])
        novo, _ = corrigir_fonte(src, res.coercions)
        onto, errs = parse(novo)
        self.assertEqual(errs, [])
        self.assertEqual(analyze(onto).coercions, [])
        self.assertEqual(padroes(analyze(onto), "relator")[0].status, STATUS_COMPLETO)

    def test_corrige_phases_sem_genset(self):
        src = HEADER + "kind P\nphase A specializes P\nphase B specializes P\n"
        novo, _ = corrigir_fonte(src, analyze(parse(src)[0]).coercions)
        self.assertEqual(padroes(analyze(parse(novo)[0]), "phase")[0].status, STATUS_COMPLETO)

    def test_erro_nao_corrigivel_fica_sem_aplicar(self):
        src = HEADER + "kind P\nphase A specializes P\n"
        novo, rel = corrigir_fonte(src, analyze(parse(src)[0]).coercions)
        self.assertEqual(novo, src)
        self.assertFalse(rel[0]["aplicado"])

    def test_to_dict_marca_corrigivel(self):
        res = analyze(parse(HEADER + "kind P\nphase A specializes P\nphase B specializes P\n")[0])
        c = [c for c in res.coercions if c.code == "ODP_PHASE_SEM_GENSET"][0]
        self.assertIsInstance(c, FixableCoercion)
        self.assertTrue(c.to_dict()["corrigivel"])

    def test_falha_interna_nao_interrompe(self):
        class Quebrado:
            pattern = "x"

            @guarded
            def detect(self, ctx):
                raise ValueError("boom")

        d = Quebrado().detect(None)
        self.assertIsInstance(d, Detection)
        self.assertEqual(d.coercions[0].code, "ODP_ERRO_INTERNO")


if __name__ == "__main__":
    unittest.main()