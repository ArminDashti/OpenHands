"""Add ACP session-mirror columns to conversation_metadata table.

Durable mirror of the ACP CLI session identity (session id + cwd + CLI
version), harvested from the agent_state webhook stream. On a recycled
sandbox the filesystem copy (base_state.json) is gone; this mirror feeds
ACPAgent.acp_resume_session_id so native session/load resume survives the
recycle (#14506 / agent-canvas#1126). NULL for non-ACP conversations.

Revision ID: 119
Revises: 118
Create Date: 2026-06-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '119'
down_revision: Union[str, None] = '118'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'conversation_metadata',
        sa.Column('acp_session_id', sa.String(), nullable=True),
    )
    op.add_column(
        'conversation_metadata',
        sa.Column('acp_session_cwd', sa.String(), nullable=True),
    )
    op.add_column(
        'conversation_metadata',
        sa.Column('acp_agent_version', sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('conversation_metadata', 'acp_agent_version')
    op.drop_column('conversation_metadata', 'acp_session_cwd')
    op.drop_column('conversation_metadata', 'acp_session_id')
