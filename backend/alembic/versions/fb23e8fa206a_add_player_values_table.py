"""add_player_values_table

Revision ID: fb23e8fa206a
Revises: e1f2a3b4c5d6
Create Date: 2026-04-10 20:09:23.503396

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fb23e8fa206a'
down_revision = 'e1f2a3b4c5d6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'player_values',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('player_id', sa.String(length=50), nullable=True),
        sa.Column('pick_key', sa.String(length=50), nullable=True),
        sa.Column('ktc_name', sa.String(length=200), nullable=False),
        sa.Column('value', sa.Integer(), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=True),
        sa.Column('source', sa.String(length=20), nullable=False),
        sa.Column('position', sa.String(length=10), nullable=True),
        sa.Column('team', sa.String(length=10), nullable=True),
        sa.Column('age', sa.String(length=10), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('pick_key', name='uq_player_values_pick_key'),
        sa.UniqueConstraint('player_id', name='uq_player_values_player_id'),
    )
    op.create_index('ix_player_values_pick_key', 'player_values', ['pick_key'], unique=False)
    op.create_index('ix_player_values_player_id', 'player_values', ['player_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_player_values_player_id', table_name='player_values')
    op.drop_index('ix_player_values_pick_key', table_name='player_values')
    op.drop_table('player_values')
