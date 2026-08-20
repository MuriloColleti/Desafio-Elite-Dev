"""Normalização dos provedores externos.

Testa o mapeamento provedor → `CatalogItem` com payloads no formato real
documentado das duas APIs. É a parte que pode estar errada sem que nada quebre
visivelmente: um campo com nome trocado vira `None` silencioso na tela.

A chamada HTTP em si não é testada aqui — bater na API real deixaria a suíte
dependente de chave e de rede.
"""

from datetime import UTC, datetime

import pytest

from app.providers import fixtures
from app.providers.base import CatalogSource, parse_ref
from app.providers.ticketmaster import (
    TicketmasterProvider,
    _melhor_imagem,
    _parse_inicio,
    _parse_local,
)
from app.providers.tmdb import TMDbProvider
from app.models.enums import EventLayout


# --- parse_ref ---


@pytest.mark.parametrize(
    ("ref", "esperado"),
    [
        ("tmdb:movie:550", (CatalogSource.TMDB, "movie:550")),
        ("ticketmaster:event:G5v0Z9", (CatalogSource.TICKETMASTER, "event:G5v0Z9")),
    ],
)
def test_parse_ref_valido(ref, esperado):
    assert parse_ref(ref) == esperado


@pytest.mark.parametrize("ruim", ["", "lixo", "desconhecido:x:1", ":", "tmdb:"])
def test_parse_ref_invalido_devolve_none(ruim):
    """Ref inválida vem do cliente: é 422 de validação, não erro interno."""
    assert parse_ref(ruim) is None


# --- TMDb ---

# Formato de /search/movie conforme a documentação do TMDb.
TMDB_RAW = {
    "id": 496243,
    "title": "Parasita",
    "original_title": "기생충",
    "overview": "Toda a família de Ki-taek está desempregada.",
    "poster_path": "/igw938inb6Fy0YVcwIyxQ7Lu5FO.jpg",
    "release_date": "2019-05-30",
    "vote_average": 8.5,
}


def test_tmdb_mapeia_campos():
    item = TMDbProvider("chave-falsa")._to_item(TMDB_RAW)

    assert item.ref == "tmdb:movie:496243"
    assert item.source is CatalogSource.TMDB
    assert item.title == "Parasita"
    assert item.synopsis == "Toda a família de Ki-taek está desempregada."
    assert item.poster_url == (
        "https://image.tmdb.org/t/p/w500/igw938inb6Fy0YVcwIyxQ7Lu5FO.jpg"
    )


def test_tmdb_nao_sugere_data_nem_local():
    """Filme não tem sessão: data e local são decisão do organizador.

    `release_date` é data de estreia do filme, não do evento — usá-la como
    sugestão criaria eventos no passado.
    """
    item = TMDbProvider("x")._to_item(TMDB_RAW)
    assert item.suggested_starts_at is None
    assert item.suggested_venue is None


def test_tmdb_sugere_assento_marcado():
    assert TMDbProvider("x")._to_item(TMDB_RAW).suggested_layout is EventLayout.SEATED


def test_tmdb_cai_para_titulo_original():
    raw = {**TMDB_RAW, "title": None}
    assert TMDbProvider("x")._to_item(raw).title == "기생충"


def test_tmdb_sem_titulo_nenhum():
    raw = {"id": 1, "poster_path": "/a.jpg"}
    assert TMDbProvider("x")._to_item(raw).title == "Sem título"


def test_tmdb_sem_poster_fica_none():
    raw = {**TMDB_RAW, "poster_path": None}
    assert TMDbProvider("x")._to_item(raw).poster_url is None


def test_tmdb_sinopse_vazia_vira_none():
    """String vazia na tela é pior que ausência: o front não sabe omitir."""
    raw = {**TMDB_RAW, "overview": ""}
    assert TMDbProvider("x")._to_item(raw).synopsis is None


# --- Ticketmaster ---

