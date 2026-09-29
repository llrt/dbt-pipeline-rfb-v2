{% test tamanho_exato(model, column_name, tamanho) %}
-- Códigos com tamanho diferente de `tamanho` (não nulos): o `lpad` não pode mascarar truncamento.
select {{ column_name }} as valor
from {{ model }}
where {{ column_name }} is not null
  and length({{ column_name }}) != {{ tamanho }}
{% endtest %}
