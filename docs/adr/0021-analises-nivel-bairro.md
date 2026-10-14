# ADR-0021 — Análises no nível de bairro (proposta, decisões em aberto)

**Status:** proposta. Nada foi implementado. As decisões D1–D5 abaixo esperam o usuário, e as premissas
marcadas "a confirmar" esperam o spike (PR 0).

**Contexto.** Pedido do usuário (2026-10-13): avaliar se as análises podem descer do município ao bairro e o
que mudaria em modelos, pipeline e analyses, sem alterar nada. Hoje:
- `bairro` e `cep` existem no leiaute (`esquemas.py`) e chegam ao `stg_rfb__estabelecimentos`.
- Pelo ADR-0008, o endereço (logradouro, bairro, CEP) fica **só no staging**: nenhum modelo do gold o expõe.
- A menor unidade geográfica do gold é o município (`dim_municipio`, código IBGE). Os denominadores são a
  população, o PIB e o Censo 2022 municipal da Base dos Dados (ADR-0015).

**Avaliação do dado real** (2026-09, leitura direta do raw em Parquet, só leitura):

| Medida | Valor |
|---|---:|
| Estabelecimentos / ativos | 73.366.147 / 28.263.121 |
| `bairro` nulo ou vazio | 0 (mas 281.240 "NÃO INFORMADO" e 1.069 só com espaços) |
| Ativos com bairro genérico | CENTRO 4.052.781 (14 %), ZONA RURAL 428.507, INTERIOR 52.266, NÃO INFORMADO 22.332 |
| CEP com 8 dígitos | 73.112.865 (99,7 %); 1.274.597 CEPs distintos |
| Pares (município, bairro) distintos, texto bruto → normalizado (acento, caixa, pontuação) | 1.822.343 → 1.542.778 |
| Pares normalizados com < 5 ativos / com 0 ativos | 1.361.067 (88 %) / 837.590 (54 %) |
| Vitória (ES): nomes distintos bruto / normalizado | 1.162 / 1.014 |
| Fundão (ES), município do estudo de caso: bruto / normalizado | 425 / 324 |

`bairro` é texto livre. Em Vitória, "JARDIM CAMBURI" (23.341) convive com "JD CAMBURI", "J CAMBURI",
"J. CAMBURI", "JARDIM  CAMBURI" e "Jardim Camburi". A normalização não junta abreviações nem grafias
como OSEIAS/OZEIAS (Fundão).

Crescimento do grão com o bairro em texto normalizado:

| Combinação | Município | Município × bairro | Fator |
|---|---:|---:|---:|
| município × CNAE (grão de `mart_concorrencia_municipio`) | 2.027.267 | 15.112.094 | 7,5× |
| município × CNAE × situação (proxy de `fct_resumo_mensal`, hoje 5.763.929 linhas/mês) | 3.965.486 | 21.703.091 | 5,5× |

**Opções para a chave de bairro.**

| Opção | Como | A favor | Contra |
|---|---|---|---|
| A. Texto RFB normalizado | chave = município + `bairro` normalizado | sem fonte nova | fragmentado; 14 % "CENTRO"; sem população nem domicílios, logo sem densidade |
| **B. Bairro oficial IBGE via CEP** | CEP → endereços do **CNEFE 2022** (CEP → setor censitário) → bairro IBGE do setor; população e domicílios dos **Agregados por bairros do Censo 2022** | chave oficial; denominadores; independe da grafia | fonte nova e volumosa; CEP que cruza setores (regra da maioria); só municípios com bairros oficiais |
| C. Casamento de nome RFB × IBGE | similaridade contra a lista oficial | sem CNEFE | difuso, frágil, difícil de testar; falsos positivos silenciosos |

**Proposta.** Opção **B**, com o texto RFB normalizado como atributo de auditoria e uma regra que mede a
concordância entre os dois. Tudo como **adição** (ADR-0006), com marcador de incremento próprio, como o
`enriquecimento_bd` do ADR-0015.

A confirmar no spike, não verificado nesta avaliação:
- esquema e tamanho do CNEFE 2022 (CEP, código do setor, coordenadas);
- tabela setor → bairro dos Agregados por setores;
- quantos municípios têm bairros oficiais;
- forma de download: FTP do IBGE, e não a API `downloadTable` da Base dos Dados, limitada a 100 MB.

**Mudanças previstas, por camada (opção B).**
- **Ingestão:**
  - tabelas IBGE em `esquemas.py`;
  - módulo de download do IBGE, com manifesto, `--origem-local` e retentativas;
  - variável de recorte geográfico, por exemplo `RFB_UFS_BAIRRO`;
  - fixtures com resposta conhecida: CEP que cruza dois bairros, CEP fora do CNEFE, município sem bairros oficiais.
- **Staging e intermediate:**
  - `stg_ibge__cnefe`, `stg_ibge__setores_bairros`, `stg_ibge__bairros`;
  - `int_ceps__bairro`: CEP → bairro majoritário, com `participacao` para auditar a ambiguidade;
  - `int_estabelecimentos__enriquecidos` ganha `cep`, `bairro_rfb_normalizado`, `id_bairro_ibge` e `tem_bairro_ibge`, ainda com LEFT JOIN.
