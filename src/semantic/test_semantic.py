import json
import os
import unittest

import patterns  
from parser.parser import parse
from parser.symbol_table import build_symbol_table
from semantic.core import (
    STATUS_COMPLETO,
    STATUS_INCOMPLETO,
    STATUS_INVALIDO,
    SemanticContext,
    analyze,
)
from semantic.registry import registered_names

HEADER = "package Teste\n"


def analisar(body):
    ontology, errors = parse(HEADER + body)
    if errors:
        raise AssertionError(f"fixture com erro sintático: {errors}")
    return analyze(ontology)


def padroes(result, nome):
    return [p for p in result.patterns if p.pattern == nome]


def codigos(result):
    return [c.code for c in result.coercions]


# ----------------------------------------------------------------------
# Subkind
# ----------------------------------------------------------------------


class TestSubkind(unittest.TestCase):

    def test_subkind_completo(self):
        result = analisar(
            "kind Vehicle\n"
            "subkind Car specializes Vehicle\n"
            "subkind Truck specializes Vehicle\n"
            "disjoint complete genset VehicleSubkinds {\n"
            "    general Vehicle\n"
            "    specifics Car, Truck\n"
            "}\n"
        )

        encontrados = padroes(result, "subkind")
        self.assertEqual(len(encontrados), 1)
        padrao = encontrados[0]
        self.assertEqual(padrao.status, STATUS_COMPLETO)
        self.assertEqual(padrao.lines, [2, 3, 4])
        self.assertEqual(padrao.participants["general"], "Vehicle")
        self.assertEqual(padrao.participants["specifics"], ["Car", "Truck"])
        self.assertEqual(padrao.participants["genset"], "VehicleSubkinds")
        self.assertEqual(result.coercions, [])

    def test_subkind_sem_complete_tambem_e_completo(self):
        result = analisar(
            "kind Vehicle\n"
            "subkind Car specializes Vehicle\n"
            "subkind Truck specializes Vehicle\n"
            "disjoint genset VehicleSubkinds {\n"
            "    general Vehicle\n"
            "    specifics Car, Truck\n"
            "}\n"
        )

        self.assertEqual(result.coercions, [])
        self.assertEqual(padroes(result, "subkind")[0].status, STATUS_COMPLETO)

    def test_subkind_pai_nao_e_kind(self):
        result = analisar(
            "kind Vehicle\n"
            "collective Fleet\n"
            "subkind Car specializes Fleet\n"
        )

        self.assertIn("ODP_SUBKIND_PAI_NAO_E_KIND", codigos(result))
        coercao = next(c for c in result.coercions
                       if c.code == "ODP_SUBKIND_PAI_NAO_E_KIND")
        self.assertIn("kind", coercao.suggestion)
        self.assertEqual(padroes(result, "subkind")[0].status, STATUS_INVALIDO)

    def test_subkind_genset_general_nao_e_kind(self):
        result = analisar(
            "kind Vehicle\n"
            "collective Fleet\n"
            "subkind Car specializes Vehicle\n"
            "disjoint genset FleetSubkinds {\n"
            "    general Fleet\n"
            "    specifics Car\n"
            "}\n"
        )

        self.assertIn("ODP_SUBKIND_GENERAL_NAO_E_KIND", codigos(result))
        self.assertEqual(padroes(result, "subkind")[0].status, STATUS_INVALIDO)

    def test_subkind_sem_disjoint_gera_coercao(self):
        result = analisar(
            "kind Vehicle\n"
            "subkind Car specializes Vehicle\n"
            "subkind Truck specializes Vehicle\n"
            "complete genset VehicleSubkinds {\n"
            "    general Vehicle\n"
            "    specifics Car, Truck\n"
            "}\n"
        )

        self.assertIn("ODP_SUBKIND_DISJOINT", codigos(result))
        coercao = next(c for c in result.coercions if c.code == "ODP_SUBKIND_DISJOINT")
        self.assertEqual(coercao.line, 5)
        self.assertIn("disjoint", coercao.suggestion)
        self.assertEqual(padroes(result, "subkind")[0].status, STATUS_INVALIDO)

    def test_subkind_com_overlapping_gera_coercao(self):
        result = analisar(
            "kind Vehicle\n"
            "subkind Car specializes Vehicle\n"
            "subkind Truck specializes Vehicle\n"
            "disjoint overlapping genset VehicleSubkinds {\n"
            "    general Vehicle\n"
            "    specifics Car, Truck\n"
            "}\n"
        )

        self.assertIn("ODP_SUBKIND_OVERLAPPING", codigos(result))
        self.assertEqual(padroes(result, "subkind")[0].status, STATUS_INVALIDO)

    def test_subkind_sem_genset_fica_incompleto(self):
        result = analisar(
            "kind Vehicle\n"
            "subkind Car specializes Vehicle\n"
            "subkind Truck specializes Vehicle\n"
        )

        encontrados = padroes(result, "subkind")
        self.assertEqual(len(encontrados), 1)
        padrao = encontrados[0]
        self.assertEqual(padrao.status, STATUS_INCOMPLETO)
        self.assertIsNone(padrao.participants["genset"])
        self.assertEqual(padrao.participants["specifics"], ["Car", "Truck"])
        self.assertEqual(result.coercions, [])

    def test_subkind_sem_pai_gera_coercao(self):
        result = analisar("subkind Orphan\n")

        self.assertIn("ODP_SUBKIND_SEM_PAI", codigos(result))
        encontrados = padroes(result, "subkind")
        self.assertEqual(len(encontrados), 1)
        self.assertEqual(encontrados[0].status, STATUS_INVALIDO)
        self.assertIsNone(encontrados[0].participants["general"])
        self.assertEqual(encontrados[0].lines, [2])

    def test_subkind_com_pai_desconhecido(self):
        result = analisar("subkind Car specializes Ghost\n")

        self.assertIn("ODP_SUBKIND_PAI_DESCONHECIDO", codigos(result))
        encontrados = padroes(result, "subkind")
        self.assertEqual(encontrados[0].participants["general"], "Ghost")

    def test_genset_com_membro_que_nao_e_subkind(self):
        result = analisar(
            "kind Vehicle\n"
            "subkind Car specializes Vehicle\n"
            "role Driver specializes Vehicle\n"
            "disjoint genset VehicleGroup {\n"
            "    general Vehicle\n"
            "    specifics Car, Driver\n"
            "}\n"
        )

        self.assertIn("ODP_SUBKIND_GENSET_MEMBRO", codigos(result))
        self.assertEqual(padroes(result, "subkind")[0].status, STATUS_INVALIDO)

    def test_complete_e_incomplete_juntos(self):
        result = analisar(
            "kind Vehicle\n"
            "subkind Car specializes Vehicle\n"
            "subkind Truck specializes Vehicle\n"
            "disjoint complete incomplete genset VehicleSubkinds {\n"
            "    general Vehicle\n"
            "    specifics Car, Truck\n"
            "}\n"
        )

        self.assertIn("ODP_SUBKIND_COMPLETUDE_CONFLITANTE", codigos(result))


