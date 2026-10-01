{#- Consulta de CNPJs inválidos em `relacao` (nome de tabela, view ou CTE com a coluna `coluna`, não
    nula): valida os dois dígitos verificadores (módulo 11, pesos 5,4,3,2,9,8,7,6,5,4,3,2 e
    6,5,4,3,2,9,8,7,6,5,4,3,2). Aceita o CNPJ alfanumérico (valor de cada caractere = código ASCII −
    48). Formato fora de `[0-9A-Z]{14}` também é inválido. Separada do teste genérico para que o
    singular `cnpj_dv_valido_casos` a exercite com valores conhecidos (R3-09). -#}
{% macro cnpj_dv_invalidos(relacao, coluna) %}
with base as (
  select {{ coluna }} as cnpj
  from {{ relacao }}
),

digitos as (
  select
    cnpj,
    list_transform(range(1, 15), i -> ascii(substr(cnpj, i, 1)) - 48) as d
  from base
  where regexp_matches(cnpj, '^[0-9A-Z]{14}$')
),

calculo as (
  select
    cnpj,
    d,
    list_sum(list_transform(range(1, 13), i -> d[i] * [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2][i])) % 11 as resto_1,
    list_sum(list_transform(range(1, 14), i -> d[i] * [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2][i])) % 11 as resto_2
  from digitos
)

select cnpj
from base
where not regexp_matches(cnpj, '^[0-9A-Z]{14}$')

union all

select cnpj
from calculo
where
  d[13] != case when resto_1 < 2 then 0 else 11 - resto_1 end
  or d[14] != case when resto_2 < 2 then 0 else 11 - resto_2 end
{% endmacro %}

{#- Teste genérico (DQ-01): retorna os CNPJs inválidos (use com `severity: warn` e
    `store_failures: true`).
    Limiar: o teste falha com erro (em vez de warn) quando a fração de inválidos entre os não nulos
    passa de `limiar_erro` (padrão 0,001 = 0,1%) E há mais de `minimo_falhas_erro` inválidos (piso
    absoluto, como na regra de `idade_atual`: amostras minúsculas, como as fixtures, só avisam).
    Feito aqui porque `error_if` do dbt só aceita limites absolutos. Uma passada só (R3-17): os
    CNPJs inválidos e o total saem de CTEs materializadas, e o erro é levantado pelo próprio
    DuckDB (`error()`), sem `run_query` prévio. `limiar_erro=none` desliga o erro. -#}
{% test cnpj_dv_valido(model, column_name, limiar_erro=0.001, minimo_falhas_erro=100) %}
with base as materialized (
  select {{ column_name }} as cnpj
  from {{ model }}
  where {{ column_name }} is not null
),

invalidos as materialized (
  {{ cnpj_dv_invalidos('base', 'cnpj') }}
)

select cnpj
from invalidos
{%- if limiar_erro is not none %}
where
  (
    select
      case
        when
          count(*) > {{ minimo_falhas_erro }}
          and count(*)::double / (select count(*) from base) > {{ limiar_erro }}
          then error(
            'cnpj_dv_valido: ' || count(*) || ' de ' || (select count(*) from base)
            || ' CNPJs inválidos em {{ column_name }} (> {{ limiar_erro * 100 }}%)'
          )
        else 1
      end
    from invalidos
  ) = 1
{%- endif %}
{% endtest %}
