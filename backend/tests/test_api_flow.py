"""Fluxo de vitrine, evento e reserva pela API.

Testa pelo HTTP e não pelo serviço: é o que garante que as guardas de papel, os
códigos de erro e os schemas estão de fato ligados nas rotas. Um serviço correto
com uma rota sem guarda passaria num teste de unidade.
"""

from datetime import UTC, datetime, timedelta

import pytest

pytestmark = pytest.mark.usefixtures("app_semeado")


def _futuro(dias: int = 30) -> str:
    return (datetime.now(UTC) + timedelta(days=dias)).isoformat()


# --- Vitrine (pública) ---


def test_vitrine_dispensa_autenticacao(app_semeado):
    """A vitrine é a porta de entrada: exigir login afastaria o visitante."""
    clientes, _ = app_semeado
    r = clientes["anon"].get("/events")

    assert r.status_code == 200
    # Quantidade não é afirmada: o seed cresce, e um teste que trava o número
    # vira manutenção sem valor. O que importa é a vitrine responder com
    # eventos a quem não fez login.
    assert len(r.json()) > 0


def test_vitrine_traz_data_local_e_preco(app_semeado):
    """Exigência literal do enunciado."""
    clientes, _ = app_semeado
    evento = clientes["anon"].get("/events").json()[0]

    assert evento["starts_at"] and evento["venue"] and evento["price_cents"]


def test_vitrine_omite_rascunho_e_cancelado(app_semeado):
    clientes, _ = app_semeado
    assert all(e["status"] == "PUBLISHED" for e in clientes["anon"].get("/events").json())


def test_vitrine_ordena_por_data_crescente(app_semeado):
    """Quem abre a vitrine quer o que dá para assistir logo."""
    clientes, _ = app_semeado
    datas = [e["starts_at"] for e in clientes["anon"].get("/events").json()]
    assert datas == sorted(datas)


def test_vitrine_desconta_lugares_ocupados(app_semeado):
    clientes, _ = app_semeado
    cinema = next(
        e for e in clientes["anon"].get("/events").json() if e["layout"] == "SEATED"
    )
    assert cinema["available"] == cinema["capacity"] - 10


@pytest.mark.parametrize("termo", ["parasita", "PARASITA", "parasi"])
def test_busca_por_titulo(app_semeado, termo):
    clientes, _ = app_semeado
    assert len(clientes["anon"].get(f"/events?q={termo}").json()) == 1


def test_busca_por_local(app_semeado):
    """As pessoas procuram tanto pelo filme quanto pela casa de show."""
    clientes, _ = app_semeado
    assert len(clientes["anon"].get("/events?q=Circo").json()) == 1


def test_filtro_por_layout(app_semeado):
    clientes, _ = app_semeado
    r = clientes["anon"].get("/events?layout=GENERAL").json()

    assert r, "o seed deveria ter evento de pista"
    assert all(e["layout"] == "GENERAL" for e in r)


def test_rascunho_responde_404_nao_403(app_semeado):
    """A existência de um evento não publicado não é informação pública."""
    clientes, refs = app_semeado
    # O rascunho não está em refs; buscamos pelo painel do organizador.
    rascunhos = [
        e
        for e in clientes["organizador"].get("/organizer/events").json()
        if e["status"] == "DRAFT"
    ]
    assert rascunhos, "o seed deveria ter um rascunho"

    r = clientes["anon"].get(f"/events/{rascunhos[0]['id']}")
    assert r.status_code == 404


# --- Mapa de assentos ---


def test_detalhe_traz_mapa_com_ocupados(app_semeado):
    clientes, refs = app_semeado
    mapa = clientes["anon"].get(f"/events/{refs['evento_cinema']}").json()["seat_map"]

    assert mapa["rows"] == 8 and mapa["seats_per_row"] == 12
    assert len(mapa["taken"]) == 10, "o seed ocupa 10 lugares"


def test_evento_de_pista_nao_tem_mapa(app_semeado):
    clientes, refs = app_semeado
    assert clientes["anon"].get(f"/events/{refs['evento_show']}").json()["seat_map"] is None


# --- Reserva com assento ---


