{# ---
id: gq_core__empresa_estabelecimento__02
conceito: empresa_estabelecimento
camada: core
perguntas:
  - "Quantas lojas de tinta tem em Fundão?"
  - "Quantos concorrentes de comércio de tintas existem em Fundão/ES, abertos e fechados?"
  - "Tem loja de material de pintura funcionando em Fundão?"
intencao: "Estabelecimentos de um CNAE principal (subclasse) num município, ativos e não ativos, no mês do gold."
tabelas: [fct_estabelecimentos, dim_cnae, dim_municipio]
colunas_chave: [sk_cnae, sk_municipio, eh_ativa, codigo_subclasse, nome_municipio, sigla_uf]
armadilhas:
  - "'Loja' é estabelecimento (CNPJ completo), não empresa: uma rede com filiais conta várias lojas."
  - "Filtre o município pelo nome E pela UF: há municípios homônimos (Água Branca em AL, PB e PI)."
  - "Só o CNAE principal: quem vende tintas como atividade secundária fica de fora (ver gq_core__cnae_secundario__01)."
  - "'Aberta' = ativa no cadastro, não prova que opera; o resultado é do mês do gold."
variacoes:
  - "Outro CNAE: troque `codigo_subclasse`; a classe (5 dígitos) é `codigo_classe`, o grupo `codigo_grupo`."
  - "UF inteira: tire o filtro de `nome_municipio` e agrupe por município."
  - "Por porte: junte dim_porte e agrupe por `rotulo_porte`."
resposta_esperada_fixtures:
  colunas: [nome_municipio, sigla_uf, codigo_subclasse, ativos, nao_ativos]
  linhas:
    - [Fundão, ES, '4741500', 1, 4]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  mun.nome_municipio,
  mun.sigla_uf,
  cnae.codigo_subclasse,
  count(*) filter (where fct.eh_ativa) as ativos,
  count(*) filter (where not fct.eh_ativa) as nao_ativos
from {{ ref('fct_estabelecimentos') }} as fct
inner join {{ ref('dim_cnae') }} as cnae
  on fct.sk_cnae = cnae.sk_cnae
inner join {{ ref('dim_municipio') }} as mun
  on fct.sk_municipio = mun.sk_municipio
where cnae.codigo_subclasse = '4741500' and mun.nome_municipio = 'Fundão' and mun.sigla_uf = 'ES'
group by mun.nome_municipio, mun.sigla_uf, cnae.codigo_subclasse
order by mun.nome_municipio
