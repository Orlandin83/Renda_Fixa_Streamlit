import streamlit as st
import datetime as dt
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
# SIDEBAR / MENU LATERAL DE INPUTS (Substitui o Pop-Up 1)
# ==========================================
with st.sidebar:
    st.header("Entrada de Dados")
    
    # Substitui os Radiobuttons do Tkinter pelo Selectbox do Streamlit
    escolha = st.selectbox(
        "Selecione a Modalidade:",
        options=["% do CDI", "CDI + Taxa Fixa"]
    )
    modalidade = 1 if escolha == "% do CDI" else 2
    
    # Substitui os Entries por Number Inputs para impedir digitação de letras
    prazo = st.number_input("Prazo em dias corridos:", min_value=1, max_value=3600, value=360, step=1)
    taxa = st.number_input("Taxa negociada (ex: 110 ou 1.5):", min_value=0.0, value=110.0, step=0.1)
    
    st.markdown("---")
    st.caption("elaborado por: Fabricio Orlandin, CFP® | matrícula: c074311")
    
    simular = st.button("Simular", type="primary", use_container_width=True)

# ==========================================
# LÓGICA MATEMÁTICA (Oculta do usuário até clicar no botão)
# ==========================================
if simular:
    with st.spinner("Conectando à Anbima e extraindo a Curva de Juros..."):
        try:
            # 1. DATABASE
            hoje = pd.Timestamp.today()
            data_util = hoje - pd.tseries.offsets.BDay(1)
            data_formatada = data_util.strftime("%d/%m/%Y")
            
            # 2. CONFIG
            url = "https://www.anbima.com.br/informacoes/est-termo/CZ-down.asp"
            max_dias = 3600
            base_ano = 360
            tipo_curva = "PREFIXADOS"
            
            # 3. EXTRAÇÃO DOS PARÂMETROS DA ANBIMA (Via Web Scraping do POST)
            payload = {'Idioma': 'PT', 'Dt_Ref': data_formatada, 'saida': 'csv'}
            response = requests.post(url, data=payload)
            
            linhas_csv = response.text.splitlines()
            linha_alvo = [linha for linha in linhas_csv if linha.startswith(tipo_curva)][0]
            colunas = linha_alvo.split(';')
            
            b1 = float(colunas[1].replace(',', '.'))
            b2 = float(colunas[2].replace(',', '.'))
            b3 = float(colunas[3].replace(',', '.'))
            b4 = float(colunas[4].replace(',', '.'))
            l1 = float(colunas[5].replace(',', '.'))
            l2 = float(colunas[6].replace(',', '.'))
            
            # 4. CÁLCULO DA CURVA DE SVENSSON (Vetorizada)
            vertices = np.arange(1, max_dias + 1)
            t = vertices / base_ano
            termo1 = (1 - np.exp(-l1 * t)) / (l1 * t)
            termo2 = termo1 - np.exp(-l1 * t)
            termo3 = ((1 - np.exp(-l2 * t)) / (l2 * t)) - np.exp(-l2 * t)
            taxas = (b1 + b2 * termo1 + b3 * termo2 + b4 * termo3) * 100 # Em %
            
            df_curva = pd.DataFrame({'Vertice': vertices, 'Taxa': taxas})
            df_curva = df_curva.set_index("Vertice")
            
            # 5. ENCONTRA O VÉRTICE SOLICITADO
            if prazo in df_curva.index:
                di_aa = df_curva.loc[prazo]
            else:
                di_aa = df_curva.loc[df_curva.index <= prazo].iloc[-1]
                
            prazo_selecionado = int(di_aa.name)
            taxa_di = float(di_aa.values[0])
            
            # 6. CÁLCULOS DE RENTABILIDADE
            taxa_di_dia = ((1 + taxa_di / 100) ** (1/360) - 1) * 100
            fator_di = (1 + taxa_di_dia / 100) ** prazo_selecionado
            resultado_di = round(((fator_di - 1) * 100), 2)
            
            if modalidade == 1:
                taxa_contratada_dia = (taxa_di_dia * taxa / 100)
                taxa_contratada_ano = (((1 + taxa_contratada_dia / 100) ** 360) - 1) * 100
                fator_contratado = (1 + taxa_contratada_dia / 100) ** prazo_selecionado
                resultado = round(((fator_contratado - 1) * 100) , 2)
                lbl_anual = f"Retorno anual estimado"
                val_anual = f"{taxa_contratada_ano:.2f}% a.a."
            else:
                spread_dia = ((1 + taxa / 100) ** (1 / 360) - 1) * 100
                taxa_dia_mista = ((1 + taxa_di_dia / 100) * (1 + spread_dia / 100) - 1) * 100
                taxa_ano = (((1 + taxa_dia_mista / 100) ** 360) - 1) * 100
                fator_spread = (1 + taxa_dia_mista / 100) ** prazo_selecionado
                resultado = round(((fator_spread - 1) * 100), 2)
                lbl_anual = f"Retorno anual estimado"
                val_anual = f"{taxa_ano:.2f}% a.a."

            # ==========================================
            # APRESENTAÇÃO DOS RESULTADOS (Substitui o Pop-up 2)
            # ==========================================
            st.success("Cálculo realizado com sucesso!")
            
            # Divide os resultados em caixas bonitas e modernas
            col1, col2, col3 = st.columns(3)
            col1.metric("Data Base da Curva", data_formatada)
            col2.metric("Vértice Utilizado", f"{prazo_selecionado} dias")
            col3.metric("DI Estimado", f"{taxa_di:.2f}% a.a.")
            
            st.markdown("### Resultado da Aplicação")
            c1, c2, c3 = st.columns(3)
            c1.metric("Rendimento DI", f"{resultado_di}%")
            c2.metric(lbl_anual, val_anual)
            c3.metric("Rendimento Final", f"{resultado}%", delta="Sua Carteira")
            
            # BÔNUS: PLOTANDO O GRÁFICO DA CURVA
            st.markdown("---")
            st.subheader("Gráfico da Curva de Juros (ETTJ)")
            df_plot = df_curva.reset_index()
            fig = px.line(df_plot, x="Vertice", y="Taxa", 
                          labels={"Vertice": "Dias Corridos", "Taxa": "Taxa Anualizada (%)"},
                          title=f"Curva Prefixada Anbima - Base: {data_formatada}")
            
            # Adiciona um ponto vermelho mostrando exatamente onde o usuário está investindo
            fig.add_scatter(x=[prazo_selecionado], y=[taxa_di], mode='markers', 
                            marker=dict(color='red', size=10), name="Seu Prazo")
            st.plotly_chart(fig, use_container_width=True)

            # Footer / Disclaimer
            st.markdown("---")
            st.caption("**Fonte:** B3 / Metodologia Nelson-Siegel-Svensson (ANBIMA)")
            st.info("Disclaimer: Os resultados apresentados constituem meras projeções matemáticas baseadas na Estrutura a Termo da Taxa de Juros (ETTJ) vigente na data-base consultada. Tratando-se de estimativas fundamentadas em expectativas de mercado, os retornos reais apurados no vencimento poderão divergir das taxas aqui demonstradas devido à volatilidade econômica e às flutuações diárias da taxa CDI. Este cálculo possui caráter estritamente informativo e não configura promessa, recomendação de investimento ou garantia de rentabilidade futura.")
            
        except Exception as e:
            st.error("Ops! Não foi possível acessar a base de dados da Anbima no momento. A B3 ou a Anbima podem ter atualizado o layout do site. Tente novamente em alguns minutos.")

else:
    # Tela inicial antes do usuário clicar em Simular
    st.info("👈 Preencha os dados no menu lateral e clique em **Simular** para projetar a curva.")