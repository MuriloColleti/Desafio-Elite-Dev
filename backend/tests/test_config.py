"""Configuração — a validação que impede subir produção insegura.

O erro que estes testes evitam é silencioso e grave: subir com o segredo do HMAC
padrão. A aplicação funcionaria normalmente, e qualquer pessoa que lesse o
repositório poderia assinar um ingresso válido.
"""

import pytest

from app.core.config import SEGREDO_PADRAO, Settings


def _config(**kwargs) -> Settings:
    """Settings ignorando o .env local, para o teste não depender da máquina."""
    return Settings(_env_file=None, **kwargs)


# --- Desenvolvimento ---


def test_dev_sobe_com_os_padroes():
    """Rodar local não pode exigir cerimônia de configuração."""
    cfg = _config()

    assert cfg.ticket_hmac_secret == SEGREDO_PADRAO
    assert cfg.session_cookie_secure is False
    assert cfg.session_cookie_samesite == "lax"


# --- Produção ---


def test_producao_recusa_o_segredo_padrao():
    """Segredo previsível = QR forjável. Melhor não subir."""
    with pytest.raises(ValueError, match="TICKET_HMAC_SECRET"):
        _config(session_cookie_secure=True)


def test_producao_sobe_com_segredo_proprio():
    cfg = _config(
        session_cookie_secure=True,
        ticket_hmac_secret="um-segredo-longo-e-aleatorio-de-verdade",
        session_cookie_samesite="none",
    )

    assert cfg.session_cookie_samesite == "none"


def test_samesite_none_exige_cookie_secure():
    """O navegador rejeita SameSite=None sem Secure — falharia em runtime.

    Falhar no boot é melhor: o erro aparece no log do deploy, não como sessão
    que não persiste sem explicação.
    """
    with pytest.raises(ValueError, match="SESSION_COOKIE_SECURE"):
        _config(session_cookie_secure=False, session_cookie_samesite="none")


# --- CORS ---


def test_cors_aceita_varias_origens():
    """Produção costuma ter o domínio da Vercel e o de preview."""
    cfg = _config(CORS_ORIGINS="https://a.vercel.app,https://b.vercel.app")

    assert cfg.cors_origins == ["https://a.vercel.app", "https://b.vercel.app"]


def test_cors_ignora_espacos_e_vazios():
    cfg = _config(CORS_ORIGINS=" https://a.app , , https://b.app ")

    assert cfg.cors_origins == ["https://a.app", "https://b.app"]


# --- Catálogo ---


def test_sem_chave_o_catalogo_fica_offline():
    """É o que permite percorrer o fluxo sem cadastrar chave em serviço nenhum."""
    assert _config().catalog_offline is True


@pytest.mark.parametrize(
    "chaves",
    [
        {"tmdb_api_key": "x"},
        {"ticketmaster_api_key": "y"},
        {"tmdb_api_key": "x", "ticketmaster_api_key": "y"},
    ],
)
def test_uma_chave_basta_para_sair_do_offline(chaves):
    assert _config(**chaves).catalog_offline is False
