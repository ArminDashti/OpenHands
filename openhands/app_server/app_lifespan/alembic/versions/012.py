"""Add ACP session-mirror columns to conversation_metadata table

Revision ID: 012
Revises: 011
Create Date: 2026-06-07

Durable mirror of the ACP CLI session identity (session id + cwd + CLI
version), harvested from the agent_state webhook stream. On a recycled
sandbox the filesystem copy (base_state.json) is gone; this mirror feeds
ACPAgent.acp_resume_session_id so native session/load resume survives the
recycle (#14506 / agent-canvas#1126). NULL for non-ACP conversations.
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '012'
down_revision: str | None = '011'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


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
