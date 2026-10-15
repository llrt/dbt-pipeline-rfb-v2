# RDIC — Revisão independente do lote DIC (dicionário de dados)

Revisor: agente RDIC (Traycer, Claude Opus), 2026-10-13. Não sou autor de nenhum dos 5 commits. Alvo: branch
`feat/dicionario-dados`, HEAD `07067dc`, `git diff main...HEAD` (base `dd089e3` = v1.1.0). Pedido do usuário: "acrescente
o detalhe dos campos de cada tabela disponível na base". Não alterei código, YAML, docs nem testes. As mutações foram
aplicadas e revertidas com `git checkout`; `git status --porcelain` ficou vazio no fim. O dado real (`dados/` do
checkout principal) foi lido só para leitura: Parquet com `read_parquet` e `warehouse.duckdb` com `read_only=True`.

## Veredito

**APROVÁVEL COM RESSALVAS.** Não há bloqueante. O que mais importava confere:

- O mapeamento coluna → campo do leiaute está certo nas **54 de 54** colunas. O raw é posicional
  (`src/rfb_pipeline/esquemas.py`), e a ordem das tuplas de colunas é a ordem do PDF oficial.
- `coluna_bigquery` e `tabela_bigquery` batem em **88 de 88** colunas e 7 de 7 tabelas com o cabeçalho real da exportação
  `downloadTable` da Base dos Dados.
- O gerador é determinístico no caminho suportado. Duas execuções de `dbt docs generate` com `--no-partial-parse` dão
  saídas idênticas entre si e iguais ao arquivo versionado. Não há caminho absoluto no dicionário.
- O `make ci` está verde.

Há 4 achados importantes. Convém resolvê-los antes do PR A, porque tratam justamente das perguntas que o dicionário
promete responder:

1. **RDIC-01:** "Pode ser nulo? não" é afirmado a partir de testes `warn`. `dim_municipio.codigo_rfb` aparece como
   "não (`not_null`)", mas tem 1 NULL no dado real.
2. **RDIC-02:** o grão declarado da vizinhança ("uma linha por par por ano") é falso. Há 19 duplicatas no raw real, e a
   própria descrição do staging diz "possíveis duplicatas".
3. **RDIC-03:** a coluna **Origem** fica vazia em 304 das 317 colunas de staging, intermediate e gold modelado (dimensões, fatos, pontes e marts analíticos). O
   dicionário não diz de que tabela cada tabela do gold é lida.
4. **RDIC-04:** os **valores** dos códigos não aparecem. Por exemplo, `dim_situacao_cadastral.codigo_situacao_cadastral`
   é `'2'`, mas o raw é `'02'`. As seeds de domínio, que são a resposta, não mostram linhas.

Além disso, 8 das minhas 10 mutações sobreviveram (RDIC-08). Os testes provam que o arquivo está **em dia** com o
gerador, não que o gerador está **certo**. Ninguém testa a semântica do gerador nem a cobertura de `campo_leiaute`.

Execução:

- `caffeinate -i make ci`: **verde em 2 min 53 s**. 249 unit + 151 integração. `dbt build` PASS=354 WARN=5 ERROR=0 nos
  dois meses; backfill PASS=199 WARN=2; `ruff check`, `ruff format --check` e `sqlfluff` limpos.
- Determinismo: dois `dbt docs generate --no-partial-parse` em diretórios separados do scratch, gerador sobre cada um,
  `cmp a.md b.md && cmp a.md docs/DICIONARIO_DADOS.md` → idênticos. `grep -c "/Users\|/private\|/tmp/"
  docs/DICIONARIO_DADOS.md` → 0.
- PDF oficial baixado em 2026-10-13 (`cnpj-metadados.pdf`, 6 páginas, texto extraído com `pypdf`).

## Achados

Severidade: **bloqueante** (impede o merge), **importante** (corrigir antes de fechar), **menor**, **sugestão**.

### RDIC-01 — nulidade e domínio afirmados a partir de testes `warn` (importante, correção)

- **Onde:** `scripts/gerar_dicionario_dados.py:329-334` (`_anulavel` ignora a severidade) e `:303-319` (`_dominio`
  marca a severidade só em `data_nao_futura` e `cnpj_dv_valido`). Efeito em `docs/DICIONARIO_DADOS.md:1466`
  (`dim_municipio.codigo_rfb`: "não (`not_null`)") e `:1452` ("Outras chaves únicas: `codigo_rfb`", sem a marca
  `warn` que a chave primária recebe em `:226`).
