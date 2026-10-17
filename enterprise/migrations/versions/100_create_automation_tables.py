"""Create automation tables (automations, automation_events, automation_runs)

Revision ID: 100
Revises: 099
Create Date: 2025-03-10 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '100'
down_revision: Union[str, None] = '099'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- automation_events (must come first, referenced by automation_runs) ---
    op.create_table(
        'automation_events',
        sa.Column('id', sa.BigInteger(), sa.Identity(), nullable=False, primary_key=True),
        sa.Column('source_type', sa.String(), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('dedup_key', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default=sa.text("'NEW'")),
        sa.Column('error_detail', sa.Text(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP'),
        ),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('dedup_key', name='uq_automation_events_dedup'),
    )
    op.create_index(
        'ix_automation_events_new',
        'automation_events',
        ['created_at'],
        postgresql_where=sa.text("status = 'NEW'"),
    )

    # --- automations ---
    op.create_table(
        'automations',
        sa.Column('id', sa.String(), nullable=False, primary_key=True),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('org_id', sa.String(), nullable=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('TRUE')),
        sa.Column('config', sa.JSON(), nullable=False),
        sa.Column('trigger_type', sa.String(), nullable=False),
        sa.Column('file_store_key', sa.String(), nullable=False),
        sa.Column('last_triggered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP'),
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP'),
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_automations_user_id', 'automations', ['user_id'])
    op.create_index('ix_automations_org_id', 'automations', ['org_id'])
    op.create_index('ix_automations_enabled_trigger', 'automations', ['enabled', 'trigger_type'])

    # --- automation_runs ---
    op.create_table(
        'automation_runs',
        sa.Column('id', sa.String(), nullable=False, primary_key=True),
        sa.Column(
            'automation_id',
            sa.String(),
            sa.ForeignKey('automations.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'event_id',
            sa.BigInteger(),
            sa.ForeignKey('automation_events.id'),
            nullable=True,
        ),
        sa.Column('conversation_id', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column('claimed_by', sa.String(), nullable=True),
        sa.Column('claimed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('heartbeat_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default=sa.text('3')),
        sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('event_payload', sa.JSON(), nullable=True),
        sa.Column('error_detail', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP'),
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_automation_runs_automation_id', 'automation_runs', ['automation_id'])
    op.create_index(
        'ix_automation_runs_claimable',
        'automation_runs',
        ['status', 'next_retry_at'],
        postgresql_where=sa.text("status = 'PENDING' AND (next_retry_at IS NULL OR next_retry_at <= now())"),
    )
    op.create_index(
        'ix_automation_runs_heartbeat',
        'automation_runs',
        ['heartbeat_at'],
        postgresql_where=sa.text("status = 'RUNNING'"),
    )


def downgrade() -> None:
    op.drop_table('automation_runs')
    op.drop_table('automations')
    op.drop_table('automation_events')
