"""add group_id to power_ranking_snapshots

Snapshots were keyed (season_year, week, roster_id) where roster_id is
Sleeper's per-league 1..N — the three configured leagues overwrote each
other's rows on every Tuesday snapshot. Adds the canonical league group_id
and includes it in the unique constraint. Existing rows (NULL group_id,
cross-league corrupted) are deleted so trends restart clean per league.

Revision ID: c6d7e8f9a0b1
Revises: b5c6d7e8f9a0
Create Date: 2026-07-06 00:02:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'c6d7e8f9a0b1'
down_revision = 'b5c6d7e8f9a0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing rows are a cross-league mix (each league overwrote the last);
    # they cannot be attributed to a league retroactively.
    op.execute("DELETE FROM power_ranking_snapshots")
    op.add_column('power_ranking_snapshots', sa.Column('group_id', sa.String(50), nullable=True))
    op.create_index('ix_power_ranking_snapshots_group_id', 'power_ranking_snapshots', ['group_id'])
    op.drop_constraint('uq_power_ranking_snapshot', 'power_ranking_snapshots', type_='unique')
    op.create_unique_constraint(
        'uq_power_ranking_snapshot',
        'power_ranking_snapshots',
        ['group_id', 'season_year', 'week', 'roster_id'],
    )


def downgrade() -> None:
    op.drop_constraint('uq_power_ranking_snapshot', 'power_ranking_snapshots', type_='unique')
    op.create_unique_constraint(
        'uq_power_ranking_snapshot',
        'power_ranking_snapshots',
        ['season_year', 'week', 'roster_id'],
    )
    op.drop_index('ix_power_ranking_snapshots_group_id', 'power_ranking_snapshots')
    op.drop_column('power_ranking_snapshots', 'group_id')
