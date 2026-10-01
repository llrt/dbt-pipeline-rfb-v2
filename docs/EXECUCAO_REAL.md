# Execução real (B8 — T28/T36)

Registro da execução ponta a ponta sobre os dados reais da RFB e da Base dos Dados, da comparação
numérica com o MVP original (AD-018) e da validação da atualização mensal. Números de **2026-10-01**,
máquina de referência: MacBook (Apple Silicon, 15 núcleos, 48 GB de RAM, SSD), macOS, com
`caffeinate -i` (P20). Os dados ficaram fora do repositório (`dados/`, ignorado pelo git).

## 1. Pipeline real de 2026-09 (`rfb pipeline --mes 2026-09`)

Comando: `RAIZ_DADOS=dados/real-2026-09 caffeinate -i rfb pipeline --mes 2026-09` (target `dev`,
`DBT_THREADS=8`, `DUCKDB_THREADS=8`, `DUCKDB_MEMORY_LIMIT` padrão 24 GB).

**Resultado: `dbt build` PASS=339 WARN=14 ERROR=0 (NO-OP=1), paridade `bh_empresas` × SQL original =
0 diferenças em 71.396.386 linhas, relatório gerado, estado gravado (`2026-09`, extrato de
2026-09-12).** Saída 0.

### Tempos por etapa

| Etapa | Tempo | Observação |
|---|---|---|
| Download WebDAV (31 zips, 7,07 GB) | ~21 min (≈ 5,5 MB/s) | sem travamentos nem retomadas; `Estabelecimentos0.zip` tem 2,2 GB |
| Conversão CSV → Parquet | 162 s | empresas 21,8 s (70,1 M), estabelecimentos 124,2 s (73,4 M), simples 7,2 s (50,4 M), domínios e BD < 1 s cada |
| Ingestão numa reexecução (nada mudou) | 10–12 s | manifesto: só sha256 dos zips; entidades puladas |
| `dbt source freshness` | 3,1 s | |
| `dbt build` (8/8 threads) | **318 s** | `bh_empresas` 153 s, `paridade_bh_empresas` 109 s, `bh_empresas_descartes_inner_join` 92 s, `int_estabelecimentos__enriquecidos` 49 s, `bh_empresas_nome_alterado_por_trim` 44 s, `cnpj_dv_valido` 42 s |
| Relatório (`docs/RELATORIO_ESTUDO_CASO.md`) | 4,8 s | |
| Publicação | 0 s | MotherDuck não configurado ("nada publicado") |
| **Total do pipeline (com o raw já baixado)** | **339 s** | + ~24 min de download/conversão na 1ª vez |

### Volumes por camada

| Camada | Objeto | Linhas | Tamanho |
|---|---|---|---|
| raw | `rfb/empresas` | 70.085.592 | 1,1 GB (Parquet zstd) |
| raw | `rfb/estabelecimentos` | 73.366.147 | 3,6 GB |
| raw | `rfb/simples` | 50.396.768 | 208 MB |
| raw | domínios RFB (cnaes, municípios, naturezas, motivos, países, qualificações) | 1.359 / 5.572 / 91 / 63 / 255 / 68 | < 100 KB |
| raw | BD (município 5.571, cnae_2 1.356, população 191.099, PIB 122.466, censo 5.570, RM 1.385, vizinhança 522.822) | | 7,7 MB |
| staging | `stg_rfb__empresas` (após a deduplicação, §3) | 70.085.591 | view |
| staging | `stg_rfb__estabelecimentos` / `stg_rfb__simples` | 73.366.147 / 50.396.768 | view |
| intermediate | `int_estabelecimentos__enriquecidos` / `int_cnaes_secundarios__explodidos` | 73.366.147 / 125.421.187 | tabelas no `.duckdb` |
| gold (original) | `bh_empresas` | 71.396.386 | 3,8 GB |
| gold (original) | `agg_empresas` | 5.812.927 | 75 MB |
| gold (core) | `fct_estabelecimentos` | 73.366.147 | 1,26 GB |
| gold (core) | `bridge_estabelecimento_cnae_secundario` | 125.421.187 | 1,57 GB |
| gold (core) | `fct_resumo_mensal` (partição 2026-09) | 5.763.929 | 62 MB |
| gold (core) | dimensões (`dim_data` 46.279, `dim_municipio` 5.572, `dim_cnae` 1.357, natureza 92, porte 5, situação 6) | | < 1 MB |
| gold (analytics) | `mart_dinamica_mercado` 16.138.510; `mart_concorrencia_municipio` e `_area_mercado` 2.027.104; `mart_sobrevivencia_coorte` 1.669.209; `mart_fornecedores_proximos` 1.726 | | 313 MB |
| gold (observabilidade) | `dq_historico_testes/` (RBP-12): uma partição por execução | 6 execuções, 1.570 linhas | — |

