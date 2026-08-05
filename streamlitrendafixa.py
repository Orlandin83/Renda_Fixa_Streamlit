import streamlit as st
import requests
import numpy as np
import pandas as pd
import plotly.express as px


# ==========================================
# CONFIGURAÇÃO DA PÁGINA STREAMLIT
# ==========================================
st.set_page_config(page_title="Simulador CDI Futuro", page_icon="📊", layout="centered")

st.title("📊 Simulador de CDI Futuro")
st.markdown("Cálculo baseado na Estrutura a Termo da Taxa de Juros (ETTJ) da Anbima")


# ==========================================
# FUNÇÕES AUXILIARES
# ==========================================
def obter_aliquota_ir(prazo_dias_corridos: int) -> float:
    if prazo_dias_corridos <= 180:
        return 0.225
    elif prazo_dias_corridos <= 360:
        return 0.20
    elif prazo_dias_corridos <= 720:
        return 0.175
    return 0.15


def dias_corridos_aproximados(prazo_dias_uteis: int) -> int:
    return int(round(prazo_dias_uteis * 365 / 252))


def calcular_vertice(df_curva: pd.DataFrame, prazo_selecionado: int):
    if prazo_selecionado in df_curva.index:
        di_aa = df_curva.loc[prazo_selecionado]
    else:
        di_aa = df_curva.loc[df_curva.index <= prazo_selecionado].iloc[-1]
    return int(di_aa.name), float(di_aa.values[0])


def calcular_titulo(taxa_di_anual, tipo_regime, taxa_input, prazo_selecionado, modalidade):
    taxa_di_dia = ((1 + taxa_di_anual / 100) ** (1 / 252) - 1)
    fator_di = (1 + taxa_di_dia) ** prazo_selecionado
    resultado_di = round(((fator_di - 1) * 100), 2)
    dias_corridos = dias_corridos_aproximados(prazo_selecionado)

    def fluxo_sem_ir(taxa_dia):
        fator_bruto_local = (1 + taxa_dia) ** prazo_selecionado
        taxa_ano_local = (((1 + taxa_dia) ** 252) - 1) * 100
        resultado_bruto_local = round(((fator_bruto_local - 1) * 100), 2)
        return fator_bruto_local, taxa_ano_local, resultado_bruto_local

    if modalidade == 1:
        percentual_cdi = taxa_input / 100 if taxa_input > 1 else taxa_input
        taxa_contratada_dia = ((1 + taxa_di_dia) ** percentual_cdi) - 1
        fator_bruto, taxa_contratada_ano, resultado_bruto = fluxo_sem_ir(taxa_contratada_dia)

    elif modalidade == 2:
        spread_dia = ((1 + taxa_input / 100) ** (1 / 252) - 1)
        taxa_contratada_dia = ((1 + taxa_di_dia) * (1 + spread_dia)) - 1
        fator_bruto, taxa_contratada_ano, resultado_bruto = fluxo_sem_ir(taxa_contratada_dia)

    else:
        taxa_contratada_dia = ((1 + taxa_input / 100) ** (1 / 252) - 1)
        fator_bruto, taxa_contratada_ano, resultado_bruto = fluxo_sem_ir(taxa_contratada_dia)

    if tipo_regime == "Isento":
        return {
            "tipo": "Isento",
            "taxa_anual_bruta": taxa_contratada_ano,
            "resultado_bruto": resultado_bruto,
            "resultado_liquido": resultado_bruto,
            "fator_bruto": fator_bruto,
            "fator_liquido": fator_bruto,
            "aliquota_ir": 0.0,
            "resultado_di": resultado_di,
            "taxa_plot": taxa_contratada_ano,
            "lucro_bruto": fator_bruto - 1,
            "lucro_liquido": fator_bruto - 1,
            "taxa_ano_liquida": taxa_contratada_ano,
            "dias_corridos": dias_corridos,
        }

    lucro_bruto = fator_bruto - 1
    aliquota_ir = obter_aliquota_ir(dias_corridos)
    lucro_liquido = lucro_bruto * (1 - aliquota_ir)
    fator_liquido = 1 + lucro_liquido
    resultado_liquido = round(lucro_liquido * 100, 2)
    taxa_liquida_ano = (((fator_liquido) ** (252 / prazo_selecionado)) - 1) * 100 if prazo_selecionado > 0 else 0.0

    return {
        "tipo": "Tributado",
        "taxa_anual_bruta": taxa_contratada_ano,
        "resultado_bruto": resultado_bruto,
        "resultado_liquido": resultado_liquido,
        "fator_bruto": fator_bruto,
        "fator_liquido": fator_liquido,
        "aliquota_ir": aliquota_ir,
        "resultado_di": resultado_di,
        "taxa_plot": taxa_contratada_ano,
        "lucro_bruto": lucro_bruto,
        "lucro_liquido": lucro_liquido,
        "taxa_ano_liquida": taxa_liquida_ano,
        "dias_corridos": dias_corridos,
    }


