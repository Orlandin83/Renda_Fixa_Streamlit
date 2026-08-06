import streamlit as st
import requests
import numpy as np
import pandas as pd
import plotly.express as px


# ==========================================
# CONFIGURAÇÃO DA PÁGINA STREAMLIT
# ==========================================
st.set_page_config(
    page_title="Simulador de Renda Fixa através da Estrutura de Taxa a Termo da ANBIMA",
    page_icon="📊",
    layout="centered",
)

st.title("📊 Simulador de Renda Fixa através da Estrutura de Taxa a Termo da ANBIMA")
st.markdown("Cálculo baseado na Estrutura a Termo da Taxa de Juros (ETTJ) da ANBIMA")


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
        menores = df_curva.loc[df_curva.index <= prazo_selecionado]
        if menores.empty:
            di_aa = df_curva.iloc[0]
        else:
            di_aa = menores.iloc[-1]
    return int(di_aa.name), float(di_aa.values[0])


def curva_svensson(vertices: np.ndarray, b1: float, b2: float, b3: float, b4: float, l1: float, l2: float):
    t = np.where(vertices == 0, 1e-9, vertices / 252)
    termo1 = (1 - np.exp(-l1 * t)) / (l1 * t)
    termo2 = termo1 - np.exp(-l1 * t)
    termo3 = ((1 - np.exp(-l2 * t)) / (l2 * t)) - np.exp(-l2 * t)
    return (b1 + b2 * termo1 + b3 * termo2 + b4 * termo3) * 100


def taxa_anual_para_diaria(taxa_anual: float) -> float:
    return (1 + taxa_anual / 100) ** (1 / 252) - 1


def retorno_252_dias(taxa_anual_dia: float, prazo_uteis: int) -> float:
    return (1 + taxa_anual_dia) ** prazo_uteis


def taxa_aa_de_taxa_dia(taxa_dia: float) -> float:
    return ((1 + taxa_dia) ** 252 - 1) * 100


def formatar_br(valor: float) -> str:
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def calcular_taxa_di(dias_uteis: int, curva_df: pd.DataFrame) -> float:
    vertice_sel, taxa_sel = calcular_vertice(curva_df, dias_uteis)
    return vertice_sel, taxa_sel


def calcular_inflacao_implicita(taxa_pre: np.ndarray, taxa_ipca: np.ndarray) -> np.ndarray:
    return ((1 + taxa_pre / 100) / (1 + taxa_ipca / 100) - 1) * 100


def arredondar_resultado(res: dict) -> dict:
    campos = [
        "taxa_anual_bruta",
        "resultado_bruto",
        "resultado_liquido",
        "resultado_di",
        "taxa_plot",
        "lucro_bruto",
        "lucro_liquido",
        "taxa_ano_liquida",
    ]
    for campo in campos:
        if campo in res and isinstance(res[campo], (int, float, np.floating)):
            res[campo] = round(float(res[campo]), 2)
    if "aliquota_ir" in res and isinstance(res["aliquota_ir"], (int, float, np.floating)):
        res["aliquota_ir"] = round(float(res["aliquota_ir"]), 3)
    return res


