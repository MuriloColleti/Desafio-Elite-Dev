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
from app.providers import fixtures
from app.providers.base import CatalogSource

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
    # Derivados das fixtures do catálogo: título, sinopse e pôster vêm de lá, e
    # não duplicados aqui. Duas cópias do mesmo pôster divergiriam na primeira
    # correção — já aconteceu neste arquivo.
    #
    # Datas relativas ao momento da execução: com data fixa o seed envelhece e
    # a vitrine aparece vazia semanas depois.
    filmes = [i for i in fixtures.FIXTURES if i.source is CatalogSource.TMDB]
    shows = [i for i in fixtures.FIXTURES if i.source is CatalogSource.TICKETMASTER]

    def evento_de(
        item,
        *,
        venue: str,
        cidade: str,
        uf: str,
        dias: float,
        preco: int,
        layout: EventLayout,
        status: EventStatus = EventStatus.PUBLISHED,
        fileiras: int | None = None,
        por_fileira: int | None = None,
        capacidade: int | None = None,
    ) -> Event:
        return Event(
            organizer_id=organizador.id,
            catalog_ref=item.ref,
            title=item.title,
            synopsis=item.synopsis,
            poster_url=item.poster_url,
            venue=venue,
            city=cidade,
            state=uf,
            country="BR",
            starts_at=_agora() + timedelta(days=dias),
            layout=layout,
            genre=item.suggested_genre,
            seat_rows=fileiras,
            seats_per_row=por_fileira,
            # Assento marcado deriva a capacidade do mapa; pista informa direto.
            capacity=(fileiras * por_fileira) if fileiras and por_fileira else (capacidade or 0),
            price_cents=preco,
            status=status,
        )

    # Programação gerada, e não uma lista fixa: com ~50 eventos escrever cada
    # sala e horário à mão seria repetição sem informação. As variações vêm de
    # ciclos sobre listas curtas, o que mantém a diversidade sem tabela enorme.
    # (sala, cidade, UF) — salas espalhadas por várias capitais, para o filtro
    # de localização ter o que filtrar de verdade.
    SALAS = (
        ("Cine Belas Artes — Sala 1", "São Paulo", "SP"),
        ("Cine Odeon — Sala 1", "Rio de Janeiro", "RJ"),
        ("Espaço Itaú — Sala 3", "São Paulo", "SP"),
        ("Cinemateca — Sala Grande", "Belo Horizonte", "MG"),
        ("Cine Passeio — Sala 2", "Curitiba", "PR"),
        ("Reserva Cultural — Sala 2", "Niterói", "RJ"),
        ("Cine Joia — Sala Panorâmica", "Recife", "PE"),
        ("Petra Belas Artes — Sala 4", "São Paulo", "SP"),
        ("Cinesystem — Sala VIP", "Porto Alegre", "RS"),
        ("Kinoplex — Sala 7", "Salvador", "BA"),
        ("Cine Brasília — Sala 1", "Brasília", "DF"),
        ("UCI Orient — Sala 5", "Fortaleza", "CE"),
    )
    # (fileiras, assentos por fileira) — salas de tamanhos diferentes mostram
    # que o mapa não é fixo.
    MAPAS = ((8, 12), (6, 10), (7, 14), (9, 12), (5, 10), (6, 12), (8, 10), (7, 12))
    PRECOS = (3200, 2800, 3600, 2400, 4200, 3000, 4800, 2600, 5400, 2200)

    eventos_cinema = []
    for n, item in enumerate(filmes):
        fileiras, por_fileira = MAPAS[n % len(MAPAS)]
        sala, cidade, uf = SALAS[n % len(SALAS)]
        eventos_cinema.append(
            evento_de(
                item,
                venue=sala,
                cidade=cidade,
                uf=uf,
                # Espalha as sessões pelas próximas ~7 semanas, em horários de
                # cinema (tarde e noite), sem duas no mesmo minuto.
                dias=2 + n * 0.9 + (n % 3) * 0.25,
                preco=PRECOS[n % len(PRECOS)],
                layout=EventLayout.SEATED,
                fileiras=fileiras,
                por_fileira=por_fileira,
            )
        )

    CAPACIDADES = (500, 800, 350, 250, 1200, 600, 400, 900)
    PRECOS_SHOW = (9000, 12000, 7500, 6000, 15000, 8000, 5500, 11000)

    eventos_show = []
    for n, item in enumerate(shows):
        eventos_show.append(
            evento_de(
                item,
                venue=item.suggested_venue or "Local a definir",
                cidade=item.suggested_city or "São Paulo",
                uf=item.suggested_state or "SP",
                dias=3 + n * 3.1,
                preco=PRECOS_SHOW[n % len(PRECOS_SHOW)],
                layout=EventLayout.GENERAL,
                capacidade=CAPACIDADES[n % len(CAPACIDADES)],
            )
        )

    # Rascunho: o painel do organizador precisa mostrar estado misto, senão não
    # se vê a diferença entre publicar e não publicar.
    rascunho = evento_de(
        filmes[-1],
        venue="Cine Belas Artes — Sala 5",
        cidade="São Paulo",
        uf="SP",
        dias=30,
        preco=3400,
        layout=EventLayout.SEATED,
        status=EventStatus.DRAFT,
        fileiras=6,
        por_fileira=10,
    )

    db.add_all([*eventos_cinema, *eventos_show, rascunho])
    db.flush()

    # O primeiro filme e o primeiro show são os usados no roteiro de avaliação.
    cinema = eventos_cinema[0]
    show = eventos_show[0]

    # A portaria valida a entrada de um evento específico — é o que permite
    # responder "evento errado" em vez de aceitar qualquer ingresso legítimo.
    portaria.gate_event_id = cinema.id

    # --- Assentos já ocupados no evento do roteiro ---
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

    # --- Procura variada nos outros eventos ---
    # Sem isto a lista "mais procurados" mostraria tudo com 0% vendido, e a
    # seção não demonstraria nada. As proporções são espalhadas de propósito:
    # um quase esgotado, alguns na metade, outros vazios.
    # Ciclo de proporções: cobre todos os eventos em vez dos primeiros, senão
    # a vitrine teria uma dezena de itens com procura e trinta com zero.
    OCUPACAO_ALVO = (0.94, 0.12, 0.58, 0.0, 0.76, 0.31, 0.05, 0.63, 0.22, 0.88, 0.0, 0.44)

    for n, evento in enumerate(eventos_cinema[1:] + eventos_show[1:]):
        alvo = OCUPACAO_ALVO[n % len(OCUPACAO_ALVO)]
        vendidos = int(evento.capacity * alvo)
        if vendidos == 0:
            continue

        if evento.layout is EventLayout.SEATED:
            # Preenche do começo do mapa: os rótulos têm de existir na sala, e
            # a validação de assento é a mesma que a reserva usa.
            for n in range(vendidos):
                fileira, numero = divmod(n, evento.seats_per_row or 1)
                db.add(
                    Reservation(
                        event_id=evento.id,
                        customer_id=ana.id if n % 2 else bruno.id,
                        seat_label=f"{chr(ord('A') + fileira)}{numero + 1}",
                        quantity=1,
                        status=ReservationStatus.PAID,
                    )
                )
        else:
            # Pista: uma reserva agregada em vez de centenas de linhas.
            db.add(
                Reservation(
                    event_id=evento.id,
                    customer_id=bruno.id,
                    seat_label=None,
                    quantity=vendidos,
                    status=ReservationStatus.PAID,
                )
            )

    db.flush()

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