# ==========================================
# SIDEBAR / MENU LATERAL DE INPUTS
# ==========================================
with st.sidebar:
    st.header("Entrada de Dados")

    modo_analise = st.radio(
        "Tipo de análise:",
        options=["Um título", "Comparar dois títulos"],
        horizontal=False,
    )

    st.markdown("### Título 1")
    tipo_titulo_1 = st.selectbox(
        "Regime do título 1:",
        options=["Isento", "Tributado"],
        key="tipo_titulo_1",
    )

    escolha_1 = st.selectbox(
        "Selecione a Modalidade do título 1:",
        options=["% do CDI", "CDI + Taxa Fixa", "Taxa Pré-fixada"],
        key="escolha_1",
    )
    modalidade_1 = 1 if escolha_1 == "% do CDI" else 2 if escolha_1 == "CDI + Taxa Fixa" else 3

    prazo_1 = st.number_input(
        "Prazo do título 1 em dias úteis:", min_value=1, max_value=10000, value=252, step=1, format="%d", key="prazo_1"
    )
    taxa_1 = st.number_input(
        "Taxa negociada do título 1 (ex: 104, 1.5 ou 11):", min_value=0.0, value=104.0, step=0.1, key="taxa_1"
    )

    if modo_analise == "Comparar dois títulos":
        st.markdown("---")
        st.markdown("### Título 2")
        tipo_titulo_2 = st.selectbox(
            "Regime do título 2:",
            options=["Isento", "Tributado"],
            key="tipo_titulo_2",
        )

        escolha_2 = st.selectbox(
            "Selecione a Modalidade do título 2:",
            options=["% do CDI", "CDI + Taxa Fixa", "Taxa Pré-fixada"],
            key="escolha_2",
        )
        modalidade_2 = 1 if escolha_2 == "% do CDI" else 2 if escolha_2 == "CDI + Taxa Fixa" else 3

        prazo_2 = st.number_input(
            "Prazo do título 2 em dias úteis:", min_value=1, max_value=10000, value=252, step=1, format="%d", key="prazo_2"
        )
        taxa_2 = st.number_input(
            "Taxa negociada do título 2 (ex: 104, 1.5 ou 11):", min_value=0.0, value=104.0, step=0.1, key="taxa_2"
        )
    else:
        tipo_titulo_2 = None
        escolha_2 = None
        modalidade_2 = None
        prazo_2 = None
        taxa_2 = None

    st.markdown("---")
    st.caption("elaborado por: Fabricio Orlandin, CFP®")
    simular = st.button("Simular", type="primary", use_container_width=True)


