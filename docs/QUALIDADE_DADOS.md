# Qualidade de dados — catálogo de checks

> Gerado por `scripts/gerar_qualidade_dados.py` a partir do manifesto dbt; não edite à mão.
> Estratégia: [ARCHITECTURE.md §6](../ARCHITECTURE.md); severidades: [ADR-0009](adr/0009-estrategia-testes.md);
> escopo: [ADR-0006](adr/0006-marcacao-escopo.md). Resultados de cada execução ficam em
> `dq_historico_testes` (resumo em `dq_resumo_execucao`) e as linhas com falha dos testes `warn`
> em `main_dbt_test__audit.*` (`store_failures`).

## Como ler

- **Antes** = valida a entrada de uma etapa; **Depois** = valida a saída.
- **Severidade**: `error` interrompe o `dbt build`; `warn` registra a anomalia e não interrompe.
  Exceção documentada: `cnpj_dv_valido` é `warn`, mas vira erro se mais de 0,1% dos CNPJs forem
  inválidos **e** houver mais de 100 inválidos (`error_if` do dbt não aceita limites relativos).
  `data_nao_futura` cobre toda data do staging, exceto `dat_exclusao_simples` e `dat_exclusao_mei`
  (exclusão com efeito futuro é legítima; R3-11).
- **Escopo**: `original` (check do MVP; notebook de origem na última coluna) ou `adicao`.

## Checks da ingestão (Python, antes do dbt)

| Etapa | Antes | Depois |
|---|---|---|
| Download | mês existe (senão lista os disponíveis); tamanho remoto conhecido | tamanho confere com `getcontentlength`; zip íntegro e sem path traversal; sha256 no manifesto |
| Conversão | encoding latin-1, delimitador `;` e escape fixos | taxa de rejeito ≤ `RFB_MAX_TAXA_REJEITO` (rejeitos em `raw/_rejeitos/`); contagem > 0; `_manifestos/<mes>.json` |
| Gravação | — | Parquet escrito em temp + rename atômico; mesma soma sha256 não reconverte |

## Checks dbt por etapa

| Etapa | Momento | O que valida |
|---|---|---|
| Fontes | Antes | Entrada do dbt: Parquet raw (checks dos notebooks 2.x do original). (34 testes) |
| Seeds | Antes | Domínios estáticos usados por staging e dimensões. (6 testes) |
| Staging | Depois | Tipagem, CNPJ, datas e ausência de colunas de contato. (43 testes) |
| Intermediate | Depois | Joins sem descarte e explosão de CNAEs secundários. (7 testes) |
| Original | Depois | `bh_empresas`/`agg_empresas`: reconciliação, domínios, paridade. (12 testes) |
| Core | Depois | Modelo estrela: chaves, relacionamentos, reconciliação da fato. (59 testes) |
| Análises | Depois | Marts analíticos: invariantes numéricas. (37 testes) |
| Observabilidade | Depois | Resumo do histórico de testes. (2 testes) |

### Fontes (Antes)

