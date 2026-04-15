import pandas as pd
import requests
import numpy as np
import urllib.request
import json

def svensson_rate(beta1, beta2, beta3, beta4, lambda1, lambda2, t):
    """Fórmula oficial do modelo de Svensson da ANBIMA"""
    if t == 0:
        return beta1 + beta2
    termo1 = (1 - np.exp(-lambda1 * t)) / (lambda1 * t)
    termo2 = termo1 - np.exp(-lambda1 * t)
    termo3 = ((1 - np.exp(-lambda2 * t)) / (lambda2 * t)) - np.exp(-lambda2 * t)
    taxa = beta1 + beta2 * termo1 + beta3 * termo2 + beta4 * termo3
    return taxa * 100

def get_ettj(data):
    dias_corridos = [30, 60, 90, 180, 360, 720, 1080]
    dias_uteis = [21, 42, 63, 126, 252, 504, 756]
    
    try:
        # 1. TENTA A CURVA COMPLETA DA ANBIMA
        url = "https://www.anbima.com.br/informacoes/est-termo/CZ.asp"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=5)
        response.encoding = 'iso-8859-1'
        
        linhas = response.text.split('\n')
        linha_pre = [linha for linha in linhas if "PREFIXADOS" in linha][0]
        valores_str = linha_pre.split(';')[1:] 
        
        coeficientes = [float(v.strip().replace(',', '.')) for v in valores_str if v.strip()]
        b1, b2, b3, b4, L1, L2 = coeficientes

        taxas_projetadas = []
        for du in dias_uteis:
            t = du / 252.0
            taxas_projetadas.append(round(svensson_rate(b1, b2, b3, b4, L1, L2, t), 4))
            
        return pd.DataFrame({
            "Dias Corridos": dias_corridos,
            "Dias Úteis": dias_uteis,
            "DI x pré 252": taxas_projetadas,
            "DI x pré 360": taxas_projetadas
        })
        
    except Exception:
        # 2. SE A ANBIMA BLOQUEAR A NUVEM, BUSCA NO BANCO CENTRAL IMEDIATAMENTE
        try:
            url_bcb = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.11/dados/ultimos/1?formato=json"
            req = urllib.request.Request(url_bcb, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response_bcb:
                dados = json.loads(response_bcb.read().decode('utf-8'))
                taxa_fallback = float(dados[0]["valor"])
        except Exception:
            # 3. SE O BCB CAIR, USA TAXA FIXA PARA NÃO TRAVAR O SITE
            taxa_fallback = 10.40
            
        return pd.DataFrame({
            "Dias Corridos": dias_corridos,
            "Dias Úteis": dias_uteis,
            "DI x pré 252": [taxa_fallback]*7,
            "DI x pré 360": [taxa_fallback]*7
        })