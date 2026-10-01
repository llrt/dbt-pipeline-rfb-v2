{#- Teste genérico (DQ-01): datas posteriores a `data_referencia` (ADR-0004). Retorna uma linha por
    valor futuro; nulos são ignorados. `data_referencia` vem da macro de mesmo nome (var ou
    `_data_referencia` do mês selecionado das fontes). -#}
{% test data_nao_futura(model, column_name) %}
select {{ column_name }} as valor
from {{ model }}
where {{ column_name }} > {{ data_referencia() }}
{% endtest %}
