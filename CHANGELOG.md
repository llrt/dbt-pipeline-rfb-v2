# Changelog

> **Para quem:** quem atualiza de uma versão para outra ou quer saber o que mudou · **Quando ler:** antes de
> atualizar, e para achar a release com o detalhe de cada versão.

Formato do [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/); versões no
[Versionamento Semântico](https://semver.org/lang/pt-BR/). O detalhe completo está na release de cada versão; o
histórico de como o projeto foi feito, em [docs/historico/](docs/historico/README.md).

## [Não lançada] — v1.5.0

### Alterado
- Documentação reorganizada por público: `docs/uso/`, `docs/referencia/`, `docs/relatorios/` e `docs/historico/`;
  o README vira porta de entrada com 6 entradas. Correspondência das seções antigas em
  [reorganizacao-v1.5.0.md](docs/historico/reorganizacao-v1.5.0.md).
- Conceitos de negócio com fonte única: definições curtas em doc blocks do dbt, usadas pelos YAMLs, pelo
  dicionário, pelo catálogo do agente e por [docs/conceitos.md](docs/conceitos.md), que recebe a antiga Parte A da
  camada semântica. O ESCOPO entra no ARCHITECTURE (§11) e cada triagem vai para o fim da sua revisão.
- Verificador de links e âncoras dos `.md` no `make ci`; caminhos de `docs/` centralizados no código.

**Nota de upgrade:** `rfb relatorio` e `rfb regras` passam a gravar em `docs/relatorios/estudo-caso.md` e
`docs/relatorios/regras-negocio.md`. `--saida` e `--saida-relatorio` continuam valendo. Os arquivos-ponte nos
caminhos antigos (`docs/CAMADA_SEMANTICA.md`, `docs/DICIONARIO_DADOS.md`, `docs/GUIA_CONSULTA_LINGUAGEM_NATURAL.md`,
`docs/REGRAS_NEGOCIO.md`, `docs/ESCOPO.md`, `RETRO.md`) saem na v1.6.0.

## [1.4.1] — 2026-10-15

### Adicionado
- 93 golden queries em 23 conceitos × 7 camadas, testadas no CI com a resposta exata nas fixtures, e a matriz
  de cobertura conceito × camada.
- Catálogo legível por máquina (`make golden`) e o guia de consulta em linguagem natural para um agente, com
  glossário, 21 armadilhas, privacidade e exemplos testados (ADR-0023). Modelos e métricas não mudam.

Release: [v1.4.1](https://github.com/llrt/dbt-pipeline-rfb-v2/releases/tag/v1.4.1)

## [1.4.0] — 2026-10-15

### Adicionado
- Fontes gratuitas do IBGE baixadas da origem: CEMPRE, renda do Censo 2022 e REGIC 2018, mais o valor
  adicionado por atividade (ADR-0022).
- `bridge_municipio_destino_compras`, `mart_emprego_setor_municipio`, o polo de compras em `dim_municipio` e em
  `mart_concorrencia_area_mercado`, a RN-30 e os cenários de uso.
- `--renovar-ibge` e `--sem-ibge`; uma falha do IBGE vira aviso. Upgrade da v1.3 sem quebra.

Release: [v1.4.0](https://github.com/llrt/dbt-pipeline-rfb-v2/releases/tag/v1.4.0)

## [1.3.0] — 2026-10-13

### Adicionado
- Catálogo das regras e invariantes de negócio (RN-01 a RN-29), cada uma com a fonte primária (ADR-0020).
- Checks fora do `dbt build` e `rfb regras` / `make regras`, que geram o relatório de inconsistências do dado
  real só com contagens e saem com 0 mesmo havendo violações.

Release: [v1.3.0](https://github.com/llrt/dbt-pipeline-rfb-v2/releases/tag/v1.3.0)

## [1.2.0] — 2026-10-13

### Adicionado
- Dicionário de dados gerado do manifesto e do catálogo do dbt (`make dicionario`, ADR-0019): 57 tabelas e 559
  colunas, com grão, chaves, domínio, origem e linhagem, conferido no CI.
- `meta.campo_leiaute`, `meta.grao` e `meta.linhagem` nos YAMLs; descrições a 100 % nas fontes e no gold.

Release: [v1.2.0](https://github.com/llrt/dbt-pipeline-rfb-v2/releases/tag/v1.2.0)

## [1.1.0] — 2026-10-10

### Adicionado
- Camada semântica dbt/MetricFlow (ADR-0018): 8 modelos semânticos, 26 métricas com fotografia mensal, *time
  spine* e 4 *saved queries*; `make semantica`.
- Contexto de negócio das bases da RFB com fontes primárias e a ontologia OWL ligada ao modelo, ambos testados.

Release: [v1.1.0](https://github.com/llrt/dbt-pipeline-rfb-v2/releases/tag/v1.1.0)

## [1.0.1] — 2026-10-06

### Alterado
- YAMLs no formato `config:`, compatível com o dbt v2 (Fusion); a migração ao Fusion foi avaliada e adiada
  (ADR-0017).
- Testes herméticos (ignoram o `.env` do desenvolvedor) e CI com actions em Node 24. Sem mudança de modelo ou
  resultado.

Release: [v1.0.1](https://github.com/llrt/dbt-pipeline-rfb-v2/releases/tag/v1.0.1)

## [1.0.0] — 2026-10-02

### Adicionado
- Port do MVP de notebooks Spark para dbt + DuckDB sobre Parquet: `bh_empresas`, `agg_empresas` e o estudo de
  caso Fundão/ES, com paridade de 0 diferenças em 71,4 M linhas contra o SQL original.
- Pipeline mensal idempotente (`rfb pipeline`, `rfb atualizar`), modelo estrela para Power BI, marts de
  concorrência, sobrevivência, dinâmica e fornecedores, enriquecimento Base dos Dados e publicação opcional no
  MotherDuck.
- Qualidade de dados em todas as etapas, CPF mascarado nos nomes, guia de dbt e ADRs 0001–0016.

Release: [v1.0.0](https://github.com/llrt/dbt-pipeline-rfb-v2/releases/tag/v1.0.0)
