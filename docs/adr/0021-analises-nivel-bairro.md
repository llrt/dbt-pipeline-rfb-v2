# ADR-0021 — Análises no nível de bairro: adiar

**Status:** adiada. Nada foi implementado. Este ADR guarda a avaliação, o custo × benefício e os gatilhos
para reabrir.

**Contexto.** Pedido do usuário (2026-10-13): avaliar se as análises podem descer do município ao bairro e o
que mudaria em modelos, pipeline e analyses, sem alterar nada. Hoje:
- `bairro` e `cep` existem no leiaute (`esquemas.py`) e chegam ao `stg_rfb__estabelecimentos`.
- Pelo ADR-0008, o endereço (logradouro, bairro, CEP) fica **só no staging**: nenhum modelo do gold o expõe.
- A menor unidade geográfica do gold é o município (`dim_municipio`, código IBGE). Os denominadores são a
  população, o PIB e o Censo 2022 municipal da Base dos Dados (ADR-0015).

A primeira versão deste ADR propôs o incremento completo em quatro PRs. Na revisão de custo × benefício
pedida pelo usuário, a decisão passou a ser **adiar**.

**Avaliação do dado real** (2026-09, leitura direta do raw em Parquet, só leitura):

| Medida | Valor |
|---|---:|
| Estabelecimentos / ativos | 73.366.147 / 28.263.121 |
| `bairro` nulo ou vazio | 0 (mas 281.240 "NÃO INFORMADO" e 1.069 só com espaços) |
| Ativos com bairro genérico | CENTRO 4.052.781 (14 %), ZONA RURAL 428.507, INTERIOR 52.266, NÃO INFORMADO 22.332 |
| CEP com 8 dígitos | 73.112.865 (99,7 %); 1.274.597 CEPs distintos |
| Pares (município, bairro) distintos, texto bruto → normalizado (acento, caixa, pontuação) | 1.822.343 → 1.542.778 |
| Pares normalizados com < 5 ativos / com 0 ativos | 1.361.067 (88 %) / 837.590 (54 %) |
| Pares (município, 5 primeiros dígitos do CEP) | 39.488 |
| Vitória (ES): nomes distintos bruto / normalizado | 1.162 / 1.014 |
| Fundão (ES), município do estudo de caso: bruto / normalizado | 425 / 324 |
| Fundão: ativos no CNAE alvo do caso (4741-5/00) | 0 |

`bairro` é texto livre. Em Vitória, "JARDIM CAMBURI" (23.341) convive com "JD CAMBURI", "J CAMBURI",
"J. CAMBURI", "JARDIM  CAMBURI" e "Jardim Camburi". O grão município × CNAE cresce de 2.027.267 para
15.112.094 linhas (7,5×) com o bairro em texto normalizado.

**Opções avaliadas para a chave de bairro.**

| Opção | Como | A favor | Contra |
|---|---|---|---|
| A. Texto RFB normalizado | chave = município + `bairro` normalizado | sem fonte nova | fragmentado; 14 % "CENTRO"; sem população nem domicílios, logo sem densidade |
| B. Bairro oficial IBGE via CEP | CEP → endereços do **CNEFE 2022** (CEP → setor censitário) → bairro IBGE do setor; população e domicílios dos **Agregados por bairros do Censo 2022** | chave oficial; denominadores; independe da grafia | fonte nova e volumosa; CEP que cruza setores; só municípios com bairros oficiais |
| C. Casamento de nome RFB × IBGE | similaridade contra a lista oficial | sem CNEFE | difuso, frágil, difícil de testar; falsos positivos silenciosos |

Se o tema for reaberto, o caminho técnico é **B**, com o texto RFB como atributo de auditoria.

**Custo × benefício.**

| Benefício esperado | O que o dado mostra |
|---|---|
| Concorrência por bairro no estudo de caso | Fundão tem 0 ativos no CNAE alvo: a concorrência local por bairro é zero em todo o município. O que restaria é a demanda (domicílios por bairro), que vem do IBGE e não precisa do pipeline da RFB |
| Distância mais precisa em `mart_fornecedores_proximos` | O raio é de 100 km. Trocar o centroide do município pelo do bairro muda as distâncias em poucos km. Só os fornecedores perto da borda do raio podem entrar ou sair da lista, e o miolo dela não muda. Para uma escolha de fornecedor, isso pesa pouco |
| Densidade por bairro no BI | 88 % dos pares têm < 5 ativos: a densidade é ruído, e a supressão de células pequenas que a privacidade exige esconderia a maior parte |
| Concorrência dentro de cidades grandes | Benefício real, mas restrito a capitais e cidades grandes. Nenhuma pergunta atual do projeto pede isso |

