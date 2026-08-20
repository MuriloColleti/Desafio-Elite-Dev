"""Serviço de catálogo: unifica os provedores e cacheia o resultado.

Duas responsabilidades:

1. **Fan-out tolerante a falha.** Consulta os provedores configurados em
   paralelo. Um provedor fora do ar não derruba a busca — devolve lista vazia e
   os outros seguem. Sem nenhuma chave configurada, cai nas fixtures locais.
2. **Cache no Redis.** As duas APIs têm rate limit, e a busca do organizador
   repete muito o mesmo termo. O cache é compartilhado entre instâncias, então
   escalar não multiplica o consumo de quota.
"""

import asyncio
import json
from dataclasses import asdict
from datetime import datetime

import redis

from app.core.config import settings
from app.core.redis_client import client
from app.providers import fixtures
from app.providers.base import CatalogItem, CatalogProvider, CatalogSource, parse_ref
from app.providers.ticketmaster import TicketmasterProvider
from app.providers.tmdb import TMDbProvider

_CACHE_PREFIX = "catalog:"


def _provedores() -> list[CatalogProvider]:
    """Só os que têm chave. Lista vazia significa modo offline."""
    ativos: list[CatalogProvider] = []
    if settings.tmdb_api_key:
        ativos.append(TMDbProvider(settings.tmdb_api_key))
    if settings.ticketmaster_api_key:
        ativos.append(TicketmasterProvider(settings.ticketmaster_api_key))
    return ativos


# --- serialização para o cache ---


def _dump(itens: list[CatalogItem]) -> str:
    def encode(i: CatalogItem) -> dict:
        d = asdict(i)
        d["source"] = str(i.source)
        d["suggested_starts_at"] = (
            i.suggested_starts_at.isoformat() if i.suggested_starts_at else None
        )
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
        # Modo offline: fixtures locais, também filtradas por origem.
        itens = fixtures.buscar(termo, limit)
        if source is not None:
            itens = [i for i in itens if i.source is source]
        _cache_set(chave, itens)
        return itens

    # Fan-out. return_exceptions=True para um provedor lento ou quebrado não
    # anular o resultado do outro.
    resultados = await asyncio.gather(
        *(p.search(termo, limit) for p in ativos),
        return_exceptions=True,
    )

    itens: list[CatalogItem] = []
    for r in resultados:
        if isinstance(r, list):
            itens.extend(r)

    # Intercala as origens em vez de concatenar: com 12 filmes seguidos de 12
    # shows, o organizador que não rolar a lista nunca vê um show.
    itens = _intercalar(itens)[:limit]

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


def _intercalar(itens: list[CatalogItem]) -> list[CatalogItem]:
    """Alterna itens de origens diferentes, preservando a ordem de cada uma."""
    por_origem: dict[CatalogSource, list[CatalogItem]] = {}
    for i in itens:
        por_origem.setdefault(i.source, []).append(i)

    saida: list[CatalogItem] = []
    for nivel in range(max((len(v) for v in por_origem.values()), default=0)):
        for lista in por_origem.values():
            if nivel < len(lista):
                saida.append(lista[nivel])
    return saida
