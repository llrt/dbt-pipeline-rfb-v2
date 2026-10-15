{{ config(tags=['escopo_adicao'], meta={'escopo': 'adicao'}) }}

-- RN-24 (docs/referencia/regras-negocio.md): grãos declarados e sem teste (RDIC-09) nas fontes e no seed de
-- exceções. Por tabela: avaliados = linhas; violações = linhas excedentes (linhas − chaves
-- distintas). A vizinhança é avaliada como publicada: o grão declarado admite par repetido. As
-- fontes RFB guardam todos os meses ingeridos: países e qualificações são lidos só no mês do
-- relatório (o de `int_estabelecimentos__enriquecidos`, como nas demais regras), para que um
-- duplicado de um mês antigo não conte e apagar meses antigos não mude o total. As demais tabelas
-- não têm mês: a Base dos Dados e o seed são uma versão só, e o histórico de testes é, por
-- desenho, um acúmulo de execuções.
with mes_relatorio as (
  select max(_mes_referencia) as mes
  from {{ ref('int_estabelecimentos__enriquecidos') }}
),

paises as (
  select
    codigo,
    _mes_referencia,
    count(*) as linhas
  from {{ source('rfb', 'paises') }}
  where _mes_referencia = (select mes_relatorio.mes from mes_relatorio)
  group by all
),

qualificacoes as (
  select
    codigo,
    _mes_referencia,
    count(*) as linhas
  from {{ source('rfb', 'qualificacoes') }}
  where _mes_referencia = (select mes_relatorio.mes from mes_relatorio)
  group by all
),

cnae_2 as (
  select
    subclasse,
    count(*) as linhas
  from {{ source('basedosdados', 'cnae_2') }}
  group by all
),

regiao_metropolitana as (
  select
    id_municipio,
    nome_regiao_metropolitana,
    count(*) as linhas
  from {{ source('basedosdados', 'regiao_metropolitana_2017') }}
  group by all
),

vizinhanca as (
  select
    ano,
    id_municipio_1,
    id_municipio_2,
    count(*) as linhas
  from {{ source('basedosdados', 'vizinhanca_municipio') }}
  group by all
),

excecoes as (
  select
    codigo,
    count(*) as linhas
  from {{ ref('excecoes_conhecidas_municipio') }}
  group by all
),

historico_testes as (
  select
    invocation_id,
    nome_teste,
    count(*) as linhas
  from {{ source('observabilidade', 'dq_historico_testes') }}
  group by all
)

select
  'RN-24' as regra,
  'rfb.paises' as tabela,
  coalesce(sum(linhas), 0) as avaliados,
  coalesce(sum(linhas - 1), 0) as violacoes
from paises

union all

select
  'RN-24' as regra,
  'rfb.qualificacoes' as tabela,
  coalesce(sum(linhas), 0) as avaliados,
  coalesce(sum(linhas - 1), 0) as violacoes
from qualificacoes

union all

select
  'RN-24' as regra,
  'basedosdados.cnae_2' as tabela,
  coalesce(sum(linhas), 0) as avaliados,
  coalesce(sum(linhas - 1), 0) as violacoes
from cnae_2

union all

select
  'RN-24' as regra,
  'basedosdados.regiao_metropolitana_2017' as tabela,
  coalesce(sum(linhas), 0) as avaliados,
  coalesce(sum(linhas - 1), 0) as violacoes
from regiao_metropolitana

union all

select
  'RN-24' as regra,
  'basedosdados.vizinhanca_municipio' as tabela,
  coalesce(sum(linhas), 0) as avaliados,
  coalesce(sum(linhas - 1), 0) as violacoes
from vizinhanca

union all

select
  'RN-24' as regra,
  'excecoes_conhecidas_municipio' as tabela,
  coalesce(sum(linhas), 0) as avaliados,
  coalesce(sum(linhas - 1), 0) as violacoes
from excecoes

union all

select
  'RN-24' as regra,
  'observabilidade.dq_historico_testes' as tabela,
  coalesce(sum(linhas), 0) as avaliados,
  coalesce(sum(linhas - 1), 0) as violacoes
from historico_testes
