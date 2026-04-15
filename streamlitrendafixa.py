import streamlit as st
from taxa_b3 import get_ettj
import datetime as dt

st.set_page_config(page_title="Simulador CDI Futuro", page_icon="📈", layout="centered")

st.title("Simulador de Renda Fixa Atrelada ao CDI")
st.write("Simule operações em % do CDI ou CDI + Taxa Fixa com base na curva ETTJ da B3.")

@st.cache_data(show_spinner=False)
def carregar_ettj():
    data_ref = dt.date.today() - dt.timedelta(days=1)

    while True:
        data_base = data_ref.strftime("%d/%m/%Y")
        try:
            df_ettj = get_ettj(data_base)
            return df_ettj, data_base
        except ValueError:
            data_ref = data_ref - dt.timedelta(days=1)

modalidade = st.selectbox(
    "Informe a modalidade:",
    options=["% do CDI", "CDI + Taxa Fixa"]
)

prazo = st.number_input(
    "Informe o prazo em dias corridos:",
    min_value=1,
    step=1,
    value=360
)

taxa = st.number_input(
    "Informe a taxa negociada (%):",
    min_value=0.0,
    step=0.01,
    value=100.0 if modalidade == "% do CDI" else 1.0,
    format="%.2f"
)

if st.button("Simular"):
    try:
        with st.spinner("Consultando curva ETTJ..."):
            df_ettj, data_base = carregar_ettj()

        vertice = df_ettj[["Dias Corridos", "DI x pré 360"]].copy()
        vertice["Dias Corridos"] = vertice["Dias Corridos"].astype(int)
        vertice = vertice.set_index("Dias Corridos").sort_index()

        if prazo in vertice.index:
            di_aa = vertice.loc[prazo]
        else:
            elegiveis = vertice.loc[vertice.index <= prazo]
            if elegiveis.empty:
                st.error("Não há vértice disponível para prazo inferior ou igual ao informado.")
                st.stop()
            di_aa = elegiveis.iloc[-1]

        prazo_selecionado = int(di_aa.name)
        taxa_di = float(di_aa.values[0])

        taxa_di_dia = ((1 + taxa_di / 100) ** (1 / 360) - 1) * 100
        fator_di = (1 + taxa_di_dia / 100) ** prazo_selecionado
        resultado_di = round(((fator_di - 1) * 100), 2)

        if modalidade == "% do CDI":
            taxa_contratada_dia = taxa_di_dia * taxa / 100
            taxa_contratada_ano = (((1 + taxa_contratada_dia / 100) ** 360) - 1) * 100
            fator_contratado = (1 + taxa_contratada_dia / 100) ** prazo_selecionado
            resultado = round(((fator_contratado - 1) * 100), 2)
            retorno_anual = taxa_contratada_ano

        else:
            spread_dia = ((1 + taxa / 100) ** (1 / 360) - 1) * 100
            taxa_dia = ((1 + taxa_di_dia / 100) * (1 + spread_dia / 100) - 1) * 100
            taxa_ano = (((1 + taxa_dia / 100) ** 360) - 1) * 100
            fator_spread = (1 + taxa_dia / 100) ** prazo_selecionado
            resultado = round(((fator_spread - 1) * 100), 2)
            retorno_anual = taxa_ano

        st.subheader("Resultado")
        st.write(f"**Data base utilizada:** {data_base}")
        st.write(f"**Vértice utilizado:** {prazo_selecionado} dias")
        st.write(f"**DI a.a. estimado:** {taxa_di:.2f}% a.a.")
        st.write(f"**Resultado do DI estimado:** {resultado_di:.2f}%")
        st.write(f"**Retorno anual estimado:** {retorno_anual:.2f}% a.a.")
        st.write(f"**Resultado estimado da aplicação:** {resultado:.2f}%")

        st.markdown("---")
        st.caption("Elaborado por: Fabricio Orlandin, CFP® / Fonte: B3")
        st.info(
            "Disclaimer: Os resultados apresentados constituem meras projeções "
            "matemáticas baseadas na Estrutura a Termo da Taxa de Juros (ETTJ) "
            "vigente na data-base consultada. Tratando-se de estimativas "
            "fundamentadas em expectativas de mercado, os retornos reais "
            "apurados no vencimento poderão divergir das taxas aqui demonstradas "
            "devido à volatilidade econômica e às flutuações diárias da taxa CDI. "
            "Este cálculo possui caráter estritamente informativo e não configura "
            "promessa, recomendação de investimento ou garantia de rentabilidade futura."
        )

    except Exception as e:
        st.error(f"Erro ao executar a simulação: {e}")