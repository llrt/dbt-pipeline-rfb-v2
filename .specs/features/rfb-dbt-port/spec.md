# Port RFB/CNPJ para dbt + DuckDB Specification

## Problem Statement

O MVP original (Databricks CE + Spark, notebooks) monta uma base de inteligência de mercado a partir dos
dados abertos de CNPJ da RFB e da Base dos Dados, mas não é reprodutível fora do Databricks, não tem testes
automatizados, depende de `now()` e sofre com limites da plataforma. Precisamos de um pipeline dbt sobre
DuckDB + Parquet (local ou S3/Tigris) que preserve as regras originais, meça a qualidade dos dados antes e
depois de cada etapa e acrescente análises que respondam melhor às perguntas de negócio.

## Goals

- [ ] Um comando (`make pipeline`) reconstrói raw → gold do mês de referência a partir das fontes públicas.
- [ ] `bh_empresas`/`agg_empresas` com paridade lógica comprovada por teste contra o SQL original.
- [ ] `make ci` roda o fluxo completo sobre fixtures sintéticas em < 2 min, sem rede, verificando os números do cenário conhecido.
- [ ] Todos os checks de qualidade dos notebooks 2.x do original automatizados como testes dbt, mais novos checks por etapa.
- [ ] Quatro análises novas (densidade, sobrevivência por coorte, dinâmica, fornecedores por distância) + estudo de caso Fundão/ES reproduzido.
- [ ] Guia de dbt em português cobrindo conceitos, estrutura, comandos, fluxo, testes, bibliotecas e checks por etapa.

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Ingestão de `Socios*` | Dados de pessoas físicas; não respondem às perguntas (ADR-0008) |
| Orquestrador (Airflow, Dagster) | `rfb atualizar` é idempotente; receitas de agendamento (cron/launchd/GitHub Actions) documentadas, não executadas (ADR-0012) |
| Dashboard/UI pronto (arquivo .pbix) | Entregamos o modelo estrela em Parquet + guia Power BI; montar o relatório é do usuário (ADR-0013) |
| Snapshots SCD2 por estabelecimento | Volume (~65 M × meses); tendência coberta pela série agregada `fct_resumo_mensal` (ADR-0012) |
| Geocodificação por endereço | Distância usa centroide do município |
| Validação real no Tigris | Sem credenciais no ambiente; coberto por moto + roteiro manual |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Mês de referência | Último mês listado no WebDAV (2026-09 hoje); `--mes` sobrescreve | 2025-02 do original não existe mais (ADR-0003) | y (líder) |
| Paridade com o original | Lógica (mesmas regras nos mesmos dados), não numérica | Dados de outro mês | y (líder) |
| Idade das empresas | Relativa a `data_referencia` (data do extrato), não `now()` | Determinismo (ADR-0004) | y (líder) |
| "Inativa" | `situacao_codigo != 2` (regra original); data de encerramento = `dat_situacao` | Consistência com o original | y (líder) |
| Sobrevivência a N anos | Coorte = ano de `dat_inicio`. A coorte inteira é elegível no horizonte N se `make_date(ano_coorte + N, 12, 31) <= data_referencia`; um membro sobrevive se ativo ou `dat_situacao >= dat_inicio + N anos` | Elegibilidade por coorte inteira garante sobreviventes_N ⊆ sobreviventes_M (N>M) e, portanto, taxas monotônicas | y (líder) |
| População usada | Último `ano` disponível em `br_ibge_populacao.municipio` (var `ano_populacao` sobrescreve) | Dado mais recente | y (líder) |
| Distância | Haversine, raio 6371.0088 km, entre centroides BD | Sem geocodificação (out of scope) | y (líder) |
| Nomes de colunas | snake_case minúsculo (`CNAE_principal` → `cnae_principal`, `UF` → `uf`) | Convenção dbt; mapeamento em docs/ESCOPO.md | y (líder) |
| Strings vazias na RFB | Convertidas para NULL no staging | Spark do original tratava vazio como null | y (líder) |
| Limiar de rejeito do parser | 0,0001 (0,01%) | Original não teve rejeitos após ajuste de escape | y (líder) |

**Open questions:** none - all resolved or logged above (required before the spec is confirmed).

---

## Cenário de fixtures com respostas conhecidas (fonte dos valores esperados)

`data_referencia = 2026-09-12`, `mes_referencia = 2026-09`. Nomes internos iguais aos reais de 2026-09: `K3241.K03200Y0.D60912.EMPRECSV` (Empresas0), `K3241.K03200Y0.D60912.ESTABELE` (Estabelecimentos0), `F.K03200$W.SIMPLES.CSV.D60912` (Simples), `F.K03200$Z.D60912.<CNAECSV|MUNICCSV|NATJUCSV|MOTICSV|PAISCSV|QUALSCSV>` (domínios). Formato real: separador `;`, **todos** os campos entre aspas, fim de linha LF, latin-1; datas vazias vêm como `"00000000"` (Simples) ou `""`; `dat_situacao` de ativos = data de início. `D60912` = ano cujo último dígito é 6 (resolvido pelo mês de referência) + `0912`.

**Domínios RFB:** municípios `5643 FUNDAO`, `5663 LINHARES`, `5611 ARACRUZ`, `5699 SERRA`, `5705 VITORIA`,
`2701 AGUA BRANCA`, `1003 AGUA BRANCA`, `1901 AGUA BRANCA`, `9707 EXTERIOR`, `1182 BOA ESPERANCA DO NORTE`;
CNAEs `4741500, 2071100, 4679601, 4679699, 4711302, 4744099, 0111301, 3511500`; naturezas `2062, 2135, 2305,
0000 "Natureza Jurídica não informada", 8885 "Natureza Jurídica não informada"`; motivos `00, 01`.

