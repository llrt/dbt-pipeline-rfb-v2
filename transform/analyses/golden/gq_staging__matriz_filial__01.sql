{# ---
id: gq_staging__matriz_filial__01
conceito: matriz_filial
camada: staging
perguntas:
  - "Há empresa com mais de uma matriz no extrato?"
  - "Quantas empresas têm filial, segundo o staging?"
intencao: "Auditoria do staging: por CNPJ básico, quantas matrizes e filiais há, resumido em faixas (base da regra RN-16)."
tabelas: [stg_rfb__estabelecimentos]
colunas_chave: [cnpj_raiz, matriz_filial_codigo]
armadilhas:
  - "Contar empresas pelas matrizes supõe uma matriz por CNPJ básico; no dado real há uma exceção (RN-16)."
  - "Uma filial pode existir sem matriz no extrato do mês (ex.: matriz em outro arquivo ou ausente)."
  - "Resultado só em contagens: não liste CNPJ básico (ADR-0008)."
variacoes:
  - "Só ativos: `where situacao_codigo = 2` antes de agrupar."
resposta_esperada_fixtures:
  colunas: [matrizes, filiais, empresas]
  linhas:
    - [1, 0, 14]
    - [1, 1, 2]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

with por_empresa as (
  select
    cnpj_raiz,
    count(*) filter (where matriz_filial_codigo = 1) as matrizes,
    count(*) filter (where matriz_filial_codigo = 2) as filiais
  from {{ ref('stg_rfb__estabelecimentos') }}
  group by cnpj_raiz
)

select
  matrizes,
  filiais,
  count(*) as empresas
from por_empresa
group by matrizes, filiais
order by matrizes, filiais
