"""Dummy test migration to trigger enterprise-check-migrations workflow

Revision ID: 102
Revises: 101
Create Date: 2025-03-21 00:00:00.000000

This is a no-op migration created solely to test the enterprise-check-migrations
GitHub Action workflow (PR #12190).
"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = '102'
down_revision: Union[str, None] = '101'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op migration for testing purposes."""
    pass


def downgrade() -> None:
    """No-op migration for testing purposes."""
    pass