**BD:** municípios = os 8 acima exceto 9707 e 1182 (ids IBGE, nomes acentuados, micro/meso, regiões
imediata/intermediária e centroides reais: Fundão `POINT(-40.3557928987053 -19.9687204052472)`, Serra
`POINT(-40.3011804058758 -20.1284748148379)`, Linhares `POINT(-40.0286164065601 -19.3821001934877)`,
Aracruz `POINT(-40.1758978602985 -19.7659695292442)`, Vitória `POINT(-39.176338320945 -20.3338472806447)`,
Água Branca/AL `POINT(-37.9018536858562 -9.27325871173002)`); CNAE 2 = os CNAEs acima exceto `3511500`, com
pelo menos um registro multilinha; população 2024: Fundão 20000, Linhares 180000, Aracruz 100000, Serra
520000, Vitória 330000, cada Água Branca 10000; população 2023: Fundão 19000.

**BD — incremento `enriquecimento_bd` (ADR-0015; adições ao cenário, nenhuma resposta acima muda):**

| Tabela (arquivo `bd/…csv.gz`) | Conteúdo da fixture |
|---|---|
| `censo_2022_municipio` | 7 municípios (Água Branca/PI **ausente** de propósito: denominadores NULL). **Fundão** = Censo real: 6715 domicílios, 17951 hab., 287 km², alfabetização 0,93371, idade mediana 37, razão de sexo 97,67, índice de envelhecimento 67,68. Linhares 55000 dom./166786 hab./3502 km²; Aracruz 40000/94765/1436; Serra 160000/520653/553; Vitória 140000/322869/93; Água Branca/AL 3300/9873/454; Água Branca/PB 3200/9000/236 |
| `regiao_metropolitana_2017` | `RM Grande Vitória` (tipo `RM`) com **Fundão, Serra e Vitória**; Linhares, Aracruz e as Águas Brancas ficam sem RM (`NÃO PERTENCE`); `geometria` sintética, descartada no staging |
| `vizinhanca_municipio` | ano **2020** (mais recente): Fundão–Aracruz (duplicada), Fundão–Serra, Serra–Vitória (nos dois sentidos), Aracruz–Linhares, autopar Linhares–Linhares; ano **2019** (deve ser ignorado): Fundão–Linhares. Pares só em um sentido: o modelo simetriza. **Vizinhos conformados de Fundão = {Aracruz, Serra}**; Serra = {Fundão, Vitória}; Aracruz = {Fundão, Linhares}; Linhares = {Aracruz}; Vitória = {Serra} |

Respostas derivadas para (CNAE 4741500, Fundão): `densidade_hab_km2` de Fundão = 17951/287 ≈ 62,55; Fundão no município: ativos 1, inativos 4; nos vizinhos (Aracruz + Serra): ativos 1 (O, Serra), inativos 0; na região metropolitana (Fundão + Serra + Vitória): ativos 2, inativos 4; ativos por mil domicílios (município) = 1/6715×1000 ≈ 0,1489; ativos por km² (município) = 1/287 ≈ 0,003484.

**Estabelecimentos** (todos com DV correto, exceto L):

| id | cnpj_raiz/ordem | razão social (empresa) | natureza | porte | município | CNAE principal | situação | início | dat_situacao | observação |
|---|---|---|---|---|---|---|---|---|---|---|
| A | 11111111/0001 | TINTAS FUNDAO LTDA | 2135 | 01 | 5643 | 4741500 | 02 | 20221015 | — | nome_fantasia `TINTAS FUNDÃO` |
| B | 22222222/0001 | COLORIR TINTAS | 2062 | 03 | 5643 | 4741500 | 08 | 20150301 | 20190510 | |
| C | 33333333/0001 | PINTE BEM 52998224725 | 2135 | 01 | 5643 | 4741500 | 08 | 20200110 | 20210815 | capital `1000,50`; **emenda R4-01**: razão social de EI com CPF sintético (DV válido) depois de um espaço → `bh_empresas.nome` = `PINTE BEM ***.***.***-**` |
| D | 44444444/0001 | CASA DAS CORES | 2062 | 05 | 5643 | 4741500 | 04 | 20100601 | 20230101 | |
| E | 55555555/0001 | TINTAS CAPIXABA | 2305 | (vazio) | 5643 | 4741500 | 08 | 20180101 | 20240301 | nome_fantasia vazio |
| F | 66666666/0001 | FABRICA DE TINTAS SERRA SA | 2062 | 05 | 5699 | 2071100 | 02 | 20000101 | — | |
| G | 77777777/0001 | ` ATACADO VITORIA TINTAS` (espaço à esquerda no arquivo) | 2062 | 03 | 5705 | 4679601 | 02 | 20050505 | — | sem nome fantasia: `nome` = `ATACADO VITORIA TINTAS` (trim, ADR-0005 emenda R2-01); paridade passa e o warn de trim acusa só G |
| H | 88888888/0001 | MERCADO LINHARES | 2062 | 03 | 5663 | 4711302 | 02 | 20120312 | — | secundários `4679699,4744099` |
| I | 99999999/0001 | ATACADO ARACRUZ | 2062 | 01 | 5611 | 4679601 | 08 | 20080101 | 20200101 | |
| J | 12121212/0001 | TINTAS SERTAO | 2062 | 01 | 2701 | 2071100 | 02 | 20190101 | — | |
| K | 13131313/0001 | `EMPRESA EXTERIOR LTDA\` (com `\"` no arquivo) | 2062 | 00 | 9707 | 4711302 | 02 | 20210101 | — | quirk de escape |
| L | 14141414/0001 | ENERGIA NOVA | 2062 | 05 | 5699 | 3511500 | 02 | 20160101 | — | **DV inválido**; CNAE sem par no BD |
| M | 15151515/0001 | BOA ESPERANCA COMERCIO | 2135 | 01 | 1182 | 4711302 | 02 | 20231201 | `00000000` | município sem par no BD |
| N | 16161616/0001 | AGRO FUNDAO | 2135 | 00 | 5643 | 0111301 | 02 | 20000229 | — | CNAE com zero à esquerda |
| O | 11111111/0002 | (filial de A) | — | — | 5699 | 4741500 | 02 | 20240115 | — | matriz_filial 2; nome_fantasia multilinha |
| P | 17171717/0001 | TINTAS ARACRUZ IND11144477735 | 2062 | 03 | 5611 | 2071100 | 02 | 20180301 | — | **emenda R3-04**: fabricante ativo na microrregião de Fundão (Linhares), fora do município; **emenda R4-01**: CPF sintético colado ao nome → `mart_fornecedores_proximos.nome` = `TINTAS ARACRUZ IND***.***.***-**` |