def aplicar_taxa_ipca_plus(
    principal: float,
    prazo_uteis: int,
    inflacao_impl: float,
    taxa_real: float,
    tipo_regime: str,
):
    taxa_real_dia = (1 + taxa_real / 100) ** (1 / 252) - 1
    taxa_ipca_dia = (1 + inflacao_impl / 100) ** (1 / 252) - 1

    fator_bruto = (1 + taxa_real_dia) ** prazo_uteis * (1 + taxa_ipca_dia) ** prazo_uteis
    valor_bruto = principal * fator_bruto
    lucro_bruto = valor_bruto - principal
    resultado_bruto = round((valor_bruto / principal - 1) * 100, 2)
    dias_corridos = dias_corridos_aproximados(prazo_uteis)
    taxa_aa = (((1 + taxa_real_dia) ** 252) * ((1 + taxa_ipca_dia) ** 252) - 1) * 100

    if tipo_regime == "Isento":
        res = {
            "tipo": "Isento",
            "taxa_anual_bruta": round(taxa_aa, 2),
            "resultado_bruto": resultado_bruto,
            "resultado_liquido": resultado_bruto,
            "fator_bruto": fator_bruto,
            "fator_liquido": fator_bruto,
            "aliquota_ir": 0.0,
            "resultado_di": resultado_bruto,
            "taxa_plot": round(taxa_aa, 2),
            "lucro_bruto": lucro_bruto / principal,
            "lucro_liquido": lucro_bruto / principal,
            "taxa_ano_liquida": round(taxa_aa, 2),
            "dias_corridos": dias_corridos,
        }
        return arredondar_resultado(res)

    aliquota_ir = obter_aliquota_ir(dias_corridos)
    lucro_liquido = lucro_bruto * (1 - aliquota_ir)
    valor_liquido = principal + lucro_liquido
    resultado_liquido = round((valor_liquido / principal - 1) * 100, 2)
    fator_liquido = valor_liquido / principal
    taxa_liquida_ano = round(((fator_liquido ** (252 / prazo_uteis)) - 1) * 100, 2)

    res = {
        "tipo": "Tributado",
        "taxa_anual_bruta": round(taxa_aa, 2),
        "resultado_bruto": resultado_bruto,
        "resultado_liquido": resultado_liquido,
        "fator_bruto": fator_bruto,
        "fator_liquido": fator_liquido,
        "aliquota_ir": aliquota_ir,
        "resultado_di": resultado_bruto,
        "taxa_plot": round(taxa_aa, 2),
        "lucro_bruto": lucro_bruto / principal,
        "lucro_liquido": lucro_liquido / principal,
        "taxa_ano_liquida": taxa_liquida_ano,
        "dias_corridos": dias_corridos,
    }
    return arredondar_resultado(res)


def calcular_titulo(
    taxa_di_anual,
    tipo_regime,
    taxa_input,
    prazo_selecionado,
    modalidade,
    curva_ipca_anbima=None,
):
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
    elif modalidade == 3:
        taxa_contratada_dia = ((1 + taxa_input / 100) ** (1 / 252) - 1)
        fator_bruto, taxa_contratada_ano, resultado_bruto = fluxo_sem_ir(taxa_contratada_dia)
    elif modalidade == 4:
        if curva_ipca_anbima is None:
            raise ValueError("Curva IPCA ANBIMA não informada para a modalidade IPCA+.")
        return aplicar_taxa_ipca_plus(
            principal=10000.0,
            prazo_uteis=prazo_selecionado,
            inflacao_impl=curva_ipca_anbima,
            taxa_real=taxa_input,
            tipo_regime=tipo_regime,
        )
    else:
        raise ValueError("Modalidade inválida.")

    if tipo_regime == "Isento":
        res = {
            "tipo": "Isento",
            "taxa_anual_bruta": round(taxa_contratada_ano, 2),
            "resultado_bruto": round(resultado_bruto, 2),
            "resultado_liquido": round(resultado_bruto, 2),
            "fator_bruto": fator_bruto,
            "fator_liquido": fator_bruto,
            "aliquota_ir": 0.0,
            "resultado_di": resultado_di,
            "taxa_plot": round(taxa_contratada_ano, 2),
            "lucro_bruto": fator_bruto - 1,
            "lucro_liquido": fator_bruto - 1,
            "taxa_ano_liquida": round(taxa_contratada_ano, 2),
            "dias_corridos": dias_corridos,
        }
        return arredondar_resultado(res)

    lucro_bruto = fator_bruto - 1
    aliquota_ir = obter_aliquota_ir(dias_corridos)
    lucro_liquido = lucro_bruto * (1 - aliquota_ir)
    fator_liquido = 1 + lucro_liquido
    resultado_liquido = round(lucro_liquido * 100, 2)
    taxa_liquida_ano = round((((fator_liquido) ** (252 / prazo_selecionado)) - 1) * 100, 2)

    res = {
        "tipo": "Tributado",
        "taxa_anual_bruta": round(taxa_contratada_ano, 2),
        "resultado_bruto": round(resultado_bruto, 2),
        "resultado_liquido": resultado_liquido,
        "fator_bruto": fator_bruto,
        "fator_liquido": fator_liquido,
        "aliquota_ir": aliquota_ir,
        "resultado_di": resultado_di,
        "taxa_plot": round(taxa_contratada_ano, 2),
        "lucro_bruto": lucro_bruto,
        "lucro_liquido": lucro_liquido,
        "taxa_ano_liquida": taxa_liquida_ano,
        "dias_corridos": dias_corridos,
    }
    return arredondar_resultado(res)


