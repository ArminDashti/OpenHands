"""Tests for native ACP session/load resume across sandbox recycles.

Covers the two durable halves (#14506 / agent-canvas#1126):
- AcpSessionSnapshotService — blob capture/restore between sandbox and FileStore
- the session-id mirror + native-resume precedence over bootstrap-prompt resume
"""

import base64
import io
import json
import tarfile
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr

from openhands.app_server.app_conversation.acp_session_snapshot_service import (
    AcpSessionSnapshotService,
    supports_native_session_resume,
)
from openhands.app_server.app_conversation.app_conversation_models import (
    AppConversationInfo,
)
from openhands.app_server.app_conversation.live_status_app_conversation_service import (
    LiveStatusAppConversationService,
)
from openhands.app_server.event_callback.webhook_router import (
    _extract_acp_agent_state,
    _handle_acp_session_events,
)
from openhands.app_server.file_store.local import LocalFileStore
from openhands.app_server.sandbox.sandbox_models import (
    AGENT_SERVER,
    ExposedUrl,
    SandboxInfo,
    SandboxStatus,
)
from openhands.sdk.event import ConversationStateUpdateEvent


def _make_sandbox(url='http://localhost:8010', api_key='test-key') -> SandboxInfo:
    return SandboxInfo(
        id='sandbox-1',
        created_by_user_id='user1',
        sandbox_spec_id='spec-1',
        status=SandboxStatus.RUNNING,
        session_api_key=api_key,
        exposed_urls=[ExposedUrl(name=AGENT_SERVER, url=url, port=8010)],
    )


def _make_blob() -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w:gz') as tar:
        info = tarfile.TarInfo(name='sessions/rollout-abc.jsonl')
        content = b'{"turn": 1}\n'
        info.size = len(content)
        tar.addfile(info, io.BytesIO(content))
    return buffer.getvalue()


def _mock_async_client(handler):
    """Patch httpx.AsyncClient so requests hit *handler* in-process."""
    transport = httpx.MockTransport(handler)

    class _Client(httpx.AsyncClient):
        def __init__(self, **kwargs):
            kwargs.pop('transport', None)
            super().__init__(transport=transport, **kwargs)

    return patch(
        'openhands.app_server.app_conversation.acp_session_snapshot_service'
        '.httpx.AsyncClient',
        _Client,
    )


