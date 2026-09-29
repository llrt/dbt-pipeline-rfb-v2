{#- Valor monetário no formato RFB (vírgula decimal, sem separador de milhar): `1000,50` -> 1000.50.
    Inválido ou vazio -> NULL (`try_cast`). -#}
{% macro decimal_rfb(coluna) -%}
try_cast(replace({{ texto_ou_nulo(coluna) }}, ',', '.') as decimal(18, 2))
{%- endmacro %}
