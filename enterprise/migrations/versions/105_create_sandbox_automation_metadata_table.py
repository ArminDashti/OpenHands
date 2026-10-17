"""Create sandbox_automation_metadata table.

This table stores automation context for sandboxes, allowing conversations
created within automation-triggered sandboxes to inherit metadata like
automation_id, trigger_type, and run_id.

The automation service sets this metadata via PUT /api/service/sandboxes/{id}/automation-metadata
after creating a sandbox. When conversations are created, the webhook handler
looks up this metadata and copies relevant fields (like trigger=AUTOMATION) to
the conversation.

Revision ID: 105
Revises: 104
Create Date: 2026-03-31
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '105'
down_revision: Union[str, None] = '104'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'sandbox_automation_metadata',
        sa.Column('sandbox_id', sa.String(255), primary_key=True),
        sa.Column('automation_id', sa.String(255), nullable=True),
        sa.Column('automation_name', sa.String(500), nullable=True),
        sa.Column('trigger_type', sa.String(100), nullable=True),
        sa.Column('run_id', sa.String(255), nullable=True),
        sa.Column(
            'extra_metadata',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default='{}',
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Create indexes for common lookups
    op.create_index(
        'ix_sandbox_automation_metadata_automation_id',
        'sandbox_automation_metadata',
        ['automation_id'],
    )
    op.create_index(
        'ix_sandbox_automation_metadata_run_id',
        'sandbox_automation_metadata',
        ['run_id'],
    )


def downgrade() -> None:
    op.drop_index(
        'ix_sandbox_automation_metadata_run_id',
        table_name='sandbox_automation_metadata',
    )
    op.drop_index(
        'ix_sandbox_automation_metadata_automation_id',
        table_name='sandbox_automation_metadata',
    )
    op.drop_table('sandbox_automation_metadata')
