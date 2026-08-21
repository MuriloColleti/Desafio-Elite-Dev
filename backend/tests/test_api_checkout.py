"""Checkout, ingresso e portaria pela API.

Cobre o fluxo que o enunciado descreve por inteiro: reservar, pagar (recusando e
aprovando), receber o ingresso com QR, compartilhar por link e validar na
entrada.
"""

import pytest

pytestmark = pytest.mark.usefixtures("app_semeado")

CARTAO_OK = "4242424242424242"
CARTAO_RECUSADO = "4000000000000002"


def _reservar(cliente, event_id, **kwargs):
    """Cria e devolve a primeira reserva do grupo.

    A rota sempre responde lista — comprar N assentos são N reservas — e os
    testes de um assento só querem a única.
    """
    r = cliente.post("/reservations", json={"event_id": event_id, **kwargs})
    assert r.status_code == 201, r.text
    return r.json()["reservations"][0]


def _pagar(cliente, *reservation_ids, cartao=CARTAO_OK):
    """Uma cobrança para o grupo de reservas."""
    return cliente.post(
        "/payments",
        json={
            "reservation_ids": list(reservation_ids),
            "card_number": cartao,
            "card_holder": "TITULAR TESTE",
        },
    )


# --- Pagamento aprovado ---


def test_pagamento_aprovado_emite_ingresso(app_semeado):
    clientes, refs = app_semeado
    reserva = _reservar(clientes["bruno"], refs["evento_cinema"], seat_labels=["B5"])

    r = _pagar(clientes["bruno"], reserva["id"])

    assert r.status_code == 201
    corpo = r.json()
    assert corpo["status"] == "APPROVED"
    assert corpo["amount_cents"] == 3200
    assert corpo["ticket_ids"] and corpo["ticket_codes"]


def test_total_multiplica_pela_quantidade(app_semeado):
    clientes, refs = app_semeado
    # Preço lido do evento em vez de fixado: o seed muda, e a regra sob teste é
    # a multiplicação, não o valor.
    preco = clientes["anon"].get(f"/events/{refs['evento_pista']}").json()["price_cents"]
    reserva = _reservar(clientes["bruno"], refs["evento_pista"], quantity=2)

    r = _pagar(clientes["bruno"], reserva["id"])

    assert r.json()["amount_cents"] == preco * 2


# --- Pagamento recusado ---


def test_recusa_responde_402_com_motivo(app_semeado):
    """O enunciado pede a recusa como caminho previsto, não como falha genérica."""
    clientes, refs = app_semeado
    reserva = _reservar(clientes["bruno"], refs["evento_cinema"], seat_labels=["B5"])

    r = _pagar(clientes["bruno"], reserva["id"], cartao=CARTAO_RECUSADO)

    assert r.status_code == 402
    assert r.json()["error"]["code"] == "PAYMENT_DECLINED"
    assert "emissor" in r.json()["error"]["message"].lower()


def test_recusa_devolve_o_assento_ao_estoque(app_semeado):
    """Sem isto surge o assento fantasma: preso a um pagamento que falhou."""
    clientes, refs = app_semeado
    reserva = _reservar(clientes["bruno"], refs["evento_cinema"], seat_labels=["B5"])

    _pagar(clientes["bruno"], reserva["id"], cartao=CARTAO_RECUSADO)

    mapa = clientes["anon"].get(f"/events/{refs['evento_cinema']}").json()["seat_map"]
    assert "B5" not in mapa["taken"]

    # E outra pessoa consegue comprar o lugar.
    assert (
        clientes["ana"]
        .post(
            "/reservations",
            json={"event_id": refs["evento_cinema"], "seat_labels": ["B5"]},
        )
        .status_code
        == 201
    )


def test_recusa_nao_emite_ingresso(app_semeado):
    clientes, refs = app_semeado
    reserva = _reservar(clientes["bruno"], refs["evento_cinema"], seat_labels=["B5"])

    _pagar(clientes["bruno"], reserva["id"], cartao=CARTAO_RECUSADO)

    assert clientes["bruno"].get("/tickets/me").json() == []


@pytest.mark.parametrize(
    ("cartao", "trecho"),
    [
        ("4000000000000002", "emissor"),
        ("4000000000009995", "saldo"),
        ("4000000000000069", "expirado"),
        ("4000000000000127", "segurança"),
    ],
)
def test_cada_cartao_de_teste_tem_seu_motivo(app_semeado, cartao, trecho):
    """Motivos distintos: a tela precisa dizer o que aconteceu."""
    clientes, refs = app_semeado
    reserva = _reservar(clientes["bruno"], refs["evento_pista"], quantity=1)

    r = _pagar(clientes["bruno"], reserva["id"], cartao=cartao)

    assert r.status_code == 402
    assert trecho in r.json()["error"]["message"].lower()


