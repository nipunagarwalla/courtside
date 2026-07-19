"""add enrichment columns to players

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COLUMNS = [
    sa.Column("coach", sa.Text()),
    sa.Column("weight_kg", sa.Integer()),
    sa.Column("career_prize", sa.Text()),
    sa.Column("hi_rank", sa.Integer()),
    sa.Column("hi_rank_date", sa.Date()),
    sa.Column("ytd_wins", sa.Integer()),
    sa.Column("ytd_losses", sa.Integer()),
    sa.Column("ytd_titles", sa.Integer()),
    sa.Column("career_wins", sa.Integer()),
    sa.Column("career_losses", sa.Integer()),
    sa.Column("career_titles", sa.Integer()),
]


def upgrade() -> None:
    for col in COLUMNS:
        op.add_column("players", col)


def downgrade() -> None:
    for col in reversed(COLUMNS):
        op.drop_column("players", col.name)
