# Triagem da RDIC (líder, 2026-10-13)

Veredito da RDIC ([RDIC.md](RDIC.md)): **aprovável com ressalvas**. São 0 bloqueantes, 4 importantes, 4 menores e 3
sugestões. As 8 mutações (M1–M8) sobreviveram porque os testes provam a sincronia do dicionário, não o conteúdo. O
mapeamento do leiaute (54/54) e as colunas da Base dos Dados (88/88) conferem.

As correções ficam com o lote **FDIC**, um agente novo (Sonnet, esforço médio, o mesmo nível do lote DIC), no branch
`feat/dicionario-dados`.

| Achado | Decisão | Lote | Resolvido em |
|---|---|---|---|
| **RDIC-01** nulidade e domínio afirmados a partir de testes `warn` | Com `warn`: "em geral não (`not_null` `warn`: pode haver exceções)" e a marca `(warn)` em chave única, `relationships` e `accepted_*`. O "Como ler" explica. Teste unitário fixa o comportamento | FDIC | |
| **RDIC-02** grão da vizinhança promete unicidade | Corrigir o `meta.grao` das duas tabelas ("como publicado: pode repetir o par e trazer autopares; deduplicado em `bridge_municipio_vizinho`") | FDIC | |
| **RDIC-03** "Origem" vazia; falta linhagem de tabela | Linhas **"Lê de"** e **"Usada por"** em toda seção, tiradas de `depends_on` do manifesto. "Linhagem:" coluna a coluna nas colunas do gold que não são cópia direta (pelo menos dimensões e fatos) | FDIC | |
| **RDIC-04** valores dos códigos ausentes; formato raw × gold | Imprimir as linhas das seeds na seção de cada uma. Domínio nas colunas `codigo_*`/`rotulo_*` das dimensões semeadas. Corrigir a descrição de `codigo_situacao_cadastral` ("sem zero à esquerda") | FDIC | |
| **RDIC-05** nota "sem par → `-1`" errada em 3 colunas | A nota só aparece quando a coluna de fato recebe `-1`: `meta.membro_desconhecido: false` ou descrição explícita nas 3 colunas | FDIC | |
| **RDIC-06** PK de `basedosdados.municipio` contradiz o grão | Preferir as colunas únicas testadas que estão no `meta.grao`; sem elas, "não testada", e o `unique` `warn` vai em "Outras chaves únicas (warn)" | FDIC | |
| **RDIC-07** saída depende da ordem do manifesto | Ordenar os testes por `unique_id`; teste unitário com o manifesto embaralhado | FDIC | |
| **RDIC-08** testes provam sincronia, não correção | Colunas das fontes no teste de completude. Teste de `meta`: toda coluna de dado RFB, salvo `motivos`, tem `campo_leiaute`, na ordem de `esquemas.py`; toda `coluna_bigquery` existe no raw; toda coluna citada no `meta.grao` existe. Teste unitário do gerador com um manifesto mínimo. Ajustar o ADR-0019 ao que é provado. As mutações M1–M8 da RDIC devem morrer, ou ter a sobrevivência justificada | FDIC | |
| **RDIC-09** 12 grãos declarados sem teste de unicidade | Gerador rotula "Grão (declarado, não testado)". Os testes de unicidade (`unique_combination_of_columns`) vão para o **PR B** (regras e invariantes) | FDIC (rótulo) · PR B (testes) | |
| **RDIC-10** jargão de revisão e referências ao YAML | Reescrever as 31 descrições para o leitor do dado, sem IDs de processo nem "abaixo". Na linhagem do original, citar a tabela do projeto | FDIC | |
| **RDIC-11** navegação | `erDiagram` mermaid gerado das FKs (dimensões, fatos, pontes). FK `sk_mes_referencia` → `dim_data`. Distinguir "FK testada" de "FK da camada semântica". Explicar o "—" de `rfb.motivos` | FDIC | |