- **Evidência:**
  - O `not_null` e o `unique` de `dim_municipio.codigo_rfb` são `severity: warn`
    (`transform/models/marts/core/_core__models.yml`, comentário "a BD atual traz município novo sem código RFB (ex.:
    Boa Esperança do Norte)").
  - No dado real:

    ```text
    $ duckdb: select count(*) filter (where codigo_rfb is null), count(*) from 'dados/gold/dim_municipio.parquet'
    [(1, 5572)]   -- sk_municipio 5101837, Boa Esperança do Norte, MT
    ```

  - Testes estruturais com `warn`, do manifesto:
    - `not_null` e `unique` em `dim_municipio.codigo_rfb`;
    - `unique` em `int_municipios__conformados.codigo_rfb` e em `basedosdados.municipio.id_municipio_rf`;
    - `accepted_range` em `stg_rfb__estabelecimentos.dat_inicio_atividade` e em `stg_bd__populacao.populacao`.

    Os dois `accepted_range` aparecem como domínio firme ("valor ≥ `date '1900-01-01'`"), mas a própria descrição diz
    que há datas de 1194.
- **Por que importa:** o "Como ler" (`:17-18`) diz que a nulidade vem do teste `not_null` e que o dicionário "não
  afirma" o que não sabe. Com teste `warn`, a afirmação "não" é falsa justamente no caso que o teste existe para
  apontar. Quem junta a fato com `dim_municipio` por `codigo_rfb` confia num NOT NULL que não vale.
- **Correção sugerida:**
  - Com `warn`, escrever "em geral não (`not_null` `warn`: pode haver exceções)".
  - Acrescentar `(warn)` em toda chave única, `relationships` e `accepted_*` com `warn`, como já se faz em
    `data_nao_futura`.
  - Opcionalmente, ler `store_failures` e o `run_results.json` para dizer "falhou em N linhas na última execução".

### RDIC-02 — grão da vizinhança declara unicidade que o dado não tem (importante, `meta.grao`)

