"""add TE-premium KTC value columns to player_values

All three configured leagues enabled TE premium (scoring_settings
bonus_rec_te = 0.5) for the 2026 season, but the scraper only stored KTC's
base values, undervaluing every tight end by roughly 11%. KTC already ships
tep/tepp/teppp variants in the same payload; only tep is stored because the
higher tiers pin elite tight ends to the 9999 ceiling.

Columns are nullable and left empty here — the next KTC refresh populates
them, and every read coalesces down to the existing base value until then, so
this migration is safe to apply before a sync runs.

Revision ID: d7e8f9a0b1c2
Revises: c6d7e8f9a0b1
Create Date: 2026-08-28 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'd7e8f9a0b1c2'
down_revision = 'c6d7e8f9a0b1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('player_values', sa.Column('tep_value', sa.Integer(), nullable=True))
    op.add_column('player_values', sa.Column('tep_rank', sa.Integer(), nullable=True))
    op.add_column('player_values', sa.Column('superflex_tep_value', sa.Integer(), nullable=True))
    op.add_column('player_values', sa.Column('superflex_tep_rank', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('player_values', 'superflex_tep_rank')
    op.drop_column('player_values', 'superflex_tep_value')
    op.drop_column('player_values', 'tep_rank')
    op.drop_column('player_values', 'tep_value')
