# ADR-0019 — Dicionário de dados gerado, conferido no CI, com o campo do leiaute em `meta`

**Contexto.** Pedido do usuário (2026-10-13): acrescentar o detalhe dos campos de cada tabela disponível na
base. As descrições já existiam nos YAMLs, mas espalhadas por vários YAMLs, sem tipo, grão, chaves,
localização nem a ligação com o leiaute oficial da RFB (`cnpj-metadados.pdf`). Faltava também descrever as
colunas técnicas da ingestão e as colunas do raw da Base dos Dados que o projeto não usa.

**Decisão.**
- **Dicionário gerado**: `docs/DICIONARIO_DADOS.md` sai de `scripts/gerar_dicionario_dados.py`, a partir do
  `manifest.json` e do `catalog.json` do dbt (`make dicionario`, depois do `make ci`). Cobre fontes raw,
  seeds, staging, intermediate, gold e observabilidade. Para cada tabela traz descrição, grão, chaves
  (testes `unique`, `unique_combination_of_columns` e `relationships`, mais as entidades semânticas),
  materialização, localização (gold relativo a `RAIZ_DADOS`), escopo, incremento, contrato e camada
  semântica; para cada coluna, tipo, descrição, nulidade, domínio, origem e observações (dados pessoais,
  chaves `-1`/`-2`, sentinelas).
- **Conferido no CI**: o teste de integração `test_dicionario_dados.py` roda o gerador em modo `--verificar`
  (gera em memória e compara com o arquivo versionado), como o catálogo de qualidade faz com
  `docs/QUALIDADE_DADOS.md`. Também confere links, âncoras e que todo modelo, seed, fonte e coluna real
  tem entrada, e que nenhum identificador de tabela citado deixou de existir.
- **Nulidade sem chute**: "pode ser nulo?" vem do teste `not_null`. Sem o teste, o dicionário escreve
  *não testado*, nunca "sim".
- **Campo do leiaute em `meta`**: cada coluna das fontes RFB declara
  `config.meta.campo_leiaute` com o nome exato do campo no leiaute oficial; as fontes da Base dos Dados
  declaram `config.meta.coluna_bigquery` (e `meta.tabela_bigquery` na tabela). Campo que não consta do
  leiaute oficial fica sem o `meta` (a tabela `motivos` e as colunas técnicas). O grão de cada tabela fica em
  `meta.grao`.
- **Descrição em 100 % das colunas reais de fontes e do gold**: o teste de cobertura (RBP-09) passa a exigir
  100 % nessas camadas, conferindo as colunas do Parquet raw e do catálogo, e mantém ≥ 98 % no resto.
  As fontes declaram também as colunas técnicas da ingestão e o `data_type` de cada coluna.

**Consequências.** Mudar descrição, teste, contrato ou `meta` num YAML obriga a regenerar o dicionário (o CI
acusa). O dicionário não substitui a [camada semântica](../CAMADA_SEMANTICA.md) (conceitos de negócio,
métricas) nem o catálogo de [qualidade](../QUALIDADE_DADOS.md) (todos os testes): aponta para eles. O
`catalog.json` depende de um warehouse construído, então o gerador roda depois do `make ci`.
