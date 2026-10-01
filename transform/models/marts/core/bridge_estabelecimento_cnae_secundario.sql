-- Bridge muitos-para-muitos (ADR-0013): CNAEs secundários de cada estabelecimento. FKs para
-- `fct_estabelecimentos` (`cnpj_completo`) e `dim_cnae` (`sk_cnae`; -1 quando o CNAE secundário não
-- tem par na Base dos Dados). Opcional no BI; `codigo_cnae_secundario` guarda o código original.
select
  exp.cnpj_completo,
  coalesce(cnae.sk_cnae, -1) as sk_cnae,
  exp.codigo_cnae_secundario
from {{ ref('int_cnaes_secundarios__explodidos') }} as exp
left join {{ ref('dim_cnae') }} as cnae
  on exp.codigo_cnae_secundario = cnae.codigo_subclasse
