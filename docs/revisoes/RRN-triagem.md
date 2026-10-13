# Triagem da RRN (líder, 2026-10-13)

Veredito da RRN ([RRN.md](RRN.md)): **aprovável com ressalvas**. São 0 bloqueantes, 4 importantes, 3 menores e 3
sugestões. As 10 mutações (M1–M10) sobreviveram. A RRN reexecutou 12 regras no dado real, e todas conferem com o
relatório. Das 13 afirmações conferidas nas fontes, 12 batem; a exceção é a RN-08, em que a fonte é mais forte que o
catálogo.

Todos os achados foram aceitos. As correções ficam com o lote **FRN**, um agente novo (Opus, esforço médio, o mesmo
nível do lote RN), no branch `feat/regras-negocio`.

| Achado | Decisão | Lote | Resolvido em |
|---|---|---|---|
| **RRN-01** guarda de privacidade só léxica (CNPJ formatado, raiz de 8 dígitos e alfanumérico passam) | Guarda em duas camadas. (1) As colunas de quebra só podem ter nomes de uma **lista fechada** de dimensões agregadas. (2) Os valores são recusados se casarem com CNPJ formatado ou não, raiz de 8 dígitos, CNPJ alfanumérico (14 posições `[0-9A-Z]` com DV) ou CPF formatado ou não. M7 e M8 devem morrer | FRN | |
| **RRN-02** RN-13: D+1 do extrato e opções para 2027 legítimas | Opção pelo Simples ou pelo MEI aceita até **1º de janeiro do ano seguinte** ao `_data_referencia`, pela CGSN 190/2026 e 194/2026 (conferir na fonte primária). Início, situação e situação especial aceitos até **`_data_referencia` + 1 dia**: o corte do extrato inclui o dia seguinte, como mostra a distribuição no dado real. A RN-13 documenta isso e reporta o "D+1" como quebra informativa, não como violação. Reescrever a interpretação | FRN | |
| **RRN-03** RN-05 e RN-14 contam o que o catálogo diz não ser violação | RN-05: violação = empresa MEI com **mais de um estabelecimento não baixado**; os excedentes baixados viram quebra informativa. RN-14: violação = filial **não baixada e não nula** de matriz baixada; as NULAS viram quebra informativa | FRN | |
| **RRN-04** testes só fixam o total; injeção conjunta | Fixar `avaliados` e `violacoes` **por regra** nas fixtures. Injeção **regra a regra**: cada regra detecta a própria violação injetada com o incremento esperado. As M1–M10 da RRN devem morrer, ou ter a sobrevivência justificada | FRN | |
| **RRN-05** interpretação da RN-09 contradita pelo dado | Reescrever com o que o dado mostra (indicador do regime em N) | FRN | |
| **RRN-06** RN-20 e RN-06 com interpretação genérica | RN-20 com quebra por natureza jurídica. A interpretação cita os consórcios públicos (1210, 82 %) e, na RN-06, a exclusão do Simples já vigente (467 de 469) | FRN | |
| **RRN-07** interpretação preservada sem o mês | Marcador com o mês (`Interpretação de AAAA-MM`). Quando o mês muda, a interpretação antiga passa para "Interpretação anterior (AAAA-MM)" e o comando avisa na saída que ela precisa ser revisada. Teste | FRN | |
| **RRN-08** regras que faltam | Novas regras, cada uma com a fonte conferida pelo lote: (a) opção pelo Simples ≥ 1º/7/2007 (LC 123, art. 88), legal; (b) opção pelo MEI ≥ 1º/7/2009, legal se a LC 128/2008 for confirmada na fonte, senão coerência; (c) filial não começa atividade depois da baixa, inaptidão ou nulidade da matriz (IN 2.119, art. 21, IV), coerência, porque início de atividade não é inscrição; (d) opção não antecede o início de atividade da matriz, **observação**, para não repetir o falso positivo da RN-13; (e) **"MEI não é sociedade"**, legal (LC 123, art. 18-A, § 1º), com as naturezas de sociedade definidas pela tabela CONCLA. A RN-08 (213-5) continua observação | FRN | |
| **RRN-09** `rfb relatorio` compila as analyses de regras | Excluir `path:analyses/regras_negocio` da compilação do estudo de caso | FRN | |
| **RRN-10** RN-08 rotula "NÃO INFORMADA" um código sem descrição | `coalesce(codigo, '—') \|\| ' ' \|\| coalesce(descricao, '(fora do domínio)')` | FRN | |
