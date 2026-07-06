"""add bracket_placement to matchups

Stores Sleeper's bracket placement field (p) for playoff-week matchups:
1 = championship game, 3 = 3rd place game, etc. (within its bracket).
Used to label bracket games from real data instead of hardcoded matchup IDs.

Revision ID: b5c6d7e8f9a0
Revises: f7a8b9c0d1e2
Create Date: 2026-07-06 00:01:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'b5c6d7e8f9a0'
down_revision = 'f7a8b9c0d1e2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('matchups', sa.Column('bracket_placement', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('matchups', 'bracket_placement')
