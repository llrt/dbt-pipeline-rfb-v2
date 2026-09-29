{% macro data_rfb(coluna) -%}
try_strptime(nullif(trim({{ coluna }}), '0'), '%Y%m%d')::date
{%- endmacro %}
