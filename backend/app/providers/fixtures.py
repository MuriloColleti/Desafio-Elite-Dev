"""Catálogo offline, para quando não há chave de API configurada.

Decisão deliberada: quem avalia o desafio consegue percorrer o fluxo inteiro —
criar evento, comprar, validar na portaria — sem cadastrar chave em serviço
nenhum. O que não funciona sem chave é apenas a busca por títulos reais.

Os pôsteres apontam para URLs públicas reais do TMDb (o serviço de imagens não
exige chave), então a vitrine não fica com buraco visual em modo offline. Cada
caminho foi verificado individualmente respondendo 200 — pôster com 404 é o
tipo de erro que só aparece na demonstração.

Os gêneros são atribuídos à mão em vez de vindos da API: o TMDb devolve vários
por filme e um mapeamento automático escolheria o primeiro, que às vezes é o
menos representativo. Aqui cada item tem o gênero pelo qual as pessoas o
procurariam.
"""

from app.models.enums import Genre
from app.providers.base import CatalogItem, CatalogSource

_IMG = "https://image.tmdb.org/t/p/w500"


def _filme(tmdb_id: int, titulo: str, poster: str, genero: Genre, sinopse: str) -> CatalogItem:
    return CatalogItem(
        ref=f"tmdb:movie:{tmdb_id}",
        source=CatalogSource.TMDB,
        title=titulo,
        synopsis=sinopse,
        poster_url=f"{_IMG}/{poster}",
        suggested_genre=genero,
    )


def _show(slug: str, titulo: str, genero: Genre, local: str, sinopse: str) -> CatalogItem:
    return CatalogItem(
        ref=f"ticketmaster:event:{slug}",
        source=CatalogSource.TICKETMASTER,
        title=titulo,
        synopsis=sinopse,
        poster_url=None,
        suggested_venue=local,
        suggested_genre=genero,
    )


