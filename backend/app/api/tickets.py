"""Rotas de ingresso: meus ingressos, QR, compartilhamento e página pública."""

from datetime import datetime

from fastapi import APIRouter, Response
from pydantic import BaseModel

from app.api.deps import DbSession, RequireCustomer
from app.models.entities import Ticket
from app.models.enums import EventLayout, TicketStatus
from app.services import tickets

router = APIRouter(tags=["tickets"])


class TicketOut(BaseModel):
    id: str
    code: str
    status: TicketStatus
    used_at: datetime | None

    event_id: str
    event_title: str
    event_venue: str
    event_starts_at: datetime
    event_poster_url: str | None
    event_layout: EventLayout

    seat_label: str | None
    quantity: int
    share_url: str

    @classmethod
    def de(cls, t: Ticket) -> "TicketOut":
        evento = t.reservation.event
        return cls(
            id=t.id,
            code=tickets.codigo(t),
            status=t.status,
            used_at=t.used_at,
            event_id=evento.id,
            event_title=evento.title,
            event_venue=evento.venue,
            event_starts_at=evento.starts_at,
            event_poster_url=evento.poster_url,
            event_layout=evento.layout,
            seat_label=t.reservation.seat_label,
            quantity=t.reservation.quantity,
            share_url=tickets.link_compartilhavel(t),
        )


class PublicTicketOut(BaseModel):
    """Versão pública, para o link compartilhado.

    Omite o `code`: quem recebe o link vê o ingresso, mas não recebe o material
    para entrar no evento. É o que separa compartilhar de transferir.
    """

    status: TicketStatus
    event_title: str
    event_venue: str
    event_starts_at: datetime
    event_poster_url: str | None
    seat_label: str | None
    quantity: int
    holder_name: str

    @classmethod
    def de(cls, t: Ticket) -> "PublicTicketOut":
        evento = t.reservation.event
        return cls(
            status=t.status,
            event_title=evento.title,
            event_venue=evento.venue,
            event_starts_at=evento.starts_at,
            event_poster_url=evento.poster_url,
            seat_label=t.reservation.seat_label,
            quantity=t.reservation.quantity,
            holder_name=t.reservation.customer.name,
        )


@router.get("/tickets/me", response_model=list[TicketOut])
def meus_ingressos(session: RequireCustomer, db: DbSession) -> list[TicketOut]:
    return [TicketOut.de(t) for t in tickets.listar_do_cliente(db, session.user_id)]


@router.get("/tickets/{ticket_id}/qr")
def qr(ticket_id: str, session: RequireCustomer, db: DbSession) -> Response:
    """PNG do QR do ingresso."""
    ingresso = tickets.obter_do_cliente(
        db, ticket_id=ticket_id, customer_id=session.user_id
    )
    return Response(
        content=tickets.qr_png(ingresso),
        media_type="image/png",
        # Sem cache: um ingresso usado não deve continuar exibindo um QR que o
        # navegador guardou de antes.
        headers={"Cache-Control": "no-store"},
    )


@router.get("/public/tickets/{share_token}", response_model=PublicTicketOut)
def ingresso_publico(share_token: str, db: DbSession) -> PublicTicketOut:
    """Ingresso pelo link compartilhado. Sem autenticação, somente leitura."""
    return PublicTicketOut.de(tickets.obter_por_share_token(db, share_token))
