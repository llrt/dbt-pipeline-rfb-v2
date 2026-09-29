{#- Data de referência determinística (ADR-0004), no lugar de `now()`/`current_date`:
    var `data_referencia` se definida; senão o `_data_referencia` do mês selecionado em `relacao`
    (padrão: estabelecimentos RFB filtrados por `filtro_mes_referencia`). Passe uma relação de
    staging já filtrada por mês para evitar reler a fonte. -#}
{% macro data_referencia(relacao=none) -%}
{%- set data = var('data_referencia', none) -%}
{%- if data is not none -%}
date '{{ data }}'
{%- elif relacao is not none -%}
(select max(_data_referencia) from {{ relacao }})
{%- else -%}
{%- set fonte = source('rfb', 'estabelecimentos') -%}
(select max(_data_referencia) from {{ fonte }} where {{ filtro_mes_referencia(fonte) }})
{%- endif -%}
{%- endmacro %}