class TestAcpSessionSnapshotService:
    @pytest.fixture
    def store(self, tmp_path):
        return LocalFileStore(root=str(tmp_path / 'store'))

    @pytest.fixture
    def service(self, store):
        return AcpSessionSnapshotService(file_store=store)

    @pytest.mark.asyncio
    async def test_capture_writes_blob_and_meta(self, service, store):
        conversation_id = uuid4()
        blob = _make_blob()

        def handler(request):
            assert request.headers['X-Session-API-Key'] == 'test-key'
            assert request.url.path == f'/api/acp_session_blob/{conversation_id}/codex'
            return httpx.Response(200, content=blob)

        with _mock_async_client(handler):
            captured = await service.capture(
                conversation_id=conversation_id,
                provider='codex',
                sandbox=_make_sandbox(),
                user_id='user1',
                agent_version='0.15.0',
            )

        assert captured is True
        stored = store.read(
            f'acp_session_snapshots/user1/{conversation_id.hex}/codex.tar.gz.b64'
        )
        assert base64.b64decode(stored) == blob
        meta = json.loads(
            store.read(
                f'acp_session_snapshots/user1/{conversation_id.hex}/codex.meta.json'
            )
        )
        assert meta['provider'] == 'codex'
        assert meta['agent_version'] == '0.15.0'

    @pytest.mark.asyncio
    @pytest.mark.parametrize('status_code', [204, 404])
    async def test_capture_no_content_or_old_image(self, service, store, status_code):
        conversation_id = uuid4()
        with _mock_async_client(lambda request: httpx.Response(status_code)):
            captured = await service.capture(
                conversation_id=conversation_id,
                provider='codex',
                sandbox=_make_sandbox(),
                user_id='user1',
            )
        assert captured is False
        with pytest.raises(FileNotFoundError):
            store.read(
                f'acp_session_snapshots/user1/{conversation_id.hex}/codex.tar.gz.b64'
            )

    @pytest.mark.asyncio
    async def test_capture_skips_gemini(self, service):
        assert not supports_native_session_resume('gemini-cli')
        captured = await service.capture(
            conversation_id=uuid4(),
            provider='gemini-cli',
            sandbox=_make_sandbox(),
            user_id='user1',
        )
        assert captured is False

    @pytest.mark.asyncio
    async def test_capture_transport_error_is_swallowed(self, service):
        def handler(request):
            raise httpx.ConnectError('refused')

        with _mock_async_client(handler):
            captured = await service.capture(
                conversation_id=uuid4(),
                provider='codex',
                sandbox=_make_sandbox(),
                user_id='user1',
            )
        assert captured is False

    @pytest.mark.asyncio
    async def test_restore_puts_stored_blob(self, service, store):
        conversation_id = uuid4()
        blob = _make_blob()
        store.write(
            f'acp_session_snapshots/user1/{conversation_id.hex}/codex.tar.gz.b64',
            base64.b64encode(blob).decode('ascii'),
        )
        seen = {}

        def handler(request):
            assert request.method == 'PUT'
            seen['content'] = request.read()
            return httpx.Response(200, json={'files_written': 1})

        with _mock_async_client(handler):
            restored = await service.restore_into_sandbox(
                conversation_id=conversation_id,
                provider='codex',
                sandbox=_make_sandbox(),
                user_id='user1',
            )

        assert restored is True
        assert seen['content'] == blob

    @pytest.mark.asyncio
    async def test_restore_without_blob_checks_live_files(self, service):
        """No stored snapshot, but the sandbox volume survived with live files."""
        conversation_id = uuid4()

        def handler(request):
            assert request.method == 'GET'
            return httpx.Response(200, content=_make_blob())

        with _mock_async_client(handler):
            restored = await service.restore_into_sandbox(
                conversation_id=conversation_id,
                provider='codex',
                sandbox=_make_sandbox(),
                user_id='user1',
            )
        assert restored is True

    @pytest.mark.asyncio
    async def test_restore_without_blob_or_live_files(self, service):
        def handler(request):
            return httpx.Response(204)

        with _mock_async_client(handler):
            restored = await service.restore_into_sandbox(
                conversation_id=uuid4(),
                provider='codex',
                sandbox=_make_sandbox(),
                user_id='user1',
            )
        assert restored is False

    @pytest.mark.asyncio
    async def test_restore_404_on_old_image(self, service, store):
        conversation_id = uuid4()
        store.write(
            f'acp_session_snapshots/user1/{conversation_id.hex}/codex.tar.gz.b64',
            base64.b64encode(_make_blob()).decode('ascii'),
        )
        with _mock_async_client(lambda request: httpx.Response(404)):
            restored = await service.restore_into_sandbox(
                conversation_id=conversation_id,
                provider='codex',
                sandbox=_make_sandbox(),
                user_id='user1',
            )
        assert restored is False

    @pytest.mark.asyncio
    async def test_delete_gc(self, service, store, tmp_path):
        conversation_id = uuid4()
        path = f'acp_session_snapshots/user1/{conversation_id.hex}/codex.tar.gz.b64'
        store.write(path, 'blob')
        await service.delete(conversation_id=conversation_id, user_id='user1')
        with pytest.raises(FileNotFoundError):
            store.read(path)


