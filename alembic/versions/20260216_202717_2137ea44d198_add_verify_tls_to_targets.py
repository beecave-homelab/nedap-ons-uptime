"""Add verify_tls to targets

Revision ID: 2137ea44d198
Revises: 001
Create Date: 2026-02-16 20:27:17.371004

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2137ea44d198'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add verify_tls column with default True for existing rows
    op.add_column('targets', sa.Column('verify_tls', sa.Boolean(), nullable=False, server_default='true'))
    # Remove server_default after column is populated
    op.alter_column('targets', 'verify_tls', server_default=None)


def downgrade() -> None:
    op.drop_column('targets', 'verify_tls')
