"""Cliente do TMDb — catálogo de filmes.

Filme não tem data nem local: quem define a sessão é o organizador. Por isso
`suggested_starts_at` e `suggested_venue` vêm vazios daqui, ao contrário do
Ticketmaster.
"""

import httpx

from app.providers.base import CatalogItem, CatalogProvider, CatalogSource

API_BASE = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

# Timeout curto: a vitrine não pode ficar pendurada porque um provedor externo
# está lento. Falha rápido e o catálogo segue com o que o outro devolver.
TIMEOUT = httpx.Timeout(5.0, connect=3.0)


class TMDbProvider(CatalogProvider):
    source = CatalogSource.TMDB

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def search(self, query: str, limit: int = 12) -> list[CatalogItem]:
        data = await self._get(
            "/search/movie",
            {"query": query, "language": "pt-BR", "include_adult": "false"},
        )
        if data is None:
            return []

        itens = [self._to_item(r) for r in data.get("results", [])]
        # Sem pôster o card da vitrine fica quebrado, e o pôster é justamente o
        # que carrega o peso visual da tela. Melhor não oferecer o item.
        return [i for i in itens if i.poster_url][:limit]

    async def get(self, external_id: str) -> CatalogItem | None:
        # external_id chega como "movie:550" (o prefixo da origem já saiu).
        _, _, movie_id = external_id.partition(":")
        if not movie_id.isdigit():
            return None

        data = await self._get(f"/movie/{movie_id}", {"language": "pt-BR"})
        return self._to_item(data) if data else None

    # --- interno ---

    async def _get(self, path: str, params: dict[str, str]) -> dict | None:
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as http:
                r = await http.get(
                    f"{API_BASE}{path}",
                    params={**params, "api_key": self._api_key},
                )
                if r.status_code != httpx.codes.OK:
                    return None
                return r.json()
        except (httpx.HTTPError, ValueError):
            # Rede fora ou JSON inválido: o catálogo degrada, a aplicação não cai.
            return None

    def _to_item(self, raw: dict) -> CatalogItem:
        poster = raw.get("poster_path")
        titulo = raw.get("title") or raw.get("original_title") or "Sem título"

        return CatalogItem(
            ref=f"{self.source}:movie:{raw['id']}",
            source=self.source,
            title=titulo,
            synopsis=(raw.get("overview") or None),
            poster_url=f"{IMAGE_BASE}{poster}" if poster else None,
            # Data de estreia do filme não é data da sessão — não vira sugestão.
            suggested_starts_at=None,
            suggested_venue=None,
        )