| Alvo | Check | Severidade | Escopo | Origem (notebook) |
|---|---|---|---|---|
| `cnaes` | Reproduz o check do notebook 2.1.2 (qualidade dos domínios): CNAEs RFB sem par na Base dos Dados. | warn | original | 2.1.2 |
| `cnaes` | `unique_combination_of_columns` {"combination_of_columns": ["codigo", "_mes_referencia"]} | error | original | 2.1.1 |
| `cnaes._data_referencia` | `not_null` | error | adicao | — |
| `cnaes.codigo` | `not_null` | error | original | 2.1.1 |
| `empresas` | R1-21: `--vars 'mes_referencia: 2026-10'` sem partição geraria staging vazio e todos os testes passariam. | error | adicao | — |
| `empresas` | R1-22: os checks `relationships` do original (natureza, CNAE principal e município de empresas/estabelecimentos -> domínios) comparados DENTRO de cada `_mes_referencia`. | error | original | 2.2 / 2.3 |
| `empresas` | `unique_combination_of_columns` {"combination_of_columns": ["cnpj_raiz", "_mes_referencia"]} | error | original | 2.2 |
| `empresas._data_referencia` | `not_null` | error | adicao | — |
| `empresas.cnpj_raiz` | `not_null` | error | original | 2.2 |
| `empresas.porte` | `accepted_values` {"values": ["00", "01", "03", "05"]} | error | original | 2.2 |
| `estabelecimentos` | Staging AC 3: CNPJ completo (raiz + ordem + DV, com lpad) único por mês de referência. | error | original | 2.3 |
| `estabelecimentos` | `unique_combination_of_columns` {"combination_of_columns": ["cnpj_raiz", "cnpj_ordem", "cnpj_dv", "_mes_referencia"]} | error | original | 2.3 |
| `estabelecimentos._data_referencia` | `not_null` | error | adicao | — |
| `estabelecimentos.cnpj_dv` | `not_null` | error | original | 2.3 |
| `estabelecimentos.cnpj_ordem` | `not_null` | error | original | 2.3 |
| `estabelecimentos.cnpj_raiz` | `not_null` | error | original | 2.3 |
| `estabelecimentos.situacao` | `accepted_values` {"values": ["01", "02", "03", "04", "08"]} | error | original | 2.3 |
| `motivos` | `unique_combination_of_columns` {"combination_of_columns": ["codigo", "_mes_referencia"]} | error | original | 2.1.1 |
| `motivos._data_referencia` | `not_null` | error | adicao | — |
| `motivos.codigo` | `not_null` | error | original | 2.1.1 |
| `municipio` | Reproduz o check do notebook 2.1.2 (qualidade dos domínios): códigos de município RFB sem par na Base dos Dados. | error | original | 2.1.2 |
| `municipio` | Staging AC 6 ("exatamente os listados no seed"): uma exceção do seed que passou a ter par na Base dos Dados está obsoleta e deve sair de `excecoes_conhecidas_municipio`. | warn | original | 2.1.2 |
| `municipio.id_municipio_rf` | `unique` | warn | original | 2.1.2 |
| `municipios` | `unique_combination_of_columns` {"combination_of_columns": ["codigo", "_mes_referencia"]} | error | original | 2.1.1 |
| `municipios._data_referencia` | `not_null` | error | adicao | — |
| `municipios.codigo` | `not_null` | error | original | 2.1.1 |
| `naturezas` | `unique_combination_of_columns` {"combination_of_columns": ["codigo", "_mes_referencia"]} | error | original | 2.1.1 |
| `naturezas._data_referencia` | `not_null` | error | adicao | — |
| `naturezas.codigo` | `not_null` | error | original | 2.1.1 |
| `paises._data_referencia` | `not_null` | error | adicao | — |
| `pib` | `unique_combination_of_columns` {"combination_of_columns": ["id_municipio", "ano"]} | error | adicao | — |
| `populacao` | `unique_combination_of_columns` {"combination_of_columns": ["id_municipio", "ano"]} | error | adicao | — |
| `qualificacoes._data_referencia` | `not_null` | error | adicao | — |
| `simples._data_referencia` | `not_null` | error | adicao | — |

### Seeds (Antes)

| Alvo | Check | Severidade | Escopo | Origem (notebook) |
|---|---|---|---|---|
| `dominio_matriz_filial.codigo` | `not_null` | error | adicao | — |
| `dominio_matriz_filial.codigo` | `unique` | error | adicao | — |
| `dominio_porte.codigo` | `not_null` | error | adicao | — |
| `dominio_porte.codigo` | `unique` | error | adicao | — |
| `dominio_situacao_cadastral.codigo` | `not_null` | error | adicao | — |
| `dominio_situacao_cadastral.codigo` | `unique` | error | adicao | — |

### Staging (Depois)

