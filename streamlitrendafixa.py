import streamlit as st
import pandas as pd
import datetime as dt

st.set_page_config(page_title="Simulador CDI Futuro", page_icon="📈", layout="centered")

st.title("Simulador de Renda Fixa Atrelada ao CDI")
st.write("Simule operações em % do CDI ou CDI + Taxa Fixa com base na curva ETTJ oficial da B3.")

@st.cache_data(show_spinner=False)
def carregar_curva():
    try:
        # Lê o CSV que foi gerado pelo seu script local
        df_ettj = pd.read_csv('curva_b3.csv')
        
        # Como o pyettj gera índices complexos, garantimos a leitura limpa:
        vertice = df_ettj[["Dias Corridos", "DI x pré 360"]].copy()
        vertice["Dias Corridos"] = vertice["Dias Corridos"].astype(int)
        vertice = vertice.set_index("Dias Corridos").sort_index()
        
        # Lê a data-base que você salvou no .txt (se não existir, põe a data de hoje)
        try:
            with open('data_base.txt', 'r') as f:
                data_base = f.read().strip()
        except FileNotFoundError:
            data_base = dt.date.today().strftime("%d/%m/%Y")
            
        return vertice, data_base
    except Exception as e:
        st.error(f"Erro ao carregar a base de dados da B3: {e}")
        st.stop()

# ----- AQUI COMEÇA A INTERFACE -----

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
    with st.spinner("Consultando base de dados da B3..."):
        vertice, data_base = carregar_curva()

    # O MESMO CÓDIGO INTELIGENTE DE INTERPOLAÇÃO QUE VOCÊ CRIOU
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

    # OS CÁLCULOS QUE ARRUMAMOS ANTERIORMENTE
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

    # ----- MOSTRAR OS RESULTADOS -----
    st.subheader("Resultado")
    st.write(f"**Data base da Curva B3:** {data_base}")
    st.write(f"**Vértice da Curva utilizado:** {prazo_selecionado} dias corridos")
    st.write(f"**DI projetado no vértice (a.a.):** {taxa_di:.2f}% a.a.")
    st.write(f"**Resultado estimado do DI na aplicação:** {resultado_di:.2f}%")
    st.write(f"**Retorno anual da aplicação estimado:** {retorno_anual:.2f}% a.a.")
    st.write(f"**Resultado final estimado da aplicação:** {resultado:.2f}%")

    st.markdown("---")
    st.caption("Elaborado por: Fabricio Orlandin, CFP® / Fonte: B3")
    st.info(
        "Disclaimer: Os resultados apresentados constituem meras projeções matemáticas baseadas na "
        "Estrutura a Termo da Taxa de Juros (ETTJ) vigente na data-base consultada. "
        "Este cálculo possui caráter estritamente informativo."
    )