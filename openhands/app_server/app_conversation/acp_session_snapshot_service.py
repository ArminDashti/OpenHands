"""Durable snapshots of an ACP CLI's opaque session files — the "files half" of
native ``session/load`` resume (agent-canvas#1126; the session-id half lives on
``conversation_metadata``).

Captures the allowlisted session subtree (Codex ``sessions/**``, Claude Code
``projects/**``) from the sandbox at turn boundaries into the app server's
``FileStore`` (the same substrate the events use, so it survives exactly what
the events do), and seeds it back into a fresh sandbox before rebuild
(seed-if-absent, so a live copy wins). The agent-server route excludes
``auth.json``/``.credentials.json``/``history.jsonl`` by construction and the
sandbox never holds store credentials, so no secret rides a blob.
"""

import asyncio
import base64
import binascii
import json
import logging
from dataclasses import dataclass, field
from uuid import UUID

import httpx

from openhands.agent_server.utils import utc_now
from openhands.app_server.file_store.files import FileStore
from openhands.app_server.sandbox.sandbox_models import AGENT_SERVER, SandboxInfo
from openhands.app_server.utils.docker_utils import (
    replace_localhost_hostname_for_docker,
)

_logger = logging.getLogger(__name__)

# Providers whose CLIs support session/load from a restorable session subtree.
# gemini-cli is excluded: load_session is unreliable and its only data-dir
# lever is HOME (far too broad to snapshot) — it stays on bootstrap-prompt
# resume permanently. The authoritative allowlist enforcement (which files may
# ride a blob) lives in the agent-server routes; this set only decides whether
# the app server attempts capture/restore at all.
NATIVE_SESSION_RESUME_PROVIDERS: tuple[str, ...] = ('claude-code', 'codex')

_BLOB_TIMEOUT_SECONDS = 60.0


def supports_native_session_resume(provider: str | None) -> bool:
    return provider in NATIVE_SESSION_RESUME_PROVIDERS


def get_agent_server_url(sandbox: SandboxInfo) -> str:
    """Agent-server URL for a running sandbox (docker-hostname aware)."""
    exposed_urls = sandbox.exposed_urls
    assert exposed_urls is not None
    url = next(u.url for u in exposed_urls if u.name == AGENT_SERVER)
    return replace_localhost_hostname_for_docker(url)


