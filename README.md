# Simulador de renda fixa

## Ambiente com uv

Instale o [uv](https://docs.astral.sh/uv/getting-started/installation/) em cada
computador. Depois de clonar o repositório, execute na pasta do projeto:

```sh
uv sync --locked
uv run --locked streamlit run streamlitrendafixa.py
```

O uv baixa o Python 3.13, se necessário, e cria o ambiente `.venv` com as
versões registradas no `uv.lock`. Não é necessário ativar o ambiente manualmente.
A série Python 3.13 é usada para manter compatibilidade com as dependências atuais.
Configuração validada com uv 0.13.4.

O arquivo `.python-version` fixa apenas a série `3.13`, permitindo usar a
atualização de correção disponível no computador ou serviço de hospedagem.
As versões das dependências continuam fixadas no `uv.lock`.

No Streamlit Community Cloud, selecione **Python 3.13** em **Advanced settings**
ao implantar. A seleção do interpretador é feita pela plataforma; o arquivo
`.python-version` não instala uma versão específica no Cloud. Se o app existente
usar outra série, siga as
[instruções para alterar o Python](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/upgrade-python).

Para sincronizar alterações em outro computador:

```sh
git pull
uv sync --locked
```

Versione `pyproject.toml`, `uv.lock` e `.python-version` junto com o código.
Cada computador deve ter sua própria `.venv`; não copie ou sincronize essa pasta
pelo iCloud ou outros serviços. Prefira clones locais separados via Git.
No VS Code, selecione o interpretador da `.venv` deste projeto.
As configurações locais em `.streamlit/secrets.toml`, quando necessárias, devem
ser configuradas separadamente em cada máquina e não entram no Git.

### Dependências

`pyproject.toml` é a fonte das dependências diretas; `uv.lock` fixa também as
dependências transitivas. Para adicionar ou remover pacotes, use `uv add nome`
ou `uv remove nome`. Para mudar uma versão fixada, use, por exemplo,
`uv add 'requests==VERSAO'`, substituindo `VERSAO` pela versão desejada.

O `requirements.txt` é exportado do lock para ambientes que ainda usam pip.
Após qualquer alteração nas dependências, regenere esse arquivo e rode os testes:

```sh
uv export --locked --no-dev --no-emit-project --no-hashes --output-file requirements.txt
uv run --locked python -m unittest discover -s tests
```

Inclua os arquivos de dependências alterados no mesmo commit. O Dev Container
também instala e executa o app com uv.

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

Testes: `uv run --locked python -m unittest discover -s tests`.

Na validação da migração para uv, 4 dos 9 testes passaram; os 5 testes de
interação falharam no `AppTest` do Streamlit 1.48.1 ao processar o
`segmented_control` (`ValueError` em `ButtonGroup.indices`). Essa limitação
permanece pendente; a migração preserva a versão de Streamlit já declarada.
