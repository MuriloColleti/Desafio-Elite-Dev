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


class Genre(StrEnum):
    """Gênero do evento.

    Um enum só para filme e show, e não dois: a vitrine filtra por gênero
    independentemente do tipo, e dois enums exigiriam duas colunas ou um campo
    polimórfico para nada. O valor já diz a que família pertence.
    """

    # --- Filme ---
    ACAO = "ACAO"
    AVENTURA = "AVENTURA"
    ANIMACAO = "ANIMACAO"
    COMEDIA = "COMEDIA"
    DOCUMENTARIO = "DOCUMENTARIO"
    DRAMA = "DRAMA"
    FANTASIA = "FANTASIA"
    FICCAO = "FICCAO"
    ROMANCE = "ROMANCE"
    SUSPENSE = "SUSPENSE"
    TERROR = "TERROR"

    # --- Show ---
    AXE = "AXE"
    ELETRONICA = "ELETRONICA"
    FORRO = "FORRO"
    FUNK = "FUNK"
    MPB = "MPB"
    PAGODE = "PAGODE"
    RAP = "RAP"
    REGGAE = "REGGAE"
    ROCK = "ROCK"
    SAMBA = "SAMBA"
    SERTANEJO = "SERTANEJO"

    @classmethod
    def de_filme(cls) -> tuple["Genre", ...]:
        return (
            cls.ACAO,
            cls.AVENTURA,
            cls.ANIMACAO,
            cls.COMEDIA,
            cls.DOCUMENTARIO,
            cls.DRAMA,
            cls.FANTASIA,
            cls.FICCAO,
            cls.ROMANCE,
            cls.SUSPENSE,
            cls.TERROR,
        )

    @classmethod
    def de_show(cls) -> tuple["Genre", ...]:
        return (
            cls.AXE,
            cls.ELETRONICA,
            cls.FORRO,
            cls.FUNK,
            cls.MPB,
            cls.PAGODE,
            cls.RAP,
            cls.REGGAE,
            cls.ROCK,
            cls.SAMBA,
            cls.SERTANEJO,
        )


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