Empresas: as 15 raízes acima (O compartilha a raiz de A), mais uma linha "fantasma" que repete a raiz de B sem razão social, natureza `0000`, porte/qualificação `00` e capital `0,00` (**emenda R4-05**: o arquivo tem 16 linhas e 15 raízes; o staging e a paridade ficam com a linha boa e nenhuma resposta muda). Simples: A e C optantes pelo MEI (`opcao_mei = S`).

**Segundo mês (2026-08, para atualização/série):** pasta `rfb/2026-08/` idêntica à de 2026-09 **exceto**: (a) sem a linha O (a filial de Serra só aparece no extrato de 2026-09); (b) nomes internos com `D60810` (`_data_referencia = 2026-08-10`). Logo 2026-08 tem 15 estabelecimentos e 15 empresas (raízes; 16 linhas com a "fantasma" de B). As respostas de 2026-09 acima não mudam.

---

## User Stories

### P1: Ingestão reprodutível para Parquet raw ⭐ MVP

**User Story**: Como engenheiro(a) de dados, quero baixar e converter os arquivos da RFB e da BD para Parquet raw com um comando, para que o dbt trabalhe sobre dados fiéis e auditáveis.

**Why P1**: Sem raw não há pipeline.

**Acceptance Criteria**:

1. WHEN `rfb ingerir` runs without `--mes` THEN the system SHALL select the most recent **complete** `YYYY-MM` folder listed by the WebDAV share. *(Emenda R4-07: o código e o UPD AC 3 usam o mais recente completo.)*
2. WHEN `rfb ingerir --mes 2026-09` runs THEN the system SHALL write one Parquet dataset per entity under `raw/rfb/<entidade>/mes_referencia=2026-09/` for `empresas, estabelecimentos, simples, cnaes, municipios, naturezas, motivos, paises, qualificacoes`.
3. The system SHALL store every RFB data column as VARCHAR using the column names listed in ARCHITECTURE.md §4.2, plus `_arquivo_origem`, `_mes_referencia`, `_data_referencia`, `_ingerido_em`.
4. WHEN a field contains `\"` before the closing quote (row K) THEN the system SHALL parse it as a value ending in `\` without rejecting the row.
5. WHEN a quoted field spans multiple lines (row O) THEN the system SHALL keep it as a single record.
6. WHEN the fixtures are ingested THEN the system SHALL write exactly 15 `empresas` rows, 16 `estabelecimentos` rows and 0 rejected rows.
7. WHEN the internal file name contains `D60912` THEN the system SHALL set `_data_referencia` to `2026-09-12`.
8. IF the rejected-row rate for an entity exceeds `RFB_MAX_TAXA_REJEITO` THEN the system SHALL exit non-zero and SHALL keep the rejected rows under `raw/_rejeitos/`.
9. IF a downloaded file size differs from the WebDAV `getcontentlength` THEN the system SHALL delete the file and exit non-zero without writing to `raw/`.
10. IF a network error persists after 3 attempts THEN the system SHALL exit non-zero naming the file.
11. IF the requested month does not exist THEN the system SHALL exit non-zero listing the available months.
12. WHEN the same month is ingested twice with identical zip checksums THEN the system SHALL skip conversion and leave the Parquet files unchanged.
13. The system SHALL never leave a partially written Parquet dataset under `raw/` (write to temp + atomic rename).
14. WHEN ingestion finishes THEN the system SHALL write `_manifestos/<mes>.json` with size, sha256, rows read and rows rejected per file.
15. WHEN `rfb ingerir` runs THEN the system SHALL download the four BD tables (municipio, cnae_2, populacao, pib) to `raw/bd/<tabela>/`.
16. IF a zip entry path escapes the extraction directory THEN the system SHALL refuse to extract it and exit non-zero.
17. The system SHALL NOT download `Socios*` files.

**Independent Test**: `rfb ingerir --origem-local tests/fixtures --mes 2026-09` produces the datasets and manifest; pytest checks counts and quirks.

---

### P1: Staging e fontes com os checks do original ⭐ MVP

**User Story**: Como analista, quero fontes declaradas com os mesmos checks de qualidade dos notebooks 2.x e um staging tipado, para confiar nos dados antes de modelar.

**Why P1**: Checks do original fazem parte do escopo; staging é a base de tudo.

**Acceptance Criteria**:

1. The system SHALL declare dbt sources for every raw dataset with `external_location` derived from `env_var('RAIZ_DADOS')`.
2. The system SHALL test `unique` and `not_null` on `codigo` of `cnaes`, `municipios`, `naturezas`, `motivos` (notebook 2.1.1).
3. The system SHALL test `unique` + `not_null` on `empresas.cnpj_raiz` and on the concatenated `cnpj_completo` of `estabelecimentos` (notebooks 2.2/2.3).
4. The system SHALL test that `empresas.natureza_jur`, `estabelecimentos.cnae_principal` and `estabelecimentos.municipio` exist in their RFB domain tables (notebooks 2.2/2.3).
5. The system SHALL test `porte ∈ {00,01,03,05}` (nulls allowed) and `situacao ∈ {01,02,03,04,08}`.
6. The system SHALL test that RFB municipalities without a BD pair are exactly those listed in seed `excecoes_conhecidas_municipio` (fixtures: 9707, 1182), with severity error for any other.
7. WHEN RFB CNAEs have no BD pair THEN the system SHALL raise a `warn` reporting their count (fixtures: 1).
8. WHILE `_ingerido_em` is older than 35 days the system SHALL report source freshness `warn`, and older than 65 days `error`. *(Emenda RBP-04: `dbt source freshness --target ci` roda no `make ci`; como `_ingerido_em` mede quando ingerimos e não a data do extrato, o teste singular `extrato_desatualizado` — `warn`, ativo só fora do target `ci` — avisa quando o `_data_referencia` mais recente de `empresas`, `estabelecimentos` ou `simples` é mais velho que `limite_dias_extrato` = 65 dias.)*
9. WHEN staging runs THEN `stg_rfb__estabelecimentos.cnpj_completo` SHALL be `lpad(raiz,8)||lpad(ordem,4)||lpad(dv,2)` with exactly 14 digits.
10. WHEN a date field is `0`, `00000000` or not a valid `YYYYMMDD` THEN staging SHALL output NULL.
11. WHEN `capital_soc` is `1000,50` THEN `stg_rfb__empresas.capital_social` SHALL equal 1000.50.
12. WHEN a text field is empty THEN staging SHALL output NULL.
13. The system SHALL pad CNAE codes to 7 digits (`0111301`) and RFB municipality codes to 4 digits.
14. The system SHALL NOT expose `email`, `ddd1`, `tel1`, `ddd2`, `tel2`, `ddd_fax`, `fax` in any staging or downstream model.
15. WHERE `mes_referencia` var is null the staging SHALL select the greatest available `_mes_referencia`.

**Independent Test**: `dbt build --select staging+ sources --target ci` passes with the listed warns only.

---

### P1: Modelos originais com paridade ⭐ MVP

**User Story**: Como avaliador(a), quero `bh_empresas` e `agg_empresas` com as regras do notebook 3, para comparar com o MVP original.

**Why P1**: É o núcleo do escopo original.

**Acceptance Criteria**:

1. The system SHALL build `bh_empresas` with exactly the columns `cnpj_raiz, cnpj_completo, nome, natureza_juridica, porte, cnae_principal, desc_cnae_principal, grupo_cnae_principal, cnaes_secundarios, municipio, microrregiao_municipio, mesorregiao_municipio, uf, situacao, idade_atual` under an enforced contract.
2. WHEN built on fixtures THEN `bh_empresas` SHALL contain 13 rows (16 minus K, L, M dropped by the original inner joins).
3. The system SHALL map porte `0→'N/A'`, `1→'MICRO'`, `3→'PEQUENA'`, `5→'DEMAIS'`, otherwise NULL (row E → NULL).
4. The system SHALL map situação `2→'ATIVA'`, otherwise `'INATIVA'`.
5. WHEN situação is ATIVA THEN `idade_atual` SHALL be `round(days(data_referencia − dat_inicio)/365.25, 1)` (row A → 3.9); otherwise NULL.
6. The system SHALL set `nome = upper(coalesce(nome_fantasia, razao_social))` (row A → `TINTAS FUNDÃO`, row E → `TINTAS CAPIXABA`).
7. The system SHALL set `municipio`, `microrregiao_municipio`, `mesorregiao_municipio`, `uf`, `desc_cnae_principal`, `grupo_cnae_principal`, `natureza_juridica` as upper-case values from BD/RFB domains (row A → `FUNDÃO`, `LINHARES`, `LITORAL NORTE ESPÍRITO-SANTENSE`, `ES`).
8. The system SHALL build `agg_empresas` grouped by the 10 original dimensions with `qtd_empresas = count(cnpj_completo)` and `media_idade = avg(idade_atual)`.
9. The system SHALL fail (error) if `sum(agg_empresas.qtd_empresas) != count(bh_empresas)`.
10. The system SHALL fail (error) if `bh_empresas` differs from the literal DuckDB translation of the notebook 3 SQL (same data, with `now()` replaced by `data_referencia`).
11. The system SHALL report (warn) the number of estabelecimentos dropped by the inner joins (fixtures: 3).
12. IF any `idade_atual` is outside [0, 200] THEN the system SHALL report it as `warn`, and SHALL fail (error) when more than 100 rows are outside the range (emenda R2-02: o extrato real contém inícios de atividade absurdos, ex. 1194).
13. The system SHALL cover rules 3–6 with dbt unit tests.

**Independent Test**: fixtures → `agg_empresas` for `cnae_principal='4741500'`, `municipio='FUNDÃO'`, `uf='ES'` returns ATIVA=1 (MICRO, media_idade 3.9) and INATIVA totaling 4.

---

### P2: Star schema conformado (adição)

**User Story**: Como analista, quero dimensões e fato sem descartes silenciosos, com Simples/MEI e CNAEs secundários explodidos, para análises completas.

**Why P2**: Corrige limitações do original ("trabalhos futuros"), não bloqueia o MVP.

**Acceptance Criteria**:

1. The system SHALL build `fct_estabelecimentos` with one row per `cnpj_completo` (fixtures: 16 rows) and enforced contract. *(Emenda R4-07: a fixture P, do F3b, elevou de 15 para 16.)*
2. WHEN a estabelecimento has no matching dimension member THEN the fact SHALL reference the "não informado" member (key `-1`) instead of dropping the row.
3. The system SHALL build `dim_municipio` with IBGE id, RFB code, name, UF, micro/meso, região imediata/intermediária, latitude, longitude, população do último ano (Fundão → 20000) and PIB.
4. The system SHALL build `dim_cnae` with subclass, classe, grupo, divisão, seção and descriptions.
5. The system SHALL build `bridge_estabelecimento_cnae_secundario` with one row per (cnpj_completo, CNAE secundário) (row H → 2 rows).
6. The system SHALL flag `opcao_mei` on the fact (rows A, C and O → true; O is a branch of A and inherits the root's option). *(Emenda R4-07.)*
7. The system SHALL test `relationships` from every fact foreign key to its dimension with severity error.

**Independent Test**: fixtures → fact 16 rows; K, L, M present with key -1 on the missing dimension.

---

### P2: Análises novas (adição)

**User Story**: Como consultor(a), quero densidade de concorrência, sobrevivência por coorte, dinâmica de mercado e fornecedores por distância, para decidir com mais evidência que o MVP original.

**Why P2**: Valor analítico novo sobre o núcleo.

**Acceptance Criteria**:

1. WHEN built on fixtures THEN `mart_concorrencia_municipio` for (4741500, Fundão) SHALL show ativos=1, inativos=4, ativos_por_10k_hab=0.5.
2. WHEN built on fixtures THEN `mart_sobrevivencia_coorte` summed over cohorts and portes for (4741500, ES) SHALL give eligible/survivors 6/6 at 1 year, 5/4 at 3 years and 4/2 at 5 years.
3. The system SHALL fail (error) if any survival rate is outside [0,1] or if, within a row, taxa_1a < taxa_3a or taxa_3a < taxa_5a when both compared rates are non-null.
4. WHEN built on fixtures THEN `mart_dinamica_mercado` for (4741500, Fundão) SHALL show aberturas in 2010, 2015, 2018, 2020, 2022 (1 each) and encerramentos in 2019, 2021, 2023, 2024 (1 each).
5. WHEN built on fixtures THEN `mart_fornecedores_proximos` for Fundão with CNAEs {2071100, 4679601, 4679699} and radius 100 km SHALL list exactly F (Serra, 18.66 ± 0.5 km, via CNAE principal), P (Aracruz, via CNAE principal; incluído pela emenda R3-04) and H (Linhares, 73.68 ± 0.5 km, via CNAE secundário).
6. The system SHALL exclude inactive suppliers (row I) and suppliers beyond the radius (rows G at ≈129.6 km and J).
7. The system SHALL fail (error) if any distance is negative or if a municipality's distance to itself is not 0.

**Independent Test**: fixtures → queries on the gold Parquet return the numbers above.

---

### P2: Qualidade de dados e observabilidade (adição)

**User Story**: Como engenheiro(a), quero checks novos por etapa e histórico dos resultados, para detectar regressões de qualidade entre meses.

**Acceptance Criteria**:

1. The system SHALL provide a generic test `cnpj_dv_valido` that validates both CNPJ check digits (fixtures: exactly 1 failure, row L, severity warn).
2. The system SHALL provide a generic test `data_nao_futura` relative to `data_referencia` applied to every staging date column, **except** `dat_exclusao_simples` and `dat_exclusao_mei` (a exclusão do Simples/MEI com efeito futuro — fim do mês ou do ano — é legítima; no extrato real de fev/2025 todos os 1.854 e 1.766 avisos eram 2025-02-28 ou 2025-12-31). *(Emenda R3-11.)*
3. The system SHALL store failures of `warn` tests (`store_failures`).
4. WHEN `dbt build` finishes THEN the system SHALL append one row per executed test to `dq_historico_testes` with invocation id, test name, status, failures, severity and escopo.
5. The system SHALL produce `docs/QUALIDADE_DADOS.md` listing every check by stage (antes/depois), marking original vs adição.
6. The system SHALL fail CI if any dbt node lacks `meta.escopo`.

---

### P2: Estudo de caso e relatório (original + adição)

**User Story**: Como consultor(a), quero o estudo de caso de Fundão/ES reproduzido como análises dbt parametrizadas e um relatório gerado.

**Acceptance Criteria**:

1. The system SHALL provide `analyses/` SQL for each question of notebook 4, parameterized by vars `caso_*`.
2. WHEN `rfb relatorio` runs THEN the system SHALL write `docs/RELATORIO_ESTUDO_CASO.md` with the answers of the original questions and of the new analyses for the configured case.
3. WHEN run on fixtures THEN the report SHALL state 1 active competitor and 4 inactive in Fundão/ES for CNAE 4741500.

---

### P1: Operação ponta a ponta ⭐ MVP

**User Story**: Como analista, quero um comando para rodar tudo e um CI local rápido.

**Acceptance Criteria**:

1. WHEN `make ci` runs THEN the system SHALL generate fixtures, ingest them into a temporary `RAIZ_DADOS`, run `dbt build --target ci` and the integration tests, finishing in under 180 s on the reference machine. *(Emenda AD-026/R4-07: era 120 s; o CI passou a rodar unit + lint + freshness + integração.)*
2. WHEN `make pipeline MES=2026-09` runs THEN the system SHALL execute ingest → source freshness → dbt build → reports and exit non-zero if any error-severity test fails.
3. WHERE `RAIZ_DADOS` starts with `s3://` the system SHALL read/write through DuckDB httpfs using `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_ENDPOINT_URL_S3` from the environment.
4. IF `RAIZ_DADOS` is `s3://` and any of those variables is missing THEN the system SHALL exit non-zero naming the missing variables.
5. WHEN `rfb sincronizar` runs THEN the system SHALL upload `raw/` and `gold/` to the configured bucket, skipping objects with identical size and checksum.
6. The system SHALL write gold marts as Parquet under `RAIZ_DADOS/gold/`.

