"""add hashed_password to users

Revision ID: a1b2c3d4e5f6
Revises: eb42e7a9a3e2
Create Date: 2026-07-27 14:50:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "eb42e7a9a3e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("hashed_password", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "hashed_password")
