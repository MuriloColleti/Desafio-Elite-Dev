"""O seed entrega o que o enunciado exige.

O PDF é explícito: um organizador, dois clientes, um usuário de portaria e ao
menos um evento publicado com ingressos disponíveis. Este teste é a garantia de
que o roteiro de avaliação do README funciona de verdade — se o seed quebrar, o
avaliador trava na primeira tela.
"""

import os

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.core.security import verify_password, verify_ticket_code
from app.models.entities import Event, Reservation, Ticket, User
from app.models.enums import EventLayout, EventStatus, Role, TicketStatus
from app.seed import SENHA, limpar, povoar

TEST_DB_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DB_URL, reason="TEST_DATABASE_URL não definida — precisa de Postgres real"
)


@pytest.fixture(scope="module")
def db_semeado():
    engine = create_engine(TEST_DB_URL)
    Session = sessionmaker(bind=engine)

    with Session() as db:
        limpar(db)
        refs = povoar(db)

    with Session() as db:
        yield db, refs

    engine.dispose()


# --- Usuários ---


def test_cria_os_quatro_usuarios_exigidos(db_semeado):
    db, _ = db_semeado
    papeis = dict(
        db.execute(select(User.role, func.count(User.id)).group_by(User.role)).all()
    )

    assert papeis[Role.ORGANIZER] == 1
    assert papeis[Role.CUSTOMER] == 2, "o PDF pede dois clientes"
    assert papeis[Role.GATE] == 1


def test_senha_documentada_funciona(db_semeado):
    """Se a senha do README não logar, o avaliador para na tela de login."""
    db, _ = db_semeado
    for email in (
        "organizador@palco.dev",
        "ana@palco.dev",
        "bruno@palco.dev",
        "portaria@palco.dev",
    ):
        u = db.scalar(select(User).where(User.email == email))
        assert u is not None, f"{email} não foi criado"
        assert verify_password(SENHA, u.password_hash), f"senha não confere para {email}"


def test_portaria_esta_vinculada_a_um_evento(db_semeado):
    """Sem vínculo não há como responder "evento errado"."""
    db, _ = db_semeado
    portaria = db.scalar(select(User).where(User.role == Role.GATE))
    assert portaria.gate_event_id is not None

    evento = db.get(Event, portaria.gate_event_id)
    assert evento.status is EventStatus.PUBLISHED


# --- Eventos ---


def test_tem_evento_publicado_com_ingresso_disponivel(db_semeado):
    """Exigência literal do PDF."""
    db, _ = db_semeado
    publicados = db.scalars(
        select(Event).where(Event.status == EventStatus.PUBLISHED)
    ).all()

    assert len(publicados) >= 1

    for e in publicados:
        vendidos = db.scalar(
            select(func.coalesce(func.sum(Reservation.quantity), 0)).where(
                Reservation.event_id == e.id,
                Reservation.status.in_(("PENDING", "PAID")),
            )
        )
        assert vendidos < e.capacity, f"{e.title} não tem lugar disponível"


def test_cobre_os_dois_layouts_de_reserva(db_semeado):
    """Mapa de assentos e pista, para o avaliador ver os dois fluxos."""
    db, _ = db_semeado
    layouts = {
        e.layout
        for e in db.scalars(
            select(Event).where(Event.status == EventStatus.PUBLISHED)
        ).all()
    }
    assert EventLayout.SEATED in layouts
    assert EventLayout.GENERAL in layouts


def test_evento_com_assentos_tem_dimensoes_do_mapa(db_semeado):
    db, _ = db_semeado
    for e in db.scalars(select(Event).where(Event.layout == EventLayout.SEATED)).all():
        assert e.seat_rows and e.seats_per_row
        assert e.seat_rows * e.seats_per_row == e.capacity, (
            f"{e.title}: capacidade não bate com o mapa"
        )


def test_tem_rascunho_para_o_painel_do_organizador(db_semeado):
    db, _ = db_semeado
    assert db.scalar(select(Event).where(Event.status == EventStatus.DRAFT)) is not None


def test_eventos_estao_no_futuro(db_semeado):
    """Datas relativas: o seed não pode envelhecer e sumir da vitrine."""
    db, _ = db_semeado
    from datetime import UTC, datetime

    agora = datetime.now(UTC)
    for e in db.scalars(
        select(Event).where(Event.status == EventStatus.PUBLISHED)
    ).all():
        assert e.starts_at > agora, f"{e.title} já passou"


def test_precos_sao_inteiros_positivos(db_semeado):
    db, _ = db_semeado
    for e in db.scalars(select(Event)).all():
        assert isinstance(e.price_cents, int) and e.price_cents > 0


# --- Assentos ocupados ---


def test_mapa_tem_assentos_ocupados(db_semeado):
    """Mapa vazio não demonstra que a indisponibilidade funciona."""
    db, _ = db_semeado
    ocupados = db.scalar(
        select(func.count(Reservation.id)).where(
            Reservation.seat_label.is_not(None),
            Reservation.status == "PAID",
        )
    )
    assert ocupados >= 5


# --- Ingressos (os três casos da portaria) ---


def test_tem_ingresso_valido_usado_e_de_outro_evento(db_semeado):
    db, _ = db_semeado
    status = {t.status for t in db.scalars(select(Ticket)).all()}
    assert TicketStatus.VALID in status
    assert TicketStatus.USED in status


