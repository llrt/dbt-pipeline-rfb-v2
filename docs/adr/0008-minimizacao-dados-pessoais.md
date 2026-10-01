# ADR-0008 — Minimização de dados pessoais

**Contexto.** A base RFB é pública, mas `Socios*` traz nomes/CPFs parciais de pessoas físicas e
estabelecimentos (sobretudo MEI) trazem e-mail e telefone que frequentemente são pessoais.

**Decisão.** Não ingerir `Socios*`. O raw preserva o arquivo como publicado; o staging **descarta** `email`,
`ddd1`, `tel1`, `ddd2`, `tel2`, `ddd_fax`, `fax`. Nenhum modelo a jusante expõe contatos.

**Consequências.** As perguntas de negócio não dependem desses campos. Endereço (logradouro/bairro/CEP) é
mantido só no staging, não nos marts.

**Emenda (2026-10-01, R4-01, decisão do usuário).** A razão social de empresários individuais e MEI termina
com o **CPF completo** do titular (12,5 M de linhas no gold real de 2026-09). Decisão: **mascarar** o sufixo de
11 dígitos (`***.***.***-**`) em todo nome exposto no gold (`bh_empresas.nome`, `mart_fornecedores_proximos.nome`
e qualquer outro), como **adaptação declarada**; a paridade com o SQL original aplica o mesmo mascaramento no
alinhamento final (como faz com o `trim`); teste `error` barra sequências de 11 dígitos com DV de CPF válido em
colunas de nome do gold. O raw continua com o dado da fonte (pública), sem sair da máquina.
