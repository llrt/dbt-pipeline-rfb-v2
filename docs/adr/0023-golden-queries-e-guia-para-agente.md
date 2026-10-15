# ADR-0023 — Golden queries testadas, catálogo gerado e guia para um agente de consulta

**Status:** aceita (2026-10-14).

**Contexto.** Pedido do usuário (2026-10-14): registrar as golden queries de cada conceito do modelo, em cada
camada, para que mais à frente, em outro projeto, um agente use a documentação e essas consultas para responder
perguntas livres em linguagem natural sobre a base. A documentação existente ([camada semântica](../CAMADA_SEMANTICA.md),
[dicionário](../DICIONARIO_DADOS.md), [cenários](../CENARIOS_DE_USO.md)) foi escrita para pessoas: falta o que um
agente precisa para escolher a tabela certa, evitar as armadilhas do cadastro e respeitar a privacidade. Uma consulta
de exemplo que ninguém executa envelhece em silêncio quando o modelo muda.

**Decisão.**

- **Fonte de verdade = SQL em `transform/analyses/golden/`**, um arquivo por golden query,
  `gq_<camada>__<conceito>__<nn>.sql`. Cada arquivo abre com um cabeçalho YAML num comentário Jinja
  (`{# --- ... --- #}`: id, conceito, camada, 2 a 4 perguntas em português natural, intenção, tabelas, colunas-chave,
  armadilhas, variações, privacidade e a resposta exata nas fixtures). A config tem `meta.escopo: adicao` e a tag
  `golden_query` (mais o incremento, quando a query é de uma fonte de incremento). O dbt compila e valida os `ref()` e
  `source()`; o CI executa cada uma nas fixtures e confere a resposta, na ordem.
- **Camada semântica em `docs/golden_queries/semantica.yml`**: comandos `mf query` (métricas, dimensões, filtro) e as
  consultas salvas existentes, com o mesmo cabeçalho. O CI **executa** cada comando nas fixtures e compara a saída
  (linhas ordenadas, porque o MetricFlow não garante a ordem). Executar é mais forte que só `--explain`; custa ~30 s.
  Nenhuma consulta salva nova: as cinco existentes entram como golden queries.
- **Cobertura conceito × camada** em `docs/golden_queries/matriz.yml`: 22 conceitos × 7 camadas (raw, staging,
  intermediate, core, analytics, original, semântica). Toda célula tem golden query ou o motivo de não ter, nunca os
  dois; o motivo que cita outra golden query precisa citar uma que existe. O caminho que o agente **deve** usar é o
  gold e a semântica; raw e staging servem a auditoria e linhagem ("o que a RFB publicou"), e os modelos originais só
  à paridade com o MVP.
- **Catálogo gerado** `docs/golden_queries/catalogo.json`, por `scripts/gerar_catalogo_golden.py` (`make golden`), a
  partir dos cabeçalhos, do SQL **compilado** e de `semantica.yml`. O SQL compilado é normalizado para ser portável:
  `"warehouse"."main"."x"` vira `main.x` (o schema do warehouse local e do MotherDuck) e o caminho absoluto de
  `RAIZ_DADOS` nos `read_parquet` das fontes raw vira `${RAIZ_DADOS}`. O gerador também escreve a matriz e o índice
  num bloco gerado do guia. Como no dicionário (ADR-0019), o CI roda o gerador em modo `--verificar` e falha se o
  catálogo ou o bloco estiverem desatualizados.
- **Guia para o agente** [`docs/GUIA_CONSULTA_LINGUAGEM_NATURAL.md`](../GUIA_CONSULTA_LINGUAGEM_NATURAL.md), escrito
  para um LLM que só recebe o guia, o catálogo e acesso somente leitura ao DuckDB ou ao MotherDuck: regra de escolha
  da camada, esquema físico, grão e caminhos de join, glossário com as ambiguidades, armadilhas, privacidade,
  procedimento e exemplos de ponta a ponta.
- **Privacidade (ADR-0008) testada**: nenhuma golden query devolve coluna de nome, CPF, contato ou endereço (lista
  proibida no gerador, que também entende as dimensões `entidade__coluna` do MetricFlow); CNPJ só com
  `privacidade: identifica_estabelecimento` (nenhuma usa hoje); e os valores de texto passam pela guarda de
  identificador de `regras.py` (`traz_identificador`), salvo datas ISO.

**Alternativas descartadas.**

| Alternativa | Motivo |
|---|---|
| Golden queries só em Markdown | ninguém executa; envelhecem em silêncio quando um modelo muda |
| Um YAML com o SQL dentro | perde a compilação do dbt (`ref()` e `source()` validados) e o lint do SQL |
| Resposta esperada deduzida à mão | a regra do projeto é resposta conferida por execução; o teste compara com o resultado real |
| Validar a semântica só com `mf query --explain` | prova que o SQL é gerado, não que a métrica responde o esperado |
| Saved queries novas para cada golden query | aumentaria a camada semântica sem ganho: um `mf query` com `--metrics` é a mesma coisa |

**Consequências.** Mudar um modelo, uma métrica ou as fixtures pode mudar a resposta de uma golden query: o CI acusa, e
quem mudou revê a resposta (e a armadilha, se for o caso). Golden query nova exige rodar `make golden` e versionar o
catálogo. As analyses de `golden/` ficam fora da compilação do relatório do caso (`rfb relatorio`) e de `rfb regras`.
É só aditivo: nenhum modelo, coluna, grão, comando ou métrica existente mudou (versão 1.4.1).

**Revisão (RGQ, 2026-10-15).** A revisão independente ([RGQ](../revisoes/RGQ.md),
[triagem](../revisoes/RGQ-triagem.md)) mudou o seguinte, ainda na v1.4.1:

- **SQL da semântica no catálogo (RGQ-01).** O `mf query` exige o repositório e abre o warehouse em modo de escrita,
  o que o agente não pode fazer. Cada golden query semântica ganha o campo `sql`: o que o MetricFlow gera
  (`mf query --quiet --explain`), normalizado como o compilado (`main.x`). O gerador roda o `mf` sobre uma **cópia**
  do `warehouse.duckdb` (`CAMINHO_DUCKDB`), nunca sobre o original. O CI executa esse SQL numa conexão
  `read_only` e compara com a resposta esperada; o valor passa pelo mesmo texto do CSV do `mf` (o `DATE_TRUNC` devolve
  timestamp, `2026-08-01 00:00:00` vira `2026-08-01`). Esse teste substitui o que executava o `mf query`: o
  `--verificar` prova que o SQL é o que o `mf` gera hoje, e a execução prova que ele responde o esperado. O SQL gerado
  roda no DuckDB direto sem ajuste de dialeto. O guia manda o agente usar o `sql`; o `comando` fica para quem tem o
  repositório.
- **Esquema consultável gerado (RGQ-02).** O catálogo ganha `metricas` (tipo, natureza, medida, filtro e entidades
  aceitas), `dimensoes` (por entidade, com o nome qualificado do MetricFlow) e `relacoes` (colunas, tipos e a marca
  das colunas proibidas na saída), gerados do `semantic_manifest.json` e do `catalog.json` do dbt; o guia ganha um
  segundo bloco gerado com as métricas, as dimensões e as colunas do gold. Por isso o `make golden` roda
  `dbt docs generate` em vez de `dbt parse`. A natureza de cada métrica vem do modelo semântico da medida, numa tabela
  do gerador que falha com modelo novo. Um teste confere as dimensões contra `mf list dimensions`.