- **Core:**
  - `dim_bairro`: `sk_bairro`, código e nome IBGE, `sk_municipio`, população, domicílios, centroide se houver;
  - membros −1 "NÃO INFORMADO" e "SEM BAIRRO OFICIAL";
  - `fct_estabelecimentos` ganha `sk_bairro`;
  - `fct_resumo_mensal` **não** ganha bairro, para não reverter a emenda R3-02 do ADR-0013. Se o BI precisar, um `fct_resumo_mensal_bairro` à parte.
- **Analytics:**
  - novos `mart_concorrencia_bairro` (ativos por mil domicílios, ranking no município) e `mart_dinamica_mercado_bairro`;
  - `mart_fornecedores_proximos` passa a medir a distância pelo centroide do bairro;
  - a sobrevivência fica no nível atual: coortes por bairro são pequenas demais;
  - a área de mercado fica no município: vizinhança de bairros exige a malha geográfica;
  - `bh_empresas` e `agg_empresas` não mudam, pela paridade (ADR-0005).
- **Semântica e docs:**
  - entidade e dimensões `bairro`, métricas de densidade e uma saved query;
  - `rfbo:Bairro` na ontologia (parte de Município);
  - `CAMADA_SEMANTICA.md`, dicionário regenerado, `ARCHITECTURE.md`, `ESCOPO.md`.
- **Analyses:**
  - visão por bairro no estudo de caso. Em 2026-09 há **0 ativos** no CNAE alvo (4741-5/00) em Fundão, então a visão localiza a demanda (domicílios por bairro), não concorrentes;
  - novas regras:
    - RN-30: bairro genérico, como faixa informativa;
    - RN-31: o CEP pertence ao município declarado;
    - RN-32: o bairro RFB concorda com o bairro IBGE do CEP (observação);
  - `QUEBRAS_PERMITIDAS` continua **sem** `bairro`.
- **Testes:**
  - unitários: normalização, regra da maioria, download;
  - dbt: grão, FK e cobertura (`warn` com limiar) de `dim_bairro`;
  - integração com respostas conhecidas;
  - mutações nas fronteiras: empate na maioria, CEP fora do CNEFE.

**Decisões em aberto (usuário).**

| # | Decisão | Opções | Recomendação |
|---|---|---|---|
| D1 | Chave de bairro | A, B ou C | **B**, com o texto RFB como auditoria |
| D2 | Privacidade: emenda ao ADR-0008 | manter o endereço só no staging ou subir o bairro ao gold | subir só o nome e o código IBGE do bairro; logradouro, número, complemento e CEP continuam fora do gold (o CEP fica no intermediate). Suprimir células pequenas (ex.: < 5 ativos) em relatórios e no BI |
| D3 | Escopo geográfico | Brasil inteiro ou por UF | começar por **ES** (UF do caso) e ampliar por variável |
| D4 | `fct_resumo_mensal` | ganha bairro ou agregado à parte | agregado **à parte**, opcional |
| D5 | Versionamento | minor por PR ou um minor no fim | minor por PR, como na v1.2.0 e na v1.3.0 |

**Plano de entrega** (cada PR com implementador e revisor novos, como no ADR-0011):

| PR | Conteúdo | Saída verificável |
|---|---|---|
| 0, spike | CNEFE e agregados de ES; cobertura CEP → bairro, ambiguidade, tamanho; este ADR passa a `aceita` com D1–D5 decididas | números de cobertura |
| 1, ingestão + staging | download IBGE, `esquemas.py`, fixtures, `stg_ibge__*`, `int_ceps__bairro` | `make ci` verde |
| 2, dimensão + fatos + marts | `dim_bairro`, `sk_bairro`, marts de bairro, emenda do ADR-0008 | testes de grão e FK; real de ES sem identificador |
| 3, semântica + docs + analyses | métricas, ontologia, dicionário, estudo de caso, RN-30 a RN-32 | `make semantica`, `make dicionario`, `make regras` |

**Riscos.**
- O volume do CNEFE é o motivo do recorte por UF.
- Nem todo município tem bairros oficiais. Esses estabelecimentos ficam num membro explícito, nunca descartados.
- No município pequeno com um só CEP para a cidade toda, o CEP cai no bairro majoritário com `participacao` baixa. A RN-32 e o `warn` de cobertura expõem esses casos.

**Consequências.**
- Nada muda no código enquanto o ADR estiver como proposta.
- Aceitar a opção B traz uma fonte nova (IBGE) além da RFB e da Base dos Dados.
- Também emenda o ADR-0008, porque o bairro passa a estar no gold.

Fontes: [IBGE, Censo 2022](https://www.ibge.gov.br/estatisticas/Sociais/populacao/22827-censo-demografico-2022.html?edicao=41851),
[IBGE, quadro geográfico: bairros 2022](https://www.ibge.gov.br/apps/quadrogeografico/pdf/qg_2022_650_bairro.pdf),
[IBGE, Agregados por Setores Censitários](https://biblioteca.ibge.gov.br/visualizacao/livros/liv102136.pdf),
[Geobases ES, agregados por bairros do Censo 2022](https://ide.geobases.es.gov.br/layers/geonode:ibge_cd2022_bairros_epsg_31984).
