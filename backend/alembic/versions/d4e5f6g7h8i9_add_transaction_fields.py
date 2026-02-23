"""Add adds, drops, waiver_bid, status_updated to transactions

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2026-02-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6g7h8i9'
down_revision: Union[str, None] = 'c3d4e5f6g7h8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('transactions', sa.Column('adds', sa.JSON(), nullable=True))
    op.add_column('transactions', sa.Column('drops', sa.JSON(), nullable=True))
    op.add_column('transactions', sa.Column('waiver_bid', sa.Integer(), nullable=True))
    op.add_column('transactions', sa.Column('status_updated', sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column('transactions', 'status_updated')
    op.drop_column('transactions', 'waiver_bid')
    op.drop_column('transactions', 'drops')
    op.drop_column('transactions', 'adds')
