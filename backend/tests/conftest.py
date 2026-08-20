"""Fixtures dos testes.

As sessões são testadas contra um Redis falso, em memória: o comportamento que
importa (TTL, revogação, expiração absoluta) é do nosso código, não do servidor
Redis — então o teste não precisa de infraestrutura para provar a regra.
"""

import fakeredis
import pytest


@pytest.fixture
def redis_fake(monkeypatch):
    """Substitui o cliente Redis global por um em memória."""
    fake = fakeredis.FakeRedis(decode_responses=True)

    import app.core.redis_client as redis_client
    import app.services.session_store as session_store

    monkeypatch.setattr(redis_client, "client", fake)
    monkeypatch.setattr(session_store, "client", fake)

    return fake