def test_aceita_cartao_com_espacos(app_semeado):
    """O campo de cartão costuma formatar em grupos de quatro."""
    clientes, refs = app_semeado
    reserva = _reservar(clientes["bruno"], refs["evento_cinema"], seat_labels=["B5"])

    r = _pagar(clientes["bruno"], reserva["id"], cartao="4242 4242 4242 4242")

    assert r.status_code == 201


# --- Regras de pagamento ---


def test_nao_paga_reserva_cancelada(app_semeado):
    clientes, refs = app_semeado
    reserva = _reservar(clientes["bruno"], refs["evento_cinema"], seat_labels=["B5"])
    clientes["bruno"].delete(f"/reservations/{reserva['id']}")

    assert _pagar(clientes["bruno"], reserva["id"]).status_code == 422


def test_nao_paga_duas_vezes(app_semeado):
    clientes, refs = app_semeado
    reserva = _reservar(clientes["bruno"], refs["evento_cinema"], seat_labels=["B5"])

    assert _pagar(clientes["bruno"], reserva["id"]).status_code == 201
    assert _pagar(clientes["bruno"], reserva["id"]).status_code == 422


def test_nao_paga_reserva_de_outro_cliente(app_semeado):
    clientes, refs = app_semeado
    reserva = _reservar(clientes["ana"], refs["evento_cinema"], seat_labels=["B5"])

    r = _pagar(clientes["bruno"], reserva["id"])

    assert r.status_code == 404, "não confirmamos a existência de reservas alheias"


def test_pagamento_exige_papel_de_cliente(app_semeado):
    clientes, refs = app_semeado
    r = _pagar(clientes["organizador"], "qualquer-id")
    assert r.status_code == 403


# --- Meus ingressos ---


def test_lista_meus_ingressos(app_semeado):
    clientes, _ = app_semeado
    ingressos = clientes["ana"].get("/tickets/me").json()

    # A Ana tem três no seed: válido, usado e de outro evento.
    assert len(ingressos) == 3
    assert {i["status"] for i in ingressos} == {"VALID", "USED"}


def test_ingresso_traz_dados_do_evento_e_codigo(app_semeado):
    clientes, _ = app_semeado
    ingresso = clientes["ana"].get("/tickets/me").json()[0]

    assert ingresso["event_title"] and ingresso["event_venue"]
    assert ingresso["event_starts_at"]
    assert ingresso["code"] and "." in ingresso["code"]
    assert ingresso["share_url"].startswith("http")


def test_cliente_so_ve_os_proprios_ingressos(app_semeado):
    clientes, _ = app_semeado
    assert clientes["bruno"].get("/tickets/me").json() == []


def test_portaria_nao_tem_meus_ingressos(app_semeado):
    clientes, _ = app_semeado
    assert clientes["portaria"].get("/tickets/me").status_code == 403


# --- QR ---


def test_qr_e_png_valido(app_semeado):
    clientes, _ = app_semeado
    ingresso = clientes["ana"].get("/tickets/me").json()[0]

    r = clientes["ana"].get(f"/tickets/{ingresso['id']}/qr")

    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert r.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_qr_nao_e_cacheado(app_semeado):
    """Ingresso usado não deve seguir exibindo um QR guardado pelo navegador."""
    clientes, _ = app_semeado
    ingresso = clientes["ana"].get("/tickets/me").json()[0]

    r = clientes["ana"].get(f"/tickets/{ingresso['id']}/qr")

    assert r.headers.get("cache-control") == "no-store"


def test_nao_acessa_qr_de_ingresso_alheio(app_semeado):
    clientes, _ = app_semeado
    ingresso = clientes["ana"].get("/tickets/me").json()[0]

    r = clientes["bruno"].get(f"/tickets/{ingresso['id']}/qr")

    assert r.status_code == 404


# --- Link de compartilhamento ---


def test_link_publico_dispensa_autenticacao(app_semeado):
    clientes, refs = app_semeado
    token = refs["share_token_ana"]

    r = clientes["anon"].get(f"/public/tickets/{token}")

    assert r.status_code == 200
    assert r.json()["event_title"]
    assert r.json()["holder_name"] == "Ana Ribeiro"


def test_link_publico_nao_entrega_o_codigo(app_semeado):
    """Compartilhar não é transferir: quem recebe vê, mas não entra."""
    clientes, refs = app_semeado

    corpo = clientes["anon"].get(f"/public/tickets/{refs['share_token_ana']}").json()

    assert "code" not in corpo
    assert "id" not in corpo


