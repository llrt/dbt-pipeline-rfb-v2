# Triagem da RGQ (líder, 2026-10-15)

Veredito da RGQ ([RGQ.md](RGQ.md)): **aprovável como minor (v1.4.1), com ressalvas.**
- São 1 achado alto, 3 médios e 6 baixos.
- O teste de uso real ficou em 8 certas e 2 parciais em 10 perguntas livres.
- Das 11 mutações, 6 sobreviveram.

Como o objetivo do pedido é o uso por um agente de outro projeto, **todos os achados entram antes do merge**,
inclusive o RGQ-01 e o RGQ-02, que a RGQ recomendou corrigir antes da entrega do material. As correções ficam com o
lote **FGQ**, um agente novo (Opus, esforço médio, o mesmo nível do lote GQ), no branch `docs/retro-custos-v1.4.0`.

| Achado | Decisão | Lote | Resolvido em |
|---|---|---|---|
| **RGQ-01** a semântica não roda no ambiente prometido ao agente; o `mf query` abre o warehouse para escrita; as 20 golden queries semânticas não têm SQL | Cada golden query semântica ganha o campo **`sql`**: o SQL que o MetricFlow gera (`mf query --explain`), normalizado como o das analyses (`main.x`). O CI **executa esse SQL** com conexão `read_only` e compara com a resposta esperada. O guia muda a regra: o agente usa o SQL do catálogo; o `mf query` é só para quem tem o repositório | FGQ | `1ed6c39` |
| **RGQ-02** não há lista de métricas e dimensões nem das colunas das relações | O catálogo e o guia ganham, **gerados**: as métricas (nome, descrição, tipo, medida e filtro), as dimensões por entidade com o nome qualificado (`municipio__nome_municipio`) e as relações consultáveis com colunas e tipos. O §8 do procedimento manda consultar `information_schema`/`describe` antes de escrever SQL novo | FGQ | `54da5e1` |
| **RGQ-03** 8 golden queries perguntam por "empresas" e contam estabelecimentos | Corrigir as perguntas ou o SQL para casar com o glossário (empresa = raiz; estabelecimento = CNPJ completo). Quando a pergunta for ambígua, a armadilha diz isso. Teste: pergunta com "empresa" exige `cnpj_raiz` distinto ou uma armadilha explícita | FGQ | `24512d9` |
| **RGQ-04** a guarda de privacidade só olha nome de coluna e valor de texto | Testes: coluna de saída derivada de coluna proibida, mesmo com alias (análise do SQL compilado, `min(nome) as titular`), e CNPJ/raiz numéricos detectados pelo tipo e pelo nome (`cnpj*`, `*_raiz`). M1 e M2 têm de morrer. No guia, uma **checagem obrigatória pós-execução** para o agente, com a lista de colunas proibidas e os padrões de valor | FGQ | `46d12d9` |
| **RGQ-05** "salário" falta no glossário; `tem_sigilo` é da linha; salário agregado por UF sem aviso | Glossário com salário (CEMPRE, mil reais, sigilo); a armadilha de agregação com sigilo vira subestimativa declarada | FGQ | `3e872cf`, `f9c78f9` |
| **RGQ-06** busca de CNAE pela descrição sem volume | A golden query de busca de CNAE traz o volume de ativos por subclasse e marca as subclasses sem uso. Armadilha "padaria": fabricação (1091102) × varejo (4721101). Glossário com o procedimento "mostrar candidatos e perguntar" | FGQ | `b221430`, `f9c78f9` |
| **RGQ-07** SQL e ids citados no texto escrito à mão do guia não são testados | Teste: todo `gq_*` citado no guia e nas armadilhas existe, e os blocos SQL de exemplo do guia compilam e executam nas fixtures. M8, M9 e M10 têm de morrer | FGQ | `7fade17` |
| **RGQ-08** falta o conceito de perfil do município; filtro de UF não testado (só Fundão nas fixtures) | Conceito novo `perfil_municipio` (população BD × Censo, PIB, VA, Censo) na matriz, com golden queries no core e na semântica, se houver métrica. Uma golden query com município homônimo em outra UF nas fixtures (já existe Água Branca), para M4 morrer | FGQ | `a81fc59`, `f9c78f9` |
| **RGQ-09** MotherDuck: o "token de leitura" é vago | Usar o nome oficial (Read Scaling token), a sintaxe `ATTACH 'md:<banco>'` + `USE` e a nota de que `read_only` não se aplica ao `md:`, com link para a doc oficial | FGQ | `12f76c0` |
| **RGQ-10** três cabeçalhos inconsistentes | Corrigir os três | FGQ | `f6ad2de` |
