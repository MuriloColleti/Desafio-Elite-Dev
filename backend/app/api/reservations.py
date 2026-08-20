"""Rotas de reserva — o hold antes do pagamento."""

from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel, Field, model_validator

from app.api.deps import DbSession, RequireCustomer
from app.models.entities import Reservation
from app.models.enums import ReservationStatus
from app.services import reservations

router = APIRouter(prefix="/reservations", tags=["reservations"])


class ReservationCreate(BaseModel):
    event_id: str
    # SEATED usa seat_label; GENERAL usa quantity. O serviço rejeita a
    # combinação errada para o layout do evento — aqui só barramos o pedido que
    # não faz sentido em nenhum caso.
    seat_label: str | None = Field(None, max_length=16)
    quantity: int = Field(1, ge=1, le=10)

    @model_validator(mode="after")
    def _coerente(self) -> "ReservationCreate":
        if self.seat_label and self.quantity != 1:
            raise ValueError("Um assento marcado corresponde a um ingresso.")
        return self


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


@router.post("", response_model=ReservationOut, status_code=201)
def criar(
    payload: ReservationCreate, session: RequireCustomer, db: DbSession
) -> ReservationOut:
    """Reserva o lugar. Responde 409 SEAT_TAKEN se outra pessoa chegou antes."""
    reserva = reservations.criar(
        db,
        event_id=payload.event_id,
        customer_id=session.user_id,
        seat_label=payload.seat_label,
        quantity=payload.quantity,
    )
    return ReservationOut.de(reserva)


@router.delete("/{reservation_id}", response_model=ReservationOut)
def liberar(
    reservation_id: str, session: RequireCustomer, db: DbSession
) -> ReservationOut:
    """Desiste da reserva e devolve o lugar ao estoque."""
    reserva = reservations.liberar(
        db, reservation_id=reservation_id, customer_id=session.user_id
    )
    return ReservationOut.de(reserva)
