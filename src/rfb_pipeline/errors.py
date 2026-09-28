"""Hierarquia de erros do pacote rfb_pipeline."""

from __future__ import annotations


class ErroIngestao(Exception):
    """Erro base de todo o pacote."""


class MesInexistenteError(ErroIngestao):
    """O mês solicitado não existe no compartilhamento WebDAV da RFB."""

    def __init__(self, mes: str, disponiveis: list[str]) -> None:
        self.mes = mes
        self.disponiveis = disponiveis
        disponiveis_str = ", ".join(disponiveis) if disponiveis else "nenhum mês disponível"
        super().__init__(f"mês {mes!r} não encontrado; meses disponíveis: {disponiveis_str}")


class DownloadError(ErroIngestao):
    """Falha ao baixar um arquivo, após esgotar as tentativas configuradas."""

    def __init__(self, arquivo: str, motivo: str) -> None:
        self.arquivo = arquivo
        super().__init__(f"falha ao baixar {arquivo}: {motivo}")


class TamanhoDivergenteError(DownloadError):
    """O tamanho baixado não confere com o tamanho anunciado pelo servidor."""

    def __init__(self, arquivo: str, esperado: int, obtido: int) -> None:
        self.esperado = esperado
        self.obtido = obtido
        super().__init__(arquivo, f"tamanho divergente (esperado {esperado}, obtido {obtido})")


class HostNaoPermitidoError(ErroIngestao):
    """O host de destino não está na allowlist configurada."""

    def __init__(self, host: str, hosts_permitidos: tuple[str, ...]) -> None:
        self.host = host
        self.hosts_permitidos = hosts_permitidos
        super().__init__(f"host {host!r} não está na allowlist {hosts_permitidos!r}")