| Alvo | Check | Severidade | Escopo | Origem (notebook) |
|---|---|---|---|---|
| `estabelecimentos` | DQ-01 / R3-09: casos conhecidos do teste `data_nao_futura`. | error | adicao | — |
| `stg_bd__cnaes.subclasse` | `not_null` | error | adicao | — |
| `stg_bd__cnaes.subclasse` | `tamanho_exato` {"tamanho": 7} | error | adicao | — |
| `stg_bd__cnaes.subclasse` | `unique` | error | adicao | — |
| `stg_bd__municipios.id_municipio` | `not_null` | error | adicao | — |
| `stg_bd__municipios.id_municipio` | `unique` | error | adicao | — |
| `stg_bd__municipios.id_municipio_rf` | `tamanho_exato` {"tamanho": 4} | error | adicao | — |
| `stg_rfb__cnaes.codigo` | `not_null` | error | adicao | — |
| `stg_rfb__cnaes.codigo` | `tamanho_exato` {"tamanho": 7} | error | adicao | — |
| `stg_rfb__cnaes.codigo` | `unique` | error | adicao | — |
| `stg_rfb__empresas.cnpj_raiz` | `not_null` | error | adicao | — |
| `stg_rfb__empresas.cnpj_raiz` | `tamanho_exato` {"tamanho": 8} | error | adicao | — |
| `stg_rfb__empresas.cnpj_raiz` | `unique` | error | adicao | — |
| `stg_rfb__empresas.porte_codigo` | `accepted_values` {"values": [0, 1, 3, 5], "quote": false} | error | adicao | — |
| `stg_rfb__estabelecimentos` | Staging AC 14 / ADR-0008: nenhum modelo de staging, intermediate ou marts expõe dados de contato. | error | adicao | — |
| `stg_rfb__estabelecimentos._data_referencia` | `not_null` | error | adicao | — |
| `stg_rfb__estabelecimentos.cnae_principal` | `tamanho_exato` {"tamanho": 7} | error | adicao | — |
| `stg_rfb__estabelecimentos.cnpj_completo` | `cnpj_dv_valido` | warn | adicao | — |
| `stg_rfb__estabelecimentos.cnpj_completo` | `not_null` | error | adicao | — |
| `stg_rfb__estabelecimentos.cnpj_completo` | `tamanho_exato` {"tamanho": 14} | error | adicao | — |
| `stg_rfb__estabelecimentos.cnpj_completo` | `unique` | error | adicao | — |
| `stg_rfb__estabelecimentos.cnpj_raiz` | `not_null` | error | adicao | — |
| `stg_rfb__estabelecimentos.dat_inicio_atividade` | `accepted_range` {"min_value": "date '1900-01-01'"} | warn | adicao | — |
| `stg_rfb__estabelecimentos.dat_inicio_atividade` | `data_nao_futura` | warn | adicao | — |
| `stg_rfb__estabelecimentos.dat_situacao` | `data_nao_futura` | warn | adicao | — |
| `stg_rfb__estabelecimentos.dat_situacao_especial` | `data_nao_futura` | warn | adicao | — |
| `stg_rfb__estabelecimentos.municipio_rfb_codigo` | `tamanho_exato` {"tamanho": 4} | error | adicao | — |
| `stg_rfb__estabelecimentos.situacao_codigo` | `accepted_values` {"values": [1, 2, 3, 4, 8], "quote": false} | error | adicao | — |
| `stg_rfb__motivos.codigo` | `not_null` | error | adicao | — |
| `stg_rfb__motivos.codigo` | `tamanho_exato` {"tamanho": 2} | error | adicao | — |
| `stg_rfb__motivos.codigo` | `unique` | error | adicao | — |
| `stg_rfb__municipios.codigo` | `not_null` | error | adicao | — |
| `stg_rfb__municipios.codigo` | `tamanho_exato` {"tamanho": 4} | error | adicao | — |
| `stg_rfb__municipios.codigo` | `unique` | error | adicao | — |
| `stg_rfb__naturezas.codigo` | `not_null` | error | adicao | — |
| `stg_rfb__naturezas.codigo` | `tamanho_exato` {"tamanho": 4} | error | adicao | — |
| `stg_rfb__naturezas.codigo` | `unique` | error | adicao | — |
| `stg_rfb__simples.cnpj_raiz` | `not_null` | error | adicao | — |
| `stg_rfb__simples.cnpj_raiz` | `tamanho_exato` {"tamanho": 8} | error | adicao | — |
| `stg_rfb__simples.cnpj_raiz` | `unique` | error | adicao | — |
| `stg_rfb__simples.dat_opcao_mei` | `data_nao_futura` | warn | adicao | — |
| `stg_rfb__simples.dat_opcao_simples` | `data_nao_futura` | warn | adicao | — |
| `—` | DQ-01 / R3-09: casos conhecidos do teste `cnpj_dv_valido`. | error | adicao | — |

