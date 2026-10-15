{# ---
id: gq_staging__situacao_cadastral__01
conceito: situacao_cadastral
camada: staging
perguntas:
  - "Por que os estabelecimentos fecharam? Qual o motivo da situação cadastral?"
  - "Quantos estabelecimentos baixados há por motivo?"
intencao: "Auditoria do staging: situação cadastral × motivo (com a descrição do domínio de motivos), que não chega ao gold."
tabelas: [stg_rfb__estabelecimentos, stg_rfb__motivos]
colunas_chave: [situacao_codigo, motivo_situacao_codigo]
armadilhas:
  - "O motivo só existe no staging; o gold tem só a situação (dim_situacao_cadastral)."
  - "Ativa tem o motivo 00 (SEM MOTIVO). 'Ativa' não quer dizer 'em operação' (IN 2.119, art. 9º, parágrafo único)."
  - "Encerramento no projeto é todo não ativo (nula, suspensa, inapta ou baixada), não só a baixa."
variacoes:
  - "Só baixadas: `where est.situacao_codigo = 8`."
resposta_esperada_fixtures:
  colunas: [situacao_codigo, motivo_situacao_codigo, descricao_motivo, estabelecimentos]
  linhas:
    - [2, '00', SEM MOTIVO, 11]
    - [4, '01', EXTINCAO POR ENCERRAMENTO LIQUIDACAO VOLUNTARIA, 1]
    - [8, '01', EXTINCAO POR ENCERRAMENTO LIQUIDACAO VOLUNTARIA, 6]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  est.situacao_codigo,
  est.motivo_situacao_codigo,
  mot.descricao as descricao_motivo,
  count(*) as estabelecimentos
from {{ ref('stg_rfb__estabelecimentos') }} as est
left join {{ ref('stg_rfb__motivos') }} as mot
  on est.motivo_situacao_codigo = mot.codigo
group by est.situacao_codigo, est.motivo_situacao_codigo, mot.descricao
order by est.situacao_codigo, est.motivo_situacao_codigo
