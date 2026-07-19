"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "players",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("first_name", sa.Text()),
        sa.Column("last_name", sa.Text()),
        sa.Column("country", sa.Text()),
        sa.Column("tour", sa.Text(), nullable=False, server_default="atp"),
        sa.Column("dob", sa.Date()),
        sa.Column("turned_pro", sa.Integer()),
        sa.Column("height_cm", sa.Integer()),
        sa.Column("hand", sa.Text()),
        if_not_exists=True,
    )

    op.create_table(
        "tournaments",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("tour", sa.Text(), nullable=False, server_default="atp"),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("surface", sa.Text()),
        sa.Column("tier", sa.Text()),
        sa.Column("country", sa.Text()),
        sa.Column("city", sa.Text()),
        sa.Column("start_date", sa.Date()),
        sa.Column("end_date", sa.Date()),
        sa.Column("prize_money", sa.BigInteger()),
        sa.Column("draw_size", sa.Integer()),
        if_not_exists=True,
    )

    op.create_table(
        "matches",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("tournament_id", sa.Text(), sa.ForeignKey("tournaments.id")),
        sa.Column("tour", sa.Text(), nullable=False, server_default="atp"),
        sa.Column("year", sa.Integer()),
        sa.Column("surface", sa.Text()),
        sa.Column("round", sa.Text()),
        sa.Column("winner_id", sa.Text(), sa.ForeignKey("players.id")),
        sa.Column("loser_id", sa.Text(), sa.ForeignKey("players.id")),
        sa.Column("winner_name", sa.Text()),
        sa.Column("loser_name", sa.Text()),
        sa.Column("score", sa.Text()),
        sa.Column("winner_sets", sa.Integer()),
        sa.Column("loser_sets", sa.Integer()),
        sa.Column("minutes", sa.Integer()),
        sa.Column("w_aces", sa.Integer()),
        sa.Column("w_dfs", sa.Integer()),
        sa.Column("w_svpt", sa.Integer()),
        sa.Column("w_1stin", sa.Integer()),
        sa.Column("w_1stwon", sa.Integer()),
        sa.Column("w_2ndwon", sa.Integer()),
        sa.Column("w_bpfaced", sa.Integer()),
        sa.Column("w_bpsaved", sa.Integer()),
        sa.Column("l_aces", sa.Integer()),
        sa.Column("l_dfs", sa.Integer()),
        sa.Column("l_svpt", sa.Integer()),
        sa.Column("l_1stin", sa.Integer()),
        sa.Column("l_1stwon", sa.Integer()),
        sa.Column("l_2ndwon", sa.Integer()),
        sa.Column("l_bpfaced", sa.Integer()),
        sa.Column("l_bpsaved", sa.Integer()),
        sa.Column("match_date", sa.Date()),
        sa.Column("infosys_match_id", sa.Text()),
        sa.Column("ibm_match_id", sa.Text()),
        sa.Column("is_live", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("ibm_backfilled", sa.Boolean(), server_default=sa.text("false")),
        if_not_exists=True,
    )

    op.create_table(
        "rankings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("player_id", sa.Text(), sa.ForeignKey("players.id")),
        sa.Column("tour", sa.Text(), nullable=False, server_default="atp"),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("points", sa.Integer()),
        sa.Column("ranking_type", sa.Text(), server_default="standard"),
        sa.Column("week_date", sa.Date(), nullable=False),
        sa.UniqueConstraint("player_id", "week_date", "ranking_type"),
        if_not_exists=True,
    )

    op.create_table(
        "point_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("match_id", sa.Text(), sa.ForeignKey("matches.id")),
        sa.Column("set_number", sa.Integer(), nullable=False),
        sa.Column("game_number", sa.Integer(), nullable=False),
        sa.Column("point_number", sa.Integer(), nullable=False),
        sa.Column("server", sa.Integer()),
        sa.Column("score_before", sa.Text()),
        sa.Column("score_after", sa.Text()),
        sa.Column("p1_games", sa.Integer()),
        sa.Column("p2_games", sa.Integer()),
        sa.Column("p1_sets", sa.Integer()),
        sa.Column("p2_sets", sa.Integer()),
        sa.Column("winner", sa.Integer()),
        sa.Column("point_end_type", sa.Text()),
        sa.Column("serve_speed_kmh", sa.Integer()),
        sa.Column("serve_type", sa.Text()),
        sa.Column("rally_length", sa.Integer()),
        sa.Column("is_break_point", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("is_set_point", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("is_match_point", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("is_game_winner", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("winner_shot", sa.Text()),
        sa.Column("serve_width", sa.Text()),
        sa.Column("serve_depth", sa.Text()),
        sa.Column("return_depth", sa.Text()),
        sa.Column("p1_distance_m", sa.Float()),
        sa.Column("p2_distance_m", sa.Float()),
        sa.Column("sentence", sa.Text()),
        sa.Column("source", sa.Text(), server_default="infosys"),
        sa.Column("raw_data", JSONB()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("match_id", "set_number", "game_number", "point_number"),
        if_not_exists=True,
    )
    op.create_index(
        "ix_point_events_match_set_game",
        "point_events",
        ["match_id", "set_number", "game_number"],
        if_not_exists=True,
    )

    op.create_table(
        "match_keystats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("match_id", sa.Text(), sa.ForeignKey("matches.id")),
        sa.Column("set_number", sa.Integer()),
        sa.Column("player", sa.Integer()),
        sa.Column("stat_name", sa.Text()),
        sa.Column("value", sa.Text()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("match_id", "set_number", "player", "stat_name"),
        if_not_exists=True,
    )

    op.create_table(
        "match_rally",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("match_id", sa.Text(), sa.ForeignKey("matches.id")),
        sa.Column("rally_length", sa.Integer()),
        sa.Column("count", sa.Integer()),
        sa.Column("winner_player", sa.Integer()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        if_not_exists=True,
    )

    op.create_table(
        "live_polls",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("match_id", sa.Text()),
        sa.Column("polled_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Column("new_points", sa.Integer()),
        sa.Column("status", sa.Text()),
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_table("live_polls")
    op.drop_table("match_rally")
    op.drop_table("match_keystats")
    op.drop_index("ix_point_events_match_set_game", table_name="point_events")
    op.drop_table("point_events")
    op.drop_table("rankings")
    op.drop_table("matches")
    op.drop_table("tournaments")
    op.drop_table("players")
