{{ config(
    severity='error',
    tags=['escopo_adicao'],
    meta={'escopo': 'adicao'}
) }}

-- CASE-01 / ANA-04 (R3-15): `caso_municipio` + `caso_uf` devem resolver para exatamente 1 município em
-- `dim_municipio`. Sem isso (erro de digitação, homônimo na mesma UF) o mart de fornecedores e a
-- analysis q4 saem vazios ou duplicados e nenhum outro teste acusa. Retorna uma linha se != 1.
select
  '{{ var("caso_municipio") }}' as caso_municipio,
  '{{ var("caso_uf") }}' as caso_uf,
  count(*) as municipios_encontrados
from {{ ref('dim_municipio') }}
where upper(nome_municipio) = upper('{{ var("caso_municipio") }}') and sigla_uf = '{{ var("caso_uf") }}'
having count(*) != 1