---

### P2: Documentação e guia dbt

**Acceptance Criteria**:

1. The system SHALL provide `docs/guia-dbt/` covering: o que é dbt; como funciona; conceitos (models, sources, seeds, snapshots, tests, macros, packages, materializations, refs/DAG, vars, targets/profiles, docs, exposures, contracts, unit tests); estrutura de projeto; comandos; fluxo de dados por etapa neste projeto; testes; bibliotecas/plugins; checks de qualidade antes/depois de cada etapa.
2. The system SHALL link each guide section to the corresponding files of this project and to official docs.
3. The system SHALL provide `docs/ESCOPO.md` mapping every model/check to original or adição, with the notebook of origin for originals.

---


### P2: Atualização mensal com dados mais recentes (melhoria — pedido do usuário)

**User Story**: Como analista, quero que o pipeline detecte e processe sozinho o mês mais recente publicado pela RFB, mantendo uma série histórica, para ter a base sempre atualizada sem retrabalho.

**Why P2**: Transforma a carga pontual do original num processo recorrente; não bloqueia o MVP.

**Acceptance Criteria**:

1. WHEN `rfb atualizar` runs AND the most recent complete remote month is newer than the last successfully processed month THEN the system SHALL run ingest → `dbt build --vars mes_referencia=<mês>` → reports and SHALL record that month in `RAIZ_DADOS/_estado/ultima_execucao.json`. *(Emenda R4-06: com `RAIZ_DADOS=s3://…` o estado fica em `RAIZ_DADOS_LOCAL/_estado/` — o disco local, não o bucket —, e a retenção do AC 5 apaga só o raw e os zips locais; as partições raw enviadas ao bucket pelo `rfb sincronizar` não são apagadas. Comportamento aceito e documentado em `docs/OPERACAO.md`.)*
2. WHEN the most recent complete month equals the last processed month THEN `rfb atualizar` SHALL exit 0 without downloading any file and SHALL print "nenhum mês novo".
3. IF the most recent remote month folder lacks any expected file (`Empresas0–9`, `Estabelecimentos0–9`, `Simples`, 6 domínios) THEN the system SHALL treat it as incomplete and SHALL select the previous complete month.
4. IF `dbt build` fails THEN `rfb atualizar` SHALL exit non-zero and SHALL NOT update `ultima_execucao.json`.
5. WHEN a month is processed successfully THEN the system SHALL keep only the raw partitions of the last `RFB_MESES_RETIDOS` months (default 2) and SHALL delete that month's downloaded zips unless `RFB_MANTER_ZIPS=true`.
6. The system SHALL persist `fct_resumo_mensal` as one Parquet partition per month under `gold/fct_resumo_mensal/mes_referencia=YYYY-MM/`, surviving deletion of `warehouse.duckdb`.
7. WHEN a month already present in `fct_resumo_mensal` is reprocessed THEN the system SHALL replace only that month's partition.
8. WHEN fixture months 2026-08 then 2026-09 are processed in order THEN `fct_resumo_mensal` SHALL contain both months, with `qtd_estabelecimentos` for (Serra, 4741500, ATIVA) equal to 0 or absent in 2026-08 and 1 in 2026-09.
9. The system SHALL document scheduling recipes for cron, launchd and GitHub Actions in `docs/OPERACAO.md`.

