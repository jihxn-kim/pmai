"""add_expertise_to_users

Revision ID: a1b2c3d4e5f6
Revises: d29d8a0f7510
Create Date: 2026-03-26 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "d29d8a0f7510"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("expertise", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "expertise")
