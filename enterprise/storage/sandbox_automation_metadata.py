"""Storage model for sandbox automation metadata.

This module provides storage for associating automation metadata with sandboxes.
When an automation run creates a sandbox, it can store metadata here which will
be copied to any conversations created within that sandbox.
"""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from storage.base import Base


class SandboxAutomationMetadataModel(Base):
    """SQLAlchemy model for sandbox automation metadata."""

    __tablename__ = 'sandbox_automation_metadata'

    sandbox_id = Column(String(255), primary_key=True)
    automation_id = Column(String(255), nullable=True, index=True)
    automation_name = Column(String(500), nullable=True)
    trigger_type = Column(String(100), nullable=True)
    run_id = Column(String(255), nullable=True, index=True)
    # Store any additional metadata as JSON
    extra_metadata = Column(JSONB, nullable=True, default=dict)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    # Note: No __table_args__ needed - primary key auto-indexes sandbox_id


class SandboxAutomationMetadata(BaseModel):
    """Pydantic model for sandbox automation metadata."""

    sandbox_id: str
    automation_id: str | None = None
    automation_name: str | None = None
    trigger_type: str | None = Field(
        default=None,
        description='The type of trigger that initiated the automation (e.g., cron, webhook)',
    )
    run_id: str | None = Field(
        default=None,
        description='The automation run ID',
    )
    extra_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description='Additional metadata as key-value pairs',
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def from_orm(cls, model: SandboxAutomationMetadataModel) -> 'SandboxAutomationMetadata':
        """Create a Pydantic model from the SQLAlchemy model."""
        return cls(
            sandbox_id=model.sandbox_id,
            automation_id=model.automation_id,
            automation_name=model.automation_name,
            trigger_type=model.trigger_type,
            run_id=model.run_id,
            extra_metadata=model.extra_metadata or {},
            created_at=model.created_at,
        )
