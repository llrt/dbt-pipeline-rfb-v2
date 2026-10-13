# ADR-0020 — Regras de negócio verificadas fora do build, com relatório próprio

**Contexto.** O usuário pediu (2026-10-13) que o projeto documente as regras e invariantes de negócio do cadastro
CNPJ (CNAE principal e secundários, MEI com um único estabelecimento, "empresa ativa não tem data de
encerramento"…), crie checks delas em `analyses/` e relate as inconsistências num relatório próprio, **sem falhar o
build**. Os testes de dados do dbt já cobrem chaves e domínios e derrubam ou avisam no `dbt build`; uma regra de
negócio violada pelo cadastro real (3.749 filiais de MEI, RSEM-06) não é motivo para parar a atualização mensal.
Também ficaram 12 grãos declarados sem teste (RDIC-09).

**Decisão.**

- Catálogo [`docs/REGRAS_NEGOCIO.md`](../REGRAS_NEGOCIO.md): uma seção `RN-xx` por regra, com enunciado, tipo
  (legal, leiaute/cadastro, estrutural, coerência do projeto), fonte primária conferida ou "regra do projeto",
  dados, conceito, leitura de uma violação e a analysis. As regras que o cadastro não expressa diretamente são
  traduzidas, e a tradução é documentada (ex.: "ativa sem data de encerramento" vira motivo, data e situação).
- Um check por regra em `transform/analyses/regras_negocio/rn_<nn>_<descricao>.sql`. Analyses não rodam no
  `dbt build`: os checks não derrubam nem atrasam o pipeline.
- Saída padronizada: `regra`, `avaliados`, `violacoes` e, opcionalmente, quebras agregadas de uma lista fechada.
  Só contagens ([ADR-0008](0008-minimizacao-dados-pessoais.md)): o `rfb regras` recusa outra coluna e qualquer valor
  que pareça identificador depois de tirar a máscara (8 ou mais dígitos: CNPJ básico, CPF, CNPJ; ou CNPJ
  alfanumérico de 14 posições). A guarda é a barreira entre um erro de SQL e um relatório versionado (RRN-01).
- `rfb regras` / `make regras` compila as analyses, executa-as no warehouse de `RAIZ_DADOS` **somente leitura** e
  escreve `docs/RELATORIO_REGRAS_NEGOCIO.md` (ou `--saida`). **Sai com 0 mesmo com violações**; falha só em erro de
  execução, inclusive desencontro entre o catálogo e as analyses. A seção "Interpretação de AAAA-MM" do relatório é
  escrita à mão e preservada quando ele é regenerado no mesmo mês; em mês novo, vira "Interpretação anterior" e o
  comando avisa que ela precisa ser revista (RRN-07).
- Dois relatórios: o do `make ci`, sobre as fixtures, vai para `.tmp/ci/` e não é versionado; o versionado é o do
  dado real, gerado sobre uma cópia do warehouse.
- Os grãos sem teste da RDIC-09 entram como regras estruturais (RN-22 a RN-24), não como testes do build.

**Consequências.** Uma regra nova é um arquivo SQL e uma seção no catálogo; o teste de correspondência falha se um
existir sem o outro. Os testes de integração conferem o universo e as violações de cada regra nas fixtures e, numa
cópia nova do warehouse por caso, o delta exato por quebra de cada violação ou caso de borda injetado (RRN-04). O relatório real precisa ser regenerado a
cada mês, à mão (`make regras`), e a interpretação revista: os números mudam, a leitura pode mudar.
