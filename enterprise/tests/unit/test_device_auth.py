"""Tests for OAuth Device Authorization."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from storage.database import Base
from storage.device_auth_store import DeviceAuthSession, DeviceAuthStore


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def device_store(db_session):
    """Create a DeviceAuthStore for testing."""
    return DeviceAuthStore(db_session)


def test_generate_device_code(device_store):
    """Test device code generation."""
    code = device_store.generate_device_code()
    assert isinstance(code, str)
    assert len(code) > 0
    # Should be URL-safe base64
    assert all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_' for c in code)


def test_generate_user_code(device_store):
    """Test user code generation."""
    code = device_store.generate_user_code()
    assert isinstance(code, str)
    assert len(code) == 9  # XXXX-XXXX
    assert code[4] == '-'
    # Should not contain confusable characters
    assert '0' not in code
    assert 'O' not in code
    assert 'I' not in code
    assert 'L' not in code
    assert '1' not in code


def test_create_session(device_store):
    """Test creating a device authorization session."""
    device_code, user_code, expires_at = device_store.create_session(expires_in=300)
    
    assert isinstance(device_code, str)
    assert isinstance(user_code, str)
    assert isinstance(expires_at, datetime)
    
    # Check expiration time is approximately correct
    expected_expires = datetime.now(timezone.utc) + timedelta(seconds=300)
    assert abs((expires_at - expected_expires).total_seconds()) < 2
    
    # Verify session was saved to database
    session = device_store.get_session_by_device_code(device_code)
    assert session is not None
    assert session.device_code == device_code
    assert session.user_code == user_code
    assert session.status == 'pending'


def test_get_session_by_device_code(device_store):
    """Test retrieving session by device code."""
    device_code, user_code, _ = device_store.create_session()
    
    session = device_store.get_session_by_device_code(device_code)
    assert session is not None
    assert session.device_code == device_code
    assert session.user_code == user_code
    
    # Test with invalid device code
    invalid_session = device_store.get_session_by_device_code('invalid_code')
    assert invalid_session is None


def test_get_session_by_user_code(device_store):
    """Test retrieving session by user code."""
    device_code, user_code, _ = device_store.create_session()
    
    session = device_store.get_session_by_user_code(user_code)
    assert session is not None
    assert session.device_code == device_code
    assert session.user_code == user_code
    
    # Test with invalid user code
    invalid_session = device_store.get_session_by_user_code('INVALID')
    assert invalid_session is None


def test_authorize_session(device_store):
    """Test authorizing a device session."""
    device_code, user_code, _ = device_store.create_session(expires_in=300)
    
    # Authorize the session
    success = device_store.authorize_session(
        user_code=user_code,
        user_id='test_user_123',
        api_key='ohsk_test_key',
    )
    
    assert success is True
    
    # Verify session was updated
    session = device_store.get_session_by_user_code(user_code)
    assert session.status == 'authorized'
    assert session.user_id == 'test_user_123'
    assert session.api_key == 'ohsk_test_key'


def test_authorize_session_invalid_code(device_store):
    """Test authorizing with invalid user code."""
    success = device_store.authorize_session(
        user_code='INVALID',
        user_id='test_user',
        api_key='ohsk_test_key',
    )
    
    assert success is False


def test_authorize_session_expired(device_store, db_session):
    """Test authorizing an expired session."""
    # Create a session that's already expired
    device_code = device_store.generate_device_code()
    user_code = device_store.generate_user_code()
    past_time = datetime.now(timezone.utc) - timedelta(seconds=60)
    
    session = DeviceAuthSession(
        device_code=device_code,
        user_code=user_code,
        created_at=past_time,
        expires_at=past_time,
        status='pending',
    )
    db_session.add(session)
    db_session.commit()
    
    # Try to authorize
    success = device_store.authorize_session(
        user_code=user_code,
        user_id='test_user',
        api_key='ohsk_test_key',
    )
    
    assert success is False
    
    # Verify status was updated to expired
    session = device_store.get_session_by_user_code(user_code)
    assert session.status == 'expired'


def test_authorize_session_already_authorized(device_store):
    """Test authorizing an already authorized session."""
    device_code, user_code, _ = device_store.create_session()
    
    # First authorization
    success1 = device_store.authorize_session(
        user_code=user_code,
        user_id='user1',
        api_key='key1',
    )
    assert success1 is True
    
    # Try to authorize again
    success2 = device_store.authorize_session(
        user_code=user_code,
        user_id='user2',
        api_key='key2',
    )
    assert success2 is False
    
    # Verify original authorization is preserved
    session = device_store.get_session_by_user_code(user_code)
    assert session.user_id == 'user1'
    assert session.api_key == 'key1'


def test_deny_session(device_store):
    """Test denying a device session."""
    device_code, user_code, _ = device_store.create_session()
    
    success = device_store.deny_session(user_code)
    assert success is True
    
    # Verify session was denied
    session = device_store.get_session_by_user_code(user_code)
    assert session.status == 'denied'


def test_deny_session_invalid_code(device_store):
    """Test denying with invalid user code."""
    success = device_store.deny_session('INVALID')
    assert success is False


def test_is_session_expired(device_store, db_session):
    """Test checking if session is expired."""
    # Create non-expired session
    device_code1, _, _ = device_store.create_session(expires_in=300)
    assert device_store.is_session_expired(device_code1) is False
    
    # Create expired session
    device_code2 = device_store.generate_device_code()
    user_code2 = device_store.generate_user_code()
    past_time = datetime.now(timezone.utc) - timedelta(seconds=60)
    
    session = DeviceAuthSession(
        device_code=device_code2,
        user_code=user_code2,
        created_at=past_time,
        expires_at=past_time,
        status='pending',
    )
    db_session.add(session)
    db_session.commit()
    
    assert device_store.is_session_expired(device_code2) is True
    
    # Invalid device code should return True
    assert device_store.is_session_expired('invalid') is True


def test_cleanup_expired_sessions(device_store, db_session):
    """Test cleaning up expired sessions."""
    # Create some expired sessions
    for i in range(3):
        device_code = device_store.generate_device_code()
        user_code = device_store.generate_user_code()
        past_time = datetime.now(timezone.utc) - timedelta(seconds=60)
        
        session = DeviceAuthSession(
            device_code=device_code,
            user_code=user_code,
            created_at=past_time,
            expires_at=past_time,
            status='pending',
        )
        db_session.add(session)
    
    # Create some non-expired sessions
    for i in range(2):
        device_store.create_session(expires_in=300)
    
    db_session.commit()
    
    # Cleanup expired sessions
    count = device_store.cleanup_expired_sessions()
    assert count == 3
    
    # Verify only non-expired sessions remain
    remaining = db_session.query(DeviceAuthSession).count()
    assert remaining == 2


def test_user_code_uniqueness(device_store, db_session):
    """Test that user codes are unique."""
    # Generate many codes to check for collisions
    # Note: With a good charset, collisions should be extremely rare
    codes = set()
    for _ in range(100):
        code = device_store.generate_user_code()
        codes.add(code)
    
    # All codes should be unique
    assert len(codes) == 100


def test_device_code_security(device_store):
    """Test that device codes are cryptographically secure."""
    # Generate many codes and check they don't have obvious patterns
    codes = set()
    for _ in range(100):
        code = device_store.generate_device_code()
        codes.add(code)
    
    # All codes should be unique
    assert len(codes) == 100
    
    # Codes should be sufficiently long
    for code in codes:
        assert len(code) >= 32
