"""Rota de busca no catálogo externo.

Restrita ao organizador: é ele que monta evento a partir do catálogo. O cliente
navega pelos **eventos publicados** (`/events`), não pelo catálogo cru — item de
catálogo não tem data, local nem preço, então não é comprável.
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.api.deps import RequireOrganizer
from app.core.config import settings
from app.models.enums import EventLayout, Genre
from app.providers.base import CatalogItem, CatalogSource
from app.services import catalog

router = APIRouter(prefix="/catalog", tags=["catalog"])


class CatalogItemOut(BaseModel):
    ref: str
    source: CatalogSource
    title: str
    synopsis: str | None
    poster_url: str | None
    suggested_starts_at: str | None
    suggested_venue: str | None
    suggested_city: str | None
    suggested_state: str | None
    suggested_genre: Genre | None
    suggested_layout: EventLayout

    @classmethod
    def de(cls, i: CatalogItem) -> "CatalogItemOut":
        return cls(
            ref=i.ref,
            source=i.source,
            title=i.title,
            synopsis=i.synopsis,
            poster_url=i.poster_url,
            suggested_starts_at=(
                i.suggested_starts_at.isoformat() if i.suggested_starts_at else None
            ),
            suggested_venue=i.suggested_venue,
            suggested_city=i.suggested_city,
            suggested_state=i.suggested_state,
            suggested_genre=i.suggested_genre,
            suggested_layout=i.suggested_layout,
        )


class SearchResponse(BaseModel):
    items: list[CatalogItemOut]
    # O front avisa na tela que está em modo offline; sem esse sinal, o
    # organizador acha que a busca está quebrada em vez de sem chave.
    offline: bool


@router.get("/search", response_model=SearchResponse)
async def search(
    _: RequireOrganizer,
    q: str = Query("", max_length=120, description="Termo de busca"),
    source: CatalogSource | None = Query(None, description="Filtra por provedor"),
    limit: int = Query(12, ge=1, le=40),
) -> SearchResponse:
    itens = await catalog.search(q, source=source, limit=limit)
    return SearchResponse(
        items=[CatalogItemOut.de(i) for i in itens],
        offline=settings.catalog_offline,
    )
