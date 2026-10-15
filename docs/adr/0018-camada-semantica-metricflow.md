# ADR-0018 — Camada semântica no padrão dbt/MetricFlow (YAML)

**Contexto.** Pedido do usuário (2026-10-09): documentar a camada semântica no padrão dbt/MetricFlow, em YAML.
As regras de cálculo das métricas viviam só como medidas DAX no [guia Power BI](../uso/power-bi.md) e em SQL nos marts.
O cuidado "não some meses" do resumo mensal, por exemplo, dependia de quem escrevia o painel lembrar dele.

**Decisão.**
- **Padrão novo do YAML** (dbt-core 1.12+ e dbt v2): anotações junto do modelo (`semantic_model`, `entity` e
  `dimension` nas colunas, `derived_semantics`, `agg_time_dimension`, `metrics`). O formato antigo
  (`semantic_models:` + `measures`) não é usado: é o legado, e o dbt v2 trabalha no novo.
- **Escopo**:
  - modelos semânticos das 5 dimensões, das duas fatos (`fct_resumo_mensal` e `fct_estabelecimentos`) e de
    `mart_sobrevivencia_coorte`;
  - 26 métricas: as medidas DAX do guia, mais aberturas, encerramentos, baixas e as taxas de sobrevivência;
  - 4 *saved queries*, entre elas a pergunta-guia de Fundão.
- **Time spine = `dim_data`** (`time_spine.standard_granularity_column: data`). As datas sentinela dos membros
  `-1`/`-2` (1899-12-30/31) são contíguas a 1900-01-01, então o calendário segue contínuo. Elas aparecem como
  `metric_time` em consultas de dimensão pura (RSEM-11). Nenhuma métrica é afetada hoje; se uma métrica futura com
  `join_to_timespine` ou `cumulative` precisar, o caminho é um *time spine* próprio sem os membros `-1`/`-2`.
- **Fotografia mensal**: as contagens do resumo usam `non_additive_dimension` (`mes`, `max`). Em grão maior
  que o mês vale o último mês **em que o recorte filtrado tem linhas**, em vez da soma dos meses. O MetricFlow
  calcula o `MAX(mes)` depois do `--where` (RSEM-01): se o filtro esvazia o último mês, a consulta devolve uma
  fotografia velha. Sem como mudar isso no MetricFlow, a doc ensina o estoque atual por `metric_time__month` e
  `qtd_ativos` em vez de filtrar `ATIVA`, e um teste documenta o comportamento.
- **Datas como dimensões derivadas**: `mes` do resumo vem de `mes_referencia`. `data_inicio_atividade` e
  `data_situacao` vêm das chaves `sk_data` (`-1`/`-2` viram nulo). Nenhum modelo SQL muda.
- **Ferramenta local**: CLI `mf` (`dbt-metricflow>=0.15,<0.16`, dependência de desenvolvimento, compatível com
  o dbt-core 1.12.5 e o MetricFlow 0.213 já trazido pelo dbt-core). O limite de versão documenta a dependência:
  a semântica do `non_additive_dimension` e o descarte de `fill_nulls_with` são deste MetricFlow. `make semantica` valida (inclusive contra o
  warehouse) e lista as métricas. Testes de integração comparam as métricas com SQL direto no gold.
- **Escopo/marcação (ADR-0006)**:
  - modelos semânticos e métricas levam `meta.escopo: adicao`; o dbt não aceita tags neles;
  - *saved queries* levam meta e tag;
  - o `test_escopo_meta` cobre os três tipos.
- **Fora da camada**:
  - densidades por população ou domicílio: exigem somar um atributo de dimensão uma vez por município;
    ficam no mart de área de mercado e no DAX;
  - pontes muitos-para-muitos (CNAEs secundários, vizinhança).
- **Compatibilidade com o dbt v2**:
  - `input_metrics` sempre como objetos;
  - *saved queries* sem `order_by`, que o v2 rejeita.

  Verificado com o dbt 2.0.8: o YAML semântico passa, e resta só o bloqueio já conhecido do `options`
  (ADR-0017).

**Consequências.**
- **Bug do dbt-core 1.12.5:** o *partial parse* duplica as métricas de um YAML editado ("dbt found two metrics with the
  name …"). Os alvos `ci`, `pipeline`, `atualizar` e `semantica` do Makefile fazem um `dbt parse --no-partial-parse`
  antes, e a doc ensina o contorno.
- **OSI:** o `dbt parse` passa a gravar `target/osi_document.json` (Open Semantic Interchange).
- **Power BI:** continua com DAX. A tabela de equivalência métrica × medida fica em `docs/referencia/camada-semantica.md`.

**Contexto de negócio e ontologia (2026-10-10, pedido do usuário).** A doc só descrevia a estrutura; faltava o
significado dos dados para usar as métricas direito.
- `docs/referencia/camada-semantica.md` ganhou a **Parte A — Negócio**, antes da parte técnica:
  - as bases;
  - os conceitos (empresa × estabelecimento, porte, Simples/MEI, situação cadastral, CNAE, município);
  - o ciclo de vida e a relação dele com as métricas;
  - glossário e perguntas frequentes com `mf query`.
  Toda regra legal cita a fonte primária (leiaute da RFB, IN RFB 2.119/2022, LC 123/2006, Resolução CGSN
  140/2018, CONCLA), com data de acesso.
- **Ontologia formal** em `docs/referencia/ontologia/rfb_cnpj.ttl` (OWL/Turtle). As anotações próprias
  (`rfbo:entidadeSemantica`, `rfbo:dimensaoSemantica`, `rfbo:metricaDbt`, `rfbo:modeloDbt`, `rfbo:colunaDbt`)
  ligam cada conceito ao projeto.
- `tests/integration/test_ontologia.py` (rdflib, dependência de desenvolvimento) cobre os dois sentidos: todo nome
  anotado existe nos manifestos, e toda entidade semântica e toda métrica tem um conceito.
- Não há entidade semântica "empresa": a empresa (CNPJ básico) é contada pelas matrizes (`qtd_matrizes`). As
  entidades `estabelecimento`, `porte` e `situacao_cadastral` ganharam `description` de negócio no YAML.
- `scripts/verificar_doc_semantica.py` confere os identificadores entre crases e as âncoras da doc e executa os
  exemplos `mf`. A parte estática roda no `make ci`, pelo `tests/integration/test_doc_semantica.py` (RSEM-10).

**Revisão RSEM (2026-10-10, lote FRSEM).** Nova métrica `baixas` (só BAIXADA), porque `encerramentos` inclui
inaptidões declaradas em lote (44 % dos encerramentos de 2026 no dado real). Os testes passam a comparar com SQL
todas as métricas do resumo nos grãos mês, ano e sem tempo, e as de sobrevivência a 1, 3 e 5 anos. A ontologia
ganha o teste de afinidade conceito × modelo semântico.

Fontes: [Semantic models](https://docs.getdbt.com/docs/build/semantic-models),
[Metrics overview](https://docs.getdbt.com/docs/build/metrics-overview),
[MetricFlow time spine](https://docs.getdbt.com/docs/build/metricflow-time-spine),
[Migrate to the latest YAML spec](https://docs.getdbt.com/docs/build/latest-metrics-spec),
[Modernizing the Semantic Layer spec](https://docs.getdbt.com/blog/modernizing-the-semantic-layer-spec).
