"""
Tests for SaasNestedConversationManager conversation attachment methods.

This module tests the attach_to_conversation and detach_from_conversation methods
that are not supported in SaasNestedConversationManager (clients should connect
directly to the nested server).

Test Coverage:
- attach_to_conversation returns None instead of raising ValueError
- detach_from_conversation completes without raising ValueError
"""

from unittest.mock import Mock

import pytest

from enterprise.server.saas_nested_conversation_manager import (
    SaasNestedConversationManager,
)


class TestSaasNestedConversationManagerAttachment:
    """Test suite for attach_to_conversation and detach_from_conversation methods."""

    @pytest.fixture
    def conversation_manager(self):
        """Create a minimal SaasNestedConversationManager instance for testing."""
        mock_sio = Mock()
        mock_config = Mock()
        mock_config.max_concurrent_conversations = 5
        mock_server_config = Mock()
        mock_file_store = Mock()

        manager = SaasNestedConversationManager(
            sio=mock_sio,
            config=mock_config,
            server_config=mock_server_config,
            file_store=mock_file_store,
            event_retrieval=Mock(),
        )
        return manager

    @pytest.mark.asyncio
    async def test_attach_to_conversation_returns_none(self, conversation_manager):
        """
        Test: attach_to_conversation returns None instead of raising ValueError.

        This is the expected behavior per the method's return type signature
        (ServerConversation | None). Returning None allows the calling code
        to handle the case properly with a 404 response instead of a 500 error.
        """
        result = await conversation_manager.attach_to_conversation(
            'test_conversation_id', 'test_user_id'
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_attach_to_conversation_returns_none_without_user_id(
        self, conversation_manager
    ):
        """
        Test: attach_to_conversation returns None when user_id is not provided.
        """
        result = await conversation_manager.attach_to_conversation(
            'test_conversation_id'
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_detach_from_conversation_completes_without_error(
        self, conversation_manager
    ):
        """
        Test: detach_from_conversation completes without raising ValueError.

        Since attach_to_conversation returns None, detach_from_conversation
        should also complete gracefully. The calling code in conversation.py
        calls detach in a finally block after attach, so this method should
        not raise an exception even when the operation is not supported.
        """
        mock_conversation = Mock()
        # This should not raise an exception
        await conversation_manager.detach_from_conversation(mock_conversation)

    @pytest.mark.asyncio
    async def test_attach_to_conversation_does_not_raise_value_error(
        self, conversation_manager
    ):
        """
        Test: attach_to_conversation does not raise ValueError.

        This test explicitly verifies that the previous behavior (raising
        ValueError('unsupported_operation')) has been changed.
        """
        # This should NOT raise ValueError
        try:
            result = await conversation_manager.attach_to_conversation(
                'any_sid', 'any_user'
            )
            # If we get here, no exception was raised - which is correct
            assert result is None
        except ValueError as e:
            pytest.fail(f'attach_to_conversation raised ValueError: {e}')

    @pytest.mark.asyncio
    async def test_detach_from_conversation_does_not_raise_value_error(
        self, conversation_manager
    ):
        """
        Test: detach_from_conversation does not raise ValueError.

        This test explicitly verifies that the previous behavior (raising
        ValueError('unsupported_operation')) has been changed.
        """
        mock_conversation = Mock()
        # This should NOT raise ValueError
        try:
            await conversation_manager.detach_from_conversation(mock_conversation)
        except ValueError as e:
            pytest.fail(f'detach_from_conversation raised ValueError: {e}')
