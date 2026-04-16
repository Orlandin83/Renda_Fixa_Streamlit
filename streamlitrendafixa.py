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
# SIDEBAR / MENU LATERAL DE INPUTS
# ==========================================
with st.sidebar:
    st.header("Entrada de Dados")
    
    escolha = st.selectbox(
        "Selecione a Modalidade:",
        options=["% do CDI", "CDI + Taxa Fixa"]
    )
    modalidade = 1 if escolha == "% do CDI" else 2
    
    # Atualizado para pedir dias úteis
    prazo = st.number_input("Prazo em dias úteis:", min_value=1, max_value=3600, value=252, step=1)
    taxa = st.number_input("Taxa negociada (ex: 110 ou 1.5):", min_value=0.0, value=110.0, step=0.1)
    
    st.markdown("---")
    st.caption("elaborado por: Fabricio Orlandin, CFP®")
    
    simular = st.button("Simular", type="primary", use_container_width=True)

# ==========================================
# LÓGICA MATEMÁTICA
# ==========================================
if simular:
    with st.spinner("Conectando à Anbima e extraindo a Curva de Juros..."):
        try:
            # 1 e 2. CONFIG, DATABASE E EXTRAÇÃO (Busca Inteligente de Data)
            url = "https://www.anbima.com.br/informacoes/est-termo/CZ-down.asp"
            max_dias = 3600
            tipo_curva = "PREFIXADOS"
            
            data_teste = pd.Timestamp.today().normalize()
            
            while True:
                data_formatada = data_teste.strftime("%d/%m/%Y")
                payload = {'Idioma': 'PT', 'Dt_Ref': data_formatada, 'saida': 'csv'}
                response = requests.post(url, data=payload)
                linhas_csv = response.text.splitlines()
                
                linhas_filtradas = [linha for linha in linhas_csv if linha.startswith(tipo_curva)]
                
                if len(linhas_filtradas) > 0:
                    linha_alvo = linhas_filtradas[0]
                    break
                else:
                    data_teste = data_teste - pd.tseries.offsets.BDay(1)
            
            colunas = linha_alvo.split(';')
            
            b1 = float(colunas[1].replace(',', '.'))
            b2 = float(colunas[2].replace(',', '.'))
            b3 = float(colunas[3].replace(',', '.'))
            b4 = float(colunas[4].replace(',', '.'))
            l1 = float(colunas[5].replace(',', '.'))
            l2 = float(colunas[6].replace(',', '.'))
            
            # 3. CÁLCULO DA CURVA DE SVENSSON (Base 252)
            vertices = np.arange(1, max_dias + 1)
            t = vertices / 252
            
            termo1 = (1 - np.exp(-l1 * t)) / (l1 * t)
            termo2 = termo1 - np.exp(-l1 * t)
            termo3 = ((1 - np.exp(-l2 * t)) / (l2 * t)) - np.exp(-l2 * t)
            taxas = (b1 + b2 * termo1 + b3 * termo2 + b4 * termo3) * 100 # Em %
            
            df_curva = pd.DataFrame({'Vertice': vertices, 'Taxa': taxas})
            df_curva = df_curva.set_index("Vertice")
            
            # 4. ENCONTRA O VÉRTICE SOLICITADO
            if prazo in df_curva.index:
                di_aa = df_curva.loc[prazo]
            else:
                di_aa = df_curva.loc[df_curva.index <= prazo].iloc[-1]
                
            # 5. CÁLCULOS DE RENTABILIDADE (Matemática alinhada à B3)
            prazo_selecionado = int(di_aa.name)
            taxa_di_anual = float(di_aa.values[0])
            
            taxa_di_dia = ((1 + taxa_di_anual / 100) ** (1/252) - 1)
            fator_di = (1 + taxa_di_dia) ** prazo_selecionado
            resultado_di = round(((fator_di - 1) * 100), 2)
            
            if modalidade == 1:
                percentual_cdi = taxa / 100
                taxa_contratada_dia = taxa_di_dia * percentual_cdi
                taxa_contratada_ano = (((1 + taxa_contratada_dia) ** 252) - 1) * 100
                fator_contratado = (1 + taxa_contratada_dia) ** prazo_selecionado
                resultado = round(((fator_contratado - 1) * 100) , 2)
                lbl_anual = "Retorno anual estimado"
                val_anual = f"{taxa_contratada_ano:.2f}% a.a."
            else:
                spread_dia = ((1 + taxa / 100) ** (1/252) - 1)
                taxa_mista_dia = ((1 + taxa_di_dia) * (1 + spread_dia)) - 1
                taxa_ano = (((1 + taxa_mista_dia) ** 252) - 1) * 100
                fator_spread = (1 + taxa_mista_dia) ** prazo_selecionado
                resultado = round(((fator_spread - 1) * 100), 2)
                lbl_anual = "Retorno anual estimado"
                val_anual = f"{taxa_ano:.2f}% a.a."

            # ==========================================
            # APRESENTAÇÃO DOS RESULTADOS
            # ==========================================
            st.success("Cálculo realizado com sucesso!")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Data Base da Curva", data_formatada)
            col2.metric("Vértice Utilizado", f"{prazo_selecionado} dias úteis")
            col3.metric("DI Estimado", f"{taxa_di_anual:.2f}% a.a.")
            
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
                          labels={"Vertice": "Dias Úteis", "Taxa": "Taxa Anualizada (%)"},
                          title=f"Curva Prefixada Anbima - Base: {data_formatada}")
            
            fig.add_scatter(x=[prazo_selecionado], y=[taxa_di_anual], mode='markers', 
                            marker=dict(color='red', size=10), name="Seu Prazo")
            st.plotly_chart(fig, use_container_width=True)

            # Footer / Disclaimer
            st.markdown("---")
            st.caption("**Fonte:** B3 / Metodologia Nelson-Siegel-Svensson (ANBIMA)")
            st.info("Disclaimer: Os resultados apresentados constituem meras projeções matemáticas baseadas na Estrutura a Termo da Taxa de Juros (ETTJ) vigente na data-base consultada. Tratando-se de estimativas fundamentadas em expectativas de mercado, os retornos reais apurados no vencimento poderão divergir das taxas aqui demonstradas devido à volatilidade econômica e às flutuações diárias da taxa CDI. Este cálculo possui caráter estritamente informativo e não configura promessa, recomendação de investimento ou garantia de rentabilidade futura.")
            
        except Exception as e:
            st.error(f"Ops! Não foi possível acessar a base de dados da Anbima no momento. Tente novamente em alguns minutos. Detalhe: {e}")

else:
    st.info("👈 Preencha os dados no menu lateral e clique em **Simular** para projetar a curva.")