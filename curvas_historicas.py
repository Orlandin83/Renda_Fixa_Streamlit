"""Consulta somente leitura do histórico e reconstrução das curvas ANBIMA."""
import numpy as np
import pandas as pd
import requests

# Chave publicável: permite apenas SELECT, protegido por grants e RLS no banco.
SUPABASE_URL = 'https://ptwmqpxdnomamxfuogfg.supabase.co'
SUPABASE_PUBLIC_KEY = 'sb_publishable_OGXzjngxdwuH9yX9nbbngA_HYvCDTBN'
PARAMETROS = ['b1', 'b2', 'b3', 'b4', 'l1', 'l2']
TIPOS = ['Prefixada', 'Juros reais (IPCA+)', 'Inflação implícita']


def curva_svensson(vertices, b1, b2, b3, b4, l1, l2):
    t = np.asarray(vertices, dtype=float) / 252
    if l1 <= 0 or l2 <= 0 or np.any(t <= 0):
        raise ValueError('Prazos e lambdas devem ser positivos.')
    termo1 = -np.expm1(-l1 * t) / (l1 * t)
    termo2 = termo1 - np.exp(-l1 * t)
    termo3 = -np.expm1(-l2 * t) / (l2 * t) - np.exp(-l2 * t)
    return (b1 + b2 * termo1 + b3 * termo2 + b4 * termo3) * 100


def consultar_historico():
    registros = []
    # Paginação explícita: a API limita o número de linhas por resposta.
    for offset in range(0, 100000, 500):
        resposta = requests.get(
            SUPABASE_URL + '/rest/v1/curvas_anbima',
            headers={'apikey': SUPABASE_PUBLIC_KEY},
            params={'select': 'data_referencia,indexador,ultimo_vertice_du,' + ','.join(PARAMETROS),
                    'order': 'data_referencia.desc,indexador.asc',
                    'limit': 500, 'offset': offset}, timeout=20)
        resposta.raise_for_status()
        pagina = resposta.json()
        if not isinstance(pagina, list):
            raise ValueError('Histórico inválido.')
        registros.extend(pagina)
        if len(pagina) < 500:
            break
    else:
        raise ValueError('Histórico excedeu o limite de consulta.')
    df = pd.DataFrame(registros, columns=['data_referencia', 'indexador', 'ultimo_vertice_du', *PARAMETROS])
    if not df.empty:
        df['data_referencia'] = pd.to_datetime(df['data_referencia']).dt.date
        df[PARAMETROS] = df[PARAMETROS].astype(float)
        if not np.isfinite(df[PARAMETROS].to_numpy()).all() or (df[['l1', 'l2']] <= 0).any().any():
            raise ValueError('Parâmetros inválidos no histórico.')
    return df


def datas_completas(df):
    return sorted([data for data, grupo in df.groupby('data_referencia')
                   if len(grupo) == 2 and set(grupo['indexador']) == {'PREFIXADOS', 'IPCA'}], reverse=True)


def calcular_curvas(df, datas, tipo, vertices):
    partes = []
    for data in sorted(datas):
        linhas = df[df['data_referencia'] == data].set_index('indexador')
        pre = curva_svensson(vertices, *linhas.loc['PREFIXADOS', PARAMETROS].to_numpy(dtype=float))
        real = curva_svensson(vertices, *linhas.loc['IPCA', PARAMETROS].to_numpy(dtype=float))
        if np.any(real <= -100):
            raise ValueError('Curva real inválida para calcular inflação implícita.')
        taxas = pre if tipo == TIPOS[0] else real if tipo == TIPOS[1] else ((1 + pre / 100) / (1 + real / 100) - 1) * 100
        limite = limite_publicado(linhas, tipo)
        situacao = np.where(np.asarray(vertices) <= limite, 'Intervalo publicado', 'Extrapolação') if pd.notna(limite) else np.repeat('Limite não disponível', len(vertices))
        partes.append(pd.DataFrame({'Data': data.strftime('%d/%m/%Y'),
                                    'Prazo (anos)': np.asarray(vertices) / 252,
                                    'Taxa (% a.a.)': taxas, 'Trecho': situacao}))
    return pd.concat(partes, ignore_index=True)


def limite_publicado(linhas, tipo):
    """Inflação implícita usa o intervalo comum das curvas de origem."""
    if 'ultimo_vertice_du' not in linhas:
        return float('nan')
    pre = linhas.loc['PREFIXADOS', 'ultimo_vertice_du']
    real = linhas.loc['IPCA', 'ultimo_vertice_du']
    pre = float(pre) if pd.notna(pre) else float('nan')
    real = float(real) if pd.notna(real) else float('nan')
    if tipo == TIPOS[0]:
        return pre
    if tipo == TIPOS[1]:
        return real
    return min(pre, real) if pd.notna(pre) and pd.notna(real) else float('nan')
