{# ---
id: gq_core__porte__01
conceito: porte
camada: core
perguntas:
  - "Quantos estabelecimentos ativos há por porte, e qual a idade média?"
  - "Quantas microempresas ativas existem?"
intencao: "Ativos por porte da empresa (rótulo de dim_porte) e idade média em anos na data de referência."
tabelas: [fct_estabelecimentos, dim_porte]
colunas_chave: [sk_porte, rotulo_porte, idade_anos, eh_ativa]
armadilhas:
  - "O porte é declarado (ME/EPP pela LC 123), não medido; MEI não é porte (use `opcao_mei`)."
  - "'N/A' (código 00 da RFB) ≠ 'NÃO INFORMADO' (membro -1, porte vazio ou fora do domínio)."
  - "Idade média = média de `idade_anos`, que só existe para ativos e é relativa à data de referência, não a hoje."
  - "O porte é da empresa e se repete em cada estabelecimento."
variacoes:
  - "Só empresas: `and fct.eh_matriz`."
  - "Por UF ou CNAE: junte a dimensão e filtre."
resposta_esperada_fixtures:
  colunas: [codigo_porte, rotulo_porte, ativos, idade_media_anos]
  linhas:
    - ['0', N/A, 2, 16.1]
    - ['1', MICRO, 4, 4.3]
    - ['3', PEQUENA, 3, 14.8]
    - ['5', DEMAIS, 2, 18.7]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  por.codigo_porte,
  por.rotulo_porte,
  count(*) as ativos,
  round(avg(fct.idade_anos), 1) as idade_media_anos
from {{ ref('fct_estabelecimentos') }} as fct
inner join {{ ref('dim_porte') }} as por
  on fct.sk_porte = por.sk_porte
where fct.eh_ativa
group by por.codigo_porte, por.rotulo_porte
order by por.codigo_porte
