{% macro texto_ou_nulo(coluna) -%}
nullif(trim({{ coluna }}), '')
{%- endmacro %}
