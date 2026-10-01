{{ config(
    severity='error',
    tags=['escopo_adicao'],
    meta={'escopo': 'adicao'}
) }}

-- R3-18 / BI-02: toda chave da partição do mês processado existe na dimensão correspondente.
-- Só o mês processado: as partições antigas dependem das dimensões do mês em que foram gravadas
-- (ver `fct_resumo_mensal_integridade_historica`). Retorna uma linha por (mês, chave) órfã.
{{ resumo_chaves_orfas(true) }}
