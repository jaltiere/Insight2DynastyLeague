"""Add rookie_year to players

Revision ID: ba3e881fcc08
Revises: e5f6g7h8i9j0
Create Date: 2026-02-23 20:48:51.829938

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ba3e881fcc08'
down_revision = 'e5f6g7h8i9j0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('players', sa.Column('rookie_year', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('players', 'rookie_year')
