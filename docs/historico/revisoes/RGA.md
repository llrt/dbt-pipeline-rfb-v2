# RGA — Revisão independente do guia de construção do agente (v1.5.1)

Revisor: agente RGA (Traycer, Claude Opus), 2026-10-15. Não sou autor de nenhum dos commits revisados.

- **Alvo:** branch `docs/guia-construcao-agente`, `git diff a6d2983..9bf9b8f`, só os commits do lote GA:
  `743eb7f` (campo `versao_projeto`), `35fc731` (documento, teste e links), `4c1e992` (versão 1.5.1), `afa027a` e
  `f09c1ee` (estilo do teste). O `19f2db3` (RETRO e custos) veio do `main` e ficou fora.
- **O que não toquei:** não alterei código, YAML, docs nem testes. Os únicos arquivos do commit são esta revisão e a
  linha dela em `docs/historico/README.md`.
- **Protótipo:** escrito no scratch do revisor, fora do repositório. Lê só o `construcao-agente.md` e o que ele indica
  (catálogo e guia §7). Roda sobre `.tmp/ci/dados/warehouse.duckdb`, com `read_only=True`.
- **Mutações:** aplicadas com `sed` e revertidas com `git checkout -- <arquivo>`. `git status --short` ficou vazio
  no fim.
- **Gates:**
  - `caffeinate -i make ci`: verde em 6 min 15 s. `tests/unit` passou com 582 testes e `tests/integration` com 435.
  - `uvx pre-commit run --all-files`: verde.
  - `make golden`: idempotente, `git status` vazio depois.

## Veredito

**APROVÁVEL COMO PATCH, COM RESSALVAS.**

- A mudança é só aditiva: um documento novo, um campo novo no topo do catálogo, links e um teste.
- O documento cumpre o pedido. Diz o que indexar, o que vai no prompt e quais ferramentas dar ao modelo. Também
  cobre como casar catálogo e banco e como avaliar, e aponta para o guia em vez de copiá-lo.
- O protótipo montou o índice e executou as 5 golden queries escolhidas sem erro. A checagem de privacidade passou
  nelas e pegou o controle positivo.

Mas quem seguir o documento ao pé da letra esbarra em quatro coisas, todas no próprio documento:

- **Segurança (RGA-01, alta).** A combinação somente leitura + filtro de `SELECT` ainda deixa o modelo ler qualquer
  arquivo da máquina e acessar a rede.
- **Avaliação (RGA-02, média).** O acerto exato do §7 reprova 18 das 20 golden queries semânticas, mesmo executando o
  próprio SQL do catálogo.
- **Recuperação (RGA-03, média).** A reordenação por camada rebaixa a golden query certa nas perguntas de auditoria
  e de paridade.
- **Falha fechada do §6 (RGA-04, média).** Não liga as relações às golden queries sem normalizar nomes, e a semântica
  não tem `tabelas`.

Nenhum dos quatro bloqueia o merge: o patch não muda o comportamento do pipeline. Mas RGA-01 e RGA-02 deveriam ser
corrigidos **antes** de o usuário construir o agente do outro projeto. Há ainda um achado médio (RGA-05, no guia §7)
e cinco baixos.

O que está bem:

- **Divisão de papéis.** Fica claro que o guia é para o agente e este documento é para quem o constrói. O documento
  aponta para as seções do guia (§2, §3, §4, §5, §7, §8, §9) e não copia o conteúdo. As únicas repetições são as
  regras duras do prompt (de propósito) e um resumo de 3 linhas do DuckDB × MotherDuck, com link.
- **Fatos conferidos.**
  - Todos os campos citados existem no catálogo, nos lugares indicados.
  - Na semântica faltam `tabelas` e `colunas_chave`, como o documento avisa.
  - As contagens batem: 93 golden queries, 23 conceitos, 48 relações, 29 métricas e 50 dimensões.
  - As afirmações sobre o MotherDuck batem com o guia §3: só o gold, Read Scaling token, `read_only` sem efeito em
    `md:` e o SQL semântico só lê o gold. As 10 relações que esse SQL usa são de core ou analytics.
  - O marcador `${RAIZ_DADOS}` só aparece no raw.
  - A ADR-0016 não fala de Read Scaling token; quem fala é o guia §3, e o documento aponta para ele.
- **Conferência por esquema.** Funciona no warehouse das fixtures: 48 relações, nenhuma coluna faltando ou a mais,
  nenhum tipo diferente. A string de `tipo` é igual à de `information_schema.columns.data_type`.
- **Patch.** O campo `versao_projeto` é aditivo e `formato` continua `1`. Nenhum consumidor do repositório valida o
  conjunto de chaves do topo. O teste novo e o `make golden --verificar` pegam versão desatualizada.

