"""Entidades do domínio.

A regra central do sistema vive aqui, não no código de serviço: o índice
`uq_seat_active` em `Reservation` é o que garante que um lugar não seja vendido
duas vezes. Ver o comentário nele.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.enums import (
    EventLayout,
    EventStatus,
    Genre,
    PaymentStatus,
    ReservationStatus,
    Role,
    TicketStatus,
)


def _uuid() -> str:
    return str(uuid.uuid4())


def _enum(enum_cls: type) -> Enum:
    """Enum como VARCHAR + CHECK, não como tipo nativo do Postgres."""
    return Enum(enum_cls, native_enum=False, length=32, validate_strings=True)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(_enum(Role), nullable=False)

    # Portaria é vinculada a um evento: é isso que permite responder
    # "evento errado" em vez de aceitar qualquer ingresso legítimo.
    #
    # users → events e events → users formam um ciclo de foreign keys, então
    # nenhuma das duas tabelas pode ser criada primeiro com a FK embutida.
    # use_alter=True faz esta ser emitida como ALTER TABLE depois que as duas
    # existem, quebrando o ciclo na criação do schema.
    gate_event_id: Mapped[str | None] = mapped_column(
        ForeignKey("events.id", ondelete="SET NULL", use_alter=True, name="fk_user_gate_event"),
        nullable=True,
    )

    events: Mapped[list["Event"]] = relationship(
        back_populates="organizer", foreign_keys="Event.organizer_id"
    )


class Event(Base, TimestampMixin):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organizer_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    # Referência ao item do catálogo externo, ex. "tmdb:movie:550".
    # O snapshot abaixo é cópia deliberada: a vitrine não pode depender de a
    # API externa estar de pé, e um evento publicado não deve mudar de cara se
    # o provedor editar o registro depois.
    catalog_ref: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    synopsis: Mapped[str | None] = mapped_column(Text, nullable=True)
    poster_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    venue: Mapped[str] = mapped_column(String(255), nullable=False)
    # Localização em colunas próprias, e não extraída do texto de `venue`:
    # separar "Circo Voador, Rio de Janeiro" por vírgula funciona nos dados
    # que escrevemos e quebra em qualquer venue digitado diferente. Filtro
    # que erra em silêncio é pior que filtro nenhum.
    city: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    state: Mapped[str | None] = mapped_column(String(2), nullable=True, index=True)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True, index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    layout: Mapped[EventLayout] = mapped_column(_enum(EventLayout), nullable=False)
    # Opcional: evento com título livre pode não ter gênero definido, e
    # exigir um obrigaria o organizador a escolher no chute.
    genre: Mapped[Genre | None] = mapped_column(_enum(Genre), nullable=True, index=True)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[EventStatus] = mapped_column(
        _enum(EventStatus), nullable=False, default=EventStatus.DRAFT, index=True
    )

    # Só para layout SEATED. Guardar as dimensões em vez de derivar da tabela
    # de assentos deixa o mapa renderizável com uma consulta só.
    seat_rows: Mapped[int | None] = mapped_column(Integer, nullable=True)
    seats_per_row: Mapped[int | None] = mapped_column(Integer, nullable=True)

    organizer: Mapped["User"] = relationship(
        back_populates="events", foreign_keys=[organizer_id]
    )
    reservations: Mapped[list["Reservation"]] = relationship(back_populates="event")

    __table_args__ = (
        CheckConstraint("capacity > 0", name="ck_event_capacity_positive"),
        CheckConstraint("price_cents >= 0", name="ck_event_price_non_negative"),
    )


class Reservation(Base, TimestampMixin):
    __tablename__ = "reservations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    event_id: Mapped[str] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    customer_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    # SEATED usa seat_label ("F7") e quantity=1; GENERAL usa seat_label=NULL e
    # quantity>=1. Um modelo só para os dois layouts, em vez de duas tabelas.
    seat_label: Mapped[str | None] = mapped_column(String(16), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    status: Mapped[ReservationStatus] = mapped_column(
        _enum(ReservationStatus), nullable=False, default=ReservationStatus.PENDING, index=True
    )
    # Hold: a expiração é avaliada na leitura, então não existe job de
    # background que precise rodar para o estoque ficar correto.
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    event: Mapped["Event"] = relationship(back_populates="reservations")
    customer: Mapped["User"] = relationship(foreign_keys=[customer_id])
    payments: Mapped[list["Payment"]] = relationship(back_populates="reservation")
    ticket: Mapped["Ticket | None"] = relationship(back_populates="reservation", uselist=False)

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_reservation_quantity_positive"),
        # ── A garantia de assento único ──────────────────────────────────────
        # Índice único PARCIAL: vale só para reservas que ocupam lugar. Checar
        # "está livre?" em Python não resolve, porque duas requisições
        # simultâneas passam pelo check as duas. Aqui o Postgres serializa: a
        # segunda inserção viola a unicidade e o serviço traduz em SEAT_TAKEN.
        #
        # Como CANCELLED/EXPIRED ficam fora do índice, cancelar ou expirar
        # devolve o assento ao estoque sem nenhuma rotina de limpeza.
        Index(
            "uq_seat_active",
            "event_id",
            "seat_label",
            unique=True,
            postgresql_where=text(
                "status IN ('PENDING', 'PAID') AND seat_label IS NOT NULL"
            ),
        ),
    )


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    reservation_id: Mapped[str] = mapped_column(
        ForeignKey("reservations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[PaymentStatus] = mapped_column(_enum(PaymentStatus), nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    # Motivo da recusa, para a tela poder dizer o que aconteceu.
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    reservation: Mapped["Reservation"] = relationship(back_populates="payments")


class Ticket(Base, TimestampMixin):
    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    reservation_id: Mapped[str] = mapped_column(
        ForeignKey("reservations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # um ingresso por reserva
        index=True,
    )

    # O QR carrega "<id>.<hmac>"; o HMAC é recalculável a partir do id, então
    # não guardamos o código, só o token de compartilhamento — que é aleatório
    # e precisa ser consultável.
    share_token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)

    status: Mapped[TicketStatus] = mapped_column(
        _enum(TicketStatus), nullable=False, default=TicketStatus.VALID, index=True
    )
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    used_by_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    reservation: Mapped["Reservation"] = relationship(back_populates="ticket")

    __table_args__ = (
        UniqueConstraint("reservation_id", name="uq_ticket_reservation"),
    )
