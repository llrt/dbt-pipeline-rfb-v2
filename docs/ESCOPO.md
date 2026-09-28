# Escopo: original × adição × adaptado

> Marcação no código: `meta.escopo` + tag `escopo_<valor>` em cada nó dbt ([ADR-0006](adr/0006-marcacao-escopo.md)).
> Listar pelo dbt: `dbt ls --select tag:escopo_original` (ou `escopo_adicao`, `escopo_adaptado`).
> Fonte do original: [docs/referencia-original/](referencia-original/README.md).
> Esta tabela é mantida pelos lotes; a versão final é consolidada na tarefa T31.

Legenda: **original** = regra/artefato do MVP; **adaptado** = do MVP com mudança intencional documentada;
**adição** = novo neste port.

## Artefatos

| Artefato no port | Escopo | Origem no MVP / justificativa |
|---|---|---|
| Download dos zips RFB | adaptado | `baixar_dados_QSA-*.sh` (wget + unzip) → cliente WebDAV com retry/verificação (URL mudou, ADR-0003) |
| Conversão CSV (latin-1, `;`, escape `"`, multilinha) | original | notebook 1 (opções do `spark.read.csv`) |
| Raw em Parquet all-VARCHAR particionado por mês | adaptado | notebook 1 salvava tabela Spark com `inferSchema` (ADR-0002) |
| Tabelas BD `municipio`, `cnae_2` | original | notebook 1, seção 2 |
| Tabelas BD `populacao`, `pib`; RFB `simples`, `paises`, `qualificacoes` | adição | enriquecimento (densidade, MEI) |
| Manifesto, idempotência, limiar de rejeitos | adição | — |
| Upload para Tigris (`rfb sync`) | adaptado | `subir_arquivos_tigris.py` |
| Fontes dbt com testes de unicidade/completude/integridade/domínio | original | notebooks 2.1.1, 2.1.2, 2.2, 2.3 |
| Freshness das fontes | adição | — |
| Staging tipado | adição | original não tinha camada explícita |
| `bh_empresas` | original | notebook 3 |
| `bh_empresas.idade_atual` relativa a `data_referencia` | adaptado | notebook 3 usava `now()` (ADR-0004) |
| `agg_empresas` | original | notebook 3 |
| Teste de paridade com SQL original | adição | — |
| Star schema (`dim_*`, `fct_estabelecimentos`, bridge) | adição | "trabalhos futuros" do notebook 5 |
| `mart_concorrencia_municipio`, `mart_sobrevivencia_coorte`, `mart_dinamica_mercado`, `mart_fornecedores_proximos` | adição | aprofundam as perguntas do notebook 0/4 |
| Análises do estudo de caso Fundão/ES (`analyses/`) | original | notebook 4 |
| Relatório gerado do estudo de caso | adição | — |
| Testes CNPJ-DV, data não futura, reconciliação, histórico DQ | adição | — |
| Workaround Hive Metastore (`## Reconstruir tabelas Spark`) | removido | desnecessário: Parquet + DuckDB não têm metastore volátil |
| Script Pig `grep.pig` | removido | exploração manual; substituída por rejeitos do parser e fixtures com os quirks |

## Mapeamento de nomes de colunas (original → port)

| Original | Port |
|---|---|
| `CNAE_principal` | `cnae_principal` |
| `desc_CNAE_principal` | `desc_cnae_principal` |
| `grupo_CNAE_principal` | `grupo_cnae_principal` |
| `CNAEs_secundarios` | `cnaes_secundarios` |
| `UF` | `uf` |
| `CEP` | `cep` (só no staging) |
| demais | iguais |
