{{ config(tags=['escopo_adicao'], meta={'escopo': 'adicao'}) }}

-- RN-06 (docs/referencia/regras-negocio.md): quem tem opção pelo MEI é optante pelo Simples Nacional (LC 123,
-- art. 18-A, § 1º). Grão: empresa (CNPJ básico) com opção pelo MEI no arquivo Simples.
select
  'RN-06' as regra,
  count(*) as avaliados,
  count(*) filter (where opcao_simples is distinct from true) as violacoes
from {{ ref('stg_rfb__simples') }}
where opcao_mei
