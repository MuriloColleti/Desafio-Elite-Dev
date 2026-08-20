"""Configuração da aplicação, lida do ambiente."""

from functools import lru_cache

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # --- Ingresso ---
    # Segredo do HMAC do QR. Diferente da sessão: aqui o código viaja fora do
    # nosso controle (impresso, print de tela), então precisa ser verificável
    # por assinatura.
    ticket_hmac_secret: str = "trocar-em-producao"

    # --- Regras de negócio ---
    reservation_ttl_minutes: int = 10
    payment_decline_rate: float = 0.0

    # --- APIs externas ---
    tmdb_api_key: str | None = None
    ticketmaster_api_key: str | None = None
    catalog_cache_ttl_seconds: int = 60 * 15

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
