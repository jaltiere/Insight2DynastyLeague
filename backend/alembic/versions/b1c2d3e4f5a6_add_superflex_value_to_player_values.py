"""add superflex value columns to player_values

Revision ID: b1c2d3e4f5a6
Revises: a9f3c2e1d4b7
Create Date: 2026-05-19 00:01:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'b1c2d3e4f5a6'
down_revision = 'a9f3c2e1d4b7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('player_values', sa.Column('superflex_value', sa.Integer(), nullable=True))
    op.add_column('player_values', sa.Column('superflex_rank', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('player_values', 'superflex_rank')
    op.drop_column('player_values', 'superflex_value')
