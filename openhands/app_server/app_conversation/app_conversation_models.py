from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from openhands.agent_server.models import SendMessageRequest
from openhands.agent_server.utils import utc_now
from openhands.app_server.event_callback.event_callback_models import (
    EventCallbackProcessor,
)
from openhands.app_server.sandbox.sandbox_models import SandboxStatus
from openhands.integrations.service_types import ProviderType
from openhands.sdk.conversation.state import AgentExecutionStatus
from openhands.sdk.llm import MetricsSnapshot
from openhands.storage.data_models.conversation_metadata import ConversationTrigger


class AppConversationInfo(BaseModel):
    """Conversation info which does not contain status."""

    id: UUID = Field(default_factory=uuid4)

    created_by_user_id: str | None
    sandbox_id: str

    selected_repository: str | None = None
    selected_branch: str | None = None
    git_provider: ProviderType | None = None
    title: str | None = None
    trigger: ConversationTrigger | None = None
    pr_number: list[int] = Field(default_factory=list)
    llm_model: str | None = None

    # Conversation-scoped snapshot of the ACP agent spec, frozen at creation.
    # The cloud backend rebuilds the ACP agent from the user's *global* settings
    # whenever a recycled sandbox is restarted (#14640); re-resolving from live
    # settings lets a settings edit between create and resume silently re-target
    # an in-flight conversation (e.g. Claude Code -> Codex). Pinning the spec
    # here makes the agent identity conversation-scoped, mirroring how the
    # regular agent rides the agent-server's meta.json snapshot (#1015).
    # Secret-bearing fields are stripped before persisting — provider creds,
    # acp_env, mcp_config and agent_context are re-resolved from the live
    # encrypted vault on every build, so nothing secret persists at rest (#1016).
    # Internal: persisted via the explicit SQL mapping and read back by
    # attribute on resume; excluded from serialization so it neither bloats
    # conversation-list responses nor leaks the spec into the public API.
    acp_agent_settings_snapshot: ACPAgentSettings | None = Field(
        default=None, exclude=True
    )

    # Durable mirror of the ACP CLI session identity, harvested from the
    # ConversationStateUpdateEvent(key='agent_state') webhook stream. On a
    # recycled sandbox the filesystem copy (base_state.json) is gone; this
    # mirror is what feeds ACPAgent.acp_resume_session_id so native
    # session/load resume survives the recycle (#14506 / #1126). Server-private:
    # excluded from API serialization like the spec snapshot above.
    acp_session_id: str | None = Field(default=None, exclude=True)
    acp_session_cwd: str | None = Field(default=None, exclude=True)
    acp_agent_version: str | None = Field(default=None, exclude=True)

    metrics: MetricsSnapshot | None = None

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class AppConversationSortOrder(Enum):
    CREATED_AT = 'CREATED_AT'
    CREATED_AT_DESC = 'CREATED_AT_DESC'
    UPDATED_AT = 'UPDATED_AT'
    UPDATED_AT_DESC = 'UPDATED_AT_DESC'
    TITLE = 'TITLE'
    TITLE_DESC = 'TITLE_DESC'


class AppConversationInfoPage(BaseModel):
    items: list[AppConversationInfo]
    next_page_id: str | None = None


class AppConversation(AppConversationInfo):  # type: ignore
    sandbox_status: SandboxStatus = Field(
        default=SandboxStatus.MISSING,
        description='Current sandbox status. Will be MISSING if the sandbox does not exist.',
    )
    agent_status: AgentExecutionStatus | None = Field(
        default=None,
        description='Current agent status. Will be None if the sandbox_status is not RUNNING',
    )
    conversation_url: str | None = Field(
        default=None, description='The URL where the conversation may be accessed'
    )
    session_api_key: str | None = Field(
        default=None, description='The Session Api Key for REST operations.'
    )

    # JSON fields for complex data types
    pr_number: list[int] = Field(default_factory=list)
    metrics: MetricsSnapshot | None = Field(default=None)


class AppConversationPage(BaseModel):
    items: list[AppConversation]
    next_page_id: str | None = None


class AppConversationStartRequest(BaseModel):
    """Start conversation request object.

    Although a user can go directly to the sandbox and start conversations, they
    would need to manually supply required startup parameters such as LLM key. Starting
    from the app server copies these from the user info.
    """

    sandbox_id: str | None = Field(default=None)
    initial_message: SendMessageRequest | None = None
    processors: list[EventCallbackProcessor] = Field(default_factory=list)
    llm_model: str | None = None

    # Git parameters
    selected_repository: str | None = None
    selected_branch: str | None = None
    git_provider: ProviderType | None = None
    title: str | None = None
    trigger: ConversationTrigger | None = None
    pr_number: list[int] = Field(default_factory=list)


class AppConversationStartTaskStatus(Enum):
    WORKING = 'WORKING'
    WAITING_FOR_SANDBOX = 'WAITING_FOR_SANDBOX'
    PREPARING_REPOSITORY = 'PREPARING_REPOSITORY'
    RUNNING_SETUP_SCRIPT = 'RUNNING_SETUP_SCRIPT'
    SETTING_UP_GIT_HOOKS = 'SETTING_UP_GIT_HOOKS'
    STARTING_CONVERSATION = 'STARTING_CONVERSATION'
    READY = 'READY'
    ERROR = 'ERROR'


class AppConversationStartTaskSortOrder(Enum):
    CREATED_AT = 'CREATED_AT'
    CREATED_AT_DESC = 'CREATED_AT_DESC'
    UPDATED_AT = 'UPDATED_AT'
    UPDATED_AT_DESC = 'UPDATED_AT_DESC'


class AppConversationStartTask(BaseModel):
    """Object describing the start process for an app conversation.

    Because starting an app conversation can be slow (And can involve starting a sandbox),
    we kick off a background task for it. Once the conversation is started, the app_conversation_id
    is populated."""

    id: UUID = Field(default_factory=uuid4)
    created_by_user_id: str | None
    status: AppConversationStartTaskStatus = AppConversationStartTaskStatus.WORKING
    detail: str | None = None
    app_conversation_id: UUID | None = Field(
        default=None, description='The id of the app_conversation, if READY'
    )
    sandbox_id: str | None = Field(
        default=None, description='The id of the sandbox, if READY'
    )
    agent_server_url: str | None = Field(
        default=None, description='The agent server url, if READY'
    )
    request: AppConversationStartRequest
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class AppConversationStartTaskPage(BaseModel):
    items: list[AppConversationStartTask]
    next_page_id: str | None = None
