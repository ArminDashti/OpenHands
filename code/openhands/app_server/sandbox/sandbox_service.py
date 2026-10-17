import asyncio
from abc import ABC, abstractmethod

from openhands.app_server.sandbox.sandbox_models import SandboxInfo, SandboxPage
from openhands.app_server.services.injector import Injector
from openhands.sdk.utils.models import DiscriminatedUnionMixin

# Known start-failure classes we translate into short, user-safe messages. Raw
# runtime status_detail (k8s pod/scheduling text) can leak internal registry
# hosts, secret/configmap names, node taints/labels, cluster size, etc., so it
# is logged for debugging but never surfaced to end users. Only the standard
# resource names below are echoed back; extended/device resources are not (the
# name can reveal the device plugin in use).
_CAPACITY_MARKERS = (
    'Insufficient cpu',
    'Insufficient memory',
    'Insufficient ephemeral-storage',
    'Insufficient pods',
)
_IMAGE_PULL_MARKERS = ('ImagePullBackOff', 'ErrImagePull')
# Deterministic placement failures -- retrying won't help. Substrings match the
# scheduler's predicate messages without echoing specific taint/label values.
_SCHEDULING_MARKERS = (
    'untolerated taint',
    'node affinity',
    'node selector',
    'volume node affinity conflict',
    'topology spread',
    'unbound',  # e.g. "unbound immediate PersistentVolumeClaims"
)

_GENERIC_START_FAILURE = (
    'The sandbox failed to start for an unexpected reason. Please try again.'
)


def _classify_start_failure(detail: str | None) -> str | None:
    """Translate a raw runtime status_detail into a user-safe message.

    Describes the failure class and likely cause so an owner knows where to
    look, but never echoes the raw detail (it can leak registry hosts, secret
    names, taints, cluster size). Returns None when nothing safe can be said,
    so the caller falls back to a generic message; the raw detail is logged.
    """
    if not detail:
        return None
    if any(m in detail for m in _IMAGE_PULL_MARKERS):
        return (
            'The sandbox image could not be pulled. The image tag may be missing, '
            'the registry credentials may be invalid, or the registry may be '
            'unreachable.'
        )
    if 'CreateContainerConfigError' in detail:
        return (
            'The sandbox failed to start due to a configuration issue (e.g. a '
            'missing secret or config value).'
        )
    if 'CreateContainerError' in detail:
        return (
            'The sandbox container could not be created, possibly due to an '
            'invalid mount, device, or startup command.'
        )
    resource = next((m for m in _CAPACITY_MARKERS if m in detail), None)
    if resource:
        return (
            f'The system is at capacity right now ({resource.lower()}). '
            'Please try again in a few minutes.'
        )
    if any(m in detail for m in _SCHEDULING_MARKERS):
        return (
            'The sandbox could not be scheduled onto any available node. No node '
            'met its placement requirements (node affinity/selector, taints, or '
            'volume constraints).'
        )
    if 'Insufficient ' in detail:
        return (
            'The sandbox could not be scheduled because a required device or '
            'resource is currently unavailable.'
        )
    return None


def _start_failure_error(sandbox_id: str, detail: str | None) -> SandboxError:
    """Build the user-facing start-failure error: a safe, descriptive message
    tagged with the sandbox id so an owner can find the raw reason in the logs.
    """
    message = _classify_start_failure(detail) or _GENERIC_START_FAILURE
    return SandboxError(f'{message} (reference: {sandbox_id})')


class SandboxService(ABC):
    """Service for accessing sandboxes in which conversations may be run."""

    @abstractmethod
    async def search_sandboxes(
        self,
        page_id: str | None = None,
        limit: int = 100,
    ) -> SandboxPage:
        """Search for sandboxes."""

    @abstractmethod
    async def get_sandbox(self, sandbox_id: str) -> SandboxInfo | None:
        """Get a single sandbox. Return None if the sandbox was not found."""

    async def batch_get_sandboxes(
        self, sandbox_ids: list[str]
    ) -> list[SandboxInfo | None]:
        """Get a batch of sandboxes, returning None for any which were not found."""
        results = await asyncio.gather(
            *[self.get_sandbox(sandbox_id) for sandbox_id in sandbox_ids]
        )
        return results

    @abstractmethod
    async def start_sandbox(self, sandbox_spec_id: str | None = None) -> SandboxInfo:
        """Begin the process of starting a sandbox.

        Return the info on the new sandbox. If no spec is selected, use the default.
        """

    @abstractmethod
    async def resume_sandbox(self, sandbox_id: str) -> bool:
        """Begin the process of resuming a sandbox.

        Return True if the sandbox exists and is being resumed or is already running.
        Return False if the sandbox did not exist.
        """

    @abstractmethod
    async def pause_sandbox(self, sandbox_id: str) -> bool:
        """Begin the process of pausing a sandbox.

        Return True if the sandbox exists and is being paused or is already paused.
        Return False if the sandbox did not exist.
        """

    @abstractmethod
    async def delete_sandbox(self, sandbox_id: str) -> bool:
        """Begin the process of deleting a sandbox (which may involve stopping it).

        Return False if the sandbox did not exist.
        """


class SandboxServiceInjector(DiscriminatedUnionMixin, Injector[SandboxService], ABC):
    pass