def test_reserva_cria_hold_com_prazo(app_semeado):
    """Sem prazo, um assento abandonado no checkout ficaria preso para sempre."""
    clientes, refs = app_semeado
    r = clientes["bruno"].post(
        "/reservations", json={"event_id": refs["evento_cinema"], "seat_label": "A1"}
    )

    assert r.status_code == 201
    assert r.json()["status"] == "PENDING"
    assert r.json()["expires_at"] is not None


def test_hold_ocupa_o_assento_imediatamente(app_semeado):
    """A disputa se resolve no clique, não no pagamento."""
    clientes, refs = app_semeado
    clientes["bruno"].post(
        "/reservations", json={"event_id": refs["evento_cinema"], "seat_label": "A1"}
    )

    mapa = clientes["anon"].get(f"/events/{refs['evento_cinema']}").json()["seat_map"]
    assert "A1" in mapa["taken"]


def test_segundo_cliente_recebe_seat_taken(app_semeado):
    """O caso central do enunciado: o mesmo lugar não se vende duas vezes."""
    clientes, refs = app_semeado
    corpo = {"event_id": refs["evento_cinema"], "seat_label": "A1"}

    assert clientes["bruno"].post("/reservations", json=corpo).status_code == 201

    r = clientes["ana"].post("/reservations", json=corpo)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "SEAT_TAKEN"


def test_assento_vendido_no_seed_esta_bloqueado(app_semeado):
    clientes, refs = app_semeado
    r = clientes["bruno"].post(
        "/reservations", json={"event_id": refs["evento_cinema"], "seat_label": "C4"}
    )
    assert r.status_code == 409


def test_calcula_o_total(app_semeado):
    clientes, refs = app_semeado
    r = clientes["bruno"].post(
        "/reservations", json={"event_id": refs["evento_cinema"], "seat_label": "A1"}
    )
    assert r.json()["total_cents"] == 3200


@pytest.mark.parametrize(
    ("rotulo", "motivo"),
    [
        ("Z1", "fileira além das 8 do mapa"),
        ("A99", "número além dos 12 por fileira"),
        ("lixo", "formato inválido"),
        ("1A", "invertido"),
    ],
)
def test_rejeita_assento_fora_do_mapa(app_semeado, rotulo, motivo):
    """A constraint aceitaria "Z99" (é único), mas o assento não existe na sala."""
    clientes, refs = app_semeado
    r = clientes["bruno"].post(
        "/reservations", json={"event_id": refs["evento_cinema"], "seat_label": rotulo}
    )
    assert r.status_code == 422, motivo


def test_assento_e_case_insensitive(app_semeado):
    clientes, refs = app_semeado
    r = clientes["bruno"].post(
        "/reservations", json={"event_id": refs["evento_cinema"], "seat_label": "a1"}
    )
    assert r.status_code == 201


# --- Reserva de pista ---


def test_reserva_de_pista_por_quantidade(app_semeado):
    clientes, refs = app_semeado
    r = clientes["bruno"].post(
        "/reservations", json={"event_id": refs["evento_show"], "quantity": 3}
    )

    assert r.status_code == 201
    assert r.json()["seat_label"] is None
    assert r.json()["total_cents"] == 9000 * 3


def test_reservas_de_pista_coexistem(app_semeado):
    """O índice é parcial: sem assento, não há o que conflitar."""
    clientes, refs = app_semeado
    corpo = {"event_id": refs["evento_show"], "quantity": 2}

    assert clientes["bruno"].post("/reservations", json=corpo).status_code == 201
    assert clientes["ana"].post("/reservations", json=corpo).status_code == 201


def test_pista_recusa_assento(app_semeado):
    clientes, refs = app_semeado
    r = clientes["bruno"].post(
        "/reservations", json={"event_id": refs["evento_show"], "seat_label": "A1"}
    )
    assert r.status_code == 422


def test_evento_com_assento_exige_assento(app_semeado):
    clientes, refs = app_semeado
    r = clientes["bruno"].post(
        "/reservations", json={"event_id": refs["evento_cinema"], "quantity": 1}
    )
    assert r.status_code == 422


# --- Liberar reserva ---


