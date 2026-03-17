"""add_matchup_recaps_table

Revision ID: d81cf4157f4a
Revises: caba8e073524
Create Date: 2026-03-17 14:27:19.275619

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd81cf4157f4a'
down_revision = 'caba8e073524'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create matchup_recaps table
    op.create_table(
        'matchup_recaps',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('matchup_id', sa.Integer(), nullable=False),
        sa.Column('recap_text', sa.Text(), nullable=True),
        sa.Column('predictions_text', sa.Text(), nullable=True),
        sa.Column('generated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('week', sa.Integer(), nullable=False),
        sa.Column('season_id', sa.Integer(), nullable=False),
        sa.Column('recap_type', sa.String(length=20), server_default='weekly', nullable=False),
        sa.Column('recap_metadata', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['matchup_id'], ['matchups.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['season_id'], ['seasons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('idx_matchup_recap', 'matchup_recaps', ['matchup_id'])
    op.create_index('idx_season_week', 'matchup_recaps', ['season_id', 'week'])

    # Create unique constraint for matchup_id + recap_type
    op.create_unique_constraint('unique_matchup_recap_type', 'matchup_recaps', ['matchup_id', 'recap_type'])


def downgrade() -> None:
    # Drop table (indexes and constraints will be dropped automatically)
    op.drop_table('matchup_recaps')
