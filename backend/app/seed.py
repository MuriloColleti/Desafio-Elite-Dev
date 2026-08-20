"""Dados de teste, conforme exigido pelo enunciado.

O PDF pede: um organizador, dois clientes, um usuário de portaria e ao menos um
evento publicado com ingressos disponíveis, para percorrer o fluxo sem montar
tudo do zero.

Vamos além em três pontos, todos para que o avaliador não precise *construir*
uma situação para conseguir vê-la:

- **Assentos já ocupados** no mapa do cinema — mapa vazio não mostra que a
  regra de indisponibilidade funciona.
- **Um ingresso já pago** da Ana, com QR válido: dá para ir direto à portaria.
- **Um ingresso já utilizado**: a resposta "já utilizado" é testável sem ter de
  validar duas vezes na mão.

Uso:
    python -m app.seed              # popula (falha se já houver dados)
    python -m app.seed --reset      # limpa e repopula
"""

import argparse
import secrets
import sys
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.core.security import hash_password, sign_ticket_code
from app.models.entities import Event, Payment, Reservation, Ticket, User
from app.models.enums import (
    EventLayout,
    EventStatus,
    PaymentStatus,
    ReservationStatus,
    Role,
    TicketStatus,
)

SENHA = "senha123"

# Assentos pré-ocupados no evento de cinema. Espalhados em fileiras diferentes
# de propósito: agrupados no meio pareceria bug de renderização do mapa.
ASSENTOS_OCUPADOS = ("C4", "C5", "E7", "E8", "E9", "G2", "H11", "H12")


def _agora() -> datetime:
    return datetime.now(UTC)


def limpar(db: Session) -> None:
    """Apaga na ordem inversa das dependências.

    gate_event_id é zerado antes dos eventos: a FK é SET NULL, mas explicitar
    deixa a intenção clara e não depende do comportamento da constraint.
    """
    db.execute(delete(Ticket))
    db.execute(delete(Payment))
    db.execute(delete(Reservation))
    db.query(User).update({User.gate_event_id: None})
    db.execute(delete(Event))
    db.execute(delete(User))
    db.commit()


def _ja_populado(db: Session) -> bool:
    return db.scalar(select(User).limit(1)) is not None


