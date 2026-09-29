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


class MesIncompletoError(ErroIngestao):
    """A pasta do mês não tem todos os arquivos esperados (a RFB publica ao longo de dias)."""

    def __init__(self, mes: str, faltantes: list[str]) -> None:
        self.mes = mes
        self.faltantes = faltantes
        super().__init__(
            f"mês {mes!r} incompleto; faltam {len(faltantes)} arquivo(s): "
            + ", ".join(faltantes)
            + " (use --permitir-incompleto para ingerir mesmo assim)"
        )


class ExecucaoEmAndamentoError(ErroIngestao):
    """Outra execução de `rfb ingest` detém o lock de `DATA_ROOT/_estado/rfb.lock`."""

    def __init__(self, lock: str) -> None:
        self.lock = lock
        super().__init__(f"execução em andamento (lock {lock} ocupado); tente novamente depois")


class DownloadError(ErroIngestao):
    """Falha ao baixar um arquivo, após esgotar as tentativas configuradas."""

    def __init__(self, arquivo: str, motivo: str) -> None:
        self.arquivo = arquivo
        super().__init__(f"falha ao baixar {arquivo}: {motivo}")


class WebDAVIndisponivelError(ErroIngestao):
    """Falha de rede/HTTP ao consultar o WebDAV (listagem), após esgotar as tentativas."""

    def __init__(self, url: str, motivo: str) -> None:
        self.url = url
        super().__init__(f"WebDAV indisponível em {url}: {motivo}")


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


class ZipInseguroError(ErroIngestao):
    """Entrada de zip com caminho absoluto ou que escapa do diretório de extração (zip-slip)."""

    def __init__(self, zip_path: str, entrada: str) -> None:
        self.zip_path = zip_path
        self.entrada = entrada
        super().__init__(f"zip {zip_path}: entrada insegura {entrada!r} recusada")


class ZipCorrompidoError(ErroIngestao):
    """Zip ilegível ou com CRC inválido."""

    def __init__(self, zip_path: str, motivo: str) -> None:
        self.zip_path = zip_path
        super().__init__(f"zip corrompido {zip_path}: {motivo}")


class TaxaRejeitoExcedidaError(ErroIngestao):
    """A taxa de linhas rejeitadas pelo parser CSV excedeu o limiar configurado."""

    def __init__(self, entidade: str, taxa: float, limiar: float, caminho_rejeitos: str) -> None:
        self.entidade = entidade
        self.taxa = taxa
        self.limiar = limiar
        self.caminho_rejeitos = caminho_rejeitos
        super().__init__(
            f"{entidade}: taxa de rejeito {taxa:.6%} excede o limiar {limiar:.6%}; "
            f"rejeitos em {caminho_rejeitos}"
        )


class ConversaoError(ErroIngestao):
    """Falha do DuckDB ao converter um arquivo para Parquet."""

    def __init__(self, arquivo: str, motivo: str) -> None:
        self.arquivo = arquivo
        super().__init__(f"falha ao converter {arquivo}: {motivo}")


class CredenciaisS3FaltandoError(ErroIngestao):
    """`DATA_ROOT` é `s3://` mas faltam variáveis de ambiente obrigatórias."""

    def __init__(self, faltando: list[str]) -> None:
        self.faltando = faltando
        super().__init__(
            "DATA_ROOT é s3:// mas faltam variáveis de ambiente: " + ", ".join(faltando)
        )