- **Onde:** `transform/models/staging/basedosdados/_bd__sources.yml:467` ("par de municípios vizinhos por ano de malha
  (`ano`, `id_municipio_1`, `id_municipio_2`)") e `transform/models/staging/basedosdados/_bd__staging.yml:280`
  ("... como publicado (`ano`, `id_municipio_1`, `id_municipio_2`)"). Saem em `docs/DICIONARIO_DADOS.md:82`, `:118` e
  nas seções `:704` e `:1046` como "Uma linha por ...".
- **Evidência:**

  ```text
  raw/bd/vizinhanca_municipio  count(*), count(distinct (ano,id_1,id_2)), autopares
  fixture: (8, 7, 1)          real: (522822, 522803, 4)
  ```

  A descrição de `stg_bd__vizinhanca`, na mesma tabela, diz "possíveis duplicatas e autopares em anos antigos". Quem
  deduplica e simetriza é `bridge_municipio_vizinho`, cujo grão está certo e é testado.
- **Conferência dos demais grãos sem teste de unicidade** (dado real, `count(*)` × `count(distinct grão)`):

  | Tabela | Linhas | Distintas | Grão confere |
  |---|---|---|---|
  | `basedosdados.cnae_2` | 1.356 | 1.356 | sim |
  | `basedosdados.regiao_metropolitana_2017` | 1.385 | 1.385 | sim |
  | `basedosdados.municipio` (`id_municipio`) | 5.571 | 5.571 | sim |
  | `rfb.paises`, `rfb.qualificacoes`, `rfb.simples` | 255 / 68 / 50.396.768 | idem | sim |
  | `agg_empresas` (10 dimensões) | 5.812.927 | 5.812.927 | sim |
  | `mart_dinamica_mercado` | 16.138.510 | 16.138.510 | sim |
  | `mart_sobrevivencia_coorte` | 1.669.209 | 1.669.209 | sim |
  | `observabilidade.dq_historico_testes` | 638 | 638 | sim |
  | `basedosdados.vizinhanca_municipio`, `stg_bd__vizinhanca` | 522.822 | 522.803 | **não** |

- **Correção sugerida:** escrever o grão como "par de municípios vizinhos por ano de malha, como publicado: **pode
  repetir o par e trazer autopares** (deduplicado em `bridge_municipio_vizinho`)". No gerador, quando a tabela não tem
  chave única testada, rotular a linha como "Grão (declarado, não testado)" (ver RDIC-09).

### RDIC-03 — "Origem" vazia em quase todo o modelado; falta a linhagem de tabela (importante, utilidade)

- **Onde:** `scripts/gerar_dicionario_dados.py:337-362` (`_origem` só conhece `campo_leiaute`, `coluna_bigquery`,
  colunas `_*`, o texto "Linhagem:" da descrição e o `taxa_conversao_tipada`).
- **Evidência** (células "—" na coluna Origem, por seção do dicionário):

  | Seção | Colunas | Origem vazia |
  |---|---|---|
  | Staging | 112 | 101 |
  | Intermediate | 44 | 44 |
  | Gold — dimensões | 63 | 61 |
  | Gold — fatos | 26 | 26 |
  | Gold — pontes | 5 | 5 |
  | Gold — marts analíticos | 67 | 67 |
  | Gold — marts originais | 27 | 0 |

  Nenhuma seção diz de que tabelas a tabela é lida, nem por quem é usada. Para responder "de onde vem
  `fct_estabelecimentos.sk_municipio`?", o analista precisa abrir o SQL.
- **Por que importa:** o `README.md` e o `docs/POWER_BI.md` anunciam "tipo, grão, chaves, domínio de valores e
  **origem** de cada coluna do `gold/`". Para o gold modelado, a promessa não se cumpre.
- **Correção sugerida:**
  1. Barata e determinística: duas linhas novas na tabela de atributos de cada seção. Uma, **"Lê de"**, com os links
     de `depends_on.nodes` do manifesto (modelos, seeds e fontes do pacote). Outra, **"Usada por"**, com o inverso.
     Isso já responde "como ligo esta tabela às outras" em toda a cadeia raw → gold.
  2. Coluna a coluna: estender a convenção "Linhagem:" (já usada em `bh_empresas`/`agg_empresas`) às colunas do gold
     que não são cópia direta, ou um `meta.linhagem`.

### RDIC-04 — valores dos códigos ausentes; formato muda entre raw e gold sem aviso (importante, utilidade)

- **Onde:**
  - `docs/DICIONARIO_DADOS.md:1568`: `codigo_situacao_cadastral` com "Código RFB da situação.", domínio "—".
  - Seções das seeds, `:763-860`: só as 3 colunas, nenhuma linha do domínio.
  - Nas dimensões, 62 das 63 colunas têm domínio "—".
- **Evidência** (fixture e real, idênticos):

  ```text
  dim_situacao_cadastral: ('-1','NÃO INFORMADO') ('1','NULA') ('2','ATIVA') ('3','SUSPENSA') ('4','INAPTA') ('8','BAIXADA')
  rfb.estabelecimentos.situacao (raw): '02', '03', '04', '08'     -- accepted_values `01`,`02`,`03`,`04`,`08`
  ```

  Quem leu o raw no dicionário (`:291`, "`02` ativa") e filtra `codigo_situacao_cadastral = '02'` no gold recebe zero
  linhas. `codigo_porte` foi corrigido no lote (`0`/`1`/`3`/`5`); `codigo_situacao_cadastral` não. A pergunta "que
  valores tem?" fica sem resposta para todo código cujo domínio está numa seed ou numa dimensão pequena.
- **Correção sugerida:**
  - No gerador, imprimir as linhas das seeds (o CSV está em `transform/seeds/`, caminho no manifesto) como uma
    tabelinha na seção da seed.
  - Nas colunas `codigo_*` das dimensões semeadas, citar o domínio ("valores de `[dominio_situacao_cadastral](#...)`,
    sem zero à esquerda, mais `-1`").
  - Corrigir a descrição de `codigo_situacao_cadastral` como foi feito com `codigo_porte`.

### RDIC-05 — nota genérica "sem par na dimensão → chave `-1`" contradiz o SQL em 3 colunas (menor, correção)

- **Onde:** `scripts/gerar_dicionario_dados.py:385-386`. Afeta:
  - `docs/DICIONARIO_DADOS.md:1690-1691`: `bridge_municipio_vizinho.sk_municipio` e `sk_municipio_vizinho`;
  - `:1896`: `mart_fornecedores_proximos.sk_municipio`.
- **Evidência:** `bridge_municipio_vizinho.sql` faz `inner join` com `dim_municipio` ("restrita aos municípios de
  `dim_municipio`"), e o par sem município é **descartado**, não vira `-1`. O fornecedor exige centroide (haversine) e
  `distancia_km` not null, e o membro `-1` tem `latitude` NULL. No dado:

  ```text
  bridge_municipio_vizinho com -1: fixture 0 de 8; real 0 de 31.832
  mart_fornecedores_proximos com -1: fixture 0 de 3; real 0 de 1.726
  ```

  Nas outras 3 colunas que recebem a nota, ela confere: `fct_resumo_mensal.sk_porte` (239 linhas `-1` no real),
  `sk_situacao_cadastral` e `mart_sobrevivencia_coorte.sk_porte`.
- **Correção sugerida:** só emitir a nota quando o SQL usar `coalesce(..., -1)`. Uma alternativa barata é um
  `meta.membro_desconhecido: false` na coluna, ou a nota explícita na descrição (o gerador já prefere a descrição,
  `:380-382`). Nas três colunas acima, escrever "sem `-1`: pares/fornecedores sem município são descartados".

### RDIC-06 — chave primária de `basedosdados.municipio` contradiz o grão (menor, correção)

- **Onde:** `scripts/gerar_dicionario_dados.py:207-212`. Sem entidade semântica, o gerador escolhe a primeira coluna com
  `unique`. Resultado em `docs/DICIONARIO_DADOS.md`, seção `basedosdados.municipio`: grão "`id_municipio`", chave
  primária "`id_municipio_rf` (teste `warn`)".
- **Evidência:** no raw real, `id_municipio` tem 5.571 distintos em 5.571 linhas, e `id_municipio_rf` tem 5.570
  distintos e 1 NULL. O `id_municipio_rf` não é chave da tabela; é a chave de junção com a RFB, com `unique` `warn`.
- **Correção sugerida:** preferir, entre as colunas únicas testadas, as que aparecem no `meta.grao`. Sem nenhuma,
  escrever "não testada" e listar o `unique` `warn` em "Outras chaves únicas (warn)".

### RDIC-07 — a saída depende da ordem dos nós no manifesto (menor, robustez)

- **Onde:** `scripts/gerar_dicionario_dados.py:140-152`. `t.testes` segue a ordem de `manifest["nodes"]`, e
  `_dominio`, `_observacoes` e `_chave_primaria` iteram nessa ordem.
- **Evidência:** reordenei aleatoriamente `nodes`, `sources`, `semantic_models` e `metrics` do mesmo manifesto (5
  sementes), e 4 das 5 mudaram a saída:

  ```text
  -| `cnpj_completo` | ... | tamanho exato: 14; CNPJ com DV válido (`warn`) | ...
  +| `cnpj_completo` | ... | CNPJ com DV válido (`warn`); tamanho exato: 14 | ...
  ```

  Também mudaram `stg_rfb__estabelecimentos.dat_inicio_atividade` e outras colunas com mais de um teste. Com parse
  completo a ordem é estável (o `make dicionario` e o teste usam `--no-partial-parse`), por isso é menor. Mas quem rodar
  `uv run python scripts/gerar_dicionario_dados.py` depois de um `dbt` com *partial parse*, conforme o docstring do
  script (`:4-6`), pode ver o CI acusar um diff que não muda conteúdo.
- **Correção sugerida:** `t.testes.sort(key=lambda n: n["unique_id"])` ao fim de `_tabelas`. Um teste unitário com o
  manifesto embaralhado protege a regra.

### RDIC-08 — os testes provam sincronia, não correção; o ADR promete mais do que o teste cobre (menor, teste)

- **Onde:** `tests/integration/test_dicionario_dados.py`; `docs/adr/0019-dicionario-de-dados.md:18-19` ("confere ...
  que todo modelo, seed, fonte e coluna real tem entrada").
- **Problema:**
  1. Os dois testes principais comparam o arquivo com o gerador atual (golden file). Qualquer erro do gerador ou dos
     `meta`, regenerado, passa: M1–M6 e M8 sobreviveram.
  2. `test_toda_tabela_e_coluna_real_esta_no_dicionario` confere colunas só de `catalog["nodes"]` (modelos e seeds), não
     das fontes. A M7 apaga as 36 colunas técnicas das fontes RFB e mais as da Base dos Dados e da observabilidade, e
     passa. O ADR diz "fonte e coluna real".
  3. Nada exige `campo_leiaute` nas colunas de dado RFB (M2) nem confere que `coluna_bigquery` existe no Parquet raw
     (M3 troca a tabela). Tampouco confere que as colunas citadas no `meta.grao` existem.
  4. Não há teste unitário do gerador (`git grep gerar_dicionario -- tests` só acha o de integração).
- **Correção sugerida:**
  - Estender o laço de colunas a `catalog["sources"]`, ou às colunas do Parquet raw, como o teste de cobertura já
    faz.
  - Teste de `meta`:
    - toda coluna de dado das fontes RFB, salvo `motivos`, tem `campo_leiaute`, e a sequência segue
      `esquemas.py` e uma lista do leiaute versionada no teste;
    - toda `coluna_bigquery` está no Parquet raw;
    - toda coluna citada em crase no `meta.grao` existe.
  - Um teste unitário com um manifesto mínimo (um `not_null` `warn`, um `relationships`, uma coluna sem teste) que
    fixe `_anulavel`, `_dominio` e `_chave_primaria`. Esse teste pegaria a M5, a M8 e o RDIC-01.

### RDIC-09 — 12 tabelas com grão declarado e sem teste de unicidade (sugestão)

- **Onde:** seções com "Chave primária (testada) | não testada" e `meta.grao` preenchido:
  - fontes: `rfb.paises`, `rfb.qualificacoes`, `rfb.simples`, `basedosdados.cnae_2`,
    `basedosdados.regiao_metropolitana_2017`, `basedosdados.vizinhanca_municipio`, `observabilidade.dq_historico_testes`;
  - seeds e staging: `excecoes_conhecidas_municipio`, `stg_bd__vizinhanca`;
  - gold: `agg_empresas`, `mart_dinamica_mercado`, `mart_sobrevivencia_coorte`.
- O dicionário é honesto ("não testada"). No dado real, 9 desses grãos valem, os 2 da vizinhança não (RDIC-02), e `excecoes_conhecidas_municipio` não conferi. O lote não
  devia mexer em testes de dados, por isso fica como sugestão para um lote seguinte: `unique_combination_of_columns`
  nos três marts e em `rfb.simples`. No gerador, rotular "Grão (declarado)" quando não houver teste que o prove.

### RDIC-10 — jargão interno de revisão e referências que só fazem sentido no YAML (sugestão, legibilidade)

- **Onde:** 31 linhas do dicionário citam IDs de processo, entre eles `R2-03`, `R3-20`, "emenda R3-03", "spec
  Original AC 12", `ANA-01` e `ENR-03`. Exemplos:
  - `_data_referencia`, nas 9 fontes RFB: "NULL zeraria `idade_atual` em silêncio via `data_referencia()` (R2-03):
    not_null error";
  - `stg_rfb__estabelecimentos.dat_inicio_atividade`: "o teste warn **abaixo** as registra", que se refere à posição
    no YAML;
  - `sk_cnae` dos marts: "Chave de `dim_cnae` (R3-20)".

  A linhagem de `bh_empresas` usa os apelidos do notebook (`cnae_bd`, `municipio_bd`, `natureza_juridica`,
  `empresas`), que não são nomes de tabela do dicionário e não viram link.
- **Correção sugerida:** reescrever essas descrições para o leitor do dado. Por exemplo, `_data_referencia` = "Data do
  extrato (token `Dyymmdd` do nome interno do arquivo); base do cálculo de idade". Na linhagem do original, citar a
  tabela do projeto entre parênteses (`cnae_bd` = `basedosdados.cnae_2`).

### RDIC-11 — navegação (sugestão)

- O arquivo tem 1.990 linhas e nenhuma visão de conjunto do modelo estrela. Um diagrama `mermaid` `erDiagram` das
  dimensões, fatos e pontes, gerado das FKs que o gerador já calcula, responderia "como ligo esta tabela às outras" de
  relance.
- `fct_resumo_mensal.sk_mes_referencia` → `dim_data.sk_data` não aparece em "Chaves estrangeiras", embora a descrição
  diga que é a mesma chave. Conferi no real: 0 órfãos em 5.763.929 linhas.
- As FKs da `fct_resumo_mensal` vêm das entidades semânticas, não de `relationships`, e por isso a coluna "Domínio" dela
  fica "—", ao contrário da `fct_estabelecimentos`. Distinguir "FK testada" de "FK da camada semântica".
- `rfb.motivos` tem Origem "—" sem dizer por quê: o leiaute não traz a tabela de motivos, o que o ADR registra.
  Escrever "não consta do leiaute oficial".
- Nas tabelas de domínio RFB, o campo "CÓDIGO"/"DESCRIÇÃO" sem a seção do PDF é ambíguo. Sugestão: "PAÍSES › CÓDIGO",
  "CNAEs › DESCRIÇÃO". O leiaute chama `qualificacoes` de "QUALIFICAÇÕES DE SÓCIOS", e o grão do projeto diz
  "qualificação de responsável".

## Conferências de conteúdo

Amostra do gold, 12 tabelas, conferidas contra o SQL, os testes e o dado (fixture e real):

- `dim_data`, `dim_porte`, `dim_situacao_cadastral`, `dim_municipio`;
- `fct_estabelecimentos`, `fct_resumo_mensal`;
- `bridge_municipio_vizinho`, `agg_empresas`;
- `mart_concorrencia_municipio`, `mart_dinamica_mercado`, `mart_sobrevivencia_coorte`, `mart_fornecedores_proximos`.

Fontes, 4: `rfb.empresas`, `rfb.estabelecimentos`, `basedosdados.municipio`, `basedosdados.vizinhanca_municipio`.

| Item | Resultado |
|---|---|
| Tipos | conferem com o contrato e o Parquet (raw: dado `varchar`, `_data_referencia` `DATE`, `_ingerido_em` `TIMESTAMP`; `ano_coorte` `BIGINT`) |
| Nulidade "não testado" × "não" | correta, salvo os `warn` (RDIC-01) |
| Domínios `accepted_values`/`relationships` | conferem (`situacao` raw `02/03/04/08` na fixture; `porte` raw `00/01/03/05` + NULL); `warn` sem marca (RDIC-01) |
| Chave primária e grão | conferem, salvo a vizinhança (RDIC-02) e `basedosdados.municipio` (RDIC-06) |
| Localização Parquet | confere (`gold/<modelo>.parquet`; `gold/fct_resumo_mensal/mes_referencia=AAAA-MM/`; `raw/rfb/<entidade>/mes_referencia=*/*.parquet`) |
| Membros `-1`/`-2` | conferem em `dim_data` (`-1`/`-2` com 1899-12-31/30, `ano` NULL), dimensões e fatos (`coalesce(..., -1)` e `-2` antes de 1900 em `fct_estabelecimentos.sql`); errados em 3 colunas (RDIC-05) |
| Origem | correta onde existe (leiaute, BigQuery, `raw:` do `taxa_conversao_tipada`, "Linhagem:" do original); vazia no resto (RDIC-03) |
| Descrições × SQL | conferem `idade_anos` (round 1 casa, só ativos), `eh_matriz`/`eh_ativa` (`coalesce` false), `ativos`/`inativos` (`situacao = 2`), sobrevivência ("ativo ou encerrado após `dat_inicio + N`") e `bridge` (simétrica, sem autopares); `codigo_situacao_cadastral` incompleta (RDIC-04) |
| `meta.grao` | dos 12 não testados, 9 conferem no real, os 2 da vizinhança não (RDIC-02) e 1 não conferi; os testados conferem por construção |

## Campos do leiaute conferidos

Conferi o PDF oficial (`https://www.gov.br/receitafederal/dados/cnpj-metadados.pdf`, baixado em 2026-10-13). O raw
nomeia as colunas por posição (`src/rfb_pipeline/esquemas.py:19-72`), então o mapeamento só está certo se a ordem da
tupla for a ordem do PDF. Conferi as **54** colunas; todas batem:

| Fonte | Coluna → campo do leiaute (posição) | PDF |
|---|---|---|
| `rfb.empresas` | `cnpj_raiz` → CNPJ BÁSICO; `razao_social` → RAZÃO SOCIAL / NOME EMPRESARIAL; `natureza_jur` → NATUREZA JURÍDICA; `qualificacao_resp` → QUALIFICAÇÃO DO RESPONSÁVEL; `capital_soc` → CAPITAL SOCIAL DA EMPRESA; `porte` → PORTE DA EMPRESA; `ente_fed_resp` → ENTE FEDERATIVO RESPONSÁVEL | p. 1, EMPRESAS (7 de 7) |
| `rfb.estabelecimentos` | `cnpj_raiz` → CNPJ BÁSICO; `cnpj_ordem` → CNPJ ORDEM; `cnpj_dv` → CNPJ DV; `ind_matriz_filial` → IDENTIFICADOR MATRIZ/FILIAL; `nome_fantasia` → NOME FANTASIA; `situacao` → SITUAÇÃO CADASTRAL; `dat_situacao` → DATA SITUAÇÃO CADASTRAL; `mot_situacao` → MOTIVO SITUAÇÃO CADASTRAL; `cidade_exterior` → NOME DA CIDADE NO EXTERIOR; `pais` → PAIS; `dat_inicio_atividade` → DATA DE INÍCIO ATIVIDADE; `cnae_principal` → CNAE FISCAL PRINCIPAL; `cnaes_secundarios` → CNAE FISCAL SECUNDÁRIA | pp. 1-2 |
| `rfb.estabelecimentos` (cont.) | `tip_logradouro` → TIPO DE LOGRADOURO; `logradouro` → LOGRADOURO; `num_logradouro` → NÚMERO; `compl_logradouro` → COMPLEMENTO; `bairro` → BAIRRO; `cep` → CEP; `uf` → UF; `municipio` → MUNICÍPIO; `ddd1` → DDD 1; `tel1` → TELEFONE 1; `ddd2` → DDD 2; `tel2` → TELEFONE 2; `ddd_fax` → DDD DO FAX; `fax` → FAX; `email` → CORREIO ELETRÔNICO; `sit_especial` → SITUAÇÃO ESPECIAL; `dat_sit_especial` → DATA DA SITUAÇÃO ESPECIAL | pp. 2-3 (30 de 30) |
| `rfb.simples` | `cnpj_raiz` → CNPJ BÁSICO; `opcao_simples` → OPÇÃO PELO SIMPLES; `dat_opcao_simples` → DATA DE OPÇÃO PELO SIMPLES; `dat_exclusao_simples` → DATA DE EXCLUSÃO DO SIMPLES; `opcao_mei` → OPÇÃO PELO MEI; `dat_opcao_mei` → DATA DE OPÇÃO PELO MEI; `dat_exclusao_mei` → DATA DE EXCLUSÃO DO MEI | p. 3, DADOS DO SIMPLES (7 de 7) |
| `rfb.cnaes`, `municipios`, `naturezas`, `paises`, `qualificacoes` | `codigo` → CÓDIGO; `descricao` → DESCRIÇÃO | pp. 4-5 (CNAEs, MUNICÍPIOS, NATUREZAS JURÍDICAS, PAÍSES, QUALIFICAÇÕES DE SÓCIOS) (10 de 10) |
| `rfb.motivos` | sem `campo_leiaute` | correto: o PDF não tem a tabela de motivos (RDIC-11) |

Observações: o PDF escreve "PAIS" sem acento no campo e "PAÍS" na descrição, e o YAML segue o campo. Os códigos de
situação no PDF são "01, 2, 3, 4, 08", mas o dado traz `02`, `03`, `04`, o que o `accepted_values` reflete.

## Base dos Dados conferida

`coluna_bigquery` e `tabela_bigquery` comparados com o **cabeçalho real** do Parquet raw de `dados/raw/bd/`. Esse
Parquet é convertido do CSV exportado pela API `downloadTable` da Base dos Dados (`src/rfb_pipeline/basedosdados.py`),
que exporta a tabela do BigQuery com os nomes de coluna dela. O download por `dataset`/`tabela` de
`esquemas.py:148-172` funcionou para as 7 tabelas, e os 7 `tabela_bigquery` são iguais a esse par.

| Tabela (`tabela_bigquery`) | Colunas de dado no raw | `coluna_bigquery` declaradas | Faltam / inexistentes |
|---|---|---|---|
| `br_bd_diretorios_brasil.municipio` | 27 | 27 | 0 / 0 (ordem diferente, irrelevante) |
| `br_bd_diretorios_brasil.cnae_2` | 14 | 14 | 0 / 0 |
| `br_ibge_populacao.municipio` | 4 | 4 | 0 / 0 |
| `br_ibge_pib.municipio` | 9 | 9 | 0 / 0 |
| `br_ibge_censo_2022.municipio` | 13 | 13 | 0 / 0 |
| `br_geobr_mapas.regiao_metropolitana_2017` | 8 | 8 | 0 / 0 |
| `br_bd_vizinhanca.municipio` | 3 | 3 | 0 / 0 |

Não conferi as páginas de documentação de `basedosdados.org`. O cabeçalho da exportação é evidência mais forte que a
página para o nome da coluna, mas não confirma tipo nem descrição do lado da BD. Em todas as 88 colunas, `coluna_bigquery`
é igual ao nome da coluna. O `meta` serve hoje como afirmação "existe no BigQuery com este nome". Vale dizer isso no
ADR-0019, ou omitir o `meta` quando for igual e escrever só a tabela.

## Mutações

Cada mutação foi aplicada com substituição exata. Depois: `dbt parse --no-partial-parse --target ci` quando o arquivo
era YAML; regeneração do dicionário com `dbt docs generate` (scratch) e o gerador quando indicado; `pytest -q
tests/integration/test_dicionario_dados.py tests/integration/test_cobertura_descricoes.py` (7 testes) com
`RAIZ_DADOS=$PWD/.tmp/ci/dados`; reversão com `git checkout`. Nenhuma repete as do autor (`description` apagada no gold,
linha editada no dicionário). Script: `mutacoes.py` no scratch do revisor.

"Regenerado" simula o erro consistente do autor: muda a fonte e roda `make dicionario`. Sem regenerar, toda mudança de
YAML morre por desatualização (C1).

| # | Mutação | Regenerado | Resultado | Teste que deveria pegar |
|---|---|---|---|---|
| C1 | controle: `campo_leiaute` de `natureza_jur` trocado no YAML | não | morta (`test_verificar_passa...`, `test_dicionario_versionado_bate...`) | — |
| M1 | `natureza_jur` ↔ `qualificacao_resp` com os campos do leiaute trocados | sim | **sobreviveu** | ordem do leiaute × `esquemas.py` (RDIC-08) |
| M2 | `campo_leiaute` de `cnae_principal` removido | sim | **sobreviveu** | cobertura de `campo_leiaute` (RDIC-08) |
| M3 | `tabela_bigquery` do PIB trocada para `br_ibge_pib.uf` | sim | **sobreviveu** | `tabela_bigquery` × `TABELAS_BD` |
| M4 | `meta.grao` de `dim_porte` trocado para "município (`sk_municipio`)" | sim | **sobreviveu** | colunas do grão existem na tabela |
| M5 | gerador: `_anulavel` sempre "não (`not_null`)" | sim | **sobreviveu** | unitário do gerador (RDIC-01/08) |
| M6 | gerador: partição `mes=AAAA-MM` em vez de `mes_referencia=` | sim | **sobreviveu** | localização × disco |
| M7 | gerador: colunas técnicas (`_*`) das fontes omitidas | sim | **sobreviveu** | colunas das fontes no `test_toda_tabela...` (RDIC-08) |
| M8 | gerador: FKs de `relationships` ignoradas (só as semânticas) | sim | **sobreviveu** | unitário do gerador |
| M9 | controle: seção de `rfb.paises` omitida pelo gerador | sim | morta (`test_toda_tabela_e_coluna_real_esta_no_dicionario`) | — |

Sobreviventes: M1–M8 (8 de 8 não-controle). As duas mortes mostram que a fixture reflete o YAML (C1) e que a presença
de seções é garantida (M9). Também é garantida a presença de colunas de modelos e seeds, que a M7 não toca. Os testes
garantem que o arquivo está em dia e completo nas seções; não garantem que o conteúdo está certo.

## Higiene

- **Escopo:** sem mudança em SQL, CSV de seed, fixture ou teste de dados (`git diff main...HEAD --stat -- '*.sql'
  '*.csv' transform/tests` vazio). Nos YAMLs, só `description`, `data_type` de fontes, `meta` (`campo_leiaute`,
  `coluna_bigquery`, `tabela_bigquery`, `grao`) e a movimentação de `meta.incremento` para dentro do mesmo `config.meta`.
  O único texto corrigido fora disso é uma referência quebrada (`int_vizinhanca__municipios` →
  `bridge_municipio_vizinho`), que é bem-vinda. Os testes de integração mudados (`conftest.py`, cobertura) são do
  próprio lote.
- **`make ci`:** verde (acima).
- **Idioma (ADR-0014):** script, alvo `dicionario`, chaves `meta` e textos em português; `bigquery` é nome de
  ferramenta. Confere.
- **Escopo `adicao` (ADR-0006):** registrado em `docs/ESCOPO.md` como "adição (pedido do usuário 2026-10-13)". Confere.
- **Dado real ou segredo:** o dicionário não traz dado real além de exemplos já presentes nos YAMLs (contagens de
  fev/2025 e 2026-09 e um nome de município). Nenhum CPF, contato ou segredo. `grep` de caminhos absolutos: 0.

## Triagem do líder

*Triagem da RDIC (líder, 2026-10-13).*

Veredito da RDIC ([RDIC.md](RDIC.md)): **aprovável com ressalvas**. São 0 bloqueantes, 4 importantes, 4 menores e 3
sugestões. As 8 mutações (M1–M8) sobreviveram porque os testes provam a sincronia do dicionário, não o conteúdo. O
mapeamento do leiaute (54/54) e as colunas da Base dos Dados (88/88) conferem.

As correções ficam com o lote **FDIC**, um agente novo (Sonnet, esforço médio, o mesmo nível do lote DIC), no branch
`feat/dicionario-dados`.

| Achado | Decisão | Lote | Resolvido em |
|---|---|---|---|
| **RDIC-01** nulidade e domínio afirmados a partir de testes `warn` | Com `warn`: "em geral não (`not_null` `warn`: pode haver exceções)" e a marca `(warn)` em chave única, `relationships` e `accepted_*`. O "Como ler" explica. Teste unitário fixa o comportamento | FDIC | `600792f` |
| **RDIC-02** grão da vizinhança promete unicidade | Corrigir o `meta.grao` das duas tabelas ("como publicado: pode repetir o par e trazer autopares; deduplicado em `bridge_municipio_vizinho`") | FDIC | `25df8c3` |
| **RDIC-03** "Origem" vazia; falta linhagem de tabela | Linhas **"Lê de"** e **"Usada por"** em toda seção, tiradas de `depends_on` do manifesto. "Linhagem:" coluna a coluna nas colunas do gold que não são cópia direta (pelo menos dimensões e fatos) | FDIC | `600792f`, `25df8c3` |
| **RDIC-04** valores dos códigos ausentes; formato raw × gold | Imprimir as linhas das seeds na seção de cada uma. Domínio nas colunas `codigo_*`/`rotulo_*` das dimensões semeadas. Corrigir a descrição de `codigo_situacao_cadastral` ("sem zero à esquerda") | FDIC | `600792f`, `25df8c3` |
| **RDIC-05** nota "sem par → `-1`" errada em 3 colunas | A nota só aparece quando a coluna de fato recebe `-1`: `meta.membro_desconhecido: false` ou descrição explícita nas 3 colunas | FDIC | `25df8c3` |
| **RDIC-06** PK de `basedosdados.municipio` contradiz o grão | Preferir as colunas únicas testadas que estão no `meta.grao`; sem elas, "não testada", e o `unique` `warn` vai em "Outras chaves únicas (warn)" | FDIC | `600792f` |
| **RDIC-07** saída depende da ordem do manifesto | Ordenar os testes por `unique_id`; teste unitário com o manifesto embaralhado | FDIC | `600792f` |
| **RDIC-08** testes provam sincronia, não correção | Colunas das fontes no teste de completude. Teste de `meta`: toda coluna de dado RFB, salvo `motivos`, tem `campo_leiaute`, na ordem de `esquemas.py`; toda `coluna_bigquery` existe no raw; toda coluna citada no `meta.grao` existe. Teste unitário do gerador com um manifesto mínimo. Ajustar o ADR-0019 ao que é provado. As mutações M1–M8 da RDIC devem morrer, ou ter a sobrevivência justificada | FDIC | `f497b06` |
| **RDIC-09** 12 grãos declarados sem teste de unicidade | Gerador rotula "Grão (declarado, não testado)". Os testes de unicidade (`unique_combination_of_columns`) vão para o **PR B** (regras e invariantes) | FDIC (rótulo) · PR B (testes) | `600792f` (rótulo); testes de unicidade no PR B |
| **RDIC-10** jargão de revisão e referências ao YAML | Reescrever as 31 descrições para o leitor do dado, sem IDs de processo nem "abaixo". Na linhagem do original, citar a tabela do projeto | FDIC | `25df8c3` |
| **RDIC-11** navegação | `erDiagram` mermaid gerado das FKs (dimensões, fatos, pontes). FK `sk_mes_referencia` → `dim_data`. Distinguir "FK testada" de "FK da camada semântica". Explicar o "—" de `rfb.motivos` | FDIC | `600792f`, `25df8c3`, `f447254` |

**FDIC (2026-10-13).**
- Verificação do líder: `make ci` verde em `f497b06` (259 unit, 154 integração, PASS=354 WARN=5 ×2) e `make dicionario` sem diff.
- Mutações: as 8 da RDIC e 2 do FDIC foram reprovadas pelos testes. A mutação do líder (FK declarada removida) sobreviveu na 1ª entrega e passou a ser reprovada no `f447254`.
