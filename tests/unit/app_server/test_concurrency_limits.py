"""Tests for sandbox concurrency limit fallback resolution."""

import pytest

from openhands.app_server.user_auth.default_user_auth import DefaultUserAuth
from openhands.app_server.utils.concurrency import (
    SandboxConcurrencyLimitConfigError,
    get_max_concurrent_conversations_env,
    require_max_concurrent_conversations_env,
)


@pytest.mark.asyncio
async def test_default_user_auth_uses_max_concurrent_conversations_env(monkeypatch):
    monkeypatch.setenv('MAX_CONCURRENT_CONVERSATIONS', '17')

    result = await DefaultUserAuth().get_max_concurrent_sandboxes(default=10)

    assert result == 17


@pytest.mark.asyncio
async def test_default_user_auth_preserves_default_when_env_missing(monkeypatch):
    monkeypatch.delenv('MAX_CONCURRENT_CONVERSATIONS', raising=False)

    result = await DefaultUserAuth().get_max_concurrent_sandboxes(default=7)

    assert result == 7


def test_concurrency_env_parser_rejects_invalid_values(monkeypatch):
    monkeypatch.setenv('MAX_CONCURRENT_CONVERSATIONS', 'not-an-int')

    with pytest.raises(SandboxConcurrencyLimitConfigError):
        get_max_concurrent_conversations_env()


def test_required_concurrency_env_raises_when_missing(monkeypatch):
    monkeypatch.delenv('MAX_CONCURRENT_CONVERSATIONS', raising=False)

    with pytest.raises(SandboxConcurrencyLimitConfigError):
        require_max_concurrent_conversations_env()