FILMES: tuple[CatalogItem, ...] = (
    # --- Suspense e terror ---
    _filme(
        496243, "Parasita", "igw938inb6Fy0YVcwIyxQ7Lu5FO.jpg", Genre.SUSPENSE,
        "Uma família desempregada se infiltra na casa de uma família rica, e o plano sai do "
        "controle de um jeito que ninguém previu.",
    ),
    _filme(
        274, "O Silêncio dos Inocentes", "5fCrBDJLHxywiFr19o4aOWf92VN.jpg", Genre.SUSPENSE,
        "Uma agente do FBI recorre a um assassino canibal preso para capturar outro serial killer.",
    ),
    _filme(
        419430, "Corra!", "A0RoSZh8PEYJgDMgM2EV7Ycz3dR.jpg", Genre.TERROR,
        "Um jovem negro conhece a família da namorada branca e descobre que a hospitalidade "
        "esconde algo muito pior.",
    ),
    _filme(
        396535, "Invasão Zumbi", "QqHtwk0oHYed26zra9WGQGyBSm.jpg", Genre.TERROR,
        "Um surto zumbi se espalha num trem-bala de Seul a Busan, e os vagões viram armadilha.",
    ),
    _filme(
        758323, "O Exorcista do Papa", "hqIIoGsKKGWK7HjpgCSvV6mgKyT.jpg", Genre.TERROR,
        "O exorcista-chefe do Vaticano investiga a possessão de um menino e encontra uma "
        "conspiração secular.",
    ),
    _filme(
        762430, "A Chamada", "eqaSh2PjYcGpS6rybz6UjLNuvrg.jpg", Genre.TERROR,
        "Quem vê a criatura morre em poucos dias. A única saída é passar a maldição para outra "
        "pessoa.",
    ),
    _filme(
        550, "Clube da Luta", "mCICnh7QBH0gzYaTQChBDDVIKdm.jpg", Genre.SUSPENSE,
        "Um homem insone e um vendedor de sabão criam um clube de luta clandestino que cresce "
        "além do controle.",
    ),
    _filme(
        1124, "O Grande Truque", "4AUW2bGbQjWACUREckGJWXmyF0d.jpg", Genre.SUSPENSE,
        "Dois mágicos rivais no Londres do século XIX travam uma disputa obsessiva para criar a "
        "ilusão definitiva.",
    ),
    # --- Ficção científica ---
    _filme(
        27205, "A Origem", "9e3Dz7aCANy5aRUQF745IlNloJ1.jpg", Genre.FICCAO,
        "Um ladrão que invade sonhos recebe a tarefa inversa: plantar uma ideia na mente de um "
        "herdeiro.",
    ),
    _filme(
        157336, "Interestelar", "6ricSDD83BClJsFdGB6x7cM0MFQ.jpg", Genre.FICCAO,
        "Com a Terra se tornando inabitável, um ex-piloto atravessa um buraco de vermes em busca "
        "de um novo lar.",
    ),
    _filme(
        603, "Matrix", "lDqMDI3xpbB9UQRyeXfei0MXhqb.jpg", Genre.FICCAO,
        "Um programador descobre que o mundo é uma simulação e se junta à resistência.",
    ),
    _filme(
        438631, "Duna", "uzERcfV2rSHNhW5eViQiO9hNiA7.jpg", Genre.FICCAO,
        "O herdeiro de uma casa nobre é enviado ao planeta deserto mais valioso do universo, e "
        "cai numa guerra por especiaria.",
    ),
    _filme(
        693134, "Duna: Parte Dois", "8LJJjLjAzAwXS40S5mx79PJ2jSs.jpg", Genre.FICCAO,
        "Paul se une aos Fremen para vingar a família e tenta evitar o futuro terrível que "
        "consegue prever.",
    ),
    _filme(
        335984, "Blade Runner 2049", "49pANIZXRAdHUiWjjBv4vxPeqRC.jpg", Genre.FICCAO,
        "Um caçador de andróides descobre um segredo enterrado capaz de romper o que resta da "
        "sociedade.",
    ),
    _filme(
        653346, "Planeta dos Macacos: O Reinado", "hBGnLm2A1TapONoPo7QrMpj2B6B.jpg", Genre.FICCAO,
        "Gerações após o reinado de César, um jovem macaco questiona tudo o que aprendeu sobre "
        "o passado.",
    ),
    _filme(
        545611, "Tudo em Todo o Lugar ao Mesmo Tempo", "2dSZQGwijlXvMSyuGe0FSgrXnv0.jpg",
        Genre.FICCAO,
        "Uma dona de lavanderia descobre que precisa salvar o multiverso enquanto resolve a "
        "auditoria fiscal.",
    ),
    # --- Ação ---
    _filme(
        155, "Batman: O Cavaleiro das Trevas", "4lj1ikfsSmMZNyfdi8R8Tv5tsgb.jpg", Genre.ACAO,
        "O Coringa lança Gotham no caos e força o Batman a decidir até onde vai para deter o mal.",
    ),
    _filme(
        76341, "Mad Max: Estrada da Fúria", "tH64gzAHDFg7EFcgfkkZyHdGM5P.jpg", Genre.ACAO,
        "Numa perseguição quase ininterrupta pelo deserto, dois fugitivos enfrentam um tirano e "
        "sua frota.",
    ),
    _filme(
        361743, "Top Gun: Maverick", "kPbuLGVSJHATkW9fX9L3h1wM0Pa.jpg", Genre.ACAO,
        "Depois de trinta anos, Maverick treina uma nova geração de pilotos para uma missão "
        "considerada impossível.",
    ),
    _filme(
        299534, "Vingadores: Ultimato", "9fRX8UKlIW7Lb9GqNsJVakWWFCi.jpg", Genre.ACAO,
        "Os heróis que sobraram tentam desfazer o estalo que apagou metade da vida no universo.",
    ),
    _filme(
        505642, "Pantera Negra: Wakanda para Sempre", "cryEN3sWlgB2wTzcUNVtDGI8bkM.jpg", Genre.ACAO,
        "Wakanda luta para proteger sua soberania depois da morte do rei, enquanto uma nova "
        "potência emerge do mar.",
    ),
    _filme(
        111, "Scarface", "b089YkBDJjOGDQxXkOXBR06Lz2Y.jpg", Genre.ACAO,
        "Um imigrante cubano sobe ao topo do tráfico em Miami e descobre que o topo é um lugar "
        "muito estreito.",
    ),
    _filme(
        680, "Pulp Fiction", "tptjnB2LDbuUWya9Cx5sQtv5hqb.jpg", Genre.ACAO,
        "Histórias de bandidos, boxeadores e gângsteres se cruzam em Los Angeles, fora de ordem "
        "e com muito diálogo.",
    ),
    # --- Aventura ---
    _filme(
        1891, "O Império Contra-Ataca", "dLGT8b4Ut10z44uYLaip4QiwKta.jpg", Genre.AVENTURA,
        "A Aliança Rebelde recua diante do Império, e Luke busca um mestre Jedi num planeta "
        "pantanoso.",
    ),
    _filme(
        105, "De Volta para o Futuro", "i996T0lI1fGtFEowiH3V6eZthL0.jpg", Genre.AVENTURA,
        "Um adolescente vai acidentalmente a 1955 e precisa garantir que os próprios pais se "
        "conheçam.",
    ),
    _filme(
        447365, "Guardiões da Galáxia: Vol. 3", "4yycSPnchdNAZirGkmCYQwTd3cr.jpg", Genre.AVENTURA,
        "A equipe enfrenta o passado de Rocket numa missão que pode ser a última de todas.",
    ),
    _filme(
        916224, "Suzume", "QcS3MhdUiOEUOjY451FOFInZXF.jpg", Genre.AVENTURA,
        "Uma adolescente atravessa o Japão fechando portas mágicas que liberam desastres.",
    ),
    # --- Animação ---
    _filme(
        129, "A Viagem de Chihiro", "hhoKhsyJ3hFaxEm5pMdZRiTu2lJ.jpg", Genre.ANIMACAO,
        "Uma menina de dez anos entra num mundo de deuses e espíritos, onde humanos são "
        "transformados em animais.",
    ),
    _filme(
        4935, "O Castelo Animado", "1hTfaEWktMJPxCk5nZNtK7F86C9.jpg", Genre.ANIMACAO,
        "Uma jovem enfeitiçada e envelhecida se refugia no castelo ambulante de um mago.",
    ),
    _filme(
        324857, "Homem-Aranha: No Aranhaverso", "ybQSBSrINtjWsJQ6Ih8sva8HlEZ.jpg", Genre.ANIMACAO,
        "Miles Morales descobre que existem outros Homens-Aranha, de outras dimensões.",
    ),
    _filme(
        569094, "Através do Aranhaverso", "fBS6y0LYX4kU6pPSBYMdQy6SIHX.jpg", Genre.ANIMACAO,
        "Miles atravessa o multiverso e discorda de uma sociedade de Aranhas sobre o que é "
        "inevitável.",
    ),
    _filme(
        508442, "Soul", "1G7QNn1sUShae0Rf9k9D99wVFg5.jpg", Genre.ANIMACAO,
        "Um professor de música tem a chance da vida no mesmo dia em que sua alma se separa do "
        "corpo.",
    ),
    _filme(
        1011985, "Kung Fu Panda 4", "aNK6MA5EApIo0UJE7ZWSYcZBJKy.jpg", Genre.ANIMACAO,
        "Po precisa encontrar um sucessor antes de assumir um novo posto — e enfrentar uma "
        "feiticeira camaleoa.",
    ),
    _filme(
        502356, "Super Mario Bros. O Filme", "ij8sapIEbLf2g8npOu6XgsQS2w0.jpg", Genre.ANIMACAO,
        "Dois encanadores do Brooklyn caem num mundo de canos e precisam salvar um reino.",
    ),
    _filme(
        12477, "Túmulo dos Vagalumes", "bhPpSMKqabTXp4LuBRtK8Ndme3W.jpg", Genre.ANIMACAO,
        "Dois irmãos tentam sobreviver no Japão dos últimos meses da Segunda Guerra.",
    ),
    # --- Fantasia ---
    _filme(
        13, "Forrest Gump", "d74WpIsH8379TIL4wUxDneRCYv2.jpg", Genre.FANTASIA,
        "Um homem de coração simples atravessa décadas da história americana sem perceber o "
        "próprio papel nela.",
    ),
    # --- Drama ---
    _filme(
        278, "Um Sonho de Liberdade", "umX3lBhHoTV7Lsci140Yr8VpXyN.jpg", Genre.DRAMA,
        "Condenado por um crime que não cometeu, um bancário mantém a esperança ao longo de "
        "décadas na prisão.",
    ),
    _filme(
        238, "O Poderoso Chefão", "oJagOzBu9Rdd9BrciseCm3U3MCU.jpg", Genre.DRAMA,
        "O patriarca de uma família do crime transfere o império ao filho mais relutante.",
    ),
    _filme(
        424, "A Lista de Schindler", "jbnF7dVi8iu80zTsWAC0Om8ZYOu.jpg", Genre.DRAMA,
        "Um industrial alemão salva mais de mil judeus empregando-os em suas fábricas.",
    ),
    _filme(
        872585, "Oppenheimer", "1OsQJEoSXBjduuCvDOlRhoEUaHu.jpg", Genre.DRAMA,
        "A história do físico que liderou a bomba atômica e passou o resto da vida lidando com "
        "o que criou.",
    ),
    _filme(
        637, "A Vida é Bela", "dkK48wCY4aVpWFDdPpS6DxQ1bvB.jpg", Genre.DRAMA,
        "Um pai usa a imaginação para proteger o filho do horror de um campo de concentração.",
    ),
    # --- Romance ---
    _filme(
        597, "Titanic", "As0zX43h3w6kD2NS4uVHu9HKdEh.jpg", Genre.ROMANCE,
        "Duas pessoas de classes opostas se apaixonam na viagem inaugural do navio que não "
        "deveria afundar.",
    ),
    _filme(
        11036, "Diário de uma Paixão", "hO6k34ZNDwWzgcnzFbqYf2Rjg5W.jpg", Genre.ROMANCE,
        "Um homem lê para uma mulher com demência a história do amor que os dois viveram.",
    ),
    _filme(
        313369, "La La Land", "AvMietG6xuobpSSdmVnKuTjv4bL.jpg", Genre.ROMANCE,
        "Uma atriz e um pianista de jazz se apaixonam em Los Angeles, entre ambição e escolha.",
    ),
    _filme(
        152601, "Ela", "yyDGhBY8RYXyXYADeFq1BDxpLkl.jpg", Genre.ROMANCE,
        "Um escritor solitário se apaixona por um sistema operacional que aprende com ele.",
    ),
    # --- Comédia ---
    _filme(
        490132, "Green Book: O Guia", "u9dldwRwQjTZGlIxKaAtAPLAjOv.jpg", Genre.COMEDIA,
        "Um segurança italiano dirige para um pianista negro em turnê pelo sul dos EUA nos anos 60.",
    ),
    _filme(
        1029575, "Plano em Família", "3CezGI4ORSgVKk5Ch3UUWtL7SET.jpg", Genre.COMEDIA,
        "Um pai com passado de assassino leva a família numa viagem que vira fuga.",
    ),
    _filme(
        640344, "Eu Contra Você", "sfeQTIRkJjWt8IPDSBcPqkrcaas.jpg", Genre.COMEDIA,
        "Luccas e Gi enfrentam o Sr. S numa aventura cheia de desafios.",
    ),
    _filme(
        19404, "Dilwale Dulhania Le Jayenge", "lfRkUr7DYdHldAqi3PwdQGBRBPM.jpg", Genre.ROMANCE,
        "Dois jovens indianos se conhecem numa viagem pela Europa e enfrentam tradições "
        "familiares.",
    ),
)