# ----------------------------------------------------------------------
# Role
# ----------------------------------------------------------------------


class TestRole(unittest.TestCase):

    def test_role_completo(self):
        result = analisar(
            "kind Person\n"
            "role Student specializes Person\n"
            "role Teacher specializes Person\n"
            "complete genset PersonRoles {\n"
            "    general Person\n"
            "    specifics Student, Teacher\n"
            "}\n"
        )

        encontrados = padroes(result, "role")
        self.assertEqual(len(encontrados), 1)
        padrao = encontrados[0]
        self.assertEqual(padrao.status, STATUS_COMPLETO)
        self.assertEqual(padrao.lines, [2, 3, 4])
        self.assertEqual(padrao.participants["general"], "Person")
        self.assertEqual(padrao.participants["specifics"], ["Student", "Teacher"])
        self.assertEqual(result.coercions, [])

    def test_role_com_disjoint_gera_coercao(self):
        result = analisar(
            "kind Person\n"
            "role Student specializes Person\n"
            "role Teacher specializes Person\n"
            "disjoint complete genset PersonRoles {\n"
            "    general Person\n"
            "    specifics Student, Teacher\n"
            "}\n"
        )

        self.assertIn("ODP_ROLE_DISJOINT", codigos(result))
        coercao = next(c for c in result.coercions if c.code == "ODP_ROLE_DISJOINT")
        self.assertEqual(coercao.line, 5)
        self.assertIn("Remova", coercao.suggestion)
        self.assertEqual(padroes(result, "role")[0].status, STATUS_INVALIDO)

    def test_role_com_overlapping_e_permitido(self):
        result = analisar(
            "kind Person\n"
            "role Student specializes Person\n"
            "role Teacher specializes Person\n"
            "overlapping genset PersonRoles {\n"
            "    general Person\n"
            "    specifics Student, Teacher\n"
            "}\n"
        )

        self.assertEqual(result.coercions, [])
        self.assertEqual(padroes(result, "role")[0].status, STATUS_COMPLETO)

    def test_role_pai_nao_e_kind(self):
        result = analisar(
            "kind Person\n"
            "roleMixin Customer\n"
            "role Buyer specializes Customer\n"
        )

        self.assertIn("ODP_ROLE_PAI_NAO_E_KIND", codigos(result))
        self.assertEqual(padroes(result, "role")[0].status, STATUS_INVALIDO)

    def test_role_genset_general_nao_e_kind(self):
        result = analisar(
            "kind Person\n"
            "collective Group\n"
            "role Student specializes Person\n"
            "role Teacher specializes Person\n"
            "complete genset PersonRoles {\n"
            "    general Group\n"
            "    specifics Student, Teacher\n"
            "}\n"
        )

        self.assertIn("ODP_ROLE_GENERAL_NAO_E_KIND", codigos(result))
        self.assertEqual(padroes(result, "role")[0].status, STATUS_INVALIDO)

    def test_role_mediado_por_relator_com_genset_proprio_nao_e_ocultado(self):
        result = analisar(
            "kind Person\n"
            "role Student specializes Person\n"
            "role Teacher specializes Person\n"
            "relator Enrollment {\n"
            "    @mediation [1..*] -- [1..*] Student\n"
            "    @mediation [1..*] -- [1..*] Teacher\n"
            "}\n"
            "complete genset PersonRoles {\n"
            "    general Person\n"
            "    specifics Student, Teacher\n"
            "}\n"
        )

        encontrados = padroes(result, "role")
        self.assertEqual(len(encontrados), 1)
        self.assertEqual(encontrados[0].status, STATUS_COMPLETO)
        self.assertEqual(encontrados[0].participants["genset"], "PersonRoles")
        # O detector de Relator pode reportar o @material ausente; aqui
        # interessa apenas que o Role não seja ocultado nem acusado.
        self.assertEqual(
            [c for c in result.coercions if c.code.startswith("ODP_ROLE")], [])

    def test_role_mediado_por_relator_sem_genset_pertence_ao_relator(self):
        result = analisar(
            "kind Person\n"
            "role Student specializes Person\n"
            "relator Enrollment {\n"
            "    @mediation [1..*] -- [1..*] Student\n"
            "}\n"
        )

        self.assertEqual(padroes(result, "role"), [])
        self.assertEqual(
            [c for c in result.coercions if c.code.startswith("ODP_ROLE")], [])

    def test_role_mediado_por_relator_externo_sem_genset_pertence_ao_relator(self):
        result = analisar(
            "kind Person\n"
            "role Student specializes Person\n"
            "relator Enrollment\n"
            "@mediation relation Enrollment [1..*] -- [1..*] Student\n"
        )

        self.assertEqual(padroes(result, "role"), [])
        self.assertEqual(
            [c for c in result.coercions if c.code.startswith("ODP_ROLE")], [])

    def test_role_mediado_por_relator_externo_com_genset_proprio_nao_e_ocultado(self):
        result = analisar(
            "kind Person\n"
            "role Student specializes Person\n"
            "role Teacher specializes Person\n"
            "relator Enrollment\n"
            "@mediation relation Enrollment [1..*] -- [1..*] Student\n"
            "@mediation relation Enrollment [1..*] -- [1..*] Teacher\n"
            "complete genset PersonRoles {\n"
            "    general Person\n"
            "    specifics Student, Teacher\n"
            "}\n"
        )

        encontrados = padroes(result, "role")
        self.assertEqual(len(encontrados), 1)
        self.assertEqual(encontrados[0].status, STATUS_COMPLETO)
        self.assertEqual(encontrados[0].participants["genset"], "PersonRoles")
        self.assertEqual(
            [c for c in result.coercions if c.code.startswith("ODP_ROLE")], [])

    def test_role_de_rolemixin_com_genset_proprio_nao_e_ocultado(self):
        result = analisar(
            "kind Person\n"
            "roleMixin Customer\n"
            "role Buyer specializes Person\n"
            "role Seller specializes Person\n"
            "disjoint complete genset Customers {\n"
            "    general Customer\n"
            "    specifics Buyer, Seller\n"
            "}\n"
            "complete genset PersonRoles {\n"
            "    general Person\n"
            "    specifics Buyer, Seller\n"
            "}\n"
        )

        encontrados = padroes(result, "role")
        self.assertEqual(len(encontrados), 1)
        self.assertEqual(encontrados[0].status, STATUS_COMPLETO)
        self.assertEqual(encontrados[0].participants["genset"], "PersonRoles")
        self.assertNotIn("ODP_ROLE_DISJOINT", codigos(result))

    def test_role_sem_genset_fica_incompleto(self):
        result = analisar(
            "kind Person\n"
            "role Student specializes Person\n"
            "role Teacher specializes Person\n"
        )

        encontrados = padroes(result, "role")
        self.assertEqual(len(encontrados), 1)
        self.assertEqual(encontrados[0].status, STATUS_INCOMPLETO)
        self.assertIsNone(encontrados[0].participants["genset"])

    def test_role_sem_pai_gera_coercao(self):
        result = analisar("role Orphan\n")

        self.assertIn("ODP_ROLE_SEM_PAI", codigos(result))
        encontrados = padroes(result, "role")
        self.assertEqual(len(encontrados), 1)
        self.assertEqual(encontrados[0].status, STATUS_INVALIDO)
        self.assertIsNone(encontrados[0].participants["general"])

    def test_genset_de_rolemixin_nao_e_do_role(self):
        result = analisar(
            "kind Person\n"
            "kind Organization\n"
            "roleMixin Customer\n"
            "role Buyer specializes Person\n"
            "role Seller specializes Organization\n"
            "disjoint complete genset Customers {\n"
            "    general Customer\n"
            "    specifics Buyer, Seller\n"
            "}\n"
        )

        self.assertEqual(padroes(result, "role"), [])
        self.assertEqual(result.coercions, [])

    def test_genset_com_membro_que_nao_e_role(self):
        result = analisar(
            "kind Person\n"
            "role Student specializes Person\n"
            "subkind Car specializes Person\n"
            "complete genset PersonGroup {\n"
            "    general Person\n"
            "    specifics Student, Car\n"
            "}\n"
        )

        self.assertIn("ODP_ROLE_GENSET_MEMBRO", codigos(result))
        self.assertEqual(padroes(result, "role")[0].status, STATUS_INVALIDO)


