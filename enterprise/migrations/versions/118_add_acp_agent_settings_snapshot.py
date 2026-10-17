"""Add acp_agent_settings_snapshot column to conversation_metadata table.

Stores a secret-free snapshot of the ACP agent spec, frozen at conversation
creation, so a later edit to the user's global agent settings cannot silently
re-target an in-flight ACP conversation when its recycled sandbox is rebuilt
(agent-canvas#1015). Provider credentials and other secrets are NOT persisted
here — they are re-resolved from the live encrypted vault on every build
(agent-canvas#1016) — so a plain JSON column is sufficient. NULL for non-ACP
conversations and for ACP conversations created before this column landed.

Revision ID: 118
Revises: 117
Create Date: 2026-06-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '118'
down_revision: Union[str, None] = '117'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'conversation_metadata',
        sa.Column('acp_agent_settings_snapshot', sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('conversation_metadata', 'acp_agent_settings_snapshot')