# Formato de /discovery/v2/events.json conforme a documentação.
TM_RAW = {
    "id": "G5v0Z9Y7dA-bs",
    "name": "Baile do Terreiro",
    "info": "Samba de raiz até o amanhecer.",
    "dates": {"start": {"localDate": "2026-09-15", "dateTime": "2026-09-15T23:00:00Z"}},
    "images": [
        {"url": "https://img/pequena.jpg", "width": 100, "height": 100},
        {"url": "https://img/grande.jpg", "width": 1024, "height": 576},
        {"url": "https://img/retrato.jpg", "width": 640, "height": 1136},
    ],
    "_embedded": {
        "venues": [{"name": "Circo Voador", "city": {"name": "Rio de Janeiro"}}]
    },
}


def test_ticketmaster_mapeia_campos():
    item = TicketmasterProvider("chave-falsa")._to_item(TM_RAW)

    assert item.ref == "ticketmaster:event:G5v0Z9Y7dA-bs"
    assert item.source is CatalogSource.TICKETMASTER
    assert item.title == "Baile do Terreiro"
    assert item.synopsis == "Samba de raiz até o amanhecer."


def test_ticketmaster_sugere_data_e_local():
    """Show já traz data e local — preenchem o formulário do organizador."""
    item = TicketmasterProvider("x")._to_item(TM_RAW)

    assert item.suggested_starts_at == datetime(2026, 9, 15, 23, 0, tzinfo=UTC)
    assert item.suggested_venue == "Circo Voador, Rio de Janeiro"


def test_ticketmaster_sugere_pista():
    assert (
        TicketmasterProvider("x")._to_item(TM_RAW).suggested_layout
        is EventLayout.GENERAL
    )


def test_escolhe_a_maior_imagem_horizontal():
    """Retrato esticado num card horizontal fica pior que imagem nenhuma."""
    assert _melhor_imagem(TM_RAW["images"]) == "https://img/grande.jpg"


def test_sem_imagem_horizontal_devolve_none():
    apenas_retrato = [{"url": "https://img/r.jpg", "width": 640, "height": 1136}]
    assert _melhor_imagem(apenas_retrato) is None


def test_imagem_sem_url_e_ignorada():
    assert _melhor_imagem([{"width": 1024, "height": 576}]) is None


def test_lista_de_imagens_vazia():
    assert _melhor_imagem([]) is None


def test_parse_inicio_sem_hora_devolve_none():
    """`timeTBA`: só a data, sem hora. Não inventamos horário."""
    assert _parse_inicio({"start": {"localDate": "2026-09-15", "timeTBA": True}}) is None


def test_parse_inicio_malformado_devolve_none():
    assert _parse_inicio({"start": {"dateTime": "não é data"}}) is None
    assert _parse_inicio({}) is None


def test_parse_local_só_com_nome():
    embedded = {"venues": [{"name": "Circo Voador"}]}
    assert _parse_local(embedded) == "Circo Voador"


def test_parse_local_sem_venue():
    assert _parse_local({}) is None
    assert _parse_local({"venues": []}) is None


# --- Fixtures offline ---


def test_fixtures_cobrem_os_dois_layouts():
    """Sem chave de API o avaliador ainda precisa dos dois fluxos de reserva."""
    filmes = [i for i in fixtures.FIXTURES if i.source is CatalogSource.TMDB]
    shows = [i for i in fixtures.FIXTURES if i.source is CatalogSource.TICKETMASTER]

    assert filmes and shows
    assert all(i.suggested_layout is EventLayout.SEATED for i in filmes)
    assert all(i.suggested_layout is EventLayout.GENERAL for i in shows)


def test_fixtures_de_filme_tem_poster():
    """O pôster carrega o peso visual da vitrine; filme sem pôster fica quebrado."""
    filmes = [i for i in fixtures.FIXTURES if i.source is CatalogSource.TMDB]
    assert all(i.poster_url for i in filmes)


def test_fixtures_refs_sao_unicas():
    refs = [i.ref for i in fixtures.FIXTURES]
    assert len(refs) == len(set(refs))


def test_busca_offline_e_case_insensitive():
    assert fixtures.buscar("PARASITA")
    assert fixtures.buscar("parasita")
    assert fixtures.buscar("  parasita  ")


def test_busca_offline_sem_termo_devolve_tudo():
    assert len(fixtures.buscar("", limit=99)) == len(fixtures.FIXTURES)


def test_busca_offline_respeita_limite():
    assert len(fixtures.buscar("", limit=2)) == 2


def test_obter_por_ref_inexistente():
    assert fixtures.obter("tmdb:movie:000") is None