## Teste de uso real: o protótipo

Fiz o papel de quem constrói o agente e li só o `construcao-agente.md`. O protótipo (`prototipo.py`) tem uns 180
linhas, sem LLM e sem embeddings, com busca lexical BM25. O guia §7 entrou por extração do bloco `python`, sem
nenhuma edição.

### Dá para construir sem adivinhar?

| Pergunta | Resposta |
|---|---|
| Montar o índice? | **Sim, com duas adivinhações.** (1) `conceitos[].definicoes` é uma lista de objetos `{id, titulo, texto}`, não um texto: usei o `texto` de todos. (2) `relacoes[].nome` vem com `main.`, mas `tabelas` e `information_schema` não (RGA-04). |
| Escrever o prompt? | **Sim.** O modelo é usável como está. Ressalvas menores em RGA-10. |
| Implementar as ferramentas? | **Sim, mas** o `executar_sql_leitura` descrito não é seguro (RGA-01), e o `buscar_golden` com a reordenação descrita piora a recuperação (RGA-03). |
| Montar a avaliação? | **Não sem ler `scripts/`.** A comparação exata reprova o próprio SQL do catálogo (RGA-02). |

### (a) Índice

São 93 documentos, um por golden query.

- **Texto embutido:** as perguntas, uma por linha, mais a `intencao` e `Conceito: <nome>. <texto das definições>`.
- **Metadados:** `id`, `conceito`, `camada`, `privacidade` e `tabelas`.
- **Payload:** `sql`, `armadilhas`, `variacoes`, `colunas_chave` e `resposta_esperada_fixtures`.

Tudo o que o §3 pede existe no catálogo. A única exceção são os campos ausentes na semântica, e o documento os
anuncia.

### (b) Recuperação de 5 perguntas

Foram duas medições:

- **"Exata":** a pergunta do catálogo, que também está no índice.
- **"Sem a pergunta":** a mesma pergunta, mas fora do texto embutido da própria golden query, como se fosse uma
  redação nova.

A seta mostra a posição antes e depois da reordenação por camada que o §3 manda.

| Golden query | Pergunta | Exata | Sem a pergunta |
|---|---|---|---|
| `gq_semantica__capital_social__01` | Qual o capital social total e médio das empresas por mês? | 1 → 1 | 2 → 1 |
| `gq_core__empresa_estabelecimento__01` | Quantas empresas e quantos estabelecimentos existem? | 2 → 2 | fora do top 5 |
| `gq_analytics__concorrencia_densidade__01` | Fundão tem muita concorrência de loja de tintas? | 1 → **2** | 3 → 2 |
| `gq_raw__capital_social__01` | Em que formato a RFB publica o capital social? | 1 → **4** | 1 → **4** |
| `gq_original__concorrencia_densidade__01` | Quantos concorrentes de loja de tintas há em Fundão, pelo modelo original do MVP? | 1 → **2** | fora do top 5 |

- Com a pergunta exata, a busca lexical acha a golden query certa em 1º lugar em 4 de 5 casos. No caso do core, a
  irmã semântica do mesmo conceito ficou em 1º.
- Sem a pergunta, a busca lexical falha em 2 de 5. Isso é limite do BM25, não do documento: com embeddings deve ir
  melhor.
- **A reordenação por camada piora os dois casos que o guia §2 manda tratar à parte.** A pergunta de auditoria
  ("o que a RFB publica") cai de 1º para 4º. A de paridade com o MVP cai de 1º para 2º. Ver RGA-03.
- O id `gq_original__paridade_mvp__01`, que eu tinha escolhido, não existe. O protótipo trocou-o pelo primeiro
  `original` do catálogo.

### (c) Execução somente leitura e comparação

Todas as 5 rodaram com `duckdb.connect(..., read_only=True)` e o marcador trocado por `.tmp/ci/dados`.

| Golden query | Linhas | Igual, como o §7 manda | Igual, normalizado como o gerador |
|---|---|---|---|
| semantica `capital_social__01` | 2 | não | **não**: `2026-08-01T00:00:00` × `2026-08-01` |
| core `empresa_estabelecimento__01` | 1 | sim | sim |
| analytics `concorrencia_densidade__01` | 1 | sim | sim |
| raw `capital_social__01` | 3 | sim | sim |
| original `concorrencia_densidade__01` | 2 | sim | sim |

Depois estendi a comparação às 93 golden queries, cada uma executando o próprio `sql`:

