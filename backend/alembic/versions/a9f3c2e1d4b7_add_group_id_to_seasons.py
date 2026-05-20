"""add_group_id_to_seasons

Revision ID: a9f3c2e1d4b7
Revises: fb23e8fa206a
Create Date: 2026-05-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a9f3c2e1d4b7'
down_revision = 'fb23e8fa206a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # group_id is the stable canonical league identifier shared by all seasons
    # in the same dynasty chain. Populated by sync_all_history/sync_league.
    op.add_column('seasons', sa.Column('group_id', sa.String(50), nullable=True))
    op.create_index('ix_seasons_group_id', 'seasons', ['group_id'])


def downgrade() -> None:
    op.drop_index('ix_seasons_group_id', table_name='seasons')
    op.drop_column('seasons', 'group_id')
