{{ config(tags=['escopo_adicao'], meta={'escopo': 'adicao'}) }}

-- RN-07 (docs/REGRAS_NEGOCIO.md): o MEI é modalidade de microempresa (LC 123, art. 18-E, § 3º);
-- no cadastro, o porte declarado da empresa MEI é 01 (MICRO). Grão: empresa MEI presente no
-- arquivo Empresas, por porte declarado.
select
  'RN-07' as regra,
  coalesce(por.rotulo, 'NÃO INFORMADO') as porte,
  count(*) as avaliados,
  count(*) filter (where emp.porte_codigo is distinct from 1) as violacoes
from {{ ref('stg_rfb__simples') }} as sim
inner join {{ ref('stg_rfb__empresas') }} as emp
  on sim.cnpj_raiz = emp.cnpj_raiz
left join {{ ref('dominio_porte') }} as por
  on emp.porte_codigo = por.codigo
where sim.opcao_mei
group by all
order by porte
