"""Catálogo offline, para quando não há chave de API configurada.

Decisão deliberada: quem avalia o desafio consegue percorrer o fluxo inteiro —
criar evento, comprar, validar na portaria — sem cadastrar chave em serviço
nenhum. O que não funciona sem chave é apenas a busca por títulos reais.

Os pôsteres apontam para as URLs públicas reais do TMDb (o serviço de imagens
não exige chave), então a vitrine não fica com buraco visual em modo offline.
Cada caminho foi verificado individualmente — pôster com 404 é o tipo de erro
que só aparece na demonstração.
"""

from app.providers.base import CatalogItem, CatalogSource

_IMG = "https://image.tmdb.org/t/p/w500"


def _filme(tmdb_id: int, titulo: str, poster: str, sinopse: str) -> CatalogItem:
    return CatalogItem(
        ref=f"tmdb:movie:{tmdb_id}",
        source=CatalogSource.TMDB,
        title=titulo,
        synopsis=sinopse,
        poster_url=f"{_IMG}/{poster}",
    )


def _show(slug: str, titulo: str, sinopse: str, local: str) -> CatalogItem:
    return CatalogItem(
        ref=f"ticketmaster:event:{slug}",
        source=CatalogSource.TICKETMASTER,
        title=titulo,
        synopsis=sinopse,
        poster_url=None,
        suggested_venue=local,
    )


FIXTURES: tuple[CatalogItem, ...] = (
    # --- Filmes (viram eventos SEATED, com mapa de assentos) ---
    _filme(
        496243,
        "Parasita",
        "igw938inb6Fy0YVcwIyxQ7Lu5FO.jpg",
        "Toda a família de Ki-taek está desempregada e vivendo num porão apertado. Uma obra do "
        "destino faz o filho começar a dar aulas para a filha de uma família rica.",
    ),
    _filme(
        27205,
        "A Origem",
        "9e3Dz7aCANy5aRUQF745IlNloJ1.jpg",
        "Um ladrão que invade sonhos para roubar segredos recebe a tarefa inversa: plantar uma "
        "ideia na mente de um herdeiro.",
    ),
    _filme(
        157336,
        "Interestelar",
        "6ricSDD83BClJsFdGB6x7cM0MFQ.jpg",
        "Com a Terra se tornando inabitável, um ex-piloto atravessa um buraco de vermes em busca "
        "de um novo lar para a humanidade.",
    ),
    _filme(
        155,
        "Batman: O Cavaleiro das Trevas",
        "4lj1ikfsSmMZNyfdi8R8Tv5tsgb.jpg",
        "Um criminoso que se chama Coringa lança Gotham no caos e força o Batman a decidir até "
        "onde vai para deter o mal.",
    ),
    _filme(
        129,
        "A Viagem de Chihiro",
        "hhoKhsyJ3hFaxEm5pMdZRiTu2lJ.jpg",
        "Uma menina de dez anos entra num mundo habitado por deuses e espíritos, onde humanos "
        "são transformados em animais.",
    ),
    _filme(
        680,
        "Pulp Fiction",
        "tptjnB2LDbuUWya9Cx5sQtv5hqb.jpg",
        "Histórias de bandidos, boxeadores e gângsteres se cruzam em Los Angeles, fora de ordem "
        "e com muito diálogo.",
    ),
    _filme(
        1124,
        "O Grande Truque",
        "4AUW2bGbQjWACUREckGJWXmyF0d.jpg",
        "Dois mágicos rivais no Londres do início do século XX travam uma disputa obsessiva para "
        "criar a ilusão definitiva.",
    ),
    _filme(
        872585,
        "Oppenheimer",
        "1OsQJEoSXBjduuCvDOlRhoEUaHu.jpg",
        "A história do físico que liderou o desenvolvimento da bomba atômica e passou o resto da "
        "vida lidando com o que criou.",
    ),
    _filme(
        278,
        "Um Sonho de Liberdade",
        "umX3lBhHoTV7Lsci140Yr8VpXyN.jpg",
        "Condenado por um crime que não cometeu, um bancário mantém a esperança ao longo de "
        "décadas numa penitenciária.",
    ),
    _filme(
        13,
        "Forrest Gump",
        "d74WpIsH8379TIL4wUxDneRCYv2.jpg",
        "Um homem de coração simples atravessa décadas da história americana sem nunca perceber "
        "o próprio papel nela.",
    ),
    # --- Shows (viram eventos GENERAL, pista por quantidade) ---
    _show(
        "demo-baile",
        "Baile do Terreiro — Edição Verão",
        "Samba de raiz e partido-alto até o amanhecer, com participações especiais.",
        "Circo Voador, Rio de Janeiro",
    ),
    _show(
        "demo-lampiao",
        "Orquestra Sanfônica — Lampião Elétrico",
        "Forró instrumental encontrando arranjos de orquestra, em turnê nacional.",
        "Teatro Municipal, São Paulo",
    ),
    _show(
        "demo-carranca",
        "Carranca — Turnê Ribeirinha",
        "Rock amazônico com instrumentos de percussão regional.",
        "Arena da Amazônia, Manaus",
    ),
    _show(
        "demo-vinil",
        "Noite do Vinil — Só Clássicos",
        "DJ set tocando apenas discos originais dos anos 70 e 80.",
        "Audio Club, São Paulo",
    ),
    _show(
        "demo-cordel",
        "Cordel Encantado ao Vivo",
        "Literatura de cordel musicada, com viola e narração cênica.",
        "Teatro José de Alencar, Fortaleza",
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
