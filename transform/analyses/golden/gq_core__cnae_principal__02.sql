{# ---
id: gq_core__cnae_principal__02
conceito: cnae_principal
camada: core
perguntas:
  - "Qual o código CNAE de loja de tintas?"
  - "Que atividades da CNAE falam de tinta?"
  - "Em que classe e grupo fica o comércio de tintas?"
intencao: "Achar a subclasse CNAE (e a hierarquia) a partir de um termo da descrição, antes de filtrar a fato."
tabelas: [dim_cnae]
colunas_chave: [codigo_subclasse, descricao_subclasse, codigo_classe, codigo_grupo, codigo_secao]
armadilhas:
  - "Um termo coloquial casa várias subclasses (tinta para varejo, atacado e fabricação): mostre as opções ou pergunte."
  - "Busque sem acento e sem caixa (`strip_accents(lower(...))`); as descrições têm acentos."
  - "Filtre a fato pelo código, nunca pela descrição."
variacoes:
  - "Outro termo: troque '%tinta%'."
  - "Só o nível de classe: `select distinct codigo_classe, descricao_classe`."
resposta_esperada_fixtures:
  colunas: [codigo_subclasse, descricao_subclasse, codigo_classe, codigo_grupo, codigo_secao]
  linhas:
    - ['2071100', 'Fabricacao de tintas, vernizes, esmaltes e lacas', '20711', '207', C]
    - ['4679601', 'Comercio atacadista de tintas, vernizes e materiais para pintura', '46796', '467', G]
    - ['4741500', 'Comercio varejista de tintas, vernizes e materiais para pintura', '47415', '474', G]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  codigo_subclasse,
  descricao_subclasse,
  codigo_classe,
  codigo_grupo,
  codigo_secao
from {{ ref('dim_cnae') }}
where strip_accents(lower(descricao_subclasse)) like '%tinta%'
order by codigo_subclasse
