"""Tests for SQLAppConversationInfoService.

This module tests the SQL implementation of AppConversationInfoService,
focusing on basic CRUD operations, search functionality, filtering, pagination,
and batch operations using SQLite as a mock database.
"""

from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from openhands.app_server.app_conversation.app_conversation_models import (
    CODEX_CREDENTIAL_BINDING_TAG_KEY,
    CODEX_CREDENTIAL_BINDING_TAG_VALUE,
    AppConversationInfo,
    AppConversationSortOrder,
)
from openhands.app_server.app_conversation.sql_app_conversation_info_service import (
    APP_CONVERSATION_RESERVATION_TOKEN_KEY,
    APP_CONVERSATION_RESERVATION_VERSION,
    SQLAppConversationInfoService,
    StoredConversationMetadata,
)
from openhands.app_server.user.admin_user_context import AdminUserContext
from openhands.app_server.utils.sql_utils import Base
from openhands.integrations.service_types import ProviderType
from openhands.sdk.llm import MetricsSnapshot
from openhands.sdk.llm.utils.metrics import TokenUsage
from openhands.storage.data_models.conversation_metadata import ConversationTrigger

# Note: org_id column exists but foreign key constraint is not enforced in tests

# Note: MetricsSnapshot from SDK is not available in test environment
# We'll use None for metrics field in tests since it's optional


