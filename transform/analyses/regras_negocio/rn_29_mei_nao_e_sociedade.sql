{{ config(tags=['escopo_adicao'], meta={'escopo': 'adicao'}) }}

-- RN-29 (docs/referencia/regras-negocio.md): o MEI é empresário individual ou empreendedor, nunca sociedade
-- (LC 123, art. 18-A, § 1º, redação da LC 188/2021). Naturezas de sociedade: as da tabela CONCLA
-- de 2021 cujo nome é "Sociedade ..." (o consórcio e o grupo de sociedades e o estabelecimento de
-- sociedade estrangeira não são, eles mesmos, sociedades). Grão: empresa MEI presente no arquivo
-- Empresas, por natureza jurídica.
select
  'RN-29' as regra,
  coalesce(emp.natureza_juridica_codigo, '—') || ' '
  || coalesce(nat.descricao, '(fora do domínio)') as natureza_juridica,
  count(*) as avaliados,
  count(*) filter (
    where emp.natureza_juridica_codigo in (
      '2038', '2046', '2054', '2062', '2070', '2089', '2097', '2127', '2232', '2240', '2259',
      '2267', '2321'
    )
  ) as violacoes
from {{ ref('stg_rfb__simples') }} as sim
inner join {{ ref('stg_rfb__empresas') }} as emp
  on sim.cnpj_raiz = emp.cnpj_raiz
left join {{ ref('stg_rfb__naturezas') }} as nat
  on emp.natureza_juridica_codigo = nat.codigo
where sim.opcao_mei
group by all
order by natureza_juridica
