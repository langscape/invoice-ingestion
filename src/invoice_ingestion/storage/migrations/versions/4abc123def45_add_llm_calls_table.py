"""Add llm_calls table and correction_category column

Revision ID: 4abc123def45
Revises: 3cf1c51da32a
Create Date: 2026-02-05 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4abc123def45'
down_revision = '3cf1c51da32a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add llm_calls table
    op.create_table('llm_calls',
        sa.Column('call_id', sa.Uuid(), nullable=False),
        sa.Column('extraction_id', sa.Uuid(), nullable=True),
        sa.Column('stage', sa.String(length=50), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('system_prompt', sa.Text(), nullable=True),
        sa.Column('user_prompt', sa.Text(), nullable=False),
        sa.Column('has_images', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('image_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('max_tokens', sa.Integer(), nullable=True),
        sa.Column('response_content', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('input_tokens', sa.Integer(), nullable=True),
        sa.Column('output_tokens', sa.Integer(), nullable=True),
        sa.Column('total_tokens', sa.Integer(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['extraction_id'], ['extractions.extraction_id'], ),
        sa.PrimaryKeyConstraint('call_id')
    )
    op.create_index(op.f('ix_llm_calls_extraction_id'), 'llm_calls', ['extraction_id'], unique=False)

    # Note: correction_category column already exists in corrections table


def downgrade() -> None:
    # Drop llm_calls table
    op.drop_index(op.f('ix_llm_calls_extraction_id'), table_name='llm_calls')
    op.drop_table('llm_calls')
