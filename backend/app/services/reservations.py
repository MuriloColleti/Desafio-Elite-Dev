"""Reserva de lugar — onde a corrida pelo assento é decidida.

A regra central do sistema mora aqui. Duas pessoas clicando no mesmo assento no
mesmo instante é o caso normal, não a exceção, e a resolução **não** é feita em
Python: é o índice único parcial `uq_seat_active` que serializa. Este módulo só
traduz a violação de unicidade em `SEAT_TAKEN`.

Para layout GENERAL (pista) não há assento a disputar, e aí a contagem precisa
de outra proteção — ver `_conferir_disponibilidade_pista`.
"""

import re
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import (
    NotFound,
    ReservationExpired,
    SeatTaken,
    SoldOut,
    ValidationFailed,
)
from app.models.entities import Event, Reservation
from app.models.enums import EventLayout, EventStatus, ReservationStatus


# Rótulo de assento: uma letra de fileira seguida do número. Uma letra só
# porque 26 fileiras cobre qualquer sala real deste escopo.
_PADRAO_ASSENTO = re.compile(r"([A-Z])(\d{1,2})")


def _agora() -> datetime:
    return datetime.now(UTC)


def _ocupantes(event_id: str):
    """Filtro das reservas que ocupam lugar neste instante.

    A expiração é avaliada na leitura: um hold vencido conta como livre sem que
    nenhum job precise ter rodado. É por isso que não existe rotina de limpeza
    para o estoque ficar correto.
    """
    return (
        Reservation.event_id == event_id,
        Reservation.status.in_(ReservationStatus.occupying()),
        (Reservation.expires_at.is_(None)) | (Reservation.expires_at > _agora()),
    )


def assentos_ocupados(db: Session, event_id: str) -> set[str]:
    """Rótulos indisponíveis, para o mapa de assentos do front."""
    linhas = db.scalars(
        select(Reservation.seat_label).where(
            *_ocupantes(event_id), Reservation.seat_label.is_not(None)
        )
    ).all()
    return {label for label in linhas if label}


def lugares_vendidos(db: Session, event_id: str) -> int:
    """Total de lugares tomados, somando quantidade (pista) e assentos."""
    return db.scalar(
        select(func.coalesce(func.sum(Reservation.quantity), 0)).where(
            *_ocupantes(event_id)
        )
    )


def disponiveis(db: Session, evento: Event) -> int:
    return max(0, evento.capacity - lugares_vendidos(db, evento.id))


def rotulo_assento(fileira: int, numero: int) -> str:
    """(0, 0) -> "A1". Fonte única do formato, usada pelo mapa e pela validação."""
    return f"{chr(ord('A') + fileira)}{numero + 1}"


def _validar_rotulo(evento: Event, seat_label: str) -> None:
    """Rejeita assento fora do mapa.

    Sem isto, um cliente poderia reservar "Z99" num mapa 8x12: a constraint
    aceitaria (o rótulo é único), mas o assento não existe na sala.
    """
    if not evento.seat_rows or not evento.seats_per_row:
        raise ValidationFailed("Evento com assento marcado sem mapa configurado.")

    match = _PADRAO_ASSENTO.fullmatch(seat_label.strip().upper())
    if match is None:
        raise ValidationFailed(f"Assento inválido: {seat_label}.")

    fileira, numero = match.group(1), int(match.group(2))

    if not (0 <= ord(fileira) - ord("A") < evento.seat_rows):
        raise ValidationFailed(f"Fileira inexistente: {fileira}.")

    if not (1 <= numero <= evento.seats_per_row):
        raise ValidationFailed(f"Número de assento inexistente: {numero}.")


def _evento_reservavel(db: Session, event_id: str) -> Event:
    evento = db.get(Event, event_id)
    if evento is None:
        raise NotFound("Evento não encontrado.")

    if evento.status is not EventStatus.PUBLISHED:
        # Rascunho e cancelado não vendem. Rascunho não está na vitrine, mas o
        # id pode ter sido descoberto.
        raise ValidationFailed("Este evento não está aberto para reservas.")

    if evento.starts_at <= _agora():
        raise ValidationFailed("Este evento já começou.")

    return evento


