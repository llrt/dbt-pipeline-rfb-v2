{% macro lpad_codigo(coluna, tamanho) -%}
lpad({{ texto_ou_nulo(coluna) }}, {{ tamanho }}, '0')
{%- endmacro %}
