{# ---
id: gq_raw__data_calendario__01
conceito: data_calendario
camada: raw
perguntas:
  - "Que meses de extrato da RFB já foram ingeridos?"
  - "Qual a data de referência de cada extrato?"
intencao: "Auditoria do raw: os meses ingeridos e a data de referência (data do extrato) de cada um."
tabelas: [rfb.estabelecimentos]
colunas_chave: [_mes_referencia, _data_referencia]
armadilhas:
  - "`_data_referencia` é a data do extrato da RFB, não `now()` nem `current_date`: idades e prazos usam ela (ADR-0004)."
  - "O mês ingerido no raw pode ser mais novo que o gold (backfill) ou mais velho: o mês do gold está em gq_staging__data_calendario__01."
variacoes:
  - "Outra entidade: troque a fonte (`empresas`, `simples`)."
resposta_esperada_fixtures:
  colunas: [_mes_referencia, data_referencia]
  linhas:
    - [2026-08, '2026-08-10']
    - [2026-09, '2026-09-12']
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  _mes_referencia,
  max(_data_referencia) as data_referencia
from {{ source('rfb', 'estabelecimentos') }}
group by _mes_referencia
order by _mes_referencia