# ----------------------------------------------------------------------
# Contexto, integração e serialização
# ----------------------------------------------------------------------


class TestContexto(unittest.TestCase):

    def test_consultas_basicas(self):
        ontology, errors = parse(
            HEADER
            + "kind Vehicle\n"
            + "subkind Car specializes Vehicle\n"
            + "disjoint genset G {\n"
            + "    general Vehicle\n"
            + "    specifics Car\n"
            + "}\n"
        )
        self.assertEqual(errors, [])
        ctx = SemanticContext(ontology)

        self.assertTrue(ctx.is_class("Vehicle"))
        self.assertEqual(ctx.stereotype_of("Car"), "subkind")
        self.assertEqual(ctx.parents_of("Car"), ["Vehicle"])
        self.assertEqual(ctx.line_of("Car"), 3)
        self.assertEqual(ctx.kind_of("G"), "genset")
        self.assertTrue(ctx.has_modifier(ontology["gensets"][0], "disjoint"))

    def test_dominant_stereotype_resolve_empate_pelo_primeiro(self):
        ontology, _ = parse(
            HEADER
            + "kind Vehicle\n"
            + "role Driver specializes Vehicle\n"
            + "subkind Car specializes Vehicle\n"
            + "disjoint genset G {\n"
            + "    general Vehicle\n"
            + "    specifics Driver, Car\n"
            + "}\n"
        )
        ctx = SemanticContext(ontology)
        self.assertEqual(ctx.dominant_stereotype(ontology["gensets"][0]), "role")


