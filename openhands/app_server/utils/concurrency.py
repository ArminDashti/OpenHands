"""Utilities for resolving sandbox concurrency limits."""

import os

from openhands.app_server.utils.logger import openhands_logger as logger

MAX_CONCURRENT_CONVERSATIONS_ENV_VAR = 'MAX_CONCURRENT_CONVERSATIONS'


class SandboxConcurrencyLimitConfigError(RuntimeError):
    """Raised when no valid sandbox concurrency limit is configured."""


def get_max_concurrent_conversations_env() -> int | None:
    """Return MAX_CONCURRENT_CONVERSATIONS when configured."""
    raw_value = os.getenv(MAX_CONCURRENT_CONVERSATIONS_ENV_VAR)
    if raw_value is None or raw_value.strip() == '':
        return None

    try:
        value = int(raw_value)
    except ValueError:
        raise SandboxConcurrencyLimitConfigError(
            f'{MAX_CONCURRENT_CONVERSATIONS_ENV_VAR} must be an integer'
        ) from None

    if value <= 0:
        raise SandboxConcurrencyLimitConfigError(
            f'{MAX_CONCURRENT_CONVERSATIONS_ENV_VAR} must be greater than 0'
        )

    return value


def require_max_concurrent_conversations_env() -> int:
    """Return MAX_CONCURRENT_CONVERSATIONS or raise if it is not configured."""
    value = get_max_concurrent_conversations_env()
    if value is None:
        raise SandboxConcurrencyLimitConfigError(
            f'{MAX_CONCURRENT_CONVERSATIONS_ENV_VAR} must be configured when '
            'max_concurrent_sandboxes is unset'
        )
    return value


def get_max_concurrent_sandboxes_fallback(default: int = 10) -> int:
    """Resolve the legacy environment-variable fallback for sandbox limits."""
    try:
        return get_max_concurrent_conversations_env() or default
    except SandboxConcurrencyLimitConfigError as e:
        logger.warning(str(e))
        return default