# ==========================================
# LÓGICA MATEMÁTICA
# ==========================================
if simular:
    with st.spinner("Conectando à Anbima e extraindo a Curva de Juros..."):
        try:
            url = "https://www.anbima.com.br/informacoes/est-termo/CZ-down.asp"
            max_dias = 10000
            tipo_curva = "PREFIXADOS"

            data_teste = pd.Timestamp.today().normalize()

            while True:
                data_formatada = data_teste.strftime("%d/%m/%Y")
                payload = {"Idioma": "PT", "Dt_Ref": data_formatada, "saida": "csv"}
                response = requests.post(url, data=payload)
                linhas_csv = response.text.splitlines()
                linhas_filtradas = [linha for linha in linhas_csv if linha.startswith(tipo_curva)]
                if linhas_filtradas:
                    linha_alvo = linhas_filtradas[0]
                    break
                data_teste = data_teste - pd.tseries.offsets.BDay(1)

            colunas = linha_alvo.split(";")
            b1 = float(colunas[1].replace(",", "."))
            b2 = float(colunas[2].replace(",", "."))
            b3 = float(colunas[3].replace(",", "."))
            b4 = float(colunas[4].replace(",", "."))
            l1 = float(colunas[5].replace(",", "."))
            l2 = float(colunas[6].replace(",", "."))

            vertices = np.arange(1, max_dias + 1)
            t = vertices / 252
            termo1 = (1 - np.exp(-l1 * t)) / (l1 * t)
            termo2 = termo1 - np.exp(-l1 * t)
            termo3 = ((1 - np.exp(-l2 * t)) / (l2 * t)) - np.exp(-l2 * t)
            taxas = (b1 + b2 * termo1 + b3 * termo2 + b4 * termo3) * 100

            df_curva = pd.DataFrame({"Vertice": vertices, "Taxa": taxas}).set_index("Vertice")

            prazo_1_sel, taxa_di_1 = calcular_vertice(df_curva, int(prazo_1))
            resultado_1 = calcular_titulo(taxa_di_1, tipo_titulo_1, taxa_1, prazo_1_sel, modalidade_1)

            resultado_2 = None
            prazo_2_sel = None
            taxa_di_2 = None

            if modo_analise == "Comparar dois títulos":
                prazo_2_sel, taxa_di_2 = calcular_vertice(df_curva, int(prazo_2))
                resultado_2 = calcular_titulo(taxa_di_2, tipo_titulo_2, taxa_2, prazo_2_sel, modalidade_2)

            st.success("Cálculo realizado com sucesso!")

            col1, col2, col3 = st.columns(3)
            col1.metric("Data Base da Curva", data_formatada)
            col2.metric("Vértice Utilizado", f"{prazo_1_sel} dias úteis")
            col3.metric("DI Estimado", f"{taxa_di_1:.2f}% a.a.")

            if modo_analise == "Um título":
                st.markdown("### Resultado da Aplicação")
                c1, c2, c3 = st.columns(3)
                c1.metric("Dias corridos considerados", f"{resultado_1['dias_corridos']} dias")
                c2.metric("Alíquota de IR", f"{resultado_1['aliquota_ir'] * 100:.1f}%")
                c3.metric("Rendimento DI", f"{resultado_1['resultado_di']}%")

                c4, c5, c6 = st.columns(3)
                c4.metric("Retorno Bruto", f"{resultado_1['resultado_bruto']}%")
                if tipo_titulo_1 == "Tributado":
                    c5.metric("Retorno Líquido", f"{resultado_1['resultado_liquido']}%")
                    c6.metric("Taxa líquida a.a.", f"{resultado_1['taxa_ano_liquida']:.2f}% a.a.")
                    st.info(
                        f"💡 **Título tributado:** IR regressivo aplicado em {resultado_1['aliquota_ir'] * 100:.1f}% sobre o lucro. "
                        f"Dias corridos considerados: {resultado_1['dias_corridos']}."
                    )
                else:
                    c5.metric("Retorno Final", f"{resultado_1['resultado_liquido']}%")
                    c6.metric("Taxa estimada a.a.", f"{resultado_1['taxa_anual_bruta']:.2f}% a.a.")

            else:
                st.markdown("### Comparativo entre títulos")
                comp1, comp2 = st.columns(2)

                with comp1:
                    st.subheader("Título 1")
                    st.metric("Regime", tipo_titulo_1)
                    st.metric("Prazo", f"{prazo_1_sel} dias úteis")
                    st.metric("Dias corridos considerados", f"{resultado_1['dias_corridos']} dias")
                    st.metric("Alíquota de IR", f"{resultado_1['aliquota_ir'] * 100:.1f}%")
                    st.metric("DI Estimado", f"{taxa_di_1:.2f}% a.a.")
                    st.metric("Retorno Bruto", f"{resultado_1['resultado_bruto']}%")
                    if tipo_titulo_1 == "Tributado":
                        st.metric("Retorno Líquido", f"{resultado_1['resultado_liquido']}%")
                        st.caption(f"IR aplicado sobre o lucro: {resultado_1['aliquota_ir'] * 100:.1f}%")
                    else:
                        st.metric("Retorno Final", f"{resultado_1['resultado_liquido']}%")

                with comp2:
                    st.subheader("Título 2")
                    st.metric("Regime", tipo_titulo_2)
                    st.metric("Prazo", f"{prazo_2_sel} dias úteis")
                    st.metric("Dias corridos considerados", f"{resultado_2['dias_corridos']} dias")
                    st.metric("Alíquota de IR", f"{resultado_2['aliquota_ir'] * 100:.1f}%")
                    st.metric("DI Estimado", f"{taxa_di_2:.2f}% a.a.")
                    st.metric("Retorno Bruto", f"{resultado_2['resultado_bruto']}%")
                    if tipo_titulo_2 == "Tributado":
                        st.metric("Retorno Líquido", f"{resultado_2['resultado_liquido']}%")
                        st.caption(f"IR aplicado sobre o lucro: {resultado_2['aliquota_ir'] * 100:.1f}%")
                    else:
                        st.metric("Retorno Final", f"{resultado_2['resultado_liquido']}%")

            st.markdown("---")
            st.subheader("Gráfico da Curva de Juros (ETTJ)")
            df_plot = df_curva.reset_index()
            fig = px.line(
                df_plot,
                x="Vertice",
                y="Taxa",
                labels={"Vertice": "Dias Úteis", "Taxa": "Taxa Anualizada (%)"},
                title=f"Curva Prefixada Anbima - Base: {data_formatada}",
            )

            # DI Base
            fig.add_scatter(
                x=[prazo_1_sel],
                y=[taxa_di_1],
                mode="markers",
                marker=dict(color="blue", size=8, symbol="circle"),
                name="DI Base (ETTJ)",
            )

            # Título 1
            fig.add_scatter(
                x=[prazo_1_sel],
                y=[resultado_1["taxa_plot"]],
                mode="markers",
                marker=dict(color="red", size=10, symbol="circle"),
                name="Título 1",
            )

            # Título 2
            if modo_analise == "Comparar dois títulos":
                fig.add_scatter(
                    x=[prazo_2_sel],
                    y=[taxa_di_2],
                    mode="markers",
                    marker=dict(color="blue", size=8, symbol="circle"),
                    showlegend=False,
                )
                fig.add_scatter(
                    x=[prazo_2_sel],
                    y=[resultado_2["taxa_plot"]],
                    mode="markers",
                    marker=dict(color="green", size=10, symbol="circle"),
                    name="Título 2",
                )

            st.plotly_chart(fig, use_container_width=True)

            st.markdown("---")
            st.caption("**Fonte:** ANBIMA / Metodologia Nelson-Siegel-Svensson")
            st.info(
                "Disclaimer: Os resultados apresentados constituem meras projeções matemáticas baseadas na Estrutura a Termo da Taxa de Juros (ETTJ) vigente na data-base consultada. "
                "Tratando-se de estimativas fundamentadas em expectativas de mercado, os retornos reais apurados no vencimento poderão divergir das taxas aqui demonstradas devido à volatilidade econômica "
                "e às flutuações diárias da taxa CDI. Este cálculo possui caráter estritamente informativo e não configura promessa, recomendação de investimento ou garantia de rentabilidade futura."
            )

        except Exception as e:
            st.error(f"Ops! Não foi possível acessar a base de dados da Anbima no momento. Tente novamente em alguns minutos. Detalhe: {e}")
else:
    st.info("👈 Preencha os dados no menu lateral e clique em **Simular** para projetar a curva.")