### Intermediate (Depois)

| Alvo | Check | Severidade | Escopo | Origem (notebook) |
|---|---|---|---|---|
| `int_cnaes_secundarios__explodidos` | `unique_combination_of_columns` {"combination_of_columns": ["cnpj_completo", "codigo_cnae_secundario"]} | error | adicao | — |
| `int_estabelecimentos__enriquecidos.cnpj_completo` | `not_null` | error | adicao | — |
| `int_estabelecimentos__enriquecidos.cnpj_completo` | `unique` | error | adicao | — |
| `int_estabelecimentos__enriquecidos.matriz_filial_codigo` | `relationships` {"to": "ref('dominio_matriz_filial')", "field": "codigo"} | error | adicao | — |
| `int_municipios__conformados.codigo_rfb` | `unique` | warn | adicao | — |
| `int_municipios__conformados.sk_municipio` | `not_null` | error | adicao | — |
| `int_municipios__conformados.sk_municipio` | `unique` | error | adicao | — |

### Original (Depois)

| Alvo | Check | Severidade | Escopo | Origem (notebook) |
|---|---|---|---|---|
| `agg_empresas` | Original AC 9: a soma de `qtd_empresas` precisa ser igual à contagem de `bh_empresas`; o `group by` não pode perder nem duplicar estabelecimentos. | error | original | 3 |
| `agg_empresas.qtd_empresas` | `accepted_range` {"min_value": 1} | error | original | 3 |
| `agg_empresas.qtd_empresas` | `not_null` | error | original | 3 |
| `bh_empresas` | Original AC 10 (ADR-0005): `bh_empresas` não pode diferir, linha a linha (com multiplicidade), da tradução literal do SQL do notebook 3 sobre os mesmos dados raw. | error | adicao | — |
| `bh_empresas` | Original AC 11: estabelecimentos do mês que os inner joins do notebook 3 descartam de `bh_empresas` (fixtures: 3 — K exterior, L CNAE sem par no BD, M município sem par no BD). | warn | adicao | — |
| `bh_empresas.cnae_principal` | `tamanho_exato` {"tamanho": 7} | error | original | 3 |
| `bh_empresas.cnpj_completo` | `not_null` | error | original | 3 |
| `bh_empresas.cnpj_completo` | `unique` | error | original | 3 |
| `bh_empresas.idade_atual` | `accepted_range` {"min_value": 0, "max_value": 200} | error | original | 3 |
| `bh_empresas.porte` | `accepted_values` {"values": ["N/A", "MICRO", "PEQUENA", "DEMAIS"]} | error | original | 3 |
| `bh_empresas.situacao` | `accepted_values` {"values": ["ATIVA", "INATIVA"]} | error | original | 3 |
| `empresas` | ADR-0005, emenda R2-01: `bh_empresas.nome` sai com `trim` (staging); o original, não. | warn | adicao | — |

### Core (Depois)

