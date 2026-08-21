"""Rotas de reserva — o hold antes do pagamento."""

from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel, Field, model_validator

from app.api.deps import DbSession, RequireCustomer
from app.models.entities import Reservation
from app.models.enums import ReservationStatus
from app.services import reservations
from app.services.reservations import MAX_ASSENTOS

router = APIRouter(prefix="/reservations", tags=["reservations"])


class ReservationCreate(BaseModel):
    event_id: str
    # SEATED usa `seat_labels`; GENERAL usa `quantity`. O serviço rejeita a
    # combinação errada para o layout do evento — aqui só barramos o pedido que
    # não faz sentido em nenhum caso.
    #
    # `seat_labels` é lista porque comprar quatro assentos gera quatro reservas:
    # a constraint de unicidade é `(event_id, seat_label)`, então um registro não
    # pode representar dois lugares.
    seat_labels: list[str] = Field(default_factory=list, max_length=MAX_ASSENTOS)
    quantity: int = Field(1, ge=1, le=10)

    @model_validator(mode="after")
    def _coerente(self) -> "ReservationCreate":
        if self.seat_labels and self.quantity != 1:
            raise ValueError("Assento marcado não usa quantidade.")
        return self


class GrupoReservas(BaseModel):
    """Resposta da criação.

    Sempre lista, mesmo para um assento: o checkout trata os dois casos do mesmo
    jeito, e uma resposta que muda de forma conforme a quantidade obrigaria o
    front a ramificar sem motivo.
    """

    reservations: list["ReservationOut"]
    total_cents: int
    expires_at: datetime | None


class ReservationOut(BaseModel):
    id: str
    event_id: str
    seat_label: str | None
    quantity: int
    status: ReservationStatus
    expires_at: datetime | None
    total_cents: int

    @classmethod
    def de(cls, r: Reservation) -> "ReservationOut":
        return cls(
            id=r.id,
            event_id=r.event_id,
            seat_label=r.seat_label,
            quantity=r.quantity,
            status=r.status,
            expires_at=r.expires_at,
            total_cents=r.event.price_cents * r.quantity,
        )


@router.post("", response_model=GrupoReservas, status_code=201)
def criar(
    payload: ReservationCreate, session: RequireCustomer, db: DbSession
) -> GrupoReservas:
    """Reserva os lugares. Responde 409 SEAT_TAKEN se alguém chegou antes.

    Para assento marcado é **tudo ou nada**: se um dos assentos do grupo se
    perder, nenhum fica reservado — quem pediu quatro lugares quer os quatro.
    """
    if payload.seat_labels:
        reservas = reservations.criar_varias(
            db,
            event_id=payload.event_id,
            customer_id=session.user_id,
            seat_labels=payload.seat_labels,
        )
    else:
        reservas = [
            reservations.criar(
                db,
                event_id=payload.event_id,
                customer_id=session.user_id,
                seat_label=None,
                quantity=payload.quantity,
            )
        ]

    saida = [ReservationOut.de(r) for r in reservas]
    return GrupoReservas(
        reservations=saida,
        total_cents=sum(r.total_cents for r in saida),
        expires_at=reservas[0].expires_at,
    )


@router.delete("/{reservation_id}", response_model=ReservationOut)
def liberar(
    reservation_id: str, session: RequireCustomer, db: DbSession
) -> ReservationOut:
    """Desiste da reserva e devolve o lugar ao estoque."""
    reserva = reservations.liberar(
        db, reservation_id=reservation_id, customer_id=session.user_id
    )
    return ReservationOut.de(reserva)
