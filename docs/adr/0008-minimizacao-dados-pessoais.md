# ADR-0008 — Minimização de dados pessoais

**Contexto.** A base RFB é pública, mas `Socios*` traz nomes/CPFs parciais de pessoas físicas e
estabelecimentos (sobretudo MEI) trazem e-mail e telefone que frequentemente são pessoais.

**Decisão.** Não ingerir `Socios*`. O raw preserva o arquivo como publicado; o staging **descarta** `email`,
`ddd1`, `tel1`, `ddd2`, `tel2`, `ddd_fax`, `fax`. Nenhum modelo a jusante expõe contatos.

**Consequências.** As perguntas de negócio não dependem desses campos. Endereço (logradouro/bairro/CEP) é
mantido só no staging, não nos marts.
