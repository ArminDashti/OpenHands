from datetime import UTC, datetime, timedelta
from typing import AsyncGenerator
from uuid import UUID

import pytest
from server.routes.org_models import OrgAuthorizationError
from server.services.org_usage_service import NO_REPOSITORY_LABEL, OrgUsageService
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from storage.base import Base
from storage.org import Org
from storage.org_member import OrgMember
from storage.role import Role
from storage.stored_conversation_metadata import StoredConversationMetadata
from storage.stored_conversation_metadata_saas import StoredConversationMetadataSaas
from storage.user import User

from openhands.app_server.user.specifiy_user_context import SpecifyUserContext

PERSONAL_USER_ID = UUID("aaaaaaaa-1111-1111-1111-111111111111")
TEAM_ADMIN_USER_ID = UUID("bbbbbbbb-2222-2222-2222-222222222222")
TEAM_MEMBER_USER_ID = UUID("cccccccc-3333-3333-3333-333333333333")
TEAM_ORG_ID = UUID("dddddddd-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


@pytest.fixture
async def async_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    session_maker = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_maker() as session:
        owner_role = Role(id=1, name="owner", rank=3)
        admin_role = Role(id=2, name="admin", rank=2)
        member_role = Role(id=3, name="member", rank=1)
        session.add_all([owner_role, admin_role, member_role])

        personal_org = Org(
            id=PERSONAL_USER_ID,
            name="personal-org",
            enable_default_condenser=True,
            enable_proactive_conversation_starters=True,
        )
        team_org = Org(
            id=TEAM_ORG_ID,
            name="team-org",
            enable_default_condenser=True,
            enable_proactive_conversation_starters=True,
        )
        session.add_all([personal_org, team_org])

        personal_user = User(id=PERSONAL_USER_ID, current_org_id=PERSONAL_USER_ID)
        team_admin = User(id=TEAM_ADMIN_USER_ID, current_org_id=TEAM_ORG_ID)
        team_member = User(id=TEAM_MEMBER_USER_ID, current_org_id=TEAM_ORG_ID)
        session.add_all([personal_user, team_admin, team_member])

        session.add_all(
            [
                OrgMember(
                    org_id=PERSONAL_USER_ID,
                    user_id=PERSONAL_USER_ID,
                    role_id=3,
                    llm_api_key="personal-key",
                    status="active",
                ),
                OrgMember(
                    org_id=TEAM_ORG_ID,
                    user_id=TEAM_ADMIN_USER_ID,
                    role_id=2,
                    llm_api_key="admin-key",
                    status="active",
                ),
                OrgMember(
                    org_id=TEAM_ORG_ID,
                    user_id=TEAM_MEMBER_USER_ID,
                    role_id=3,
                    llm_api_key="member-key",
                    status="active",
                ),
            ]
        )

        now = datetime.now(UTC).replace(microsecond=0)
        rows = [
            (
                "team-1",
                TEAM_ADMIN_USER_ID,
                TEAM_ORG_ID,
                now,
                2.0,
                "openhands/backend",
                "V1",
            ),
            (
                "team-2",
                TEAM_ADMIN_USER_ID,
                TEAM_ORG_ID,
                now - timedelta(days=1),
                4.0,
                "openhands/backend",
                "V1",
            ),
            (
                "team-3",
                TEAM_MEMBER_USER_ID,
                TEAM_ORG_ID,
                now - timedelta(days=1),
                6.0,
                None,
                "V1",
            ),
            (
                "team-4",
                TEAM_MEMBER_USER_ID,
                TEAM_ORG_ID,
                now - timedelta(days=31),
                10.0,
                "openhands/frontend",
                "V1",
            ),
            (
                "team-v0",
                TEAM_ADMIN_USER_ID,
                TEAM_ORG_ID,
                now,
                8.0,
                "openhands/ignored",
                "V0",
            ),
            (
                "personal-1",
                PERSONAL_USER_ID,
                PERSONAL_USER_ID,
                now,
                3.5,
                "openhands/docs",
                "V1",
            ),
        ]

        for conversation_id, user_id, org_id, created_at, cost, repository, version in rows:
            session.add(
                StoredConversationMetadata(
                    conversation_id=conversation_id,
                    created_at=created_at,
                    last_updated_at=created_at,
                    accumulated_cost=cost,
                    selected_repository=repository,
                    conversation_version=version,
                    title=conversation_id,
                )
            )
            session.add(
                StoredConversationMetadataSaas(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    org_id=org_id,
                )
            )

        await session.commit()
        yield session


@pytest.mark.asyncio
async def test_org_usage_service_returns_team_metrics(db_session: AsyncSession):
    service = OrgUsageService(
        db_session=db_session,
        user_context=SpecifyUserContext(user_id=str(TEAM_ADMIN_USER_ID)),
    )

    result = await service.get_org_usage(TEAM_ORG_ID)

    assert result.summary.total_conversations == 4
    assert result.summary.average_cost_per_conversation_last_30_days == pytest.approx(4.0)
    assert len(result.daily_conversations) == 30

    counts_by_day = {
        item.date: item.conversation_count for item in result.daily_conversations
    }
    today = datetime.now(UTC).date().isoformat()
    yesterday = (datetime.now(UTC).date() - timedelta(days=1)).isoformat()
    assert counts_by_day[today] == 1
    assert counts_by_day[yesterday] == 2

    assert result.top_repositories[0].repository == "openhands/backend"
    assert result.top_repositories[0].conversation_count == 2
    assert any(
        item.repository == NO_REPOSITORY_LABEL and item.conversation_count == 1
        for item in result.top_repositories
    )
    assert any(
        item.repository == "openhands/frontend" and item.conversation_count == 1
        for item in result.top_repositories
    )


@pytest.mark.asyncio
async def test_org_usage_service_allows_personal_workspace_members(
    db_session: AsyncSession,
):
    service = OrgUsageService(
        db_session=db_session,
        user_context=SpecifyUserContext(user_id=str(PERSONAL_USER_ID)),
    )

    result = await service.get_org_usage(PERSONAL_USER_ID)

    assert result.summary.total_conversations == 1
    assert result.summary.average_cost_per_conversation_last_30_days == pytest.approx(3.5)
    assert result.top_repositories[0].repository == "openhands/docs"


@pytest.mark.asyncio
async def test_org_usage_service_rejects_team_members(db_session: AsyncSession):
    service = OrgUsageService(
        db_session=db_session,
        user_context=SpecifyUserContext(user_id=str(TEAM_MEMBER_USER_ID)),
    )

    with pytest.raises(OrgAuthorizationError):
        await service.get_org_usage(TEAM_ORG_ID)
