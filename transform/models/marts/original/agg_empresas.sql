-- Flat table agregada do notebook 3 (ADR-0005): `group by` das 10 dimensões de `bh_empresas`;
-- `qtd_empresas` = contagem de CNPJs completos e `media_idade` = média simples de `idade_atual`
-- (NULL para estratos só de INATIVAS, pois `idade_atual` só existe para ATIVA).
select
  municipio,
  microrregiao_municipio,
  mesorregiao_municipio,
  uf,
  cnae_principal,
  desc_cnae_principal,
  grupo_cnae_principal,
  natureza_juridica,
  porte,
  situacao,
  count(cnpj_completo) as qtd_empresas,
  avg(idade_atual) as media_idade
from {{ ref('bh_empresas') }}
group by
  municipio,
  microrregiao_municipio,
  mesorregiao_municipio,
  uf,
  cnae_principal,
  desc_cnae_principal,
  grupo_cnae_principal,
  natureza_juridica,
  porte,
  situacao