def test_liberar_devolve_o_assento_ao_estoque(app_semeado):
    """Sair do índice de unicidade é o que devolve o lugar."""
    clientes, refs = app_semeado
    corpo = {"event_id": refs["evento_cinema"], "seat_label": "A1"}

    reserva = clientes["bruno"].post("/reservations", json=corpo).json()
    r = clientes["bruno"].delete(f"/reservations/{reserva['id']}")

    assert r.status_code == 200 and r.json()["status"] == "CANCELLED"

    mapa = clientes["anon"].get(f"/events/{refs['evento_cinema']}").json()["seat_map"]
    assert "A1" not in mapa["taken"]

    # E outra pessoa consegue reservar.
    assert clientes["ana"].post("/reservations", json=corpo).status_code == 201


def test_nao_libera_reserva_de_outro_cliente(app_semeado):
    """404 e não 403: não confirmamos a existência de reservas alheias."""
    clientes, refs = app_semeado
    reserva = clientes["bruno"].post(
        "/reservations", json={"event_id": refs["evento_cinema"], "seat_label": "A1"}
    ).json()

    r = clientes["ana"].delete(f"/reservations/{reserva['id']}")
    assert r.status_code == 404


def test_liberar_duas_vezes_e_idempotente(app_semeado):
    clientes, refs = app_semeado
    reserva = clientes["bruno"].post(
        "/reservations", json={"event_id": refs["evento_cinema"], "seat_label": "A1"}
    ).json()

    assert clientes["bruno"].delete(f"/reservations/{reserva['id']}").status_code == 200
    assert clientes["bruno"].delete(f"/reservations/{reserva['id']}").status_code == 200


# --- Guardas de papel ---


def test_organizador_nao_reserva(app_semeado):
    """Os três papéis são disjuntos: organizador não compra."""
    clientes, refs = app_semeado
    r = clientes["organizador"].post(
        "/reservations", json={"event_id": refs["evento_cinema"], "seat_label": "B1"}
    )
    assert r.status_code == 403


def test_cliente_nao_acessa_painel_do_organizador(app_semeado):
    clientes, _ = app_semeado
    assert clientes["ana"].get("/organizer/events").status_code == 403


def test_portaria_nao_reserva(app_semeado):
    clientes, refs = app_semeado
    r = clientes["portaria"].post(
        "/reservations", json={"event_id": refs["evento_cinema"], "seat_label": "B1"}
    )
    assert r.status_code == 403


def test_reserva_exige_autenticacao(app_semeado):
    clientes, refs = app_semeado
    r = clientes["anon"].post(
        "/reservations", json={"event_id": refs["evento_cinema"], "seat_label": "B1"}
    )
    assert r.status_code == 401


# --- Criação de evento ---


def test_cria_evento_a_partir_do_catalogo(app_semeado):
    """O snapshot é copiado agora: a vitrine não depende da API externa depois."""
    clientes, _ = app_semeado
    r = clientes["organizador"].post(
        "/organizer/events",
        json={
            "catalog_ref": "tmdb:movie:129",
            "venue": "Cine Sala 3",
            "starts_at": _futuro(),
            "layout": "SEATED",
            "price_cents": 2500,
            "seat_rows": 5,
            "seats_per_row": 10,
            "publish": True,
        },
    )

    assert r.status_code == 201
    corpo = r.json()
    assert corpo["title"] == "A Viagem de Chihiro"
    assert corpo["poster_url"] and corpo["synopsis"]


def test_capacidade_e_derivada_do_mapa(app_semeado):
    """Dois campos livres divergiriam e o mapa não fecharia com o total."""
    clientes, _ = app_semeado
    r = clientes["organizador"].post(
        "/organizer/events",
        json={
            "title": "Sessão",
            "venue": "Sala",
            "starts_at": _futuro(),
            "layout": "SEATED",
            "price_cents": 1000,
            "seat_rows": 5,
            "seats_per_row": 10,
        },
    )
    assert r.json()["capacity"] == 50


def test_evento_publicado_aparece_na_vitrine(app_semeado):
    clientes, _ = app_semeado
    novo = clientes["organizador"].post(
        "/organizer/events",
        json={
            "title": "Novo Show",
            "venue": "Arena",
            "starts_at": _futuro(),
            "layout": "GENERAL",
            "price_cents": 5000,
            "capacity": 100,
            "publish": True,
        },
    ).json()

    ids = [e["id"] for e in clientes["anon"].get("/events").json()]
    assert novo["id"] in ids


