"""Ingresso: emissão, QR, compartilhamento e validação na portaria."""

import io
from datetime import UTC, datetime

import qrcode
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.errors import NotFound
from app.core.security import sign_ticket_code, verify_ticket_code
from app.models.entities import Event, Reservation, Ticket
from app.models.enums import GateResult, TicketStatus


def _com_relacoes():
    """Carrega reserva e evento junto: toda leitura de ingresso precisa dos dois."""
    return joinedload(Ticket.reservation).joinedload(Reservation.event)


def listar_do_cliente(db: Session, customer_id: str) -> list[Ticket]:
    """Meus ingressos, do evento mais próximo para o mais distante."""
    return list(
        db.scalars(
            select(Ticket)
            .join(Reservation)
            .join(Event)
            .where(Reservation.customer_id == customer_id)
            .options(_com_relacoes())
            .order_by(Event.starts_at.asc())
        ).unique()
    )


def obter_do_cliente(db: Session, *, ticket_id: str, customer_id: str) -> Ticket:
    ingresso = db.get(Ticket, ticket_id, options=[_com_relacoes()])
    if ingresso is None or ingresso.reservation.customer_id != customer_id:
        # Mesma resposta para inexistente e de outra pessoa: o id de um ingresso
        # alheio não deve ser confirmável por tentativa.
        raise NotFound("Ingresso não encontrado.")
    return ingresso


def codigo(ingresso: Ticket) -> str:
    """O conteúdo do QR: `<id>.<hmac>`."""
    return sign_ticket_code(ingresso.id)


def qr_png(ingresso: Ticket) -> bytes:
    """PNG do QR.

    `box_size` generoso e correção de erro baixa: o código é curto, então cabe
    numa versão baixa de QR com módulos grandes — o que é o que permite ler com
    câmera de celular em porta de cinema, muitas vezes com pouca luz.
    """
    qr = qrcode.QRCode(
        version=None,  # deixa a biblioteca escolher a menor que couber
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=2,
    )
    qr.add_data(codigo(ingresso))
    qr.make(fit=True)

    buffer = io.BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(buffer, format="PNG")
    return buffer.getvalue()


def link_compartilhavel(ingresso: Ticket) -> str:
    """URL pública do ingresso.

    Token separado do código de validação de propósito: quem recebe o link vê o
    ingresso, mas não ganha o direito de entrar. E revogar o link (trocando o
    token) não invalida o ingresso.
    """
    return f"{settings.public_base_url.rstrip('/')}/i/{ingresso.share_token}"


def obter_por_share_token(db: Session, token: str) -> Ticket:
    """Ingresso pelo token público. Sem autenticação — é o ponto do link."""
    ingresso = db.scalar(
        select(Ticket).where(Ticket.share_token == token).options(_com_relacoes())
    )
    if ingresso is None:
        raise NotFound("Ingresso não encontrado.")
    return ingresso


# --- Portaria ---


def validar(
    db: Session, *, codigo_lido: str, gate_user_id: str, gate_event_id: str | None
) -> tuple[GateResult, Ticket | None]:
    """Valida o ingresso na entrada.

    Devolve um dos quatro resultados que o enunciado exige. Os três casos de
    recusa **não** são erro de requisição: a portaria precisa exibir o motivo na
    tela, então voltam com 200 e um resultado de negócio.

    A ordem das checagens importa: autenticidade primeiro (HMAC), depois
    existência, depois evento, e só então o estado. Checar o estado antes do
    evento faria um ingresso de outro evento já usado responder "já utilizado",
    escondendo o problema real de quem está na porta errada.
    """
    ticket_id = verify_ticket_code(codigo_lido.strip())
    if ticket_id is None:
        # HMAC não confere: código forjado ou digitação errada.
        return GateResult.INVALID, None

    ingresso = db.get(Ticket, ticket_id, options=[_com_relacoes()])
    if ingresso is None:
        # Assinatura válida para um id que não existe. Só acontece se o
        # ingresso foi removido do banco depois de emitido.
        return GateResult.INVALID, None

    if gate_event_id and ingresso.reservation.event_id != gate_event_id:
        return GateResult.WRONG_EVENT, ingresso

    if ingresso.status is TicketStatus.USED:
        return GateResult.ALREADY_USED, ingresso

    if ingresso.status is TicketStatus.CANCELLED:
        return GateResult.INVALID, ingresso

    # UPDATE condicional: dois scanners lendo o mesmo QR no mesmo instante, e
    # só um vê "válido". Fazer `ingresso.status = USED` e commitar deixaria os
    # dois passarem, porque ambos leram VALID antes de escrever.
    afetadas = db.execute(
        Ticket.__table__.update()
        .where(Ticket.id == ingresso.id, Ticket.status == TicketStatus.VALID)
        .values(
            status=TicketStatus.USED,
            used_at=datetime.now(UTC),
            used_by_id=gate_user_id,
        )
    ).rowcount
    db.commit()

    if afetadas == 0:
        # Perdemos a corrida: outro scanner marcou entre a nossa leitura e o
        # nosso update.
        db.refresh(ingresso)
        return GateResult.ALREADY_USED, ingresso

    db.refresh(ingresso)
    return GateResult.VALID, ingresso
