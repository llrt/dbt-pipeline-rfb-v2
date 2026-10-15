{# ---
id: gq_core__empresa_estabelecimento__01
conceito: empresa_estabelecimento
camada: core
perguntas:
  - "Quantas empresas e quantos estabelecimentos existem?"
  - "Quantas empresas ativas há, e não CNPJs?"
  - "Quantos CNPJs ativos tem o cadastro?"
intencao: "Contagem de estabelecimentos (CNPJ completo) e de empresas (matrizes, uma por CNPJ básico), no total e só ativos, no mês do gold."
tabelas: [fct_estabelecimentos]
colunas_chave: [cnpj_completo, eh_matriz, eh_ativa]
armadilhas:
  - "Estabelecimento ≠ empresa: `count(*)` conta estabelecimentos; empresas se contam pelas matrizes (`eh_matriz`)."
  - "'Empresa ativa' aqui é matriz ativa: a situação é do estabelecimento; uma empresa ativa pode ter filial baixada."
  - "O cadastro guarda os já encerrados: o total inclui baixados; para o estoque use `eh_ativa`."
  - "Ativa ≠ em operação: a situação cadastral não prova atividade (IN 2.119, art. 9º)."
variacoes:
  - "Por UF: junte dim_municipio por `sk_municipio` e agrupe por `sigla_uf`."
  - "Por CNAE: junte dim_cnae por `sk_cnae` e filtre `codigo_subclasse` ou `codigo_classe`."
  - "Por porte: junte dim_porte por `sk_porte`."
resposta_esperada_fixtures:
  colunas: [estabelecimentos, estabelecimentos_ativos, empresas, empresas_com_matriz_ativa]
  linhas:
    - [18, 11, 16, 10]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  count(*) as estabelecimentos,
  count(*) filter (where eh_ativa) as estabelecimentos_ativos,
  count(*) filter (where eh_matriz) as empresas,
  count(*) filter (where eh_matriz and eh_ativa) as empresas_com_matriz_ativa
from {{ ref('fct_estabelecimentos') }}
order by estabelecimentos
