"""SQL implementation of AppConversationService.

This implementation provides CRUD operations for sandboxed conversations focused purely
on SQL operations:
- Direct database access without permission checks
- Batch operations for efficient data retrieval
- Integration with SandboxService for sandbox information
- HTTP client integration for agent status retrieval
- Full async/await support using SQL async db_sessions

Security and permission checks are handled by wrapper services.

Key components:
- SQLAppConversationService: Main service class implementing all operations
- SQLAppConversationInfoServiceInjector: Dependency injection resolver for FastAPI
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, AsyncGenerator
from uuid import UUID

if TYPE_CHECKING:
    from openhands.app_server.user.user_context import UserContext

from fastapi import Request
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    Select,
    String,
    delete,
    func,
    select,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession

from openhands.agent_server.utils import utc_now
from openhands.app_server.app_conversation.app_conversation_info_service import (
    AppConversationInfoService,
    AppConversationInfoServiceInjector,
)
from openhands.app_server.app_conversation.app_conversation_models import (
    AppConversationInfo,
    AppConversationInfoPage,
    AppConversationSortOrder,
)
from openhands.app_server.services.injector import InjectorState
from openhands.app_server.utils.sql_utils import (
    Base,
    create_json_type_decorator,
)
from openhands.integrations.provider import ProviderType
from openhands.sdk.llm import MetricsSnapshot
from openhands.sdk.llm.utils.metrics import TokenUsage
from openhands.storage.data_models.conversation_metadata import ConversationTrigger

logger = logging.getLogger(__name__)
APP_CONVERSATION_RESERVATION_VERSION = 'V1_RESERVATION'
APP_CONVERSATION_RESERVATION_TTL = timedelta(hours=1)
APP_CONVERSATION_RESERVATION_TOKEN_KEY = '_reservation_token'


class StoredConversationMetadata(Base):  # type: ignore
    __tablename__ = 'conversation_metadata'
    conversation_id = Column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    selected_repository = Column(String, nullable=True)
    selected_branch = Column(String, nullable=True)
    git_provider = Column(
        String, nullable=True
    )  # The git provider (GitHub, GitLab, etc.)
    title = Column(String, nullable=True)
    last_updated_at = Column(DateTime(timezone=True), default=utc_now)  # type: ignore[attr-defined]
    created_at = Column(DateTime(timezone=True), default=utc_now)  # type: ignore[attr-defined]

    trigger = Column(String, nullable=True)
    pr_number: Column[list[int]] = Column(create_json_type_decorator(list[int]))

    # Cost and token metrics
    accumulated_cost = Column(Float, default=0.0)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    max_budget_per_task = Column(Float, nullable=True)
    cache_read_tokens = Column(Integer, default=0)
    cache_write_tokens = Column(Integer, default=0)
    reasoning_tokens = Column(Integer, default=0)
    context_window = Column(Integer, default=0)
    per_turn_token = Column(Integer, default=0)

    # LLM model used for the conversation
    llm_model = Column(String, nullable=True)

    conversation_version = Column(String, nullable=False, default='V0', index=True)
    sandbox_id = Column(String, nullable=True, index=True)

    # Snapshot of the ACP agent spec, frozen at conversation creation so a later
    # edit to the user's global agent settings can't silently re-target an
    # in-flight conversation when its sandbox is recycled and rebuilt (#1015).
    # Secret-bearing fields are stripped before persisting (provider creds etc.
    # are re-resolved from the live encrypted vault on every build), so this
    # plain JSON column never holds secrets at rest (#1016). NULL for non-ACP
    # conversations and for ACP conversations created before this column landed.
    acp_agent_settings_snapshot: Mapped[ACPAgentSettings | None] = mapped_column(
        create_json_type_decorator(ACPAgentSettings | None), nullable=True
    )

    # Durable mirror of the ACP CLI session identity (harvested from the
    # agent_state webhook stream). Survives sandbox recycles so the rebuild
    # can feed ACPAgent.acp_resume_session_id for native session/load resume
    # (#14506 / #1126). NULL for non-ACP conversations.
    acp_session_id: Mapped[str | None] = mapped_column(String, nullable=True)
    acp_session_cwd: Mapped[str | None] = mapped_column(String, nullable=True)
    acp_agent_version: Mapped[str | None] = mapped_column(String, nullable=True)


@dataclass
class SQLAppConversationInfoService(AppConversationInfoService):
    """SQL implementation of AppConversationInfoService focused on db operations.

    This allows storing a record of a conversation even after its sandbox ceases to exist
    """

    db_session: AsyncSession
    user_context: UserContext
    _reservation_tokens: dict[UUID, str] = field(
        default_factory=dict, init=False, repr=False
    )

    async def search_app_conversation_info(
        self,
        title__contains: str | None = None,
        created_at__gte: datetime | None = None,
        created_at__lt: datetime | None = None,
        updated_at__gte: datetime | None = None,
        updated_at__lt: datetime | None = None,
        sort_order: AppConversationSortOrder = AppConversationSortOrder.CREATED_AT_DESC,
        page_id: str | None = None,
        limit: int = 100,
    ) -> AppConversationInfoPage:
        """Search for sandboxed conversations without permission checks."""
        query = await self._secure_select()

        query = self._apply_filters(
            query=query,
            title__contains=title__contains,
            created_at__gte=created_at__gte,
            created_at__lt=created_at__lt,
            updated_at__gte=updated_at__gte,
            updated_at__lt=updated_at__lt,
        )

        # Add sort order
        if sort_order == AppConversationSortOrder.CREATED_AT:
            query = query.order_by(StoredConversationMetadata.created_at)
        elif sort_order == AppConversationSortOrder.CREATED_AT_DESC:
            query = query.order_by(StoredConversationMetadata.created_at.desc())
        elif sort_order == AppConversationSortOrder.UPDATED_AT:
            query = query.order_by(StoredConversationMetadata.updated_at)
        elif sort_order == AppConversationSortOrder.UPDATED_AT_DESC:
            query = query.order_by(StoredConversationMetadata.updated_at.desc())
        elif sort_order == AppConversationSortOrder.TITLE:
            query = query.order_by(StoredConversationMetadata.title)
        elif sort_order == AppConversationSortOrder.TITLE_DESC:
            query = query.order_by(StoredConversationMetadata.title.desc())

        # Apply pagination
        if page_id is not None:
            try:
                offset = int(page_id)
                query = query.offset(offset)
            except ValueError:
                # If page_id is not a valid integer, start from beginning
                offset = 0
        else:
            offset = 0

        # Apply limit and get one extra to check if there are more results
        query = query.limit(limit + 1)

        result = await self.db_session.execute(query)
        rows = result.scalars().all()

        # Check if there are more results
        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]

        items = [self._to_info(row) for row in rows]

        # Calculate next page ID
        next_page_id = None
        if has_more:
            next_page_id = str(offset + limit)

        return AppConversationInfoPage(items=items, next_page_id=next_page_id)

    async def count_app_conversation_info(
        self,
        title__contains: str | None = None,
        created_at__gte: datetime | None = None,
        created_at__lt: datetime | None = None,
        updated_at__gte: datetime | None = None,
        updated_at__lt: datetime | None = None,
    ) -> int:
        """Count sandboxed conversations matching the given filters."""
        query = select(func.count(StoredConversationMetadata.conversation_id))
        user_id = await self.user_context.get_user_id()
        if user_id:
            query = query.where(
                StoredConversationMetadata.created_by_user_id == user_id
            )

        query = self._apply_filters(
            query=query,
            title__contains=title__contains,
            created_at__gte=created_at__gte,
            created_at__lt=created_at__lt,
            updated_at__gte=updated_at__gte,
            updated_at__lt=updated_at__lt,
        )

        result = await self.db_session.execute(query)
        count = result.scalar()
        return count or 0

    def _apply_filters(
        self,
        query: Select,
        title__contains: str | None = None,
        created_at__gte: datetime | None = None,
        created_at__lt: datetime | None = None,
        updated_at__gte: datetime | None = None,
        updated_at__lt: datetime | None = None,
    ) -> Select:
        # Apply the same filters as search_app_conversations
        conditions = []
        if title__contains is not None:
            conditions.append(
                StoredConversationMetadata.title.like(f'%{title__contains}%')
            )

        if created_at__gte is not None:
            conditions.append(StoredConversationMetadata.created_at >= created_at__gte)

        if created_at__lt is not None:
            conditions.append(StoredConversationMetadata.created_at < created_at__lt)

        if updated_at__gte is not None:
            conditions.append(
                StoredConversationMetadata.last_updated_at >= updated_at__gte
            )

        if updated_at__lt is not None:
            conditions.append(
                StoredConversationMetadata.last_updated_at < updated_at__lt
            )

        if conditions:
            query = query.where(*conditions)
        return query

    async def get_app_conversation_info(
        self, conversation_id: UUID
    ) -> AppConversationInfo | None:
        query = await self._secure_select()
        query = query.where(
            StoredConversationMetadata.conversation_id == str(conversation_id)
        )
        result_set = await self.db_session.execute(query)
        result = result_set.scalar_one_or_none()
        if result:
            return self._to_info(result)
        return None

    async def is_app_conversation_id_available(self, conversation_id: UUID) -> bool:
        query = select(StoredConversationMetadata.conversation_id).where(
            StoredConversationMetadata.conversation_id == str(conversation_id)
        )
        return await self.db_session.scalar(query) is None

    async def try_reserve_app_conversation_id(
        self,
        conversation_id: UUID,
        created_by_user_id: str | None = None,
    ) -> bool:
        token = uuid.uuid4().hex
        if await self._insert_app_conversation_id_reservation(conversation_id, token):
            self._reservation_tokens[conversation_id] = token
            return True
        cutoff = utc_now() - APP_CONVERSATION_RESERVATION_TTL
        now = utc_now()
        result = cast(
            CursorResult,
            await self.db_session.execute(
                update(StoredConversationMetadata)
                .where(
                    StoredConversationMetadata.conversation_id == str(conversation_id),
                    StoredConversationMetadata.conversation_version
                    == APP_CONVERSATION_RESERVATION_VERSION,
                    StoredConversationMetadata.last_updated_at < cutoff,
                )
                .values(
                    tags={APP_CONVERSATION_RESERVATION_TOKEN_KEY: token},
                    last_updated_at=now,
                    created_at=now,
                )
            ),
        )
        await self.db_session.commit()
        if not result.rowcount:
            return False
        self._reservation_tokens[conversation_id] = token
        return True

    async def _insert_app_conversation_id_reservation(
        self, conversation_id: UUID, token: str
    ) -> bool:
        self.db_session.add(
            StoredConversationMetadata(
                conversation_id=str(conversation_id),
                conversation_version=APP_CONVERSATION_RESERVATION_VERSION,
                tags={APP_CONVERSATION_RESERVATION_TOKEN_KEY: token},
            )
        )
        try:
            await self.db_session.flush()
            await self.db_session.commit()
        except IntegrityError:
            await self.db_session.rollback()
            return False
        return True

    async def release_app_conversation_id_reservation(
        self, conversation_id: UUID
    ) -> None:
        token = self._reservation_tokens.get(conversation_id)
        await self.db_session.rollback()
        if token is None:
            return
        existing = (
            await self.db_session.execute(
                select(
                    StoredConversationMetadata.conversation_version,
                    StoredConversationMetadata.tags,
                )
                .where(
                    StoredConversationMetadata.conversation_id == str(conversation_id)
                )
                .with_for_update(of=StoredConversationMetadata)
            )
        ).first()
        if (
            existing is None
            or existing.conversation_version != APP_CONVERSATION_RESERVATION_VERSION
            or (existing.tags or {}).get(APP_CONVERSATION_RESERVATION_TOKEN_KEY)
            != token
        ):
            self._reservation_tokens.pop(conversation_id, None)
            await self.db_session.rollback()
            return
        reservation = await self.db_session.get(
            StoredConversationMetadata, str(conversation_id)
        )
        assert reservation is not None
        await self.db_session.delete(reservation)
        await self.db_session.commit()
        self._reservation_tokens.pop(conversation_id, None)

    async def renew_app_conversation_id_reservation(
        self, conversation_id: UUID
    ) -> bool:
        token = self._reservation_tokens.get(conversation_id)
        bind = self.db_session.bind
        if token is None or bind is None:
            return False
        session_maker = async_sessionmaker(bind=bind, expire_on_commit=False)
        async with session_maker() as session:
            existing = (
                await session.execute(
                    select(
                        StoredConversationMetadata.conversation_version,
                        StoredConversationMetadata.tags,
                    )
                    .where(
                        StoredConversationMetadata.conversation_id
                        == str(conversation_id)
                    )
                    .with_for_update(of=StoredConversationMetadata)
                )
            ).first()
            if (
                existing is None
                or existing.conversation_version != APP_CONVERSATION_RESERVATION_VERSION
                or (existing.tags or {}).get(APP_CONVERSATION_RESERVATION_TOKEN_KEY)
                != token
            ):
                await session.rollback()
                return False
            now = utc_now()
            await session.execute(
                update(StoredConversationMetadata)
                .where(
                    StoredConversationMetadata.conversation_id == str(conversation_id)
                )
                .values(last_updated_at=now)
            )
            await session.commit()
            return True

    async def mark_app_conversation_id_reservation(
        self,
        conversation_id: UUID,
        sandbox_id: str,
        tags: dict[str, str] | None = None,
    ) -> bool:
        token = self._reservation_tokens.get(conversation_id)
        if token is None:
            return False
        existing = (
            await self.db_session.execute(
                select(
                    StoredConversationMetadata.conversation_version,
                    StoredConversationMetadata.tags,
                )
                .where(
                    StoredConversationMetadata.conversation_id == str(conversation_id)
                )
                .with_for_update(of=StoredConversationMetadata)
            )
        ).first()
        if (
            existing is None
            or existing.conversation_version != APP_CONVERSATION_RESERVATION_VERSION
            or (existing.tags or {}).get(APP_CONVERSATION_RESERVATION_TOKEN_KEY)
            != token
        ):
            await self.db_session.rollback()
            return False
        merged_tags = {**(existing.tags or {}), **(tags or {})}
        merged_tags[APP_CONVERSATION_RESERVATION_TOKEN_KEY] = token
        await self.db_session.execute(
            update(StoredConversationMetadata)
            .where(StoredConversationMetadata.conversation_id == str(conversation_id))
            .values(
                sandbox_id=sandbox_id,
                tags=merged_tags,
                last_updated_at=utc_now(),
            )
        )
        await self.db_session.commit()
        return True

    async def has_managed_credential_conversation_for_sandbox(
        self, sandbox_id: str
    ) -> bool:
        rows = (
            await self.db_session.execute(
                select(StoredConversationMetadata.tags).where(
                    StoredConversationMetadata.sandbox_id == sandbox_id,
                    StoredConversationMetadata.conversation_version.in_(
                        ('V1', APP_CONVERSATION_RESERVATION_VERSION)
                    ),
                )
            )
        ).scalars()
        return any(has_managed_codex_credential(tags or {}) for tags in rows)

    async def batch_get_app_conversation_info(
        self, conversation_ids: list[UUID]
    ) -> list[AppConversationInfo | None]:
        conversation_id_strs = [
            str(conversation_id) for conversation_id in conversation_ids
        ]
        query = await self._secure_select()
        query = query.where(
            StoredConversationMetadata.conversation_id.in_(conversation_id_strs)
        )
        result = await self.db_session.execute(query)
        rows = result.scalars().all()
        info_by_id = {info.conversation_id: info for info in rows if info}
        results: list[AppConversationInfo | None] = []
        for conversation_id in conversation_id_strs:
            info = info_by_id.get(conversation_id)
            if info:
                results.append(self._to_info(info))
            else:
                results.append(None)

        return results

    async def _merge_app_conversation_info(
        self,
        info: AppConversationInfo,
        allow_reservation_handoff: bool = False,
    ) -> None:
        metrics = info.metrics or MetricsSnapshot()
        usage = metrics.accumulated_token_usage or TokenUsage()

        stored = StoredConversationMetadata(
            conversation_id=str(info.id),
            selected_repository=info.selected_repository,
            selected_branch=info.selected_branch,
            git_provider=info.git_provider.value if info.git_provider else None,
            title=info.title,
            last_updated_at=info.updated_at,
            created_at=info.created_at,
            trigger=info.trigger.value if info.trigger else None,
            pr_number=info.pr_number or [],
            # Cost and token metrics
            accumulated_cost=metrics.accumulated_cost,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=0,
            max_budget_per_task=metrics.max_budget_per_task,
            cache_read_tokens=usage.cache_read_tokens,
            cache_write_tokens=usage.cache_write_tokens,
            context_window=usage.context_window,
            per_turn_token=usage.per_turn_token,
            llm_model=info.llm_model,
            agent_kind=info.agent_kind,
            conversation_version='V1',
            sandbox_id=info.sandbox_id,
        )

        await self.db_session.commit()
        return info

    async def _secure_select(self):
        query = select(StoredConversationMetadata).where(
            StoredConversationMetadata.conversation_version == 'V1'
        )
        return query

    def _to_info(self, stored: StoredConversationMetadata) -> AppConversationInfo:
        # V1 conversations should always have a sandbox_id
        sandbox_id = stored.sandbox_id
        assert sandbox_id is not None

        # Rebuild token usage
        token_usage = TokenUsage(
            prompt_tokens=stored.prompt_tokens,
            completion_tokens=stored.completion_tokens,
            cache_read_tokens=stored.cache_read_tokens,
            cache_write_tokens=stored.cache_write_tokens,
            context_window=stored.context_window,
            per_turn_token=stored.per_turn_token,
        )

        # Rebuild metrics object
        metrics = MetricsSnapshot(
            accumulated_cost=stored.accumulated_cost,
            max_budget_per_task=stored.max_budget_per_task,
            accumulated_token_usage=token_usage,
        )

        # Get timestamps
        created_at = self._fix_timezone(stored.created_at)
        updated_at = self._fix_timezone(stored.last_updated_at)

        return AppConversationInfo(
            id=UUID(stored.conversation_id),
            created_by_user_id=None,  # User ID is now stored in ConversationMetadataSaas
            sandbox_id=stored.sandbox_id,
            selected_repository=stored.selected_repository,
            selected_branch=stored.selected_branch,
            git_provider=ProviderType(stored.git_provider)
            if stored.git_provider
            else None,
            title=stored.title,
            trigger=ConversationTrigger(stored.trigger) if stored.trigger else None,
            pr_number=stored.pr_number,
            llm_model=stored.llm_model,
            agent_kind=stored.agent_kind or 'llm',
            metrics=metrics,
            created_at=created_at,
            updated_at=updated_at,
        )

    def _fix_timezone(self, value: datetime) -> datetime:
        """Sqlite does not stpre timezones - and since we can't update the existing models
        we assume UTC if the timezone is missing."""
        if not value.tzinfo:
            value = value.replace(tzinfo=UTC)
        return value


class SQLAppConversationInfoServiceInjector(AppConversationInfoServiceInjector):
    async def inject(
        self, state: InjectorState, request: Request | None = None
    ) -> AsyncGenerator[AppConversationInfoService, None]:
        # Define inline to prevent circular lookup
        from openhands.app_server.config import (
            get_db_session,
            get_user_context,
        )

        async with (
            get_user_context(state, request) as user_context,
            get_db_session(state, request) as db_session,
        ):
            service = SQLAppConversationInfoService(
                db_session=db_session, user_context=user_context
            )
            yield service