def test_token_inexistente_responde_404(app_semeado):
    clientes, _ = app_semeado
    assert clientes["anon"].get("/public/tickets/nao-existe").status_code == 404


# --- Portaria: os quatro resultados ---


def test_portaria_valido(app_semeado):
    clientes, refs = app_semeado

    r = clientes["portaria"].post(
        "/gate/validate", json={"code": refs["ingresso_valido"]}
    )

    assert r.status_code == 200
    corpo = r.json()
    assert corpo["result"] == "VALID"
    assert corpo["holder_name"] and corpo["event_title"]


def test_portaria_ja_utilizado(app_semeado):
    clientes, refs = app_semeado

    r = clientes["portaria"].post(
        "/gate/validate", json={"code": refs["ingresso_usado"]}
    )

    assert r.json()["result"] == "ALREADY_USED"
    assert r.json()["used_at"], "a tela precisa dizer quando foi usado"


def test_portaria_evento_errado(app_semeado):
    clientes, refs = app_semeado

    r = clientes["portaria"].post(
        "/gate/validate", json={"code": refs["ingresso_outro_evento"]}
    )

    assert r.json()["result"] == "WRONG_EVENT"


@pytest.mark.parametrize("codigo", ["qualquer-coisa", "lixo", "abc.def", "   "])
def test_portaria_invalido(app_semeado, codigo):
    clientes, _ = app_semeado

    r = clientes["portaria"].post("/gate/validate", json={"code": codigo})

    assert r.json()["result"] == "INVALID"


def test_portaria_rejeita_hmac_forjado(app_semeado):
    """O requisito de "QR que não pode ser forjado", pelo HTTP."""
    clientes, refs = app_semeado
    ticket_id = refs["ingresso_valido"].split(".")[0]

    r = clientes["portaria"].post(
        "/gate/validate", json={"code": f"{ticket_id}.{'0' * 32}"}
    )

    assert r.json()["result"] == "INVALID"


def test_recusa_da_portaria_responde_200(app_semeado):
    """As três recusas são resultado de negócio, não erro de requisição.

    Com 4xx o front cairia no caminho de falha genérica em vez de mostrar o
    motivo na tela da portaria.
    """
    clientes, refs = app_semeado

    for codigo in (refs["ingresso_usado"], refs["ingresso_outro_evento"], "lixo"):
        r = clientes["portaria"].post("/gate/validate", json={"code": codigo})
        assert r.status_code == 200, codigo


def test_segunda_leitura_do_mesmo_ingresso_recusa(app_semeado):
    clientes, refs = app_semeado
    codigo = refs["ingresso_valido"]

    assert (
        clientes["portaria"].post("/gate/validate", json={"code": codigo}).json()["result"]
        == "VALID"
    )
    assert (
        clientes["portaria"].post("/gate/validate", json={"code": codigo}).json()["result"]
        == "ALREADY_USED"
    )


def test_apenas_portaria_valida(app_semeado):
    clientes, refs = app_semeado
    corpo = {"code": refs["ingresso_valido"]}

    assert clientes["ana"].post("/gate/validate", json=corpo).status_code == 403
    assert clientes["organizador"].post("/gate/validate", json=corpo).status_code == 403
    assert clientes["anon"].post("/gate/validate", json=corpo).status_code == 401


# --- Fluxo completo ---


def test_compra_completa_ate_a_entrada(app_semeado):
    """Reservar → pagar → receber ingresso → validar na entrada."""
    clientes, refs = app_semeado

    reserva = _reservar(clientes["bruno"], refs["evento_cinema"], seat_labels=["B5"])
    pagamento = _pagar(clientes["bruno"], reserva["id"]).json()

    ingressos = clientes["bruno"].get("/tickets/me").json()
    assert len(ingressos) == 1
    assert ingressos[0]["seat_label"] == "B5"
    assert ingressos[0]["status"] == "VALID"

    r = clientes["portaria"].post(
        "/gate/validate", json={"code": pagamento["ticket_codes"][0]}
    )
    assert r.json()["result"] == "VALID"
    assert r.json()["seat_label"] == "B5"

    # E o ingresso passa a constar como usado para o cliente.
    assert clientes["bruno"].get("/tickets/me").json()[0]["status"] == "USED"


# --- Compra de vários assentos ---


def test_reserva_varios_assentos_de_uma_vez(app_semeado):
    """O caso que faltava: comprar mais de um lugar na mesma ida ao cinema."""
    clientes, refs = app_semeado

    r = clientes["bruno"].post(
        "/reservations",
        json={"event_id": refs["evento_cinema"], "seat_labels": ["A1", "A2", "A3"]},
    )

    assert r.status_code == 201
    corpo = r.json()
    # Uma reserva por assento: a constraint de unicidade é (event_id, seat_label),
    # então um registro não pode representar três lugares.
    assert len(corpo["reservations"]) == 3
    assert {x["seat_label"] for x in corpo["reservations"]} == {"A1", "A2", "A3"}
    assert corpo["total_cents"] == 3200 * 3


