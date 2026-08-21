"""adiciona genero ao evento e CHECK nos enums

Revision ID: 50fea5d396a6
Revises: 6ee76beeffb1
Create Date: 2026-08-20 20:34:31.567297

Além da coluna `genre`, esta migration corrige uma lacuna que existia desde o
schema inicial: **nenhum enum tinha CHECK no banco**. Com `native_enum=False` o
SQLAlchemy valida no Python, mas o autogenerate do Alembic não emite o CHECK
correspondente — então um `UPDATE` direto gravava qualquer string em `role`,
`status` ou `layout`, e o erro só apareceria na leitura.

Descoberto ao conferir `pg_constraint` depois de aplicar a migration, e não ao
ler o arquivo gerado.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "50fea5d396a6"
down_revision: str | None = "6ee76beeffb1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

GENEROS = (
    "ACAO",
    "AVENTURA",
    "ANIMACAO",
    "COMEDIA",
    "DOCUMENTARIO",
    "DRAMA",
    "FANTASIA",
    "FICCAO",
    "ROMANCE",
    "SUSPENSE",
    "TERROR",
    "AXE",
    "ELETRONICA",
    "FORRO",
    "FUNK",
    "MPB",
    "PAGODE",
    "RAP",
    "REGGAE",
    "ROCK",
    "SAMBA",
    "SERTANEJO",
)

# (tabela, coluna, valores aceitos, aceita nulo)
CHECKS = (
    ("users", "role", ("ORGANIZER", "CUSTOMER", "GATE"), False),
    ("events", "layout", ("SEATED", "GENERAL"), False),
    ("events", "status", ("DRAFT", "PUBLISHED", "CANCELLED"), False),
    ("events", "genre", GENEROS, True),
    ("reservations", "status", ("PENDING", "PAID", "CANCELLED", "EXPIRED"), False),
    ("payments", "status", ("APPROVED", "DECLINED"), False),
    ("tickets", "status", ("VALID", "USED", "CANCELLED"), False),
)


def _nome(tabela: str, coluna: str) -> str:
    return f"ck_{tabela}_{coluna}_valido"


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column(
            "genre",
            sa.Enum(*GENEROS, name="genre", native_enum=False, length=32),
            nullable=True,
        ),
    )
    op.create_index(op.f("ix_events_genre"), "events", ["genre"], unique=False)

    for tabela, coluna, valores, aceita_nulo in CHECKS:
        lista = ", ".join(f"'{v}'" for v in valores)
        condicao = f"{coluna} IN ({lista})"
        if aceita_nulo:
            condicao = f"{coluna} IS NULL OR {condicao}"
        op.create_check_constraint(_nome(tabela, coluna), tabela, condicao)


def downgrade() -> None:
    for tabela, coluna, _, _ in CHECKS:
        op.drop_constraint(_nome(tabela, coluna), tabela, type_="check")

    op.drop_index(op.f("ix_events_genre"), table_name="events")
    op.drop_column("events", "genre")
