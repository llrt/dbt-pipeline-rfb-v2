# ADR-0010 — Fixtures sintéticas com respostas conhecidas

**Contexto.** Rodar o pipeline real leva dezenas de minutos e ~30 GB; não serve como gate de CI. Testes
gerados junto com a implementação tendem a espelhá-la.

**Decisão.** `scripts/gen_fixtures.py` gera, de forma determinística, zips no formato RFB (latin-1, `;`,
aspas, `\"` em razão social, campo multilinha, datas `00000000`, CNAE com zero à esquerda, capital
`1000,00`, município EXTERIOR) e csv.gz no formato BD, com um **cenário de respostas conhecidas** descrito
na spec (Fundão/ES e vizinhos). Os testes de integração verificam exatamente esses números.

**Consequências.** `make ci` roda em < 2 min sem rede. Mudanças de regra exigem atualizar a spec e o cenário juntos.
