{{ config(
    severity='warn',
    store_failures=true,
    tags=['escopo_adicao'],
    meta={'escopo': 'adicao'}
) }}

-- R3-18: as chaves de TODAS as partições de `fct_resumo_mensal` existem nas dimensões atuais. Uma
-- partição antiga pode ficar órfã quando uma dimensão muda (município novo/removido na Base dos
-- Dados); é aviso, e a correção é reprocessar o mês. Retorna uma linha por (mês, chave) órfã.
{{ resumo_chaves_orfas(false) }}
