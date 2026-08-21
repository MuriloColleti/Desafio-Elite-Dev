"""adiciona localizacao ao evento

Revision ID: 1979d4f1f6d6
Revises: 50fea5d396a6
Create Date: 2026-08-21

Cidade, estado e país em colunas próprias, indexadas, em vez de extraídas do
texto de `venue`: separar "Circo Voador, Rio de Janeiro" por vírgula funciona
nos dados que nós escrevemos e quebra em qualquer venue digitado de outro jeito.

Nota sobre o autogenerate: ele propôs **remover** os sete CHECK constraints de
enum criados na migration anterior, porque eles não existem no modelo
SQLAlchemy (`native_enum=False` valida no Python). Aceitar a proposta desfaria
aquela correção em silêncio — os `drop_constraint` foram retirados à mão.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "1979d4f1f6d6"
down_revision: str | None = "50fea5d396a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

COLUNAS = (
    ("city", 120),
    ("state", 2),
    ("country", 2),
)


def upgrade() -> None:
    for nome, tamanho in COLUNAS:
        op.add_column("events", sa.Column(nome, sa.String(length=tamanho), nullable=True))
        op.create_index(op.f(f"ix_events_{nome}"), "events", [nome], unique=False)


def downgrade() -> None:
    for nome, _ in reversed(COLUNAS):
        op.drop_index(op.f(f"ix_events_{nome}"), table_name="events")
        op.drop_column("events", nome)
