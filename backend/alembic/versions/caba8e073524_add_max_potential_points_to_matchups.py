"""Add max potential points to matchups

Revision ID: caba8e073524
Revises: ba3e881fcc08
Create Date: 2026-03-02 21:47:44.445334

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'caba8e073524'
down_revision = 'ba3e881fcc08'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add max_potential_points columns for home and away teams
    op.add_column('matchups', sa.Column('home_max_potential_points', sa.Float(), nullable=True))
    op.add_column('matchups', sa.Column('away_max_potential_points', sa.Float(), nullable=True))


def downgrade() -> None:
    # Remove max_potential_points columns
    op.drop_column('matchups', 'away_max_potential_points')
    op.drop_column('matchups', 'home_max_potential_points')
