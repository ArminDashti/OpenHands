"""Storage for OAuth Device Authorization sessions."""

import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, String
from sqlalchemy.orm import Session
from storage.database import Base


class DeviceAuthSession(Base):
    """Model for OAuth Device Authorization sessions.

    Implements RFC 8628 - OAuth 2.0 Device Authorization Grant.
    """

    __tablename__ = 'device_auth_sessions'

    device_code = Column(String(255), primary_key=True)
    user_code = Column(String(10), unique=True, nullable=False)
    user_id = Column(String(255), nullable=True)
    api_key = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(20), nullable=False, default='pending')


class DeviceAuthStore:
    """Store for managing device authorization sessions."""

    def __init__(self, session: Session):
        """Initialize the device auth store.

        Args:
            session: SQLAlchemy session
        """
        self.session = session

    @staticmethod
    def generate_device_code() -> str:
        """Generate a cryptographically secure device code.

        Returns:
            A 32-character random device code
        """
        # Use secrets for cryptographically secure random generation
        return secrets.token_urlsafe(32)

    @staticmethod
    def generate_user_code() -> str:
        """Generate a human-readable user code.

        Returns:
            An 8-character code in format XXXX-XXXX
        """
        # Use uppercase letters and digits, exclude confusable characters
        charset = ''.join(set(string.ascii_uppercase + string.digits) - set('0OIL1'))
        code = ''.join(secrets.choice(charset) for _ in range(8))
        return f'{code[:4]}-{code[4:]}'

    def create_session(
        self, expires_in: int = 300
    ) -> tuple[str, str, datetime]:
        """Create a new device authorization session.

        Args:
            expires_in: Expiration time in seconds (default 5 minutes)

        Returns:
            Tuple of (device_code, user_code, expires_at)
        """
        device_code = self.generate_device_code()
        user_code = self.generate_user_code()
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=expires_in)

        session = DeviceAuthSession(
            device_code=device_code,
            user_code=user_code,
            created_at=now,
            expires_at=expires_at,
            status='pending',
        )

        self.session.add(session)
        self.session.commit()

        return device_code, user_code, expires_at

    def get_session_by_device_code(
        self, device_code: str
    ) -> Optional[DeviceAuthSession]:
        """Get a session by device code.

        Args:
            device_code: The device code

        Returns:
            DeviceAuthSession if found, None otherwise
        """
        return (
            self.session.query(DeviceAuthSession)
            .filter(DeviceAuthSession.device_code == device_code)
            .first()
        )

    def get_session_by_user_code(
        self, user_code: str
    ) -> Optional[DeviceAuthSession]:
        """Get a session by user code.

        Args:
            user_code: The user code

        Returns:
            DeviceAuthSession if found, None otherwise
        """
        return (
            self.session.query(DeviceAuthSession)
            .filter(DeviceAuthSession.user_code == user_code)
            .first()
        )

    def authorize_session(
        self, user_code: str, user_id: str, api_key: str
    ) -> bool:
        """Authorize a device session.

        Args:
            user_code: The user code
            user_id: The user ID authorizing the device
            api_key: The API key to return to the device

        Returns:
            True if authorization successful, False if session not found or expired
        """
        session = self.get_session_by_user_code(user_code)
        if not session:
            return False

        # Check if session is expired
        if session.expires_at < datetime.now(timezone.utc):
            session.status = 'expired'
            self.session.commit()
            return False

        # Check if already authorized
        if session.status != 'pending':
            return False

        # Authorize the session
        session.user_id = user_id
        session.api_key = api_key
        session.status = 'authorized'
        self.session.commit()

        return True

    def deny_session(self, user_code: str) -> bool:
        """Deny a device authorization request.

        Args:
            user_code: The user code

        Returns:
            True if denial successful, False if session not found
        """
        session = self.get_session_by_user_code(user_code)
        if not session:
            return False

        session.status = 'denied'
        self.session.commit()
        return True

    def is_session_expired(self, device_code: str) -> bool:
        """Check if a session is expired.

        Args:
            device_code: The device code

        Returns:
            True if expired, False otherwise
        """
        session = self.get_session_by_device_code(device_code)
        if not session:
            return True

        return session.expires_at < datetime.now(timezone.utc)

    def cleanup_expired_sessions(self) -> int:
        """Delete all expired sessions.

        Returns:
            Number of sessions deleted
        """
        count = (
            self.session.query(DeviceAuthSession)
            .filter(DeviceAuthSession.expires_at < datetime.now(timezone.utc))
            .delete()
        )
        self.session.commit()
        return count
