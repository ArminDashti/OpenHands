"""Tests for Automation and AutomationRun SQLAlchemy models."""

import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from storage.automation import Automation, AutomationRun
from storage.automation_event import AutomationEvent
from storage.base import Base


def _make_engine():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    return engine


class TestAutomationModel:
    def test_create_automation_with_defaults(self):
        engine = _make_engine()
        Session = sessionmaker(bind=engine)
        with Session() as session:
            auto = Automation(
                id=uuid.uuid4().hex,
                user_id='user-1',
                name='My Automation',
                config={'name': 'My Automation', 'triggers': {'cron': {'schedule': '0 9 * * 1'}}},
                trigger_type='cron',
                file_store_key='automations/user-1/abc.py',
            )
            session.add(auto)
            session.commit()

            fetched = session.get(Automation, auto.id)
            assert fetched is not None
            assert fetched.name == 'My Automation'
            assert fetched.user_id == 'user-1'
            assert fetched.trigger_type == 'cron'
            assert fetched.org_id is None
            assert fetched.last_triggered_at is None

    def test_automation_with_org_id(self):
        engine = _make_engine()
        Session = sessionmaker(bind=engine)
        with Session() as session:
            auto = Automation(
                id=uuid.uuid4().hex,
                user_id='user-1',
                org_id='org-123',
                name='Org Automation',
                config={'name': 'Org Automation'},
                trigger_type='cron',
                file_store_key='automations/user-1/xyz.py',
            )
            session.add(auto)
            session.commit()

            fetched = session.get(Automation, auto.id)
            assert fetched is not None
            assert fetched.org_id == 'org-123'


class TestAutomationRunModel:
    def test_create_run_with_defaults(self):
        engine = _make_engine()
        Session = sessionmaker(bind=engine)
        with Session() as session:
            auto = Automation(
                id=uuid.uuid4().hex,
                user_id='user-1',
                name='Test',
                config={},
                trigger_type='cron',
                file_store_key='test.py',
            )
            session.add(auto)
            session.flush()

            run = AutomationRun(
                id=uuid.uuid4().hex,
                automation_id=auto.id,
            )
            session.add(run)
            session.commit()

            fetched = session.get(AutomationRun, run.id)
            assert fetched is not None
            assert fetched.automation_id == auto.id
            assert fetched.conversation_id is None
            assert fetched.event_id is None
            assert fetched.claimed_by is None
            assert fetched.error_detail is None

    def test_run_relationship(self):
        engine = _make_engine()
        Session = sessionmaker(bind=engine)
        with Session() as session:
            auto = Automation(
                id=uuid.uuid4().hex,
                user_id='user-1',
                name='Test',
                config={},
                trigger_type='cron',
                file_store_key='test.py',
            )
            session.add(auto)
            session.flush()

            run = AutomationRun(
                id=uuid.uuid4().hex,
                automation_id=auto.id,
            )
            session.add(run)
            session.commit()

            session.refresh(auto)
            assert len(auto.runs) == 1
            assert auto.runs[0].id == run.id
            assert run.automation.id == auto.id


class TestAutomationEventModel:
    def test_create_event(self):
        engine = _make_engine()
        Session = sessionmaker(bind=engine)
        with Session() as session:
            event = AutomationEvent(
                source_type='cron',
                payload={'tick': True},
                dedup_key='cron-2025-01-01T00:00:00',
            )
            session.add(event)
            session.commit()

            fetched = session.get(AutomationEvent, event.id)
            assert fetched is not None
            assert fetched.source_type == 'cron'
            assert fetched.payload == {'tick': True}
            assert fetched.dedup_key == 'cron-2025-01-01T00:00:00'
            assert fetched.error_detail is None

    def test_event_with_metadata(self):
        engine = _make_engine()
        Session = sessionmaker(bind=engine)
        with Session() as session:
            event = AutomationEvent(
                source_type='github',
                payload={'action': 'opened'},
                dedup_key='gh-12345',
                metadata_={'installation_id': 99},
            )
            session.add(event)
            session.commit()

            fetched = session.get(AutomationEvent, event.id)
            assert fetched is not None
            assert fetched.metadata_ == {'installation_id': 99}

    def test_dedup_key_unique(self):
        engine = _make_engine()
        Session = sessionmaker(bind=engine)
        import sqlalchemy

        with Session() as session:
            e1 = AutomationEvent(
                source_type='cron',
                payload={},
                dedup_key='dup-key',
            )
            session.add(e1)
            session.commit()

        with Session() as session:
            e2 = AutomationEvent(
                source_type='cron',
                payload={},
                dedup_key='dup-key',
            )
            session.add(e2)
            try:
                session.commit()
                assert False, 'Expected IntegrityError'
            except sqlalchemy.exc.IntegrityError:
                session.rollback()
