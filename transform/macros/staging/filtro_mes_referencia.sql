{% macro filtro_mes_referencia(relacao) -%}
{%- set mes = var('mes_referencia', none) -%}
{%- if mes is not none -%}
{%- if modules.re.match('^\\d{4}-\\d{2}$', mes | string) is none -%}
{{ exceptions.raise_compiler_error("var mes_referencia inválida: '" ~ mes ~ "' (formato esperado AAAA-MM)") }}
{%- endif -%}
_mes_referencia = '{{ mes }}'
{%- else -%}
_mes_referencia = (select max(_mes_referencia) from {{ relacao }})
{%- endif -%}
{%- endmacro %}
