# Simulador de renda fixa

Execute `pip install -r requirements.txt` e `streamlit run streamlitrendafixa.py`.

## IPCA+ e CDI projetado

O indicador `% do CDI projetado (bruto)` divide o retorno bruto acumulado do
IPCA+ pelo retorno bruto do referencial no mesmo prazo, multiplicando por 100.
O referencial é estimado pela curva prefixada ANBIMA. Não representa uma taxa
contratada de remuneração diária em % do CDI. Quando o referencial é zero,
o indicador apresenta N/D. O IR não entra nessa comparação bruta.

## Contador global no Streamlit Community Cloud

O contador depende de PostgreSQL externo para sobreviver a recriações do app.

1. Em um banco PostgreSQL, execute `contador_setup.sql` uma vez.
2. Em Settings > Secrets do aplicativo, configure uma conexão de servidor:

   ```toml
   SIMULACOES_DATABASE_URL = "postgresql://USUARIO:SENHA@HOST:5432/BANCO?sslmode=require"
   ```

   Use a URL fornecida pelo seu provedor, compatível com a rede do Community
   Cloud, e um usuário autorizado a SELECT/UPDATE na tabela. Com RLS ativado,
   a conexão deve usar o proprietário da tabela ou uma política apropriada.
   Não coloque credenciais no Git. Caracteres especiais na senha devem estar
   codificados para URL.

3. Publique o código com as dependências atualizadas.

Cada clique em Simular que conclui a apresentação dos resultados soma 1,
mesmo na comparação de dois títulos. Acessos, mudanças de campos e simulações
com erro não somam. O total é compartilhado, com incremento atômico, e aparece
no rodapé: `XX simulações feitas desde 07/09/2026`.
O rodapé consulta o total a cada execução da página; não atualiza sozinho em
abas ociosas. A data é fixa e o total inicia em zero na ativação: não há
recuperação de simulações anteriores. Se o banco falhar, o cálculo continua,
mas aquela simulação pode não ser contabilizada; não há total local substituto.

Para desenvolvimento local, é possível configurar `SIMULACOES_DB_PATH` com
um caminho SQLite. Não use esse modo como armazenamento no Community Cloud.

Testes: `.venv/bin/python -m unittest discover -s tests`.
