{# ---
id: gq_analytics__cempre_setor__02
conceito: cempre_setor
camada: analytics
perguntas:
  - "Quantas pessoas trabalham no comércio de tintas no ES inteiro?"
  - "Qual o total de pessoal ocupado da classe na UF, e quanto está em sigilo?"
intencao: "Totais de uma classe CNAE numa UF, com o número de células em sigilo que deixam a soma do pessoal subestimada."
tabelas: [mart_emprego_setor_municipio]
colunas_chave: [uf, classe_cnae, pessoal_ocupado_cempre, tem_sigilo]
armadilhas:
  - "Com sigilo, o total de pessoal é um PISO: diga 'pelo menos' e quantas células ficaram fora."
  - "Unidades locais nunca são sigilosas: a soma delas é completa."
variacoes:
  - "Brasil: agrupe por `uf`."
resposta_esperada_fixtures:
  colunas: [uf, classe_cnae, unidades_locais, pessoal_ocupado_sem_sigilo, celulas_com_sigilo, ativos_rfb_sem_mei]
  linhas:
    - [ES, '47415', 73, 360, 2, 0]
--- #}
{{ config(
    tags=['escopo_adicao', 'golden_query', 'incremento_enriquecimento_ibge'],
    meta={'escopo': 'adicao', 'incremento': 'enriquecimento_ibge'}
) }}

select
  uf,
  classe_cnae,
  sum(unidades_locais_cempre) as unidades_locais,
  sum(pessoal_ocupado_cempre) as pessoal_ocupado_sem_sigilo,
  count(*) filter (where tem_sigilo) as celulas_com_sigilo,
  sum(ativos_rfb_sem_mei) as ativos_rfb_sem_mei
from {{ ref('mart_emprego_setor_municipio') }}
where uf = 'ES' and classe_cnae = '47415'
group by uf, classe_cnae
order by uf
