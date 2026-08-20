"""Fixtures dos testes.

As sessões e o cache de catálogo são testados contra um Redis falso, em
memória: o comportamento que importa (TTL, revogação, expiração absoluta,
invalidação de cache) é do nosso código, não do servidor Redis — então o teste
não precisa de infraestrutura para provar a regra.

Os testes de fluxo (`test_api_flow.py`) e de concorrência exigem Postgres real,
porque o que provam é justamente o comportamento do banco.
"""

import os

import fakeredis
import pytest

TEST_DB_URL = os.getenv("TEST_DATABASE_URL")

requer_postgres = pytest.mark.skipif(
    not TEST_DB_URL,
    reason="TEST_DATABASE_URL não definida — precisa de Postgres real",
)


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


@pytest.fixture
def argon2_rapido(monkeypatch):
    """Reduz o custo do Argon2 nos testes.

    Argon2 é lento por design — é isso que o torna bom para senha. Mas o seed
    roda a cada teste e hasheia quatro usuários, o que domina o tempo da suíte.

    Usado só pelo `app_semeado`: `test_security.py` exercita o hasher real, com
    os parâmetros de produção, porque ali o que está sob teste é o próprio hash.
    """
    from argon2 import PasswordHasher

    import app.core.security as security

    monkeypatch.setattr(
        security, "_hasher", PasswordHasher(time_cost=1, memory_cost=8, parallelism=1)
    )


@pytest.fixture
def app_semeado(redis_fake, argon2_rapido, monkeypatch):
    """App com banco semeado e clientes HTTP já autenticados por papel.

    Devolve (clientes, refs). O Redis é o falso, então as sessões destes testes
    não vazam para outros.
    """
    if not TEST_DB_URL:
        pytest.skip("precisa de Postgres real")

    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import app.core.db as core_db

    engine = create_engine(TEST_DB_URL)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(core_db, "SessionLocal", Session)

    from app.main import app
    from app.seed import limpar, povoar

    with Session() as db:
        limpar(db)
        refs = povoar(db)

    def autenticar(email: str) -> TestClient:
        c = TestClient(app, raise_server_exceptions=False)
        r = c.post("/auth/login", json={"email": email, "password": "senha123"})
        assert r.status_code == 200, f"login falhou para {email}"
        return c

    clientes = {
        "anon": TestClient(app, raise_server_exceptions=False),
        "organizador": autenticar("organizador@palco.dev"),
        "ana": autenticar("ana@palco.dev"),
        "bruno": autenticar("bruno@palco.dev"),
        "portaria": autenticar("portaria@palco.dev"),
    }

    yield clientes, refs

    engine.dispose()
