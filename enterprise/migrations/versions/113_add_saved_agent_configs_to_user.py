"""Add saved_agent_configs column to user table.

The Settings model exposes ``saved_agent_configs`` (snapshots of agent
settings per kind), but without a column on the User row the field is
silently dropped on store() and always defaults to empty on load(), so
switching between agent kinds loses the user's previous config.

The column is plain ``String`` because the ORM-level ``EncryptedJSON``
TypeDecorator stores JSON-serialized data as a JWE-encrypted string —
configs can carry per-kind ``api_key`` values, so the at-rest
representation must match the existing org/member encrypted-secret pattern.

Revision ID: 113
Revises: 112
Create Date: 2026-05-18
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
    op.add_column('user', sa.Column('saved_agent_configs', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('user', 'saved_agent_configs')