def povoar(db: Session) -> dict[str, str]:
    senha_hash = hash_password(SENHA)

    # --- Usuários (os quatro papéis que o PDF pede) ---
    organizador = User(
        name="Marina Duarte",
        email="organizador@palco.dev",
        password_hash=senha_hash,
        role=Role.ORGANIZER,
    )
    ana = User(
        name="Ana Ribeiro",
        email="ana@palco.dev",
        password_hash=senha_hash,
        role=Role.CUSTOMER,
    )
    bruno = User(
        name="Bruno Salles",
        email="bruno@palco.dev",
        password_hash=senha_hash,
        role=Role.CUSTOMER,
    )
    portaria = User(
        name="Portaria — Cine Belas Artes",
        email="portaria@palco.dev",
        password_hash=senha_hash,
        role=Role.GATE,
    )
    db.add_all([organizador, ana, bruno, portaria])
    db.flush()

    # --- Eventos ---
    # Datas relativas: o seed não envelhece. Um evento com data fixa vira
    # "evento passado" algumas semanas depois e a vitrine aparece vazia.
    cinema = Event(
        organizer_id=organizador.id,
        catalog_ref="tmdb:movie:496243",
        title="Parasita",
        synopsis=(
            "Toda a família de Ki-taek está desempregada e vivendo num porão sujo e "
            "apertado. Uma obra do destino faz com que o filho comece a dar aulas de "
            "reforço para a filha de uma família rica."
        ),
        poster_url="https://image.tmdb.org/t/p/w500/igw938inb6Fy0YVcwIyxQ7Lu5FO.jpg",
        venue="Cine Belas Artes — Sala 1",
        starts_at=_agora() + timedelta(days=3, hours=4),
        layout=EventLayout.SEATED,
        seat_rows=8,
        seats_per_row=12,
        capacity=96,
        price_cents=3200,
        status=EventStatus.PUBLISHED,
    )
    show = Event(
        organizer_id=organizador.id,
        catalog_ref="ticketmaster:event:demo-baile",
        title="Baile do Terreiro — Edição Verão",
        synopsis="Samba de raiz e partido-alto até o amanhecer, com participações especiais.",
        poster_url=None,
        venue="Circo Voador, Rio de Janeiro",
        starts_at=_agora() + timedelta(days=12),
        layout=EventLayout.GENERAL,
        capacity=500,
        price_cents=9000,
        status=EventStatus.PUBLISHED,
    )
    # Rascunho: o painel do organizador precisa mostrar estado misto, senão não
    # se vê a diferença entre publicar e não publicar.
    rascunho = Event(
        organizer_id=organizador.id,
        catalog_ref="tmdb:movie:1124",
        title="O Grande Truque",
        synopsis=(
            "Dois mágicos rivais no Londres do início do século XX travam uma disputa "
            "obsessiva para criar a ilusão definitiva."
        ),
        poster_url="https://image.tmdb.org/t/p/w500/bdN3gXuIZYaJP7ftKK2sU0nPtEA.jpg",
        venue="Cine Belas Artes — Sala 2",
        starts_at=_agora() + timedelta(days=20, hours=2),
        layout=EventLayout.SEATED,
        seat_rows=6,
        seats_per_row=10,
        capacity=60,
        price_cents=2800,
        status=EventStatus.DRAFT,
    )
    db.add_all([cinema, show, rascunho])
    db.flush()

    # A portaria valida a entrada de um evento específico — é o que permite
    # responder "evento errado" em vez de aceitar qualquer ingresso legítimo.
    portaria.gate_event_id = cinema.id

    # --- Assentos já ocupados (reservas pagas de outros clientes) ---
    for label in ASSENTOS_OCUPADOS:
        r = Reservation(
            event_id=cinema.id,
            customer_id=bruno.id,
            seat_label=label,
            quantity=1,
            status=ReservationStatus.PAID,
        )
        db.add(r)
        db.flush()
        db.add(
            Payment(
                reservation_id=r.id,
                status=PaymentStatus.APPROVED,
                amount_cents=cinema.price_cents,
            )
        )

    # --- Ingresso válido da Ana (pronto para validar na portaria) ---
    reserva_ana = Reservation(
        event_id=cinema.id,
        customer_id=ana.id,
        seat_label="F7",
        quantity=1,
        status=ReservationStatus.PAID,
    )
    db.add(reserva_ana)
    db.flush()
    db.add(
        Payment(
            reservation_id=reserva_ana.id,
            status=PaymentStatus.APPROVED,
            amount_cents=cinema.price_cents,
        )
    )
    ingresso_ana = Ticket(
        reservation_id=reserva_ana.id,
        share_token=secrets.token_urlsafe(24),
        status=TicketStatus.VALID,
    )
    db.add(ingresso_ana)

    # --- Ingresso já utilizado (para ver a resposta "já utilizado") ---
    reserva_usada = Reservation(
        event_id=cinema.id,
        customer_id=ana.id,
        seat_label="F8",
        quantity=1,
        status=ReservationStatus.PAID,
    )
    db.add(reserva_usada)
    db.flush()
    db.add(
        Payment(
            reservation_id=reserva_usada.id,
            status=PaymentStatus.APPROVED,
            amount_cents=cinema.price_cents,
        )
    )
    ingresso_usado = Ticket(
        reservation_id=reserva_usada.id,
        share_token=secrets.token_urlsafe(24),
        status=TicketStatus.USED,
        used_at=_agora() - timedelta(hours=2),
        used_by_id=portaria.id,
    )
    db.add(ingresso_usado)

    # --- Ingresso de OUTRO evento (para ver "evento errado") ---
    reserva_show = Reservation(
        event_id=show.id,
        customer_id=ana.id,
        seat_label=None,
        quantity=2,
        status=ReservationStatus.PAID,
    )
    db.add(reserva_show)
    db.flush()
    db.add(
        Payment(
            reservation_id=reserva_show.id,
            status=PaymentStatus.APPROVED,
            amount_cents=show.price_cents * 2,
        )
    )
    ingresso_show = Ticket(
        reservation_id=reserva_show.id,
        share_token=secrets.token_urlsafe(24),
        status=TicketStatus.VALID,
    )
    db.add(ingresso_show)

    db.commit()

    return {
        "ingresso_valido": sign_ticket_code(ingresso_ana.id),
        "ingresso_usado": sign_ticket_code(ingresso_usado.id),
        "ingresso_outro_evento": sign_ticket_code(ingresso_show.id),
        "share_token_ana": ingresso_ana.share_token,
        "evento_cinema": cinema.id,
        "evento_show": show.id,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Popula o banco com dados de teste.")
    parser.add_argument(
        "--reset", action="store_true", help="apaga os dados existentes antes de popular"
    )
    args = parser.parse_args()

    with SessionLocal() as db:
        if args.reset:
            limpar(db)
        elif _ja_populado(db):
            print(
                "Banco já contém dados. Use --reset para limpar e repopular.",
                file=sys.stderr,
            )
            return 1

        refs = povoar(db)

    print("Seed concluído.\n")
    print(f"  Senha de todos os usuários: {SENHA}\n")
    print("  organizador@palco.dev   ORGANIZER  cria e gerencia eventos")
    print("  ana@palco.dev           CUSTOMER   já tem ingressos (um válido, um usado)")
    print("  bruno@palco.dev         CUSTOMER   sem ingresso, para testar a compra")
    print("  portaria@palco.dev      GATE       valida a entrada do evento de cinema\n")
    print("  Códigos para testar a portaria (colar na digitação manual):\n")
    print(f"    válido .......... {refs['ingresso_valido']}")
    print(f"    já utilizado .... {refs['ingresso_usado']}")
    print(f"    evento errado ... {refs['ingresso_outro_evento']}")
    print("    inválido ........ qualquer texto\n")
    print(f"  Link de compartilhamento da Ana: /i/{refs['share_token_ana']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
