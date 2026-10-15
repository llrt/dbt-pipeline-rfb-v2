{# incremento: enriquecimento_ibge #}
{% macro valor_ibge(coluna, tipo) -%}
case
    when trim({{ coluna }}) = '-' then 0::{{ tipo }}
    when nullif(trim({{ coluna }}), '') is null or trim({{ coluna }}) in ('X', '..', '...') then null
    else trim({{ coluna }})::{{ tipo }}
end
{%- endmacro %}
