"""Contrato do catálogo externo.

TMDb e Ticketmaster têm formatos e vocabulários distintos — filme não tem local,
show não tem sinopse — mas o resto da aplicação não deve saber disso. Os dois
entram por `CatalogProvider` e saem como `CatalogItem`, e é isso que permite ao
organizador usar o mesmo formulário para os dois.

O `ref` (`tmdb:movie:550`) é a única coisa que atravessa a fronteira e volta:
identifica a origem sem que o domínio precise interpretá-la.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from app.models.enums import EventLayout


class CatalogSource(StrEnum):
    TMDB = "tmdb"
    TICKETMASTER = "ticketmaster"


@dataclass(frozen=True, slots=True)
class CatalogItem:
    """Item do catálogo, já normalizado.

    Imutável de propósito: o que vem do provedor é dado de leitura. Quando o
    organizador cria um evento, os campos relevantes são **copiados** para
    `Event` — a partir daí o evento não depende mais do provedor.
    """

    ref: str  # "tmdb:movie:550"
    source: CatalogSource
    title: str
    synopsis: str | None = None
    poster_url: str | None = None

    # Sugestões, não verdades: o organizador define data e local de fato.
    # Filme não traz data de sessão; show do Ticketmaster traz.
    suggested_starts_at: datetime | None = None
    suggested_venue: str | None = None

    @property
    def suggested_layout(self) -> EventLayout:
        """Filme sugere assento marcado; show sugere pista.

        Só sugestão: quem decide é o organizador no formulário. Um show em
        teatro pode ser SEATED, e uma sessão de cinema ao ar livre, GENERAL.
        """
        return (
            EventLayout.SEATED
            if self.source is CatalogSource.TMDB
            else EventLayout.GENERAL
        )


class CatalogProvider(ABC):
    """Um provedor de catálogo."""

    source: CatalogSource

    @abstractmethod
    async def search(self, query: str, limit: int = 12) -> list[CatalogItem]:
        """Busca por título. Nunca levanta exceção de rede para o chamador:
        provedor fora do ar devolve lista vazia, e a busca segue com o que os
        outros retornarem."""

    @abstractmethod
    async def get(self, external_id: str) -> CatalogItem | None:
        """Busca um item específico, para validar `catalog_ref` na criação."""


def parse_ref(ref: str) -> tuple[CatalogSource, str] | None:
    """Quebra "tmdb:movie:550" em (TMDB, "movie:550").

    Devolve None em vez de levantar: `catalog_ref` pode chegar do cliente, e
    entrada inválida é 422 de validação, não erro interno.
    """
    source_raw, _, external_id = ref.partition(":")
    if not source_raw or not external_id:
        return None
    try:
        return CatalogSource(source_raw), external_id
    except ValueError:
        return None
