"""
Store class for managing organizations.
"""

from typing import Optional
from uuid import UUID

from server.constants import (
    LITE_LLM_API_URL,
    ORG_SETTINGS_VERSION,
    get_default_litellm_model,
)
from sqlalchemy.orm import joinedload
from storage.database import session_maker
from storage.org import Org
from storage.user import User
from storage.user_settings import UserSettings

from openhands.core.logger import openhands_logger as logger
from openhands.storage.data_models.settings import Settings

# Member-diff keys safe to overlay onto a *different* org variant (see
# ``constrain_member_diff_to_org_kind``). ``llm`` and ``mcp_config`` are the
# only fields shared by both variants with a compatible shape. ``agent_context``
# is excluded on purpose: it is non-null on OpenHands but nullable on ACP, so
# carrying it across variants reproduces the #14674 500. Fail-closed allowlist:
# a future shared-but-type-divergent field is dropped, not forwarded.
_CROSS_VARIANT_OVERLAY_KEYS: frozenset[str] = frozenset({'llm', 'mcp_config'})


class OrgStore:
    """Store for managing organizations."""

    @staticmethod
    def create_org(
        kwargs: dict,
    ) -> Org:
        """Create a new organization."""
        with session_maker() as session:
            org = Org(**kwargs)
            org.org_version = ORG_SETTINGS_VERSION
            org.agent_settings = merge_agent_settings(
                org.agent_settings,
                {
                    'llm.model': get_org_agent_settings(org).get('llm.model')
                    or get_default_litellm_model()
                },
            )
            if org.v1_enabled is None:
                org.v1_enabled = DEFAULT_V1_ENABLED
            session.add(org)
            session.commit()
            session.refresh(org)
            return org

    @staticmethod
    def get_org_by_id(org_id: UUID) -> Org | None:
        """Get organization by ID."""
        org = None
        with session_maker() as session:
            org = session.query(Org).filter(Org.id == org_id).first()
        return OrgStore._validate_org_version(org)

    @staticmethod
    def get_current_org_from_keycloak_user_id(keycloak_user_id: str) -> Org | None:
        with session_maker() as session:
            user = (
                session.query(User)
                .options(joinedload(User.org_members))
                .filter(User.id == UUID(keycloak_user_id))
                .first()
            )
            if not user:
                logger.warning(f'User not found for ID {keycloak_user_id}')
                return None
            org_id = user.current_org_id
            org = session.query(Org).filter(Org.id == org_id).first()
            if not org:
                logger.warning(
                    f'Org not found for ID {org_id} as the current org for user {keycloak_user_id}'
                )
                return None
            return OrgStore._validate_org_version(org)

    @staticmethod
    def get_org_by_name(name: str) -> Org | None:
        """Get organization by name."""
        org = None
        with session_maker() as session:
            org = session.query(Org).filter(Org.name == name).first()
        return OrgStore._validate_org_version(org)

    @staticmethod
    def _validate_org_version(org: Org) -> Org | None:
        """Check if we need to update org version."""
        if org and org.org_version < ORG_SETTINGS_VERSION:
            org = OrgStore.update_org(
                org.id,
                {
                    'org_version': ORG_SETTINGS_VERSION,
                    'agent_settings': {
                        'llm.model': get_default_litellm_model(),
                        'llm.base_url': LITE_LLM_API_URL,
                    },
                },
            )
        return org

    @staticmethod
    def list_orgs() -> list[Org]:
        """List all organizations."""
        with session_maker() as session:
            orgs = session.query(Org).all()
            return orgs

    @staticmethod
    def update_org(
        org_id: UUID,
        kwargs: dict,
    ) -> Optional[Org]:
        """Update organization details."""
        with session_maker() as session:
            org = session.query(Org).filter(Org.id == org_id).first()
            if not org:
                return None

            if 'id' in kwargs:
                kwargs.pop('id')

            agent_settings_updates = kwargs.pop('agent_settings', None)
            for key, value in kwargs.items():
                if hasattr(org, key):
                    setattr(org, key, value)

            session.commit()
            session.refresh(org)
            return org

    @staticmethod
    def get_kwargs_from_settings(settings: Settings):
        kwargs = {
            field: getattr(settings, field)
            for field in _ORG_SETTINGS_FIELDS
            if hasattr(settings, field)
        }
        kwargs['agent_settings'] = settings.normalized_agent_settings(
            strip_secret_values=True
        )
        return kwargs

    @staticmethod
    def get_kwargs_from_user_settings(user_settings: UserSettings):
        kwargs = {
            field: getattr(user_settings, field)
            for field in _ORG_SETTINGS_FIELDS
            if hasattr(user_settings, field)
        }
        kwargs['org_version'] = user_settings.user_version
        kwargs['agent_settings'] = (
            user_settings.to_settings().normalized_agent_settings(strip_secret_values=True)
        )
        return kwargs
