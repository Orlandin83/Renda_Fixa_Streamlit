import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import Mock, patch

from streamlit.testing.v1 import AppTest
from contador_simulacoes import atualizar_contador

APP = str(Path(__file__).resolve().parents[1] / 'streamlitrendafixa.py')
CSV = 'PREFIXADOS;0,12;0;0;0;1;1\nIPCA;0,06;0;0;0;1;1'


class SimuladorTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'SIMULACOES_DB_PATH': self.tmp.name + '/counter.db', 'SIMULACOES_DATABASE_URL': ''})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_concurrent_counter(self):
        self.assertEqual(atualizar_contador(), 0)
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(lambda _: atualizar_contador(True), range(40)))
        self.assertEqual(atualizar_contador(), 40)
        self.assertEqual(atualizar_contador(), 40)

    def test_ipca_and_sessions(self):
        with patch('requests.post', return_value=Mock(text=CSV)):
            app = AppTest.from_file(APP).run()
            app.selectbox(key='escolha_1_1').select('IPCA + Taxa Fixa').run()
            app.button[0].click().run()
            self.assertFalse(app.exception)
            metrics = {m.label: m.value for m in app.metric}
            self.assertEqual(metrics['Rendimento DI'], '12.00%')
            self.assertEqual(metrics['% do CDI projetado (bruto)'], '100.00%')
            app.number_input(key='taxa_1_ipca_1').set_value(8.0).run()
            self.assertEqual(atualizar_contador(), 1)
            app.button[0].click().run()
            metrics = {m.label: m.value for m in app.metric}
            expected = ((1.12 / 1.06 * 1.08 - 1) / .12) * 100
            self.assertEqual(metrics['% do CDI projetado (bruto)'], f'{expected:.2f}%')
            self.assertEqual(metrics['Rendimento DI'], '12.00%')
            other = AppTest.from_file(APP).run()
            other.radio(key='modo_analise').set_value('Comparar dois títulos').run()
            other.selectbox(key='escolha_2_2').select('IPCA + Taxa Fixa').run()
            other.button[0].click().run()
            self.assertFalse(other.exception)
            self.assertEqual(atualizar_contador(), 3)
            self.assertTrue(any(c.value == '3 simulações feitas desde 07/09/2026' for c in other.caption))

    def test_failure_does_not_count(self):
        with patch('requests.post', side_effect=RuntimeError('falha de teste')):
            app = AppTest.from_file(APP).run()
            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertTrue(app.error)
            self.assertEqual(atualizar_contador(), 0)

    def test_zero_reference(self):
        with patch('requests.post', return_value=Mock(text=CSV.replace('0,12', '0'))):
            app = AppTest.from_file(APP).run()
            app.selectbox(key='escolha_1_1').select('IPCA + Taxa Fixa').run()
            app.button[0].click().run()
            self.assertFalse(app.exception)
            metrics = {m.label: m.value for m in app.metric}
            self.assertEqual(metrics['% do CDI projetado (bruto)'], 'N/D')


if __name__ == '__main__':
    unittest.main()
