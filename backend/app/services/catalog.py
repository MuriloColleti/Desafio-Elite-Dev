"""Serviço de catálogo: fala com o provedor e cacheia o resultado.

Duas responsabilidades:

1. **Tolerância a falha.** Provedor fora do ar devolve lista vazia em vez de
   derrubar a tela, e sem chave configurada cai nas fixtures locais — o que
   permite percorrer o fluxo inteiro sem cadastrar chave em serviço nenhum.
2. **Cache no Redis.** O TMDb tem rate limit, e a busca do organizador repete
   muito o mesmo termo. O cache é compartilhado entre instâncias, então escalar
   não multiplica o consumo de quota.

O fan-out em paralelo saiu junto com o Ticketmaster: com um provedor só, o
`asyncio.gather` era cerimônia sem função.
"""

import json
from dataclasses import asdict
from datetime import datetime

import redis

from app.core.config import settings
from app.core.redis_client import client
from app.models.enums import Genre
from app.providers import fixtures
from app.providers.base import CatalogItem, CatalogProvider, CatalogSource, parse_ref
from app.providers.tmdb import TMDbProvider

_CACHE_PREFIX = "catalog:"


def _provedores() -> list[CatalogProvider]:
    """Lista vazia significa modo offline (fixtures locais).

    Continua devolvendo lista, e não um provedor único, porque somar outra fonte
    depois não deve mudar a forma de quem chama.
    """
    if not settings.tmdb_api_key:
        return []
    return [TMDbProvider(settings.tmdb_api_key)]


# --- serialização para o cache ---


def _dump(itens: list[CatalogItem]) -> str:
    def encode(i: CatalogItem) -> dict:
        d = asdict(i)
        d["source"] = str(i.source)
        d["suggested_starts_at"] = (
            i.suggested_starts_at.isoformat() if i.suggested_starts_at else None
        )
        d["suggested_genre"] = str(i.suggested_genre) if i.suggested_genre else None
        return d

    return json.dumps([encode(i) for i in itens])


def _load(raw: str) -> list[CatalogItem]:
    itens = []
    for d in json.loads(raw):
        quando = d.get("suggested_starts_at")
        itens.append(
            CatalogItem(
                ref=d["ref"],
                source=CatalogSource(d["source"]),
                title=d["title"],
                synopsis=d.get("synopsis"),
                poster_url=d.get("poster_url"),
                suggested_starts_at=datetime.fromisoformat(quando) if quando else None,
                suggested_venue=d.get("suggested_venue"),
                suggested_city=d.get("suggested_city"),
                suggested_state=d.get("suggested_state"),
                suggested_genre=(
                    Genre(d["suggested_genre"]) if d.get("suggested_genre") else None
                ),
            )
        )
    return itens


def _cache_get(chave: str) -> list[CatalogItem] | None:
    try:
        raw = client.get(_CACHE_PREFIX + chave)
    except redis.RedisError:
        return None  # Redis fora: busca direto no provedor, não é erro fatal
    if not raw:
        return None
    try:
        return _load(raw)
    except (json.JSONDecodeError, KeyError, ValueError):
        return None


def _cache_set(chave: str, itens: list[CatalogItem]) -> None:
    try:
        client.set(
            _CACHE_PREFIX + chave,
            _dump(itens),
            ex=settings.catalog_cache_ttl_seconds,
        )
    except redis.RedisError:
        pass  # cache é otimização; falhar aqui não pode quebrar a busca


# --- API pública do serviço ---


async def search(query: str, source: CatalogSource | None = None, limit: int = 12) -> list[CatalogItem]:
    """Busca nos provedores (ou nas fixtures), com cache.

    `source` filtra por provedor; None consulta todos.
    """
    termo = query.strip()
    chave = f"search:{source or 'all'}:{limit}:{termo.lower()}"

    if (cacheado := _cache_get(chave)) is not None:
        return cacheado

    ativos = [p for p in _provedores() if source is None or p.source is source]

    if not ativos:
        # Modo offline: fixtures locais.
        itens = fixtures.buscar(termo, limit)
        if source is not None:
            itens = [i for i in itens if i.source is source]
        _cache_set(chave, itens)
        return itens

    itens: list[CatalogItem] = []
    for p in ativos:
        try:
            itens.extend(await p.search(termo, limit))
        except Exception:
            # Provedor fora do ar não derruba a busca: a tela mostra o que der,
            # e o organizador ainda pode criar evento com título livre.
            continue

    itens = itens[:limit]
    _cache_set(chave, itens)
    return itens


async def get(ref: str) -> CatalogItem | None:
    """Busca um item por `catalog_ref`, para validar na criação do evento."""
    parsed = parse_ref(ref)
    if parsed is None:
        return None
    source, external_id = parsed

    if (cacheado := _cache_get(f"ref:{ref}")) is not None:
        return cacheado[0] if cacheado else None

    provedor = next((p for p in _provedores() if p.source is source), None)
    if provedor is None:
        item = fixtures.obter(ref)
    else:
        try:
            item = await provedor.get(external_id)
        except Exception:
            item = None

    _cache_set(f"ref:{ref}", [item] if item else [])
    return item
