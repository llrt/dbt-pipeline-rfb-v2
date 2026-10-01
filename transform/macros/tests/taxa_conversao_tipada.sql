{#- Teste genérico (RBP-02): perda de tipagem silenciosa. `try_strptime`/`try_cast` transformam lixo em
    NULL (correto por linha), mas uma deriva de formato do extrato zeraria a coluna inteira com o build
    verde. Mede, no mês selecionado, a proporção de valores raw não vazios (`coluna_raw` da fonte
    `grupo.entidade`) que não viraram valor tipado em `column_name` do modelo:
    `(não vazios no raw − não nulos no tipado) / não vazios no raw`.
    `sentinelas`: valores raw que são NULL por definição (ex.: data `00000000`), fora da conta.
    Retorna uma linha (aviso, com `severity: warn`) acima de `limiar_aviso` (padrão 0,1%) e levanta
    erro (`error()` do DuckDB, como `cnpj_dv_valido`) acima de `limiar_erro` (padrão 5%), porque
    `error_if` do dbt só aceita limites absolutos. Pressupõe staging 1:1 com a fonte (sem filtro de
    linhas além do mês); `uma_linha_por_raiz=true` aplica ao raw a mesma dedup de raiz do staging
    das Empresas (`empresa_preferida_por_raiz`, R4-05), senão a linha "fantasma" descartada contaria
    como perda. `limiar_erro=none` desliga o erro. -#}
{% test taxa_conversao_tipada(
  model, column_name, coluna_raw, entidade, grupo='rfb', sentinelas=[], limiar_aviso=0.001, limiar_erro=0.05,
  uma_linha_por_raiz=false
) %}
{%- set fonte = source(grupo, entidade) -%}
with fonte_mes as (
  select {{ coluna_raw }}
  from {{ fonte }}
  where {{ filtro_mes_referencia(fonte) }}
  {%- if uma_linha_por_raiz %}
  qualify {{ empresa_preferida_por_raiz() }}
  {%- endif %}
),

raw as (
  select count(*) as n
  from fonte_mes
  where
    {{ texto_ou_nulo(coluna_raw) }} is not null
    {%- if sentinelas %}
    and trim({{ coluna_raw }}) not in ({{ sentinelas | map('tojson') | join(', ') | replace('"', "'") }})
    {%- endif %}
),

tipado as (
  select count({{ column_name }}) as n
  from {{ model }}
),

taxa as (
  select
    raw.n as n_raw,
    tipado.n as n_tipado,
    (raw.n - tipado.n)::double / nullif(raw.n, 0) as perda
  from raw, tipado
)

select
  n_raw,
  n_tipado,
  perda
from taxa
where
  perda > {{ limiar_aviso }}
  {%- if limiar_erro is not none %}
  and case
    when perda > {{ limiar_erro }}
      then error(
        'taxa_conversao_tipada: {{ column_name }} perdeu ' || (n_raw - n_tipado) || ' de ' || n_raw
        || ' valores de {{ entidade }}.{{ coluna_raw }} (' || round(perda * 100, 2) || '% > {{ limiar_erro * 100 }}%)'
      )
    else true
  end
  {%- endif %}
{% endtest %}
