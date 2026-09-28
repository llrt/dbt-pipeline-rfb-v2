# ADR-0003 — Nova fonte RFB (WebDAV) e mês de referência

**Contexto.** A URL do original (`arquivos.receitafederal.gov.br/dados/cnpj/dados_abertos_cnpj/2025-02/`)
retorna 404. Os dados agora estão num compartilhamento Nextcloud público acessível por WebDAV
(`/public.php/webdav/`, token `YggdBLfdninEJX9`), com pastas mensais; em 2026-09-28 o mais recente é
`2026-09` (Empresas ≈1,4 GB, Estabelecimentos ≈5,4 GB, Simples ≈0,3 GB zipados). O mês 2025-02 não está
disponível.

**Decisão.** Cliente WebDAV (`PROPFIND` para listar, `GET` para baixar). Mês padrão = último mês listado
(detecção automática), sobrescrevível por `--mes`. Referência do projeto: **2026-09**.

**Consequências.** Os números não batem com os do original (dados de 19 meses depois). A paridade
verificada é **lógica** (mesmas regras sobre os mesmos dados — ver ADR-0005). URL e token ficam em config.
