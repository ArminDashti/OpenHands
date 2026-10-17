"""SQL persistence for ACP resume state (#14260 Solution B).

Round-trips ``acp_session_id`` / ``acp_session_cwd`` through the
``conversation_metadata`` table via ``update_acp_session`` and confirms
they are visible to subsequent reads.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncGenerator
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from openhands.app_server.app_conversation.app_conversation_models import (
    AppConversationInfo,
)
from openhands.app_server.app_conversation.sql_app_conversation_info_service import (
    SQLAppConversationInfoService,
    StoredConversationMetadata,
)
from openhands.app_server.user.specifiy_user_context import SpecifyUserContext
from openhands.app_server.utils.sql_utils import Base


@pytest.fixture
async def async_engine():
    engine = create_async_engine(
        'sqlite+aiosqlite:///:memory:',
        poolclass=StaticPool,
        connect_args={'check_same_thread': False},
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    session_maker = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_maker() as db_session:
        yield db_session


@pytest.fixture
def service(async_session) -> SQLAppConversationInfoService:
    return SQLAppConversationInfoService(
        db_session=async_session, user_context=SpecifyUserContext(user_id=None)
    )


@pytest.fixture
async def v1_conv(async_session):
    """A V1 conversation row with no ACP session state yet."""
    conv_id = uuid4()
    stored = StoredConversationMetadata(
        conversation_id=str(conv_id),
        sandbox_id='sb-1',
        conversation_version='V1',
        title='t',
        accumulated_cost=0.0,
        prompt_tokens=0,
        completion_tokens=0,
        cache_read_tokens=0,
        cache_write_tokens=0,
        reasoning_tokens=0,
        context_window=0,
        per_turn_token=0,
        created_at=datetime.now(timezone.utc),
        last_updated_at=datetime.now(timezone.utc),
    )
    async_session.add(stored)
    await async_session.commit()
    return conv_id, stored


@pytest.mark.asyncio
async def test_update_acp_session_persists_id_and_cwd(service, async_session, v1_conv):
    conv_id, stored = v1_conv

    await service.update_acp_session(conv_id, 'sess-123', '/workspace/project')

    await async_session.refresh(stored)
    assert stored.acp_session_id == 'sess-123'
    assert stored.acp_session_cwd == '/workspace/project'


@pytest.mark.asyncio
async def test_update_acp_session_overwrites_prior_value(
    service, async_session, v1_conv
):
    """A second write replaces the prior id (e.g. after load_session failure)."""
    conv_id, stored = v1_conv

    await service.update_acp_session(conv_id, 'sess-first', '/workspace/project')
    await service.update_acp_session(conv_id, 'sess-second', '/workspace/project')

    await async_session.refresh(stored)
    assert stored.acp_session_id == 'sess-second'


@pytest.mark.asyncio
async def test_update_acp_session_unknown_conversation_is_silent(service):
    """Update on an unknown conversation does not raise (silent skip)."""
    await service.update_acp_session(uuid4(), 'sess-x', '/workspace')


@pytest.mark.asyncio
async def test_acp_session_round_trips_through_save_and_get(service, async_session):
    """``save_app_conversation_info`` writes columns; ``_to_info`` reads back."""
    conv_id = uuid4()
    info = AppConversationInfo(
        id=conv_id,
        sandbox_id='sb-1',
        created_by_user_id='user-1',
        agent_kind='acp',
        acp_session_id='persisted-sess',
        acp_session_cwd='/workspace/project',
    )

    await service.save_app_conversation_info(info)

    fetched = await service.get_app_conversation_info(conv_id)
    assert fetched is not None
    assert fetched.acp_session_id == 'persisted-sess'
    assert fetched.acp_session_cwd == '/workspace/project'


@pytest.mark.asyncio
async def test_get_returns_none_for_acp_session_when_not_set(
    service, async_session, v1_conv
):
    """A fresh row has no ACP session state — ``_to_info`` returns ``None``."""
    conv_id, _stored = v1_conv

    fetched = await service.get_app_conversation_info(conv_id)
    assert fetched is not None
    assert fetched.acp_session_id is None
    assert fetched.acp_session_cwd is None