| Comparação | Resultado |
|---|---|
| Crua (tuplas do DuckDB × `linhas`) | **24 falham**: 18 semânticas, 2 analytics, 2 core, 1 raw e 1 staging |
| Decimal e float com 6 casas, data em ISO (`normalizar_valor` do gerador) | **18 falham**, todas semânticas |
| Como o CI (`resultado_sql_semantico`, que também troca meia-noite por data e ordena as linhas) | 0 falham |

### (d) `checar_saida`

- Nas 5 saídas: nenhum problema.
- No controle positivo (`razao_social`, `cnpj_completo`, um CPF válido em texto): os 4 problemas esperados.
- Fora do protótipo: deixa passar CNPJ como `DECIMAL`, `DOUBLE` e lista (RGA-05).

## Achados

### RGA-01 — somente leitura não impede ler arquivos da máquina nem acessar a rede (alta, documento §5 e §9)

**Evidência.**

O documento promete "somente leitura em duas camadas": `read_only=True` e o filtro de um único `SELECT`/`WITH`.
Testei numa conexão `read_only=True` do DuckDB 1.5.6.

| Comando | Passa pelo filtro? | `read_only=True` impede? |
|---|---|---|
| `select length(content) from read_text('/etc/hosts')` | sim | **não**: 213 bytes lidos |
| `select count(*) from read_csv('/etc/passwd', header=false, sep=':')` | sim | **não** |
| `select count(*) from glob('/Users/*')` | sim | **não**: lista o disco |
| `select * from read_csv('https://…')` | sim | **não**: o `httpfs` é carregado sozinho |
| `copy (select 42) to '<arquivo>'` | não | **não**: o arquivo foi gravado |
| `install httpfs` | não | **não**: grava em `~/.duckdb/extensions` |
| `attach ':memory:'` / `attach '<novo>.duckdb'` | não | sim |

**Por que importa.**

- O agente recebe perguntas livres. Uma pergunta maliciosa, ou um texto injetado, pode levá-lo a escrever um `SELECT`
  que lê um `.env` com o `MOTHERDUCK_TOKEN`, `~/.aws/credentials` ou `~/.ssh/`.
- O `checar_saida` não reconhece token nem chave.
- Pela rede, o mesmo `SELECT` pode mandar dado para fora, por exemplo em `read_csv('https://…?q=' || …)`.
- O `COPY ... TO` e o `INSTALL` só são barrados pelo filtro de texto, que vira a única barreira.

**Correção sugerida.**

Em §5 e §9, configurar a conexão logo depois de abri-la:

```sql
SET allowed_directories = ['<RAIZ_DADOS>/'];
SET enable_external_access = false;
SET autoinstall_known_extensions = false;
SET lock_configuration = true;
```

Testei no warehouse das fixtures. As **93 de 93** golden queries rodam, inclusive as de raw, que leem Parquet sob a
raiz. `read_text('/etc/hosts')` e `read_csv('https://…')` dão `Permission Error`, e `SET enable_external_access=true`
é recusado.

- **`allowed_directories`:** precisa vir por `SET` depois do `connect`. Pelo `config=` do `connect` dá
  `Cannot change/set allowed_directories before the database is started`.
- **MotherDuck:** a mesma configuração vale para o processo local. Não testei se o `md:` aceita
  `enable_external_access=false` com a execução dual: confira antes de prometer.

### RGA-02 — o acerto exato do §7 reprova o próprio SQL das golden queries semânticas (média, documento §7)

**Evidência.**

- O §7 manda comparar a saída com `resposta_esperada_fixtures` (`colunas` e `linhas`) e medir o "acerto exato
  (mesmas `linhas`)".
- O gerador, porém, guarda as respostas normalizadas:
  - decimal e float com 6 casas, data em ISO (`normalizar_valor`);
  - na semântica, meia-noite vira data e as linhas são ordenadas (`normalizar_texto_mf`, `resultado_sql_semantico`
    em `scripts/gerar_catalogo_golden.py`).
- O documento não diz nada disso. Seguindo-o, o `sql` da golden query, que é a resposta certa por definição, é
  reprovado em 24 de 93 casos (crua) ou em 18 das 20 semânticas (com a normalização óbvia). Ver o protótipo (c).

