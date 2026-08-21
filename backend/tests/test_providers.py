"""Normalização do provedor TMDb.

Testa o mapeamento `resposta do TMDb → CatalogItem` com payloads no formato real
documentado. É a parte que pode estar errada sem que nada quebre visivelmente:
um campo com nome trocado vira `None` silencioso na tela.

A chamada HTTP em si não é testada aqui — bater na API real deixaria a suíte
dependente de chave e de rede.
"""

from datetime import UTC, datetime

import pytest

from app.providers import fixtures
from app.providers.base import CatalogSource, parse_ref
from app.providers.tmdb import TMDbProvider
from app.models.enums import EventLayout


# --- parse_ref ---


def test_parse_ref_valido():
    assert parse_ref("tmdb:movie:550") == (CatalogSource.TMDB, "movie:550")


@pytest.mark.parametrize("ruim", ["", "lixo", "ticketmaster:event:1", ":", "tmdb:"])
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


# --- Fixtures offline ---


def test_fixtures_sao_todas_de_filme():
    """Só o TMDb sobrou como fonte; nada de item de outra origem no fallback."""
    assert all(i.source is CatalogSource.TMDB for i in fixtures.FIXTURES)
    assert all(i.suggested_layout is EventLayout.SEATED for i in fixtures.FIXTURES)


def test_fixtures_tem_poster_e_genero():
    """O pôster carrega o peso visual da vitrine; sem ele o card fica quebrado.

    E o gênero é o que alimenta as pílulas de filtro em modo offline.
    """
    assert all(i.poster_url for i in fixtures.FIXTURES)
    assert all(i.suggested_genre for i in fixtures.FIXTURES)


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
