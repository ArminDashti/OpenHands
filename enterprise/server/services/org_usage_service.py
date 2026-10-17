"""Service for organization usage dashboard metrics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from typing import AsyncGenerator
from uuid import UUID

from fastapi import Request
from server.routes.org_models import (
    OrgAuthorizationError,
    OrgNotFoundError,
    OrgUsageDashboardResponse,
    UsageDashboardDailyConversationCount,
    UsageDashboardRepositoryCount,
    UsageDashboardSummary,
)
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from storage.org import Org
from storage.org_member import OrgMember
from storage.role import Role
from storage.stored_conversation_metadata import StoredConversationMetadata
from storage.stored_conversation_metadata_saas import StoredConversationMetadataSaas

from openhands.app_server.errors import AuthError
from openhands.app_server.services.injector import Injector, InjectorState
from openhands.app_server.user.user_context import UserContext
from openhands.core.logger import openhands_logger as logger

USAGE_WINDOW_DAYS = 30
NO_REPOSITORY_LABEL = 'No repository'
TEAM_USAGE_ALLOWED_ROLES = {'admin', 'owner'}


@dataclass
class OrgUsageService:
    """Service that aggregates org-scoped usage metrics."""

    db_session: AsyncSession
    user_context: UserContext

    async def get_org_usage(self, org_id: UUID) -> OrgUsageDashboardResponse:
        user_id = await self.user_context.get_user_id()
        if not user_id:
            raise AuthError('User not authenticated')

        logger.info(
            'Getting organization usage dashboard',
            extra={'user_id': user_id, 'org_id': str(org_id)},
        )

        org = await self._get_org(org_id)
        if not org:
            raise OrgNotFoundError(str(org_id))

        role_name = await self._get_user_role_name(org_id=org_id, user_id=UUID(user_id))
        if role_name is None:
            raise OrgAuthorizationError('User is not a member of this organization')

        if not self._can_access_usage_dashboard(
            org=org, role_name=role_name, user_id=user_id
        ):
            raise OrgAuthorizationError(
                'Only organization admins and owners can view usage for team workspaces'
            )

        total_conversations = await self._get_total_conversation_count(org_id)
        window_start = self._get_window_start()
        recent_rows = await self._get_recent_conversations(org_id, window_start)
        top_repositories = await self._get_top_repositories(org_id)

        summary = UsageDashboardSummary(
            average_cost_per_conversation_last_30_days=self._calculate_average_cost(
                recent_rows
            ),
            total_conversations=total_conversations,
        )

        return OrgUsageDashboardResponse(
            summary=summary,
            daily_conversations=self._build_daily_conversation_counts(recent_rows),
            top_repositories=top_repositories,
        )

    async def _get_org(self, org_id: UUID) -> Org | None:
        result = await self.db_session.execute(select(Org).where(Org.id == org_id))
        return result.scalar_one_or_none()

    async def _get_user_role_name(self, org_id: UUID, user_id: UUID) -> str | None:
        result = await self.db_session.execute(
            select(Role.name)
            .join(OrgMember, OrgMember.role_id == Role.id)
            .where(OrgMember.org_id == org_id, OrgMember.user_id == user_id)
        )
        return result.scalar_one_or_none()

    def _can_access_usage_dashboard(
        self, org: Org, role_name: str, user_id: str
    ) -> bool:
        is_personal_workspace = str(org.id) == user_id
        return is_personal_workspace or role_name in TEAM_USAGE_ALLOWED_ROLES

    async def _get_total_conversation_count(self, org_id: UUID) -> int:
        query = (
            select(func.count(StoredConversationMetadata.conversation_id))
            .select_from(StoredConversationMetadata)
            .join(
                StoredConversationMetadataSaas,
                StoredConversationMetadata.conversation_id
                == StoredConversationMetadataSaas.conversation_id,
            )
            .where(
                StoredConversationMetadataSaas.org_id == org_id,
                StoredConversationMetadata.conversation_version == 'V1',
            )
        )
        result = await self.db_session.execute(query)
        count = result.scalar_one_or_none()
        return count or 0

    async def _get_recent_conversations(
        self, org_id: UUID, window_start: datetime
    ) -> list[tuple[datetime, float]]:
        query = (
            select(
                StoredConversationMetadata.created_at,
                StoredConversationMetadata.accumulated_cost,
            )
            .join(
                StoredConversationMetadataSaas,
                StoredConversationMetadata.conversation_id
                == StoredConversationMetadataSaas.conversation_id,
            )
            .where(
                StoredConversationMetadataSaas.org_id == org_id,
                StoredConversationMetadata.conversation_version == 'V1',
                StoredConversationMetadata.created_at >= window_start,
            )
        )
        result = await self.db_session.execute(query)
        return [
            (self._ensure_utc(created_at), accumulated_cost or 0.0)
            for created_at, accumulated_cost in result.all()
        ]

    async def _get_top_repositories(
        self, org_id: UUID
    ) -> list[UsageDashboardRepositoryCount]:
        normalized_repository = case(
            (
                func.trim(
                    func.coalesce(StoredConversationMetadata.selected_repository, '')
                )
                == '',
                NO_REPOSITORY_LABEL,
            ),
            else_=StoredConversationMetadata.selected_repository,
        ).label('repository')

        query = (
            select(
                normalized_repository,
                func.count(StoredConversationMetadata.conversation_id).label(
                    'conversation_count'
                ),
            )
            .join(
                StoredConversationMetadataSaas,
                StoredConversationMetadata.conversation_id
                == StoredConversationMetadataSaas.conversation_id,
            )
            .where(
                StoredConversationMetadataSaas.org_id == org_id,
                StoredConversationMetadata.conversation_version == 'V1',
            )
            .group_by(normalized_repository)
            .order_by(
                func.count(StoredConversationMetadata.conversation_id).desc(),
                normalized_repository.asc(),
            )
            .limit(5)
        )
        result = await self.db_session.execute(query)
        return [
            UsageDashboardRepositoryCount(
                repository=repository,
                conversation_count=conversation_count,
            )
            for repository, conversation_count in result.all()
        ]

    def _calculate_average_cost(
        self, recent_rows: list[tuple[datetime, float]]
    ) -> float:
        if not recent_rows:
            return 0.0
        total_cost = sum(cost for _, cost in recent_rows)
        return total_cost / len(recent_rows)

    def _build_daily_conversation_counts(
        self, recent_rows: list[tuple[datetime, float]]
    ) -> list[UsageDashboardDailyConversationCount]:
        start_date = self._get_window_start().date()
        today = datetime.now(UTC).date()
        counts_by_day = {
            start_date + timedelta(days=offset): 0
            for offset in range((today - start_date).days + 1)
        }

        for created_at, _ in recent_rows:
            conversation_date = created_at.astimezone(UTC).date()
            if conversation_date in counts_by_day:
                counts_by_day[conversation_date] += 1

        return [
            UsageDashboardDailyConversationCount(
                date=bucket_date.isoformat(),
                conversation_count=counts_by_day[bucket_date],
            )
            for bucket_date in sorted(counts_by_day)
        ]

    def _get_window_start(self) -> datetime:
        today = datetime.now(UTC).date()
        start_date = today - timedelta(days=USAGE_WINDOW_DAYS - 1)
        return datetime.combine(start_date, time.min, tzinfo=UTC)

    def _ensure_utc(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class OrgUsageServiceInjector(Injector[OrgUsageService]):
    """Injector for the organization usage service."""

    async def inject(
        self, state: InjectorState, request: Request | None = None
    ) -> AsyncGenerator[OrgUsageService, None]:
        from openhands.app_server.config import get_db_session, get_user_context

        async with (
            get_user_context(state, request) as user_context,
            get_db_session(state, request) as db_session,
        ):
            yield OrgUsageService(db_session=db_session, user_context=user_context)
