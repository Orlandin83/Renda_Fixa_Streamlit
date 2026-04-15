import pandas as pd
from datetime import datetime
import json
import urllib.request

def get_ettj(data):
    try:
        data = datetime.strptime(data, "%d/%m/%Y").strftime("%Y-%m-%d")
        url = f"https://www2.cetip.com.br/ConsultarTaxaDi/ConsultarTaxaDICetip.aspx?data={data}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        
        with urllib.request.urlopen(req) as response:
            dados = json.loads(response.read().decode('utf-8'))
            taxa = float(dados["taxa"].replace(",", "."))
            
            df = pd.DataFrame({
                "Dias Corridos": [30, 60, 90, 180, 360, 720, 1080],
                "Dias Úteis": [21, 42, 63, 126, 252, 504, 756],
                "DI x pré 252": [taxa]*7,
                "DI x pré 360": [taxa]*7
            })
            return df
            
    except Exception as e:
        raise ValueError(f"Não foi possível baixar dados para a data informada. Erro: {e}")