**Independent Test**: fixtures com dois meses → `rfb atualizar --origem-local` processa 2026-09 após 2026-08; segunda chamada imprime "nenhum mês novo".

---

### P2: Modelo estrela otimizado para Power BI (melhoria — pedido do usuário)

**User Story**: Como analista de BI, quero um modelo estrela com chaves inteiras, calendário, hierarquias e uma fato agregada leve, para montar painéis no Power BI sem modelagem adicional.

**Why P2**: Viabiliza consumo self-service ("trabalho futuro" do notebook 5); não bloqueia o MVP.

**Acceptance Criteria**:

1. Every dimension SHALL have a unique, non-null integer surrogate key `sk_*` and a member with key `-1` described as `NÃO INFORMADO`.
2. The system SHALL provide `dim_data` with one row per day from 1900-01-01 to the greatest of `data_referencia` and the greatest valid date of the facts, key `sk_data = yyyymmdd` (integer), and columns `data, ano, semestre, trimestre, mes, nome_mes, ano_mes, dia_semana`, plus member `-1` NÃO INFORMADO (null date) and member `-2` DATA INVÁLIDA (date before 1900, used by the facts; `bh_empresas` keeps the original date). Both members carry a non-null `data` contiguous to the calendar (`-1` → 1899-12-31, `-2` → 1899-12-30) and NULL `ano`/`mes`, so the table can be marked as a date table in Power BI. *(Emenda R3-03, AD-020; antes: do menor dia das fatos até `data_referencia`, só o membro `-1` com data NULL.)*
3. `fct_estabelecimentos` SHALL reference dimensions only through integer keys (`sk_municipio, sk_cnae, sk_natureza_juridica, sk_porte, sk_situacao_cadastral, sk_data_inicio_atividade, sk_data_situacao`), with `-1` when unknown, plus the degenerate `cnpj_completo`.
4. `dim_municipio` SHALL expose the hierarchy columns região, UF, mesorregião, microrregião, município, região intermediária, região imediata; `dim_cnae` SHALL expose seção, divisão, grupo, classe, subclasse with code and description in separate columns.
5. The system SHALL build `fct_resumo_mensal` at grain (`sk_mes_referencia`, `sk_municipio`, `sk_cnae`, `sk_porte`, `sk_situacao_cadastral`, `opcao_mei`) with additive measures `qtd_estabelecimentos`, `qtd_ativos`, `soma_idade_anos`, `qtd_matrizes`, `soma_capital_social_matrizes` (capital social is a company attribute: only the matriz row adds it). *(Emenda R3-01/R3-02, AD-020; antes: grão com `sk_natureza_juridica` e `ano_inicio_atividade` e medida `soma_capital_social` somada por estabelecimento — ~22 M linhas/mês no real e capital 15,6× inflado.)*
6. The system SHALL fail (error) if, for the current month, `sum(fct_resumo_mensal.qtd_estabelecimentos) != count(fct_estabelecimentos)`.
7. The system SHALL provide `docs/POWER_BI.md` with the star diagram, 1:* single-direction relationships, connection steps (Power Query Parquet connector and DuckDB ODBC), incremental refresh by month and at least 8 suggested DAX measures.
8. The system SHALL declare a dbt `exposure` (type `dashboard`) depending on all star-schema models.

