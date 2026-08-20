"""Catálogo offline, para quando não há chave de API configurada.

Decisão deliberada: quem avalia o desafio consegue percorrer o fluxo inteiro —
criar evento, comprar, validar na portaria — sem cadastrar chave em serviço
nenhum. O que não funciona sem chave é apenas a busca por títulos reais.

Os pôsteres apontam para as URLs públicas reais do TMDb (o serviço de imagens
não exige chave), então a vitrine não fica com buraco visual em modo offline.
Se estiver sem internet, o front cai no placeholder de imagem quebrada — a
alternativa seria embutir base64 no repositório, o que não se justifica.
"""

from app.providers.base import CatalogItem, CatalogSource

_IMG = "https://image.tmdb.org/t/p/w500"

FIXTURES: tuple[CatalogItem, ...] = (
    # --- Filmes (viram eventos SEATED, com mapa de assentos) ---
    CatalogItem(
        ref="tmdb:movie:496243",
        source=CatalogSource.TMDB,
        title="Parasita",
        synopsis=(
            "Toda a família de Ki-taek está desempregada e vivendo num porão sujo e apertado. "
            "Uma obra do destino faz com que o filho comece a dar aulas de reforço para a filha "
            "de uma família rica."
        ),
        poster_url=f"{_IMG}/igw938inb6Fy0YVcwIyxQ7Lu5FO.jpg",
    ),
    CatalogItem(
        ref="tmdb:movie:1124",
        source=CatalogSource.TMDB,
        title="O Grande Truque",
        synopsis=(
            "Dois mágicos rivais no Londres do início do século XX travam uma disputa obsessiva "
            "para criar a ilusão definitiva."
        ),
        poster_url=f"{_IMG}/bdN3gXuIZYaJP7ftKK2sU0nPtEA.jpg",
    ),
    CatalogItem(
        ref="tmdb:movie:129",
        source=CatalogSource.TMDB,
        title="A Viagem de Chihiro",
        synopsis=(
            "Uma menina de dez anos entra num mundo habitado por deuses e espíritos, onde "
            "humanos são transformados em animais."
        ),
        poster_url=f"{_IMG}/39wmItIWsg5sZMyRUHLkWBcuVCM.jpg",
    ),
    CatalogItem(
        ref="tmdb:movie:637",
        source=CatalogSource.TMDB,
        title="A Vida é Bela",
        synopsis=(
            "Um pai judeu usa a imaginação para proteger o filho do horror de um campo de "
            "concentração, transformando tudo em um grande jogo."
        ),
        poster_url=f"{_IMG}/mfnkSeeVOBVheuyn2lo4tfmOPQb.jpg",
    ),
    CatalogItem(
        ref="tmdb:movie:238",
        source=CatalogSource.TMDB,
        title="O Poderoso Chefão",
        synopsis=(
            "O patriarca de uma família do crime organizado transfere o controle de seu império "
            "ao filho relutante."
        ),
        poster_url=f"{_IMG}/oJagOzBu9Rdd9BrciseCm3U3MCU.jpg",
    ),
    # --- Shows (viram eventos GENERAL, pista por quantidade) ---
    CatalogItem(
        ref="ticketmaster:event:demo-lampiao",
        source=CatalogSource.TICKETMASTER,
        title="Orquestra Sanfônica — Lampião Elétrico",
        synopsis="Forró instrumental encontrando arranjos de orquestra, em turnê nacional.",
        poster_url=None,
        suggested_venue="Teatro Municipal, São Paulo",
    ),
    CatalogItem(
        ref="ticketmaster:event:demo-baile",
        source=CatalogSource.TICKETMASTER,
        title="Baile do Terreiro — Edição Verão",
        synopsis="Samba de raiz e partido-alto até o amanhecer, com participações especiais.",
        poster_url=None,
        suggested_venue="Circo Voador, Rio de Janeiro",
    ),
    CatalogItem(
        ref="ticketmaster:event:demo-carranca",
        source=CatalogSource.TICKETMASTER,
        title="Carranca — Turnê Ribeirinha",
        synopsis="Rock amazônico com instrumentos de percussão regional.",
        poster_url=None,
        suggested_venue="Arena da Amazônia, Manaus",
    ),
)


def buscar(query: str, limit: int = 12) -> list[CatalogItem]:
    """Busca por substring no título, sem depender de rede."""
    termo = query.strip().lower()
    if not termo:
        return list(FIXTURES)[:limit]

    return [i for i in FIXTURES if termo in i.title.lower()][:limit]


def obter(ref: str) -> CatalogItem | None:
    return next((i for i in FIXTURES if i.ref == ref), None)
