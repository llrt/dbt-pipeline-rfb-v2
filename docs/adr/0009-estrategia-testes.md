# ADR-0009 — Estratégia de testes em camadas e severidades

**Decisão.**
1. **pytest unit** — funções da ingestão (parsing, manifesto, cliente WebDAV com `httpx.MockTransport`, storage com moto).
2. **pytest integração** — `make ci`: fixtures → ingestão → `dbt build --target ci` → asserções sobre o gold com
   os valores esperados definidos na spec (não derivados da implementação).
3. **dbt data tests** — genéricos (`unique`, `not_null`, `accepted_values`, `relationships`, `dbt_utils`,
   `dbt_expectations`), genéricos próprios (CNPJ com DV válido, data não futura, reconciliação de contagens) e
   singulares (paridade, invariantes das análises).
4. **dbt unit tests** — regras de transformação com `given/expect` (porte, situação, nome, idade, datas).
5. **Contratos** — marts `original` e `core` com `contract.enforced`.
6. **Freshness** — fontes RFB (`_ingerido_em`): warn 35 dias, error 65 dias.

Severidade: estrutura/semântica (PK, contratos, relacionamentos do core, paridade, reconciliação do agregado)
= `error`; anomalias de conteúdo da fonte (DV inválido, descartes do inner join, municípios sem par) =
`warn` com `error_if` por limiar. `store_failures` ligado para testes `warn`.