Disco: zips 6,7 GB + raw 4,9 GB + gold 6,6 GB + `warehouse.duckdb` 14 GB ≈ **32 GB** por mês
(os zips somem após `rfb atualizar`, salvo `RFB_MANTER_ZIPS=true`).

### Avisos (`warn`) do build real

| Teste | Linhas | Leitura |
|---|---|---|
| `bh_empresas_descartes_inner_join` | 1.969.761 | estabelecimentos que o SQL original descarta nos inner joins (natureza/CNAE/município sem par) — comportamento original preservado; 73.366.147 − 71.396.386 |
| `dat_situacao >= dat_inicio_atividade` (staging) | 1.058 | datas inconsistentes na fonte |
| `bh_empresas_nome_alterado_por_trim` | 861 | nomes com espaço nas bordas (trim declarado, ADR-0005/R2-01) |
| MEI ⇒ Simples (`fct_estabelecimentos`) | 494 | opção MEI sem opção pelo Simples na fonte |
| PIB: `pib ≈ va + impostos` com tolerância de 0,01 % | 477 | arredondamento da BD; o teste de 1 % (error) **passou** (P24, §4) |
| `data_nao_futura` (estabelecimentos: situação 386, início 227; simples: opção Simples 222, MEI 213) | 1.048 | datas posteriores ao extrato na fonte |
| `accepted_range` de `dat_inicio_atividade` ≥ 1900 | 4 | datas absurdas (R2-02), vão para `sk_data = -2` |
| `cnaes_sem_par_bd` | 3 | subclasses RFB sem par na BD |
| `dim_municipio.codigo_rfb` not null | 1 | município sem código RFB (P24, §4) |
| `stg_bd__populacao.id_municipio` not null | 1 | linha de 2025 sem município (§3) |
| unicidade de `empresas.cnpj_raiz` na fonte | 1 | raiz duplicada no extrato (§3) |

`extrato_desatualizado` passou (extrato de 2026-09-12, 19 dias). Os avisos ficam com
`store_failures` no warehouse e no histórico de DQ (`gold/dq_historico_testes/`).

### Memória e threads (P14)

Builds completos do `dbt build` (2026-09, mesmos dados), pico de RSS do processo do dbt
(`/usr/bin/time -l`):

| `DBT_THREADS`/`DUCKDB_THREADS` | `DUCKDB_MEMORY_LIMIT` | `dbt build` | Pico de RSS | Resultado |
|---|---|---|---|---|
| 8 / 8 | 24 GB (padrão `dev`) | 318 s | **25,9 GB** | ERROR=0 |
| 4 / 4 | 24 GB | 383 s | 24,9 GB | ERROR=0 |
| 4 / 4 | 12 GB | 431 s | **18,7 GB** | ERROR=0 |
| 4 / 4 | 8 GB | 460 s | **13,8 GB** | ERROR=0 |

O pico acompanha o `memory_limit` do DuckDB, não as threads: o limite vale para o buffer manager, e o
processo soma a ele os buffers de leitura de Parquet, o próprio dbt e o Python (~1–2 GB). Reduzir as
threads de 8 para 4 só baixou o pico em 1 GB e custou 20 % de tempo; reduzir o limite de 24 para 12 GB
baixou 7 GB e custou 35 %; com 8 GB o pico ficou em 13,8 GB (+45 % de tempo). O spill foi para `RAIZ_DADOS/_tmp` (`temp_directory`).

**Recomendação** (em `docs/OPERACAO.md`): máquina com **≥ 32 GB de RAM** com os padrões, ou
`DUCKDB_MEMORY_LIMIT` ≈ metade da RAM física. Máquina de 16 GB: `DUCKDB_MEMORY_LIMIT=8GB` e `DBT_THREADS=DUCKDB_THREADS=4` (pico medido 13,8 GB; apertado, feche outros programas — não testado numa máquina de 16 GB de fato).

## 2. Correções exigidas pelos dados reais

A primeira execução real falhou (corretamente, saída 1) e expôs quatro problemas, todos resolvidos neste
lote e cobertos por testes:

