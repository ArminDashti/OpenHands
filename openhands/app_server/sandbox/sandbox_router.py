"""Runtime Containers router for OpenHands Server."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from openhands.agent_server.models import Success
from openhands.app_server.config import depends_sandbox_service
from openhands.app_server.sandbox.sandbox_models import SandboxInfo, SandboxPage
from openhands.app_server.sandbox.sandbox_service import (
    SandboxService,
)

router = APIRouter(prefix='/sandboxes', tags=['Sandbox'])
sandbox_service_dependency = depends_sandbox_service()

# Read methods


@router.get('/search')
async def search_sandboxes(
    page_id: Annotated[
        str | None,
        Query(title='Optional next_page_id from the previously returned page'),
    ] = None,
    limit: Annotated[
        int,
        Query(title='The max number of results in the page', gt=0, lte=100),
    ] = 100,
    sandbox_service: SandboxService = sandbox_service_dependency,
) -> SandboxPage:
    """Search / list sandboxes owned by the current user."""
    assert limit > 0
    assert limit <= 100
    return await sandbox_service.search_sandboxes(page_id=page_id, limit=limit)


@router.get('')
async def batch_get_sandboxes(
    id: Annotated[list[str], Query()],
    sandbox_service: SandboxService = sandbox_service_dependency,
) -> list[SandboxInfo | None]:
    """Get a batch of sandboxes given their ids, returning null for any missing."""
    assert len(id) < 100
    sandboxes = await sandbox_service.batch_get_sandboxes(id)
    return sandboxes


def _normalize_exposed_url(url: str) -> str:
    return url.rstrip('/')


def _is_allowed_worker_url(sandbox: SandboxInfo, url: str) -> bool:
    """Only allow probing worker URLs already exposed for this sandbox."""
    requested_url = _normalize_exposed_url(url)
    return any(
        exposed_url.name.startswith('WORKER_')
        and _normalize_exposed_url(exposed_url.url) == requested_url
        for exposed_url in sandbox.exposed_urls or []
    )


async def _probe_web_host(url: str) -> bool:
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=httpx.Timeout(2.5),
        ) as client:
            async with client.stream('GET', url) as response:
                return 200 <= response.status_code < 400
    except httpx.HTTPError as exc:
        _logger.debug('Web host probe failed for %s: %s', url, exc)
        return False


@router.get('/{sandbox_id}/web-host-status')
async def get_web_host_status(
    sandbox_id: str,
    url: Annotated[str, Query()],
    sandbox_service: SandboxService = sandbox_service_dependency,
) -> WebHostStatusResponse:
    """Check whether an exposed sandbox worker URL is serving a web app."""
    sandbox = await sandbox_service.get_sandbox(sandbox_id)
    if sandbox is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    if not _is_allowed_worker_url(sandbox, url):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail='URL is not an exposed worker URL for this sandbox',
        )

    return WebHostStatusResponse(reachable=await _probe_web_host(url))


# Write Methods


@router.post('')
async def start_sandbox(
    sandbox_spec_id: str | None = None,
    sandbox_service: SandboxService = sandbox_service_dependency,
) -> SandboxInfo:
    info = await sandbox_service.start_sandbox(sandbox_spec_id)
    return info


@router.post('/{id}/pause', responses={404: {'description': 'Item not found'}})
async def pause_sandbox(
    sandbox_id: str,
    sandbox_service: SandboxService = sandbox_service_dependency,
) -> Success:
    exists = await sandbox_service.pause_sandbox(sandbox_id)
    if not exists:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return Success()


@router.post('/{id}/resume', responses={404: {'description': 'Item not found'}})
async def resume_sandbox(
    sandbox_id: str,
    sandbox_service: SandboxService = sandbox_service_dependency,
) -> Success:
    exists = await sandbox_service.resume_sandbox(sandbox_id)
    if not exists:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return Success()


@router.delete('/{id}', responses={404: {'description': 'Item not found'}})
async def delete_sandbox(
    sandbox_id: str,
    sandbox_service: SandboxService = sandbox_service_dependency,
) -> Success:
    exists = await sandbox_service.delete_sandbox(sandbox_id)
    if not exists:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return Success()