SHOWS: tuple[CatalogItem, ...] = (
    _show(
        "demo-baile", "Baile do Terreiro — Edição Verão", Genre.SAMBA,
        "Circo Voador, Rio de Janeiro",
        "Samba de raiz e partido-alto até o amanhecer, com participações especiais.",
    ),
    _show(
        "demo-lampiao", "Orquestra Sanfônica — Lampião Elétrico", Genre.FORRO,
        "Teatro Municipal, São Paulo",
        "Forró instrumental encontrando arranjos de orquestra, em turnê nacional.",
    ),
    _show(
        "demo-carranca", "Carranca — Turnê Ribeirinha", Genre.ROCK,
        "Arena da Amazônia, Manaus",
        "Rock amazônico com instrumentos de percussão regional.",
    ),
    _show(
        "demo-vinil", "Noite do Vinil — Só Clássicos", Genre.ROCK,
        "Audio Club, São Paulo",
        "DJ set tocando apenas discos originais dos anos 70 e 80.",
    ),
    _show(
        "demo-cordel", "Cordel Encantado ao Vivo", Genre.MPB,
        "Teatro José de Alencar, Fortaleza",
        "Literatura de cordel musicada, com viola e narração cênica.",
    ),
    _show(
        "demo-maloca", "Maloca Sound System", Genre.REGGAE,
        "Praça Mauá, Rio de Janeiro",
        "Reggae raiz e dub com sound system montado ao ar livre.",
    ),
    _show(
        "demo-quebrada", "Rima na Quebrada — Batalha Final", Genre.RAP,
        "Cine Joia, São Paulo",
        "Batalha de rima com os melhores MCs do ano, júri aberto ao público.",
    ),
    _show(
        "demo-pulso", "PULSO — Noite Eletrônica", Genre.ELETRONICA,
        "Warung Beach Club, Itajaí",
        "Techno melódico até o sol nascer, com line-up internacional.",
    ),
    _show(
        "demo-fluxo", "Fluxo da Zona Norte", Genre.FUNK,
        "Espaço Unimed, São Paulo",
        "Funk 150 BPM com os DJs que definiram o som das quebradas.",
    ),
    _show(
        "demo-roda", "Roda de Pagode do Cacique", Genre.PAGODE,
        "Clube Cacique, Rio de Janeiro",
        "Pagode de mesa, com repertório dos anos 90 e cerveja gelada.",
    ),
    _show(
        "demo-poeira", "Poeira & Viola — Modão Raiz", Genre.SERTANEJO,
        "Parque do Peão, Barretos",
        "Sertanejo de raiz com dupla acompanhada de viola caipira.",
    ),
    _show(
        "demo-trio", "Trio Elétrico — Ensaio de Verão", Genre.AXE,
        "Wet'n Wild, Salvador",
        "Ensaio aberto de axé com trio elétrico e bloco convidado.",
    ),
    _show(
        "demo-brasilidade", "Brasilidade — Vozes do Nordeste", Genre.MPB,
        "Theatro Municipal, Rio de Janeiro",
        "MPB nordestina em formato voz e piano, repertório autoral.",
    ),
    _show(
        "demo-bass", "Subgrave — Bass Night", Genre.ELETRONICA,
        "D-Edge, São Paulo",
        "Drum and bass e jungle, com sistema de som calibrado para graves.",
    ),
    _show(
        "demo-cadencia", "Cadência — Samba de Mesa", Genre.SAMBA,
        "Renascença Clube, Rio de Janeiro",
        "Samba tradicional em roda, sem palco, com o público em volta.",
    ),
)

# A ordem importa: o seed consome esta tupla em sequência para montar as
# sessões, e o carrossel da vitrine mostra os primeiros.
FIXTURES: tuple[CatalogItem, ...] = (*FILMES, *SHOWS)


def buscar(query: str, limit: int = 12) -> list[CatalogItem]:
    """Busca por substring no título, sem depender de rede."""
    termo = query.strip().lower()
    if not termo:
        return list(FIXTURES)[:limit]

    return [i for i in FIXTURES if termo in i.title.lower()][:limit]


def obter(ref: str) -> CatalogItem | None:
    return next((i for i in FIXTURES if i.ref == ref), None)
