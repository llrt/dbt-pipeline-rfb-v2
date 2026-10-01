{#- Datas posteriores a `data_referencia` (ADR-0004): uma linha por valor futuro de `coluna` em
    `relacao` (tabela, view ou CTE); nulos são ignorados. `data_referencia` vem da macro de mesmo
    nome (var ou `_data_referencia` do mês selecionado das fontes). Separada do teste genérico para
    que o singular `data_nao_futura_casos` a exercite com valores conhecidos (R3-09). -#}
{% macro datas_futuras(relacao, coluna) %}
select {{ coluna }} as valor
from {{ relacao }}
where {{ coluna }} > {{ data_referencia() }}
{% endmacro %}

{#- Teste genérico (DQ-01): datas posteriores a `data_referencia`. Não se aplica às colunas de
    exclusão do Simples/MEI, que podem ter efeito futuro legítimo (R3-11). -#}
{% test data_nao_futura(model, column_name) %}
{{ datas_futuras(model, column_name) }}
{% endtest %}
