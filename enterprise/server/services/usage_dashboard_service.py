"""Service for fetching usage dashboard statistics."""

from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

from server.routes.usage_dashboard_models import (
    ConversationActivityDay,
    LLMModelUsage,
    UsageDashboardData,
    UserUsageStats,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from storage.stored_conversation_metadata_saas import StoredConversationMetadataSaas
from storage.user import User

from openhands.app_server.app_conversation.sql_app_conversation_info_service import (
    StoredConversationMetadata,
)
from openhands.core.logger import openhands_logger as logger


class UsageDashboardService:
    """Service for computing usage dashboard statistics for an organization."""

    def __init__(self, db_session: AsyncSession):
        """Initialize the usage dashboard service.

        Args:
            db_session: Async database session
        """
        self.db_session = db_session

    async def get_dashboard_data(self, org_id: UUID) -> UsageDashboardData:
        """Fetch all usage dashboard data for an organization.

        Args:
            org_id: Organization ID

        Returns:
            UsageDashboardData containing all dashboard metrics
        """
        logger.info(f'Fetching usage dashboard data for org_id={org_id}')

        # Get all conversation IDs for this organization
        conversation_ids_query = select(
            StoredConversationMetadataSaas.conversation_id
        ).where(StoredConversationMetadataSaas.org_id == org_id)

        result = await self.db_session.execute(conversation_ids_query)
        conversation_ids = [row[0] for row in result.fetchall()]

        if not conversation_ids:
            # No conversations found for this org
            return UsageDashboardData(
                total_conversations=0,
                average_cost_per_conversation=0.0,
                top_llm_models=[],
                conversation_activity_30_days=[],
                top_users=[],
            )

        # Fetch aggregated data
        total_conversations = await self._get_total_conversations(conversation_ids)
        average_cost = await self._get_average_cost(conversation_ids)
        top_llm_models = await self._get_top_llm_models(conversation_ids)
        activity_30_days = await self._get_30_day_activity(conversation_ids)
        top_users = await self._get_top_users(org_id)

        return UsageDashboardData(
            total_conversations=total_conversations,
            average_cost_per_conversation=average_cost,
            top_llm_models=top_llm_models,
            conversation_activity_30_days=activity_30_days,
            top_users=top_users,
        )

    async def _get_total_conversations(self, conversation_ids: list[str]) -> int:
        """Get total count of conversations.

        Args:
            conversation_ids: List of conversation IDs for the organization

        Returns:
            Total number of conversations
        """
        query = (
            select(func.count(StoredConversationMetadata.conversation_id))
            .where(StoredConversationMetadata.conversation_id.in_(conversation_ids))
            .where(StoredConversationMetadata.conversation_version == 'V1')
        )

        result = await self.db_session.execute(query)
        count = result.scalar()
        return count or 0

    async def _get_average_cost(self, conversation_ids: list[str]) -> float:
        """Calculate average cost per conversation.

        Args:
            conversation_ids: List of conversation IDs for the organization

        Returns:
            Average cost per conversation (0.0 if no conversations with cost)
        """
        query = (
            select(func.avg(StoredConversationMetadata.accumulated_cost))
            .where(StoredConversationMetadata.conversation_id.in_(conversation_ids))
            .where(StoredConversationMetadata.conversation_version == 'V1')
            .where(StoredConversationMetadata.accumulated_cost.is_not(None))
        )

        result = await self.db_session.execute(query)
        avg_cost = result.scalar()
        return float(avg_cost) if avg_cost is not None else 0.0

    async def _get_top_llm_models(
        self, conversation_ids: list[str]
    ) -> list[LLMModelUsage]:
        """Get top 5 most popular LLM models.

        Args:
            conversation_ids: List of conversation IDs for the organization

        Returns:
            List of top 5 LLM models with their usage count
        """
        query = (
            select(
                StoredConversationMetadata.llm_model,
                func.count(StoredConversationMetadata.conversation_id).label('count'),
            )
            .where(StoredConversationMetadata.conversation_id.in_(conversation_ids))
            .where(StoredConversationMetadata.conversation_version == 'V1')
            .where(StoredConversationMetadata.llm_model.is_not(None))
            .group_by(StoredConversationMetadata.llm_model)
            .order_by(func.count(StoredConversationMetadata.conversation_id).desc())
            .limit(5)
        )

        result = await self.db_session.execute(query)
        rows = result.fetchall()

        return [
            LLMModelUsage(model_name=row[0], count=row[1])
            for row in rows
            if row[0] is not None
        ]

    async def _get_30_day_activity(
        self, conversation_ids: list[str]
    ) -> list[ConversationActivityDay]:
        """Get conversation activity for the last 30 days.

        Args:
            conversation_ids: List of conversation IDs for the organization

        Returns:
            List of daily conversation counts for the last 30 days
        """
        # Calculate date 30 days ago
        end_date = datetime.now(UTC).date()
        start_date = end_date - timedelta(days=29)  # 30 days including today

        # Query to group by date
        query = (
            select(
                func.date(StoredConversationMetadata.created_at).label('date'),
                func.count(StoredConversationMetadata.conversation_id).label('count'),
            )
            .where(StoredConversationMetadata.conversation_id.in_(conversation_ids))
            .where(StoredConversationMetadata.conversation_version == 'V1')
            .where(func.date(StoredConversationMetadata.created_at) >= start_date)
            .where(func.date(StoredConversationMetadata.created_at) <= end_date)
            .group_by(func.date(StoredConversationMetadata.created_at))
            .order_by(func.date(StoredConversationMetadata.created_at))
        )

        result = await self.db_session.execute(query)
        rows = result.fetchall()

        # Create a dict for quick lookup
        activity_dict = {cast(datetime, row[0]).date(): row[1] for row in rows}

        # Fill in all days in the range (including days with 0 conversations)
        activity_list = []
        current_date = start_date
        while current_date <= end_date:
            count = activity_dict.get(current_date, 0)
            activity_list.append(ConversationActivityDay(date=current_date, count=count))
            current_date += timedelta(days=1)

        return activity_list

    async def _get_top_users(self, org_id: UUID) -> list[UserUsageStats]:
        """Get top users by conversation count.

        Args:
            org_id: Organization ID

        Returns:
            List of top users with their conversation counts
        """
        query = (
            select(
                StoredConversationMetadataSaas.user_id,
                User.email,
                func.count(StoredConversationMetadataSaas.conversation_id).label(
                    'conversation_count'
                ),
            )
            .join(User, StoredConversationMetadataSaas.user_id == User.id)
            .where(StoredConversationMetadataSaas.org_id == org_id)
            .group_by(StoredConversationMetadataSaas.user_id, User.email)
            .order_by(
                func.count(StoredConversationMetadataSaas.conversation_id).desc()
            )
            .limit(10)
        )

        result = await self.db_session.execute(query)
        rows = result.fetchall()

        return [
            UserUsageStats(
                user_id=str(row[0]), user_email=row[1], conversation_count=row[2]
            )
            for row in rows
        ]


__all__ = ['UsageDashboardService']
