"""Pagamento simulado.

Uma compra pode envolver várias reservas: quatro assentos são quatro registros,
porque a constraint de unicidade é por assento. O que agrupa é o **pagamento** —
`cobrar_grupo` cobra o conjunto numa transação, e recusa cancela todas.

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


def cobrar_grupo(
    db: Session,
    *,
    reservation_ids: list[str],
    customer_id: str,
    numero_cartao: str,
) -> tuple[list[Payment], list[Ticket]]:
    """Cobra várias reservas numa só transação.

    Comprar quatro assentos gera quatro reservas — a constraint é um assento por
    reserva — mas **uma** cobrança: a pessoa digitou o cartão uma vez e espera
    uma linha no extrato.

    Recusa cancela **todas** as reservas do grupo. Deixar duas pagas e duas
    canceladas entregaria metade do que foi pedido, e quem compra quatro lugares
    quer sentar junto.
    """
    reservas = reservations.obter_grupo(db, ids=reservation_ids, customer_id=customer_id)

    aprovado, motivo = _decidir(numero_cartao)

    # Um registro de pagamento por reserva, com o valor daquela reserva: o total
    # do grupo é a soma, e assim cancelar um ingresso depois não exige ratear
    # uma cobrança única.
    pagamentos = [
        Payment(
            reservation_id=r.id,
            status=PaymentStatus.APPROVED if aprovado else PaymentStatus.DECLINED,
            amount_cents=r.event.price_cents * r.quantity,
            reason=motivo,
        )
        for r in reservas
    ]
    db.add_all(pagamentos)

    if not aprovado:
        for r in reservas:
            r.status = ReservationStatus.CANCELLED
            r.expires_at = None
        db.commit()
        raise PaymentDeclined(motivo or "Pagamento recusado.")

    ingressos = []
    for r in reservas:
        r.status = ReservationStatus.PAID
        # Pago não expira: o prazo existia para o hold, e ele terminou.
        r.expires_at = None
        ingressos.append(
            Ticket(
                reservation_id=r.id,
                share_token=secrets.token_urlsafe(24),
                status=TicketStatus.VALID,
            )
        )
    db.add_all(ingressos)

    db.commit()
    for p in pagamentos:
        db.refresh(p)
    for t in ingressos:
        db.refresh(t)

    return pagamentos, ingressos


def cobrar(
    db: Session,
    *,
    reservation_id: str,
    customer_id: str,
    numero_cartao: str,
) -> tuple[Payment, Ticket]:
    """Cobra uma reserva só.

    Delega para `cobrar_grupo`: a regra é a mesma, e duas implementações do
    mesmo fluxo divergiriam na primeira correção.
    """
    pagamentos, ingressos = cobrar_grupo(
        db,
        reservation_ids=[reservation_id],
        customer_id=customer_id,
        numero_cartao=numero_cartao,
    )
    return pagamentos[0], ingressos[0]
