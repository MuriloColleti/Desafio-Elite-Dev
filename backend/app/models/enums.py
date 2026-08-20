"""Enums do domínio.

Guardados como string no banco (`native_enum=False` nos modelos) em vez de tipo
ENUM do Postgres: adicionar um valor novo passa a ser mudança de código, não
migration de tipo — e o custo é só o de um CHECK constraint.
"""

from enum import StrEnum


class Role(StrEnum):
    ORGANIZER = "ORGANIZER"
    CUSTOMER = "CUSTOMER"
    GATE = "GATE"


class EventLayout(StrEnum):
    SEATED = "SEATED"  # cinema/teatro: lugar marcado, mapa de assentos
    GENERAL = "GENERAL"  # pista: só quantidade


class EventStatus(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    CANCELLED = "CANCELLED"


class ReservationStatus(StrEnum):
    PENDING = "PENDING"  # hold, ainda não pago
    PAID = "PAID"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"

    @classmethod
    def occupying(cls) -> tuple["ReservationStatus", ...]:
        """Status que ocupam lugar — os que entram no índice de unicidade."""
        return (cls.PENDING, cls.PAID)


class PaymentStatus(StrEnum):
    APPROVED = "APPROVED"
    DECLINED = "DECLINED"


class TicketStatus(StrEnum):
    VALID = "VALID"
    USED = "USED"
    CANCELLED = "CANCELLED"


class GateResult(StrEnum):
    """As quatro respostas que o PDF exige da portaria."""

    VALID = "VALID"
    INVALID = "INVALID"
    ALREADY_USED = "ALREADY_USED"
    WRONG_EVENT = "WRONG_EVENT"
