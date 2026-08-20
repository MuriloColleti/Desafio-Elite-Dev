"""Rota de pagamento simulado."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.deps import DbSession, RequireCustomer
from app.models.enums import PaymentStatus
from app.services import payments, tickets

router = APIRouter(prefix="/payments", tags=["payments"])


class PaymentRequest(BaseModel):
    reservation_id: str
    # Só o número, e nunca persistido: a cobrança é simulada e guardar dado de
    # cartão — ainda que falso — criaria o hábito errado.
    card_number: str = Field(min_length=12, max_length=25)
    card_holder: str = Field(min_length=1, max_length=120)


class PaymentResponse(BaseModel):
    payment_id: str
    status: PaymentStatus
    amount_cents: int
    ticket_id: str
    ticket_code: str


@router.post("", response_model=PaymentResponse, status_code=201)
def cobrar(
    payload: PaymentRequest, session: RequireCustomer, db: DbSession
) -> PaymentResponse:
    """Cobra a reserva e emite o ingresso.

    Recusa responde **402 PAYMENT_DECLINED** com o motivo, e a reserva é
    cancelada — o assento volta ao estoque em vez de ficar preso a um pagamento
    que falhou.
    """
    pagamento, ingresso = payments.cobrar(
        db,
        reservation_id=payload.reservation_id,
        customer_id=session.user_id,
        numero_cartao=payload.card_number,
    )

    return PaymentResponse(
        payment_id=pagamento.id,
        status=pagamento.status,
        amount_cents=pagamento.amount_cents,
        ticket_id=ingresso.id,
        ticket_code=tickets.codigo(ingresso),
    )
