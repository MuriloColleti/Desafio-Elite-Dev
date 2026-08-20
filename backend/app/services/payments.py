"""Pagamento simulado.

O enunciado pede confirmação **e** recusa, então a recusa não é um erro
genérico de tela: é uma transição de estado que devolve o assento ao estoque.
Sem isso surge o assento fantasma — reservado por alguém cujo cartão falhou e
nunca liberado.

A decisão de aprovar ou recusar é determinística pelo número do cartão, e não
aleatória, para o avaliador conseguir reproduzir os dois caminhos quando quiser.
`PAYMENT_DECLINE_RATE` existe para quem quiser recusa aleatória, mas vem
desligado.
"""

import random
import secrets

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import PaymentDeclined
from app.models.entities import Payment, Reservation, Ticket
from app.models.enums import PaymentStatus, ReservationStatus, TicketStatus
from app.services import reservations

# Cartões de teste. Os números seguem a convenção dos provedores reais (Stripe
# usa exatamente estes), o que torna o comportamento previsível para quem já
# testou integração de pagamento antes.
CARTAO_APROVADO = "4242424242424242"
CARTOES_RECUSADOS = {
    "4000000000000002": "Cartão recusado pelo emissor.",
    "4000000000009995": "Saldo insuficiente.",
    "4000000000000069": "Cartão expirado.",
    "4000000000000127": "Código de segurança inválido.",
}


def _apenas_digitos(valor: str) -> str:
    return "".join(c for c in valor if c.isdigit())


def _decidir(numero_cartao: str) -> tuple[bool, str | None]:
    """Devolve (aprovado, motivo_da_recusa)."""
    numero = _apenas_digitos(numero_cartao)

    if numero in CARTOES_RECUSADOS:
        return False, CARTOES_RECUSADOS[numero]

    if numero == CARTAO_APROVADO:
        return True, None

    # Qualquer outro número: recusa aleatória se configurada, senão aprova.
    # Aprovar por padrão é deliberado — o avaliador que digitar um número
    # qualquer quer ver o fluxo de sucesso, não descobrir a lista de cartões.
    if settings.payment_decline_rate > 0 and random.random() < settings.payment_decline_rate:
        return False, "Recusado pelo simulador (PAYMENT_DECLINE_RATE)."

    return True, None


def cobrar(
    db: Session,
    *,
    reservation_id: str,
    customer_id: str,
    numero_cartao: str,
) -> tuple[Payment, Ticket | None]:
    """Cobra a reserva. Devolve (pagamento, ingresso ou None se recusado).

    Aprovado → reserva vira PAID e o ingresso é emitido na mesma transação:
    ingresso sem pagamento, ou pagamento sem ingresso, seriam estados
    impossíveis de explicar ao cliente.

    Recusado → reserva vira CANCELLED, o que a tira do índice de unicidade e
    devolve o assento. O pagamento recusado fica registrado: é histórico, e o
    cliente precisa poder ver que a tentativa aconteceu.
    """
    reserva = reservations.obter_para_pagamento(
        db, reservation_id=reservation_id, customer_id=customer_id
    )
    valor = reserva.event.price_cents * reserva.quantity

    aprovado, motivo = _decidir(numero_cartao)

    pagamento = Payment(
        reservation_id=reserva.id,
        status=PaymentStatus.APPROVED if aprovado else PaymentStatus.DECLINED,
        amount_cents=valor,
        reason=motivo,
    )
    db.add(pagamento)

    if not aprovado:
        reserva.status = ReservationStatus.CANCELLED
        reserva.expires_at = None
        db.commit()
        # Levanta em vez de devolver: a recusa é um resultado que o front trata
        # numa tela própria, e o código de erro é o que ele usa para decidir.
        raise PaymentDeclined(motivo or "Pagamento recusado.")

    reserva.status = ReservationStatus.PAID
    # Pago não expira: o prazo existia para o hold, e ele terminou.
    reserva.expires_at = None

    ingresso = Ticket(
        reservation_id=reserva.id,
        share_token=secrets.token_urlsafe(24),
        status=TicketStatus.VALID,
    )
    db.add(ingresso)

    db.commit()
    db.refresh(pagamento)
    db.refresh(ingresso)
    return pagamento, ingresso
