{#- Uma linha por `cnpj_raiz` e mês nas Empresas da RFB (achado do B8, extrato real 2026-09: o
    `Empresas2.zip` traz o CNPJ raiz 08314885 duas vezes, a linha boa e uma "fantasma" sem razão
    social, natureza 0000, porte e qualificação zerados). Sem isso cada estabelecimento da raiz sairia
    duplicado nos joins (51 em 2026-09). Regra determinística sobre as colunas RAW: prefere a linha com
    razão social, depois com natureza informada (≠ 0000), depois o menor `natureza_jur`/razão social,
    capital, porte, qualificação e ente federativo: desempate total sobre as colunas da fonte (R4-05),
    então a escolha não depende da ordem de leitura. Usada no staging e na leitura da paridade (`audit__bh_empresas_sql_original`), que
    emula a mesma adaptação (como o trim do ADR-0005). Retorna o predicado de um `QUALIFY`. -#}
{% macro empresa_preferida_por_raiz() -%}
row_number() over (
    partition by cnpj_raiz, _mes_referencia
    order by
      nullif(trim(razao_social), '') is null,
      coalesce(try_cast(natureza_jur as integer), 0) = 0,
      natureza_jur,
      razao_social,
      capital_soc,
      porte,
      qualificacao_resp,
      ente_fed_resp
  ) = 1
{%- endmacro %}
