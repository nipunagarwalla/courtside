"""add infosys_event_id to matches

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("matches", sa.Column("infosys_event_id", sa.Text()))


def downgrade() -> None:
    op.drop_column("matches", "infosys_event_id")
