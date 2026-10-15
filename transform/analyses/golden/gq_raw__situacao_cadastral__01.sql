{# ---
id: gq_raw__situacao_cadastral__01
conceito: situacao_cadastral
camada: raw
perguntas:
  - "Que códigos de situação cadastral a RFB publicou em cada mês?"
  - "Confira no raw quantas inscrições vieram ativas (código 02) e baixadas (08)."
intencao: "Auditoria do raw: códigos de SITUAÇÃO CADASTRAL por mês, como publicados (01 nula, 02 ativa, 03 suspensa, 04 inapta, 08 baixada)."
tabelas: [rfb.estabelecimentos]
colunas_chave: [_mes_referencia, situacao]
armadilhas:
  - "Camada de auditoria: para ativos use `eh_ativa` no gold (gq_core__situacao_cadastral__01) ou a métrica `qtd_ativos`."
  - "O código é texto com zero à esquerda ('02'); no gold vira inteiro (2) e rótulo (ATIVA)."
  - "Comparar meses no raw mostra a variação líquida do estoque, não quem entrou e quem saiu."
variacoes:
  - "Só um mês: `where _mes_referencia = '2026-09'`."
  - "Com o motivo publicado: acrescente `mot_situacao`."
resposta_esperada_fixtures:
  colunas: [_mes_referencia, situacao, linhas]
  linhas:
    - [2026-08, '02', 10]
    - [2026-08, '03', 1]
    - [2026-08, '04', 1]
    - [2026-08, 08, 5]
    - [2026-09, '02', 11]
    - [2026-09, '04', 1]
    - [2026-09, 08, 6]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  _mes_referencia,
  situacao,
  count(*) as linhas
from {{ source('rfb', 'estabelecimentos') }}
group by _mes_referencia, situacao
order by _mes_referencia, situacao
