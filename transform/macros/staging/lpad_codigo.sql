{#- lpad do DuckDB TRUNCA valores maiores que o tamanho; aqui código maior fica intacto (o teste
    `tamanho_exato` o acusa) em vez de virar silenciosamente outro código. -#}
{% macro lpad_codigo(coluna, tamanho) -%}
case
  when length({{ texto_ou_nulo(coluna) }}) > {{ tamanho }} then {{ texto_ou_nulo(coluna) }}
  else lpad({{ texto_ou_nulo(coluna) }}, {{ tamanho }}, '0')
end
{%- endmacro %}
