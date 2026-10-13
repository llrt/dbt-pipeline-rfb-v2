{{ config(tags=['escopo_adicao'], meta={'escopo': 'adicao'}) }}

-- RN-08 (docs/REGRAS_NEGOCIO.md): observação do projeto, não regra legal: a empresa MEI tem a
-- natureza jurídica 213-5 (Empresário Individual). Grão: empresa MEI presente no arquivo Empresas,
-- por natureza jurídica.
select
  'RN-08' as regra,
  coalesce(emp.natureza_juridica_codigo, '—') || ' '
  || coalesce(nat.descricao, '(fora do domínio)') as natureza_juridica,
  count(*) as avaliados,
  count(*) filter (where emp.natureza_juridica_codigo is distinct from '2135') as violacoes
from {{ ref('stg_rfb__simples') }} as sim
inner join {{ ref('stg_rfb__empresas') }} as emp
  on sim.cnpj_raiz = emp.cnpj_raiz
left join {{ ref('stg_rfb__naturezas') }} as nat
  on emp.natureza_juridica_codigo = nat.codigo
where sim.opcao_mei
group by all
order by natureza_juridica
