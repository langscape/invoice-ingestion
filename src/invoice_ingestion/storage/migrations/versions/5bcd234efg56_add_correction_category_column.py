"""Add correction_category column to corrections table

Revision ID: 5bcd234efg56
Revises: 4abc123def45
Create Date: 2026-02-08 13:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5bcd234efg56'
down_revision = '4abc123def45'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('corrections', sa.Column('correction_category', sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column('corrections', 'correction_category')
