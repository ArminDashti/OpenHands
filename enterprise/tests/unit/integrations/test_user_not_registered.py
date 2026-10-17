"""Tests for user not registered error handling in GitHub and GitLab integrations."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from integrations.github.github_manager import GithubManager
from integrations.gitlab.gitlab_manager import GitlabManager
from integrations.gitlab.gitlab_view import GitlabFactory
from integrations.models import Message, SourceType
from integrations.utils import (
    HOST_URL,
    UserNotRegisteredError,
    get_user_not_registered_message,
)


class TestUserNotRegisteredError:
    """Test cases for UserNotRegisteredError exception."""

    def test_exception_with_username_and_user_id(self):
        """Test that the exception stores username and user_id correctly."""
        error = UserNotRegisteredError(username='testuser', user_id=12345)

        assert error.username == 'testuser'
        assert error.user_id == 12345
        assert 'testuser' in str(error)
        assert '12345' in str(error)
        assert 'not registered' in str(error).lower()

    def test_exception_is_subclass_of_exception(self):
        """Test that UserNotRegisteredError is a proper exception."""
        error = UserNotRegisteredError(username='user', user_id=1)
        assert isinstance(error, Exception)


class TestGetUserNotRegisteredMessage:
    """Test cases for get_user_not_registered_message function."""

    def test_message_with_username_contains_at_prefix(self):
        """Test that the message contains the username with @ prefix."""
        result = get_user_not_registered_message('testuser')
        assert '@testuser' in result

    def test_message_with_username_contains_not_registered_text(self):
        """Test that the message contains registration text."""
        result = get_user_not_registered_message('testuser')
        assert "haven't registered" in result or 'not registered' in result.lower()

    def test_message_with_username_contains_sign_up_instruction(self):
        """Test that the message contains sign up instruction."""
        result = get_user_not_registered_message('testuser')
        assert 'sign up' in result.lower() or 'register' in result.lower()

    def test_message_with_username_contains_host_url(self):
        """Test that the message contains the OpenHands Cloud URL."""
        result = get_user_not_registered_message('testuser')
        assert HOST_URL in result
        assert 'OpenHands Cloud' in result

    def test_message_contains_account_connection_instruction(self):
        """Test that the message instructs user to connect their account."""
        result = get_user_not_registered_message('testuser')
        assert 'connect' in result.lower() or 'github' in result.lower() or 'gitlab' in result.lower()

    def test_different_usernames(self):
        """Test that different usernames produce different messages."""
        result1 = get_user_not_registered_message('user1')
        result2 = get_user_not_registered_message('user2')
        assert '@user1' in result1
        assert '@user2' in result2
        assert '@user1' not in result2
        assert '@user2' not in result1

    def test_message_without_username_contains_registration_text(self):
        """Test that the message without username contains registration text."""
        result = get_user_not_registered_message()
        assert "haven't registered" in result or 'not registered' in result.lower()

    def test_message_without_username_contains_host_url(self):
        """Test that the message without username contains the OpenHands Cloud URL."""
        result = get_user_not_registered_message()
        assert HOST_URL in result
        assert 'OpenHands Cloud' in result

    def test_message_without_username_does_not_contain_at_prefix(self):
        """Test that the message without username does not contain @ prefix."""
        result = get_user_not_registered_message()
        assert not result.startswith('@')

    def test_message_with_none_username(self):
        """Test that passing None explicitly works the same as no argument."""
        result = get_user_not_registered_message(None)
        assert not result.startswith('@')


class TestGitHubManagerUserNotRegistered:
    """Test cases for GitHub integration handling unregistered users."""

    @staticmethod
    def _create_github_message(action='created', has_issue=True, has_pr=False):
        """Helper to create a mock GitHub message."""
        payload = {
            'action': action,
            'sender': {'id': 12345, 'login': 'testuser'},
            'repository': {
                'owner': {'login': 'test-org'},
                'name': 'test-repo',
                'private': False,
            },
        }
        if has_issue:
            payload['issue'] = {'number': 42}
            payload['comment'] = {'body': '@openhands help me', 'id': 123}
        if has_pr:
            payload['pull_request'] = {'number': 43}

        return Message(
            source=SourceType.GITHUB,
            message={
                'installation': 'inst_123',
                'payload': payload,
            },
        )

    @pytest.mark.asyncio
    @patch('integrations.github.github_manager.Auth')
    @patch('integrations.github.github_manager.GithubIntegration')
    @patch('integrations.github.github_manager.Github')
    async def test_receive_message_handles_unregistered_user(
        self, mock_github_class, mock_github_integration, mock_auth
    ):
        """Test that receive_message handles unregistered users gracefully."""
        # Setup manager with mocked dependencies
        mock_token_manager = MagicMock()
        mock_data_collector = MagicMock()
        github_manager = GithubManager(
            token_manager=mock_token_manager,
            data_collector=mock_data_collector,
        )

        # Setup mocks
        github_manager.is_job_requested = AsyncMock(return_value=True)
        mock_token_manager.get_user_id_from_idp_user_id = AsyncMock(return_value=None)

        # Mock _get_installation_access_token
        github_manager._get_installation_access_token = MagicMock(
            return_value='mock_installation_token'
        )

        # Create mock GitHub client
        mock_repo = MagicMock()
        mock_issue = MagicMock()
        mock_repo.get_issue.return_value = mock_issue
        mock_github_instance = MagicMock()
        mock_github_instance.__enter__ = MagicMock(return_value=mock_github_instance)
        mock_github_instance.__exit__ = MagicMock(return_value=None)
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance

        message = self._create_github_message()

        # Mock data_collector.process_payload to be sync
        mock_data_collector.process_payload = MagicMock()

        # Execute
        await github_manager.receive_message(message)

        # Verify: Should post a helpful comment
        mock_issue.create_comment.assert_called_once()
        comment_text = mock_issue.create_comment.call_args[0][0]
        assert '@testuser' in comment_text
        assert 'OpenHands Cloud' in comment_text

    @pytest.mark.asyncio
    @patch('integrations.github.github_manager.Auth')
    @patch('integrations.github.github_manager.GithubIntegration')
    @patch('integrations.github.github_manager.GithubFactory')
    async def test_receive_message_proceeds_for_registered_user(
        self, mock_factory, mock_github_integration, mock_auth
    ):
        """Test that receive_message proceeds normally for registered users."""
        # Setup manager with mocked dependencies
        mock_token_manager = MagicMock()
        mock_data_collector = MagicMock()
        github_manager = GithubManager(
            token_manager=mock_token_manager,
            data_collector=mock_data_collector,
        )

        # Setup mocks
        github_manager.is_job_requested = AsyncMock(return_value=True)
        mock_token_manager.get_user_id_from_idp_user_id = AsyncMock(
            return_value='keycloak-user-123'
        )
        mock_token_manager.store_org_token = AsyncMock()

        # Mock internal methods
        github_manager._get_installation_access_token = MagicMock(
            return_value='mock_installation_token'
        )
        github_manager._add_reaction = MagicMock()
        github_manager.start_job = AsyncMock()

        mock_view = MagicMock()
        mock_view.installation_id = 'inst_123'
        mock_view.user_info.username = 'testuser'
        mock_view.full_repo_name = 'test-org/test-repo'
        mock_view.issue_number = 42
        mock_factory.create_github_view_from_payload = AsyncMock(return_value=mock_view)

        message = self._create_github_message()

        # Mock data_collector.process_payload to be sync
        mock_data_collector.process_payload = MagicMock()

        # Execute
        await github_manager.receive_message(message)

        # Verify: Should call create_github_view_from_payload with keycloak_user_id
        mock_factory.create_github_view_from_payload.assert_called_once()
        call_args = mock_factory.create_github_view_from_payload.call_args
        assert call_args[0][1] == 'keycloak-user-123'

        # Verify: Should call start_job
        github_manager.start_job.assert_called_once_with(mock_view)


class TestGitLabViewUserNotRegistered:
    """Test cases for GitLab integration handling unregistered users."""

    def _create_gitlab_message(self, object_kind='issue', action='update'):
        """Helper to create a mock GitLab message."""
        payload = {
            'object_kind': object_kind,
            'event_type': 'note',
            'user': {'id': 12345, 'username': 'testuser'},
            'project': {
                'path_with_namespace': 'test-org/test-repo',
                'visibility_level': 20,
                'id': 99,
            },
            'object_attributes': {
                'project_id': 99,
                'action': action,
                'iid': 42,
            },
        }

        if object_kind == 'issue':
            payload['issue'] = {'iid': 42}
            payload['labels'] = [{'title': 'openhands'}]

        return Message(
            source=SourceType.GITLAB,
            message={
                'installation_id': 'webhook_123',
                'payload': payload,
            },
        )

    @pytest.mark.asyncio
    async def test_create_gitlab_view_raises_for_unregistered_user(self):
        """Test that create_gitlab_view_from_payload raises UserNotRegisteredError for unregistered users."""
        # Setup
        mock_token_manager = MagicMock()
        mock_token_manager.get_user_id_from_idp_user_id = AsyncMock(return_value=None)

        # Create a message that would trigger GitlabFactory
        message = self._create_gitlab_message()

        # Execute & Verify
        with pytest.raises(UserNotRegisteredError) as exc_info:
            await GitlabFactory.create_gitlab_view_from_payload(
                message, mock_token_manager
            )

        error = exc_info.value
        assert error.username == 'testuser'
        assert error.user_id == 12345


class TestGitLabManagerUserNotRegistered:
    """Test cases for GitLab manager handling unregistered users."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_token_manager = MagicMock()
        self.gitlab_manager = GitlabManager(token_manager=self.mock_token_manager)

    def _create_gitlab_message(self):
        """Helper to create a mock GitLab message."""
        return Message(
            source=SourceType.GITLAB,
            message={
                'installation_id': 'webhook_123',
                'payload': {
                    'object_kind': 'issue',
                    'event_type': 'note',
                    'user': {'id': 12345, 'username': 'testuser'},
                    'project': {
                        'path_with_namespace': 'test-org/test-repo',
                        'visibility_level': 20,
                        'id': 99,
                    },
                    'object_attributes': {
                        'project_id': 99,
                        'action': 'update',
                        'iid': 42,
                    },
                    'issue': {'iid': 42},
                    'labels': [{'title': 'openhands'}],
                },
            },
        )

    @pytest.mark.asyncio
    @patch('integrations.gitlab.gitlab_manager.GitlabFactory')
    @patch.object(GitlabManager, 'is_job_requested')
    @patch.object(GitlabManager, '_send_user_not_registered_message')
    async def test_receive_message_handles_unregistered_user(
        self, mock_send_msg, mock_is_job_requested, mock_factory
    ):
        """Test that receive_message catches UserNotRegisteredError and sends helpful message."""
        # Setup
        mock_is_job_requested.return_value = True
        mock_factory.create_gitlab_view_from_payload = AsyncMock(
            side_effect=UserNotRegisteredError(username='testuser', user_id=12345)
        )
        mock_send_msg.return_value = None

        message = self._create_gitlab_message()

        # Execute
        await self.gitlab_manager.receive_message(message)

        # Verify: Should call _send_user_not_registered_message
        mock_send_msg.assert_called_once()
        call_args = mock_send_msg.call_args
        assert call_args[0][1] == 'testuser'

    @pytest.mark.asyncio
    @patch('integrations.gitlab.gitlab_manager.GitlabFactory')
    @patch.object(GitlabManager, 'is_job_requested')
    @patch.object(GitlabManager, 'start_job')
    async def test_receive_message_proceeds_for_registered_user(
        self, mock_start_job, mock_is_job_requested, mock_factory
    ):
        """Test that receive_message proceeds normally for registered users."""
        # Setup
        mock_is_job_requested.return_value = True

        mock_view = MagicMock()
        mock_view.user_info.username = 'testuser'
        mock_view.full_repo_name = 'test-org/test-repo'
        mock_view.issue_number = 42
        mock_factory.create_gitlab_view_from_payload = AsyncMock(return_value=mock_view)

        mock_start_job.return_value = None

        message = self._create_gitlab_message()

        # Execute
        await self.gitlab_manager.receive_message(message)

        # Verify: Should call start_job
        mock_start_job.assert_called_once_with(mock_view)
