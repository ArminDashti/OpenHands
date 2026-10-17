"""Add display_name column to conversation_metadata table.

Stores the human-readable label for ACP conversations separately from
llm_model, so ACP conversations can set display_name = "ACP: <agent>"
and leave llm_model null.

Revision ID: 113
Revises: 112
Create Date: 2026-04-30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '113'
down_revision: Union[str, None] = '112'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'conversation_metadata',
        sa.Column('display_name', sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('conversation_metadata', 'display_name')
