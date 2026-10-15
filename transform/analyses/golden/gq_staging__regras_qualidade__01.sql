{# ---
id: gq_staging__regras_qualidade__01
conceito: regras_qualidade
camada: staging
perguntas:
  - "Há datas inválidas ou futuras no cadastro?"
  - "Quantos estabelecimentos têm data de início anterior a 1900 ou sem data?"
intencao: "Qualidade das datas no staging: início de atividade e data da situação ausentes, anteriores a 1900 ou depois do dia seguinte à data de referência (RN-13)."
tabelas: [stg_rfb__estabelecimentos]
colunas_chave: [dat_inicio_atividade, dat_situacao, _data_referencia]
armadilhas:
  - "No gold, data ausente vira `sk_data` -1 e data anterior a 1900 vira -2: nenhuma das duas gera evento nem coorte."
  - "O limite da data futura é o dia seguinte à data de referência, não `now()`."
  - "O relatório completo das regras é `rfb regras` (docs/RELATORIO_REGRAS_NEGOCIO.md); esta consulta é ad hoc."
variacoes:
  - "Só a data da situação: troque o campo das contagens."
resposta_esperada_fixtures:
  colunas: [estabelecimentos, inicio_ausente, inicio_antes_de_1900, situacao_sem_data, situacao_futura]
  linhas:
    - [18, 1, 0, 2, 0]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  count(*) as estabelecimentos,
  count(*) filter (where dat_inicio_atividade is null) as inicio_ausente,
  count(*) filter (where dat_inicio_atividade < date '1900-01-01') as inicio_antes_de_1900,
  count(*) filter (where dat_situacao is null) as situacao_sem_data,
  count(*) filter (
    where dat_situacao > _data_referencia + interval 1 day
  ) as situacao_futura
from {{ ref('stg_rfb__estabelecimentos') }}
order by estabelecimentos