**Independent Test**: fixtures → `fct_resumo_mensal` do mês 2026-09 soma 15; todas as FKs resolvem em dimensões; `dim_data` contém `20000229`.

### P2: Enriquecimento com novas bases da Base dos Dados (melhoria — pedido do usuário)

**User Story**: Como analista de mercado, quero o perfil de cada município (Censo 2022) e a noção de área de mercado (vizinhos e região metropolitana), com população e PIB atualizados, para avaliar concorrência e potencial além do próprio município.

**Why P2**: Melhora a qualidade das análises (dados atuais) e responde perguntas que o original não fazia; não bloqueia o MVP. Decisão: ADR-0015, AD-023.

**Acceptance Criteria**:

1. The system SHALL download every Base dos Dados table through `https://basedosdados.org/api/tables/downloadTable` (base64 parameters: dataset, table, `true`, `free`), and SHALL NOT use the legacy `one-click-download` path.
2. WHEN `rfb ingerir` runs, THE system SHALL also ingest `br_ibge_censo_2022.municipio`, `br_geobr_mapas.regiao_metropolitana_2017` and `br_bd_vizinhanca.municipio` into the raw layer (all-VARCHAR, manifest, same reject/emptiness rules as the other BD tables), and `--origem-local` SHALL read them from `<origem>/bd/`.
3. `dim_municipio` SHALL expose `populacao_censo_2022`, `domicilios_2022`, `area_km2`, `densidade_hab_km2`, `taxa_alfabetizacao`, `idade_mediana`, `indice_envelhecimento`, `razao_sexo` and `nome_regiao_metropolitana` (`NÃO PERTENCE` when the municipality is in no metropolitan region; member `-1` keeps `NÃO INFORMADO`).
4. The system SHALL provide a conformed neighbourhood relation (pairs of neighbouring municipalities by `sk_municipio`, latest year, symmetric, no self-pairs) tested for uniqueness and referential integrity.
5. The system SHALL provide `mart_concorrencia_area_mercado` per CNAE × municipality with active and inactive establishments in the municipality, in its neighbours and in its metropolitan region, plus active establishments per 1,000 households and per km² (NULL when the denominator is missing).
6. The case-study report SHALL include the market-area view for the case municipality and CNAE.
7. Every artifact of this increment SHALL carry `meta.incremento: enriquecimento_bd` and tag `incremento_enriquecimento_bd` (dbt nodes) or the equivalent marker in Python/docs (ADR-0015), and the scope guard SHALL fail when `meta.incremento` and the tag disagree.
8. WHERE fixtures are used, THE answers for Fundão/ES and CNAE 4741500 SHALL be documented in the fixture scenario table and asserted by integration tests (neighbours, metropolitan region, per-household and per-km² indicators).

