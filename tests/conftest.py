"""Configuração comum a todos os testes (unit e integração)."""

import pytest

from rfb_pipeline import configuracao


@pytest.fixture(autouse=True)
def _sem_dotenv(monkeypatch: pytest.MonkeyPatch) -> None:
    """Testes herméticos: `carregar_configuracao()` nunca lê o `.env` do desenvolvedor.

    O `.env` pode ter segredos reais (ex.: `MOTHERDUCK_TOKEN`); sem isto, um teste que apaga as
    variáveis do ambiente e chama a CLI as recarregaria do `.env` e publicaria no MotherDuck real.
    """
    monkeypatch.setattr(configuracao, "load_dotenv", lambda *args, **kwargs: False)
