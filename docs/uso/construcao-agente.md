# Construção do agente de consulta

> **Para quem:** quem vai **programar** o agente que responde perguntas em linguagem natural sobre a base (um modelo
> Sonnet ou Opus com RAG), num outro projeto · **Quando ler:** antes de escrever a primeira linha do agente; o
> [guia de consulta](consulta-agente.md) é o que o próprio agente lê.

Dois documentos, dois leitores. O [guia de consulta](consulta-agente.md) é o **prompt de trabalho do agente**: camadas,
esquema, grão, armadilhas, privacidade, procedimento. Este é para **quem constrói**: o que indexar, o que vai no prompt,
quais ferramentas dar ao modelo, como casar catálogo e banco, como avaliar. Ele não repete o guia: aponta para a seção.
A decisão de ter golden queries e catálogo está na [ADR-0023](../adr/0023-golden-queries-e-guia-para-agente.md).

O agente **não roda `dbt`** e não deduz SQL do código dbt (Jinja, `ref()`, `source()`). O catálogo traz o SQL
**compilado** (`main.<relação>`; o marcador `${RAIZ_DADOS}` só no raw), testado no CI exatamente como o agente o
executa. Na camada semântica, o SQL é o que o MetricFlow gera.

## 1. Arquitetura de referência

```mermaid
flowchart TD
    P[Pergunta] --> C{Classificar<br/>guia §8, passo 1}
    C -- ambígua e a escolha muda a resposta --> E[Pedir esclarecimento]
    C -- dado pessoal ou fora da base --> R[Recusar e oferecer o agregado]
    C -- consulta --> B[buscar_golden: 3 a 5 golden queries]
    B --> A[Adaptar o sql pelas variacoes<br/>aplicar as armadilhas]
    A --> S[Conferir o esquema<br/>descrever_relacao]
    S --> X[executar_sql_leitura<br/>somente leitura, LIMIT, timeout]
    X --> V[checar_saida: privacidade]
    V -- problema --> A
    V -- ok --> O[Resposta: número, mês de referência,<br/>fonte, camada e ressalvas]
```

Sem golden query próxima, o modelo escreve SQL novo a partir de `relacoes` e do grão e dos joins (guia §4), conferindo
o esquema (guia §8, passo 4). A checagem de privacidade roda **depois de toda execução**, no código, não por confiança
no modelo.

## 2. Pré-requisitos

- **Um banco construído pelo pipeline**, fora do agente: `make pipeline` (ou `make atualizar` todo mês) cria o
  `warehouse.duckdb`; `make publicar` leva o gold ao MotherDuck. O agente só lê.
- **DuckDB local × MotherDuck** (detalhe no guia §3):

| | `warehouse.duckdb` local | MotherDuck ([ADR-0016](../adr/0016-publicacao-motherduck.md)) |
|---|---|---|
| Camadas | gold, staging, intermediate e seeds; o raw por `read_parquet` | **só o gold**, como tabelas |
| Golden queries que rodam | todas (raw troca o marcador) | semântica, core, analytics, original |
| Somente leitura | `duckdb.connect(caminho, read_only=True)` | **Read Scaling token**; a conexão não protege |

- **Versão do banco.** Um banco anterior à v1.4 não tem os modelos do IBGE (`bridge_municipio_destino_compras`,
  `mart_emprego_setor_municipio`, colunas do IBGE em `dim_municipio`): as golden queries desses conceitos falham.
  Reconstrua com o pipeline atual.

## 3. O que indexar

Os nomes de campo abaixo são os do `catalogo.json`; o teste do repositório confere que existem.

### Índice principal: uma entrada por golden query (93)

| Campo | Papel no índice |
|---|---|
| `perguntas` | **texto a embutir**, junto com `intencao` e o nome e a definição do conceito (`conceitos[].definicoes`) |
| `intencao` | texto a embutir |
| `id` | metadado de filtro e chave do documento |
| `conceito` | metadado de filtro |
| `camada` | metadado de filtro e de prioridade |
| `privacidade` | metadado de filtro (`agregado` ou `identifica_estabelecimento`) |
| `tabelas` | metadado de filtro e da falha fechada (seção 6); sem o `main.`; com ponto (`rfb.empresas`) é fonte raw; na semântica, as relações que o `sql` lê |
| `sql` | **payload** devolvido ao modelo |
| `armadilhas` | payload |
| `variacoes` | payload |
| `colunas_chave` | payload (camadas SQL) |
| `resposta_esperada_fixtures` | payload, **só como forma da saída** (colunas); as linhas são das fixtures |