| Custo da opção B | Detalhe |
|---|---|
| Fonte nova e pesada | o CNEFE seria o maior insumo do projeto: download próprio pelo FTP do IBGE (a API `downloadTable` da Base dos Dados é limitada a 100 MB), novo modo de falha, mais memória. O plano já precisava recortar por UF |
| Cobertura que envelhece | o CNEFE é do Censo 2022, com ciclo decenal. CEPs e loteamentos posteriores ficam fora, e a fração "não informado" cresce a cada extrato mensal |
| Cobertura parcial | só municípios com bairros oficiais. Não foi confirmado se Fundão tem |
| Privacidade | emenda ao ADR-0008 (o bairro passaria ao gold) e supressão de células pequenas permanente no BI e nos relatórios |
| Grão e manutenção | até 7,5× no grão de concorrência. Dimensão, marts, métricas, ontologia, dicionário e regras novas para manter |
| Dinheiro e tempo | estimativa a partir do custo por versão do pós-v1 (US$ 15 a 35 em agentes por versão, mais orquestração, `docs/historico/custos-agentes.md`): **US$ 150 a 250** em quatro PRs, mais a revisão do usuário em cada um |

**Decisão.**
- **Adiar** o incremento de bairro. O gold continua no município, e o ADR-0008 não muda.
- Nenhuma alternativa barata entra agora. Ficam registradas para quando houver demanda:

  | Alternativa | Custo | Entrega | Limite |
  |---|---|---|---|
  | Analysis pontual para o município do caso | 1 PR pequeno | contagens por bairro normalizado lidas do staging, com aviso sobre a grafia; o gold não muda | expõe nomes de bairro, só agregados, num relatório: pede o aval do usuário à luz do ADR-0008 |
  | 5 primeiros dígitos do CEP como unidade intramunicipal | pequeno | chave limpa, sem fonte nova (39.488 pares) | não é um bairro reconhecível e não tem população |

**Gatilhos para reabrir** (basta um):
1. uma pergunta de negócio concreta que dependa do bairro, como concorrência dentro de uma cidade grande;
2. um estudo de caso num município em que o CNAE alvo tenha ativos suficientes por bairro;
3. uma fonte oficial mais leve que ligue o CEP ao bairro IBGE, por exemplo uma tabela da Base dos Dados abaixo do limite de download;
4. pedido do usuário.

**Como reabrir.** Começar por um spike de cobertura em uma UF (ES), antes de qualquer implementação, que
confirme o que esta avaliação não verificou:
- esquema e tamanho do CNEFE 2022 (CEP, código do setor, coordenadas);
- tabela setor → bairro dos Agregados por setores;
- quantos municípios têm bairros oficiais;
- cobertura e ambiguidade de CEP → bairro.

Se o spike for favorável, o incremento segue a opção B como **adição** (ADR-0006), com marcador próprio.

| Camada | Mudança |
|---|---|
| Ingestão | tabelas IBGE em `esquemas.py`, download do IBGE, recorte por UF |
| Staging e intermediate | `stg_ibge__*`; `int_ceps__bairro` (CEP → bairro majoritário, com `participacao`) |
| Core | `dim_bairro`; `sk_bairro` em `fct_estabelecimentos` |
| Analytics | `mart_concorrencia_bairro` e `mart_dinamica_mercado_bairro` |
| Semântica, docs, regras | entidade `bairro`, ontologia, dicionário, RN-30 a RN-32 |

`fct_resumo_mensal`, a sobrevivência, a área de mercado e os modelos originais não mudam. As decisões a tomar
na reabertura são: a chave (A, B ou C), a emenda ao ADR-0008 com o limiar de supressão, o escopo geográfico e
o resumo mensal à parte ou não.

**Consequências.**
- Nada muda no código.
- Os números do dado real e o desenho da opção B ficam guardados aqui, e a reabertura começa pelo spike, não do zero.
- A Fase 2 do ADR-0015 já listava o "diretório de CEP" como fora de escopo por exigir BigQuery. Este ADR
  acrescenta o CNEFE como alternativa sem BigQuery, também adiada.

Fontes: [IBGE, Censo 2022](https://www.ibge.gov.br/estatisticas/Sociais/populacao/22827-censo-demografico-2022.html?edicao=41851),
[IBGE, quadro geográfico: bairros 2022](https://www.ibge.gov.br/apps/quadrogeografico/pdf/qg_2022_650_bairro.pdf),
[IBGE, Agregados por Setores Censitários](https://biblioteca.ibge.gov.br/visualizacao/livros/liv102136.pdf),
[Geobases ES, agregados por bairros do Censo 2022](https://ide.geobases.es.gov.br/layers/geonode:ibge_cd2022_bairros_epsg_31984).
