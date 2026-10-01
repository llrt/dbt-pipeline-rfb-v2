{#- Mascara o CPF dentro de um nome exposto no gold (ADR-0008, emenda R4-01, decisão do usuário). A
    razão social do empresário individual e do MEI é "NOME + CPF": todo trecho de exatamente 11
    dígitos (sem dígito colado antes ou depois, com ou sem espaço) vira `***.***.***-**`. Não exige DV
    válido: um CPF digitado errado continua sendo dado pessoal. No gold real de 2026-09, 12,5 M nomes
    terminam em CPF e 908 o trazem no meio do nome; sequências de 12+ dígitos (CNPJ etc.) ficam
    como estão. Usada em `bh_empresas`, `mart_fornecedores_proximos` e no alinhamento final da
    paridade (`audit__bh_empresas_sql_original`).
    Duas passadas: a troca global consome o separador depois do trecho, então um segundo CPF colado
    só por um espaço ("… 52998224725 11144477735") só casa na segunda. -#}
{% macro mascarar_cpf_no_nome(coluna) -%}
{%- set padrao = "'(^|[^0-9])[0-9]{11}([^0-9]|$)', '\\1***.***.***-**\\2', 'g'" -%}
regexp_replace(regexp_replace({{ coluna }}, {{ padrao }}), {{ padrao }})
{%- endmacro %}
