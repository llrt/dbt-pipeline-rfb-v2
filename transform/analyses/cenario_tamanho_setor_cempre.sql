{{ config(
    tags=['escopo_adicao', 'incremento_enriquecimento_ibge'],
    meta={'escopo': 'adicao', 'incremento': 'enriquecimento_ibge'}
) }}

-- Cenário 3 (docs/CENARIOS_DE_USO.md), incremento enriquecimento_ibge: tamanho real do setor. Para a
-- classe CNAE do caso (5 primeiros dígitos) nos municípios da UF: unidades locais, pessoal ocupado e
-- salário médio mensal aproximado do CEMPRE ao lado dos CNPJs ativos da RFB (com e sem MEI). O CEMPRE não
-- conta MEI e é de 31/12 do `ano_cempre`; a RFB é do mês do gold. Sigilo (`X`) nunca é imputado: fica NULL
-- e `tem_sigilo` true. Salário médio mensal ≈ salários ÷ assalariados em 31/12 ÷ 13 (o IBGE usa o pessoal
-- assalariado médio do ano, que não está na tabela municipal). Só agregados.
select
  municipio,
  classe_cnae,
  descricao_classe,
  ano_cempre,
  unidades_locais_cempre,
  pessoal_ocupado_cempre,
  pessoal_assalariado_cempre,
  round(salarios_mil_reais * 1000 / nullif(pessoal_assalariado_cempre, 0) / 13, 2)
    as salario_medio_mensal_aprox,
  pessoal_por_unidade,
  tem_sigilo,
  ativos_rfb,
  ativos_rfb_sem_mei,
  razao_unidades_cempre_ativos_rfb,
  mes_referencia_rfb
from {{ ref('mart_emprego_setor_municipio') }}
where uf = '{{ var("caso_uf") }}' and classe_cnae = '{{ var("caso_cnae_alvo")[:5] }}'
order by coalesce(unidades_locais_cempre, 0) desc, ativos_rfb desc, municipio
