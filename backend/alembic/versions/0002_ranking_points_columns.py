"""add ranking points columns to matches

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("matches", sa.Column("winner_ranking_points", sa.Integer()))
    op.add_column("matches", sa.Column("loser_ranking_points", sa.Integer()))


def downgrade() -> None:
    op.drop_column("matches", "loser_ranking_points")
    op.drop_column("matches", "winner_ranking_points")
