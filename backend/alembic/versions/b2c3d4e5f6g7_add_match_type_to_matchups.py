"""Add match_type to matchups

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('matchups', sa.Column('match_type', sa.String(length=20), nullable=True))
    op.execute("UPDATE matchups SET match_type = 'regular' WHERE match_type IS NULL")
    op.alter_column('matchups', 'match_type', server_default='regular')


def downgrade() -> None:
    op.drop_column('matchups', 'match_type')
