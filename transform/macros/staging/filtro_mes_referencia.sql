{% macro filtro_mes_referencia(relacao) -%}
{%- set mes = var('mes_referencia', none) -%}
{%- if mes is not none -%}
_mes_referencia = '{{ mes }}'
{%- else -%}
_mes_referencia = (select max(_mes_referencia) from {{ relacao }})
{%- endif -%}
{%- endmacro %}
