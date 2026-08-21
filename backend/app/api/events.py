"""Rotas de evento: vitrine pública e painel do organizador."""

from datetime import datetime

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.api.deps import DbSession, RequireOrganizer
from app.models.entities import Event
from app.models.enums import EventLayout, EventStatus, Genre
from app.services import events, reservations

router = APIRouter(tags=["events"])


# --- Schemas ---


class EventOut(BaseModel):
    id: str
    # Exposto para o front ligar uma sessão ao item do catálogo — é o que
    # permite à seção "em cartaz" saber quais filmes já têm ingresso.
    catalog_ref: str | None
    title: str
    synopsis: str | None
    poster_url: str | None
    venue: str
    city: str | None
    state: str | None
    country: str | None
    starts_at: datetime
    layout: EventLayout
    genre: Genre | None
    price_cents: int
    capacity: int
    status: EventStatus
    available: int

    @classmethod
    def de(cls, e: Event, available: int) -> "EventOut":
        return cls(
            id=e.id,
            catalog_ref=e.catalog_ref,
            title=e.title,
            synopsis=e.synopsis,
            poster_url=e.poster_url,
            venue=e.venue,
            city=e.city,
            state=e.state,
            country=e.country,
            starts_at=e.starts_at,
            layout=e.layout,
            genre=e.genre,
            price_cents=e.price_cents,
            capacity=e.capacity,
            status=e.status,
            available=available,
        )


class LocalizacaoOut(BaseModel):
    """Cidade com evento publicado, e quantos.

    O total permite ao seletor mostrar "São Paulo (18)" — e é o que evita
    oferecer um lugar onde não há nada para comprar.
    """

    city: str
    state: str | None
    country: str | None
    total: int


class PaginaEventos(BaseModel):
    """Resposta paginada da vitrine.

    O `total` é o que permite ao front desenhar a barra de páginas. Sem ele a
    interface só descobriria o fim ao receber uma página vazia — e não teria
    como oferecer "ir para a última".
    """

    items: list[EventOut]
    total: int
    limit: int
    offset: int


class SeatMapOut(BaseModel):
    """Mapa de assentos para o front renderizar.

    Manda as dimensões e a lista de ocupados, não a matriz inteira: o front
    monta a grade, e transmitir 96 objetos para dizer "8 por 12" é desperdício.
    """

    rows: int
    seats_per_row: int
    taken: list[str]


class EventDetailOut(EventOut):
    seat_map: SeatMapOut | None


class EventCreate(BaseModel):
    # Um dos dois: título livre, ou item do catálogo (que também traz sinopse e
    # pôster). Validado no serviço, porque a regra é "pelo menos um".
    title: str | None = Field(None, max_length=255)
    catalog_ref: str | None = Field(None, max_length=120)

    venue: str = Field(min_length=1, max_length=255)
    starts_at: datetime
    layout: EventLayout
    genre: Genre | None = None
    city: str | None = Field(None, max_length=120)
    state: str | None = Field(None, max_length=2)
    price_cents: int = Field(ge=0)

    # SEATED: informa o mapa e a capacidade é derivada.
    seat_rows: int | None = Field(None, ge=1, le=26)
    seats_per_row: int | None = Field(None, ge=1, le=99)
    # GENERAL: informa a capacidade direto.
    capacity: int | None = Field(None, ge=1)

    publish: bool = False


class EventUpdate(BaseModel):
    venue: str | None = Field(None, min_length=1, max_length=255)
    starts_at: datetime | None = None
    price_cents: int | None = Field(None, ge=0)
    capacity: int | None = Field(None, ge=1)
    status: EventStatus | None = None


# --- Vitrine (pública, sem autenticação) ---


@router.get("/events", response_model=PaginaEventos)
def listar(
    db: DbSession,
    q: str | None = Query(None, max_length=120, description="Busca por título ou local"),
    layout: EventLayout | None = Query(None),
    genre: Genre | None = Query(None, description="Filtra por gênero"),
    city: str | None = Query(None, max_length=120, description="Filtra por cidade"),
    state: str | None = Query(None, max_length=2, description="UF, ex. SP"),
    country: str | None = Query(None, max_length=2, description="País, ex. BR"),
    limit: int = Query(12, ge=1, le=120),
    offset: int = Query(0, ge=0),
) -> PaginaEventos:
    filtros = {
        "busca": q,
        "layout": layout,
        "genero": genre,
        "cidade": city,
        "uf": state,
        "pais": country,
    }

    achados = events.listar_vitrine(db, **filtros, limit=limit, offset=offset)
    total = events.contar_vitrine(db, **filtros)

    return PaginaEventos(
        items=[EventOut.de(e, reservations.disponiveis(db, e)) for e in achados],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/locations", response_model=list[LocalizacaoOut])
def listar_localizacoes(db: DbSession) -> list[LocalizacaoOut]:
    """Cidades onde há evento publicado, para o seletor de localização."""
    return [LocalizacaoOut(**loc) for loc in events.localizacoes(db)]


@router.get("/events/{event_id}", response_model=EventDetailOut)
def detalhar(event_id: str, db: DbSession) -> EventDetailOut:
    evento = events.obter_publicado(db, event_id)

    mapa = None
    if evento.layout is EventLayout.SEATED and evento.seat_rows and evento.seats_per_row:
        mapa = SeatMapOut(
            rows=evento.seat_rows,
            seats_per_row=evento.seats_per_row,
            taken=sorted(reservations.assentos_ocupados(db, evento.id)),
        )

    base = EventOut.de(evento, reservations.disponiveis(db, evento))
    return EventDetailOut(**base.model_dump(), seat_map=mapa)


# --- Painel do organizador ---


@router.get("/organizer/events", response_model=list[EventOut])
def meus_eventos(session: RequireOrganizer, db: DbSession) -> list[EventOut]:
    achados = events.listar_do_organizador(db, session.user_id)
    return [EventOut.de(e, reservations.disponiveis(db, e)) for e in achados]


@router.post("/organizer/events", response_model=EventOut, status_code=201)
async def criar(
    payload: EventCreate, session: RequireOrganizer, db: DbSession
) -> EventOut:
    evento = await events.criar(
        db,
        organizer_id=session.user_id,
        titulo=payload.title,
        catalog_ref=payload.catalog_ref,
        venue=payload.venue,
        starts_at=payload.starts_at,
        layout=payload.layout,
        genero=payload.genre,
        cidade=payload.city,
        uf=payload.state,
        price_cents=payload.price_cents,
        capacity=payload.capacity,
        seat_rows=payload.seat_rows,
        seats_per_row=payload.seats_per_row,
        publicar=payload.publish,
    )
    return EventOut.de(evento, reservations.disponiveis(db, evento))


@router.patch("/organizer/events/{event_id}", response_model=EventOut)
def editar(
    event_id: str, payload: EventUpdate, session: RequireOrganizer, db: DbSession
) -> EventOut:
    evento = events.editar(
        db,
        event_id=event_id,
        organizer_id=session.user_id,
        venue=payload.venue,
        starts_at=payload.starts_at,
        price_cents=payload.price_cents,
        capacity=payload.capacity,
        status=payload.status,
    )
    return EventOut.de(evento, reservations.disponiveis(db, evento))


@router.delete("/organizer/events/{event_id}", response_model=EventOut)
def cancelar(event_id: str, session: RequireOrganizer, db: DbSession) -> EventOut:
    evento = events.cancelar(db, event_id=event_id, organizer_id=session.user_id)
    return EventOut.de(evento, reservations.disponiveis(db, evento))
