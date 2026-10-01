RAIZ_DADOS ?= $(CURDIR)/dados
MES ?=

export RAIZ_DADOS
export DBT_PROFILES_DIR = $(CURDIR)/transform

.PHONY: setup fixtures ingerir ci pipeline docs lint sincronizar relatorio publicar clean

## setup: sincroniza dependências Python e pacotes dbt
setup:
	uv sync --all-extras
	cd transform && uv run dbt deps

## fixtures: gera fixtures sintéticas RFB/BD em tests/fixtures/generated
fixtures:
	uv run python scripts/gerar_fixtures.py --saida tests/fixtures/generated

## ingerir: ingesta os dados RFB/BD em RAIZ_DADOS (rede real, ou --origem-local via ORIGEM_LOCAL)
ingerir:
	uv run rfb ingerir $(if $(MES),--mes $(MES)) $(if $(ORIGEM_LOCAL),--origem-local $(ORIGEM_LOCAL)) $(if $(PERMITIR_INCOMPLETO),--permitir-incompleto)

## ci: unit + pipeline completo sobre fixtures sintéticas + integração + lint, sem rede (RBP-03)
ci: RAIZ_DADOS := $(CURDIR)/.tmp/ci/dados
ci:
	uv run pytest -q tests/unit
	rm -rf .tmp/ci
	uv run python scripts/gerar_fixtures.py --saida .tmp/ci/fixtures
	uv run rfb ingerir --origem-local .tmp/ci/fixtures --mes 2026-08 --permitir-incompleto
	uv run rfb ingerir --origem-local .tmp/ci/fixtures --mes 2026-09 --permitir-incompleto
	mkdir -p $(RAIZ_DADOS)/gold
	cd transform && uv run dbt deps
	cd transform && uv run dbt build --target ci --selector ci_mes_antigo --vars '{mes_referencia: 2026-08}'
	cd transform && uv run dbt test --target ci --selector ci_resumo_mes_antigo --vars '{mes_referencia: 2026-08}'
	cd transform && uv run dbt source freshness --target ci
	cd transform && uv run dbt build --target ci
	uv run pytest -q tests/integration
	$(MAKE) lint

## pipeline: pipeline ponta a ponta sobre dados reais (não implementado — T28)
pipeline:
	@echo "pipeline: não implementado (tarefa T28)"
	@exit 2

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
