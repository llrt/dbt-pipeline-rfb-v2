{# ---
id: gq_analytics__area_mercado_vizinhanca__02
conceito: area_mercado_vizinhanca
camada: analytics
perguntas:
  - "Em que municípios não há nenhuma loja de tintas, mas há nos vizinhos?"
  - "Onde há vazio de mercado de tintas no ES?"
intencao: "Vazios de mercado: municípios sem estabelecimento local do CNAE, mas com ativos nos vizinhos ou na região metropolitana."
tabelas: [mart_concorrencia_area_mercado]
colunas_chave: [cnae_principal, tem_estabelecimento_local, ativos_vizinhos, ativos_regiao_metropolitana]
armadilhas:
  - "Vazio de mercado é sinal para investigar, não oportunidade comprovada: o morador pode comprar no polo (REGIC)."
  - "Município sem nenhum vizinho nem região metropolitana com o CNAE não aparece."
variacoes:
  - "Brasil: tire o filtro de `uf`."
resposta_esperada_fixtures:
  colunas: [municipio, uf, ativos_vizinhos, ativos_regiao_metropolitana]
  linhas:
    - [Aracruz, ES, 1, null]
    - [Vitória, ES, 1, 2]
--- #}
{{ config(
    tags=['escopo_adicao', 'golden_query', 'incremento_enriquecimento_bd'],
    meta={'escopo': 'adicao', 'incremento': 'enriquecimento_bd'}
) }}

select
  municipio,
  uf,
  ativos_vizinhos,
  ativos_regiao_metropolitana
from {{ ref('mart_concorrencia_area_mercado') }}
where cnae_principal = '4741500' and uf = 'ES' and not tem_estabelecimento_local
order by municipio
