from pyettj import ettj
import datetime as dt

data_ref = dt.date.today() - dt.timedelta(days=1)

while True:
    data_base = data_ref.strftime("%d/%m/%Y")
    try:
        print(f"Consultando a B3 para a data {data_base}...")
        
        # Puxa a curva completa da B3 usando o seu IP local
        df_ettj = ettj.get_ettj(data_base)
        
        # Salva a tabela inteira em um arquivo CSV
        df_ettj.to_csv("curva_b3.csv", index=False)
        
        # Salva a data consultada em um arquivo de texto para o simulador ler
        with open("data_base.txt", "w") as f:
            f.write(data_base)
            
        print("✅ Sucesso! Arquivo 'curva_b3.csv' atualizado com todos os vértices.")
        break
        
    except ValueError:
        # Se for fim de semana ou feriado, volta um dia e tenta de novo
        data_ref = data_ref - dt.timedelta(days=1)
    except Exception as e:
        print(f"❌ Erro ao baixar dados: {e}")
        break