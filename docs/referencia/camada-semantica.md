# Camada semântica (dbt + MetricFlow)

> **Para quem:** quem consulta ou estende as métricas (`mf query`, BI, agente) · **Quando ler:** para saber quais
> entidades, dimensões, métricas e consultas salvas existem, como usá-las e quais os limites.

> **Adição** ao MVP original ([ADR-0018](../adr/0018-camada-semantica-metricflow.md)). A camada semântica descreve, em YAML
> e no padrão do dbt/MetricFlow, **o que** se mede no modelo estrela: entidades, dimensões, métricas e consultas
> salvas. Qualquer ferramenta compatível calcula as métricas do mesmo jeito, sem reescrever a regra em DAX,
> SQL ou planilha.

Este documento é a referência **técnica**: arquivos, entidades, métricas, consultas salvas, testes e limites. **O que
os dados significam** (empresa × estabelecimento, porte, MEI, situação cadastral, ciclo de vida e glossário) está
em [conceitos de negócio](../conceitos.md): leia-o antes de usar as métricas. As perguntas frequentes com `mf query`
estão na [seção 5](#perguntas-frequentes), e a ontologia, na [referência da ontologia](ontologia/README.md). Até a v1.4 os dois formavam um documento só (Partes A e B); a correspondência das seções está em
[reorganização da v1.5.0](../historico/reorganizacao-v1.5.0.md).

## 1. Onde está e em qual padrão

Usamos o **padrão novo** de YAML da camada semântica, suportado pelo dbt-core 1.12+ e pelo dbt v2 (Fusion).
As anotações ficam **junto do modelo**, no mesmo YAML que já documenta colunas e testes:

| Arquivo | O que define |
|---|---|
| [`transform/models/marts/core/_core__models.yml`](../../transform/models/marts/core/_core__models.yml) | modelos semânticos das dimensões e das duas fatos, métricas do resumo mensal e da fato detalhada, *time spine* (`dim_data`) |
| [`transform/models/marts/analytics/_analytics__models.yml`](../../transform/models/marts/analytics/_analytics__models.yml) | modelos semânticos e métricas de `mart_sobrevivencia_coorte` e de `mart_emprego_setor_municipio` (incremento `enriquecimento_ibge`) |
| [`transform/models/marts/_marts__saved_queries.yml`](../../transform/models/marts/_marts__saved_queries.yml) | consultas salvas (*saved queries*) |
| [`docs/referencia/ontologia/rfb_cnpj.ttl`](ontologia/rfb_cnpj.ttl) | ontologia: conceitos de negócio mapeados para entidades, dimensões e métricas ([referência da ontologia](ontologia/README.md)) |

Elementos do padrão usados aqui:

| Chave (no modelo) | Função |
|---|---|
| `semantic_model: { enabled: true }` | transforma o modelo dbt num modelo semântico |
| `entity:` (na coluna) | chave de junção: `primary` (o grão do modelo) ou `foreign` (aponta para outra entidade); aceita `description` |
| `dimension:` (na coluna) | atributo para agrupar e filtrar (`categorical` ou `time`) |
| `derived_semantics.dimensions` | dimensão calculada por expressão SQL (ex.: data a partir de `sk_data`) |
| `agg_time_dimension` | dimensão de tempo padrão das métricas do modelo (vira `metric_time` nas consultas) |
| `primary_entity` | entidade do modelo quando o grão é composto (sem coluna de chave única) |
| `metrics:` | métricas `simple`, `ratio` e `derived` do próprio modelo |
| `time_spine:` | calendário diário que o MetricFlow usa para deslocamentos e janelas |

O detalhe dos campos de cada tabela (tipo, grão, chaves, domínio, origem, e as entidades, dimensões e métricas
desta camada em cada modelo) está no [dicionário de dados](dicionario-dados.md), gerado do manifesto do dbt
(`make dicionario`, [ADR-0019](../adr/0019-dicionario-de-dados.md)). Os comandos `mf query` testados de cada conceito,
com a resposta nas fixtures, estão em [`golden_queries/semantica.yml`](golden_queries/semantica.yml), e o
[guia de consulta em linguagem natural](../uso/consulta-agente.md) ensina um agente a escolher entre a
semântica e o SQL ([ADR-0023](../adr/0023-golden-queries-e-guia-para-agente.md)).

## 2. Entidades e junções

```mermaid
erDiagram
    resumo_mensal }o--|| municipio : sk_municipio
    resumo_mensal }o--|| cnae : sk_cnae
    resumo_mensal }o--|| porte : sk_porte
    resumo_mensal }o--|| situacao_cadastral : sk_situacao_cadastral
    estabelecimento }o--|| municipio : sk_municipio
    estabelecimento }o--|| cnae : sk_cnae
    estabelecimento }o--|| natureza_juridica : sk_natureza_juridica
    estabelecimento }o--|| porte : sk_porte
    estabelecimento }o--|| situacao_cadastral : sk_situacao_cadastral
    coorte_sobrevivencia }o--|| cnae : sk_cnae
    coorte_sobrevivencia }o--|| porte : sk_porte
    emprego_setor_municipio }o--|| municipio : sk_municipio
```

| Modelo semântico | Entidade principal | Dimensões |
|---|---|---|
| `dim_municipio` | `municipio` (`sk_municipio`) | `nome_municipio`, `sigla_uf`, `nome_uf`, `nome_regiao`, meso/microrregião, regiões intermediária e imediata, `id_municipio_ibge`, `nome_regiao_metropolitana` (incremento enriquecimento BD); `renda_per_capita_media_2022`, `renda_per_capita_mediana_2022`, `regic_hierarquia`, `regic_hierarquia_codigo`, `regic_arranjo_populacional`, `regic_regiao_influencia`, `nome_municipio_polo_compras`, `pct_compras_no_polo` (incremento enriquecimento IBGE) |
| `dim_cnae` | `cnae` (`sk_cnae`) | códigos e descrições de seção, divisão, grupo, classe e subclasse |
| `dim_natureza_juridica` | `natureza_juridica` | código e descrição |
| `dim_porte` | `porte` | `codigo_porte`, `rotulo_porte` |
| `dim_situacao_cadastral` | `situacao_cadastral` | `codigo_situacao_cadastral`, `rotulo_situacao_cadastral` |
| `fct_resumo_mensal` | `resumo_mensal` (grão composto) | tempo `mes` (mensal), `opcao_mei` |
| `fct_estabelecimentos` | `estabelecimento` (`cnpj_completo`) | tempo `data_inicio_atividade` e `data_situacao` (diárias), `opcao_simples`, `opcao_mei`, `eh_matriz`, `eh_ativa` |
| `mart_sobrevivencia_coorte` | `coorte_sobrevivencia` (grão composto) | tempo `coorte` (anual), `uf` |
| `mart_emprego_setor_municipio` | `emprego_setor_municipio` (grão composto: município × classe CNAE) | tempo `mes_rfb` (mensal, o mês do gold), `classe_cnae`, `descricao_classe`, `ano_cempre`, `tem_sigilo`, `uf` |

Nas consultas, a dimensão de outro modelo é acessada pela entidade: `municipio__sigla_uf`, `cnae__descricao_secao`,
`porte__rotulo_porte`. O membro `-1` (NÃO INFORMADO) de cada dimensão aparece como um valor normal. Não existe
entidade "empresa": ver [conceitos](../conceitos.md#empresa--estabelecimento).

## 3. Métricas

As métricas do resumo mensal são as **mesmas medidas DAX** do [guia Power BI](../uso/power-bi.md#3-medidas-dax-sugeridas),
agora definidas uma vez e fora da ferramenta de BI. A equivalência vale **no grão mensal**: num visual por ano (ou
sem mês), o DAX `SUM` soma os meses, e a métrica usa o último mês (fotografia, abaixo). Para comparar um número do
painel com o `mf`, filtre um mês nos dois.

| Métrica | Tipo | Definição | Medida DAX equivalente |
|---|---|---|---|
| `qtd_estabelecimentos` | simple (sum, fotografia) | `sum(qtd_estabelecimentos)` | Qtd Estabelecimentos |
| `qtd_ativos` | simple (sum, fotografia) | `sum(qtd_ativos)` | Qtd Ativos |
| `qtd_ativos_mei` | simple (sum, fotografia) | `sum(qtd_ativos)` com filtro `opcao_mei` | Qtd Ativos MEI |
| `qtd_matrizes` | simple (sum, fotografia) | `sum(qtd_matrizes)` | Qtd Matrizes |
| `capital_social_total` | simple (sum, fotografia) | `sum(soma_capital_social_matrizes)` | Capital Social Total (R$) |
| `soma_idade_anos_ativos` | simple (sum, fotografia) | `sum(soma_idade_anos)` (numerador) | — |
| `pct_ativos` | ratio | `qtd_ativos / qtd_estabelecimentos` | % Ativos |
| `idade_media_anos` | ratio | `soma_idade_anos_ativos / qtd_ativos` | Idade Média (anos) |
| `capital_social_medio` | ratio | `capital_social_total / qtd_matrizes` | Capital Social Médio (R$) |
| `pct_mei_entre_ativos` | ratio | `qtd_ativos_mei / qtd_ativos` | % MEI entre Ativos |
| `qtd_ativos_mes_anterior` | derived | `qtd_ativos` com `offset_window: 1 month` | Qtd Ativos Mês Anterior |
| `variacao_mensal_ativos` | derived | `qtd_ativos − mês anterior` | Variação Mensal de Ativos |
| `variacao_mensal_ativos_pct` | derived | `(qtd_ativos − anterior) / anterior` | Variação Mensal de Ativos (%) |
| `aberturas` | simple (count) | estabelecimentos pela **data de início**, só com data válida | — (regra de `mart_dinamica_mercado`) |
| `encerramentos` | simple (count) | **não ativos** (`not eh_ativa`) pela **data da situação** (`agg_time_dimension` próprio), só com data válida | — (regra de `mart_dinamica_mercado`) |
| `baixas` | simple (count) | só **BAIXADA** pela **data da situação**, só com data válida | — |
| `saldo_aberturas_encerramentos` | derived | `aberturas − encerramentos` (lado sem evento conta 0) | — (`saldo` de `mart_dinamica_mercado`) |
| `elegiveis_{1,3,5}a`, `sobreviventes_{1,3,5}a` | simple (sum) | colunas de `mart_sobrevivencia_coorte` | — |
| `taxa_sobrevivencia_{1,3,5}a` | ratio | `sobreviventes / elegíveis` (soma os estratos antes de dividir) | Taxa de Sobrevivência 3a |
| `unidades_locais_cempre` | simple (sum) | unidades locais do CEMPRE (`ano_cempre`), por município × classe | — |
| `pessoal_ocupado_cempre` | simple (sum) | pessoal ocupado do CEMPRE; células com sigilo ficam fora (subestima) | — |
| `ativos_rfb` | simple (sum) | ativos da RFB (mês do gold) da classe, nos pares do mart CEMPRE × RFB | — |

**Fotografia mensal (`non_additive_dimension`).** O resumo mensal é uma fotografia: somar `qtd_ativos` de vários
meses contaria o mesmo estabelecimento várias vezes (é o cuidado "Não some meses" do guia Power BI). As métricas
de contagem do resumo declaram `non_additive_dimension: { name: mes, window_agg: max }`. Num grão maior que o mês
(ano, ou sem tempo), o MetricFlow usa **o último mês do período em que o recorte filtrado tem linhas**, em vez da
soma. Nas fixtures do CI, `qtd_ativos` por ano dá 11 (o valor de 2026-09), não 21 (08 + 09). Testes de
integração impedem a regressão.

**Limitação: o último mês é escolhido depois do filtro.** O MetricFlow calcula o `MAX(mes)` sobre as linhas que
sobram do `--where`. Se o filtro esvazia o último mês, a consulta devolve o mês anterior com linhas, e não zero. O
MetricFlow não oferece um `MAX` fora do filtro. Para estoque atual, agrupe por `metric_time__month` ou filtre o
mês, e prefira `qtd_ativos` a `qtd_estabelecimentos` com filtro `ATIVA` (exemplo na
[perguntas frequentes](#perguntas-frequentes)).

**Ratios somam antes de dividir.** `idade_media_anos` e `taxa_sobrevivencia_3a` dividem somas, nunca tiram média
de médias. Por isso a taxa de um estado ou de um ano é ponderada pelo número de estabelecimentos.

## 4. Consultas salvas

| Saved query | Pergunta |
|---|---|
| `serie_mensal_ativos_por_uf` | ativos, % de ativos e idade média por mês e UF |
| `estudo_caso_fundao_tintas` | pergunta-guia do MVP: lojas de tintas (CNAE 4741500) em Fundão/ES por mês e porte |
| `dinamica_anual_por_secao_cnae` | aberturas, encerramentos e saldo por ano e seção CNAE. O último ano é parcial, e os encerramentos incluem inaptidões em lote (veja a [ciclo de vida](../conceitos.md#3-ciclo-de-vida)) |
| `sobrevivencia_por_coorte_e_porte` | taxas de sobrevivência a 1, 3 e 5 anos por coorte e porte |
| `polo_compras_concorrencia_caso` | ativos de lojas de tintas por mês e município do ES, com o polo de compras e o % dos deslocamentos que vão a ele, a hierarquia e a renda (incremento enriquecimento IBGE) |

## 5. Como usar

O CLI do MetricFlow (`mf`, pacote `dbt-metricflow`) vem nas dependências de desenvolvimento (`make setup`). Ele lê o
projeto dbt de `transform/` e consulta o DuckDB de `RAIZ_DADOS` (o mesmo `warehouse.duckdb` do pipeline).

```bash
make semantica                      # parse + mf validate-configs (inclusive contra o warehouse) + lista de métricas

cd transform
uv run mf list metrics              # métricas e dimensões disponíveis
uv run mf query --saved-query estudo_caso_fundao_tintas
uv run mf query --metrics qtd_ativos,pct_ativos --group-by metric_time__month,municipio__sigla_uf \
  --where "{{ Dimension('municipio__nome_regiao') }} = 'Sudeste'"
uv run mf query --metrics idade_media_anos --group-by metric_time__month --explain   # mostra o SQL gerado
uv run mf query --metrics aberturas,encerramentos --group-by metric_time__year --csv dinamica.csv
```

Resultado do estudo de caso nas fixtures do CI, igual ao do notebook 4 em 2026-09 (1 loja ativa, MICRO, 3,9 anos):

```text
metric_time__month    porte__rotulo_porte    qtd_estabelecimentos    qtd_ativos    idade_media_anos
2026-09-01            MICRO                                     2             1                 3.9
```

Outros consumidores:

- **Documento OSI.** O `dbt parse` grava `transform/target/osi_document.json`, a camada semântica no formato
  aberto *Open Semantic Interchange*, para ferramentas que o leem.
- **Power BI.** Continua com as medidas DAX do guia: o Power BI não lê MetricFlow diretamente. A tabela da
  [seção 3](#3-métricas) é o dicionário entre as duas. Use `mf query --csv` ou `--explain` para conferir um número do
  painel **num mês**: num total por ano, o `SUM` do DAX soma os meses e a métrica não.
- **dbt Semantic Layer (dbt platform).** O mesmo YAML serve, se um dia o projeto for para a plataforma.

### Perguntas frequentes

Os exemplos rodam em `transform/`, com `RAIZ_DADOS` apontando para os dados (no CI, `.tmp/ci/dados`). As saídas
e os números citados vêm das **fixtures do `make ci`** (meses 2026-08 e 2026-09), não do cadastro real. Os poucos
números que ficam na prosa são conferidos por `test_numeros_citados_na_doc_batem_com_as_fixtures`; para os
demais, veja a saída do comando.

**Quantos MEI ativos há em cada UF?**

```bash
uv run mf query --metrics qtd_ativos_mei,qtd_ativos,pct_mei_entre_ativos --group-by metric_time__month,municipio__sigla_uf
uv run mf query --metrics qtd_ativos_mei --group-by metric_time__month --where "{{ Dimension('municipio__sigla_uf') }} = 'ES'"
```

Recorte sem MEI sai vazio, não zero. Lembre que `qtd_ativos_mei` conta estabelecimentos (há MEI com filial no dado
real, veja [Simples Nacional e MEI](../conceitos.md#simples-nacional-e-mei)).

**Quantas empresas há, e não estabelecimentos?**

```bash
uv run mf query --metrics qtd_matrizes,qtd_estabelecimentos --group-by metric_time__month
uv run mf query --metrics qtd_matrizes,qtd_estabelecimentos --group-by metric_time__month --where "{{ Dimension('situacao_cadastral__rotulo_situacao_cadastral') }} = 'ATIVA'"
```

Onde há filial, a saída tem mais estabelecimentos que matrizes. Com o filtro de ATIVA, a situação filtrada é a de
cada estabelecimento: conta a matriz ativa, não a empresa como um todo.

**Por que não posso somar os meses?**

Cada mês é uma fotografia do cadastro inteiro. O mesmo estabelecimento ativo aparece em todos os meses em que segue
ativo; somar 2026-08 (10) e 2026-09 (11) daria 21 ativos que não existem. As métricas de contagem do resumo
declaram `non_additive_dimension`: num período maior que o mês, vale o **último mês em que o recorte filtrado tem
linhas** (veja a próxima pergunta).

```bash
uv run mf query --metrics qtd_ativos --group-by metric_time__month
uv run mf query --metrics qtd_ativos --group-by metric_time__year
```

A segunda consulta devolve 11 para 2026 (o valor de 2026-09), não 21.

**Quantos há agora num recorte filtrado?**

Cuidado com o filtro. O MetricFlow escolhe o "último mês" **depois** de aplicar o `--where`: se o filtro não deixa
nenhuma linha no último mês, ele usa o mês mais recente que sobrou, e devolve uma fotografia velha em vez de zero
ou vazio. Vale para a consulta por ano e para a consulta sem tempo. Nas fixtures, uma filial de Água Branca/PB
estava SUSPENSA em 2026-08 e foi baixada antes do extrato de 2026-09:

```bash
uv run mf query --metrics qtd_estabelecimentos --group-by metric_time__year --where "{{ Dimension('municipio__sigla_uf') }} = 'PB' and {{ Dimension('situacao_cadastral__rotulo_situacao_cadastral') }} = 'SUSPENSA'"
```

A consulta devolve 1 para 2026 (a fotografia de 2026-08), embora em 2026-09 não haja nenhuma suspensa na PB.
Para o estoque atual:

- agrupe por `metric_time__month`, ou filtre `metric_time` no mês desejado (vazio quer dizer nenhum):

  ```bash
  uv run mf query --metrics qtd_estabelecimentos --group-by metric_time__month --where "{{ Dimension('municipio__sigla_uf') }} = 'PB' and {{ Dimension('situacao_cadastral__rotulo_situacao_cadastral') }} = 'SUSPENSA' and {{ TimeDimension('metric_time', 'month') }} = '2026-09-01'"
  ```

- não filtre a situação: agrupe por ela, ou use `qtd_ativos` em vez de `qtd_estabelecimentos` com filtro `ATIVA`.
  O resumo guarda as linhas das outras situações, então o recorte continua com linhas no último mês e a
  fotografia sai certa:

  ```bash
  uv run mf query --metrics qtd_estabelecimentos,qtd_ativos --group-by metric_time__year,situacao_cadastral__rotulo_situacao_cadastral --where "{{ Dimension('municipio__sigla_uf') }} = 'PB'"
  ```

O teste `test_fotografia_com_filtro_vale_o_ultimo_mes_em_que_o_recorte_tem_linhas` documenta esse comportamento.
No dado real ele aparece a partir do segundo mês da série.

**Como os estabelecimentos se distribuem por situação cadastral?**

```bash
uv run mf query --metrics qtd_estabelecimentos --group-by metric_time__month,situacao_cadastral__rotulo_situacao_cadastral
```

Em 2026-09, a saída mostra as situações ATIVA, INAPTA e BAIXADA; em 2026-08, também SUSPENSA.

**Qual a idade média dos ativos por porte num mês?**

```bash
uv run mf query --metrics qtd_ativos,idade_media_anos --group-by porte__rotulo_porte --where "{{ TimeDimension('metric_time', 'month') }} = '2026-09-01'"
```

Lembre que o porte é declarado e que `N/A` (código 00) e `NÃO INFORMADO` (membro `-1`) são coisas diferentes.

**Os encerramentos são só baixas?**

Não. Pela regra do projeto, encerramento é todo estabelecimento não ativo com data da situação válida. Para só
as baixas, use `baixas`:

```bash
uv run mf query --metrics encerramentos --group-by metric_time__year,situacao_cadastral__rotulo_situacao_cadastral
uv run mf query --metrics encerramentos,baixas --group-by metric_time__year
```

Nas fixtures, há encerramentos BAIXADA e INAPTA; o baixado sem data da situação não aparece. No dado real, a
diferença é grande no ano de um lote de inaptidão (veja a [ciclo de vida](../conceitos.md#lotes-de-inaptidão-e-período-parcial)).

**Quantas aberturas houve por natureza jurídica, e por matriz ou filial?**

```bash
uv run mf query --metrics aberturas --group-by natureza_juridica__descricao_natureza_juridica
uv run mf query --metrics aberturas,encerramentos --group-by estabelecimento__eh_matriz
```

Natureza jurídica só existe na fato detalhada: combine-a com `aberturas` e `encerramentos`, não com as métricas do
resumo mensal.

**Quantos ativos há por seção da CNAE?**

```bash
uv run mf query --metrics qtd_ativos --group-by metric_time__month,cnae__descricao_secao --where "{{ TimeDimension('metric_time', 'month') }} = '2026-09-01'"
```

O recorte é pelo CNAE **principal**. O membro `NÃO INFORMADO` reúne CNAEs sem par na Base dos Dados.

**Quantas pessoas trabalham num setor, e quantos CNPJs ativos ele tem?**

```bash
uv run mf query --metrics unidades_locais_cempre,pessoal_ocupado_cempre,ativos_rfb --group-by emprego_setor_municipio__classe_cnae --where "{{ Dimension('municipio__nome_municipio') }} = 'Serra'"
```

As unidades e o pessoal são do CEMPRE (`ano_cempre`), os ativos da RFB (mês do gold). Sem MEI no CEMPRE, compare
com `ativos_rfb_sem_mei` em `mart_emprego_setor_municipio`; com sigilo, o pessoal da célula fica fora da soma. Mais
exemplos, com o dado real, nos [cenários de uso](../uso/cenarios.md).

## 6. Garantias (testes)

- `tests/integration/test_camada_semantica.py`:
  - `mf validate-configs` sem erros, inclusive contra o warehouse;
  - as 10 métricas simples e ratio do resumo iguais ao SQL direto no gold, no mês, no ano e sem tempo (no ano e
    sem tempo, a fotografia do último mês, também nos numeradores dos ratios);
  - fotografia sem soma de meses, e a fixture discriminando o último mês da soma em todas as contagens;
  - fotografia com filtro: o último mês em que o recorte tem linhas (a limitação da [seção 3](#3-métricas));
  - `qtd_ativos_mes_anterior`, `variacao_mensal_ativos` e `variacao_mensal_ativos_pct` com o mês anterior;
  - estudo de caso de Fundão e as *saved queries* `serie_mensal_ativos_por_uf` e
    `sobrevivencia_por_coorte_e_porte`, iguais ao SQL;
  - aberturas, encerramentos e saldo iguais a `mart_dinamica_mercado` por ano e por ano × seção CNAE;
  - `baixas` igual às baixadas com data válida, menor que os encerramentos;
  - elegíveis, sobreviventes e taxas a 1, 3 e 5 anos iguais ao mart, somando os estratos;
  - os números citados nesta doc e em [conceitos](../conceitos.md) iguais aos das fixtures.
- `tests/integration/test_enriquecimento_ibge.py` (incremento `enriquecimento_ibge`): o mart CEMPRE × RFB, o polo de
  compras e as analyses dos [cenários de uso](../uso/cenarios.md) nas fixtures, e o pipeline sem `ibge/`.
- `tests/integration/test_escopo_meta.py`: modelos semânticos, métricas e *saved queries* com `meta.escopo`
  (e tag, nas *saved queries*).
- `tests/integration/test_ontologia.py`: a ontologia parseia, tem rótulos em português, cobre a camada nos dois
  sentidos (todo nome anotado existe nos manifestos; toda entidade e toda métrica tem conceito) e põe cada métrica
  num conceito que anota o modelo semântico dela (afinidade).
- `tests/integration/test_doc_semantica.py`: a parte estática de `scripts/verificar_doc_semantica.py`
  (identificadores, links e âncoras desta doc e de [conceitos](../conceitos.md)). Os exemplos `mf` rodam só quando o script é chamado com a opção
  de executar os exemplos, fora do CI.
- Mutações verificadas (todas reprovadas pelos testes):
  - tirar o `non_additive_dimension` de uma contagem, ou do numerador de um ratio (`soma_idade_anos_ativos`,
    `capital_social_total`);
  - deslocar 2 meses no lugar de 1, ou dividir a variação % pelo mês corrente;
  - tirar o filtro de MEI de `qtd_ativos_mei`; trocar o denominador de `pct_ativos`; trocar o numerador da taxa de
    1 ano pelo de 3 anos;
  - trocar o filtro de `baixas` por não ativos; `window_agg: min` na fotografia;
  - remover o `meta.escopo` de uma métrica;
  - tirar o mapeamento de uma métrica da ontologia, mapeá-la num conceito de outro modelo ou mapear um conceito
    para um nome inexistente.

## 7. Limites e cuidados

- **Densidades por população ou domicílio** (ativos por 10 mil hab., por mil domicílios) **não** viraram métricas: a
  população é atributo da dimensão e precisaria ser somada uma vez por município, o que o MetricFlow não faz numa
  métrica de outra tabela. Use `mart_concorrencia_area_mercado` (já calcula `ativos_por_mil_domicilios`) ou o DAX do
  guia Power BI.
- **CNAEs secundários** (bridge muitos-para-muitos), **vizinhança** e **destinos de compra**
  (`bridge_municipio_destino_compras`) ficam fora da camada semântica: o MetricFlow não modela pontes
  muitos-para-muitos. O polo de compras entra como atributo de `dim_municipio`.
- **CEMPRE × RFB são de anos diferentes** e o CEMPRE não tem MEI nem os valores sigilosos: `pessoal_ocupado_cempre`
  somado subestima, e `ativos_rfb` não é comparável a `unidades_locais_cempre` sem tirar o MEI
  (`ativos_rfb_sem_mei`, coluna do mart). Renda (2022, nominal), REGIC (2018) e VA (`ano_va`) também têm anos
  próprios ([cenários de uso](../uso/cenarios.md#limitações-comuns)).
- `aberturas`, `encerramentos` e o saldo seguem a regra de `mart_dinamica_mercado`: abertura pela data de início;
  encerramento = estabelecimento **não ativo** (baixado, suspenso, inapto ou nulo, não só baixado) pela data da
  situação; data ausente ou inválida (`-1`/`-2`) não gera evento. Por ano, e por ano × qualquer dimensão do
  estabelecimento, os números são os do mart. Como o mart, olham **só o extrato corrente**: estabelecimentos que
  sumiram do cadastro não entram, e um inativo reativado deixa de contar como encerramento.
  Num período com eventos só de um lado, a métrica do outro lado sai vazia (nula) e o saldo a trata como 0
  (`coalesce` na expressão: o dbt-core 1.12.5 descarta `fill_nulls_with` nas métricas do YAML novo).
- **Inaptidões em lote e ano parcial** distorcem `encerramentos` e o saldo de um ano: no dado real de 2026-09, 44 %
  dos encerramentos de 2026 são INAPTA, e 2026 vai só até 12/09. Use `baixas` ou a quebra por situação, e compare
  períodos completos ([ciclo de vida](../conceitos.md#3-ciclo-de-vida)).
- **Fotografia com filtro:** o último mês é escolhido depois do `--where` ([seção 3](#3-métricas)).
- **Datas sentinela no *time spine*.** O `dim_data` tem 1899-12-30 e 1899-12-31 (membros `-2` e `-1`), e elas
  aparecem em consultas de dimensão pura (`mf query --group-by metric_time__day`). Nenhuma métrica é afetada: as do
  resumo começam em 2026, e `aberturas`, `encerramentos` e `baixas` filtram as datas nulas. Uma métrica futura com
  `join_to_timespine` ou `cumulative` veria esses dois dias; se incomodar, crie um *time spine* próprio, sem os
  membros `-1` e `-2`.
- **Bug do partial parse (dbt-core 1.12.5).** Depois de editar um YAML com métricas, o próximo comando dbt pode falhar
  com `dbt found two metrics with the name ...`. Rode `dbt parse --no-partial-parse` uma vez. Os alvos `make ci`,
  `make pipeline`, `make atualizar` e `make semantica` já fazem isso.
- **dbt v2 (Fusion).** O YAML desta camada é aceito pelo dbt v2. Por compatibilidade:
  - os `input_metrics` são sempre objetos (`{ name: ... }`);
  - as *saved queries* não usam `order_by`.

  A migração do motor continua adiada pelo ADR-0017.

## 8. Como estender

1. Métrica nova sobre um modelo que já é semântico: acrescente-a em `metrics:` do modelo, com `description`, `label`,
   `config: { meta: { escopo: adicao } }`. Contagens do resumo mensal levam o `non_additive_dimension`.
2. Dimensão nova: marque a coluna com `dimension: categorical`. Para tempo, use `dimension: time` + `granularity`,
   ou uma `derived_semantics.dimensions` com `expr`.
3. Modelo novo: `semantic_model: { enabled: true, config: { meta: { escopo: adicao } } }`, uma entidade
   `primary` (ou `primary_entity`), `foreign` para as dimensões e `agg_time_dimension`.
4. Mapeie a métrica ou a entidade nova num conceito de [`docs/referencia/ontologia/rfb_cnpj.ttl`](ontologia/rfb_cnpj.ttl)
   (`rfbo:metricaDbt`, `rfbo:entidadeSemantica`) e na tabela "Onde cada conceito está no projeto" da [referência da ontologia](ontologia/README.md#onde-cada-conceito-está-no-projeto): o `test_ontologia.py` falha
   sem isso.
5. Rode `make semantica` e acrescente um caso em `test_camada_semantica.py` que compare a métrica com o SQL direto.
