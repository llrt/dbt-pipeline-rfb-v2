{# ---
id: gq_core__regras_qualidade__01
conceito: regras_qualidade
camada: core
perguntas:
  - "Quantos estabelecimentos caem no NÃO INFORMADO de cada dimensão?"
  - "Os dados estão completos? Quanto fica sem município ou sem CNAE?"
intencao: "Cobertura do gold: estabelecimentos nos membros -1 (sem par) e -2 (data inválida) de cada chave da fato."
tabelas: [fct_estabelecimentos]
colunas_chave: [sk_municipio, sk_cnae, sk_natureza_juridica, sk_porte, sk_situacao_cadastral, sk_data_inicio_atividade, sk_data_situacao]
armadilhas:
  - "-1 = NÃO INFORMADO (sem par na dimensão); -2 = DATA INVÁLIDA (antes de 1900), nas duas datas da fato (início e situação). Eles aparecem como valores normais nos agrupamentos."
  - "Sem município inclui o exterior (UF 'EX' na RFB)."
variacoes:
  - "Só ativos: `where eh_ativa`."
resposta_esperada_fixtures:
  colunas: [estabelecimentos, sem_municipio, sem_cnae, sem_natureza, sem_porte, sem_situacao, inicio_sem_data, inicio_data_invalida, situacao_sem_data, situacao_data_invalida]
  linhas:
    - [18, 2, 1, 0, 1, 0, 1, 0, 2, 0]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  count(*) as estabelecimentos,
  count(*) filter (where sk_municipio = -1) as sem_municipio,
  count(*) filter (where sk_cnae = -1) as sem_cnae,
  count(*) filter (where sk_natureza_juridica = -1) as sem_natureza,
  count(*) filter (where sk_porte = -1) as sem_porte,
  count(*) filter (where sk_situacao_cadastral = -1) as sem_situacao,
  count(*) filter (where sk_data_inicio_atividade = -1) as inicio_sem_data,
  count(*) filter (where sk_data_inicio_atividade = -2) as inicio_data_invalida,
  count(*) filter (where sk_data_situacao = -1) as situacao_sem_data,
  count(*) filter (where sk_data_situacao = -2) as situacao_data_invalida
from {{ ref('fct_estabelecimentos') }}
order by estabelecimentos
