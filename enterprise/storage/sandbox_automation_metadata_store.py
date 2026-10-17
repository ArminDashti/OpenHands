"""Store for sandbox automation metadata.

This module provides CRUD operations for sandbox automation metadata.

Cleanup Strategy:
-----------------
Metadata records are ephemeral and only needed during the short window between
sandbox creation and conversation creation. Once a conversation is created,
the metadata is copied to the conversation and no longer needed.

Cleanup is handled via a TTL-based approach:
- Records older than 24 hours can be safely deleted (sandboxes typically run < 1 hour)
- A periodic cleanup job should be added to delete stale records
- The created_at column enables efficient cleanup queries

Note: We intentionally don't use CASCADE foreign keys because:
1. Sandboxes are managed by a separate runtime system (not this DB)
2. The cost of orphaned records is low (small table, easily cleaned up)
"""

import logging
from typing import Any

from sqlalchemy import delete, select
from storage.database import get_session
from storage.sandbox_automation_metadata import (
    SandboxAutomationMetadata,
    SandboxAutomationMetadataModel,
)

logger = logging.getLogger(__name__)


class SandboxAutomationMetadataStore:
    """Store for sandbox automation metadata."""

    @staticmethod
    async def set_metadata(
        sandbox_id: str,
        automation_id: str | None = None,
        automation_name: str | None = None,
        trigger_type: str | None = None,
        run_id: str | None = None,
        extra_metadata: dict[str, Any] | None = None,
    ) -> SandboxAutomationMetadata:
        """Set automation metadata for a sandbox.

        This will create or update the metadata for the given sandbox_id.

        Args:
            sandbox_id: The sandbox ID to associate metadata with
            automation_id: The automation definition ID
            automation_name: Human-readable name of the automation
            trigger_type: Type of trigger (e.g., 'cron', 'webhook')
            run_id: The specific automation run ID
            extra_metadata: Additional metadata as key-value pairs

        Returns:
            The created/updated SandboxAutomationMetadata
        """
        async with get_session() as session:
            # Check if metadata already exists for this sandbox
            result = await session.execute(
                select(SandboxAutomationMetadataModel).where(
                    SandboxAutomationMetadataModel.sandbox_id == sandbox_id
                )
            )
            existing = result.scalars().first()

            if existing:
                # Update existing record
                if automation_id is not None:
                    existing.automation_id = automation_id
                if automation_name is not None:
                    existing.automation_name = automation_name
                if trigger_type is not None:
                    existing.trigger_type = trigger_type
                if run_id is not None:
                    existing.run_id = run_id
                if extra_metadata is not None:
                    existing.extra_metadata = extra_metadata
                await session.commit()
                await session.refresh(existing)
                return SandboxAutomationMetadata.from_orm(existing)
            else:
                # Create new record
                model = SandboxAutomationMetadataModel(
                    sandbox_id=sandbox_id,
                    automation_id=automation_id,
                    automation_name=automation_name,
                    trigger_type=trigger_type,
                    run_id=run_id,
                    extra_metadata=extra_metadata or {},
                )
                session.add(model)
                await session.commit()
                await session.refresh(model)
                logger.info(
                    'Created sandbox automation metadata',
                    extra={
                        'sandbox_id': sandbox_id,
                        'automation_id': automation_id,
                        'trigger_type': trigger_type,
                    },
                )
                return SandboxAutomationMetadata.from_orm(model)

    @staticmethod
    async def get_metadata(sandbox_id: str) -> SandboxAutomationMetadata | None:
        """Get automation metadata for a sandbox.

        Args:
            sandbox_id: The sandbox ID to look up

        Returns:
            The SandboxAutomationMetadata if found, None otherwise
        """
        async with get_session() as session:
            result = await session.execute(
                select(SandboxAutomationMetadataModel).where(
                    SandboxAutomationMetadataModel.sandbox_id == sandbox_id
                )
            )
            model = result.scalars().first()
            if model:
                return SandboxAutomationMetadata.from_orm(model)
            return None

    @staticmethod
    async def delete_metadata(sandbox_id: str) -> bool:
        """Delete automation metadata for a sandbox.

        Args:
            sandbox_id: The sandbox ID to delete metadata for

        Returns:
            True if metadata was deleted, False if it didn't exist
        """
        async with get_session() as session:
            result = await session.execute(
                delete(SandboxAutomationMetadataModel).where(
                    SandboxAutomationMetadataModel.sandbox_id == sandbox_id
                )
            )
            await session.commit()
            deleted = result.rowcount > 0
            if deleted:
                logger.info(
                    'Deleted sandbox automation metadata',
                    extra={'sandbox_id': sandbox_id},
                )
            return deleted
