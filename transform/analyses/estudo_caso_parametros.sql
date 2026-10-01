{{ config(tags=['escopo_adicao'], meta={'escopo': 'adicao'}) }}

-- Parâmetros do caso (vars `caso_*` e `raio_fornecedores_km`), mais o mês e a data de referência
-- do extrato analisado. Lido por `rfb relatorio` para titular o relatório.
select
  '{{ var("caso_cnae_alvo") }}' as cnae_alvo,
  '{{ var("caso_municipio") }}' as municipio,
  '{{ var("caso_uf") }}' as uf,
  '{{ var("caso_cnaes_fornecedores") | join(", ") }}' as cnaes_fornecedores,
  {{ var('raio_fornecedores_km') }} as raio_fornecedores_km,
  max(_mes_referencia) as mes_referencia,
  max(_data_referencia) as data_referencia
from {{ ref('stg_rfb__estabelecimentos') }}
