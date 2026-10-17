# Simulador de renda fixa

Execute `pip install -r requirements.txt` e `streamlit run streamlitrendafixa.py`.

## IPCA+ e CDI projetado

O indicador `% do CDI projetado (bruto)` divide o retorno bruto acumulado do
IPCA+ pelo retorno bruto do referencial no mesmo prazo, multiplicando por 100.
O referencial é estimado pela curva prefixada ANBIMA. Não representa uma taxa
contratada de remuneração diária em % do CDI. Quando o referencial é zero,
o indicador apresenta N/D. O IR não entra nessa comparação bruta.

## Curvas de juros

O menu superior alterna entre o simulador e a comparação histórica, sem exigir
seleção de títulos. Compare duas ou três datas nas curvas prefixada, real (IPCA+)
e de inflação implícita. O gráfico usa prazos constantes (252 dias úteis/ano),
com opções de 5, 10, 20 e 30 anos (padrão: 10), tabela por prazo e exportação CSV.
O último vértice publicado é armazenado por data/indexador: a linha fica tracejada
além dele. Para inflação implícita, usa-se o menor limite das duas curvas.
Limites ausentes são sinalizados com linha pontilhada. A tabela marca os prazos
extrapolados com asterisco, e o CSV inclui a classificação de cada ponto. A variação em pontos-base é
sempre a última data menos a primeira, independentemente da ordem de seleção.

O Supabase `renda-fixa` armazena quatro betas e dois lambdas por data/indexador.
O app consulta a Data API com chave publicável, somente leitura, sem precisar
de senha do banco nos Secrets. A tabela tem RLS; os clientes públicos não podem
inserir, alterar, excluir nem executar a coleta. O cache do app dura 15 minutos.

`curvas_setup.sql` documenta a instalação em um banco novo. A instalação já foi
aplicada no projeto conectado. A coleta privada roda pelo Supabase Cron às
21h30 e 23h30 de Brasília, independentemente de acessos ao Streamlit, e reconsulta
a última semana para recuperar atrasos e revisões. Feriados e publicações vazias
não geram registros; pares incompletos ou parâmetros inválidos abortam a coleta.
A data do cabeçalho precisa corresponder à data solicitada.

Histórico inicial: dez datas disponíveis entre 01/10/2026 e 15/10/2026. Para
carga administrativa adicional: `select curvas_privado.coletar('AAAA-MM-DD');`.
Monitoramento: Supabase > Integrations > Cron > `curvas-anbima-diaria` > History.
Uma indisponibilidade da ANBIMA gera falha no job e nova tentativa na próxima
execução; interrupções superiores a uma semana exigem recompor o intervalo.

O contador e seus arquivos foram excluídos. A antiga chave
`SIMULACOES_DATABASE_URL` não é mais usada e pode ser removida dos Secrets.

Testes: `.venv/bin/python -m unittest discover -s tests`.
