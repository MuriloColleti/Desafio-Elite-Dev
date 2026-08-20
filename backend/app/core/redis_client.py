"""Cliente Redis — armazena as sessões e o cache do catálogo.

O Redis aqui é infraestrutura de sessão, não de domínio: se ele cair, ninguém
perde ingresso nem reserva; as pessoas só precisam entrar de novo. Essa
separação é deliberada — nada que não possa ser reconstruído mora aqui.
"""

import redis

from app.core.config import settings

# decode_responses=True: trabalhamos com str, não bytes. O que guardamos é
# JSON de sessão e de catálogo, nunca binário.
client: redis.Redis = redis.from_url(
    settings.redis_url,
    decode_responses=True,
    socket_connect_timeout=3,
    socket_timeout=3,
    health_check_interval=30,
)


def ping() -> bool:
    """Usado pelo /health para diferenciar 'Redis fora' de 'banco fora'."""
    try:
        return bool(client.ping())
    except redis.RedisError:
        return False
