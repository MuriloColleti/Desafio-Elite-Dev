"""O assento não pode ser vendido duas vezes.

Este teste exige um Postgres de verdade — e isso é proposital. O índice parcial
é a regra em si, não um detalhe de infraestrutura; testá-lo contra um banco
falso provaria nada. Sem `TEST_DATABASE_URL` os testes são pulados, não
silenciosamente aprovados.

    docker run -d --name palco-test-pg -e POSTGRES_USER=palco \\
      -e POSTGRES_PASSWORD=palco -e POSTGRES_DB=palco -p 5432:5432 postgres:16-alpine
    export TEST_DATABASE_URL=postgresql+psycopg://palco:palco@localhost:5432/palco
    alembic upgrade head
    pytest tests/test_seat_uniqueness.py
"""

import os
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

TEST_DB_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DB_URL,
    reason="TEST_DATABASE_URL não definida — precisa de Postgres real (ver docstring)",
)

SEAT = "F7"


@pytest.fixture(scope="module")
def sessionmaker_():
    engine = create_engine(TEST_DB_URL, pool_size=25, max_overflow=10)
    yield sessionmaker(bind=engine)
    engine.dispose()


@pytest.fixture
def evento(sessionmaker_):
    """Um evento com assentos, e o banco limpo."""
    org, cust, evt = (str(uuid.uuid4()) for _ in range(3))

    with sessionmaker_() as s:
        for tabela in ("tickets", "payments", "reservations", "events"):
            s.execute(text(f"DELETE FROM {tabela}"))
        s.execute(text("UPDATE users SET gate_event_id = NULL"))
        s.execute(text("DELETE FROM users"))
        s.execute(
            text(
                "INSERT INTO users (id,name,email,password_hash,role,created_at,updated_at)"
                " VALUES (:o,'Org','org@t.com','h','ORGANIZER',now(),now()),"
                "        (:c,'Cli','cli@t.com','h','CUSTOMER',now(),now())"
            ),
            {"o": org, "c": cust},
        )
        s.execute(
            text(
                "INSERT INTO events (id,organizer_id,title,venue,starts_at,layout,"
                "capacity,price_cents,status,created_at,updated_at)"
                " VALUES (:e,:o,'Filme','Sala 1',now(),'SEATED',96,4500,'PUBLISHED',now(),now())"
            ),
            {"e": evt, "o": org},
        )
        s.commit()

    return {"event_id": evt, "customer_id": cust}


def _reservar(sessionmaker_, evento, seat_label=SEAT, quantity=1, status="PENDING"):
    """Insere uma reserva. Devolve True se venceu, False se bateu na constraint."""
    try:
        with sessionmaker_() as s:
            s.execute(
                text(
                    "INSERT INTO reservations (id,event_id,customer_id,seat_label,"
                    "quantity,status,created_at,updated_at)"
                    " VALUES (:i,:e,:c,:sl,:q,:st,now(),now())"
                ),
                {
                    "i": str(uuid.uuid4()),
                    "e": evento["event_id"],
                    "c": evento["customer_id"],
                    "sl": seat_label,
                    "q": quantity,
                    "st": status,
                },
            )
            s.commit()
        return True
    except IntegrityError:
        return False


def test_reservas_simultaneas_no_mesmo_assento_uma_vence(sessionmaker_, evento):
    """20 pessoas clicam no mesmo lugar no mesmo instante: uma leva.

    Checar "está livre?" antes de inserir não resolveria — as 20 passariam pelo
    check. Quem serializa é o Postgres, via o índice único parcial.
    """
    with ThreadPoolExecutor(max_workers=20) as ex:
        vitorias = list(ex.map(lambda _: _reservar(sessionmaker_, evento), range(20)))

    assert sum(vitorias) == 1, f"esperado 1 vencedor, obtido {sum(vitorias)}"

    with sessionmaker_() as s:
        n = s.execute(
            text(
                "SELECT count(*) FROM reservations"
                " WHERE event_id=:e AND seat_label=:s AND status IN ('PENDING','PAID')"
            ),
            {"e": evento["event_id"], "s": SEAT},
        ).scalar()
    assert n == 1


def test_segunda_reserva_sequencial_e_bloqueada(sessionmaker_, evento):
    assert _reservar(sessionmaker_, evento) is True
    assert _reservar(sessionmaker_, evento) is False


@pytest.mark.parametrize("status_final", ["CANCELLED", "EXPIRED"])
def test_reserva_encerrada_devolve_assento(sessionmaker_, evento, status_final):
    """Cancelar/expirar tira a reserva do índice, sem rotina de limpeza."""
    assert _reservar(sessionmaker_, evento) is True
    assert _reservar(sessionmaker_, evento) is False

    with sessionmaker_() as s:
        s.execute(
            text("UPDATE reservations SET status=:st WHERE seat_label=:s"),
            {"st": status_final, "s": SEAT},
        )
        s.commit()

    assert _reservar(sessionmaker_, evento) is True, "assento deveria ter voltado"


def test_pista_nao_e_limitada_pelo_indice(sessionmaker_, evento):
    """Layout GENERAL usa seat_label NULL e fica fora do índice.

    Se o índice não fosse parcial, a segunda compra de pista falharia — este
    teste é o que garante que os dois layouts convivem no mesmo modelo.
    """
    vitorias = [
        _reservar(sessionmaker_, evento, seat_label=None, quantity=2) for _ in range(5)
    ]
    assert all(vitorias), f"pista não deveria ser bloqueada: {vitorias}"


def test_assentos_diferentes_nao_conflitam(sessionmaker_, evento):
    assert _reservar(sessionmaker_, evento, seat_label="A1") is True
    assert _reservar(sessionmaker_, evento, seat_label="A2") is True


def test_mesmo_rotulo_em_eventos_diferentes_coexiste(sessionmaker_, evento):
    """Duas salas de mesmo tamanho não conflitam.

    A unicidade é do par `(event_id, seat_label)`: `C1` do Filme A e `C1` do
    Filme B são chaves diferentes. Se o índice fosse só sobre `seat_label`, a
    segunda sala nunca venderia — e a sessão das 21h herdaria os assentos
    ocupados da das 18h, já que são dois eventos na mesma sala.
    """
    outro_evento = str(uuid.uuid4())
    with sessionmaker_() as s:
        s.execute(
            text(
                "INSERT INTO events (id,organizer_id,title,venue,starts_at,layout,"
                "seat_rows,seats_per_row,capacity,price_cents,status,created_at,updated_at)"
                " SELECT :novo, organizer_id, 'Outro Filme', 'Sala 2', starts_at,"
                " 'SEATED', 8, 12, 96, price_cents, 'PUBLISHED', now(), now()"
                " FROM events WHERE id = :orig"
            ),
            {"novo": outro_evento, "orig": evento["event_id"]},
        )
        s.commit()

    assert _reservar(sessionmaker_, evento) is True

    # Mesmo rótulo, outro evento: precisa passar.
    outro = {"event_id": outro_evento, "customer_id": evento["customer_id"]}
    assert _reservar(sessionmaker_, outro) is True

    # E dentro de cada evento a unicidade continua valendo.
    assert _reservar(sessionmaker_, evento) is False
    assert _reservar(sessionmaker_, outro) is False

    with sessionmaker_() as s:
        total = s.execute(
            text("SELECT count(*) FROM reservations WHERE seat_label = :s"),
            {"s": SEAT},
        ).scalar()
    assert total == 2, "uma reserva do mesmo rótulo por evento"
