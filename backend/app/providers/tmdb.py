"""Cliente do TMDb — catálogo de filmes.

Filme não tem data nem local de sessão: quem define isso é o organizador. Por
isso `suggested_starts_at` e `suggested_venue` vêm vazios daqui — `release_date`
é a estreia do filme, e usá-la como sugestão criaria eventos no passado.

O gênero, ao contrário, vem do provedor: o TMDb devolve `genre_ids` e o
mapeamento abaixo escolhe **um** para exibição.
"""

import httpx

from app.models.enums import Genre
from app.providers.base import CatalogItem, CatalogProvider, CatalogSource

API_BASE = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

# Timeout curto: a vitrine não pode ficar pendurada porque um provedor externo
# está lento. Falha rápido e o catálogo degrada para as fixtures.
TIMEOUT = httpx.Timeout(5.0, connect=3.0)

# Gêneros do TMDb → os nossos. Os ids são estáveis na API (de /genre/movie/list).
#
# Vários ids caem no mesmo destino de propósito: Crime, Mistério e Thriller viram
# SUSPENSE porque, para quem escolhe filme na vitrine, a distinção não muda a
# decisão — e onze gêneros já é o limite do que cabe em pílulas na tela.
_DE_TMDB: dict[int, Genre] = {
    28: Genre.ACAO,
    12: Genre.AVENTURA,
    16: Genre.ANIMACAO,
    35: Genre.COMEDIA,
    80: Genre.SUSPENSE,  # Crime
    99: Genre.DOCUMENTARIO,
    18: Genre.DRAMA,
    10751: Genre.AVENTURA,  # Família
    14: Genre.FANTASIA,
    36: Genre.DRAMA,  # História
    27: Genre.TERROR,
    10402: Genre.DOCUMENTARIO,  # Música
    9648: Genre.SUSPENSE,  # Mistério
    10749: Genre.ROMANCE,
    878: Genre.FICCAO,
    10770: Genre.DRAMA,  # Cinema TV
    53: Genre.SUSPENSE,  # Thriller
    10752: Genre.DRAMA,  # Guerra
    37: Genre.AVENTURA,  # Faroeste
}

# Ordem de preferência quando o filme tem vários gêneros. Os mais específicos
# vêm primeiro: um filme marcado como "Terror, Drama" é procurado como terror, e
# classificá-lo como drama o esconderia de quem quer se assustar.
_PRIORIDADE = (
    Genre.TERROR,
    Genre.ANIMACAO,
    Genre.DOCUMENTARIO,
    Genre.FICCAO,
    Genre.FANTASIA,
    Genre.SUSPENSE,
    Genre.ACAO,
    Genre.AVENTURA,
    Genre.COMEDIA,
    Genre.ROMANCE,
    Genre.DRAMA,
)


def _genero_de(ids: list[int] | None) -> Genre | None:
    """Escolhe um gênero entre os que o TMDb atribuiu ao filme."""
    if not ids:
        return None

    candidatos = {_DE_TMDB[i] for i in ids if i in _DE_TMDB}
    if not candidatos:
        return None

    return next((g for g in _PRIORIDADE if g in candidatos), None)


class TMDbProvider(CatalogProvider):
    source = CatalogSource.TMDB

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def search(self, query: str, limit: int = 12) -> list[CatalogItem]:
        # Busca vazia mostra o que está em cartaz no Brasil, em vez de nada: é o
        # que o organizador quer ver ao abrir a tela de criação.
        if not query.strip():
            data = await self._get(
                "/movie/now_playing", {"language": "pt-BR", "region": "BR"}
            )
        else:
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

        # `/search` devolve `genre_ids`; `/movie/{id}` devolve `genres` completo.
        # Aceitar os dois formatos evita o item perder o gênero conforme a rota.
        ids = raw.get("genre_ids")
        if ids is None and raw.get("genres"):
            ids = [g["id"] for g in raw["genres"] if "id" in g]

        return CatalogItem(
            ref=f"{self.source}:movie:{raw['id']}",
            source=self.source,
            title=titulo,
            synopsis=(raw.get("overview") or None),
            poster_url=f"{IMAGE_BASE}{poster}" if poster else None,
            suggested_genre=_genero_de(ids),
        )