def test_sem_publish_fica_rascunho_fora_da_vitrine(app_semeado):
    clientes, _ = app_semeado
    novo = clientes["organizador"].post(
        "/organizer/events",
        json={
            "title": "Rascunho",
            "venue": "X",
            "starts_at": _futuro(),
            "layout": "GENERAL",
            "price_cents": 1000,
            "capacity": 50,
        },
    ).json()

    assert novo["status"] == "DRAFT"
    assert novo["id"] not in [e["id"] for e in clientes["anon"].get("/events").json()]


@pytest.mark.parametrize(
    ("corpo", "motivo"),
    [
        (
            {"title": "X", "venue": "V", "layout": "GENERAL", "price_cents": 100, "capacity": 10},
            "data no passado",
        ),
        (
            {"venue": "V", "layout": "GENERAL", "price_cents": 100, "capacity": 10},
            "sem título nem catalog_ref",
        ),
        ({"title": "X", "venue": "V", "layout": "SEATED", "price_cents": 100}, "SEATED sem mapa"),
        (
            {"title": "X", "venue": "V", "layout": "GENERAL", "price_cents": 100},
            "GENERAL sem capacidade",
        ),
        (
            {
                "catalog_ref": "tmdb:movie:999999",
                "venue": "V",
                "layout": "SEATED",
                "price_cents": 100,
                "seat_rows": 2,
                "seats_per_row": 2,
            },
            "catalog_ref inexistente",
        ),
    ],
)
def test_rejeita_criacao_invalida(app_semeado, corpo, motivo):
    clientes, _ = app_semeado
    body = {**corpo}
    body.setdefault(
        "starts_at",
        (datetime.now(UTC) - timedelta(days=1)).isoformat()
        if motivo == "data no passado"
        else _futuro(),
    )

    r = clientes["organizador"].post("/organizer/events", json=body)
    assert r.status_code == 422, motivo


# --- Edição ---


def test_edita_local(app_semeado):
    clientes, refs = app_semeado
    r = clientes["organizador"].patch(
        f"/organizer/events/{refs['evento_cinema']}", json={"venue": "Nova Sala"}
    )
    assert r.status_code == 200 and r.json()["venue"] == "Nova Sala"


def test_nao_muda_preco_com_ingresso_vendido(app_semeado):
    """Quem já pagou pagou outro valor; mudar criaria duas verdades."""
    clientes, refs = app_semeado
    r = clientes["organizador"].patch(
        f"/organizer/events/{refs['evento_cinema']}", json={"price_cents": 5000}
    )
    assert r.status_code == 422


def test_nao_reduz_capacidade_abaixo_do_vendido(app_semeado):
    clientes, refs = app_semeado
    r = clientes["organizador"].patch(
        f"/organizer/events/{refs['evento_show']}", json={"capacity": 1}
    )
    assert r.status_code == 422


def test_capacidade_de_evento_com_assento_vem_do_mapa(app_semeado):
    clientes, refs = app_semeado
    r = clientes["organizador"].patch(
        f"/organizer/events/{refs['evento_cinema']}", json={"capacity": 200}
    )
    assert r.status_code == 422


# --- Cancelamento ---


def test_cancelar_remove_da_vitrine(app_semeado):
    clientes, refs = app_semeado
    r = clientes["organizador"].delete(f"/organizer/events/{refs['evento_show']}")

    assert r.status_code == 200 and r.json()["status"] == "CANCELLED"
    ids = [e["id"] for e in clientes["anon"].get("/events").json()]
    assert refs["evento_show"] not in ids


def test_evento_cancelado_nao_aceita_reserva(app_semeado):
    clientes, refs = app_semeado
    clientes["organizador"].delete(f"/organizer/events/{refs['evento_show']}")

    r = clientes["bruno"].post(
        "/reservations", json={"event_id": refs["evento_show"], "quantity": 1}
    )
    assert r.status_code == 422


def test_cancelar_e_idempotente(app_semeado):
    clientes, refs = app_semeado
    url = f"/organizer/events/{refs['evento_show']}"

    assert clientes["organizador"].delete(url).status_code == 200
    assert clientes["organizador"].delete(url).status_code == 200
