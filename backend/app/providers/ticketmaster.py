"""Cliente do Ticketmaster Discovery — catálogo de shows.

Ao contrário do filme, o show **já traz** data e local: são sugestões úteis que
preenchem o formulário do organizador. Ele ainda pode mudar — o evento é dele,
não do provedor.
"""

from datetime import datetime

import httpx

from app.providers.base import CatalogItem, CatalogProvider, CatalogSource

API_URL = "https://app.ticketmaster.com/discovery/v2/events.json"

TIMEOUT = httpx.Timeout(5.0, connect=3.0)

# A API devolve várias resoluções do mesmo cartaz. Queremos a maior imagem
# larga, que é a que funciona como pôster no card da vitrine.
_MIN_POSTER_WIDTH = 500


class TicketmasterProvider(CatalogProvider):
    source = CatalogSource.TICKETMASTER

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def search(self, query: str, limit: int = 12) -> list[CatalogItem]:
        data = await self._get({"keyword": query, "size": str(limit), "locale": "*"})
        if data is None:
            return []

        eventos = data.get("_embedded", {}).get("events", [])
        return [self._to_item(e) for e in eventos][:limit]

    async def get(self, external_id: str) -> CatalogItem | None:
        # external_id chega como "event:G5v0Z9Y7dA-bs".
        _, _, event_id = external_id.partition(":")
        if not event_id:
            return None

        data = await self._get({"id": event_id, "locale": "*"})
        if data is None:
            return None

        eventos = data.get("_embedded", {}).get("events", [])
        return self._to_item(eventos[0]) if eventos else None

    # --- interno ---

    async def _get(self, params: dict[str, str]) -> dict | None:
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as http:
                r = await http.get(API_URL, params={**params, "apikey": self._api_key})
                if r.status_code != httpx.codes.OK:
                    return None
                return r.json()
        except (httpx.HTTPError, ValueError):
            return None

    def _to_item(self, raw: dict) -> CatalogItem:
        return CatalogItem(
            ref=f"{self.source}:event:{raw['id']}",
            source=self.source,
            title=raw.get("name") or "Sem título",
            synopsis=(raw.get("info") or raw.get("pleaseNote") or None),
            poster_url=_melhor_imagem(raw.get("images", [])),
            suggested_starts_at=_parse_inicio(raw.get("dates", {})),
            suggested_venue=_parse_local(raw.get("_embedded", {})),
        )


def _melhor_imagem(images: list[dict]) -> str | None:
    """Maior imagem larga disponível.

    Ignora as verticais: o card da vitrine é horizontal, e uma imagem retrato
    esticada fica pior do que nenhuma.
    """
    largas = [
        img
        for img in images
        if img.get("url")
        and (img.get("width") or 0) >= _MIN_POSTER_WIDTH
        and (img.get("width") or 0) >= (img.get("height") or 0)
    ]
    if not largas:
        return None
    return max(largas, key=lambda i: i.get("width", 0))["url"]


def _parse_inicio(dates: dict) -> datetime | None:
    """`dates.start.dateTime` vem em ISO 8601 com Z."""
    bruto = dates.get("start", {}).get("dateTime")
    if not bruto:
        return None
    try:
        return datetime.fromisoformat(bruto.replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_local(embedded: dict) -> str | None:
    """Monta "Nome do local, Cidade" a partir do primeiro venue."""
    venues = embedded.get("venues") or []
    if not venues:
        return None

    v = venues[0]
    nome = v.get("name")
    cidade = (v.get("city") or {}).get("name")

    partes = [p for p in (nome, cidade) if p]
    return ", ".join(partes) if partes else None