def test_um_pagamento_cobre_o_grupo(app_semeado):
    """A pessoa digitou o cartão uma vez e espera uma linha no extrato."""
    clientes, refs = app_semeado
    grupo = clientes["bruno"].post(
        "/reservations",
        json={"event_id": refs["evento_cinema"], "seat_labels": ["A1", "A2"]},
    ).json()

    r = _pagar(clientes["bruno"], *[x["id"] for x in grupo["reservations"]])

    assert r.status_code == 201
    assert r.json()["amount_cents"] == 3200 * 2
    assert len(r.json()["ticket_ids"]) == 2


def test_emite_um_ingresso_por_assento(app_semeado):
    clientes, refs = app_semeado
    grupo = clientes["bruno"].post(
        "/reservations",
        json={"event_id": refs["evento_cinema"], "seat_labels": ["A1", "A2", "A3"]},
    ).json()
    _pagar(clientes["bruno"], *[x["id"] for x in grupo["reservations"]])

    ingressos = clientes["bruno"].get("/tickets/me").json()

    assert len(ingressos) == 3
    assert {i["seat_label"] for i in ingressos} == {"A1", "A2", "A3"}


def test_recusa_cancela_o_grupo_inteiro(app_semeado):
    """Deixar dois pagos e dois cancelados entregaria metade do pedido.

    Quem compra quatro lugares quer sentar junto.
    """
    clientes, refs = app_semeado
    grupo = clientes["bruno"].post(
        "/reservations",
        json={"event_id": refs["evento_cinema"], "seat_labels": ["A1", "A2"]},
    ).json()

    r = _pagar(
        clientes["bruno"],
        *[x["id"] for x in grupo["reservations"]],
        cartao=CARTAO_RECUSADO,
    )

    assert r.status_code == 402
    mapa = clientes["anon"].get(f"/events/{refs['evento_cinema']}").json()["seat_map"]
    assert "A1" not in mapa["taken"]
    assert "A2" not in mapa["taken"]
    assert clientes["bruno"].get("/tickets/me").json() == []


def test_reserva_e_tudo_ou_nada(app_semeado):
    """Se um assento do grupo se perder, nenhum fica reservado.

    Deixar dois presos num hold que o cliente não vai pagar bloqueia lugares
    de graça — ele queria os três.
    """
    clientes, refs = app_semeado
    # C4 já está vendido no seed.
    r = clientes["bruno"].post(
        "/reservations",
        json={"event_id": refs["evento_cinema"], "seat_labels": ["A1", "C4", "A2"]},
    )

    assert r.status_code == 409
    assert r.json()["error"]["code"] == "SEAT_TAKEN"

    mapa = clientes["anon"].get(f"/events/{refs['evento_cinema']}").json()["seat_map"]
    assert "A1" not in mapa["taken"], "A1 não deveria ter ficado preso"
    assert "A2" not in mapa["taken"], "A2 não deveria ter ficado preso"


def test_rejeita_assento_repetido_na_escolha(app_semeado):
    """Erro de entrada, não corrida: a mensagem tem de dizer isso."""
    clientes, refs = app_semeado

    r = clientes["bruno"].post(
        "/reservations",
        json={"event_id": refs["evento_cinema"], "seat_labels": ["A1", "a1"]},
    )

    assert r.status_code == 422, "'a1' e 'A1' são o mesmo lugar"


def test_limita_assentos_por_compra(app_semeado):
    """Sem limite, uma pessoa bloquearia meia fileira durante o hold."""
    clientes, refs = app_semeado

    r = clientes["bruno"].post(
        "/reservations",
        json={
            "event_id": refs["evento_cinema"],
            "seat_labels": ["A1", "A2", "A3", "A4", "A5", "A6", "A7"],
        },
    )

    assert r.status_code == 422


def test_nao_paga_grupo_de_outro_cliente(app_semeado):
    """Basta uma reserva alheia no lote para o pagamento inteiro cair."""
    clientes, refs = app_semeado
    meu = clientes["bruno"].post(
        "/reservations", json={"event_id": refs["evento_cinema"], "seat_labels": ["A1"]}
    ).json()["reservations"][0]
    alheio = clientes["ana"].post(
        "/reservations", json={"event_id": refs["evento_cinema"], "seat_labels": ["A2"]}
    ).json()["reservations"][0]

    r = _pagar(clientes["bruno"], meu["id"], alheio["id"])

    assert r.status_code == 404
