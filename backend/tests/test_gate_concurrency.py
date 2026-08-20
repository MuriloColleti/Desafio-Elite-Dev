"""O mesmo ingresso não é validado duas vezes.

Exigência explícita do enunciado, e o espelho do problema do assento: aqui a
disputa é entre dois scanners na mesma porta lendo o mesmo QR no mesmo instante.

Exige Postgres real — o que se prova é que o `UPDATE ... WHERE status = 'VALID'`
serializa de fato. Contra banco falso o teste não significaria nada.
"""

import os
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from app.core.security import sign_ticket_code
from app.models.entities import Ticket
from app.models.enums import GateResult, TicketStatus
from app.services import tickets

TEST_DB_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DB_URL, reason="TEST_DATABASE_URL não definida — precisa de Postgres real"
)


@pytest.fixture
def cenario():
    """Um ingresso válido, e o id do usuário de portaria."""
    engine = create_engine(TEST_DB_URL, pool_size=25, max_overflow=10)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    org, cliente, portaria = (str(uuid.uuid4()) for _ in range(3))
    evento, reserva, ingresso = (str(uuid.uuid4()) for _ in range(3))

    with Session() as db:
        for t in ("tickets", "payments", "reservations", "events"):
            db.execute(text(f"DELETE FROM {t}"))
        db.execute(text("UPDATE users SET gate_event_id = NULL"))
        db.execute(text("DELETE FROM users"))
        db.execute(
            text(
                "INSERT INTO users (id,name,email,password_hash,role,created_at,updated_at)"
                " VALUES (:o,'Org','o@t.com','h','ORGANIZER',now(),now()),"
                "        (:c,'Cliente','c@t.com','h','CUSTOMER',now(),now()),"
                "        (:p,'Portaria','p@t.com','h','GATE',now(),now())"
            ),
            {"o": org, "c": cliente, "p": portaria},
        )
        db.execute(
            text(
                "INSERT INTO events (id,organizer_id,title,venue,starts_at,layout,"
                "capacity,price_cents,status,created_at,updated_at)"
                " VALUES (:e,:o,'Filme','Sala',now(),'SEATED',96,3200,'PUBLISHED',now(),now())"
            ),
            {"e": evento, "o": org},
        )
        db.execute(
            text("UPDATE users SET gate_event_id = :e WHERE id = :p"),
            {"e": evento, "p": portaria},
        )
        db.execute(
            text(
                "INSERT INTO reservations (id,event_id,customer_id,seat_label,quantity,"
                "status,created_at,updated_at)"
                " VALUES (:r,:e,:c,'A1',1,'PAID',now(),now())"
            ),
            {"r": reserva, "e": evento, "c": cliente},
        )
        db.execute(
            text(
                "INSERT INTO tickets (id,reservation_id,share_token,status,created_at,updated_at)"
                " VALUES (:t,:r,:s,'VALID',now(),now())"
            ),
            {"t": ingresso, "r": reserva, "s": uuid.uuid4().hex},
        )
        db.commit()

    yield {
        "Session": Session,
        "codigo": sign_ticket_code(ingresso),
        "ticket_id": ingresso,
        "portaria_id": portaria,
        "event_id": evento,
    }

    engine.dispose()


def test_dois_scanners_no_mesmo_qr_so_um_valida(cenario):
    """20 leituras simultâneas do mesmo ingresso: uma entra, 19 são recusadas.

    Se a marcação fosse `ingresso.status = USED` seguido de commit, todas as 20
    leriam VALID antes de qualquer escrita e todas passariam. O que impede isso
    é o UPDATE condicional com checagem de linhas afetadas.
    """
    Session = cenario["Session"]

    def validar(_n: int) -> GateResult:
        with Session() as db:
            resultado, _ = tickets.validar(
                db,
                codigo_lido=cenario["codigo"],
                gate_user_id=cenario["portaria_id"],
                gate_event_id=cenario["event_id"],
            )
            return resultado

    with ThreadPoolExecutor(max_workers=20) as ex:
        resultados = list(ex.map(validar, range(20)))

    validos = resultados.count(GateResult.VALID)
    usados = resultados.count(GateResult.ALREADY_USED)

    assert validos == 1, f"esperado 1 entrada liberada, obtido {validos}"
    assert usados == 19

    with Session() as db:
        ingresso = db.get(Ticket, cenario["ticket_id"])
        assert ingresso.status is TicketStatus.USED
        assert ingresso.used_at is not None
        assert ingresso.used_by_id == cenario["portaria_id"]


