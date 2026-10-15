# ADR-0019 — Dicionário de dados gerado, conferido no CI, com o campo do leiaute em `meta`

**Contexto.** Pedido do usuário (2026-10-13): acrescentar o detalhe dos campos de cada tabela disponível na
base. As descrições já existiam nos YAMLs, mas espalhadas por vários YAMLs, sem tipo, grão, chaves,
localização nem a ligação com o leiaute oficial da RFB (`cnpj-metadados.pdf`). Faltava também descrever as
colunas técnicas da ingestão e as colunas do raw da Base dos Dados que o projeto não usa.

**Decisão.**
- **Dicionário gerado**: `docs/referencia/dicionario-dados.md` sai de `scripts/gerar_dicionario_dados.py`, a partir do
  `manifest.json` e do `catalog.json` do dbt (`make dicionario`, depois do `make ci`). Cobre fontes raw,
  seeds, staging, intermediate, gold e observabilidade. Para cada tabela traz descrição, grão, chaves
  (testes `unique`, `unique_combination_of_columns` e `relationships`, mais as entidades semânticas),
  materialização, localização (gold relativo a `RAIZ_DADOS`), escopo, incremento, contrato e camada
  semântica; para cada coluna, tipo, descrição, nulidade, domínio, origem e observações (dados pessoais,
  chaves `-1`/`-2`, sentinelas).
- **Conferido no CI**: o teste de integração `test_dicionario_dados.py` roda o gerador em modo `--verificar`
  (gera em memória e compara com o arquivo versionado), como o catálogo de qualidade faz com
  `docs/referencia/qualidade-dados.md`. Isso prova que o arquivo está **em dia**, não que está **certo**; por isso o teste
  confere também o conteúdo que o gerador não infere sozinho:
  - links e âncoras resolvem, e nenhum identificador de tabela citado deixou de existir;
  - todo modelo, seed e fonte tem seção, e toda coluna real (do catálogo ou do Parquet raw, inclusive das
    fontes) tem linha;
  - toda coluna de dado das fontes RFB, salvo `motivos`, declara `meta.campo_leiaute`, na ordem posicional de
    `esquemas.py` e conforme a lista do leiaute versionada no teste (conferida contra o PDF);
  - `meta.tabela_bigquery` é o par `dataset.tabela` de `esquemas.py` e toda `meta.coluna_bigquery` existe no
    Parquet raw (hoje é igual ao nome da coluna: o `meta` afirma "existe no BigQuery com este nome", não traz
    tipo nem descrição do lado da Base dos Dados);
  - toda coluna citada entre crases em `meta.grao` existe na própria tabela.
  O teste unitário `test_gerar_dicionario_dados.py` fixa as regras do gerador (nulidade, `warn`, chaves,
  FKs, linhagem, ordem do manifesto) sobre um manifesto mínimo.
- **Nulidade, domínio e chaves sem chute**: "pode ser nulo?" vem do teste `not_null`. Sem o teste, o dicionário
  escreve *não testado*, nunca "sim". Com o teste em `severity: warn`, escreve *em geral não*, porque o teste só
  avisa. Chave única, `relationships` e `accepted_*` em `warn` levam a marca `(warn)`. A chave primária é a
  coluna (ou combinação) com teste de unicidade que está em `meta.grao`; sem ela, a linha diz *não testada* e o
  grão aparece como *declarado, não testado*. As FKs dizem se são *testadas*, *semânticas* ou *declaradas*
  (`meta.fk_declarada`, sem teste).
- **Linhagem**: cada tabela traz **Lê de** e **Usada por** (dependências do manifesto, sem testes), e as colunas
  do gold que não são cópia direta trazem a origem em `meta.linhagem` (ou em "Linhagem:" na descrição). Um
  diagrama `erDiagram` das FKs do gold abre a navegação. As seeds mostram as linhas, e as colunas das
  dimensões semeadas citam os valores da seed (`meta.dominio_seed`). `meta.membro_desconhecido: false` marca a
  chave que **não** recebe `-1` (a linha sem par é descartada).
- **Campo do leiaute em `meta`**: cada coluna das fontes RFB declara
  `config.meta.campo_leiaute` com o nome exato do campo no leiaute oficial; as fontes da Base dos Dados
  declaram `config.meta.coluna_bigquery` (e `meta.tabela_bigquery` na tabela). Campo que não consta do
  leiaute oficial fica sem o `meta` (a tabela `motivos` e as colunas técnicas). O grão de cada tabela fica em
  `meta.grao`.
- **Descrição em 100 % das colunas reais de fontes e do gold**: o teste de cobertura (RBP-09) passa a exigir
  100 % nessas camadas, conferindo as colunas do Parquet raw e do catálogo, e mantém ≥ 98 % no resto.
  As fontes declaram também as colunas técnicas da ingestão e o `data_type` de cada coluna.

**Consequências.** Mudar descrição, teste, contrato ou `meta` num YAML (ou a ordem das colunas das fontes) obriga a regenerar o dicionário (o CI
acusa). O dicionário não substitui a [camada semântica](../referencia/camada-semantica.md) (conceitos de negócio,
métricas) nem o catálogo de [qualidade](../referencia/qualidade-dados.md) (todos os testes): aponta para eles. O
`catalog.json` depende de um warehouse construído, então o gerador roda depois do `make ci`.
