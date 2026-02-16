"""Add metadata column to leagues table

Revision ID: a1b2c3d4e5f6
Revises: de3b9f4b3a7d
Create Date: 2026-02-16

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'de3b9f4b3a7d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('leagues', sa.Column('metadata', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('leagues', 'metadata')
