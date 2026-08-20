"""Configuração da aplicação, lida do ambiente."""

from functools import lru_cache

from pydantic import Field, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SEGREDO_PADRAO = "trocar-em-producao"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Aplicação ---
    app_name: str = "Palco"
    debug: bool = False

    # URL pública do front. Usada para montar o link de compartilhamento do
    # ingresso: sem isso o link geraria "localhost" e não abriria para ninguém.
    public_base_url: str = "http://localhost:5173"

    cors_origins_raw: str = Field(
        default="http://localhost:5173",
        alias="CORS_ORIGINS",
    )

    # --- Persistência ---
    database_url: str = "postgresql+psycopg://palco:palco@localhost:5432/palco"
    redis_url: str = "redis://localhost:6379/0"

    # --- Sessão ---
    # O session_id é um token opaco; estes valores controlam só o seu ciclo de
    # vida no Redis. Não existe segredo de assinatura de sessão porque o token
    # não carrega dado nenhum para assinar.
    session_ttl_seconds: int = 60 * 60 * 8  # 8h de inatividade
    session_absolute_ttl_seconds: int = 60 * 60 * 24 * 7  # 7 dias no máximo
    session_cookie_name: str = "palco_session"
    session_cookie_secure: bool = False  # True em produção (HTTPS)
    # "lax" em desenvolvimento (mesma origem). Em produção o front e a API
    # ficam em domínios diferentes, e aí o navegador só envia o cookie com
    # "none" — que por sua vez exige Secure, logo HTTPS.
    session_cookie_samesite: str = "lax"

    # --- Ingresso ---
    # Segredo do HMAC do QR. Diferente da sessão: aqui o código viaja fora do
    # nosso controle (impresso, print de tela), então precisa ser verificável
    # por assinatura.
    ticket_hmac_secret: str = SEGREDO_PADRAO

    # --- Regras de negócio ---
    reservation_ttl_minutes: int = 10
    payment_decline_rate: float = 0.0

    # --- APIs externas ---
    tmdb_api_key: str | None = None
    ticketmaster_api_key: str | None = None
    catalog_cache_ttl_seconds: int = 60 * 15

    @model_validator(mode="after")
    def _conferir_producao(self) -> "Settings":
        """Falha no boot se produção estiver mal configurada.

        Um `TICKET_HMAC_SECRET` previsível torna o QR forjável — qualquer pessoa
        assinaria um ingresso válido. Vale mais não subir do que subir inseguro.

        `session_cookie_secure` é o sinal de "estou em produção": ele só é
        ligado quando há HTTPS, que é justamente o cenário de deploy.
        """
        # Esta checagem vem primeiro porque vale em qualquer ambiente: o
        # navegador rejeita SameSite=None sem Secure, e a sessão simplesmente
        # não persistiria — falha silenciosa, difícil de diagnosticar.
        if self.session_cookie_samesite.lower() == "none" and not self.session_cookie_secure:
            raise ValueError("SESSION_COOKIE_SAMESITE=none exige SESSION_COOKIE_SECURE=true.")

        if not self.session_cookie_secure:
            return self

        if self.ticket_hmac_secret == SEGREDO_PADRAO:
            raise ValueError(
                "TICKET_HMAC_SECRET está com o valor padrão. Gere um segredo "
                "com `python -c \"import secrets; print(secrets.token_urlsafe(32))\"`."
            )

        return self

    @computed_field
    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins_raw.split(",") if o.strip()]

    @computed_field
    @property
    def catalog_offline(self) -> bool:
        """Sem nenhuma chave configurada, o catálogo usa as fixtures locais."""
        return not (self.tmdb_api_key or self.ticketmaster_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
