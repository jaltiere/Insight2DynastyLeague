"""add_power_ranking_snapshots_table

Revision ID: e1f2a3b4c5d6
Revises: d81cf4157f4a
Create Date: 2026-04-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e1f2a3b4c5d6'
down_revision = 'd81cf4157f4a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'power_ranking_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('season_year', sa.Integer(), nullable=False),
        sa.Column('week', sa.Integer(), nullable=False),
        sa.Column('roster_id', sa.Integer(), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('total_score', sa.Float(), nullable=False),
        sa.Column('current_season_score', sa.Float(), nullable=False),
        sa.Column('roster_value_score', sa.Float(), nullable=False),
        sa.Column('historical_score', sa.Float(), nullable=False),
        sa.Column('snapped_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('season_year', 'week', 'roster_id', name='uq_power_ranking_snapshot'),
    )
    op.create_index('ix_power_ranking_snapshots_season_year', 'power_ranking_snapshots', ['season_year'])


def downgrade() -> None:
    op.drop_index('ix_power_ranking_snapshots_season_year', table_name='power_ranking_snapshots')
    op.drop_table('power_ranking_snapshots')
