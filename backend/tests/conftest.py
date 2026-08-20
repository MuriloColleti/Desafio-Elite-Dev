"""Fixtures dos testes.

As sessões e o cache de catálogo são testados contra um Redis falso, em
memória: o comportamento que importa (TTL, revogação, expiração absoluta,
invalidação de cache) é do nosso código, não do servidor Redis — então o teste
não precisa de infraestrutura para provar a regra.
"""

import fakeredis
import pytest


@pytest.fixture
def redis_fake(monkeypatch):
    """Substitui o cliente Redis por um em memória, em todos os módulos.

    Cada módulo que usa Redis faz `from app.core.redis_client import client`, o
    que liga o nome no momento do import. Trocar só em `redis_client` não
    alcança esses módulos — eles seguiriam usando o Redis real, e o teste
    passaria (ou falharia) por motivo errado.
    """
    fake = fakeredis.FakeRedis(decode_responses=True)

    import app.core.redis_client as redis_client
    import app.services.catalog as catalog
    import app.services.session_store as session_store

    monkeypatch.setattr(redis_client, "client", fake)
    monkeypatch.setattr(session_store, "client", fake)
    monkeypatch.setattr(catalog, "client", fake)

    return fake
