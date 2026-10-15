{# ---
id: gq_core__cnae_principal__02
conceito: cnae_principal
camada: core
perguntas:
  - "Qual o código CNAE de loja de tintas?"
  - "Que atividades da CNAE falam de tinta?"
  - "Em que classe e grupo fica o comércio de tintas?"
  - "Qual o CNAE de padaria?"
intencao: "Achar as subclasses CNAE candidatas (e a hierarquia) a partir de um termo da descrição, com o volume de estabelecimentos e de ativos de cada uma, antes de filtrar a fato."
tabelas: [dim_cnae, fct_estabelecimentos]
colunas_chave: [codigo_subclasse, descricao_subclasse, codigo_classe, codigo_grupo, codigo_secao, sk_cnae, eh_ativa]
armadilhas:
  - "Um termo coloquial casa várias subclasses (tinta para varejo, atacado e fabricação): mostre as candidatas com o volume e pergunte qual vale, ou some as que o usuário aceitar. Nunca escolha só pelo nome."
  - "Padaria (dado real, 2026-09): '%padaria%' casa 1091102 (fabricação de produtos de padaria, 457.872 estabelecimentos no Brasil, a maioria das padarias), 4721102 (padaria e confeitaria com revenda, 289.460) e 4721101 (com produção própria, 4: obsoleta). Em Vitória, 2025, quem filtra só pelo nome 'Padaria e confeitaria' conta 30 aberturas em vez de 137."
  - "Subclasse com nenhum ou quase nenhum estabelecimento (`sem_uso` true ou volume ínfimo diante das outras) costuma ser obsoleta: não a ofereça como a principal."
  - "Busque sem acento e sem caixa (`strip_accents(lower(...))`); as descrições têm acentos."
  - "Filtre a fato pelo código, nunca pela descrição."
variacoes:
  - "Outro termo: troque '%tinta%' (ex.: '%padaria%', '%restaurante%')."
  - "Volume de uma UF ou de um município: junte dim_municipio na fato (`left join` com o filtro de UF no `on`) para não perder as subclasses sem uso."
  - "Só o nível de classe: agrupe por `codigo_classe, descricao_classe`."
resposta_esperada_fixtures:
  colunas: [codigo_subclasse, descricao_subclasse, codigo_classe, codigo_grupo, codigo_secao, estabelecimentos, ativos, sem_uso]
  linhas:
    - ['2071100', 'Fabricacao de tintas, vernizes, esmaltes e lacas', '20711', '207', C, 3, 3, false]
    - ['4679601', 'Comercio atacadista de tintas, vernizes e materiais para pintura', '46796', '467', G, 2, 1, false]
    - ['4741500', 'Comercio varejista de tintas, vernizes e materiais para pintura', '47415', '474', G, 6, 2, false]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  cnae.codigo_subclasse,
  cnae.descricao_subclasse,
  cnae.codigo_classe,
  cnae.codigo_grupo,
  cnae.codigo_secao,
  count(fct.cnpj_completo) as estabelecimentos,
  count(fct.cnpj_completo) filter (where fct.eh_ativa) as ativos,
  count(fct.cnpj_completo) = 0 as sem_uso
from {{ ref('dim_cnae') }} as cnae
left join {{ ref('fct_estabelecimentos') }} as fct
  on cnae.sk_cnae = fct.sk_cnae
where strip_accents(lower(cnae.descricao_subclasse)) like '%tinta%'
group by
  cnae.codigo_subclasse,
  cnae.descricao_subclasse,
  cnae.codigo_classe,
  cnae.codigo_grupo,
  cnae.codigo_secao
order by cnae.codigo_subclasse
