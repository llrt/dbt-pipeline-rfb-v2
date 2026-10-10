# Triagem da RSEM (líder, 2026-10-10)

Veredito da RSEM ([RSEM.md](RSEM.md)): **aprovável com ressalvas**. São 0 bloqueantes, 4 importantes, 6 menores e 2
sugestões. Das 8 mutações, 7 sobreviveram (M1–M7). Os 3 comentários do Greptile estão resolvidos.

Todos os achados foram aceitos. As correções ficam com o lote **FRSEM**, um agente novo (Opus, esforço médio, porque
as métricas são críticas), no mesmo branch do PR #1. A exceção é o `STATE.md`, que é registro do líder.

| Achado | Decisão | Lote | Resolvido em |
|---|---|---|---|
| **RSEM-01** fotografia mensal devolve mês antigo quando o filtro esvazia o último mês | Limitação do MetricFlow, que calcula o `MAX(mes)` depois do filtro. Corrigir a promessa na doc (B3, A6, ADR-0018): "último mês **em que o recorte tem linhas**". Guiar o estoque atual por `metric_time__month` ou por um filtro de mês, e preferir `qtd_ativos` a `qtd_estabelecimentos` + `ATIVA`. Teste de integração que **documenta o comportamento** com um recorte que só existe no penúltimo mês: linha nova na fixture, fora do caso de Fundão | FRSEM | |
| **RSEM-02** 15 de 25 métricas sem comparação; M1–M4, M6 e M7 sobrevivem | Estender a comparação com SQL a **todas** as métricas do resumo (mês, ano e sem tempo, com os numeradores dos ratios) e às taxas e contagens de 1, 3 e 5 anos; testar `variacao_mensal_ativos_pct`. As 6 mutações devem morrer. Corrigir a B6 para listar só o que está provado | FRSEM | |
| **RSEM-03** "sobrevivente" = "ainda ativo" na doc e no TTL | Usar a definição do mart ("ativos hoje ou encerrados depois do aniversário de N anos") na A6, no TTL e nas `description` de `sobreviventes_*a`/`taxa_sobrevivencia_*a` | FRSEM | |
| **RSEM-04** inaptidões em lote e ano/mês parciais distorcem `encerramentos`/saldo | Avisar na A3/B7, com o exemplo do dado real. Nova métrica **`baixas`** (só BAIXADA, mesma regra de data válida), mapeada na ontologia e testada. A `description` da saved query passa a dizer que o último ano é parcial | FRSEM | |
| **RSEM-05** opção pelo Simples alterada pela CGSN 190/2026 | Manter a regra vigente com a ressalva da CGSN 190/2026, conferida na fonte primária. Só citar a CGSN 194/2026 se for confirmada na fonte | FRSEM | |
| **RSEM-06** definição de MEI incompleta; 213-5 sem fonte; MEI com filial | Citar o § 1º completo (LC 188/2021). Natureza 213-5 vira "observação do projeto no dado real (99,99 %; 1.238 exceções)". Registrar as 3.749 filiais de MEI e o efeito em `qtd_ativos_mei` | FRSEM | |
| **RSEM-07** "inscrição da entidade = matriz" sem base no art. 9º; faculdades lidas como automáticas | Marcar a frase como leitura do projeto (art. 4º, § 1º, e art. 9º). Trocar "quando ocorre" por "pode ocorrer quando" na tabela e no diagrama | FRSEM | |
| **RSEM-08** ontologia: o teste só prova existência; `dcterms:source` não declarada; `OpcaoSimplesNacional` mistura registro e opção | Declarar `dcterms:source` como `owl:AnnotationProperty`. Ajustar o comentário de `OpcaoSimplesNacional`; separar a classe só se ficar mais simples. Teste de **afinidade conceito × modelo semântico**: M5 deve morrer | FRSEM | |
| **RSEM-09** equivalência DAX × MetricFlow só no grão mensal | Dizer isso na B3 e no `POWER_BI.md`. Num grão maior, filtrar um mês. Sem DAX novo não testado | FRSEM | |
| **RSEM-10** `verificar_doc_semantica.py` fora do CI; números da prosa não conferidos | A parte estática entra num teste de integração (roda no `make ci`). Números da prosa: trocar por "veja a saída do comando" onde não forem essenciais; os que ficarem são conferidos por teste | FRSEM | |
| **RSEM-11** time spine expõe 1899-12-30/31 como `metric_time` | Registrar no ADR-0018 e na B7. Spine próprio só se um dia incomodar | FRSEM | |
| **RSEM-12a** dependências sem limite | `dbt-metricflow>=0.15,<0.16` e `rdflib>=7,<8` | FRSEM | |
| **RSEM-12b** "não verificou uma matriz por básico" | Trocar pelo número verificado pela RSEM (70.085.592 matrizes para 70.085.591 básicos, 1 exceção, `08314885`) | FRSEM | |
| **RSEM-12c** `rfbo:codigoRfb` não uniforme | Uniformizar com o leiaute (`01`, `08`) | FRSEM | |
| **RSEM-12d** STATE AD-037 com "7 testes" | Atualizar no fechamento do PR | líder | |
| **RSEM-12e** dbt v2 não reproduzido | Já verificado pelo líder com o dbt 2.0.8 num ambiente isolado: só resta o erro conhecido do `options`, ADR-0017. Sem ação | — | — |