Um documento por golden query: não quebre em pedaços. Texto sugerido para o embedding: perguntas, uma por linha, mais
a intenção e `Conceito: <nome>. <definição>`. Recupere de **3 a 5**, mostre ao modelo o `sql` e as `armadilhas`, e
deixe-o adaptar pelas `variacoes`. Na semântica, `comando` e `group_by` são do `mf` e **não** vão ao modelo (o guia §2
explica por quê).

**Prioridade de camada.** Ordene o resultado por `camada`: `semantica`, depois `core` e `analytics`; `raw`, `staging`
e `intermediate` só para auditoria; `original` só se a pergunta pedir paridade com o MVP (guia §2). Com MotherDuck,
filtre fora `raw`, `staging` e `intermediate`.

### Conceitos, métricas, dimensões e relações

- `conceitos`: um item por conceito (23), com `nome` e `definicoes`; entra no texto embutido das golden queries e pode
  ser um índice à parte para as perguntas de vocabulário (guia §5).
- `metricas` e `dimensoes`: contexto curto, útil para a semântica; o guia §12 já traz as duas listas.
- `relacoes` (48): `nome`, `camada`, `grao`, `descricao` e `colunas` (`nome`, `tipo`, `descricao`,
  `proibida_na_saida`). É o maior bloco depois das golden queries. Ofereça-o como a ferramenta `descrever_relacao`
  (seção 5) e deixe só `nome`, `camada` e `grao` no contexto; se couber, o JSON inteiro dispensa a ferramenta.

### Tamanhos medidos

Estimativa de tokens = bytes ÷ 4, uma aproximação para texto em português e JSON; meça com o tokenizador do seu
modelo antes de decidir. O bloco abaixo é gerado pelo `make golden` e conferido no CI: o catálogo inteiro é o arquivo
como é distribuído; cada bloco, o `json.dumps` compacto (separadores padrão, acentos em UTF-8).

<!-- INÍCIO do bloco gerado dos tamanhos por scripts/gerar_catalogo_golden.py (make golden): não edite à mão -->

Medido na versão 1.5.1 (`versao_projeto` do catálogo).

| Bloco | Bytes | Tokens (est.) |
|---|---|---|
| `catalogo.json` inteiro (o arquivo) | 492.746 | ~123.200 |
| `golden_queries` (93) | 213.471 | ~53.400 |
| `relacoes` (48) | 124.672 | ~31.200 |
| `dimensoes` (50) | 16.586 | ~4.100 |
| `metricas` (29) | 13.536 | ~3.400 |
| `conceitos` (23) | 26.974 | ~6.700 |
| Guia `consulta-agente.md` (848 linhas) | 114.684 | ~28.700 |
| Guia, seções 11 e 12 (316 linhas) | 72.348 | ~18.100 |

<!-- FIM do bloco gerado dos tamanhos -->

O catálogo inteiro não cabe com folga num prompt e custa caro a cada pergunta: use o RAG. O guia cabe.

### O que não indexar

O SQL Jinja do dbt (`transform/`; o `arquivo` de cada golden query aponta para ele, mas o modelo deve usar o `sql`),
`docs/historico/` e as ADRs (decisões, não instruções para o agente).

## 4. Prompt de sistema

**Entra:** o guia inteiro, `consulta-agente.md` (linhas e tokens estimados na seção 3), mais as regras duras abaixo,
repetidas no fim porque são as que não podem falhar. **Fica fora:** o catálogo, que chega pelo RAG a cada pergunta.
Se precisar economizar, as seções 11 e 12 do guia (o índice e o esquema, tamanho na seção 3) repetem o catálogo e
são as candidatas a sair, desde que `buscar_golden` e `descrever_relacao` cubram o mesmo conteúdo.

Modelo, com os blocos (preencha `<…>`; **não copie o guia aqui, ele vai no bloco 3**):

