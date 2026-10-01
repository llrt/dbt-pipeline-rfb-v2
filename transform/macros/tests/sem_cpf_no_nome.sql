{#- Teste genérico (ADR-0008, emenda R4-01): retorna os valores da coluna que ainda trazem um CPF, isto
    é, um trecho de exatamente 11 dígitos (sem dígito colado) cujos dois dígitos verificadores de CPF
    batem (módulo 11, pesos 10..2 e 11..2). Guarda do `mascarar_cpf_no_nome`: se a máscara for
    desligada ou deixar escapar um formato, o build para (`severity: error`). O filtro por
    `[0-9]{11}` antes do `unnest` mantém o custo baixo (só nomes com 11+ dígitos seguidos). -#}
{% test sem_cpf_no_nome(model, column_name) %}
with candidatos as (
  select {{ column_name }} as nome
  from {{ model }}
  where regexp_matches({{ column_name }}, '[0-9]{11}')
),

trechos as (
  select
    nome,
    unnest(regexp_extract_all(nome, '[0-9]+')) as trecho
  from candidatos
),

digitos as (
  select
    nome,
    trecho,
    list_transform(range(1, 12), i -> ascii(substr(trecho, i, 1)) - 48) as d
  from trechos
  where length(trecho) = 11
)

-- a falha não repete o CPF (o `store_failures` gravaria o dado que o teste quer barrar)
select replace(nome, trecho, '<cpf>') as nome_com_cpf
from digitos
where
  d[10] = (list_sum(list_transform(range(1, 10), i -> d[i] * (11 - i))) * 10 % 11) % 10
  and d[11] = (list_sum(list_transform(range(1, 11), i -> d[i] * (12 - i))) * 10 % 11) % 10
{% endtest %}
