"""Eventos: vitrine pública e gestão pelo organizador."""

from datetime import UTC, datetime

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import Forbidden, NotFound, ValidationFailed
from app.models.entities import Event
from app.models.enums import EventLayout, EventStatus, Genre
from app.services import catalog, reservations


def _agora() -> datetime:
    return datetime.now(UTC)


# --- Vitrine (pública) ---


def _base_vitrine() -> Select:
    """Só publicados e que ainda não começaram.

    Evento passado sai da vitrine sozinho: filtrar por data evita ter de mudar
    status por rotina agendada.
    """
    return select(Event).where(
        Event.status == EventStatus.PUBLISHED, Event.starts_at > _agora()
    )


def _aplicar_filtros(
    stmt: Select,
    *,
    busca: str | None,
    layout: EventLayout | None,
    genero: Genre | None,
) -> Select:
    """Os filtros da vitrine, num lugar só.

    Extraído porque a contagem e a página precisam dos **mesmos** filtros: se
    divergirem, o total não corresponde ao que a lista devolve e a paginação
    aponta para páginas vazias.
    """
    if busca:
        termo = f"%{busca.strip()}%"
        # ilike: busca sem diferenciar maiúsculas. Título e local porque é como
        # as pessoas procuram — pelo nome do filme ou pela casa de show.
        stmt = stmt.where(or_(Event.title.ilike(termo), Event.venue.ilike(termo)))

    if layout is not None:
        stmt = stmt.where(Event.layout == layout)

    if genero is not None:
        stmt = stmt.where(Event.genre == genero)

    return stmt


def contar_vitrine(
    db: Session,
    *,
    busca: str | None = None,
    layout: EventLayout | None = None,
    genero: Genre | None = None,
) -> int:
    """Total que atende aos filtros, ignorando a página.

    É o que permite ao front saber quantas páginas existem. Sem isso ele só
    descobriria o fim ao receber uma página vazia.
    """
    stmt = _aplicar_filtros(
        select(func.count()).select_from(Event).where(
            Event.status == EventStatus.PUBLISHED, Event.starts_at > _agora()
        ),
        busca=busca,
        layout=layout,
        genero=genero,
    )
    return db.scalar(stmt) or 0


def listar_vitrine(
    db: Session,
    *,
    busca: str | None = None,
    layout: EventLayout | None = None,
    genero: Genre | None = None,
    limit: int = 24,
    offset: int = 0,
) -> list[Event]:
    stmt = _aplicar_filtros(
        _base_vitrine(), busca=busca, layout=layout, genero=genero
    )

    # Mais próximos primeiro: quem abre a vitrine quer o que dá para assistir já.
    # `id` como segundo critério porque duas sessões podem começar no mesmo
    # instante — sem ele a ordem entre elas é indefinida e um evento poderia
    # aparecer em duas páginas, ou em nenhuma.
    stmt = stmt.order_by(Event.starts_at.asc(), Event.id.asc()).limit(limit).offset(offset)

    return list(db.scalars(stmt).all())


def obter_publicado(db: Session, event_id: str) -> Event:
    evento = db.get(Event, event_id)
    if evento is None or evento.status is not EventStatus.PUBLISHED:
        # Rascunho responde 404, não 403: a existência de um evento não
        # publicado não é informação pública.
        raise NotFound("Evento não encontrado.")
    return evento


# --- Gestão (organizador) ---


def listar_do_organizador(db: Session, organizer_id: str) -> list[Event]:
    """Todos os estados, inclusive rascunho e cancelado.

    Ao contrário da vitrine, inclui eventos passados: o organizador precisa ver
    o histórico do que realizou.
    """
    return list(
        db.scalars(
            select(Event)
            .where(Event.organizer_id == organizer_id)
            .order_by(Event.starts_at.desc())
        ).all()
    )


def _do_organizador(db: Session, event_id: str, organizer_id: str) -> Event:
    evento = db.get(Event, event_id)
    if evento is None:
        raise NotFound("Evento não encontrado.")
    if evento.organizer_id != organizer_id:
        raise Forbidden("Este evento é de outro organizador.")
    return evento


