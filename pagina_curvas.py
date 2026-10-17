"""Área de comparação histórica, independente da simulação de títulos."""
import logging
import numpy as np
import plotly.graph_objects as go
import streamlit as st

from curvas_historicas import consultar_historico, datas_completas, calcular_curvas, limite_publicado, TIPOS


@st.cache_data(ttl=900, show_spinner=False)
def carregar_historico():
    return consultar_historico()


def exibir_curvas():
    st.title('📈 Curvas de juros da ANBIMA')
    st.write('Estrutura a Termo das Taxas de Juros (ETTJ) da ANBIMA. Compare como as curvas mudaram ao longo do tempo, sem escolher um título.')
    try:
        with st.spinner('Carregando o histórico da ANBIMA...'):
            historico = carregar_historico()
        datas = datas_completas(historico)
    except Exception:
        logging.getLogger(__name__).exception('Falha ao consultar o histórico ANBIMA')
        st.error('Não foi possível carregar o histórico. Tente novamente em alguns instantes.')
        if st.button('Tentar novamente'):
            carregar_historico.clear()
            st.rerun()
        return
    if len(datas) < 2:
        st.info('O histórico está sendo formado. A comparação estará disponível quando houver pelo menos duas datas completas.')
        return
    st.caption(f'Histórico disponível: {datas[-1]:%d/%m/%Y} a {datas[0]:%d/%m/%Y} · Fonte: ANBIMA')
    with st.container(border=True):
        selecionadas = st.multiselect('Datas para comparar (até 3)', datas,
            default=[datas[1], datas[0]], max_selections=3,
            format_func=lambda d: d.strftime('%d/%m/%Y'), key='datas_curvas')
        tipo = st.radio('Curva', TIPOS, horizontal=True, key='tipo_curva')
        anos = st.radio('Prazo máximo no gráfico', [5, 10, 20, 30], index=1,
                        format_func=lambda n: f'{n} anos', horizontal=True, key='horizonte_curva')
    if len(selecionadas) < 2:
        st.info('Selecione pelo menos duas datas para comparar as curvas.')
        return
    limites = {d: limite_publicado(historico[historico['data_referencia'] == d].set_index('indexador'), tipo)
               for d in selecionadas}
    vertices = np.unique(np.concatenate([np.arange(21, anos * 252 + 1, 21),
        [v for v in limites.values() if np.isfinite(v) and 21 <= v <= anos * 252]]))
    curvas = calcular_curvas(historico, selecionadas, tipo, vertices)
    fig = criar_grafico(curvas)
    st.plotly_chart(fig, use_container_width=True)
    st.caption('Prazos constantes em dias úteis, considerando 252 dias úteis por ano. Curvas estimadas pelo modelo Svensson.')
    st.caption('Linha contínua: modelo até o último prazo publicado pela ANBIMA. Linha tracejada: extrapolação além desse prazo. Os limites variam por curva e data.')
    if any(not np.isfinite(v) for v in limites.values()):
        st.warning('O limite publicado de uma das datas não está disponível. Sua curva aparece pontilhada, sem confirmação do intervalo publicado.')
    st.subheader('O que mudou por prazo')
    pontos = calcular_curvas(historico, selecionadas, tipo, np.array([n * 252 for n in [1, 2, 5, 10, 20, 30] if n <= anos]))
    tabela = pontos.pivot(index='Prazo (anos)', columns='Data', values='Taxa (% a.a.)')
    ordenadas = [d.strftime('%d/%m/%Y') for d in sorted(selecionadas)]
    tabela = tabela[ordenadas]
    tabela['Variação (p.b.)'] = (tabela[ordenadas[-1]] - tabela[ordenadas[0]]) * 100
    incertos = pontos[pontos['Trecho'] != 'Intervalo publicado']['Prazo (anos)'].unique()
    tabela.index = [f"{int(n)} {'ano' if n == 1 else 'anos'}" + (' *' if n in incertos else '') for n in tabela.index]
    tabela.index.name = 'Prazo'
    st.dataframe(tabela.style.format({**{d: '{:.2f}%' for d in ordenadas}, 'Variação (p.b.)': '{:+.1f}'}), use_container_width=True)
    st.caption('* Prazo além do último vértice publicado, ou com limite não disponível, em pelo menos uma das datas. Consulte a classificação de cada ponto no CSV.')
    st.caption(f'Variação entre {ordenadas[0]} e {ordenadas[-1]}. Positivo: taxa subiu; negativo: caiu. 100 pontos-base (p.b.) equivalem a 1 ponto percentual.')
    st.download_button('Baixar comparação em CSV', curvas.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig'),
                       file_name='comparacao_curvas_anbima.csv', mime='text/csv')
    st.info('As curvas refletem as condições de mercado de cada data. A inflação implícita pode ser diferente da inflação futura. Esta comparação é informativa e não representa recomendação de investimento nem garantia de rentabilidade.')


def criar_grafico(curvas):
    fig = go.Figure()
    for (data, grupo), cor in zip(curvas.groupby('Data', sort=False), ['#2563eb', '#e67e22', '#169b83']):
        publicado = grupo[grupo['Trecho'] == 'Intervalo publicado']
        extrapolado = grupo[grupo['Trecho'] == 'Extrapolação']
        desconhecido = grupo[grupo['Trecho'] == 'Limite não disponível']
        primeiro = True
        for pontos, estilo, nome in [(publicado, 'solid', 'Intervalo publicado'),
                                     (extrapolado, 'dash', 'Extrapolação'),
                                     (desconhecido, 'dot', 'Limite não disponível')]:
            if pontos.empty:
                continue
            # Repete apenas o ponto de junção para não deixar lacuna na linha.
            if estilo == 'dash' and not publicado.empty:
                import pandas as pd
                pontos = pd.concat([publicado.tail(1), pontos])
            fig.add_trace(go.Scatter(x=pontos['Prazo (anos)'], y=pontos['Taxa (% a.a.)'],
                mode='lines', name=data, legendgroup=data, showlegend=primeiro,
                line=dict(color=cor, width=3, dash=estilo),
                hovertemplate=f'%{{x:.2f}} anos<br>%{{y:.2f}}% a.a.<br>{nome}<extra>{data}</extra>'))
            primeiro = False
    fig.update_layout(hovermode='x unified', legend_title_text='Data de referência', height=440,
                      xaxis_title='Prazo (anos)', yaxis_title='Taxa (% a.a.)')
    return fig
