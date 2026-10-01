RAIZ_DADOS ?= $(CURDIR)/dados
MES ?=

export RAIZ_DADOS
export DBT_PROFILES_DIR = $(CURDIR)/transform

.PHONY: setup fixtures ingerir ci pipeline atualizar docs lint sincronizar relatorio publicar clean

## setup: sincroniza dependências Python e pacotes dbt (`--locked`: falha se o uv.lock divergir, R4-09)
setup:
	uv sync --locked --all-extras
	cd transform && uv run dbt deps

## fixtures: gera fixtures sintéticas RFB/BD em tests/fixtures/generated
fixtures:
	uv run python scripts/gerar_fixtures.py --saida tests/fixtures/generated

## ingerir: ingesta os dados RFB/BD em RAIZ_DADOS (rede real, ou --origem-local via ORIGEM_LOCAL)
ingerir:
	uv run rfb ingerir $(if $(MES),--mes $(MES)) $(if $(ORIGEM_LOCAL),--origem-local $(ORIGEM_LOCAL)) $(if $(PERMITIR_INCOMPLETO),--permitir-incompleto)

## ci: unit + pipeline completo sobre fixtures sintéticas + integração + lint, sem rede (RBP-03)
## Sequência (P22/UPD): pipeline 2026-08 (corrente) -> atualizar (2026-09 novo) -> atualizar (no-op)
## -> pipeline 2026-08 de novo (backfill: só a partição do resumo; gold corrente fica em 2026-09).
## A partição 2026-08 do resumo é apagada antes do backfill: o teste prova que ele a regrava (R4-04).
ci: RAIZ_DADOS := $(CURDIR)/.tmp/ci/dados
ci: CI_ORIGEM := --origem-local .tmp/ci/fixtures --permitir-incompleto --target ci --sem-publicar
ci:
	uv run pytest -q tests/unit
	rm -rf .tmp/ci
	uv run python scripts/gerar_fixtures.py --saida .tmp/ci/fixtures
	cd transform && uv run dbt deps
	uv run rfb pipeline $(CI_ORIGEM) --mes 2026-08 --saida-relatorio .tmp/ci/relatorio-2026-08.md
	uv run rfb atualizar $(CI_ORIGEM) --saida-relatorio .tmp/ci/relatorio.md
	set -o pipefail; uv run rfb atualizar $(CI_ORIGEM) --saida-relatorio .tmp/ci/relatorio.md | tee .tmp/ci/atualizar-noop.log
	rm -rf "$(RAIZ_DADOS)/gold/fct_resumo_mensal/mes_referencia=2026-08"
	set -o pipefail; uv run rfb pipeline $(CI_ORIGEM) --mes 2026-08 --sem-relatorio | tee .tmp/ci/backfill.log
	uv run pytest -q tests/integration
	$(MAKE) lint

## pipeline: ponta a ponta sobre dados reais (T28): ingest -> freshness -> dbt build -> relatório
## (-> publicar se MotherDuck configurado). MES=AAAA-MM opcional (padrão: mais recente completo).
pipeline:
	cd transform && uv run dbt deps
	uv run rfb pipeline $(if $(MES),--mes $(MES)) $(if $(ORIGEM_LOCAL),--origem-local $(ORIGEM_LOCAL)) $(if $(PERMITIR_INCOMPLETO),--permitir-incompleto)

## atualizar: atualização mensal (T36): processa o mês completo mais recente se for novo; senão no-op
atualizar:
	cd transform && uv run dbt deps
	uv run rfb atualizar $(if $(ORIGEM_LOCAL),--origem-local $(ORIGEM_LOCAL))

## docs: gera a documentação de dbt
docs:
	cd transform && uv run dbt docs generate

## lint: ruff + sqlfluff (mkdir -p $(RAIZ_DADOS): o templater dbt do sqlfluff abre RAIZ_DADOS/warehouse.duckdb)
lint:
	uv run ruff check .
	uv run ruff format --check .
	mkdir -p $(RAIZ_DADOS)
	uv run sqlfluff lint transform/models transform/tests transform/analyses

## sincronizar: envia raw/ e gold/ a s3:// (RAIZ_DADOS precisa ser s3://...; ver docs/adr/0007)
sincronizar:
	uv run rfb sincronizar

## relatorio: gera docs/RELATORIO_ESTUDO_CASO.md (requer `dbt build` prévio sobre RAIZ_DADOS)
relatorio:
	uv run rfb relatorio

## publicar: publica o gold no MotherDuck (requer MOTHERDUCK_TOKEN e MOTHERDUCK_BANCO; sem eles não faz nada)
publicar:
	uv run rfb publicar --destino motherduck $(if $(TABELAS),--tabelas $(TABELAS))

## clean: remove artefactos temporais e de build
clean:
	rm -rf .tmp .venv
	rm -rf transform/target transform/logs transform/dbt_packages
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
