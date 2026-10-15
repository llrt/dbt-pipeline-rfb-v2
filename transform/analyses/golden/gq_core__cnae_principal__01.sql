{# ---
id: gq_core__cnae_principal__01
conceito: cnae_principal
camada: core
perguntas:
  - "Quantos estabelecimentos ativos há em cada setor (seção da CNAE)?"
  - "Qual ramo tem mais empresas ativas, comércio ou indústria?"
intencao: "Ativos por seção e divisão da CNAE do CNAE principal (hierarquia de dim_cnae)."
tabelas: [fct_estabelecimentos, dim_cnae]
colunas_chave: [sk_cnae, codigo_secao, descricao_secao, codigo_divisao, descricao_divisao]
armadilhas:
  - "Empresa × estabelecimento: conta estabelecimentos (CNPJ completo), não empresas. Se o usuário quer empresas (CNPJ básico), filtre `fct.eh_matriz` (uma matriz por empresa) ou conte `distinct left(cnpj_completo, 8)`; se não está claro, declare a escolha na resposta."
  - "'Setor'/'ramo' é ambíguo: seção (letra), divisão (2 dígitos), grupo (3), classe (5) ou subclasse (7). Escolha o nível ou pergunte."
  - "Só o CNAE principal; o secundário está na ponte (gq_core__cnae_secundario__01)."
  - "O membro -1 (NÃO INFORMADO) reúne CNAEs sem par na Base dos Dados."
variacoes:
  - "Por grupo ou classe: troque as colunas por `codigo_grupo`/`descricao_grupo` ou `codigo_classe`/`descricao_classe`."
  - "Numa UF: junte dim_municipio e filtre `sigla_uf`."
resposta_esperada_fixtures:
  colunas: [codigo_secao, descricao_secao, codigo_divisao, descricao_divisao, ativos]
  linhas:
    - ['-1', NÃO INFORMADO, '-1', NÃO INFORMADO, 1]
    - [A, 'Agricultura, pecuaria, producao florestal, pesca e aquicultura', '01', 'Agricultura, pecuaria e servicos relacionados', 1]
    - [C, Industrias de transformacao, '20', Fabricacao de produtos quimicos, 3]
    - [G, Comercio; reparacao de veiculos automotores e motocicletas, '46', 'Comercio por atacado, exceto veiculos automotores e motocicletas', 1]
    - [G, Comercio; reparacao de veiculos automotores e motocicletas, '47', Comercio varejista, 3]
    - [G, Comercio; reparacao de veiculos automotores e motocicletas, '47', 'Comercio varejista, exceto de

    veiculos automotores e motocicletas', 2]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  cnae.codigo_secao,
  cnae.descricao_secao,
  cnae.codigo_divisao,
  cnae.descricao_divisao,
  count(*) as ativos
from {{ ref('fct_estabelecimentos') }} as fct
inner join {{ ref('dim_cnae') }} as cnae
  on fct.sk_cnae = cnae.sk_cnae
where fct.eh_ativa
group by cnae.codigo_secao, cnae.descricao_secao, cnae.codigo_divisao, cnae.descricao_divisao
order by cnae.codigo_secao, cnae.codigo_divisao, cnae.descricao_divisao
