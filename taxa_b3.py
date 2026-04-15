import pandas as pd
import requests
import numpy as np

def svensson_rate(beta1, beta2, beta3, beta4, lambda1, lambda2, t):
    """
    Fórmula oficial do modelo de Svensson para calcular a taxa na ETTJ.
    t: tempo em anos úteis (dias_uteis / 252)
    """
    if t == 0:
        return beta1 + beta2
        
    termo1 = (1 - np.exp(-lambda1 * t)) / (lambda1 * t)
    termo2 = termo1 - np.exp(-lambda1 * t)
    termo3 = ((1 - np.exp(-lambda2 * t)) / (lambda2 * t)) - np.exp(-lambda2 * t)
    
    taxa = beta1 + beta2 * termo1 + beta3 * termo2 + beta4 * termo3
    return taxa * 100  # Retorna em %

def get_ettj(data):
    """
    Busca os parâmetros da ETTJ da ANBIMA e projeta a curva para os vértices do simulador.
    Como a ANBIMA não trava robôs internacionais, isso funciona perfeitamente no Streamlit Cloud.
    """
    try:
        # A Anbima fornece os parâmetros diários da curva neste endpoint público simples
        url = "https://www.anbima.com.br/informacoes/est-termo/CZ.asp"
        
        # Fazemos a requisição (timeout de 10s para não travar o app)
        response = requests.get(url, timeout=10)
        response.encoding = 'iso-8859-1'
        
        # Processa o texto de retorno para extrair os 6 coeficientes da linha "PREFIXADOS"
        linhas = response.text.split('\n')
        linha_pre = [linha for linha in linhas if "PREFIXADOS" in linha][0]
        valores_str = linha_pre.split(';')[1:] # Ignora a primeira coluna
        
        # Converte as strings brasileiras (vírgula) para floats do Python
        coeficientes = [float(v.strip().replace(',', '.')) for v in valores_str if v.strip()]
        b1, b2, b3, b4, L1, L2 = coeficientes

        # Monta a estrutura da curva que o seu simulador espera
        dias_corridos = [30, 60, 90, 180, 360, 720, 1080]
        dias_uteis = [21, 42, 63, 126, 252, 504, 756]
        taxas_projetadas = []
        
        for du in dias_uteis:
            # O tempo (t) no modelo é medido em anos úteis (Dias Úteis / 252)
            t = du / 252.0
            taxa_vertice = svensson_rate(b1, b2, b3, b4, L1, L2, t)
            taxas_projetadas.append(round(taxa_vertice, 4))
            
        # Retorna o DataFrame exatamente como o arquivo ettj.py antigo fazia
        df = pd.DataFrame({
            "Dias Corridos": dias_corridos,
            "Dias Úteis": dias_uteis,
            "DI x pré 252": taxas_projetadas,
            "DI x pré 360": taxas_projetadas # Mantido para não quebrar a chamada do seu simulador
        })
        
        return df
            
    except Exception as e:
        raise ValueError(f"Não foi possível calcular a curva de juros via ANBIMA. Erro: {e}")