"""HTTP client for the main OpenHands V1 API (internal cluster calls).

Used by the automation executor to create and monitor conversations
in the main OpenHands server.
"""

import base64
import logging

import httpx

logger = logging.getLogger('saas.automation.api_client')


def _raise_with_body(resp: httpx.Response) -> None:
    """Call raise_for_status, enriching the error with the response body."""
    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        error_body = resp.text[:500] if resp.text else 'no response body'
        raise httpx.HTTPStatusError(
            f'{e.args[0]} — Response: {error_body}',
            request=e.request,
            response=e.response,
        ) from e


class OpenHandsAPIClient:
    """Async HTTP client for the OpenHands V1 API."""

    def __init__(self, base_url: str = 'http://openhands-service:3000'):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)

    async def start_conversation(
        self,
        api_key: str,
        automation_file: bytes,
        title: str,
        event_payload: dict | None = None,
    ) -> dict:
        """Submit an SDK script for sandboxed execution via V1 API.

        Args:
            api_key: User's API key for authentication.
            automation_file: Raw bytes of the .py automation script.
            title: Display title for the conversation.
            event_payload: Optional trigger event data (injected as env var).

        Returns:
            Parsed JSON response containing conversation details.

        Raises:
            httpx.HTTPStatusError: If the API returns a non-2xx status.
        """
        resp = await self.client.post(
            '/api/v1/app-conversations',
            json={
                'automation_file': base64.b64encode(automation_file).decode(),
                'trigger': 'automation',
                'title': title,
                'event_payload': event_payload,
            },
            headers={'Authorization': f'Bearer {api_key}'},
        )
        _raise_with_body(resp)
        return resp.json()

    async def get_conversation(self, api_key: str, conversation_id: str) -> dict | None:
        """Get conversation status.

        Args:
            api_key: User's API key for authentication.
            conversation_id: The conversation ID to look up.

        Returns:
            Conversation data dict, or None if not found.

        Raises:
            httpx.HTTPStatusError: If the API returns a non-2xx status.
        """
        resp = await self.client.get(
            '/api/v1/app-conversations',
            params={'ids': [conversation_id]},
            headers={'Authorization': f'Bearer {api_key}'},
        )
        _raise_with_body(resp)
        conversations = resp.json()
        return conversations[0] if conversations else None

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self.client.aclose()