async def criar(
    db: Session,
    *,
    organizer_id: str,
    titulo: str | None,
    catalog_ref: str | None,
    venue: str,
    starts_at: datetime,
    layout: EventLayout,
    price_cents: int,
    genero: Genre | None = None,
    capacity: int | None = None,
    seat_rows: int | None = None,
    seats_per_row: int | None = None,
    publicar: bool = False,
) -> Event:
    """Cria o evento, opcionalmente a partir de um item do catálogo.

    O snapshot de título/pôster/sinopse é copiado agora e não volta a ser lido
    do provedor: a vitrine não pode depender de a API externa estar de pé, e um
    evento publicado não deve mudar de cara se o TMDb editar o registro depois.
    """
    if starts_at <= _agora():
        raise ValidationFailed("A data do evento precisa estar no futuro.")
    if price_cents < 0:
        raise ValidationFailed("Preço não pode ser negativo.")

    snapshot_titulo = titulo
    sinopse = None
    poster = None
    genero_final = genero

    if catalog_ref:
        item = await catalog.get(catalog_ref)
        if item is None:
            raise ValidationFailed(f"Item de catálogo não encontrado: {catalog_ref}.")
        snapshot_titulo = titulo or item.title
        sinopse = item.synopsis
        poster = item.poster_url
        # O gênero informado ganha do sugerido: o organizador pode discordar da
        # classificação do catálogo.
        genero_final = genero or item.suggested_genre

    if not snapshot_titulo:
        raise ValidationFailed("Informe um título ou um item do catálogo.")

    if layout is EventLayout.SEATED:
        if not seat_rows or not seats_per_row:
            raise ValidationFailed(
                "Evento com assento marcado precisa de fileiras e assentos por fileira."
            )
        if seat_rows > 26:
            # O rótulo usa uma letra por fileira.
            raise ValidationFailed("Máximo de 26 fileiras.")
        # Capacidade é derivada, não informada: se fossem dois campos livres,
        # divergiriam e o mapa não fecharia com o total de ingressos.
        capacidade_final = seat_rows * seats_per_row
    else:
        if seat_rows or seats_per_row:
            raise ValidationFailed("Evento de pista não tem mapa de assentos.")
        if not capacity or capacity < 1:
            raise ValidationFailed("Informe a capacidade da pista.")
        capacidade_final = capacity

    evento = Event(
        organizer_id=organizer_id,
        catalog_ref=catalog_ref,
        title=snapshot_titulo,
        synopsis=sinopse,
        poster_url=poster,
        venue=venue,
        starts_at=starts_at,
        layout=layout,
        genre=genero_final,
        capacity=capacidade_final,
        price_cents=price_cents,
        seat_rows=seat_rows,
        seats_per_row=seats_per_row,
        status=EventStatus.PUBLISHED if publicar else EventStatus.DRAFT,
    )
    db.add(evento)
    db.commit()
    db.refresh(evento)
    return evento


def editar(
    db: Session,
    *,
    event_id: str,
    organizer_id: str,
    venue: str | None = None,
    starts_at: datetime | None = None,
    price_cents: int | None = None,
    capacity: int | None = None,
    status: EventStatus | None = None,
) -> Event:
    """Edita o evento. O que já foi vendido limita o que pode mudar."""
    evento = _do_organizador(db, event_id, organizer_id)

    if evento.status is EventStatus.CANCELLED:
        raise ValidationFailed("Evento cancelado não pode ser editado.")

    vendidos = reservations.lugares_vendidos(db, evento.id)

    if starts_at is not None:
        if starts_at <= _agora():
            raise ValidationFailed("A data do evento precisa estar no futuro.")
        evento.starts_at = starts_at

    if venue is not None:
        evento.venue = venue

    if price_cents is not None:
        if price_cents < 0:
            raise ValidationFailed("Preço não pode ser negativo.")
        if vendidos and price_cents != evento.price_cents:
            # Quem já pagou pagou outro valor. Mudar o preço criaria duas
            # verdades para o mesmo evento.
            raise ValidationFailed(
                "Não é possível alterar o preço com ingressos já vendidos."
            )
        evento.price_cents = price_cents

    if capacity is not None:
        if evento.layout is EventLayout.SEATED:
            raise ValidationFailed(
                "A capacidade de evento com assentos vem do mapa; edite o mapa."
            )
        if capacity < vendidos:
            raise ValidationFailed(
                f"Já há {vendidos} lugares vendidos; a capacidade não pode ser menor."
            )
        evento.capacity = capacity

    if status is not None:
        _mudar_status(evento, status)

    db.commit()
    db.refresh(evento)
    return evento


def _mudar_status(evento: Event, novo: EventStatus) -> None:
    if novo is EventStatus.CANCELLED:
        raise ValidationFailed("Use o cancelamento para encerrar o evento.")

    if novo is EventStatus.DRAFT and evento.status is EventStatus.PUBLISHED:
        raise ValidationFailed(
            "Evento publicado não volta a rascunho; cancele-o em vez disso."
        )

    if novo is EventStatus.PUBLISHED and evento.starts_at <= _agora():
        raise ValidationFailed("Não é possível publicar um evento que já começou.")

    evento.status = novo


def cancelar(db: Session, *, event_id: str, organizer_id: str) -> Event:
    """Cancela o evento.

    As reservas seguem no banco com o status que tinham: o histórico de quem
    comprou não é apagado por cancelamento, e o evento cancelado sai da vitrine
    por filtro de status.
    """
    evento = _do_organizador(db, event_id, organizer_id)

    if evento.status is EventStatus.CANCELLED:
        return evento  # idempotente

    evento.status = EventStatus.CANCELLED
    db.commit()
    db.refresh(evento)
    return evento