@pytest.fixture
async def async_engine():
    """Create an async SQLite engine for testing."""
    engine = create_async_engine(
        'sqlite+aiosqlite:///:memory:',
        poolclass=StaticPool,
        connect_args={'check_same_thread': False},
        echo=False,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create an async session for testing."""
    async_session_maker = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as db_session:
        yield db_session


@pytest.fixture
def service(async_session) -> SQLAppConversationInfoService:
    """Create a SQLAppConversationInfoService instance for testing."""
    return SQLAppConversationInfoService(
        db_session=async_session, user_context=AdminUserContext(user_id=None)
    )


@pytest.fixture
def service_with_user(async_session) -> SQLAppConversationInfoService:
    """Create a SQLAppConversationInfoService instance with a user_id for testing."""
    return SQLAppConversationInfoService(
        db_session=async_session, user_id='test_user_123'
    )


@pytest.fixture
def sample_conversation_info() -> AppConversationInfo:
    """Create a sample AppConversationInfo for testing."""
    return AppConversationInfo(
        id=uuid4(),
        created_by_user_id='test_user_123',
        sandbox_id='sandbox_123',
        selected_repository='https://github.com/test/repo',
        selected_branch='main',
        git_provider=ProviderType.GITHUB,
        title='Test Conversation',
        trigger=ConversationTrigger.GUI,
        pr_number=[123, 456],
        llm_model='gpt-4',
        metrics=None,
        created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2024, 1, 1, 12, 30, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def multiple_conversation_infos() -> list[AppConversationInfo]:
    """Create multiple AppConversationInfo instances for testing."""
    base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    return [
        AppConversationInfo(
            id=uuid4(),
            created_by_user_id=None,
            sandbox_id=f'sandbox_{i}',
            selected_repository=f'https://github.com/test/repo{i}',
            selected_branch='main',
            git_provider=ProviderType.GITHUB,
            title=f'Test Conversation {i}',
            trigger=ConversationTrigger.GUI,
            pr_number=[i * 100],
            llm_model='gpt-4',
            metrics=None,
            created_at=base_time.replace(hour=12 + i),
            updated_at=base_time.replace(hour=12 + i, minute=30),
        )
        for i in range(1, 6)  # Create 5 conversations
    ]


class TestSQLAppConversationInfoService:
    """Test suite for SQLAppConversationInfoService."""

    @pytest.mark.asyncio
    async def test_save_and_get_conversation_info(
        self,
        service: SQLAppConversationInfoService,
        sample_conversation_info: AppConversationInfo,
    ):
        """Test basic save and get operations."""
        # Save the conversation info
        saved_info = await service.save_app_conversation_info(sample_conversation_info)

        # Verify the saved info matches the original
        assert saved_info.id == sample_conversation_info.id
        assert (
            saved_info.created_by_user_id == sample_conversation_info.created_by_user_id
        )
        assert saved_info.title == sample_conversation_info.title

        # Retrieve the conversation info
        retrieved_info = await service.get_app_conversation_info(
            sample_conversation_info.id
        )

        # Verify the retrieved info matches the original
        assert retrieved_info is not None
        assert retrieved_info.id == sample_conversation_info.id
        assert retrieved_info.sandbox_id == sample_conversation_info.sandbox_id
        assert (
            retrieved_info.selected_repository
            == sample_conversation_info.selected_repository
        )
        assert (
            retrieved_info.selected_branch == sample_conversation_info.selected_branch
        )
        assert retrieved_info.git_provider == sample_conversation_info.git_provider
        assert retrieved_info.title == sample_conversation_info.title
        assert retrieved_info.trigger == sample_conversation_info.trigger
        assert retrieved_info.pr_number == sample_conversation_info.pr_number
        assert retrieved_info.llm_model == sample_conversation_info.llm_model
        assert (
            retrieved_info.acp_session_id
            == sample_conversation_info.acp_session_id
        )
        assert (
            retrieved_info.acp_session_cwd
            == sample_conversation_info.acp_session_cwd
        )

    @pytest.mark.asyncio
    async def test_concurrent_saves_recover_from_duplicate_key_race(
        self,
        sample_conversation_info: AppConversationInfo,
    ):
        """Two concurrent writers can both miss a row before one insert wins."""

        class ScalarResult:
            def __init__(self, row):
                self.row = row

            def scalar_one_or_none(self):
                return self.row

        class RaceyConversationMetadataTable:
            def __init__(self, conversation_id: str):
                self.conversation_id = conversation_id
                self.rows = {}
                self.merge_count = 0
                self.all_writers_ready = asyncio.Event()
                self.unique_index_lock = asyncio.Lock()
                self.duplicate_errors = 0
                self.recovery_selects = 0

            async def wait_until_both_writers_have_selected_no_row(self):
                self.merge_count += 1
                if self.merge_count == 2:
                    self.all_writers_ready.set()
                await self.all_writers_ready.wait()

        def make_db_session_mock(insert_delay: float) -> Mock:
            session = Mock(spec=AsyncSession)
            pending_insert = None

            async def merge(stored):
                nonlocal pending_insert
                pending_insert = stored
                await table.wait_until_both_writers_have_selected_no_row()

            async def commit():
                nonlocal pending_insert
                if pending_insert is None:
                    return

                stored = pending_insert
                pending_insert = None
                await asyncio.sleep(insert_delay)

                async with table.unique_index_lock:
                    if stored.conversation_id in table.rows:
                        table.duplicate_errors += 1
                        raise IntegrityError(
                            'INSERT INTO conversation_metadata',
                            {},
                            Exception(
                                'duplicate key value violates unique constraint '
                                '"conversation_metadata_pkey"'
                            ),
                        )
                    table.rows[stored.conversation_id] = stored

            async def rollback():
                nonlocal pending_insert
                pending_insert = None

            async def execute(_query):
                table.recovery_selects += 1
                await asyncio.sleep(0)
                return ScalarResult(table.rows.get(table.conversation_id))

            session.merge = AsyncMock(side_effect=merge)
            session.commit = AsyncMock(side_effect=commit)
            session.rollback = AsyncMock(side_effect=rollback)
            session.execute = AsyncMock(side_effect=execute)
            return session

        conversation_id = str(sample_conversation_info.id)
        table = RaceyConversationMetadataTable(conversation_id)
        webhook_session = make_db_session_mock(insert_delay=0.01)
        live_status_session = make_db_session_mock(insert_delay=0.05)
        webhook_service = SQLAppConversationInfoService(
            db_session=cast(AsyncSession, webhook_session),
            user_context=SpecifyUserContext(user_id='test_user'),
        )
        live_status_service = SQLAppConversationInfoService(
            db_session=cast(AsyncSession, live_status_session),
            user_context=SpecifyUserContext(user_id='test_user'),
        )

        webhook_info = sample_conversation_info.model_copy(
            deep=True, update={'title': 'metadata from webhook'}
        )
        live_status_info = sample_conversation_info.model_copy(
            deep=True, update={'title': 'metadata from live status'}
        )

        await asyncio.gather(
            webhook_service.save_app_conversation_info(webhook_info),
            live_status_service.save_app_conversation_info(live_status_info),
        )

        assert table.merge_count == 2
        assert table.duplicate_errors == 1
        assert table.recovery_selects == 1
        webhook_session.rollback.assert_not_awaited()
        live_status_session.rollback.assert_awaited_once()
        assert table.rows[conversation_id].title == live_status_info.title

    @pytest.mark.asyncio
    async def test_get_nonexistent_conversation_info(
        self, service: SQLAppConversationInfoService
    ):
        """Test getting a conversation info that doesn't exist."""
        nonexistent_id = uuid4()
        result = await service.get_app_conversation_info(nonexistent_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_conversation_id_availability(
        self,
        service: SQLAppConversationInfoService,
        sample_conversation_info: AppConversationInfo,
    ):
        assert await service.is_app_conversation_id_available(
            sample_conversation_info.id
        )

        await service.save_app_conversation_info(sample_conversation_info)

        assert not await service.is_app_conversation_id_available(
            sample_conversation_info.id
        )

    @pytest.mark.asyncio
    async def test_stale_reservation_reclaim_rejects_old_owner(
        self,
        service: SQLAppConversationInfoService,
        async_session: AsyncSession,
    ):
        conversation_id = uuid4()
        assert await service.try_reserve_app_conversation_id(conversation_id)
        stored = await async_session.get(
            StoredConversationMetadata, str(conversation_id)
        )
        assert stored is not None
        old_token = stored.tags[APP_CONVERSATION_RESERVATION_TOKEN_KEY]
        stale_created_at = datetime.now(timezone.utc) - timedelta(days=2)
        stored.created_at = stale_created_at
        stored.last_updated_at = datetime.now(timezone.utc) - timedelta(hours=2)
        await async_session.commit()
        async_session.expunge_all()

        replacement = SQLAppConversationInfoService(
            db_session=async_session,
            user_context=SpecifyUserContext(user_id=None),
        )
        assert await replacement.try_reserve_app_conversation_id(conversation_id)
        await service.release_app_conversation_id_reservation(conversation_id)

        stored = await async_session.get(
            StoredConversationMetadata, str(conversation_id)
        )
        assert stored is not None
        assert stored.conversation_version == APP_CONVERSATION_RESERVATION_VERSION
        assert stored.tags[APP_CONVERSATION_RESERVATION_TOKEN_KEY] != old_token
        reclaimed_created_at = stored.created_at
        assert reclaimed_created_at is not None
        if reclaimed_created_at.tzinfo is None:
            reclaimed_created_at = reclaimed_created_at.replace(tzinfo=timezone.utc)
        assert reclaimed_created_at > stale_created_at

        info = AppConversationInfo(
            id=conversation_id,
            created_by_user_id=None,
            sandbox_id='sandbox',
        )
        with pytest.raises(ValueError, match='reservation is not owned'):
            await service.save_app_conversation_info(info)
        await async_session.rollback()

        await replacement.save_app_conversation_info(info)
        await replacement.release_app_conversation_id_reservation(conversation_id)
        assert await replacement.get_app_conversation_info(conversation_id) is not None

    @pytest.mark.asyncio
    async def test_reservation_renewal_preserves_creation_time(
        self,
        service: SQLAppConversationInfoService,
        async_session: AsyncSession,
    ):
        conversation_id = uuid4()
        assert await service.try_reserve_app_conversation_id(conversation_id)
        stored = await async_session.get(
            StoredConversationMetadata, str(conversation_id)
        )
        assert stored is not None
        created_at = stored.created_at
        stale_updated_at = datetime.now(timezone.utc) - timedelta(hours=2)
        stored.last_updated_at = stale_updated_at
        await async_session.commit()
        async_session.expunge_all()

        assert await service.renew_app_conversation_id_reservation(conversation_id)

        stored = await async_session.get(
            StoredConversationMetadata, str(conversation_id)
        )
        assert stored is not None
        assert stored.created_at == created_at
        assert stored.last_updated_at != stale_updated_at

    @pytest.mark.asyncio
    async def test_webhook_handoff_preserves_managed_reservation(
        self,
        service: SQLAppConversationInfoService,
        async_session: AsyncSession,
    ):
        conversation_id = uuid4()
        assert await service.try_reserve_app_conversation_id(conversation_id)
        assert await service.mark_app_conversation_id_reservation(
            conversation_id,
            'sandbox-1',
            {CODEX_CREDENTIAL_BINDING_TAG_KEY: (CODEX_CREDENTIAL_BINDING_TAG_VALUE)},
        )
        assert await service.has_managed_credential_conversation_for_sandbox(
            'sandbox-1'
        )

        webhook_service = SQLAppConversationInfoService(
            db_session=async_session,
            user_context=SpecifyUserContext(user_id=None),
        )
        await webhook_service.save_app_conversation_info(
            AppConversationInfo(
                id=conversation_id,
                created_by_user_id=None,
                sandbox_id='sandbox-1',
            ),
            allow_reservation_handoff=True,
        )

        stored = await webhook_service.get_app_conversation_info(conversation_id)
        assert stored is not None
        assert stored.tags[CODEX_CREDENTIAL_BINDING_TAG_KEY] == (
            CODEX_CREDENTIAL_BINDING_TAG_VALUE
        )

    @pytest.mark.asyncio
    async def test_webhook_handoff_rejects_another_sandbox(
        self,
        service: SQLAppConversationInfoService,
    ):
        conversation_id = uuid4()
        assert await service.try_reserve_app_conversation_id(conversation_id)
        assert await service.mark_app_conversation_id_reservation(
            conversation_id,
            'sandbox-1',
        )
        other_service = SQLAppConversationInfoService(
            db_session=service.db_session,
            user_context=SpecifyUserContext(user_id=None),
        )

        with pytest.raises(ValueError, match='reservation is not owned'):
            await other_service.save_app_conversation_info(
                AppConversationInfo(
                    id=conversation_id,
                    created_by_user_id=None,
                    sandbox_id='sandbox-2',
                ),
                allow_reservation_handoff=True,
            )

    @pytest.mark.asyncio
    async def test_round_trip_with_all_fields(
        self, service: SQLAppConversationInfoService
    ):
        """Test round trip with all possible fields populated."""
        original_info = AppConversationInfo(
            id=uuid4(),
            created_by_user_id='test_user_456',
            sandbox_id='sandbox_full_test',
            selected_repository='https://github.com/full/test',
            selected_branch='feature/test',
            git_provider=ProviderType.GITLAB,
            title='Full Test Conversation',
            trigger=ConversationTrigger.RESOLVER,
            pr_number=[789, 101112],
            llm_model='claude-3',
            agent_kind='acp',
            acp_session_id='session-123',
            acp_session_cwd='/workspace/project',
            metrics=MetricsSnapshot(accumulated_token_usage=TokenUsage()),
            created_at=datetime(2024, 2, 15, 10, 30, 0, tzinfo=timezone.utc),
            updated_at=datetime(2024, 2, 15, 11, 45, 0, tzinfo=timezone.utc),
        )

        # Save and retrieve
        await service.save_app_conversation_info(original_info)
        retrieved_info = await service.get_app_conversation_info(original_info.id)

        # Verify all fields
        assert retrieved_info is not None
        assert retrieved_info.id == original_info.id
        assert retrieved_info.sandbox_id == original_info.sandbox_id
        assert retrieved_info.selected_repository == original_info.selected_repository
        assert retrieved_info.selected_branch == original_info.selected_branch
        assert retrieved_info.git_provider == original_info.git_provider
        assert retrieved_info.title == original_info.title
        assert retrieved_info.trigger == original_info.trigger
        assert retrieved_info.pr_number == original_info.pr_number
        assert retrieved_info.llm_model == original_info.llm_model
        assert retrieved_info.agent_kind == original_info.agent_kind
        assert retrieved_info.acp_session_id == original_info.acp_session_id
        assert retrieved_info.acp_session_cwd == original_info.acp_session_cwd
        assert retrieved_info.metrics == original_info.metrics

    @pytest.mark.asyncio
    async def test_round_trip_with_minimal_fields(
        self, service: SQLAppConversationInfoService
    ):
        """Test round trip with only required fields."""
        minimal_info = AppConversationInfo(
            id=uuid4(),
            created_by_user_id='minimal_user',
            sandbox_id='minimal_sandbox',
        )

        # Save and retrieve
        await service.save_app_conversation_info(minimal_info)
        retrieved_info = await service.get_app_conversation_info(minimal_info.id)

        # Verify required fields
        assert retrieved_info is not None
        assert retrieved_info.id == minimal_info.id
        assert retrieved_info.sandbox_id == minimal_info.sandbox_id

        # Verify optional fields are None or default values
        assert retrieved_info.selected_repository is None
        assert retrieved_info.selected_branch is None
        assert retrieved_info.git_provider is None
        assert retrieved_info.title is None
        assert retrieved_info.trigger is None
        assert retrieved_info.pr_number == []
        assert retrieved_info.llm_model is None
        assert retrieved_info.metrics == MetricsSnapshot(
            accumulated_token_usage=TokenUsage()
        )

    @pytest.mark.asyncio
    async def test_batch_get_conversation_info(
        self,
        service: SQLAppConversationInfoService,
        multiple_conversation_infos: list[AppConversationInfo],
    ):
        """Test batch get operations."""
        # Save all conversation infos
        for info in multiple_conversation_infos:
            await service.save_app_conversation_info(info)

        # Get all IDs
        all_ids = [info.id for info in multiple_conversation_infos]

        # Add a non-existent ID
        nonexistent_id = uuid4()
        all_ids.append(nonexistent_id)

        # Batch get
        results = await service.batch_get_app_conversation_info(all_ids)

        # Verify results
        assert len(results) == len(all_ids)

        # Check that all existing conversations are returned
        for i, original_info in enumerate(multiple_conversation_infos):
            result = results[i]
            assert result is not None
            assert result.id == original_info.id
            assert result.title == original_info.title

        # Check that non-existent conversation returns None
        assert results[-1] is None

    @pytest.mark.asyncio
    async def test_batch_get_empty_list(self, service: SQLAppConversationInfoService):
        """Test batch get with empty list."""
        results = await service.batch_get_app_conversation_info([])
        assert results == []

    @pytest.mark.asyncio
    async def test_search_conversation_info_no_filters(
        self,
        service: SQLAppConversationInfoService,
        multiple_conversation_infos: list[AppConversationInfo],
    ):
        """Test search without any filters."""
        # Save all conversation infos
        for info in multiple_conversation_infos:
            await service.save_app_conversation_info(info)

        # Search without filters
        page = await service.search_app_conversation_info()

        # Verify results
        assert len(page.items) == len(multiple_conversation_infos)
        assert page.next_page_id is None

    @pytest.mark.asyncio
    async def test_search_conversation_info_title_filter(
        self,
        service: SQLAppConversationInfoService,
        multiple_conversation_infos: list[AppConversationInfo],
    ):
        """Test search with title filter."""
        # Save all conversation infos
        for info in multiple_conversation_infos:
            await service.save_app_conversation_info(info)

        # Search for conversations with "1" in title
        page = await service.search_app_conversation_info(title__contains='1')

        # Should find "Test Conversation 1"
        assert len(page.items) == 1
        assert '1' in page.items[0].title

    @pytest.mark.asyncio
    async def test_search_conversation_info_date_filters(
        self,
        service: SQLAppConversationInfoService,
        multiple_conversation_infos: list[AppConversationInfo],
    ):
        """Test search with date filters."""
        # Save all conversation infos
        for info in multiple_conversation_infos:
            await service.save_app_conversation_info(info)

        # Search for conversations created after a certain time
        cutoff_time = datetime(2024, 1, 1, 14, 0, 0, tzinfo=timezone.utc)
        page = await service.search_app_conversation_info(created_at__gte=cutoff_time)

        # Should find conversations created at 14:00, 15:00, 16:00, 17:00
        assert len(page.items) == 4
        for item in page.items:
            # Convert naive datetime to UTC for comparison
            item_created_at = (
                item.created_at.replace(tzinfo=timezone.utc)
                if item.created_at.tzinfo is None
                else item.created_at
            )
            assert item_created_at >= cutoff_time

    @pytest.mark.asyncio
    async def test_search_conversation_info_sorting(
        self,
        service: SQLAppConversationInfoService,
        multiple_conversation_infos: list[AppConversationInfo],
    ):
        """Test search with different sort orders."""
        # Save all conversation infos
        for info in multiple_conversation_infos:
            await service.save_app_conversation_info(info)

        # Test created_at ascending
        page = await service.search_app_conversation_info(
            sort_order=AppConversationSortOrder.CREATED_AT
        )
        created_times = [item.created_at for item in page.items]
        assert created_times == sorted(created_times)

        # Test created_at descending (default)
        page = await service.search_app_conversation_info(
            sort_order=AppConversationSortOrder.CREATED_AT_DESC
        )
        created_times = [item.created_at for item in page.items]
        assert created_times == sorted(created_times, reverse=True)

        # Test title ascending
        page = await service.search_app_conversation_info(
            sort_order=AppConversationSortOrder.TITLE
        )
        titles = [item.title for item in page.items]
        assert titles == sorted(titles)

        # Test title descending
        page = await service.search_app_conversation_info(
            sort_order=AppConversationSortOrder.TITLE_DESC
        )
        titles = [item.title for item in page.items]
        assert titles == sorted(titles, reverse=True)

    @pytest.mark.asyncio
    async def test_search_conversation_info_pagination(
        self,
        service: SQLAppConversationInfoService,
        multiple_conversation_infos: list[AppConversationInfo],
    ):
        """Test search with pagination."""
        # Save all conversation infos
        for info in multiple_conversation_infos:
            await service.save_app_conversation_info(info)

        # Get first page with limit 2
        page1 = await service.search_app_conversation_info(limit=2)
        assert len(page1.items) == 2
        assert page1.next_page_id is not None

        # Get second page
        page2 = await service.search_app_conversation_info(
            limit=2, page_id=page1.next_page_id
        )
        assert len(page2.items) == 2
        assert page2.next_page_id is not None

        # Get third page
        page3 = await service.search_app_conversation_info(
            limit=2, page_id=page2.next_page_id
        )
        assert len(page3.items) == 1  # Only 1 remaining
        assert page3.next_page_id is None

        # Verify no overlap between pages
        all_ids = set()
        for page in [page1, page2, page3]:
            for item in page.items:
                assert item.id not in all_ids  # No duplicates
                all_ids.add(item.id)

        assert len(all_ids) == len(multiple_conversation_infos)

    @pytest.mark.asyncio
    async def test_count_conversation_info_no_filters(
        self,
        service: SQLAppConversationInfoService,
        multiple_conversation_infos: list[AppConversationInfo],
    ):
        """Test count without any filters."""
        # Save all conversation infos
        for info in multiple_conversation_infos:
            await service.save_app_conversation_info(info)

        # Count without filters
        count = await service.count_app_conversation_info()
        assert count == len(multiple_conversation_infos)

    @pytest.mark.asyncio
    async def test_count_conversation_info_with_filters(
        self,
        service: SQLAppConversationInfoService,
        multiple_conversation_infos: list[AppConversationInfo],
    ):
        """Test count with various filters."""
        # Save all conversation infos
        for info in multiple_conversation_infos:
            await service.save_app_conversation_info(info)

        # Count with title filter
        count = await service.count_app_conversation_info(title__contains='1')
        assert count == 1

        # Count with date filter
        cutoff_time = datetime(2024, 1, 1, 14, 0, 0, tzinfo=timezone.utc)
        count = await service.count_app_conversation_info(created_at__gte=cutoff_time)
        assert count == 4

        # Count with no matches
        count = await service.count_app_conversation_info(title__contains='nonexistent')
        assert count == 0

    @pytest.mark.asyncio
    async def test_user_isolation(
        self,
        async_session: AsyncSession,
        multiple_conversation_infos: list[AppConversationInfo],
    ):
        """Test that user isolation works correctly."""
        # Create services for different users
        user1_service = SQLAppConversationInfoService(
            db_session=async_session, user_context=AdminUserContext(user_id='user1')
        )
        user2_service = SQLAppConversationInfoService(
            db_session=async_session, user_context=AdminUserContext(user_id='user2')
        )

        # Create conversations for different users
        user1_info = AppConversationInfo(
            id=uuid4(),
            created_by_user_id='user1',
            sandbox_id='sandbox_user1',
            title='User 1 Conversation',
        )

        user2_info = AppConversationInfo(
            id=uuid4(),
            created_by_user_id='user2',
            sandbox_id='sandbox_user2',
            title='User 2 Conversation',
        )

        # Save conversations
        await user1_service.save_app_conversation_info(user1_info)
        await user2_service.save_app_conversation_info(user2_info)

        # User 1 should only see their conversation
        user1_page = await user1_service.search_app_conversation_info()
        assert len(user1_page.items) == 1
        assert user1_page.items[0].created_by_user_id == 'user1'

        # User 2 should only see their conversation
        user2_page = await user2_service.search_app_conversation_info()
        assert len(user2_page.items) == 1
        assert user2_page.items[0].created_by_user_id == 'user2'

        # User 1 should not be able to get user 2's conversation
        user2_from_user1 = await user1_service.get_app_conversation_info(user2_info.id)
        assert user2_from_user1 is None

        # User 2 should not be able to get user 1's conversation
        user1_from_user2 = await user2_service.get_app_conversation_info(user1_info.id)
        assert user1_from_user2 is None

    @pytest.mark.asyncio
    async def test_update_conversation_info(
        self,
        service: SQLAppConversationInfoService,
        sample_conversation_info: AppConversationInfo,
    ):
        """Test updating an existing conversation info."""
        # Save initial conversation info
        await service.save_app_conversation_info(sample_conversation_info)

        # Update the conversation info
        updated_info = sample_conversation_info.model_copy()
        updated_info.title = 'Updated Title'
        updated_info.llm_model = 'gpt-4-turbo'
        updated_info.pr_number = [789]

        # Save the updated info
        await service.save_app_conversation_info(updated_info)

        # Retrieve and verify the update
        retrieved_info = await service.get_app_conversation_info(
            sample_conversation_info.id
        )
        assert retrieved_info is not None
        assert retrieved_info.title == 'Updated Title'
        assert retrieved_info.llm_model == 'gpt-4-turbo'
        assert retrieved_info.pr_number == [789]

        # Verify other fields remain unchanged
        assert retrieved_info.sandbox_id == sample_conversation_info.sandbox_id

    @pytest.mark.asyncio
    async def test_search_with_invalid_page_id(
        self,
        service: SQLAppConversationInfoService,
        multiple_conversation_infos: list[AppConversationInfo],
    ):
        """Test search with invalid page_id."""
        # Save all conversation infos
        for info in multiple_conversation_infos:
            await service.save_app_conversation_info(info)

        # Search with invalid page_id (should start from beginning)
        page = await service.search_app_conversation_info(page_id='invalid')
        assert len(page.items) == len(multiple_conversation_infos)

    @pytest.mark.asyncio
    async def test_complex_date_range_filters(
        self,
        service: SQLAppConversationInfoService,
        multiple_conversation_infos: list[AppConversationInfo],
    ):
        """Test complex date range filtering."""
        # Save all conversation infos
        for info in multiple_conversation_infos:
            await service.save_app_conversation_info(info)

        # Search for conversations in a specific time range
        start_time = datetime(2024, 1, 1, 13, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2024, 1, 1, 15, 0, 0, tzinfo=timezone.utc)

        page = await service.search_app_conversation_info(
            created_at__gte=start_time, created_at__lt=end_time
        )

        # Should find conversations created at 13:00 and 14:00
        assert len(page.items) == 2
        for item in page.items:
            # Convert naive datetime to UTC for comparison
            item_created_at = (
                item.created_at.replace(tzinfo=timezone.utc)
                if item.created_at.tzinfo is None
                else item.created_at
            )
            assert start_time <= item_created_at < end_time

        # Test count with same filters
        count = await service.count_app_conversation_info(
            created_at__gte=start_time, created_at__lt=end_time
        )
        assert count == 2
