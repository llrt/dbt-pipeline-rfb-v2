DATA_ROOT ?= $(CURDIR)/data
MES ?=

export DATA_ROOT
export DBT_PROFILES_DIR = $(CURDIR)/transform

.PHONY: setup fixtures ingest ci pipeline docs lint sync report clean

## setup: sincroniza dependências Python e pacotes dbt
setup:
	uv sync --all-extras
	cd transform && uv run dbt deps

## fixtures: gera fixtures sintéticas RFB/BD em tests/fixtures/generated
fixtures:
	uv run python scripts/gen_fixtures.py --saida tests/fixtures/generated

## ingest: ingesta os dados RFB/BD em DATA_ROOT (rede real, ou --origem-local via ORIGEM_LOCAL)
ingest:
	uv run rfb ingest $(if $(MES),--mes $(MES)) $(if $(ORIGEM_LOCAL),--origem-local $(ORIGEM_LOCAL)) $(if $(PERMITIR_INCOMPLETO),--permitir-incompleto)

## ci: pipeline local completo sobre fixtures sintéticas, sem rede, em < 120s
ci: DATA_ROOT := $(CURDIR)/.tmp/ci/data
ci:
	rm -rf .tmp/ci
	uv run python scripts/gen_fixtures.py --saida .tmp/ci/fixtures
	uv run rfb ingest --origem-local .tmp/ci/fixtures --mes 2026-09 --permitir-incompleto
	mkdir -p $(DATA_ROOT)/gold
	cd transform && uv run dbt deps && uv run dbt build --target ci
	uv run pytest -q tests/integration

## pipeline: pipeline ponta a ponta sobre dados reais (não implementado — T28)
pipeline:
	@echo "pipeline: não implementado (tarefa T28)"
	@exit 2

## docs: gera a documentação de dbt
docs:
	cd transform && uv run dbt docs generate

## lint: ruff + sqlfluff (mkdir -p $(DATA_ROOT): o templater dbt do sqlfluff abre DATA_ROOT/warehouse.duckdb)
lint:
	uv run ruff check .
	uv run ruff format --check .
	mkdir -p $(DATA_ROOT)
	uv run sqlfluff lint transform/models transform/tests

## sync: envia raw/ e gold/ a s3:// (DATA_ROOT precisa ser s3://...; ver docs/adr/0007)
sync:
	uv run rfb sync

## report: gera o relatório do estudo de caso (não implementado — T27)
report:
	@echo "report: não implementado (tarefa T27)"
	@exit 2

## clean: remove artefactos temporais e de build
clean:
	rm -rf .tmp .venv
	rm -rf transform/target transform/logs transform/dbt_packages
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
