{#- Observabilidade de DQ (DQ-02). `criar_historico_testes` (on-run-start) garante a tabela persistente
    `main.dq_historico_testes` no warehouse; `registrar_resultados_testes` (on-run-end) acrescenta uma
    linha por teste executado (dados e unitários) com invocation_id, nome, status, falhas, severidade,
    escopo e timestamp. O histórico acumula enquanto o `warehouse.duckdb` existir (o `make ci` recria
    o warehouse a cada execução; o ambiente real mantém o arquivo). -#}
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
    {{ log('dq_historico_testes: ' ~ (linhas | length) ~ ' resultados registrados', info=True) }}
  {%- endif -%}
{%- endif -%}
{%- endmacro %}
