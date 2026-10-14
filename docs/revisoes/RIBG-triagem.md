# Triagem da RIBG (líder, 2026-10-14)

Veredito da RIBG ([RIBG.md](RIBG.md)): **não aprovável como minor até corrigir o RIBG-01, que é bloqueante.** O resto
é aprovável com ressalvas. São 1 bloqueante, 1 alto, 1 médio e 8 baixos.
- A RIBG fez 13 mutações próprias: 11 foram reprovadas pelos testes e 2 sobreviveram (P4 e D4).
- No dado real tudo confere: renda, polo, mart, RN-30, as linhas dos cenários e a exclusão de MEI do CEMPRE.

Todos os achados foram aceitos. As correções ficam com o lote **FIBG**, um agente novo (Opus, esforço médio, o mesmo
nível dos lotes IBG1 e IBG2), no branch `feat/enriquecimento-ibge`. O FIBG também faz o commit da versão 1.4.0.

| Achado | Decisão | Lote | Resolvido em |
|---|---|---|---|
| **RIBG-01** `RAIZ_DADOS` da v1.3 sem `raw/ibge/` quebra `rfb pipeline --sem-ingestao`, `rfb atualizar` sem mês novo e `rfb regras` | **Bloqueante para o minor.** Garantir o raw IBGE (vazio, com esquema, se não existir) antes de **toda** chamada ao dbt e no `rfb regras`, sem rede. Teste de integração com uma cópia sem `raw/ibge` para `pipeline --sem-ingestao`, `atualizar` no-op e `regras` | FIBG | |
| **RIBG-02** o mensal passa a depender do IBGE, sem como desligar; 1–2 h do CEMPRE no primeiro `atualizar` | (a) **Falha do IBGE não derruba o mês**: aviso, mantém o raw anterior (ou vazio) e registra a falha no manifesto IBGE; a RFB e a BD seguem. (b) Opção nova **`--sem-ibge`** (aditiva) em ingerir, pipeline e atualizar, que pula a rede do IBGE e garante o raw vazio. (c) A sonda de ano novo do CEMPRE roda no máximo uma vez a cada 30 dias, com a data da última sonda no manifesto IBGE, ou sempre com `--renovar-ibge`. (d) `OPERACAO.md` e as notas da release avisam do primeiro download longo e de como adiá-lo | FIBG | |
| **RIBG-03** polo em outra UF some do caso; o relatório diz "não tem polo" (314 de 5.503 municípios) | O polo é sempre mostrado, com a UF dele; `ativos_no_polo` vale também para polo em outra UF. Teste com polo interestadual nas fixtures | FIBG | |
| **RIBG-04** `atualizar --renovar-ibge` ignorado sem mês novo | Sem mês novo, `--renovar-ibge` renova só o IBGE e reconstrói o que depende dele. Teste | FIBG | |
| **RIBG-05** mutações P4 (sem 429 na retentativa) e D4 (renda da UF por `avg` simples) sobreviveram; faltam testes de polo interestadual e de upgrade | Testes que reprovem P4 e D4, além dos testes do 01 e do 03 | FIBG | |
| **RIBG-06** docs dizem que a renda tem `...` nas medianas; a 10295 real não tem símbolos | Corrigir CAMADA_SEMANTICA e o dicionário: o `...` é só um caso da fixture para provar o tratamento | FIBG | |
| **RIBG-07** ADR-0022 cita a redação revogada do art. 4º do Decreto 8.777 | Citar a redação vigente (Decreto 9.903/2019), conferida na fonte | FIBG | |
| **RIBG-08** `POWER_BI.md` sem a ponte e o mart novos nem a linha toda NULL | Atualizar | FIBG | |
| **RIBG-09** classes 70.10-7 e 47.90-3 do CEMPRE fora da `dim_cnae` | Descrição da classe pelo nome do CEMPRE quando faltar na `dim_cnae`; a RN-30 avalia só classes que existem na `dim_cnae`, com nota no catálogo | FIBG | |
| **RIBG-10** saved query do polo promete o % no polo e não agrupa por ele | Agrupar pelo % ou ajustar a descrição, o que for possível no MetricFlow | FIBG | |
| **RIBG-11** WARN permanente de `destino_compras_soma_100` no CI | Completar as fixtures REGIC para as origens somarem 100, sem mudar o caso de Fundão | FIBG | |
