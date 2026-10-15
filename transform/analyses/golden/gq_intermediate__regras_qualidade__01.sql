{# ---
id: gq_intermediate__regras_qualidade__01
conceito: regras_qualidade
camada: intermediate
perguntas:
  - "Há MEI com mais de um estabelecimento?"
  - "Quantas empresas MEI violam a regra de estabelecimento único?"
intencao: "Regra RN-05 ad hoc: empresas com opção pelo MEI por número de estabelecimentos não baixados no extrato."
tabelas: [int_estabelecimentos__enriquecidos]
colunas_chave: [cnpj_raiz, opcao_mei, situacao_codigo]
armadilhas:
  - "Só contagens: nunca liste os CNPJs das empresas que violam (ADR-0008)."
  - "O baixado continua no extrato mas não é mais estabelecimento da empresa: conte os não baixados."
  - "A versão oficial da regra é `rn_05_mei_estabelecimento_unico` (rfb regras)."
variacoes:
  - "Por UF: junte o município e agrupe pela UF."
resposta_esperada_fixtures:
  colunas: [nao_baixados, empresas_mei]
  linhas:
    - [0, 1]
    - [2, 1]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

with por_empresa as (
  select
    cnpj_raiz,
    count(*) filter (where situacao_codigo != 8) as nao_baixados
  from {{ ref('int_estabelecimentos__enriquecidos') }}
  where opcao_mei
  group by cnpj_raiz
)

select
  nao_baixados,
  count(*) as empresas_mei
from por_empresa
group by nao_baixados
order by nao_baixados
