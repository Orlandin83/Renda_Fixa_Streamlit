from datetime import date
import unittest
from unittest.mock import patch, Mock
import numpy as np
import pandas as pd
from streamlit.testing.v1 import AppTest
from curvas_historicas import calcular_curvas, datas_completas, consultar_historico, curva_svensson, TIPOS
from pagina_curvas import carregar_historico, criar_grafico
from pathlib import Path

APP = str(Path(__file__).resolve().parents[1] / 'streamlitrendafixa.py')


def historico():
    return pd.DataFrame([
        dict(data_referencia=date(2026, 10, dia), indexador=tipo,
             ultimo_vertice_du=2520 if tipo == 'PREFIXADOS' else 8316,
             b1=taxa, b2=0., b3=0., b4=0., l1=1., l2=1.)
        for dia, pre in [(14, .12), (15, .13), (16, .14)]
        for tipo, taxa in [('PREFIXADOS', pre), ('IPCA', .06)]])


class CurvasTest(unittest.TestCase):
    def tearDown(self):
        carregar_historico.clear()

    def test_curva_e_inflacao(self):
        df = historico()
        resultado = calcular_curvas(df, [date(2026, 10, 14)], TIPOS[2], np.array([252, 2520]))
        np.testing.assert_allclose(resultado['Taxa (% a.a.)'], (1.12 / 1.06 - 1) * 100)
        taxas = curva_svensson(np.array([252]), .12, .02, -.01, .03, .8, .3)
        esperado = (.12 + .02 * (1-np.exp(-.8))/.8 - .01*((1-np.exp(-.8))/.8-np.exp(-.8)) + .03*((1-np.exp(-.3))/.3-np.exp(-.3))) * 100
        np.testing.assert_allclose(taxas, esperado)

    def test_limites_e_juncao(self):
        df = historico()
        data = date(2026, 10, 14)
        vertices = np.array([252, 2520, 5040, 7560])
        for tipo in [TIPOS[0], TIPOS[2]]:
            pontos = calcular_curvas(df, [data], tipo, vertices)
            self.assertEqual(list(pontos['Trecho']), ['Intervalo publicado'] * 2 + ['Extrapolação'] * 2)
            fig = criar_grafico(pontos)
            self.assertEqual([t.line.dash for t in fig.data], ['solid', 'dash'])
            self.assertEqual(fig.data[0].x[-1], fig.data[1].x[0])
            self.assertEqual(fig.data[1].x[-1], 30)
        pontos = calcular_curvas(df, [data], TIPOS[1], vertices)
        self.assertTrue((pontos['Trecho'] == 'Intervalo publicado').all())
        df['ultimo_vertice_du'] = None
        pontos = calcular_curvas(df, [data], TIPOS[0], vertices)
        self.assertEqual(criar_grafico(pontos).data[0].line.dash, 'dot')

    def test_datas_incompletas(self):
        self.assertNotIn(date(2026, 10, 16), datas_completas(historico().iloc[:-1]))

    def test_api_paginada(self):
        base = historico().iloc[0].to_dict()
        base['data_referencia'] = '2026-10-14'
        with patch('curvas_historicas.requests.get', side_effect=[Mock(json=lambda: [base]*500), Mock(json=lambda: [base])]) as get:
            self.assertEqual(len(consultar_historico()), 501)
            self.assertEqual(get.call_args.kwargs['params']['offset'], 500)

    def test_navegacao_comparacao_e_retorno(self):
        carregar_historico.clear()
        with patch('pagina_curvas.consultar_historico', return_value=historico()):
            app = AppTest.from_file(APP, default_timeout=20).run()
            app.session_state['pagina'] = 'Curvas de juros'
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.sidebar.selectbox), 0)
            self.assertEqual(len(app.get('plotly_chart')), 1)
            self.assertEqual(app.radio(key='horizonte_curva').value, 10)
            app.radio(key='horizonte_curva').set_value(30).run()
            self.assertFalse(app.exception)
            self.assertIn('30 anos *', app.dataframe[0].value.index)
            tabela = app.dataframe[0].value
            np.testing.assert_allclose(tabela['Variação (p.b.)'], 100)
            app.multiselect(key='datas_curvas').set_value([date(2026,10,14),date(2026,10,15),date(2026,10,16)]).run()
            app.radio(key='tipo_curva').set_value(TIPOS[2]).run()
            self.assertFalse(app.exception)
            app.multiselect(key='datas_curvas').set_value([]).run()
            self.assertEqual(len(app.get('plotly_chart')), 0)
            app.session_state['pagina'] = 'Simulador de títulos'
            app.run()
            self.assertTrue(app.sidebar.selectbox)
            self.assertFalse(app.exception)

    def test_historico_vazio_e_falha(self):
        for retorno in [historico().iloc[:0], RuntimeError('indisponível')]:
            carregar_historico.clear()
            kwargs = {'side_effect': retorno} if isinstance(retorno, Exception) else {'return_value': retorno}
            with patch('pagina_curvas.consultar_historico', **kwargs):
                app = AppTest.from_file(APP, default_timeout=20).run()
                app.session_state['pagina'] = 'Curvas de juros'
                app.run()
                self.assertFalse(app.exception)
                self.assertTrue(app.error if isinstance(retorno, Exception) else app.info)