| Alvo | Check | Severidade | Escopo | Origem (notebook) |
|---|---|---|---|---|
| `bridge_estabelecimento_cnae_secundario` | `unique_combination_of_columns` {"combination_of_columns": ["cnpj_completo", "codigo_cnae_secundario"]} | error | adicao | — |
| `bridge_estabelecimento_cnae_secundario.cnpj_completo` | `not_null` | error | adicao | — |
| `bridge_estabelecimento_cnae_secundario.cnpj_completo` | `relationships` {"to": "ref('fct_estabelecimentos')", "field": "cnpj_completo"} | error | adicao | — |
| `bridge_estabelecimento_cnae_secundario.sk_cnae` | `not_null` | error | adicao | — |
| `bridge_estabelecimento_cnae_secundario.sk_cnae` | `relationships` {"to": "ref('dim_cnae')", "field": "sk_cnae"} | error | adicao | — |
| `dim_cnae.codigo_subclasse` | `not_null` | error | adicao | — |
| `dim_cnae.codigo_subclasse` | `unique` | error | adicao | — |
| `dim_cnae.sk_cnae` | `not_null` | error | adicao | — |
| `dim_cnae.sk_cnae` | `unique` | error | adicao | — |
| `dim_data` | BI-01 / R3-03: o calendário começa em 1900-01-01, contém o dia de `data_referencia`, não tem lacunas (uma linha por dia) e os membros -1/-2 ficam contíguos (1899-12-31 e 1899-12-30), com data, para que a tabela possa ser marcada como tabela de datas no Power BI. Retorna uma linha por violação. | error | adicao | — |
| `dim_data.sk_data` | `not_null` | error | adicao | — |
| `dim_data.sk_data` | `unique` | error | adicao | — |
| `dim_municipio.codigo_rfb` | `not_null` | error | adicao | — |
| `dim_municipio.codigo_rfb` | `unique` | warn | adicao | — |
| `dim_municipio.sk_municipio` | `not_null` | error | adicao | — |
| `dim_municipio.sk_municipio` | `unique` | error | adicao | — |
| `dim_natureza_juridica.codigo_natureza_juridica` | `not_null` | error | adicao | — |
| `dim_natureza_juridica.codigo_natureza_juridica` | `unique` | error | adicao | — |
| `dim_natureza_juridica.sk_natureza_juridica` | `not_null` | error | adicao | — |
| `dim_natureza_juridica.sk_natureza_juridica` | `unique` | error | adicao | — |
| `dim_porte.codigo_porte` | `not_null` | error | adicao | — |
| `dim_porte.codigo_porte` | `unique` | error | adicao | — |
| `dim_porte.sk_porte` | `not_null` | error | adicao | — |
| `dim_porte.sk_porte` | `unique` | error | adicao | — |
| `dim_situacao_cadastral.codigo_situacao_cadastral` | `not_null` | error | adicao | — |
| `dim_situacao_cadastral.codigo_situacao_cadastral` | `unique` | error | adicao | — |
| `dim_situacao_cadastral.sk_situacao_cadastral` | `not_null` | error | adicao | — |
| `dim_situacao_cadastral.sk_situacao_cadastral` | `unique` | error | adicao | — |
| `fct_estabelecimentos` | CORE-01: a fato não descarta nem duplica estabelecimentos (mesma contagem do staging do mês) e usa a chave -1 exatamente onde falta par na dimensão (flags `tem_*` da camada intermediate). | error | adicao | — |
| `fct_estabelecimentos.cnpj_completo` | `not_null` | error | adicao | — |
| `fct_estabelecimentos.cnpj_completo` | `unique` | error | adicao | — |
| `fct_estabelecimentos.sk_cnae` | `not_null` | error | adicao | — |
| `fct_estabelecimentos.sk_cnae` | `relationships` {"to": "ref('dim_cnae')", "field": "sk_cnae"} | error | adicao | — |
| `fct_estabelecimentos.sk_data_inicio_atividade` | `not_null` | error | adicao | — |
| `fct_estabelecimentos.sk_data_inicio_atividade` | `relationships` {"to": "ref('dim_data')", "field": "sk_data"} | error | adicao | — |
| `fct_estabelecimentos.sk_data_situacao` | `not_null` | error | adicao | — |
| `fct_estabelecimentos.sk_data_situacao` | `relationships` {"to": "ref('dim_data')", "field": "sk_data"} | error | adicao | — |
| `fct_estabelecimentos.sk_municipio` | `not_null` | error | adicao | — |
| `fct_estabelecimentos.sk_municipio` | `relationships` {"to": "ref('dim_municipio')", "field": "sk_municipio"} | error | adicao | — |
| `fct_estabelecimentos.sk_natureza_juridica` | `not_null` | error | adicao | — |
| `fct_estabelecimentos.sk_natureza_juridica` | `relationships` {"to": "ref('dim_natureza_juridica')", "field": "sk_natureza_juridica"} | error | adicao | — |
| `fct_estabelecimentos.sk_porte` | `not_null` | error | adicao | — |
| `fct_estabelecimentos.sk_porte` | `relationships` {"to": "ref('dim_porte')", "field": "sk_porte"} | error | adicao | — |
| `fct_estabelecimentos.sk_situacao_cadastral` | `not_null` | error | adicao | — |
| `fct_estabelecimentos.sk_situacao_cadastral` | `relationships` {"to": "ref('dim_situacao_cadastral')", "field": "sk_situacao_cadastral"} | error | adicao | — |
| `fct_resumo_mensal` | BI-02 / ADR-0013: a partição do mês processado em `fct_resumo_mensal` reconcilia com `fct_estabelecimentos` (quantidade, ativos, matrizes, capital das matrizes e soma da idade); soma errada ou partição ausente retornam uma linha. | error | adicao | — |
| `fct_resumo_mensal` | R3-18 / BI-02: toda chave da partição do mês processado existe na dimensão correspondente. | error | adicao | — |
| `fct_resumo_mensal` | R3-18: as chaves de TODAS as partições de `fct_resumo_mensal` existem nas dimensões atuais. | warn | adicao | — |
| `fct_resumo_mensal` | `unique_combination_of_columns` {"combination_of_columns": ["mes_referencia", "sk_municipio", "sk_cnae", "sk_porte", "sk_situacao_cadastral", "opcao_mei"]} | error | adicao | — |
| `fct_resumo_mensal.mes_referencia` | `not_null` | error | adicao | — |
| `fct_resumo_mensal.opcao_mei` | `not_null` | error | adicao | — |
| `fct_resumo_mensal.qtd_ativos` | `not_null` | error | adicao | — |
| `fct_resumo_mensal.qtd_estabelecimentos` | `not_null` | error | adicao | — |
| `fct_resumo_mensal.qtd_matrizes` | `not_null` | error | adicao | — |
| `fct_resumo_mensal.sk_cnae` | `not_null` | error | adicao | — |
| `fct_resumo_mensal.sk_mes_referencia` | `not_null` | error | adicao | — |
| `fct_resumo_mensal.sk_municipio` | `not_null` | error | adicao | — |
| `fct_resumo_mensal.sk_porte` | `not_null` | error | adicao | — |
| `fct_resumo_mensal.sk_situacao_cadastral` | `not_null` | error | adicao | — |