class TestIntegracao(unittest.TestCase):

    def test_analyze_aceita_symbol_table(self):
        ontology, errors = parse(
            HEADER
            + "kind Vehicle\n"
            + "subkind Car specializes Vehicle\n"
            + "subkind Truck specializes Vehicle\n"
            + "disjoint genset G {\n"
            + "    general Vehicle\n"
            + "    specifics Car, Truck\n"
            + "}\n"
        )
        self.assertEqual(errors, [])

        sem_tabela = analyze(ontology).to_dict()
        com_tabela = analyze(ontology, build_symbol_table(ontology)).to_dict()
        self.assertEqual(sem_tabela, com_tabela)

    def test_ontology_vazia(self):
        self.assertEqual(
            analyze(None).to_dict(),
            {"patterns": [], "coercions": [], "inferences": []},
        )

    def test_parser_example(self):
        caminho = os.path.join(
            os.path.dirname(__file__), "..", "..",
            "dataset-test", "ParserExample", "src", "parser.tonto",
        )
        with open(caminho, encoding="utf-8") as arquivo:
            ontology, errors = parse(arquivo.read())
        self.assertEqual(errors, [])

        result = analyze(ontology)

        subkinds = padroes(result, "subkind")
        self.assertEqual(len(subkinds), 2)
        staff = next(p for p in subkinds if p.participants["genset"] == "StaffLevel")
        self.assertEqual(staff.status, STATUS_INVALIDO)
        self.assertEqual(staff.participants["specifics"], ["SeniorStaff", "JuniorStaff"])
        classroom = next(p for p in subkinds if p.participants["genset"] is None)
        self.assertEqual(classroom.participants["specifics"], ["Classroom"])
        self.assertEqual(classroom.status, STATUS_INCOMPLETO)

        roles = padroes(result, "role")
        self.assertEqual(len(roles), 3)
        student_status = next(
            p for p in roles if p.participants["genset"] == "StudentStatus")
        self.assertEqual(student_status.status, STATUS_INVALIDO)
        self.assertEqual(
            sum(1 for p in roles if p.status == STATUS_COMPLETO), 0)
        self.assertEqual(
            sum(1 for p in roles if p.status == STATUS_INCOMPLETO), 0)
        self.assertEqual(
            sum(1 for p in roles if p.status == STATUS_INVALIDO), 3)

        # Employee e UniversityStudent são mediados por relators neste
        # exemplo; pertencem ao padrão Relator e não viram Role isolado.
        specifics = {n for p in roles for n in p.participants["specifics"]}
        self.assertNotIn("Employee", specifics)
        self.assertNotIn("UniversityStudent", specifics)

        # Staff é collective e UniversityStudent é role: nenhum dos dois é kind.
        self.assertIn("ODP_SUBKIND_PAI_NAO_E_KIND", codigos(result))
        self.assertIn("ODP_SUBKIND_GENERAL_NAO_E_KIND", codigos(result))
        self.assertIn("ODP_ROLE_PAI_NAO_E_KIND", codigos(result))
        self.assertIn("ODP_ROLE_GENERAL_NAO_E_KIND", codigos(result))

    def test_ordem_dos_detectores(self):
        self.assertEqual(registered_names()[:2], ["subkind", "role"])


class TestSerializacao(unittest.TestCase):

    def test_to_dict_tem_as_tres_chaves(self):
        result = analisar(
            "kind Vehicle\n"
            "subkind Car specializes Vehicle\n"
            "subkind Truck specializes Vehicle\n"
            "complete genset VehicleSubkinds {\n"
            "    general Vehicle\n"
            "    specifics Car, Truck\n"
            "}\n"
        )
        data = result.to_dict()

        self.assertEqual(set(data), {"patterns", "coercions", "inferences"})
        self.assertEqual(data["patterns"][0]["pattern"], "subkind")
        self.assertEqual(
            set(data["coercions"][0]),
            {"line", "code", "message", "suggestion"},
        )
        json.dumps(data, ensure_ascii=False)  


if __name__ == "__main__":
    unittest.main()