| Problema | Sintoma | Decisão |
|---|---|---|
| Bytes 0x80–0x9F (controles C1) em 5 campos de `Estabelecimentos0/4/7` | o DuckDB recusa o arquivo: "File is not latin-1 encoded" (o latin-1 do Python aceita) | conversão relê o CSV após transcodificar latin-1 → UTF-8 em Python, só quando o DuckDB recusa; aviso com a contagem (`conversao.py`, teste `test_bytes_de_controle_c1_sao_relidos_em_utf8`). Escopo adaptado |
| Raiz `08314885` duplicada em `Empresas2` (linha "fantasma": sem razão social, natureza 0000, porte e qualificação zerados) | `unique` da fonte (error) falhou; o SQL original duplicaria os 51 estabelecimentos da raiz | staging mantém uma linha por raiz (`empresa_preferida_por_raiz`: com razão social e natureza ≠ 0000), a leitura da paridade emula o mesmo; teste da fonte vira `warn` + `store_failures`; unit test `test_stg_rfb__empresas_raiz_duplicada_vira_uma_linha`. Escopo adaptado (`docs/ESCOPO.md`) |
| Linha da BD `populacao` (2025) sem `id_municipio` nem UF (5.877 hab.) | `not_null` (error) falhou | `warn` + `store_failures`: a linha não casa com município nenhum e não afeta os marts |
| **CNPJ alfanumérico** (`00000000 E08G 12`, Banco do Brasil, o primeiro do extrato) | `paridade_bh_empresas` FAIL 2: a emulação do `inferSchema` fazia `try_cast(cnpj_ordem as bigint)` → NULL | o Spark tiparia a coluna como texto se um valor não fosse inteiro; a emulação passou a fazer o mesmo por coluna e mês (`inferschema_inteiro_ou_texto`, unit test `test_audit__bh_empresas_sql_original_cnpj_alfanumerico`). `bh_empresas` já estava certo |
| `SET temp_directory` reaplicado pelo dbt-duckdb a cada cursor | "Cannot switch temporary directory after the current one has been used" em builds parciais com 8 threads | `temp_directory` passou de `settings` para `config_options` (aplicado uma vez no connect) |

## 3. Paridade numérica com o notebook 4 (fev/2025, AD-018)

Extrato real de **fev/2025** (o mesmo mês do MVP; arquivos internos `…D50208…` → `_data_referencia`
= **2025-02-08**), convertido dos CSVs do projeto v1 (só leitura). Base dos Dados: as 4 tabelas do
original (`municipio`, `cnae_2`, `populacao`, `pib`) na versão usada pelo v1; censo, RM e vizinhança
copiadas do raw de 2026-09 (não existiam no original). Comando:
`RAIZ_DADOS=dados/real-2025-02 rfb pipeline --sem-ingestao --mes 2025-02`.

**Build:** PASS=344 WARN=9 ERROR=0 em 258 s (pico 27,0 GB, 8/8 threads); `paridade_bh_empresas`
PASS (0 diferenças em 62.586.264 linhas; 64.547.773 estabelecimentos, 1.961.509 descartados pelos inner
joins do original). Avisos a mais que em 2026-09: `extrato_desatualizado` (3 entidades: o extrato tem
mais de 65 dias, esperado) e idade fora de [0, 200] (2 linhas).

As consultas do notebook 4 foram reexecutadas **literalmente** (o SQL publicado, sobre o gold do port:
`agg_empresas`, `bh_empresas` e `municipio_bd` = raw da BD):

| Pergunta (notebook 4) | Publicado no original | Port, SQL literal | Port, analysis/relatório | Divergência |
|---|---|---|---|---|
| 1. Concorrentes 4741500 em Fundão/ES | 1 ativa (Empresário Individual) + 4 inativas | 1 ativa (EI, MICRO) + 4 inativas (3 EI + 1 Ltda.) | 1 ativo e 4 inativos | nenhuma |
| 2. Idade média das ativas | **3,9** anos | **3,8** | 3,8 | **explicada (P15)** — abaixo |
| 3. Porte das ativas | MICRO | MICRO (1 empresa) | MICRO | nenhuma |
| 4a. Fabricante (2071100) no município | 0 | 0 | 0 | nenhuma |
| 4b. Fabricante na microrregião | 0 | 0 | **1** | **adaptação declarada (R3-04)** |
| 4c. Fabricante na mesorregião | 0 | 0 | **1** | idem |
| 4d. Atacadistas (4679601, 4679699) na mesorregião | 0 | 0 | **12** | idem |
| 4e. CNAE de fornecedor como secundário na mesorregião | 0 | 0 | **155** | idem |
| 4f. Idem, na UF (ES) | "muitas opções", citando Serra, Vila Velha, Vitória, Cariacica e Linhares | 1.977 ativos; os maiores municípios são Serra (479), Vila Velha (315), Cariacica (246), Vitória (156), Cachoeiro (118), Linhares (65) | 1.977 | nenhuma (o original não publicou a contagem) |

