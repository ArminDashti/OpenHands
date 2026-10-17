"""Webhook handling for ACP session-resume mirroring (#14260 Solution B).

When the SDK reassigns ``state.agent_state`` after starting (or resuming) an
ACP session it autosaves and fires a
``ConversationStateUpdateEvent(key='agent_state', value=<dict>)``.  The
webhook ``on_event`` handler must extract ``acp_session_id`` /
``acp_session_cwd`` and mirror them into ``AppConversationInfo`` via
``update_acp_session`` so the next sandbox can resume the session.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from openhands.app_server.app_conversation.app_conversation_models import (
    AppConversationInfo,
)
from openhands.app_server.event_callback.webhook_router import on_event
from openhands.sdk.event import ConversationStateUpdateEvent


def _info(conversation_id):
    return AppConversationInfo(
        id=conversation_id,
        sandbox_id='sb-1',
        created_by_user_id='user-1',
    )


async def _call_on_event(events, conversation_id):
    app_info = _info(conversation_id)
    info_service = AsyncMock()
    event_service = AsyncMock()
    with patch(
        'openhands.app_server.event_callback.webhook_router'
        '._run_callbacks_in_bg_and_close'
    ):
        await on_event(
            events=events,
            conversation_id=conversation_id,
            app_conversation_info=app_info,
            app_conversation_info_service=info_service,
            event_service=event_service,
        )
    return info_service


@pytest.mark.asyncio
async def test_agent_state_with_acp_id_is_mirrored():
    """agent_state update carrying acp_session_id triggers update_acp_session."""
    conversation_id = uuid4()
    event = ConversationStateUpdateEvent(
        key='agent_state',
        value={
            'acp_session_id': 'sess-abc',
            'acp_session_cwd': '/workspace/project',
            'acp_agent_name': 'claude-agent-acp',
        },
    )

    info_service = await _call_on_event([event], conversation_id)

    info_service.update_acp_session.assert_awaited_once_with(
        conversation_id, 'sess-abc', '/workspace/project'
    )


@pytest.mark.asyncio
async def test_agent_state_without_acp_keys_is_ignored():
    """agent_state writes from non-ACP agents must not call update_acp_session."""
    conversation_id = uuid4()
    event = ConversationStateUpdateEvent(
        key='agent_state',
        value={'some_other_key': 'value'},
    )

    info_service = await _call_on_event([event], conversation_id)

    info_service.update_acp_session.assert_not_called()


@pytest.mark.asyncio
async def test_non_agent_state_events_are_ignored():
    """Events with unrelated keys must not trigger update_acp_session."""
    conversation_id = uuid4()
    events = [
        ConversationStateUpdateEvent(key='execution_status', value='running'),
        ConversationStateUpdateEvent(key='stats', value={'usage_to_metrics': {}}),
    ]

    info_service = await _call_on_event(events, conversation_id)

    info_service.update_acp_session.assert_not_called()


@pytest.mark.asyncio
async def test_only_cwd_with_no_id_still_mirrors():
    """agent_state carrying only ``acp_session_cwd`` still flows through.

    The webhook should reflect whatever the SDK autosaved verbatim — clearing
    the id (e.g. after a load_session failure followed by a successful
    new_session that hasn't landed yet) is the SDK's call, not ours.
    """
    conversation_id = uuid4()
    event = ConversationStateUpdateEvent(
        key='agent_state',
        value={'acp_session_cwd': '/workspace/project'},
    )

    info_service = await _call_on_event([event], conversation_id)

    info_service.update_acp_session.assert_awaited_once_with(
        conversation_id, None, '/workspace/project'
    )


@pytest.mark.asyncio
async def test_update_acp_session_failure_does_not_break_pipeline():
    """A DB write failure must not bubble up and lose subsequent events."""
    conversation_id = uuid4()
    event = ConversationStateUpdateEvent(
        key='agent_state',
        value={'acp_session_id': 'sess-x', 'acp_session_cwd': '/workspace'},
    )

    app_info = _info(conversation_id)
    info_service = AsyncMock()
    info_service.update_acp_session.side_effect = RuntimeError('db down')
    event_service = AsyncMock()
    with patch(
        'openhands.app_server.event_callback.webhook_router'
        '._run_callbacks_in_bg_and_close'
    ):
        result = await on_event(
            events=[event],
            conversation_id=conversation_id,
            app_conversation_info=app_info,
            app_conversation_info_service=info_service,
            event_service=event_service,
        )

    assert result is not None  # Success returned even though the mirror failed.
    info_service.update_acp_session.assert_awaited_once()
