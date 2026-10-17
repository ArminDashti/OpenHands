"""create device auth table

Revision ID: 084
Revises: 083
Create Date: 2025-12-08

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '084'
down_revision: Union[str, None] = '083'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create device_auth_sessions table for OAuth Device Flow."""
    op.create_table(
        'device_auth_sessions',
        sa.Column('device_code', sa.String(255), primary_key=True),
        sa.Column('user_code', sa.String(10), unique=True, nullable=False),
        sa.Column('user_id', sa.String(255), nullable=True),
        sa.Column('api_key', sa.String(255), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
    )

    # Create indices for better performance
    op.create_index(
        'idx_device_auth_user_code',
        'device_auth_sessions',
        ['user_code'],
    )
    op.create_index(
        'idx_device_auth_expires_at',
        'device_auth_sessions',
        ['expires_at'],
    )
    op.create_index(
        'idx_device_auth_status',
        'device_auth_sessions',
        ['status'],
    )


def downgrade() -> None:
    """Drop device_auth_sessions table."""
    op.drop_index('idx_device_auth_status', table_name='device_auth_sessions')
    op.drop_index('idx_device_auth_expires_at', table_name='device_auth_sessions')
    op.drop_index('idx_device_auth_user_code', table_name='device_auth_sessions')
    op.drop_table('device_auth_sessions')
