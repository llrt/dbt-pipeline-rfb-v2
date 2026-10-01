{#- Observabilidade de DQ (DQ-02). `criar_historico_testes` (on-run-start) garante a tabela persistente
    `main.dq_historico_testes` no warehouse; `registrar_resultados_testes` (on-run-end) acrescenta uma
    linha por teste executado (dados e unitários) com invocation_id, nome, status, falhas, severidade,
    escopo e timestamp. O histórico acumula enquanto o `warehouse.duckdb` existir (o `make ci` recria
    o warehouse a cada execução; o ambiente real mantém o arquivo). `exportar_historico_testes` copia
    as linhas da execução para `gold/dq_historico_testes/invocation_id=<id>/` (Parquet), que sobrevive
    ao descarte do warehouse (RBP-12). -#}
{% macro criar_historico_testes() -%}
{%- if execute -%}
  {%- do run_query('create schema if not exists main') -%}
  {%- do run_query(
    'create table if not exists main.dq_historico_testes ('
    ~ 'invocation_id varchar, executado_em timestamp, nome_teste varchar, tipo_teste varchar, '
    ~ 'status varchar, falhas bigint, severidade varchar, escopo varchar)'
  ) -%}
{%- endif -%}
{%- endmacro %}

{% macro registrar_resultados_testes(resultados) -%}
{%- if execute -%}
  {%- set linhas = [] -%}
  {%- for r in resultados if r.node.resource_type in ('test', 'unit_test') -%}
    {%- set meta = r.node.config.meta or r.node.meta or {} -%}
    {%- set severidade = r.node.config.severity if r.node.resource_type == 'test' else 'error' -%}
    {%- do linhas.append(
      "('" ~ invocation_id ~ "', current_timestamp::timestamp, '"
      ~ (r.node.name | replace("'", "''")) ~ "', '" ~ r.node.resource_type ~ "', '"
      ~ (r.status | string | lower) ~ "', " ~ (r.failures if r.failures is not none else 'null') ~ ", '"
      ~ ((severidade or 'error') | lower) ~ "', '" ~ (meta.get('escopo', 'indefinido')) ~ "')"
    ) -%}
  {%- endfor -%}
  {%- if linhas | length > 0 -%}
    {%- do run_query('insert into main.dq_historico_testes values ' ~ linhas | join(', ')) -%}
    {%- do exportar_historico_testes() -%}
    {{ log('dq_historico_testes: ' ~ (linhas | length) ~ ' resultados registrados', info=True) }}
  {%- endif -%}
{%- endif -%}
{%- endmacro %}

{#- RBP-12: uma partição Parquet por execução em `<raiz_gold>/dq_historico_testes/` (append por
    `invocation_id`; reexecutar a mesma invocação substitui a partição). Usa `raiz_gold()`, não o
    `external_root`, para valer também no backfill (P22). O COPY particionado cria só o diretório de
    destino, não os pais: o primeiro COPY (vazio, particionado) garante `gold/` sem gravar arquivo. -#}
{% macro exportar_historico_testes() -%}
  {%- set gold = raiz_gold() -%}
  {%- do run_query(
    "copy (select 1 as p, 1 as q where false) to '" ~ gold ~ "' "
    ~ "(format parquet, partition_by (p), overwrite_or_ignore true)"
  ) -%}
  {%- do run_query(
    "copy (select * from main.dq_historico_testes where invocation_id = '" ~ invocation_id ~ "') "
    ~ "to '" ~ gold ~ "/dq_historico_testes' "
    ~ "(format parquet, partition_by (invocation_id), overwrite_or_ignore true)"
  ) -%}
{%- endmacro %}
