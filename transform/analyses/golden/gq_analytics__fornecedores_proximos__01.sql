{# ---
id: gq_analytics__fornecedores_proximos__01
conceito: fornecedores_proximos
camada: analytics
perguntas:
  - "Há fornecedores de tinta perto de Fundão?"
  - "Quantos fabricantes e atacadistas de tinta há num raio de 100 km de Fundão, e onde?"
intencao: "Fornecedores ativos do caso (CNAEs e raio das vars do projeto) por município, via (principal × secundário) e distância."
tabelas: [mart_fornecedores_proximos]
colunas_chave: [municipio, uf, via, cnae_fornecido, distancia_km]
armadilhas:
  - "O mart é PARAMETRIZADO pelas vars do build (`caso_municipio`, `caso_uf`, `caso_cnaes_fornecedores`, `raio_fornecedores_km`): só responde para o caso configurado (Fundão/ES, tintas, 100 km). Outro caso exige outro build ou a consulta ad hoc por haversine."
  - "Distância entre centroides de municípios, não entre endereços."
  - "Agregue: não liste CNPJ nem nome por padrão (ADR-0008)."
variacoes:
  - "Só pela atividade principal: `where via = 'principal'`."
  - "Raio menor: `where distancia_km <= 50`."
resposta_esperada_fixtures:
  colunas: [municipio, uf, via, cnae_fornecido, fornecedores, distancia_km]
  linhas:
    - [Serra, ES, principal, '2071100', 1, 18.66]
    - [Aracruz, ES, principal, '2071100', 1, 29.36]
    - [Linhares, ES, secundario, '4679699', 1, 73.68]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  municipio,
  uf,
  via,
  cnae_fornecido,
  count(*) as fornecedores,
  min(distancia_km) as distancia_km
from {{ ref('mart_fornecedores_proximos') }}
group by municipio, uf, via, cnae_fornecido
order by distancia_km, municipio, via, cnae_fornecido
