"""Serviço de catálogo: modo offline, cache e tolerância a falha.

O fan-out é testado com provedores falsos: o que importa aqui é o comportamento
do serviço quando um provedor quebra, não o cliente HTTP em si (esse está em
`test_providers.py`).
"""

import asyncio

import pytest

from app.providers.base import CatalogItem, CatalogProvider, CatalogSource
from app.services import catalog


@pytest.fixture
def sem_chaves(monkeypatch):
    """Força o modo offline (fixtures locais)."""
    monkeypatch.setattr(catalog, "_provedores", lambda: [])


# --- Modo offline ---


def test_offline_usa_fixtures(redis_fake, sem_chaves):
    from app.providers import fixtures

    itens = asyncio.run(catalog.search("", limit=99))

    # Compara com as fixtures em vez de um número fixo: o catálogo de exemplo
    # cresce, e travar a contagem só cria manutenção.
    assert len(itens) == len(fixtures.FIXTURES)


def test_offline_busca_por_titulo(redis_fake, sem_chaves):
    itens = asyncio.run(catalog.search("parasita"))
    assert [i.title for i in itens] == ["Parasita"]


def test_offline_respeita_limite(redis_fake, sem_chaves):
    assert len(asyncio.run(catalog.search("", limit=3))) == 3


def test_offline_get_por_ref(redis_fake, sem_chaves):
    item = asyncio.run(catalog.get("tmdb:movie:496243"))
    assert item is not None and item.title == "Parasita"


def test_get_com_ref_invalida(redis_fake, sem_chaves):
    assert asyncio.run(catalog.get("lixo")) is None
    assert asyncio.run(catalog.get("tmdb:movie:inexistente")) is None


# --- Provedores falsos ---


class ProvedorFalso(CatalogProvider):
    def __init__(self, source, itens, explode=False):
        self.source = source
        self._itens = itens
        self._explode = explode
        self.chamadas = 0

    async def search(self, query, limit=12):
        self.chamadas += 1
        if self._explode:
            raise RuntimeError("provedor fora do ar")
        return self._itens

    async def get(self, external_id):
        if self._explode:
            raise RuntimeError("provedor fora do ar")
        return self._itens[0] if self._itens else None


def _item(ref, source, titulo):
    return CatalogItem(ref=ref, source=source, title=titulo, poster_url="https://x/p.jpg")


def test_provedor_que_falha_nao_derruba_a_busca(redis_fake, monkeypatch):
    """Provedor fora do ar devolve vazio em vez de estourar na tela.

    O organizador ainda consegue criar evento com título livre, sem catálogo.
    """
    ruim = ProvedorFalso(CatalogSource.TMDB, [], explode=True)
    monkeypatch.setattr(catalog, "_provedores", lambda: [ruim])

    assert asyncio.run(catalog.search("x")) == []
    assert ruim.chamadas == 1, "o provedor foi consultado"


def test_segunda_busca_vem_do_cache(redis_fake, monkeypatch):
    """Rate limit das APIs externas é o motivo do cache existir."""
    p = ProvedorFalso(
        CatalogSource.TMDB, [_item("tmdb:movie:1", CatalogSource.TMDB, "Filme")]
    )
    monkeypatch.setattr(catalog, "_provedores", lambda: [p])

    primeira = asyncio.run(catalog.search("mesmo termo"))
    segunda = asyncio.run(catalog.search("mesmo termo"))

    assert p.chamadas == 1, "a segunda busca deveria ter vindo do cache"
    assert [i.ref for i in primeira] == [i.ref for i in segunda]


def test_cache_tem_ttl(redis_fake, sem_chaves):
    asyncio.run(catalog.search("parasita"))

    chaves = redis_fake.keys("catalog:*")
    assert chaves
    assert redis_fake.ttl(chaves[0]) > 0, "cache sem TTL nunca se renova"


def test_termos_diferentes_nao_compartilham_cache(redis_fake, sem_chaves):
    a = asyncio.run(catalog.search("parasita"))
    b = asyncio.run(catalog.search("chihiro"))
    assert [i.ref for i in a] != [i.ref for i in b]


def test_cache_corrompido_nao_quebra_a_busca(redis_fake, sem_chaves):
    asyncio.run(catalog.search("parasita"))
    chave = redis_fake.keys("catalog:*")[0]
    redis_fake.set(chave, "isto-nao-e-json")

    itens = asyncio.run(catalog.search("parasita"))
    assert [i.title for i in itens] == ["Parasita"], "deveria reconsultar o provedor"