def test_segunda_validacao_sequencial_recusa(cenario):
    Session = cenario["Session"]

    with Session() as db:
        primeiro, _ = tickets.validar(
            db,
            codigo_lido=cenario["codigo"],
            gate_user_id=cenario["portaria_id"],
            gate_event_id=cenario["event_id"],
        )
    with Session() as db:
        segundo, ingresso = tickets.validar(
            db,
            codigo_lido=cenario["codigo"],
            gate_user_id=cenario["portaria_id"],
            gate_event_id=cenario["event_id"],
        )

    assert primeiro is GateResult.VALID
    assert segundo is GateResult.ALREADY_USED
    # A resposta informa quando foi usado, para quem está na porta entender.
    assert ingresso.used_at is not None


def test_codigo_forjado_nao_marca_nada(cenario):
    """Sem o segredo do HMAC não se produz um código aceito."""
    Session = cenario["Session"]
    forjado = f"{cenario['ticket_id']}.{'0' * 32}"

    with Session() as db:
        resultado, ingresso = tickets.validar(
            db,
            codigo_lido=forjado,
            gate_user_id=cenario["portaria_id"],
            gate_event_id=cenario["event_id"],
        )

    assert resultado is GateResult.INVALID
    assert ingresso is None

    with Session() as db:
        assert db.get(Ticket, cenario["ticket_id"]).status is TicketStatus.VALID


def test_evento_errado_nao_consome_o_ingresso(cenario):
    """Portaria da porta errada não pode queimar um ingresso legítimo."""
    Session = cenario["Session"]
    outro_evento = str(uuid.uuid4())

    with Session() as db:
        resultado, _ = tickets.validar(
            db,
            codigo_lido=cenario["codigo"],
            gate_user_id=cenario["portaria_id"],
            gate_event_id=outro_evento,
        )

    assert resultado is GateResult.WRONG_EVENT

    with Session() as db:
        assert db.get(Ticket, cenario["ticket_id"]).status is TicketStatus.VALID


def test_evento_errado_tem_prioridade_sobre_ja_usado(cenario):
    """A ordem das checagens: evento antes de estado.

    Um ingresso já usado, apresentado na porta errada, deve responder "evento
    errado" — senão a portaria não descobre que está no lugar errado.
    """
    Session = cenario["Session"]

    with Session() as db:
        tickets.validar(
            db,
            codigo_lido=cenario["codigo"],
            gate_user_id=cenario["portaria_id"],
            gate_event_id=cenario["event_id"],
        )

    with Session() as db:
        resultado, _ = tickets.validar(
            db,
            codigo_lido=cenario["codigo"],
            gate_user_id=cenario["portaria_id"],
            gate_event_id=str(uuid.uuid4()),
        )

    assert resultado is GateResult.WRONG_EVENT


def test_ingresso_cancelado_e_invalido(cenario):
    Session = cenario["Session"]

    with Session() as db:
        db.execute(
            text("UPDATE tickets SET status='CANCELLED' WHERE id=:t"),
            {"t": cenario["ticket_id"]},
        )
        db.commit()

    with Session() as db:
        resultado, _ = tickets.validar(
            db,
            codigo_lido=cenario["codigo"],
            gate_user_id=cenario["portaria_id"],
            gate_event_id=cenario["event_id"],
        )

    assert resultado is GateResult.INVALID