class TestPrepareNativeAcpResume:
    @pytest.fixture
    def service(self):
        mock_user_context = Mock()
        mock_user_context.get_user_id = AsyncMock(return_value='user1')
        svc = LiveStatusAppConversationService(
            init_git_in_empty_workspace=True,
            user_context=mock_user_context,
            app_conversation_info_service=Mock(),
            app_conversation_start_task_service=Mock(),
            event_callback_service=Mock(),
            event_service=Mock(),
            sandbox_service=Mock(),
            sandbox_spec_service=Mock(),
            jwt_service=Mock(),
            pending_message_service=Mock(),
            sandbox_startup_timeout=30,
            sandbox_startup_poll_frequency=1,
            max_num_conversations_per_sandbox=20,
            httpx_client=Mock(),
            web_url=None,
            openhands_provider_base_url=None,
            access_token_hard_timeout=None,
            app_mode='test',
        )
        svc._acp_snapshot_service = Mock(spec=AcpSessionSnapshotService)
        svc._acp_snapshot_service.restore_into_sandbox = AsyncMock(return_value=True)
        return svc

    def _info(self, **kwargs) -> AppConversationInfo:
        defaults = dict(
            id=uuid4(),
            created_by_user_id='user1',
            sandbox_id='sandbox-1',
            agent_kind='acp',
            tags={'acp_server': 'codex'},
            acp_session_id='sess-123',
            acp_session_cwd='/workspace/project',
        )
        defaults.update(kwargs)
        return AppConversationInfo(**defaults)

    @pytest.mark.asyncio
    async def test_happy_path(self, service):
        result = await service._prepare_native_acp_resume(
            sandbox=_make_sandbox(),
            conversation_id=uuid4(),
            existing_info=self._info(),
            expected_cwd='/workspace/project',
        )
        assert result == 'sess-123'
        service._acp_snapshot_service.restore_into_sandbox.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_existing_info(self, service):
        result = await service._prepare_native_acp_resume(
            sandbox=_make_sandbox(),
            conversation_id=uuid4(),
            existing_info=None,
            expected_cwd='/workspace/project',
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_no_mirrored_session_id(self, service):
        result = await service._prepare_native_acp_resume(
            sandbox=_make_sandbox(),
            conversation_id=uuid4(),
            existing_info=self._info(acp_session_id=None),
            expected_cwd='/workspace/project',
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_gemini_excluded(self, service):
        result = await service._prepare_native_acp_resume(
            sandbox=_make_sandbox(),
            conversation_id=uuid4(),
            existing_info=self._info(tags={'acp_server': 'gemini-cli'}),
            expected_cwd='/workspace/project',
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_cwd_mismatch_falls_back(self, service):
        result = await service._prepare_native_acp_resume(
            sandbox=_make_sandbox(),
            conversation_id=uuid4(),
            existing_info=self._info(acp_session_cwd='/somewhere/else'),
            expected_cwd='/workspace/project',
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_restore_failure_falls_back(self, service):
        service._acp_snapshot_service.restore_into_sandbox = AsyncMock(
            return_value=False
        )
        result = await service._prepare_native_acp_resume(
            sandbox=_make_sandbox(),
            conversation_id=uuid4(),
            existing_info=self._info(),
            expected_cwd='/workspace/project',
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_provider_from_spec_snapshot(self, service):
        from openhands.sdk.settings import ACPAgentSettings

        snapshot = ACPAgentSettings(acp_server='claude-code')
        result = await service._prepare_native_acp_resume(
            sandbox=_make_sandbox(),
            conversation_id=uuid4(),
            existing_info=self._info(tags={}, acp_agent_settings_snapshot=snapshot),
            expected_cwd='/workspace/project',
        )
        assert result == 'sess-123'

    def test_apply_acp_resume_fields(self, service):
        from openhands.sdk.agent.acp_agent import ACPAgent

        agent = ACPAgent(acp_command=['codex-acp'])
        stamped = service._apply_acp_resume_fields(agent, 'sess-123')
        assert stamped.acp_isolate_data_dir is True
        assert stamped.acp_resume_session_id == 'sess-123'

        fresh = service._apply_acp_resume_fields(agent, None)
        assert fresh.acp_isolate_data_dir is True
        assert fresh.acp_resume_session_id is None


class TestWebhookAcpSessionMirror:
    def _info(self, **kwargs) -> AppConversationInfo:
        defaults = dict(
            id=uuid4(),
            created_by_user_id='user1',
            sandbox_id='sandbox-1',
            agent_kind='acp',
            tags={'acp_server': 'codex'},
        )
        defaults.update(kwargs)
        return AppConversationInfo(**defaults)

    def test_extract_agent_state_incremental(self):
        events = [
            ConversationStateUpdateEvent(
                key='agent_state',
                value={'acp_session_id': 'sess-1', 'acp_session_cwd': '/w'},
            )
        ]
        state = _extract_acp_agent_state(events)
        assert state is not None
        assert state['acp_session_id'] == 'sess-1'

    def test_extract_agent_state_full_state(self):
        events = [
            ConversationStateUpdateEvent(
                key='full_state',
                value={'agent_state': {'acp_session_id': 'sess-2'}},
            )
        ]
        state = _extract_acp_agent_state(events)
        assert state is not None
        assert state['acp_session_id'] == 'sess-2'

    def test_extract_agent_state_last_wins_and_ignores_empty(self):
        events = [
            ConversationStateUpdateEvent(
                key='agent_state', value={'acp_session_id': 'sess-old'}
            ),
            ConversationStateUpdateEvent(key='agent_state', value={'other': 1}),
            ConversationStateUpdateEvent(
                key='agent_state', value={'acp_session_id': 'sess-new'}
            ),
            ConversationStateUpdateEvent(key='execution_status', value='running'),
        ]
        state = _extract_acp_agent_state(events)
        assert state is not None
        assert state['acp_session_id'] == 'sess-new'

    @pytest.mark.asyncio
    async def test_mirror_updates_on_new_session_id(self):
        conversation_id = uuid4()
        info = self._info(id=conversation_id)
        info_service = Mock()
        info_service.update_acp_session = AsyncMock()
        events = [
            ConversationStateUpdateEvent(
                key='agent_state',
                value={
                    'acp_session_id': 'sess-1',
                    'acp_session_cwd': '/workspace/project',
                    'acp_agent_version': '0.15.0',
                },
            )
        ]

        await _handle_acp_session_events(
            conversation_id, info, _make_sandbox(), events, info_service
        )

        info_service.update_acp_session.assert_awaited_once_with(
            conversation_id,
            session_id='sess-1',
            session_cwd='/workspace/project',
            agent_version='0.15.0',
        )

    @pytest.mark.asyncio
    async def test_mirror_skips_when_unchanged(self):
        conversation_id = uuid4()
        info = self._info(
            id=conversation_id,
            acp_session_id='sess-1',
            acp_session_cwd='/workspace/project',
            acp_agent_version='0.15.0',
        )
        info_service = Mock()
        info_service.update_acp_session = AsyncMock()
        events = [
            ConversationStateUpdateEvent(
                key='agent_state',
                value={
                    'acp_session_id': 'sess-1',
                    'acp_session_cwd': '/workspace/project',
                    'acp_agent_version': '0.15.0',
                },
            )
        ]

        await _handle_acp_session_events(
            conversation_id, info, _make_sandbox(), events, info_service
        )

        info_service.update_acp_session.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_turn_boundary_schedules_capture(self):
        conversation_id = uuid4()
        info = self._info(id=conversation_id)
        info_service = Mock()
        info_service.update_acp_session = AsyncMock()
        events = [
            ConversationStateUpdateEvent(key='execution_status', value='finished'),
        ]
        capture = AsyncMock(return_value=True)
        with patch(
            'openhands.app_server.event_callback.webhook_router'
            '._get_acp_snapshot_service'
        ) as get_service:
            get_service.return_value.capture = capture
            await _handle_acp_session_events(
                conversation_id, info, _make_sandbox(), events, info_service
            )
            # The capture is scheduled as a background task; let it run.
            import asyncio

            await asyncio.sleep(0)

        capture.assert_awaited_once()
        kwargs = capture.await_args.kwargs
        assert kwargs['conversation_id'] == conversation_id
        assert kwargs['provider'] == 'codex'

    @pytest.mark.asyncio
    async def test_running_status_does_not_capture(self):
        conversation_id = uuid4()
        info = self._info(id=conversation_id)
        info_service = Mock()
        info_service.update_acp_session = AsyncMock()
        events = [
            ConversationStateUpdateEvent(key='execution_status', value='running'),
        ]
        with patch(
            'openhands.app_server.event_callback.webhook_router'
            '._get_acp_snapshot_service'
        ) as get_service:
            await _handle_acp_session_events(
                conversation_id, info, _make_sandbox(), events, info_service
            )
        get_service.assert_not_called()

    @pytest.mark.asyncio
    async def test_gemini_turn_boundary_does_not_capture(self):
        conversation_id = uuid4()
        info = self._info(id=conversation_id, tags={'acp_server': 'gemini-cli'})
        info_service = Mock()
        info_service.update_acp_session = AsyncMock()
        events = [
            ConversationStateUpdateEvent(key='execution_status', value='finished'),
        ]
        with patch(
            'openhands.app_server.event_callback.webhook_router'
            '._get_acp_snapshot_service'
        ) as get_service:
            await _handle_acp_session_events(
                conversation_id, info, _make_sandbox(), events, info_service
            )
        get_service.assert_not_called()


class TestNativeResumePrecedenceInBuild:
    """Native resume engaged ⇒ no bootstrap prompt; not engaged ⇒ bootstrap."""

    @pytest.fixture
    def service(self):
        mock_user_context = Mock()
        return LiveStatusAppConversationService(
            init_git_in_empty_workspace=True,
            user_context=mock_user_context,
            app_conversation_info_service=Mock(),
            app_conversation_start_task_service=Mock(),
            event_callback_service=Mock(),
            event_service=Mock(),
            sandbox_service=Mock(),
            sandbox_spec_service=Mock(),
            jwt_service=Mock(),
            pending_message_service=Mock(),
            sandbox_startup_timeout=30,
            sandbox_startup_poll_frequency=1,
            max_num_conversations_per_sandbox=20,
            httpx_client=Mock(),
            web_url=None,
            openhands_provider_base_url=None,
            access_token_hard_timeout=None,
            app_mode='test',
        )

    def _make_acp_user(self, acp_server='codex'):
        from openhands.app_server.app_conversation.app_conversation_models import (
            SandboxGroupingStrategy,
        )
        from openhands.sdk.llm import LLM
        from openhands.sdk.settings import ACPAgentSettings, ConversationSettings

        user = Mock()
        user.id = 'user1'
        user.disabled_skills = []
        user.agent_settings = ACPAgentSettings(
            acp_server=acp_server,
            llm=LLM(model='gpt-5.5', api_key=SecretStr('sk-test')),
        )
        user.sandbox_grouping_strategy = SandboxGroupingStrategy.ADD_TO_ANY
        user.conversation_settings = ConversationSettings()
        return user

    @pytest.mark.asyncio
    async def test_native_resume_skips_bootstrap_and_sets_resume_id(
        self, service, tmp_path
    ):
        conversation_id = uuid4()
        user = self._make_acp_user()
        service.user_context.get_user_info = AsyncMock(return_value=user)
        service.user_context.get_user_email = AsyncMock(return_value=None)
        service.user_context.get_user_id = AsyncMock(return_value='user1')
        service._setup_secrets_for_git_providers = AsyncMock(return_value={})
        existing = AppConversationInfo(
            id=conversation_id,
            created_by_user_id='user1',
            sandbox_id='sandbox-1',
            agent_kind='acp',
            tags={'acp_server': 'codex'},
            acp_session_id='sess-native',
            acp_session_cwd=str(tmp_path),
        )
        service.app_conversation_info_service.get_app_conversation_info = AsyncMock(
            return_value=existing
        )
        service._acp_snapshot_service = Mock(spec=AcpSessionSnapshotService)
        service._acp_snapshot_service.restore_into_sandbox = AsyncMock(
            return_value=True
        )
        service._synthesize_acp_resume_initial_message = AsyncMock(return_value=None)

        request = await service._build_acp_start_conversation_request(
            sandbox=_make_sandbox(),
            conversation_id=conversation_id,
            initial_message=None,
            working_dir=str(tmp_path),
            plugins=None,
        )

        assert request.agent.acp_resume_session_id == 'sess-native'
        assert request.agent.acp_isolate_data_dir is True
        # Bootstrap synthesis must never run when native resume is engaged.
        service._synthesize_acp_resume_initial_message.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_no_mirror_falls_back_to_bootstrap(self, service, tmp_path):
        conversation_id = uuid4()
        user = self._make_acp_user()
        service.user_context.get_user_info = AsyncMock(return_value=user)
        service.user_context.get_user_email = AsyncMock(return_value=None)
        service._setup_secrets_for_git_providers = AsyncMock(return_value={})
        service.app_conversation_info_service.get_app_conversation_info = AsyncMock(
            return_value=None
        )
        service._synthesize_acp_resume_initial_message = AsyncMock(return_value=None)

        request = await service._build_acp_start_conversation_request(
            sandbox=_make_sandbox(),
            conversation_id=conversation_id,
            initial_message=None,
            working_dir=str(tmp_path),
            plugins=None,
        )

        assert request.agent.acp_resume_session_id is None
        assert request.agent.acp_isolate_data_dir is True
        service._synthesize_acp_resume_initial_message.assert_awaited_once()
