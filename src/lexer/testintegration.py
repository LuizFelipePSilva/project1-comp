"""
roda o lexer contra TODOS os exemplo e garante que ele não trava (nenhuma exceção
não tratada), mesmo em arquivos com erros léxicos esperados.
"""
import glob
import os
import unittest

from report import coletar_tokens

DATASET_DIR = os.path.join(os.path.dirname(__file__), '..', 'dataset-test')

def arquivos_tonto():
    return sorted(glob.glob(os.path.join(DATASET_DIR, '**', '*.tonto'), recursive=True))


class TestIntegracaoDataset(unittest.TestCase):

    def test_nenhum_arquivo_trava_o_lexer(self):
        arquivos = arquivos_tonto()
        self.assertTrue(len(arquivos) > 0, "nenhum arquivo .tonto encontrado no dataset-test")
        for caminho in arquivos:
            with self.subTest(arquivo=caminho):
                try:
                    coletar_tokens(caminho)
                except Exception as e:
                    self.fail(f"{caminho} quebrou o lexer: {e}")

    def test_arquivos_sem_erro_geram_tokens(self):
        limpos = ['CarExample/src/car.tonto', 'Pizzaria_Model/src/Empresa.tonto']
        for rel in limpos:
            caminho = os.path.join(DATASET_DIR, rel)
            tokens = coletar_tokens(caminho)
            self.assertGreater(len(tokens), 0, f"{rel} não gerou nenhum token")


if __name__ == '__main__':
    unittest.main()