def test_codigos_impressos_pelo_seed_sao_validos(db_semeado):
    """O seed imprime códigos para colar na portaria — precisam funcionar."""
    db, refs = db_semeado

    for chave in ("ingresso_valido", "ingresso_usado", "ingresso_outro_evento"):
        ticket_id = verify_ticket_code(refs[chave])
        assert ticket_id is not None, f"{chave}: HMAC não confere"
        assert db.get(Ticket, ticket_id) is not None, f"{chave}: ingresso não existe"


def test_ingresso_de_outro_evento_e_de_evento_diferente_da_portaria(db_semeado):
    """Senão o caso "evento errado" não é testável."""
    db, refs = db_semeado

    portaria = db.scalar(select(User).where(User.role == Role.GATE))
    ticket_id = verify_ticket_code(refs["ingresso_outro_evento"])
    ingresso = db.get(Ticket, ticket_id)

    assert ingresso.reservation.event_id != portaria.gate_event_id


def test_ingresso_usado_registra_quando_e_por_quem(db_semeado):
    db, refs = db_semeado
    ingresso = db.get(Ticket, verify_ticket_code(refs["ingresso_usado"]))

    assert ingresso.status is TicketStatus.USED
    assert ingresso.used_at is not None
    assert ingresso.used_by_id is not None


def test_share_tokens_sao_unicos_e_opacos(db_semeado):
    db, _ = db_semeado
    tokens = [t.share_token for t in db.scalars(select(Ticket)).all()]

    assert len(tokens) == len(set(tokens))
    for t in tokens:
        assert len(t) >= 20, "token curto é adivinhável"


def test_todo_ingresso_vem_de_reserva_paga(db_semeado):
    db, _ = db_semeado
    for t in db.scalars(select(Ticket)).all():
        assert t.reservation.status == "PAID", "ingresso sem pagamento aprovado"


# --- Fonte dos filmes ---


def test_sem_chave_usa_as_fixtures(redis_fake, monkeypatch):
    """Quem clona sem chave precisa de vitrine populada.

    Um seed que dependesse da API deixaria a home vazia — e o README promete
    que o fluxo inteiro funciona sem cadastrar chave em serviço nenhum.
    """
    import asyncio

    from app.core import config
    from app.providers import fixtures
    from app.seed import obter_filmes

    monkeypatch.setattr(config.settings, "tmdb_api_key", None)

    filmes, da_api = asyncio.run(obter_filmes(quantos=5))

    assert da_api is False
    assert [f.ref for f in filmes] == [f.ref for f in fixtures.FIXTURES[:5]]


def test_com_chave_busca_no_catalogo(redis_fake, monkeypatch):
    import asyncio

    from app.core import config
    from app.providers.base import CatalogItem, CatalogSource
    from app.seed import obter_filmes

    monkeypatch.setattr(config.settings, "tmdb_api_key", "chave-falsa")

    async def falso(_termo, limit=20):
        return [
            CatalogItem(
                ref=f"tmdb:movie:{n}",
                source=CatalogSource.TMDB,
                title=f"Filme {n}",
                poster_url="https://img/p.jpg",
            )
            for n in range(limit)
        ]

    monkeypatch.setattr("app.seed.catalog.search", falso)

    filmes, da_api = asyncio.run(obter_filmes(quantos=5))

    assert da_api is True
    assert len(filmes) == 5
    assert all(f.title.startswith("Filme") for f in filmes)


def test_api_com_pouco_resultado_completa_com_fixtures(redis_fake, monkeypatch):
    """Rede instável ou quota não deve resultar em vitrine magra."""
    import asyncio

    from app.core import config
    from app.providers.base import CatalogItem, CatalogSource
    from app.seed import obter_filmes

    monkeypatch.setattr(config.settings, "tmdb_api_key", "chave-falsa")

    async def poucos(_termo, limit=20):
        return [
            CatalogItem(
                ref="tmdb:movie:1",
                source=CatalogSource.TMDB,
                title="Único",
                poster_url="https://img/p.jpg",
            )
        ]

    monkeypatch.setattr("app.seed.catalog.search", poucos)

    filmes, _ = asyncio.run(obter_filmes(quantos=6))

    assert len(filmes) == 6, "deveria completar com fixtures"
    assert filmes[0].title == "Único"


def test_provedor_quebrado_nao_impede_o_seed(redis_fake, monkeypatch):
    """Sem isto o seed falharia e o banco ficaria sem evento nenhum."""
    import asyncio

    from app.core import config
    from app.seed import obter_filmes

    monkeypatch.setattr(config.settings, "tmdb_api_key", "chave-falsa")

    async def explode(_termo, limit=20):
        raise RuntimeError("API fora do ar")

    monkeypatch.setattr("app.seed.catalog.search", explode)

    filmes, da_api = asyncio.run(obter_filmes(quantos=4))

    assert da_api is False
    assert len(filmes) == 4


def test_nao_repete_filme_entre_as_sessoes(db_semeado):
    """O mesmo título duas vezes na vitrine parece descuido.

    Num cinema real duas sessões do mesmo filme é o normal, mas na tela de
    demonstração passa por erro — daí os dois filmes reservados.
    """
    from collections import Counter

    from sqlalchemy import select

    db, _ = db_semeado
    titulos = [e.title for e in db.scalars(select(Event)).all()]

    repetidos = {t: n for t, n in Counter(titulos).items() if n > 1}
    assert not repetidos, f"títulos repetidos: {repetidos}"