@dataclass
class AcpSessionSnapshotService:
    """Capture/restore ACP session blobs between sandboxes and the FileStore."""

    file_store: FileStore
    timeout: float = _BLOB_TIMEOUT_SECONDS
    # Best-effort in-process dedup of concurrent captures (keyed by hex id). It
    # is instance-local; a multi-instance double-capture is harmless since the
    # write is idempotent (overwrites the same blob).
    _in_flight: set[str] = field(default_factory=set)

    def _blob_path(self, user_id: str | None, conversation_id: UUID, provider: str):
        # FileStore.read is text-only across backends, so the gzip blob is
        # stored base64-armored.
        return (
            f'acp_session_snapshots/{user_id or "-"}/{conversation_id.hex}/'
            f'{provider}.tar.gz.b64'
        )

    def _meta_path(self, user_id: str | None, conversation_id: UUID, provider: str):
        return (
            f'acp_session_snapshots/{user_id or "-"}/{conversation_id.hex}/'
            f'{provider}.meta.json'
        )

    async def capture(
        self,
        *,
        conversation_id: UUID,
        provider: str,
        sandbox: SandboxInfo,
        user_id: str | None,
        agent_version: str | None = None,
    ) -> bool:
        """Pull the session blob from a running sandbox into the FileStore.

        Best-effort: returns False (never raises) when the provider doesn't
        support native resume, no session files exist yet (204), the sandbox
        image predates the blob routes (404), or on any transport error.
        Deduplicates concurrent captures per conversation.
        """
        if not supports_native_session_resume(provider):
            return False
        key = conversation_id.hex
        if key in self._in_flight:
            return False
        self._in_flight.add(key)
        try:
            url = (
                f'{get_agent_server_url(sandbox)}'
                f'/api/acp_session_blob/{conversation_id}/{provider}'
            )
            headers = (
                {'X-Session-API-Key': sandbox.session_api_key}
                if sandbox.session_api_key
                else {}
            )
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
            if response.status_code == 204:
                return False
            if response.status_code == 404:
                _logger.info(
                    'Sandbox image has no ACP session-blob route; '
                    'skipping snapshot for %s',
                    conversation_id,
                )
                return False
            response.raise_for_status()
            blob = response.content
            encoded = base64.b64encode(blob).decode('ascii')
            meta = json.dumps(
                {
                    'provider': provider,
                    'agent_version': agent_version,
                    'captured_at': utc_now().isoformat(),
                    'size_bytes': len(blob),
                }
            )
            blob_path = self._blob_path(user_id, conversation_id, provider)
            meta_path = self._meta_path(user_id, conversation_id, provider)
            await asyncio.to_thread(self.file_store.write, blob_path, encoded)
            await asyncio.to_thread(self.file_store.write, meta_path, meta)
            _logger.info(
                'Captured ACP session snapshot for %s (%s, %d bytes)',
                conversation_id,
                provider,
                len(blob),
            )
            return True
        except Exception:
            _logger.exception(
                'Failed to capture ACP session snapshot for %s', conversation_id
            )
            return False
        finally:
            self._in_flight.discard(key)

    async def _read_blob(
        self, user_id: str | None, conversation_id: UUID, provider: str
    ) -> bytes | None:
        path = self._blob_path(user_id, conversation_id, provider)
        try:
            encoded = await asyncio.to_thread(self.file_store.read, path)
            return base64.b64decode(encoded)
        except FileNotFoundError:
            return None
        except (OSError, binascii.Error, ValueError):
            _logger.exception('Unreadable ACP session snapshot at %s', path)
            return None

    async def restore_into_sandbox(
        self,
        *,
        conversation_id: UUID,
        provider: str,
        sandbox: SandboxInfo,
        user_id: str | None,
    ) -> bool:
        """Seed the stored blob into a sandbox; report whether native resume is viable.

        Returns True when the sandbox ends up with session files for this
        conversation: either the stored blob was PUT successfully
        (seed-if-absent on the sandbox side), or no blob is stored but the
        sandbox already has live session files (pause/resume — the volume
        survived, nothing to restore). Returns False when neither holds, so
        the caller can fall back to bootstrap-prompt resume.
        """
        if not supports_native_session_resume(provider):
            return False
        base_url = (
            f'{get_agent_server_url(sandbox)}'
            f'/api/acp_session_blob/{conversation_id}/{provider}'
        )
        headers = (
            {'X-Session-API-Key': sandbox.session_api_key}
            if sandbox.session_api_key
            else {}
        )
        try:
            blob = await self._read_blob(user_id, conversation_id, provider)
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if blob is None:
                    # No stored snapshot — native resume is still viable if the
                    # sandbox volume survived with live session files on it.
                    response = await client.get(base_url, headers=headers)
                    return response.status_code == 200
                response = await client.put(
                    base_url,
                    content=blob,
                    headers={**headers, 'Content-Type': 'application/gzip'},
                )
                if response.status_code == 404:
                    _logger.info(
                        'Sandbox image has no ACP session-blob route; '
                        'cannot restore snapshot for %s',
                        conversation_id,
                    )
                    return False
                response.raise_for_status()
                files_written = response.json().get('files_written', 0)
                _logger.info(
                    'Restored ACP session snapshot for %s (%s, %d file(s) written)',
                    conversation_id,
                    provider,
                    files_written,
                )
                return True
        except Exception:
            _logger.exception(
                'Failed to restore ACP session snapshot for %s', conversation_id
            )
            return False

    async def delete(self, *, conversation_id: UUID, user_id: str | None) -> None:
        """GC all snapshot objects for a conversation (best-effort)."""
        prefix = f'acp_session_snapshots/{user_id or "-"}/{conversation_id.hex}'
        try:
            await asyncio.to_thread(self.file_store.delete, prefix)
        except Exception:
            _logger.exception(
                'Failed to delete ACP session snapshots for %s', conversation_id
            )
