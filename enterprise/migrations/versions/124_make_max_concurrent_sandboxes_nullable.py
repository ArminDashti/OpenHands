"""Make max_concurrent_sandboxes nullable.

Revision ID: 124
Revises: 123
Create Date: 2026-06-16
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '124'
down_revision: Union[str, None] = '123'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'org',
        'max_concurrent_sandboxes',
        existing_type=sa.Integer(),
        nullable=True,
        server_default=None,
    )
    op.execute("""
        UPDATE org
        SET max_concurrent_sandboxes = NULL
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE org
        SET max_concurrent_sandboxes = 3
        WHERE max_concurrent_sandboxes IS NULL
        AND id IN (SELECT id FROM "user")
    """)
    op.execute("""
        UPDATE org
        SET max_concurrent_sandboxes = 10
        WHERE max_concurrent_sandboxes IS NULL
    """)
    op.alter_column(
        'org',
        'max_concurrent_sandboxes',
        existing_type=sa.Integer(),
        nullable=False,
        server_default='10',
    )
