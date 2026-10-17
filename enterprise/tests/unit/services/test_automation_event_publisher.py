"""Tests for automation event publisher."""

from __future__ import annotations

from unittest.mock import MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from services.automation_event_publisher import pg_notify_new_event, publish_automation_event
from storage.automation_event import AutomationEvent
from storage.base import Base


def _make_engine():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    return engine


class TestPublishAutomationEvent:
    def test_creates_event_with_correct_fields(self):
        engine = _make_engine()
        Session = sessionmaker(bind=engine)
        with Session() as session:
            event = publish_automation_event(
                session=session,
                source_type='cron',
                payload={'automation_id': 'abc'},
                dedup_key='cron-abc-2025',
                metadata={'extra': 'data'},
            )
            session.commit()

            fetched = session.get(AutomationEvent, event.id)
            assert fetched is not None
            assert fetched.source_type == 'cron'
            assert fetched.payload == {'automation_id': 'abc'}
            assert fetched.dedup_key == 'cron-abc-2025'
            assert fetched.metadata_ == {'extra': 'data'}
            assert fetched.status == 'NEW'

    def test_creates_event_without_metadata(self):
        engine = _make_engine()
        Session = sessionmaker(bind=engine)
        with Session() as session:
            event = publish_automation_event(
                session=session,
                source_type='manual',
                payload={'test': True},
                dedup_key='manual-123',
            )
            session.commit()

            fetched = session.get(AutomationEvent, event.id)
            assert fetched is not None
            assert fetched.metadata_ is None


class TestPgNotifyNewEvent:
    def test_pg_notify_executes_sql(self):
        """pg_notify uses PostgreSQL-specific function; verify it at least
        constructs the correct SQL statement. On SQLite this will fail at
        execution, so we just verify the function doesn't error before execute."""
        mock_session = MagicMock()
        pg_notify_new_event(mock_session, 42)
        mock_session.execute.assert_called_once()
        call_args = mock_session.execute.call_args
        sql_text = str(call_args[0][0])
        assert 'pg_notify' in sql_text
