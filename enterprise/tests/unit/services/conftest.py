"""Shared fixtures for services tests.

Note: We pre-load ``storage`` as a namespace package to avoid the heavy
``storage/__init__.py`` that imports the entire enterprise model graph.
This must happen *before* any ``from storage.…`` import.
"""

import contextlib
import sys
import types

# Prevent storage/__init__.py from loading the full model graph.
# We only need the lightweight automation models for these tests.
if 'storage' not in sys.modules:
    import pathlib

    _storage_dir = str(pathlib.Path(__file__).resolve().parents[3] / 'storage')
    _mod = types.ModuleType('storage')
    _mod.__path__ = [_storage_dir]
    sys.modules['storage'] = _mod

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from storage.automation import Automation, AutomationRun  # noqa: F401
from storage.automation_event import AutomationEvent  # noqa: F401
from storage.base import Base


@pytest.fixture
async def async_engine():
    """Create an async SQLite engine for testing."""
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
async def async_session_factory(async_engine):
    """Create an async session factory that yields context-managed sessions."""
    factory = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    @contextlib.asynccontextmanager
    async def _session_ctx():
        async with factory() as session:
            yield session

    return _session_ctx


@pytest.fixture
async def async_session(async_session_factory):
    """Create a single async session for testing."""
    async with async_session_factory() as session:
        yield session