**Independent Test**: fixtures → Fundão pertence à região metropolitana definida na fixture, tem os vizinhos da fixture e os indicadores da área de mercado com os valores da tabela do cenário.

### P2: Publicação no MotherDuck e acesso pelo Power BI (melhoria — pedido do usuário)

**User Story**: Como analista de BI, quero publicar as tabelas finais numa conta MotherDuck quando ela estiver configurada e saber exatamente como o Power BI acessa os dados (Parquet, DuckDB local ou MotherDuck), para escolher o caminho certo para o meu cenário.

**Why P2**: Facilita o consumo compartilhado e o DirectQuery; não bloqueia o MVP. Decisão: ADR-0016, AD-025.

**Acceptance Criteria**:

1. WHEN `rfb publicar --destino motherduck` runs AND `MOTHERDUCK_TOKEN` and `MOTHERDUCK_BANCO` are set, THE system SHALL recreate in the MotherDuck database one table per gold dataset (dimensions, facts, bridges, original and analytics marts, and every partition of `fct_resumo_mensal`) from the Parquet files, and SHALL report table names and row counts.
2. IF `MOTHERDUCK_TOKEN` or `MOTHERDUCK_BANCO` is missing, THEN the command SHALL publish nothing and SHALL exit 0 with a clear message.
3. The publication SHALL accept a selection of tables (`--tabelas`) and SHALL be idempotent (re-running replaces the tables).
4. The token SHALL never be logged, written to files or committed.
5. `docs/POWER_BI.md` SHALL describe the access options — Parquet in `gold/`, local DuckDB file through the DuckDB ODBC driver, MotherDuck through the PostgreSQL endpoint — with Import/DirectQuery support, installation, refresh in Power BI Service (gateway), file-locking caveats and a recommendation per scenario.

