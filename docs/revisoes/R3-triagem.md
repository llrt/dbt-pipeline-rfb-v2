# Triagem da R3 (líder, 2026-10-01)

Veredito da R3: **APROVADO COM RESSALVAS** — 0 bloqueantes, 6 importantes, 11 menores, 3 sugestões
([R3.md](R3.md)). O `dbt build --target dev` completo sobre o extrato real de fev/2025 (64,5 M
estabelecimentos) passou verde em 275 s (PASS=251 WARN=7 ERROR=0, pico de RSS 24,5 GB), e Fundão/4741500 no
`agg_empresas` real reproduz o notebook 4 (1 ativa + 4 inativas). O líder conferiu no código o R3-05
(`threads` do profile como string, sem `settings.threads` do DuckDB) e o R3-04 (notebook 4 compara
`microrregiao_municipio` em MAIÚSCULAS com `nome_microrregiao` em grafia mista da BD).

## Decisões do líder

| Achado | Decisão | Lote | Resolvido em |
|---|---|---|---|
| **R3-01** capital social não aditivo | `fct_resumo_mensal` passa a somar o capital **só das matrizes** (`soma_capital_social_matrizes`) e ganha `qtd_matrizes`; "Capital Médio" no DAX = soma ÷ matrizes. Descrição de `fct_estabelecimentos.capital_social`: "atributo da empresa; não some por estabelecimento". Reconciliação e guia ajustados. | F3a | `0b22904`, `f57f57d`, `51cb2d8` |
| **R3-02** resumo mensal com 22 M linhas | **ADR-0013 e spec BI-02 AC 5 emendados**: o grão do resumo **perde `ano_inicio_atividade` e `natureza_juridica`** (coorte fica em `mart_sobrevivencia_coorte`; natureza segue na fato detalhada). Grão novo: mês × município × subclasse × porte × situação × MEI. Medir o tamanho real (fev/2025) e registrar no guia e no ADR; o guia passa a recomendar Import dos **últimos 24 meses**. Se ainda passar de ~6 M linhas/mês, o worker reporta antes de seguir. | F3a | `0b22904`, `f823b44`, `51cb2d8` |
| **R3-03** `dim_data` (P16 + P21) | Adotado o desenho da R3: calendário de **1900-01-01** até `greatest(data_referencia, maior data válida)`; membro **−2 "DATA INVÁLIDA"** para datas anteriores a 1900 (na fato; `bh_empresas` intocado por causa da paridade); datas sentinela contíguas **−1 → 1899-12-31**, **−2 → 1899-12-30** (`ano`/`mes` NULL); `accepted_range` de início passa a 1900 (warn). Guia: marcar `dim_data` como tabela de datas. | F3a | `910af26`, `f823b44` |
| **R3-04** notebook 4 × caixa de texto | Manter a correção (`upper` dos dois lados) como **`adaptado`** (bug latente do original: as buscas por micro e mesorregião sempre davam 0, daí "nada nas imediações"). Comentário na analysis, linha no ESCOPO, nota no relatório; fixture com um fabricante 2071100 ATIVO na microrregião de Linhares para matar M21. | F3b | `2155921`, `bfceca1` |
| **R3-05** `DUCKDB_THREADS` | Variáveis separadas: `DBT_THREADS` (paralelismo de nós, `as_number`) e `DUCKDB_THREADS` (vai em `settings.threads` do DuckDB). Teste de `dbt debug` com as duas definidas. P14 passa a ser medida com a variável certa no B8. | F3a | `b2309eb` |
| **R3-06** `rfb relatorio` com `s3://` (P19) | Para o B8 (T28/T36): httpfs + secret na conexão do relatório, URI S3 no `dbt compile`, teste unitário. | B8 | — |
| **R3-07** limites da sobrevivência | unit test com coorte elegível a 1 ano e não a 3, e baixa exatamente no aniversário. | F3b | `7635347` |
| **R3-08** prioridade da `via` | unit test com CNAE de fornecedor no principal e no secundário, e com dois secundários. | F3b | `7635347` |
| **R3-09** casos positivos de DQ | CNPJ alfanumérico válido e inválido; data futura num estabelecimento. | F3b | `f623e29` |
| **R3-10** `soma_idade_anos` não afirmada | incluir `sum(idade_anos)` na reconciliação do mês e teste de integração. | F3a | `0b22904`, `f57f57d` |
| **R3-11** `data_nao_futura` no Simples | tirar das colunas de exclusão do Simples/MEI (efeito futuro é legítimo); registrar a exceção na spec (DQ-01 AC 2) e no catálogo. | F3b | `5ebef65` |
| **R3-12** catálogo de DQ | `attached_node` para o dono do teste; regerar; guarda no CI (`git diff --exit-code docs/QUALIDADE_DADOS.md`). | F3b | `dc4932a` |
| **R3-13** `store_failures` em teste que avisa | ligar no `accepted_range` de `idade_atual`; a guarda passa a olhar `warn_if` também. | F3b | `dc4932a` |
| **R3-14** imprecisões do guia Power BI | corrigir (a) coluna de partição, (b) Date × DateTime, (c) bridge sem relação direta ativa com `dim_cnae`, (d) `dim_mes` ou cópia da `dim_data` para o resumo, (e) "Mês Mais Recente" com `ALL`. | F3a | `51cb2d8` |
| **R3-15** caso não resolvido | teste singular: `caso_municipio`/`caso_uf` resolve para exatamente 1 município. | F3b | `514d48e` |
| **R3-16** relatório real longo | top 20 + total nas tabelas longas; média ponderada; rótulos corretos; `--target-path` explícito. | F3b | `8d58da0`, `2155921` |
| **R3-17** custo do `cnpj_dv_valido` | uma passada só; `run_query` só em `test`/`build`. | F3b | `f623e29` |
| **R3-18** relationships do resumo em todas as partições | filtrar ao mês processado (error) + teste `warn` de integridade histórica. | F3a | `57ebe5d`, `e9132ac` |
| **R3-19** "ativa" ≠ em operação | nota de interpretação no relatório e no guia. | F3b | `8d58da0` |
| **R3-20** marts sem `sk_*` | expor `sk_municipio`/`sk_cnae` nos marts de analytics. | F3b | `00c2a6e` |
| **P18** grafias de município | manter; documentar no `POWER_BI.md` e no ESCOPO (`upper(nome_municipio)` + UF para cruzar com os marts do original). | F3a | `51cb2d8` |
| **P22** ordem de meses | para o B8, com as três medidas da R3 (ordem garantida, `external_root` temporário no backfill, teste de gold "corrente"). | B8 | — |

Execução: **F3a** (Claude Sonnet médio, nível de origem dos lotes B6/B7b) primeiro, por mexer no modelo estrela
e no guia; **F3b** (Claude Sonnet médio, nível do B7) em seguida, sobre DQ, analyses, relatório e testes.
Sequenciais porque compartilham `QUALIDADE_DADOS.md`, ESCOPO e fixtures.

**Achado de produto (para o RETRO e o relatório):** a conclusão "não há fornecedores nas imediações" do
notebook 4 original vinha de um bug de comparação de caixa. Com a comparação corrigida, o extrato real de
fev/2025 mostra 1 fabricante na microrregião de Fundão, 12 atacadistas e 155 estabelecimentos com CNAE de
fornecedor como secundário na mesorregião.