### Análises (Depois)

| Alvo | Check | Severidade | Escopo | Origem (notebook) |
|---|---|---|---|---|
| `dim_municipio` | CASE-01 / ANA-04 (R3-15): `caso_municipio` + `caso_uf` devem resolver para exatamente 1 município em `dim_municipio`. | error | adicao | — |
| `mart_concorrencia_municipio` | `unique_combination_of_columns` {"combination_of_columns": ["cnae_principal", "sk_municipio"]} | error | adicao | — |
| `mart_concorrencia_municipio.ativos` | `not_null` | error | adicao | — |
| `mart_concorrencia_municipio.ativos_por_10k_hab` | `accepted_range` {"min_value": 0} | error | adicao | — |
| `mart_concorrencia_municipio.cnae_principal` | `not_null` | error | adicao | — |
| `mart_concorrencia_municipio.inativos` | `not_null` | error | adicao | — |
| `mart_concorrencia_municipio.sk_cnae` | `not_null` | error | adicao | — |
| `mart_concorrencia_municipio.sk_cnae` | `relationships` {"to": "ref('dim_cnae')", "field": "sk_cnae"} | error | adicao | — |
| `mart_concorrencia_municipio.sk_municipio` | `not_null` | error | adicao | — |
| `mart_concorrencia_municipio.sk_municipio` | `relationships` {"to": "ref('dim_municipio')", "field": "sk_municipio"} | error | adicao | — |
| `mart_dinamica_mercado.aberturas` | `not_null` | error | adicao | — |
| `mart_dinamica_mercado.ano` | `not_null` | error | adicao | — |
| `mart_dinamica_mercado.cnae_principal` | `not_null` | error | adicao | — |
| `mart_dinamica_mercado.encerramentos` | `not_null` | error | adicao | — |
| `mart_dinamica_mercado.saldo` | `not_null` | error | adicao | — |
| `mart_dinamica_mercado.sk_cnae` | `not_null` | error | adicao | — |
| `mart_dinamica_mercado.sk_cnae` | `relationships` {"to": "ref('dim_cnae')", "field": "sk_cnae"} | error | adicao | — |
| `mart_dinamica_mercado.sk_municipio` | `not_null` | error | adicao | — |
| `mart_dinamica_mercado.sk_municipio` | `relationships` {"to": "ref('dim_municipio')", "field": "sk_municipio"} | error | adicao | — |
| `mart_fornecedores_proximos` | ANA-04 AC 7: nenhuma distância negativa e distância 0 para fornecedor no próprio município do caso (a distância de um ponto a si mesmo é nula). | error | adicao | — |
| `mart_fornecedores_proximos.cnae_fornecido` | `not_null` | error | adicao | — |
| `mart_fornecedores_proximos.cnpj_completo` | `not_null` | error | adicao | — |
| `mart_fornecedores_proximos.cnpj_completo` | `unique` | error | adicao | — |
| `mart_fornecedores_proximos.distancia_km` | `accepted_range` {"min_value": 0} | error | adicao | — |
| `mart_fornecedores_proximos.distancia_km` | `not_null` | error | adicao | — |
| `mart_fornecedores_proximos.sk_cnae` | `not_null` | error | adicao | — |
| `mart_fornecedores_proximos.sk_cnae` | `relationships` {"to": "ref('dim_cnae')", "field": "sk_cnae"} | error | adicao | — |
| `mart_fornecedores_proximos.sk_municipio` | `not_null` | error | adicao | — |
| `mart_fornecedores_proximos.sk_municipio` | `relationships` {"to": "ref('dim_municipio')", "field": "sk_municipio"} | error | adicao | — |
| `mart_fornecedores_proximos.via` | `accepted_values` {"values": ["principal", "secundario"]} | error | adicao | — |
| `mart_sobrevivencia_coorte` | ANA-02 AC 3: taxas em [0,1] e, dentro da linha, taxa_1a >= taxa_3a >= taxa_5a quando ambas as taxas comparadas são não nulas. | error | adicao | — |
| `mart_sobrevivencia_coorte.ano_coorte` | `not_null` | error | adicao | — |
| `mart_sobrevivencia_coorte.cnae_principal` | `not_null` | error | adicao | — |
| `mart_sobrevivencia_coorte.sk_cnae` | `not_null` | error | adicao | — |
| `mart_sobrevivencia_coorte.sk_cnae` | `relationships` {"to": "ref('dim_cnae')", "field": "sk_cnae"} | error | adicao | — |
| `mart_sobrevivencia_coorte.sk_porte` | `not_null` | error | adicao | — |
| `mart_sobrevivencia_coorte.sk_porte` | `relationships` {"to": "ref('dim_porte')", "field": "sk_porte"} | error | adicao | — |

