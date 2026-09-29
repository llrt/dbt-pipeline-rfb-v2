"""Hierarquia de erros do pacote rfb_pipeline."""

from __future__ import annotations


class ErroIngestao(Exception):
    """Erro base de todo o pacote."""


class MesInexistenteErro(ErroIngestao):
    """O mês solicitado não existe no compartilhamento WebDAV da RFB."""

    def __init__(self, mes: str, disponiveis: list[str]) -> None:
        self.mes = mes
        self.disponiveis = disponiveis
        disponiveis_str = ", ".join(disponiveis) if disponiveis else "nenhum mês disponível"
        super().__init__(f"mês {mes!r} não encontrado; meses disponíveis: {disponiveis_str}")


class MesIncompletoErro(ErroIngestao):
    """A pasta do mês não tem todos os arquivos esperados (a RFB publica ao longo de dias)."""

    def __init__(self, mes: str, faltantes: list[str]) -> None:
        self.mes = mes
        self.faltantes = faltantes
        super().__init__(
            f"mês {mes!r} incompleto; faltam {len(faltantes)} arquivo(s): "
            + ", ".join(faltantes)
            + " (use --permitir-incompleto para ingerir mesmo assim)"
        )


class ExecucaoEmAndamentoErro(ErroIngestao):
    """Outra execução de `rfb ingerir` detém a trava de `DATA_ROOT/_estado/rfb.lock`."""

    def __init__(self, trava: str) -> None:
        self.trava = trava
        super().__init__(f"execução em andamento (trava {trava} ocupada); tente novamente depois")


class BaixaArquivoErro(ErroIngestao):
    """Falha ao baixar um arquivo, após esgotar as tentativas configuradas."""

    def __init__(self, arquivo: str, motivo: str) -> None:
        self.arquivo = arquivo
        super().__init__(f"falha ao baixar {arquivo}: {motivo}")


class WebDAVIndisponivelErro(ErroIngestao):
    """Falha de rede/HTTP ao consultar o WebDAV (listagem), após esgotar as tentativas."""

    def __init__(self, url: str, motivo: str) -> None:
        self.url = url
        super().__init__(f"WebDAV indisponível em {url}: {motivo}")


class TamanhoDivergenteErro(BaixaArquivoErro):
    """O tamanho baixado não confere com o tamanho anunciado pelo servidor."""

    def __init__(self, arquivo: str, esperado: int, obtido: int) -> None:
        self.esperado = esperado
        self.obtido = obtido
        super().__init__(arquivo, f"tamanho divergente (esperado {esperado}, obtido {obtido})")


class HostNaoPermitidoErro(ErroIngestao):
    """O host de destino não está na allowlist configurada."""

    def __init__(self, host: str, hosts_permitidos: tuple[str, ...]) -> None:
        self.host = host
        self.hosts_permitidos = hosts_permitidos
        super().__init__(f"host {host!r} não está na allowlist {hosts_permitidos!r}")


class ZipInseguroErro(ErroIngestao):
    """Entrada de zip com caminho absoluto ou que escapa do diretório de extração (zip-slip)."""

    def __init__(self, caminho_zip: str, entrada: str) -> None:
        self.caminho_zip = caminho_zip
        self.entrada = entrada
        super().__init__(f"zip {caminho_zip}: entrada insegura {entrada!r} recusada")


class ZipCorrompidoErro(ErroIngestao):
    """Zip ilegível ou com CRC inválido."""

    def __init__(self, caminho_zip: str, motivo: str) -> None:
        self.caminho_zip = caminho_zip
        super().__init__(f"zip corrompido {caminho_zip}: {motivo}")


class TaxaRejeitoExcedidaErro(ErroIngestao):
    """A taxa de linhas rejeitadas pelo analisador CSV excedeu o limiar configurado."""

    def __init__(self, entidade: str, taxa: float, limiar: float, caminho_rejeitos: str) -> None:
        self.entidade = entidade
        self.taxa = taxa
        self.limiar = limiar
        self.caminho_rejeitos = caminho_rejeitos
        super().__init__(
            f"{entidade}: taxa de rejeito {taxa:.6%} excede o limiar {limiar:.6%}; "
            f"rejeitos em {caminho_rejeitos}"
        )


class ConversaoErro(ErroIngestao):
    """Falha do DuckDB ao converter um arquivo para Parquet."""

    def __init__(self, arquivo: str, motivo: str) -> None:
        self.arquivo = arquivo
        super().__init__(f"falha ao converter {arquivo}: {motivo}")


class EntidadeVaziaErro(ErroIngestao):
    """A conversão de uma entidade produziu 0 linhas no total; nada é publicado."""

    def __init__(self, entidade: str, arquivos: list[str]) -> None:
        self.entidade = entidade
        self.arquivos = arquivos
        super().__init__(
            f"{entidade}: conversão produziu 0 linhas (arquivos: {', '.join(arquivos) or '-'}); "
            "a partição anterior foi mantida"
        )


class CredenciaisS3FaltandoErro(ErroIngestao):
    """`DATA_ROOT` é `s3://` mas faltam variáveis de ambiente obrigatórias."""

    def __init__(self, faltando: list[str]) -> None:
        self.faltando = faltando
        super().__init__(
            "DATA_ROOT é s3:// mas faltam variáveis de ambiente: " + ", ".join(faltando)
        )


class ConfiguracaoInvalidaErro(ErroIngestao):
    """Variável de ambiente com valor que não pode ser interpretado."""

    def __init__(self, variavel: str, valor: str, esperado: str) -> None:
        self.variavel = variavel
        super().__init__(f"variável {variavel}={valor!r} inválida (esperado {esperado})")