```text
# 1. Papel
Você responde perguntas sobre empresas brasileiras (CNPJ) usando a base descrita abaixo. Só tem as ferramentas
buscar_golden, descrever_relacao, executar_sql_leitura e checar_saida. A base é do mês <AAAA-MM>.

# 2. Regras duras
- Somente leitura. Nunca DDL/DML, nunca dbt, nunca mf query.
- Nunca devolva nome de pessoa, CPF, contato, endereço, nem CNPJ em massa. Recuse e ofereça o agregado.
- Nunca adivinhe nome de coluna: confira com descrever_relacao. Sempre use LIMIT.
- Toda execução passa por checar_saida; com problema, refaça só com agregados ou recuse.

# 3. Guia
<conteúdo integral de docs/uso/consulta-agente.md>

# 4. Procedimento (resumo; o completo está no guia §8)
Classifique · resolva o vocabulário (§5) · escolha a camada (§2) · parta da golden query mais próxima e leia as
armadilhas · valide grão e filtros (§4) · execute com LIMIT e checagem (§7) · responda.

# 5. Formato da resposta
O número pedido; o mês de referência (e o ano de cada fonte não RFB); a fonte e a golden query ou camada usada;
as ressalvas que mudam a leitura. Pedido ambíguo: pergunte antes (guia §9, exemplo 3).
```

## 5. Ferramentas sugeridas

