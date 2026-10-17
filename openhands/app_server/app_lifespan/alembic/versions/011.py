"""Add acp_agent_settings_snapshot column to conversation_metadata table

Revision ID: 011
Revises: 010
Create Date: 2026-06-05

Stores a secret-free snapshot of the ACP agent spec, frozen at conversation
creation, so a later edit to the user's global agent settings cannot silently
re-target an in-flight ACP conversation when its recycled sandbox is rebuilt
(agent-canvas#1015). Provider credentials and other secrets are NOT persisted
here — they are re-resolved from the live encrypted vault on every build
(agent-canvas#1016) — so a plain JSON column is sufficient. NULL for non-ACP
conversations and for ACP conversations created before this column landed.
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '011'
down_revision: str | None = '010'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'conversation_metadata',
        sa.Column('acp_agent_settings_snapshot', sa.JSON, nullable=True),
    )


def downgrade() -> None:
    op.drop_column('conversation_metadata', 'acp_agent_settings_snapshot')
