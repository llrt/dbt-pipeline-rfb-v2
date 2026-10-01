{#- Raiz do gold "real" (`RAIZ_DADOS/gold`, local ou `s3://`), independente do `external_root` do
    target. O `rfb pipeline` faz backfill de mês antigo com `RFB_EXTERNAL_ROOT` temporário (P22): os
    externals de apoio vão para lá, mas o que precisa sobreviver — a partição de `fct_resumo_mensal` e
    o histórico de DQ (RBP-12) — usa esta raiz. -#}
{% macro raiz_gold() -%}
{{ env_var('RAIZ_DADOS', '../dados') }}/gold
{%- endmacro %}