**Por que importa.** A avaliação é o que o §8 manda usar para escolher entre Sonnet e Opus ("decida pela diferença
no acerto exato"). Com 18 falsos negativos na camada preferida, a métrica mede a formatação, não o modelo.

**Correção sugerida.**

- No §7, descrever a normalização: 6 casas, data ISO sem hora à meia-noite, linhas ordenadas. Ou apontar para
  `normalizar_resultado` e `resultado_sql_semantico` do gerador, para quem puder importá-los.
- Dizer como tratar o SQL que o agente escreve: ordem de linhas e alias de coluna diferentes do esperado. Sugestão:
  comparar as linhas como multiconjunto e as colunas pela posição, com alias livre.

### RGA-03 — "ordene o resultado por camada" rebaixa a golden query certa (média, documento §3 e §5)

**Evidência.**

- O §3 manda "Ordene o resultado por `camada`: `semantica`, depois `core` e `analytics`…".
- O §5 repete: "Reordena pela prioridade de camada".
- O guia §2, no entanto, manda usar raw e staging quando a pergunta "pede o que a fonte publicou", e o `original`
  quando pede paridade com o MVP.
- No protótipo, a ordenação estável por camada sobre o top 5 levou a golden query certa:
  - de 1º para **4º** em "Em que formato a RFB publica o capital social?";
  - de 1º para **2º** na pergunta de paridade e na de concorrência de analytics.

  Nos três casos, o 1º lugar passou a ser a irmã semântica ou de core do mesmo conceito.

**Por que importa.** O documento manda mostrar ao modelo "o `sql` e as `armadilhas`" das recuperadas. Com a certa
fora do topo, o modelo parte da golden query errada justamente nas perguntas em que a camada importa.

**Correção sugerida.**

- Ordenar por relevância e usar a camada só como desempate, ou como um reforço pequeno na nota.
- Ou classificar a pergunta antes (auditoria, paridade ou negócio) e, só nas de negócio, filtrar fora raw, staging,
  intermediate e original.
- O "só para auditoria" do §3 já sugere isso, mas "ordene" diz outra coisa.

### RGA-04 — a falha fechada do §6 não acha as relações das golden queries (média, documento §6)

**Evidência.**

O §6 manda não responder com uma golden query cuja relação (`tabelas`) divergiu. Rodei a conferência no warehouse
das fixtures (`conferencia_esquema.py`):

- **Prefixo.** `relacoes[].nome` vem com prefixo (`main.dim_cnae`). `tabelas` e
  `information_schema.columns.table_name` vêm sem ele (`dim_cnae`). Das 101 entradas de `tabelas`, nenhuma casa
  literalmente com `relacoes`. Com `main.` na frente, 88 casam.
- **Fontes raw.** 13 entradas são fontes raw (`rfb.empresas`, `ibge.cempre_municipio_cnae`…), que não estão em
  `relacoes` nem no `information_schema`: a regra não as cobre.
- **Semântica.** As **20 golden queries semânticas não têm `tabelas`**. O SQL delas lê 10 relações do gold, entre
  elas `fct_resumo_mensal` e `dim_municipio`. Se uma dessas divergir, a regra não bloqueia nenhuma semântica,
  justamente a camada preferida.

**Por que importa.** A falha fechada é a defesa contra catálogo e banco de versões diferentes, já que o banco não
tem carimbo. Do jeito que está escrita, ela ou não casa nada (sem normalizar) ou deixa passar a semântica.

**Correção sugerida.**

- No §6, dizer a normalização: tirar o `main.` de `relacoes[].nome`, e tratar `tabelas` com ponto (`rfb.*`,
  `ibge.*`) como fonte raw, conferida pelos arquivos sob `${RAIZ_DADOS}/raw`.
- Para a semântica, uma de duas:
  - extrair `main.<x>` do `sql`, que é o que o protótipo fez;
  - preencher `tabelas` também na semântica, no gerador. É aditivo.

### RGA-05 — `checar_saida` "como está" deixa passar CNPJ em decimal, double e lista (média, guia §7, citado no §5)

**Evidência.**

- O §5 recomenda reaproveitar a função do guia §7 "como está".
- O §1 diz que a checagem roda "no código, não por confiança no modelo".
- Com a coluna renomeada para `x`, testei a função do guia:

| Valor | Tipo em Python | Problemas |
|---|---|---|
| `11222333000181` | `int` | detectado |
| `11222333000181::hugeint` | `int` | detectado |
| `11222333000181::decimal(18,0)` | `Decimal` | **nenhum** |
| `11222333000181::double` | `float` | **nenhum** |
| `['11222333000181']` (ex.: `array_agg(cnpj_completo) as x`) | `list` | **nenhum** |

A regra da derivada do guia proíbe essas formas no SQL, mas a checagem existe para quando o modelo erra. A RGQ-04 já
tratou nome de coluna e texto; os tipos numéricos não inteiros e os aninhados ficaram de fora.

**Correção sugerida.**

- No guia §7, achatar listas, structs e mapas antes de checar, e tratar `Decimal` e `float` inteiros como `int`.
- Até lá, o §5 deveria dizer "reaproveite e estenda", não "como está".

### RGA-06 — o teste só olha a primeira coluna das tabelas do §3 (baixa, testes)

**Evidência.**

- O brief do GA pede que "todo nome de campo do catálogo citado no documento entre crases" exista no catálogo.
- `campos_inexistentes` só lê a primeira coluna das tabelas da seção "O que indexar". Os campos citados em prosa ou
  em outras seções ficam fora: `conceitos[].definicoes`, `proibida_na_saida`, `colunas[].tipo`, o `versao_projeto`
  do §6 e os campos devolvidos por `buscar_golden` no §5.
- Quatro mutações nesses campos sobreviveram (ver [Mutações](#mutações)).

**Correção sugerida.** Conferir todo identificador entre crases com cara de campo (`[a-z_]+`, com `[]` e `.`) em §3,
§5 e §6, com uma lista de exceções para nomes de ferramenta e de SQL. Ou, no mínimo, os de `buscar_golden` e o
`versao_projeto`.

### RGA-07 — o manifesto do mês tem versão, ao contrário do que diz o §6 (baixa, documento §6)

**Evidência.**

- O §6 diz: "o manifesto da ingestão é de arquivos do mês, não da versão do projeto".
- Mas `_manifestos/AAAA-MM.json` traz `versao_pipeline` (`manifesto.py`, igual a `__version__`). Nas fixtures,
  `1.5.1`.

A conclusão do §6 continua certa, por três motivos:

- o manifesto não é consultável por SQL e não vai ao MotherDuck;
- registra a versão que **ingeriu**, não a que rodou o dbt depois;
- `Manifesto.from_dict` preenche a chave ausente com a versão **atual**, o que faz um manifesto antigo parecer novo.

**Correção sugerida.** Trocar a frase: o manifesto tem `versao_pipeline`, mas é a versão da ingestão, não está no
banco e, nos manifestos antigos, é preenchida com a versão atual. Por isso a conferência é por esquema.

### RGA-08 — no MotherDuck, `table_schema = 'main'` pode trazer outros bancos da conta (baixa, plausível, documento §6)

**Evidência.**

- Localmente, `information_schema.columns` só tem o catálogo `warehouse`, com os schemas `main` e
  `main_dbt_test__audit`, e o filtro basta.
- No `md:<banco>`, a sessão costuma enxergar os outros bancos da conta, como o `sample_data`, também com schema
  `main`. As colunas deles entrariam como "coluna a mais" ou se misturariam com as de mesmo nome.
- Não testei: não há token no ambiente.

**Correção sugerida.** Acrescentar `and table_catalog = current_database()` à consulta do §6.

### RGA-09 — `identifica_estabelecimento` nunca se aplica (baixa, documento §5)

**Evidência.**

- O §5 diz "Peça ao usuário `identifica_estabelecimento=True` apenas quando a golden query tiver
  `privacidade: identifica_estabelecimento`". Mas as 93 golden queries são `agregado`.
- O guia §7 permite CNPJ quando a pergunta é sobre um estabelecimento identificado ("este CNPJ está ativo?"), o que
  hoje sempre exige SQL novo.

Quem constrói não sabe quem liga o parâmetro nem quando: a frase "peça ao usuário" também é ambígua.

**Correção sugerida.** Dizer que hoje nenhuma golden query liga o parâmetro. Dizer também que a decisão é da etapa de
classificação, para pergunta sobre um CNPJ dado pelo usuário, e nunca do modelo durante a execução.

### RGA-10 — pequenas inconsistências (baixa, documento)

- **Tamanhos datados.** O título diz "(v1.5.0)", e o próprio lote mudou os números.
  - O guia agora tem **830** linhas e 113.898 bytes; o documento diz 828 linhas e 113.740 bytes, nos §3 e §4.
  - O catálogo tem 491.069 bytes; o documento diz 491.040, por causa do `versao_projeto`.
  - Os bytes dos blocos são do `json.dumps` sem indentação (separadores padrão), o que não está dito. Eles batem
    exatamente nessa serialização.
- **Prompt × ferramentas.** O prompt lista `checar_saida` como ferramenta do modelo, mas o §5 manda chamá-la dentro
  de `executar_sql_leitura`. Basta uma das duas, e o §5 tem razão.
- **Mês da base.** "A base é do mês `<AAAA-MM>`" não diz de onde vem. Sugestão: `select max(mes_referencia) from
  main.fct_resumo_mensal`.
- **Filtro de `SELECT`.** O "único `SELECT`/`WITH`" recusa a forma `FROM tabela` do DuckDB, que é de leitura. Isso é
  conservador e aceitável, mas vale uma linha.
- **Pergunta repetida.** "Quantos MEI ativos há em cada UF?" está em `gq_core__simples_mei__01` e em
  `gq_semantica__simples_mei__01`. Na avaliação, o "acerto da camada" dessa pergunta precisa aceitar as duas.

## Mutações

Rodei `pytest tests/unit/test_construcao_agente.py tests/unit/test_cabecalho_docs.py` depois de cada mutação e
reverti com `git checkout`.

| # | Mutação | Resultado |
|---|---|---|
| M1 | §3, tabela: `colunas_chave` → `colunas_chaves` | morta (1 falhou) |
| M2 | §6: `versao_projeto` → `versao_catalogo` | **sobrevive** |
| M3 | §3, prosa: `conceitos[].definicoes` → `conceitos[].definicao` | **sobrevive** |
| M4 | §3, prosa: `proibida_na_saida` → `proibido` | **sobrevive** |
| M5 | §5: `buscar_golden` devolve `chaves` em vez de `colunas_chave` | **sobrevive** |
| M6 | §3, tamanhos: `491.040` → `9.999` | **sobrevive** (nada confere os tamanhos; ver RGA-10) |
| M7 | catálogo sem a linha `versao_projeto` | morta (1 falhou) |
| M8 | §3, tabela: `privacidade` → `sigilo` | morta (1 falhou) |

M2 a M5 são o RGA-06. M6 é aceitável, porque tamanho medido envelhece, mas pede a data ou a versão certa no título.

## Conferências

### Campos e contagens

| Afirmação do documento | Conferido |
|---|---|
| 93 golden queries, 23 conceitos, 48 relações | 93, 23, 48 |
| `metricas` (29), `dimensoes` (50) | 29, 50 |
| Campos do índice (§3) | todos existem. Na semântica faltam `tabelas` e `colunas_chave` e há `metricas`, `comando`, `group_by`, `where`, `saved_query` |
| `relacoes`: `nome`, `camada`, `grao`, `descricao`, `colunas` (`nome`, `tipo`, `descricao`, `proibida_na_saida`) | exato |
| `privacidade` é `agregado` ou `identifica_estabelecimento` | as 93 são `agregado` (RGA-09) |
| Seções 11 e 12 do guia, "cerca de 315 linhas" | linhas 515 a 830: 316 |

### Tamanhos (bytes do `json.dumps` sem indentação; tokens = bytes ÷ 4)

| Bloco | Documento | Medido |
|---|---|---|
| `catalogo.json` | 491.040 | 491.069 (+29, o `versao_projeto`) |
| `golden_queries` | 212.402 | 212.402 |
| `relacoes` | 124.672 | 124.672 |
| `dimensoes` | 16.586 | 16.586 |
| `metricas` | 13.536 | 13.536 |
| `conceitos` | 26.974 | 26.974 |
| Guia | 113.740 / 828 linhas | 113.898 / 830 linhas (o lote acrescentou 2) |

Não medi tokens com um tokenizador real. A divisão por 4 está declarada como estimativa, e o documento manda medir.

### DuckDB local × MotherDuck, versão e camadas

- **Camadas.** O local tem gold, staging, intermediate e seeds, e o raw por `read_parquet`. O MotherDuck tem só o
  gold. Confere com o guia §3.
- **Seeds.** A conferência do §6 restrita a `core`, `analytics` e `original` no MotherDuck exclui os 4 seeds e
  `relacoes` não tem relação de camada `semantica`, então está certa.
- **SQL semântico.** Lê só relações de core e analytics: `dim_*`, `fct_*`, `mart_emprego_setor_municipio` e
  `mart_sobrevivencia_coorte`. Roda no MotherDuck.
- **Carimbo de versão.** Não há carimbo de versão consultável no banco.
  - `dq_resumo_execucao` só tem `invocation_id`, data e contagens de testes.
  - `dbt_project.yml` tem `version: "1.0.0"`, fixo e fora do banco.
  - O manifesto tem `versao_pipeline`, mas fora do banco (RGA-07).
- **Marcador.** `${RAIZ_DADOS}` só no raw, e `normalizar_sql` o grava assim.
- **Falha fechada.** A conferência por esquema rodou nas fixtures sem falso positivo. Os nomes e as dificuldades de
  ligar `tabelas` às relações estão no RGA-04. As tabelas `dq_historico_testes` e `dq_resumo_execucao` estão no banco
  e fora de `relacoes`; como o §6 percorre `relacoes`, não atrapalham.

### Compatibilidade (patch)

- **`versao_projeto` é aditivo.** O topo ganhou uma chave, nenhuma mudou, e `formato` continua `1`. No repositório,
  só o gerador, o teste novo e `tests/integration/test_golden_queries.py` leem o catálogo, e nenhum deles valida o
  conjunto de chaves.
- **Acoplamento novo.** Daqui em diante, todo `chore: versão` precisa regenerar o catálogo, como o `4c1e992` fez, ou
  o teste unitário quebra. Isso exige o warehouse do `make ci`. Não há checklist de release que diga isso. O teste
  pega rápido, então não é achado, mas vale uma linha na operação.
- **Links.** README, `consulta-agente.md`, ADR-0023 e CHANGELOG só ganharam um link ou uma linha cada. O verificador
  de links do `make ci` passou.

## Triagem do líder

Data: 2026-10-15. Veredito da RGA: **aprovável como patch, com ressalvas.**
- São 1 achado alto, 4 médios e 5 baixos.
- O protótipo que seguiu o documento montou o índice e executou em modo somente leitura. Mas a comparação de
  respostas e a conferência de esquema, do jeito que o documento manda, não funcionaram, e a ordenação por camada
  rebaixou a golden query certa.
- Das 8 mutações, 5 sobreviveram.

Como o documento existe para o usuário construir o agente noutro projeto, **todos os achados entram antes da release**.
As correções ficam com o lote **FGA**, um agente novo (Opus, esforço médio). O lote é de nível acima do GA porque o
RGA-01 é de segurança.

| Achado | Decisão | Lote | Resolvido em |
|---|---|---|---|
| **RGA-01** `read_only` e o filtro de SELECT ainda leem qualquer arquivo e acessam a rede | O endurecimento testado pela RGA (`allowed_directories` na raiz dos dados, `enable_external_access=false`, `autoinstall_known_extensions=false`, `lock_configuration=true`) entra como **receita obrigatória** da ferramenta de execução, em `construcao-agente.md` e no guia §3. Teste: as golden queries rodam todas com essa conexão (no raw, depois de trocar `${RAIZ_DADOS}`), e leitura de arquivo fora da raiz, URL `https://`, `COPY ... TO` e `INSTALL` falham. No MotherDuck, dizer o que se aplica e o que não, sem afirmar o que não foi testado | FGA | `10f4575`, `69a71d9` (testes), `264d226`, `f6406de` (teste do lock) |
| **RGA-02** a comparação exata reprova o próprio `sql` do catálogo | O documento traz a função de comparação (`comparar_resposta`) num bloco marcado, com a normalização que o CI usa (decimais, datas ISO, meia-noite → data, ordem das linhas na semântica). Teste: ela é extraída do documento e aprova as 93 golden queries contra `resposta_esperada_fixtures` | FGA | `7cfd82c`, `69a71d9` (testes) |
| **RGA-03** ordenar por camada rebaixa a golden query certa | A camada vira **desempate** entre candidatos de relevância próxima, não a ordem principal, como no guia §2. Ajustar o texto e o exemplo | FGA | `cc24ab7` |
| **RGA-04** a conferência de esquema com falha fechada não casa nada sem normalizar | O documento traz a função `conferir_esquema` num bloco marcado, com a normalização: tira o `main.`; trata as fontes raw (`rfb.*`, `ibge.*`) como fora do banco; nas semânticas, as tabelas vêm do `sql` ou de um campo novo `tabelas` gerado no catálogo, o que for mais simples e testável. Teste: aprova o warehouse das fixtures e reprova um esquema mutado (coluna removida de uma relação usada) | FGA | `5017008` (`tabelas` na semântica), `69a71d9`, `4865e3b` |
| **RGA-05** `checar_saida` (guia §7) deixa passar CNPJ como Decimal, double ou lista | Corrigir a função no guia: normaliza números inteiros em qualquer tipo numérico e percorre listas e structs. Teste com os vazamentos da RGA | FGA | `381c15c` |
| **RGA-06** o teste só olha a 1ª coluna do §3 | Ampliar a guarda para todo nome de campo do catálogo citado no documento (prosa, §5, §6), com uma convenção explícita de marcação, se for preciso. M2, M3, M4 e M5 têm de morrer | FGA | `e7c9666` |
| **RGA-07** o §6 diz que o manifesto não tem versão | Corrigir: `_manifestos/AAAA-MM.json` tem `versao_pipeline` (versão da ingestão, fora do banco; o manifesto antigo herda a atual). A conclusão (conferência por esquema) fica | FGA | `69a71d9` |
| **RGA-08** MotherDuck: `table_schema='main'` pode trazer outros bancos | Acrescentar `table_catalog = current_database()` na conferência, com a ressalva de que não foi testado sem token | FGA | `69a71d9` |
| **RGA-09** quem liga `identifica_estabelecimento` | Dizer que é política do construtor, desligada por padrão. Hoje nenhuma golden query a usa | FGA | `10f4575` |
| **RGA-10** tamanhos datados e inconsistências menores | Os tamanhos passam a ser **gerados** (bloco marcado em `construcao-agente.md`, atualizado pelo `make golden` e conferido no CI), o que mata a M6. Também: `checar_saida` dentro da ferramenta de execução, e não como ferramenta do modelo; a origem do mês da base no prompt; o filtro que recusava `FROM tabela`; a pergunta repetida entre core e semântica | FGA | `5017008` (tamanhos gerados), `cc24ab7` (prompt, mês), `10f4575` (filtro `FROM tabela`), `7cfd82c` (pergunta repetida) |

## Reteste (FGA)

Data: 2026-10-15. Refiz o protótipo (a)–(d) usando só as funções dos blocos marcados de `construcao-agente.md`
(`conectar_somente_leitura`, `exigir_leitura`, `comparar_resposta`, `conferir_esquema`) e `checar_saida` do guia §7,
extraídas por regex e executadas como estão, sobre o `.tmp/ci/dados` do `make ci`. A busca é um BM25 próprio (o
protótipo da RGA ficou no scratch do revisor), então as posições "antes" não são idênticas às da tabela (b) acima.

| Etapa | Resultado |
|---|---|
| (a) Índice | 93 documentos; as 93 golden queries têm `tabelas` (as 20 semânticas, pelo `sql`) |
| (b) Recuperação, pergunta exata | por relevância, a certa fica em 1º em 4 de 5 (core em 2º, atrás da irmã semântica); com a reordenação antiga por camada, raw cairia para 3º e analytics e original para 2º; com a camada só como desempate (notas a menos de 5 % da maior), as posições da relevância se mantêm |
| (c) Execução | as 93 rodam pela conexão endurecida e passam por `exigir_leitura`; `comparar_resposta` aprova **93 de 93** (antes: 24 falhas cruas); `conferir_esquema` devolve `([], [])` |
| (c) Ataques | `read_text('/etc/hosts')`, `glob('/Users/*')` e `read_csv('https://…')` passam pelo filtro, mas a conexão recusa (`Permission Error`); `COPY ... TO` fora da raiz, `INSTALL`, `ATTACH` e `SET` são recusados pelos dois; `COPY ... TO` **dentro** da raiz só o filtro recusa (o documento diz isso); `FROM tabela` agora passa |
| (d) `checar_saida` | as 5 saídas sem problema; controle positivo com os 4 problemas; CNPJ como `int`, `Decimal`, `float`, lista e struct, todos detectados |

### Mutações (FGA)

Aplicadas no documento, testadas e revertidas com `git checkout`.

| # | Mutação | Resultado |
|---|---|---|
| M2 | §6: `versao_projeto` → `versao_catalogo` | morta: `assert ['versao_catalogo'] == []` |
| M3 | §3: `conceitos[].definicoes` → `conceitos[].definicao` | morta: `assert ['conceitos[].definicao'] == []` |
| M4 | §3: `proibida_na_saida` → `proibido` | morta: `assert ['proibido'] == []` |
| M5 | §5: `buscar_golden` devolve `chaves` | morta: `assert ['chaves'] == []` |
| M6 | tamanhos: `124.672` → `9.999` | morta: o bloco de tamanhos difere do gerado ("rode `make golden`") |
| F1 | sem `enable_external_access = false` | morta: `DID NOT RAISE` em `read_text` fora da raiz |
| F2 | `comparar_resposta` sem a regra da meia-noite | morta: 13 golden queries semânticas reprovadas |
| F3 | `conferir_esquema` sem tirar o `main.` | morta: 48 "relação ausente no banco" nas fixtures |
| F4 (líder) | sem `lock_configuration = true` | sobrevivia; morta depois do `f6406de`: 7 falhas, `DID NOT RAISE` em `set autoinstall_known_extensions = true`, `set autoload_known_extensions = true`, `reset autoinstall_known_extensions` e `set lock_configuration = false`; nos de `allowed_directories` e `enable_external_access`, a mensagem deixa de ser a do lock ("Cannot change allowed_directories when enable_external_access is disabled", "Cannot enable external access while database is running") |

Uma variante de F3 só no cálculo do banco só-gold sobrevivia (o caso só-gold ficava sempre verdadeiro); o teste do
`4865e3b` (staging ausente num banco local tem de ser cobrado) a mata. A F4, achada pelo líder, mostrou que nenhum teste
exigia o lock: sem ele, o DuckDB 1.5 já recusa ampliar `allowed_directories` e religar o acesso externo, mas aceita
religar a instalação e a carga automáticas de extensão e destravar a configuração.
