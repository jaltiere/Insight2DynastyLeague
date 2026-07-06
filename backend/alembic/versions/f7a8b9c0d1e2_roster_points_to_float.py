"""change roster points_for/points_against to float

Sleeper splits scores into integer and decimal parts (fpts + fpts_decimal);
these columns were Integer, silently truncating the fraction.

Revision ID: f7a8b9c0d1e2
Revises: b1c2d3e4f5a6
Create Date: 2026-07-05 00:01:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'f7a8b9c0d1e2'
down_revision = 'b1c2d3e4f5a6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('rosters', 'points_for',
                    existing_type=sa.Integer(),
                    type_=sa.Float(),
                    existing_nullable=True)
    op.alter_column('rosters', 'points_against',
                    existing_type=sa.Integer(),
                    type_=sa.Float(),
                    existing_nullable=True)


def downgrade() -> None:
    op.alter_column('rosters', 'points_against',
                    existing_type=sa.Float(),
                    type_=sa.Integer(),
                    existing_nullable=True)
    op.alter_column('rosters', 'points_for',
                    existing_type=sa.Float(),
                    type_=sa.Integer(),
                    existing_nullable=True)