### Observabilidade (Depois)

| Alvo | Check | Severidade | Escopo | Origem (notebook) |
|---|---|---|---|---|
| `dq_resumo_execucao.invocation_id` | `not_null` | error | adicao | — |
| `dq_resumo_execucao.invocation_id` | `unique` | error | adicao | — |

## Testes unitários dbt (regras de negócio)

| Modelo | Teste | Escopo |
|---|---|---|
| `agg_empresas` | `test_agg_empresas_agrupa_conta_e_tira_media` | adicao |
| `audit__bh_empresas_sql_original` | `test_audit__bh_empresas_sql_original_joins_por_inteiro` | adicao |
| `bh_empresas` | `test_bh_empresas_idade_usa_var_data_referencia` | adicao |
| `bh_empresas` | `test_bh_empresas_nome_e_dominios` | adicao |
| `bh_empresas` | `test_bh_empresas_porte` | adicao |
| `bh_empresas` | `test_bh_empresas_situacao_e_idade` | adicao |
| `bridge_estabelecimento_cnae_secundario` | `test_bridge_estabelecimento_cnae_secundario_sk_e_menos_um` | adicao |
| `dim_cnae` | `test_dim_cnae_sk_inteira_e_membro_nao_informado` | adicao |
| `dim_data` | `test_dim_data_calendario_continuo_com_atributos_em_portugues` | adicao |
| `dim_municipio` | `test_dim_municipio_membro_nao_informado` | adicao |
| `dim_natureza_juridica` | `test_dim_natureza_juridica_sk_e_membro_nao_informado` | adicao |
| `fct_estabelecimentos` | `test_fct_estabelecimentos_chaves_inteiras_e_menos_um` | adicao |
| `fct_resumo_mensal` | `test_fct_resumo_mensal_medidas_aditivas_por_grao` | adicao |
| `int_cnaes_secundarios__explodidos` | `test_int_cnaes_secundarios_explodidos` | adicao |
| `int_estabelecimentos__enriquecidos` | `test_int_estabelecimentos_enriquecidos_flags_e_nada_descartado` | adicao |
| `int_municipios__conformados` | `test_int_municipios_conformados_ano_mais_recente` | adicao |
| `int_municipios__conformados` | `test_int_municipios_conformados_var_ano_populacao` | adicao |
| `mart_fornecedores_proximos` | `test_mart_fornecedores_proximos_haversine_e_via` | adicao |
| `mart_sobrevivencia_coorte` | `test_mart_sobrevivencia_coorte_elegibilidade_e_sobrevivencia` | adicao |
| `mart_sobrevivencia_coorte` | `test_mart_sobrevivencia_coorte_limites_de_elegibilidade_e_aniversario` | adicao |
| `stg_bd__municipios` | `test_stg_bd__municipios_lpad_id_municipio_rf` | adicao |
| `stg_bd__municipios` | `test_stg_bd__municipios_parse_centroide` | adicao |
| `stg_rfb__cnaes` | `test_stg_rfb__cnaes_lpad_e_texto_vazio` | adicao |
| `stg_rfb__cnaes` | `test_stg_rfb__cnaes_lpad_nao_trunca_codigo_maior` | adicao |
| `stg_rfb__empresas` | `test_stg_rfb__empresas_filtra_mes_mais_recente` | adicao |
| `stg_rfb__empresas` | `test_stg_rfb__empresas_tipagem` | adicao |
| `stg_rfb__estabelecimentos` | `test_stg_rfb__estabelecimentos_cnaes_secundarios` | adicao |
| `stg_rfb__estabelecimentos` | `test_stg_rfb__estabelecimentos_cnpj_e_codigos` | adicao |
| `stg_rfb__estabelecimentos` | `test_stg_rfb__estabelecimentos_datas` | adicao |
| `stg_rfb__estabelecimentos` | `test_stg_rfb__estabelecimentos_filtra_mes_mais_recente` | adicao |
| `stg_rfb__municipios` | `test_stg_rfb__municipios_lpad_codigo` | adicao |
| `stg_rfb__municipios` | `test_stg_rfb__municipios_var_explicita_usa_o_mes_pedido` | adicao |
| `stg_rfb__municipios` | `test_stg_rfb__municipios_var_nula_usa_o_maior_mes` | adicao |
| `stg_rfb__simples` | `test_stg_rfb__simples_datas_invalidas_viram_null` | adicao |
| `stg_rfb__simples` | `test_stg_rfb__simples_flags_e_datas` | adicao |

## Histórico de execuções (DQ-02)

- `on-run-start` cria `main.dq_historico_testes` no `warehouse.duckdb`; `on-run-end` acrescenta uma
  linha por teste executado (dados e unitários): `invocation_id`, `nome_teste`, `status`, `falhas`,
  `severidade`, `escopo`, `executado_em`.
- `dq_resumo_execucao` (view) agrega por execução: aprovados, avisos, falhos, pulados.
- O histórico acumula enquanto o `warehouse.duckdb` existir. O `make ci` recria o warehouse a cada
  execução (histórico só da execução corrente); no ambiente real o arquivo é mantido.
