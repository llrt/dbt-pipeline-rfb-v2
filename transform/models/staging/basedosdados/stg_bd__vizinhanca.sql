-- incremento: enriquecimento_bd (ADR-0015)
-- Pares de municípios vizinhos como publicados (um sentido, possivelmente duplicados e com
-- autopares em anos antigos); a seleção do ano mais recente e a simetria ficam em `int_`.
select
  ano::int as ano,
  {{ texto_ou_nulo('id_municipio_1') }} as id_municipio_1,
  {{ texto_ou_nulo('id_municipio_2') }} as id_municipio_2
from {{ source('basedosdados', 'vizinhanca_municipio') }}
