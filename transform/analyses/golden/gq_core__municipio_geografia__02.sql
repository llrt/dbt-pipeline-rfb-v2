{# ---
id: gq_core__municipio_geografia__02
conceito: municipio_geografia
camada: core
perguntas:
  - "Quantas empresas tem em Água Branca?"
  - "Qual Água Branca? Quantos estabelecimentos há em cada uma?"
intencao: "Desambiguação de município homônimo: o mesmo nome em várias UFs, com código IBGE e estabelecimentos de cada um."
tabelas: [fct_estabelecimentos, dim_municipio]
colunas_chave: [sk_municipio, id_municipio_ibge, nome_municipio, sigla_uf]
armadilhas:
  - "Empresa × estabelecimento: conta estabelecimentos (CNPJ completo), não empresas. Se o usuário quer empresas (CNPJ básico), filtre `fct.eh_matriz` (uma matriz por empresa) ou conte `distinct left(cnpj_completo, 8)`; aqui a pergunta é ambígua também no município: pergunte (exemplo 3 do guia)."
  - "Nome sem UF é ambíguo: se houver mais de uma linha, pergunte a UF antes de responder."
  - "O `left join` mantém o município sem nenhum estabelecimento (0), que um `inner join` esconderia."
variacoes:
  - "Outro nome: troque o filtro; compare sem acento com `strip_accents(lower(...))`."
resposta_esperada_fixtures:
  colunas: [id_municipio_ibge, nome_municipio, sigla_uf, estabelecimentos, ativos]
  linhas:
    - ['2700102', Água Branca, AL, 1, 1]
    - ['2500106', Água Branca, PB, 2, 0]
    - ['2200202', Água Branca, PI, 0, 0]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  mun.id_municipio_ibge,
  mun.nome_municipio,
  mun.sigla_uf,
  count(fct.cnpj_completo) as estabelecimentos,
  count(fct.cnpj_completo) filter (where fct.eh_ativa) as ativos
from {{ ref('dim_municipio') }} as mun
left join {{ ref('fct_estabelecimentos') }} as fct
  on mun.sk_municipio = fct.sk_municipio
where strip_accents(lower(mun.nome_municipio)) = 'agua branca'
group by mun.id_municipio_ibge, mun.nome_municipio, mun.sigla_uf
order by mun.sigla_uf