def criar(
    db: Session,
    *,
    event_id: str,
    customer_id: str,
    seat_label: str | None = None,
    quantity: int = 1,
) -> Reservation:
    """Cria o hold. Levanta SEAT_TAKEN se perdeu a corrida pelo assento.

    O hold existe para a disputa ser resolvida no clique, e não no pagamento:
    sem ele, duas pessoas chegam ao checkout com o mesmo lugar e uma descobre no
    fim do processo que perdeu.
    """
    evento = _evento_reservavel(db, event_id)

    if evento.layout is EventLayout.SEATED:
        if not seat_label:
            raise ValidationFailed("Escolha um assento para este evento.")
        if quantity != 1:
            raise ValidationFailed("Cada assento é um ingresso.")
        _validar_rotulo(evento, seat_label)
    else:
        if seat_label:
            raise ValidationFailed("Este evento é por quantidade, não por assento.")
        if quantity < 1:
            raise ValidationFailed("Quantidade inválida.")
        _conferir_disponibilidade_pista(db, evento, quantity)

    reserva = Reservation(
        event_id=evento.id,
        customer_id=customer_id,
        seat_label=seat_label,
        quantity=quantity,
        status=ReservationStatus.PENDING,
        expires_at=_agora() + timedelta(minutes=settings.reservation_ttl_minutes),
    )
    db.add(reserva)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # Única constraint que uma reserva pode violar é a do assento ativo.
        # Chegar aqui significa que outra transação inseriu o mesmo lugar entre
        # a nossa leitura e o nosso commit — exatamente o caso que o índice
        # existe para resolver.
        raise SeatTaken() from exc

    db.refresh(reserva)
    return reserva


def _conferir_disponibilidade_pista(db: Session, evento: Event, quantity: int) -> None:
    """Capacidade da pista.

    Diferente do assento, aqui não há constraint que sirva: a regra é uma soma,
    e o Postgres não expressa "SUM(quantity) <= capacity" como unique index.
    Então esta checagem é sujeita a corrida — duas compras simultâneas podem
    passar juntas e estourar a capacidade em alguns lugares.

    Aceitei o risco em vez de serializar tudo: o efeito é overbooking pequeno em
    pista, que é reconciliável na entrada, e o custo de um lock por evento seria
    pago em toda compra. Assento marcado, onde vender duas vezes é inaceitável,
    tem a garantia forte.
    """
    if disponiveis(db, evento) < quantity:
        raise SoldOut()


def liberar(db: Session, *, reservation_id: str, customer_id: str) -> Reservation:
    """Cancela o hold e devolve o lugar ao estoque.

    Sair do índice de unicidade é o que devolve o assento — não há passo de
    "repor estoque" a executar.
    """
    reserva = db.get(Reservation, reservation_id)
    if reserva is None or reserva.customer_id != customer_id:
        # Mesma resposta para inexistente e de outro cliente: não confirmamos a
        # existência de reservas alheias.
        raise NotFound("Reserva não encontrada.")

    if reserva.status is ReservationStatus.CANCELLED:
        return reserva  # idempotente: cancelar duas vezes não é erro

    if reserva.status is not ReservationStatus.PENDING:
        raise ValidationFailed("Só é possível liberar uma reserva pendente.")

    reserva.status = ReservationStatus.CANCELLED
    reserva.expires_at = None
    db.commit()
    db.refresh(reserva)
    return reserva


def obter_para_pagamento(db: Session, *, reservation_id: str, customer_id: str) -> Reservation:
    """Reserva pronta para cobrança, validando dono e prazo."""
    reserva = db.get(Reservation, reservation_id)
    if reserva is None or reserva.customer_id != customer_id:
        raise NotFound("Reserva não encontrada.")

    if reserva.status is ReservationStatus.PENDING and _expirou(reserva):
        # Marca o vencimento ao encostar nela: o estado no banco passa a
        # refletir o que a leitura já considerava.
        reserva.status = ReservationStatus.EXPIRED
        db.commit()
        raise ReservationExpired()

    if reserva.status is not ReservationStatus.PENDING:
        raise ValidationFailed(
            f"Esta reserva não está aguardando pagamento (status: {reserva.status})."
        )

    return reserva


def _expirou(reserva: Reservation) -> bool:
    return reserva.expires_at is not None and reserva.expires_at <= _agora()
