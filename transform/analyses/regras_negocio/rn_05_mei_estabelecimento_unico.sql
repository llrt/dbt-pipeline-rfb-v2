{{ config(tags=['escopo_adicao'], meta={'escopo': 'adicao'}) }}

-- RN-05 (docs/referencia/regras-negocio.md): a empresa optante pelo MEI tem um único estabelecimento (LC 123,
-- art. 18-A, § 4º, II). Grão: empresa (CNPJ básico) com opção pelo MEI no arquivo Simples. Viola
-- quem tem mais de um estabelecimento não baixado de situação conhecida (RRN-03): o baixado continua
-- no extrato, mas não é mais estabelecimento da empresa. A quebra mostra à parte, sem violação, quem
-- tem estabelecimentos baixados além do único não baixado e quem só teria mais de um não baixado se
-- os de situação nula (vazia ou ilegível no extrato) contassem: esses ficam "indeterminado", para a
-- falta de informação não parecer cadastro limpo.
with mei as (
  select cnpj_raiz
  from {{ ref('stg_rfb__simples') }}
  where opcao_mei
),

por_empresa as (
  select
    cnpj_raiz,
    count(*) as qtd,
    count(*) filter (where situacao_codigo != 8) as qtd_nao_baixados,
    count(*) filter (where situacao_codigo is null) as qtd_desconhecidos
  from {{ ref('int_estabelecimentos__enriquecidos') }}
  group by cnpj_raiz
),

base as (
  select
    case
      when emp.qtd is null then 'nenhum no extrato'
      when emp.qtd = 1 then 'um'
      when emp.qtd_nao_baixados > 1 then 'mais de um não baixado'
      when emp.qtd_nao_baixados + emp.qtd_desconhecidos > 1
        then 'indeterminado (situação desconhecida)'
      else 'mais de um, no máximo um não baixado'
    end as estabelecimentos,
    coalesce(emp.qtd_nao_baixados > 1, false) as viola
  from mei
  left join por_empresa as emp
    on mei.cnpj_raiz = emp.cnpj_raiz
)

select
  'RN-05' as regra,
  estabelecimentos,
  count(*) as avaliados,
  count(*) filter (where viola) as violacoes
from base
group by all
order by estabelecimentos
