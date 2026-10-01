{#- Emula o `inferSchema=True` do Spark (notebook 1) para uma coluna de código na paridade: o Spark
    tipa a coluna como inteiro só se TODOS os valores lidos forem inteiros; um único valor não numérico
    a deixa como texto. O extrato real 2026-09 traz o 1º CNPJ alfanumérico (`cnpj_ordem` = 'E08G'):
    um `try_cast` fixo viraria NULL e divergiria do que o Spark faria (B8). Devolve texto nos dois
    casos — o inteiro sem zeros à esquerda (como o Spark o leria) ou o valor original — para que joins
    e `lpad` se comportem igual ao original. `relacao` deve ser a fonte já filtrada pelo mês. -#}
{% macro inferschema_inteiro_ou_texto(coluna, relacao, filtro) -%}
case
  when (
    select coalesce(bool_and(try_cast({{ coluna }} as bigint) is not null), true)
    from {{ relacao }}
    where {{ filtro }} and {{ coluna }} is not null
  )
    then try_cast({{ coluna }} as bigint)::varchar
  else {{ coluna }}
end
{%- endmacro %}
