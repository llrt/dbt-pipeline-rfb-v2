-- incremento: enriquecimento_ibge (ADR-0022). Para onde os moradores de cada município vão comprar
-- (REGIC 2018), em tabela longa: grão = origem × destino × tema, nos temas de compra
-- `vestuario_calcados` (Q1) e `moveis_eletro` (Q2), só ligações com % > 0. `posto` 1 é o principal
-- destino listado da origem no tema (empate: menor código IBGE). O destino "Outros" (lugares não
-- listados) vira uma linha com `sk_municipio_destino` = -1 e `eh_outros`, sem posto, para a soma por
-- origem e tema bater ~100. Origem fora de `dim_municipio` fica de fora; destino listado fora dela
-- (município extinto ou renomeado na malha) também vai para -1, com `eh_outros` false.
select
  ori.sk_municipio as sk_municipio_origem,
  coalesce(des.sk_municipio, -1) as sk_municipio_destino,
  lig.eh_outros,
  lig.tema,
  lig.pct,
  lig.posto
from {{ ref('int_regic__destinos_compras') }} as lig
inner join {{ ref('dim_municipio') }} as ori
  on lig.id_municipio_origem = ori.id_municipio_ibge
left join {{ ref('dim_municipio') }} as des
  on lig.id_municipio_destino = des.id_municipio_ibge
