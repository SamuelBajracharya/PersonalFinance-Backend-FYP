"""add_is_successful_to_budgets

Revision ID: 0deda326e57b
Revises: f01d5319e7b1
Create Date: 2026-05-30 22:35:54.127714

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0deda326e57b'
down_revision: Union[str, Sequence[str], None] = 'f01d5319e7b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('budgets', sa.Column('is_successful', sa.Boolean(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('budgets', 'is_successful')