| Ferramenta | Comportamento |
|---|---|
| `buscar_golden(pergunta: str, k: int = 5, filtros: dict = {})` | Busca vetorial no índice principal; `filtros` sobre `camada`, `conceito`, `privacidade`. Devolve, por golden query, `id`, `camada`, `perguntas`, `sql`, `armadilhas`, `variacoes`, `colunas_chave`. Reordena pela prioridade de camada. |
| `descrever_relacao(nome: str)` | Devolve `grao`, `descricao` e `colunas` da relação em `relacoes` (ou consulta `information_schema.columns`). Nome desconhecido: devolve erro com as relações parecidas. |
| `executar_sql_leitura(sql: str, limite: int = 50)` | Troca `${RAIZ_DADOS}` pela raiz dos dados (só no local); recusa tudo que não seja um único `SELECT`/`WITH` (DDL, DML, `COPY`, `ATTACH`, `INSTALL`); acrescenta `LIMIT` se faltar; aplica timeout; devolve `colunas` e `linhas`. |
| `checar_saida(colunas, linhas, identifica_estabelecimento=False)` | A função do bloco `python` do [guia §7](consulta-agente.md#checagem-obrigatória-pós-execução), que você pode reaproveitar **como está**. Devolve a lista de problemas; vazia = pode responder. |

Chame `checar_saida` dentro de `executar_sql_leitura` e devolva ao modelo o problema no lugar das linhas: assim ela não
depende de o modelo lembrar. Peça ao usuário `identifica_estabelecimento=True` apenas quando a golden query tiver
`privacidade: identifica_estabelecimento`.

## 6. Versão do catálogo × banco

O catálogo e o banco têm de ser da **mesma versão do projeto**: o `sql` usa os nomes de relação e de coluna daquela
versão.

- **Entregue o catálogo da tag que construiu o banco.** O `catalogo.json` traz `versao_projeto` (desde a v1.5.1);
  guarde a tag junto do índice vetorial.
- **O banco não carrega carimbo de versão consultável.** `dq_resumo_execucao` só tem a execução do dbt, a contagem de
  testes e a data; o manifesto da ingestão é de arquivos do mês, não da versão do projeto. Por isso a conferência é
  **por esquema**.
- **Na partida**, para cada item de `relacoes` presente no banco (no MotherDuck, só `core`, `analytics` e `original`),
  compare `colunas[].nome` e `colunas[].tipo` com `information_schema.columns`:

```sql
select table_name, column_name, data_type
from information_schema.columns
where table_schema = 'main'
```

- **Relação ou coluna faltando no banco:** banco mais antigo que o catálogo. Reconstrua o banco (`make atualizar`) ou
  use o catálogo da tag anterior. **Coluna a mais no banco:** banco mais novo; use o catálogo da tag nova.
- **Falha fechada.** Se a divergência atinge uma relação que alguma golden query usa (`tabelas`), não responda com
  ela: avise o operador. Divergência só em relação que nenhuma golden query cita pode virar aviso no log.

## 7. Avaliação

As golden queries são um **conjunto de avaliação pronto**. Construa o banco das fixtures (`make ci` gera
`.tmp/ci/dados`), rode o agente com cada item de `perguntas` e compare a saída com `resposta_esperada_fixtures`
(`colunas` e `linhas`).

- **Perguntas de recusa e de esclarecimento**, além das golden queries: os exemplos 3 ("Quantas empresas tem em Água
  Branca?") e 5 ("Me passa o nome e o telefone dos MEI…") do [guia §9](consulta-agente.md). Esperado: pergunta de
  volta e recusa com o agregado oferecido, sem executar SQL de pessoa.
- **Métricas:** acerto exato (mesmas `linhas`); acerto da camada (a escolhida é a de `camada`, ou uma que a
  [regra do guia §2](consulta-agente.md) aceita); violações de privacidade, com meta **zero** (conte as saídas que
  `checar_saida` recusa e as respostas em texto que trazem pessoa).
- Rode também com a redação de cada pergunta alterada (sinônimos, outro município) para medir a recuperação, e sem a
  golden query esperada no índice para medir o SQL novo.
- A resposta esperada é das **fixtures** (18 estabelecimentos); não compare com o banco real.

## 8. Escolha de modelo e custo

- **Sonnet** basta quando há golden query próxima: o trabalho é adaptar o `sql` e aplicar as `armadilhas`.
- **Opus** vale para o que exige raciocínio: pergunta ambígua que pede esclarecimento, SQL novo fora das golden
  queries (grão, joins, ponte com `distinct`), cruzamentos entre fontes de anos diferentes.
- Meça os dois no conjunto da seção 7 e decida pela diferença no acerto exato e nas violações, não por impressão.
- **Custo.** O prompt fixo é o guia (tokens estimados na seção 3) mais as k golden queries recuperadas; é o que
  se repete em toda pergunta. Use cache de prompt para o guia. O preço por token é do provedor e muda: calcule com a
  tabela vigente dele, não com números deste documento.

## 9. Segurança e privacidade

- **Somente leitura em duas camadas.** Local: `read_only=True` e o filtro de `SELECT` em `executar_sql_leitura`.
  MotherDuck: o **Read Scaling token** (o token comum escreve); o filtro continua valendo.
- **Limites:** `LIMIT`, timeout por consulta e teto de linhas devolvidas ao modelo.
- **Recusa de dado pessoal** é dupla: o prompt (guia §7) e `checar_saida` no código. Nenhuma das duas basta sozinha.
- **Logs sem dado pessoal** ([ADR-0008](../adr/0008-minimizacao-dados-pessoais.md)): registre `id` da golden query, SQL,
  camada, contagem de linhas, problemas da checagem e tempo. Não registre as linhas devolvidas; se registrar a
  pergunta, trate-a como dado do usuário.

## 10. Atualização

- **Reindexe a cada release** do projeto e a cada `make golden` (golden query nova, conceito novo, SQL alterado).
- O que mudou entre versões está no [CHANGELOG](../../CHANGELOG.md); olhe as seções "Adicionado" e "Alterado" antes de
  trocar o catálogo e o banco.
- O catálogo é **gerado e conferido no CI** (`make golden`, `make ci`): não o edite, não o regenere por fora. Atualize
  o banco **e** o catálogo juntos, e rode a avaliação (seção 7) antes de promover.

## 11. Limitações

- O MotherDuck não tem raw, staging nem intermediate: as golden queries dessas camadas não rodam lá.
- `resposta_esperada_fixtures` é das fixtures, não do real; serve para conferir o SQL, não é número do mundo.
- As fontes têm anos diferentes (RFB mensal, CEMPRE, Censo 2022, REGIC 2018, PIB): a resposta deve dizer o ano de cada
  uma (guia §8, passo 7).
- O banco real precisa estar na versão do catálogo (seção 6); o projeto não carimba a versão no banco.
- O projeto não tem sócios, contatos nem faturamento: pergunta sobre isso não tem resposta na base.
