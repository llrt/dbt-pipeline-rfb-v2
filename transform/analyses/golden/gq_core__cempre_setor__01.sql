{# ---
id: gq_core__cempre_setor__01
conceito: cempre_setor
camada: core
perguntas:
  - "Quantas pessoas trabalham em empresas formais em Fundão?"
  - "Quantas unidades locais o CEMPRE conta em cada município do ES?"
intencao: "O total do CEMPRE por município (todas as atividades): unidades locais e pessoal ocupado, com o ano do CEMPRE, ao lado dos ativos da RFB."
tabelas: [dim_municipio, fct_estabelecimentos]
colunas_chave: [sk_municipio, ano_cempre, unidades_locais_cempre, pessoal_ocupado_cempre]
armadilhas:
  - "Empresa × estabelecimento: o CEMPRE conta unidades locais (o equivalente a estabelecimentos), não empresas; o pessoal é o das unidades do município."
  - "O CEMPRE é de 31/12 do `ano_cempre` (hoje 2024); a RFB é do mês do extrato: anos diferentes."
  - "O CEMPRE não conta MEI e só conta quem tem sinal de atividade: ele é menor que os ativos da RFB."
  - "Pessoal ocupado inclui sócios e proprietários; não é só emprego com carteira."
variacoes:
  - "Por setor (classe CNAE): use mart_emprego_setor_municipio (gq_analytics__cempre_setor__01)."
  - "Outra UF: troque `sigla_uf`."
resposta_esperada_fixtures:
  colunas: [nome_municipio, ano_cempre, unidades_locais_cempre, pessoal_ocupado_cempre, ativos_rfb]
  linhas:
    - [Aracruz, 2024, 3900, 30500, 1]
    - [Fundão, 2024, 1054, 5125, 2]
    - [Linhares, 2024, 6200, 41000, 1]
    - [Serra, 2024, 16000, 160000, 3]
    - [Vitória, 2024, 21000, 290000, 1]
--- #}
{{ config(
    tags=['escopo_adicao', 'golden_query', 'incremento_enriquecimento_ibge'],
    meta={'escopo': 'adicao', 'incremento': 'enriquecimento_ibge'}
) }}

select
  mun.nome_municipio,
  mun.ano_cempre,
  mun.unidades_locais_cempre,
  mun.pessoal_ocupado_cempre,
  count(fct.cnpj_completo) filter (where fct.eh_ativa) as ativos_rfb
from {{ ref('dim_municipio') }} as mun
left join {{ ref('fct_estabelecimentos') }} as fct
  on mun.sk_municipio = fct.sk_municipio
where mun.sigla_uf = 'ES'
group by mun.nome_municipio, mun.ano_cempre, mun.unidades_locais_cempre, mun.pessoal_ocupado_cempre
order by mun.nome_municipio