**Independent Test**: publicação num destino DuckDB local (arquivo) recria as tabelas do gold com as mesmas contagens; sem as variáveis, o comando não publica e sai 0.

---

## Edge Cases

- IF the WebDAV share is unreachable THEN the system SHALL exit non-zero after retries with the URL in the message.
- IF a BD table download fails THEN the system SHALL exit non-zero without partial Parquet.
- WHEN a CNAE secundário list is empty THEN the bridge SHALL have no rows for that estabelecimento.
- WHEN `dat_inicio_atividade` is NULL THEN `idade_atual` SHALL be NULL and the row SHALL be excluded from cohort analyses.
- WHEN a municipality has no population row THEN density SHALL be NULL (not zero, not error).

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| ING-01 | P1: Ingestão (AC 1, 11) | Tasks | In Tasks |
| ING-02 | P1: Ingestão (AC 2, 3, 7, 17) | Tasks | In Tasks |
| ING-03 | P1: Ingestão (AC 4, 5, 6, 8) | Tasks | In Tasks |
| ING-04 | P1: Ingestão (AC 9, 10, 13, 16) | Tasks | In Tasks |
| ING-05 | P1: Ingestão (AC 12, 14) | Tasks | In Tasks |
| ING-06 | P1: Ingestão (AC 15) | Tasks | In Tasks |
| SRC-01 | P1: Staging/fontes (AC 1–8) | Tasks | In Tasks |
| STG-01 | P1: Staging/fontes (AC 9–15) | Tasks | In Tasks |
| ORI-01 | P1: Originais (AC 1–7, 12, 13) | Tasks | In Tasks |
| ORI-02 | P1: Originais (AC 8, 9) | Tasks | In Tasks |
| ORI-03 | P1: Originais (AC 10, 11) | Tasks | In Tasks |
| CORE-01 | P2: Star schema (AC 1–7) | Tasks | In Tasks |
| ANA-01 | P2: Análises (AC 1) | Tasks | In Tasks |
| ANA-02 | P2: Análises (AC 2, 3) | Tasks | In Tasks |
| ANA-03 | P2: Análises (AC 4) | Tasks | In Tasks |
| ANA-04 | P2: Análises (AC 5–7) | Tasks | In Tasks |
| DQ-01 | P2: DQ (AC 1, 2, 3, 6) | Tasks | In Tasks |
| DQ-02 | P2: DQ (AC 4, 5) | Tasks | In Tasks |
| CASE-01 | P2: Estudo de caso (AC 1–3) | Tasks | In Tasks |
| OPS-01 | P1: Operação (AC 1, 2, 6) | Tasks | In Tasks |
| OPS-02 | P1: Operação (AC 3–5) | Tasks | In Tasks |
| DOC-01 | P2: Documentação (AC 1–3) | Tasks | In Tasks |
| UPD-01 | P2: Atualização mensal (AC 1–5, 9) | Tasks | In Tasks |
| UPD-02 | P2: Atualização mensal (AC 6–8) | Tasks | In Tasks |
| BI-01 | P2: Modelo estrela BI (AC 1–4) | Tasks | In Tasks |
| BI-02 | P2: Modelo estrela BI (AC 5–8) | Tasks | In Tasks |
| ENR-01 | P2: Enriquecimento Base dos Dados (AC 1–2) | T38, T39 | In Tasks |
| ENR-02 | P2: Enriquecimento Base dos Dados (AC 3–4) | T40 | In Tasks |
| ENR-03 | P2: Enriquecimento Base dos Dados (AC 5–8) | T39–T41 | In Tasks |
| PUB-01 | P2: Publicação MotherDuck (AC 1–4) | T42 | In Tasks |
| PUB-02 | P2: Acesso pelo Power BI (AC 5) | T43 | In Tasks |

**Coverage:** 31 total, 31 mapped to tasks, 0 unmapped.

---

## Success Criteria

- [ ] `make ci` verde em < 180 s, com os números do cenário conhecido. *(Emenda AD-026: era < 120 s; o `make ci` passou a incluir testes unitários, lint, freshness e ~105 testes de integração — 117 s medidos.)*
- [ ] `make pipeline MES=2026-09` conclui sobre os dados reais sem testes `error` falhando.
- [ ] Teste de paridade com o SQL original com diferença zero nos dados reais.
- [ ] Relatório do estudo de caso gerado com dados reais de 2026-09.
- [ ] Guia dbt revisado por um revisor independente sem erros técnicos pendentes.
- [ ] `rfb atualizar` processa um mês novo e é no-op quando não há novidade.
- [ ] Modelo estrela carregável no Power BI seguindo `docs/POWER_BI.md`.
