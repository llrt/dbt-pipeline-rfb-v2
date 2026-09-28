DATA_ROOT ?= $(CURDIR)/data
MES ?=

export DATA_ROOT
export DBT_PROFILES_DIR = $(CURDIR)/transform

.PHONY: setup fixtures ingest ci pipeline docs lint sync report clean

## setup: sincroniza dependências Python e pacotes dbt
setup:
	uv sync
	cd transform && uv run dbt deps

## fixtures: gera fixtures sintéticas RFB/BD (não implementado — T4)
fixtures:
	@echo "fixtures: não implementado (tarefa T4)"
	@exit 2

## ingest: ingesta os dados RFB/BD (não implementado — T10)
ingest:
	@echo "ingest: não implementado (tarefa T10)"
	@exit 2

## ci: pipeline local completo sobre fixtures (não implementado — T10)
ci:
	@echo "ci: não implementado (tarefa T10)"
	@exit 2

## pipeline: pipeline ponta a ponta sobre dados reais (não implementado — T28)
pipeline:
	@echo "pipeline: não implementado (tarefa T28)"
	@exit 2

## docs: gera a documentação de dbt
docs:
	cd transform && uv run dbt docs generate

## lint: ruff + sqlfluff
lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run sqlfluff lint transform/models

## sync: envia raw/ e gold/ a s3:// (não implementado — T11)
sync:
	@echo "sync: não implementado (tarefa T11)"
	@exit 2

## report: gera o relatório do estudo de caso (não implementado — T27)
report:
	@echo "report: não implementado (tarefa T27)"
	@exit 2

## clean: remove artefactos temporais e de build
clean:
	rm -rf .tmp .venv
	rm -rf transform/target transform/logs transform/dbt_packages
	find . -type d -name __pycache__ -prune -exec rm -rf {} +