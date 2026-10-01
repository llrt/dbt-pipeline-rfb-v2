{% macro data_rfb(coluna) -%}
try_strptime(trim({{ coluna }}), '%Y%m%d')::date
{%- endmacro %}