**P15 — idade 3,8 × 3,9.** A única ativa iniciou atividade em **2021-05-06**. O port mede a idade na
data do extrato (ADR-0004): 2025-02-08 − 2021-05-06 = 1.374 dias / 365,25 = **3,76 → 3,8**. O notebook
usava `now()` no momento em que rodou: 3,9 corresponde a qualquer data entre **2025-03-13 e
2025-04-17** (1.407 a 1.442 dias), ou seja, o notebook foi executado de 5 a 10 semanas depois da
publicação do extrato. Reprodução com `--vars` (`dbt run --select bh_empresas agg_empresas --vars
'{mes_referencia: 2025-02, data_referencia: <data>}'` e a consulta da pergunta 2):

| `data_referencia` | Idade média (MICRO, 1 empresa) |
|---|---|
| (padrão: 2025-02-08, data do extrato) | 3,8 |
| 2025-03-12 | 3,8 |
| **2025-03-13** | **3,9** |
| **2025-04-17** | **3,9** |
| 2025-04-18 | 4,0 |

A diferença é a adaptação declarada do ADR-0004 (determinismo), não erro de cálculo.

**Pergunta 4 (R3-04).** O SQL literal do notebook dá 0 nas buscas por micro e mesorregião porque compara
`microrregiao_municipio`/`mesorregiao_municipio` de `agg_empresas` (MAIÚSCULAS, herdadas do SQL do
notebook 3) com `nome_microrregiao`/`nome_mesorregiao` da BD em grafia mista ("Linhares"): o port
reproduz esse 0 com o SQL literal, e a analysis adaptada (`upper()` dos dois lados) mostra o que o
original deveria ter achado — 1 fabricante na micro/mesorregião, 12 atacadistas e 155 estabelecimentos
com o CNAE de fornecedor como secundário. A conclusão do notebook ("não há fornecedores nas
imediações") decorre desse bug; o relatório do port traz a nota de adaptação.

**2026-09 para comparação:** a empresa ativa de 2025 passou a inativa; em 2026-09 Fundão tem **0 ativos
e 5 inativos** no CNAE 4741500 (relatório em `docs/RELATORIO_ESTUDO_CASO.md`).

## 4. Conferências P24 (dados reais)

- **`dim_municipio.codigo_rfb` not null (warn):** 1 linha, exatamente a prevista — Boa Esperança do
  Norte/MT (IBGE 5101837, criado em 2025), sem `id_municipio_rf` na BD. Fica na dimensão (para o BI),
  não casa com estabelecimentos; `unique` de `codigo_rfb` passou. **Mantido como warn.**
- **Identidade `pib ≈ va + impostos_liquidos`:** o teste de **1 % (error, RBP-06) passou** nas 122.466
  linhas. O de 0,01 % (warn) acusou 477 linhas, todas com diferença de **exatamente R$ 1.000** (máximo
  0,037 % do PIB; ex.: 2210383/2002, PIB 2.720.000 × VA + impostos 2.721.000): é o arredondamento em
  milhares das séries antigas do IBGE convertidas para reais, não troca de coluna nem de unidade.
  **Decisão: manter** error em 1 % e warn em 0,01 % (o aviso documenta o arredondamento; um erro real
  de unidade daria diferenças de 1.000× ou de 100 %).
- **População sem município (warn novo, §2):** 1 linha (2025, 5.877 habitantes, sem `id_municipio` nem
  UF) — provavelmente o mesmo município novo; não casa com nada e não afeta densidade.

## 5. Atualização mensal real (T36)

`RAIZ_DADOS=dados/real-2026-09 rfb atualizar`, depois do pipeline de 2026-09, contra o WebDAV da RFB:

```
nenhum mês novo (mais recente completo: 2026-09; último processado: 2026-09)
```

Saída 0 em 0,56 s, só com a listagem (PROPFIND): nenhum arquivo baixado (`_baixados/2026-09/`
inalterado), nenhum dbt executado. Em 2026-10-01 a pasta de 2026-10 ainda não existia no WebDAV.
O fluxo com mês novo, falha do dbt e retenção roda a cada `make ci` sobre as fixtures de dois meses
(`tests/integration/test_atualizar.py`).
