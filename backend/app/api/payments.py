"""Rota de pagamento simulado."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.deps import DbSession, RequireCustomer
from app.models.enums import PaymentStatus
from app.services import payments, tickets
from app.services.reservations import MAX_ASSENTOS

router = APIRouter(prefix="/payments", tags=["payments"])


class PaymentRequest(BaseModel):
    # Lista porque uma compra de quatro assentos são quatro reservas e **uma**
    # cobrança: a pessoa digitou o cartão uma vez.
    reservation_ids: list[str] = Field(min_length=1, max_length=MAX_ASSENTOS)
    # Só o número, e nunca persistido: a cobrança é simulada e guardar dado de
    # cartão — ainda que falso — criaria o hábito errado.
    card_number: str = Field(min_length=12, max_length=25)
    card_holder: str = Field(min_length=1, max_length=120)


class PaymentResponse(BaseModel):
    status: PaymentStatus
    # Total do grupo: é o que a pessoa vê cobrado.
    amount_cents: int
    ticket_ids: list[str]
    ticket_codes: list[str]


@router.post("", response_model=PaymentResponse, status_code=201)
def cobrar(
    payload: PaymentRequest, session: RequireCustomer, db: DbSession
) -> PaymentResponse:
    """Cobra a reserva e emite o ingresso.

    Recusa responde **402 PAYMENT_DECLINED** com o motivo, e a reserva é
    cancelada — o assento volta ao estoque em vez de ficar preso a um pagamento
    que falhou.
    """
    pagamentos, ingressos = payments.cobrar_grupo(
        db,
        reservation_ids=payload.reservation_ids,
        customer_id=session.user_id,
        numero_cartao=payload.card_number,
    )

    return PaymentResponse(
        status=pagamentos[0].status,
        amount_cents=sum(p.amount_cents for p in pagamentos),
        ticket_ids=[i.id for i in ingressos],
        ticket_codes=[tickets.codigo(i) for i in ingressos],
    )
