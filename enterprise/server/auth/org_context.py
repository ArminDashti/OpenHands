"""Resolve the *effective* organization ID for the current request.

Precedence (highest first):

1. ``api_key_org_id`` — org bound to the API key used for authentication.
   The key is pinned to that org and cannot be overridden. If an
   ``X-Org-Id`` header is also present and differs, the request is
   rejected with 403.

2. ``X-Org-Id`` header — explicit, per-request override sent by the
   client. Validated against the authenticated user's org memberships;
   rejected with 403 if the user is not a member of that org.

3. ``user.current_org_id`` — the user's currently selected org (as
   mutated by ``POST /api/organizations/{org_id}/switch``). Default
   fallback when neither of the above is supplied.

The resolution is cached on ``SaasUserAuth`` for the duration of a
single request so that downstream callers (route handlers, services,
SAAS conversation/pending-message injectors) all see a consistent value
without paying for the membership lookup more than once.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from server.auth.saas_user_auth import SaasUserAuth
from server.logger import logger

from openhands.app_server.user_auth import get_user_auth

X_ORG_ID_HEADER = 'X-Org-Id'


async def resolve_effective_org_id(request: Request) -> UUID:
    """FastAPI dependency that returns the effective org id for this request.

    Raises:
        HTTPException 400: ``X-Org-Id`` header is present but is not a UUID.
        HTTPException 403: User is not a member of the requested org, or
            the request authenticates with an org-bound API key whose
            org does not match the ``X-Org-Id`` header.
        HTTPException 404: No effective org could be determined (e.g.
            user has no current org and did not supply the header).
    """
    user_auth = await get_user_auth(request)
    if not isinstance(user_auth, SaasUserAuth):
        # Non-SAAS deployments do not have multi-org context.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Organizations are not available in this deployment',
        )

    effective_org_id = await user_auth.get_effective_org_id()
    if effective_org_id is None:
        logger.warning(
            'effective_org_id_unavailable',
            extra={'user_id': user_auth.user_id},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='No current organization for user',
        )
    return effective_org_id


async def maybe_resolve_effective_org_id(request: Request) -> UUID | None:
    """Variant of :func:`resolve_effective_org_id` that returns ``None``
    rather than 404 when no effective org can be determined.

    Still raises 400/403 for malformed or unauthorized ``X-Org-Id`` headers.
    """
    user_auth = await get_user_auth(request)
    if not isinstance(user_auth, SaasUserAuth):
        return None
    return await user_auth.get_effective_org_id()


# Module-level Depends shortcuts so call sites read tidily:
#     effective_org_id: UUID = EFFECTIVE_ORG_ID,
EFFECTIVE_ORG_ID = Depends(resolve_effective_org_id)
MAYBE_EFFECTIVE_ORG_ID = Depends(maybe_resolve_effective_org_id)