with st.sidebar:
    st.header("Entrada de Dados")

    modo_analise = st.radio(
        "Tipo de análise:",
        options=["Um título", "Comparar dois títulos"],
        horizontal=False,
        key="modo_analise",
    )

    st.markdown("### Título 1")
    tipo_titulo_1 = st.selectbox(
        "Regime do título 1:",
        options=["Isento", "Tributado"],
        key="tipo_titulo_1_1",
    )

    escolha_1 = st.selectbox(
        "Selecione a Modalidade do título 1:",
        options=["% do CDI", "CDI + Taxa Fixa", "Taxa Pré-fixada", "IPCA + Taxa Fixa"],
        key="escolha_1_1",
    )
    modalidade_1 = (
        1 if escolha_1 == "% do CDI"
        else 2 if escolha_1 == "CDI + Taxa Fixa"
        else 3 if escolha_1 == "Taxa Pré-fixada"
        else 4
    )

    prazo_1 = st.number_input(
        "Prazo do título 1 em dias úteis:",
        min_value=1,
        max_value=10000,
        value=252,
        step=1,
        format="%d",
        key="prazo_1_1",
    )

    if modalidade_1 == 4:
        taxa_1 = st.number_input(
            "Taxa real do título 1 (IPCA + % a.a.):",
            min_value=0.0,
            value=6.0,
            step=0.1,
            key="taxa_1_ipca_1",
        )
    else:
        taxa_1 = st.number_input(
            "Taxa negociada do título 1 (ex: 104, 1.5 ou 11):",
            min_value=0.0,
            value=104.0,
            step=0.1,
            key="taxa_1_1",
        )

    if modo_analise == "Comparar dois títulos":
        st.markdown("---")
        st.markdown("### Título 2")
        tipo_titulo_2 = st.selectbox(
            "Regime do título 2:",
            options=["Isento", "Tributado"],
            key="tipo_titulo_2_2",
        )

        escolha_2 = st.selectbox(
            "Selecione a Modalidade do título 2:",
            options=["% do CDI", "CDI + Taxa Fixa", "Taxa Pré-fixada", "IPCA + Taxa Fixa"],
            key="escolha_2_2",
        )
        modalidade_2 = (
            1 if escolha_2 == "% do CDI"
            else 2 if escolha_2 == "CDI + Taxa Fixa"
            else 3 if escolha_2 == "Taxa Pré-fixada"
            else 4
        )

        prazo_2 = st.number_input(
            "Prazo do título 2 em dias úteis:",
            min_value=1,
            max_value=10000,
            value=252,
            step=1,
            format="%d",
            key="prazo_2_2",
        )

        if modalidade_2 == 4:
            taxa_2 = st.number_input(
                "Taxa real do título 2 (IPCA + % a.a.):",
                min_value=0.0,
                value=6.0,
                step=0.1,
                key="taxa_2_ipca_2",
            )
        else:
            taxa_2 = st.number_input(
                "Taxa negociada do título 2 (ex: 104, 1.5 ou 11):",
                min_value=0.0,
                value=104.0,
                step=0.1,
                key="taxa_2_2",
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

if simular:
    with st.spinner("Conectando à ANBIMA e extraindo a Curva de Juros..."):
        try:
            url = "https://www.anbima.com.br/informacoes/est-termo/CZ-down.asp"
            max_dias = 10000
            data_teste = pd.Timestamp.today().normalize()

            linha_prefixados = None
            linha_ipca = None
            data_formatada = None

            while True:
                data_formatada = data_teste.strftime("%d/%m/%Y")
                payload = {"Idioma": "PT", "Dt_Ref": data_formatada, "saida": "csv"}
                response = requests.post(url, data=payload, timeout=30)
                linhas_csv = response.text.splitlines()

                linhas_prefixadas = [linha for linha in linhas_csv if linha.startswith("PREFIXADOS")]
                linhas_ipca = [linha for linha in linhas_csv if linha.startswith("IPCA")]

                if linhas_prefixadas and linhas_ipca:
                    linha_prefixados = linhas_prefixadas[0]
                    linha_ipca = linhas_ipca[0]
                    break

                data_teste = data_teste - pd.tseries.offsets.BDay(1)

            col_prefix = linha_prefixados.split(";")
            b1_pre = float(col_prefix[1].replace(",", "."))
            b2_pre = float(col_prefix[2].replace(",", "."))
            b3_pre = float(col_prefix[3].replace(",", "."))
            b4_pre = float(col_prefix[4].replace(",", "."))
            l1_pre = float(col_prefix[5].replace(",", "."))
            l2_pre = float(col_prefix[6].replace(",", "."))

            col_ipca = linha_ipca.split(";")
            b1_ipca = float(col_ipca[1].replace(",", "."))
            b2_ipca = float(col_ipca[2].replace(",", "."))
            b3_ipca = float(col_ipca[3].replace(",", "."))
            b4_ipca = float(col_ipca[4].replace(",", "."))
            l1_ipca = float(col_ipca[5].replace(",", "."))
            l2_ipca = float(col_ipca[6].replace(",", "."))

            vertices = np.arange(1, max_dias + 1)
            taxas_pre = curva_svensson(vertices, b1_pre, b2_pre, b3_pre, b4_pre, l1_pre, l2_pre)
            taxas_ipca = curva_svensson(vertices, b1_ipca, b2_ipca, b3_ipca, b4_ipca, l1_ipca, l2_ipca)
            inflacao_impl = calcular_inflacao_implicita(taxas_pre, taxas_ipca)

            df_curva_pre = pd.DataFrame({"Vertice": vertices, "Taxa": taxas_pre}).set_index("Vertice")
            df_curva_ipca = pd.DataFrame({"Vertice": vertices, "Taxa": taxas_ipca}).set_index("Vertice")
            df_curva_impl = pd.DataFrame({"Vertice": vertices, "Taxa": inflacao_impl}).set_index("Vertice")

            prazo_1_sel, taxa_di_1 = calcular_vertice(df_curva_pre, int(prazo_1))
            _, taxa_ipca_1 = calcular_vertice(df_curva_ipca, int(prazo_1))
            _, inflacao_impl_1 = calcular_vertice(df_curva_impl, int(prazo_1))

            if modalidade_1 == 4:
                resultado_1 = aplicar_taxa_ipca_plus(
                    principal=10000.0,
                    prazo_uteis=prazo_1_sel,
                    inflacao_impl=inflacao_impl_1,
                    taxa_real=taxa_1,
                    tipo_regime=tipo_titulo_1,
                )
            else:
                resultado_1 = calcular_titulo(
                    taxa_di_anual=taxa_di_1,
                    tipo_regime=tipo_titulo_1,
                    taxa_input=taxa_1,
                    prazo_selecionado=prazo_1_sel,
                    modalidade=modalidade_1,
                )

            resultado_2 = None
            prazo_2_sel = None
            taxa_di_2 = None
            inflacao_impl_2 = None

            if modo_analise == "Comparar dois títulos":
                prazo_2_sel, taxa_di_2 = calcular_vertice(df_curva_pre, int(prazo_2))
                _, taxa_ipca_2 = calcular_vertice(df_curva_ipca, int(prazo_2))
                _, inflacao_impl_2 = calcular_vertice(df_curva_impl, int(prazo_2))

                if modalidade_2 == 4:
                    resultado_2 = aplicar_taxa_ipca_plus(
                        principal=10000.0,
                        prazo_uteis=prazo_2_sel,
                        inflacao_impl=inflacao_impl_2,
                        taxa_real=taxa_2,
                        tipo_regime=tipo_titulo_2,
                    )
                else:
                    resultado_2 = calcular_titulo(
                        taxa_di_anual=taxa_di_2,
                        tipo_regime=tipo_titulo_2,
                        taxa_input=taxa_2,
                        prazo_selecionado=prazo_2_sel,
                        modalidade=modalidade_2,
                    )

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
                c3.metric("Rendimento DI", f"{resultado_1['resultado_di']:.2f}%")

                c4, c5, c6 = st.columns(3)
                c4.metric("Retorno Bruto", f"{resultado_1['resultado_bruto']:.2f}%")
                if tipo_titulo_1 == "Tributado":
                    c5.metric("Retorno Líquido", f"{resultado_1['resultado_liquido']:.2f}%")
                    c6.metric("Taxa líquida a.a.", f"{resultado_1['taxa_ano_liquida']:.2f}% a.a.")
                    st.info(
                        f"💡 **Título tributado:** IR regressivo aplicado em {resultado_1['aliquota_ir'] * 100:.1f}% sobre o lucro. "
                        f"Dias corridos considerados: {resultado_1['dias_corridos']}."
                    )
                else:
                    c5.metric("Retorno Final", f"{resultado_1['resultado_liquido']:.2f}%")
                    c6.metric("Taxa estimada a.a.", f"{resultado_1['taxa_anual_bruta']:.2f}% a.a.")

                if modalidade_1 == 4:
                    st.info(
                        f"💡 **IPCA+**: a simulação usa a inflação implícita da ANBIMA no vértice selecionado "
                        f"({inflacao_impl_1:.2f}% a.a.) somada à taxa real contratada pelo usuário ({taxa_1:.2f}% a.a.)."
                    )
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
                    st.metric("Retorno Bruto", f"{resultado_1['resultado_bruto']:.2f}%")
                    if tipo_titulo_1 == "Tributado":
                        st.metric("Retorno Líquido", f"{resultado_1['resultado_liquido']:.2f}%")
                        st.caption(f"IR aplicado sobre o lucro: {resultado_1['aliquota_ir'] * 100:.1f}%")
                    else:
                        st.metric("Retorno Final", f"{resultado_1['resultado_liquido']:.2f}%")

                    if modalidade_1 == 4:
                        st.caption(
                            f"IPCA implícito ANBIMA: {inflacao_impl_1:.2f}% a.a. | Taxa real contratada: {taxa_1:.2f}% a.a."
                        )

                with comp2:
                    st.subheader("Título 2")
                    st.metric("Regime", tipo_titulo_2)
                    st.metric("Prazo", f"{prazo_2_sel} dias úteis")
                    st.metric("Dias corridos considerados", f"{resultado_2['dias_corridos']} dias")
                    st.metric("Alíquota de IR", f"{resultado_2['aliquota_ir'] * 100:.1f}%")
                    st.metric("DI Estimado", f"{taxa_di_2:.2f}% a.a.")
                    st.metric("Retorno Bruto", f"{resultado_2['resultado_bruto']:.2f}%")
                    if tipo_titulo_2 == "Tributado":
                        st.metric("Retorno Líquido", f"{resultado_2['resultado_liquido']:.2f}%")
                        st.caption(f"IR aplicado sobre o lucro: {resultado_2['aliquota_ir'] * 100:.1f}%")
                    else:
                        st.metric("Retorno Final", f"{resultado_2['resultado_liquido']:.2f}%")

                    if modalidade_2 == 4:
                        st.caption(
                            f"IPCA implícito ANBIMA: {inflacao_impl_2:.2f}% a.a. | Taxa real contratada: {taxa_2:.2f}% a.a."
                        )

            st.markdown("---")
            st.subheader("Gráfico da Curva de Juros (ETTJ)")
            df_plot_pre = df_curva_pre.reset_index()
            fig = px.line(
                df_plot_pre,
                x="Vertice",
                y="Taxa",
                labels={"Vertice": "Dias Úteis", "Taxa": "Taxa Anualizada (%)"},
                title=f"Curva Prefixada ANBIMA - Base: {data_formatada}",
            )

            fig.add_scatter(
                x=[prazo_1_sel],
                y=[taxa_di_1],
                mode="markers",
                marker=dict(color="blue", size=8, symbol="circle"),
                name="DI Base (ETTJ)",
            )

            fig.add_scatter(
                x=[prazo_1_sel],
                y=[resultado_1["taxa_plot"]],
                mode="markers",
                marker=dict(color="red", size=10, symbol="circle"),
                name="Título 1",
            )

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
                "Para os títulos IPCA+, a simulação utiliza a inflação implícita da ANBIMA, obtida a partir da relação entre a curva prefixada e a curva real, pela identidade de Fisher. "
                "Essa inflação implícita não é uma previsão pura do IPCA realizado: ela reflete a precificação do mercado e pode incluir expectativa de inflação, prêmio de risco, prêmio de liquidez, convexidade "
                "e outros componentes de mercado. Assim, os retornos reais apurados no vencimento poderão divergir das taxas demonstradas devido à volatilidade econômica, às mudanças de curva, ao comportamento "
                "da inflação, à tributação e às particularidades de cada ativo. Este cálculo possui caráter estritamente informativo e não configura promessa, recomendação de investimento ou garantia de rentabilidade futura."
            )
        except Exception as e:
            st.error(
                f"Ops! Não foi possível acessar a base de dados da ANBIMA no momento. Tente novamente em alguns minutos. Detalhe: {e}"
            )
else:
    st.info("👈 Preencha os dados no menu lateral e clique em **Simular** para projetar a curva.")