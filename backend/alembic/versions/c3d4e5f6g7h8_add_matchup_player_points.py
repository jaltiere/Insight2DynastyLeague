"""Add matchup_player_points table

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2026-02-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6g7h8"
down_revision: Union[str, None] = "b2c3d4e5f6g7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "matchup_player_points",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("matchup_id", sa.Integer(), nullable=False),
        sa.Column("roster_id", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.String(50), nullable=False),
        sa.Column("points", sa.Float(), server_default="0.0"),
        sa.Column("is_starter", sa.Boolean(), server_default="0"),
        sa.ForeignKeyConstraint(["matchup_id"], ["matchups.id"]),
        sa.ForeignKeyConstraint(["roster_id"], ["rosters.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_mpp_matchup_id", "matchup_player_points", ["matchup_id"]
    )
    op.create_index(
        "ix_mpp_player_id", "matchup_player_points", ["player_id"]
    )
    op.create_index(
        "ix_mpp_roster_id", "matchup_player_points", ["roster_id"]
    )


def downgrade() -> None:
    op.drop_table("matchup_player_points")
