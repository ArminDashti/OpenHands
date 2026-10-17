"""Tests for OpenHandsAPIClient with mocked HTTP responses."""

import base64

import httpx
import pytest
from services.openhands_api_client import OpenHandsAPIClient


@pytest.fixture
def api_client():
    client = OpenHandsAPIClient(base_url='http://test-server:3000')
    yield client
    # close handled in tests that need it


# ---------------------------------------------------------------------------
# start_conversation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_conversation_sends_correct_request(api_client, respx_mock):
    """start_conversation sends properly formatted POST with auth header."""
    automation_file = b'print("hello")'
    expected_b64 = base64.b64encode(automation_file).decode()

    route = respx_mock.post('http://test-server:3000/api/v1/app-conversations').mock(
        return_value=httpx.Response(
            200,
            json={
                'app_conversation_id': 'conv-123',
                'status': 'RUNNING',
            },
        )
    )

    result = await api_client.start_conversation(
        api_key='sk-oh-test123',
        automation_file=automation_file,
        title='Test Automation',
        event_payload={'automation_id': 'auto-1'},
    )

    assert route.called
    request = route.calls[0].request

    assert request.headers['Authorization'] == 'Bearer sk-oh-test123'

    import json

    body = json.loads(request.content)
    assert body['automation_file'] == expected_b64
    assert body['trigger'] == 'automation'
    assert body['title'] == 'Test Automation'
    assert body['event_payload'] == {'automation_id': 'auto-1'}

    assert result == {'app_conversation_id': 'conv-123', 'status': 'RUNNING'}


@pytest.mark.asyncio
async def test_start_conversation_without_event_payload(api_client, respx_mock):
    """start_conversation works with event_payload=None."""
    respx_mock.post('http://test-server:3000/api/v1/app-conversations').mock(
        return_value=httpx.Response(200, json={'app_conversation_id': 'conv-456'})
    )

    result = await api_client.start_conversation(
        api_key='sk-oh-test',
        automation_file=b'code',
        title='Test',
        event_payload=None,
    )

    assert result['app_conversation_id'] == 'conv-456'


@pytest.mark.asyncio
async def test_start_conversation_http_error(api_client, respx_mock):
    """start_conversation raises on HTTP errors."""
    respx_mock.post('http://test-server:3000/api/v1/app-conversations').mock(
        return_value=httpx.Response(500, json={'error': 'Internal Server Error'})
    )

    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await api_client.start_conversation(
            api_key='sk-oh-test',
            automation_file=b'code',
            title='Test',
        )

    assert exc_info.value.response.status_code == 500


@pytest.mark.asyncio
async def test_start_conversation_auth_error(api_client, respx_mock):
    """start_conversation raises on 401 Unauthorized."""
    respx_mock.post('http://test-server:3000/api/v1/app-conversations').mock(
        return_value=httpx.Response(401, json={'error': 'Unauthorized'})
    )

    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await api_client.start_conversation(
            api_key='bad-key',
            automation_file=b'code',
            title='Test',
        )

    assert exc_info.value.response.status_code == 401


# ---------------------------------------------------------------------------
# get_conversation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_conversation_returns_data(api_client, respx_mock):
    """get_conversation returns the first conversation from the list."""
    respx_mock.get('http://test-server:3000/api/v1/app-conversations').mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    'conversation_id': 'conv-123',
                    'status': 'RUNNING',
                    'title': 'My Automation',
                }
            ],
        )
    )

    result = await api_client.get_conversation('sk-oh-test', 'conv-123')

    assert result is not None
    assert result['conversation_id'] == 'conv-123'
    assert result['status'] == 'RUNNING'


@pytest.mark.asyncio
async def test_get_conversation_returns_none_when_empty(api_client, respx_mock):
    """get_conversation returns None when API returns empty list."""
    respx_mock.get('http://test-server:3000/api/v1/app-conversations').mock(
        return_value=httpx.Response(200, json=[])
    )

    result = await api_client.get_conversation('sk-oh-test', 'nonexistent')

    assert result is None


@pytest.mark.asyncio
async def test_get_conversation_sends_auth_header(api_client, respx_mock):
    """get_conversation sends the correct authorization header."""
    route = respx_mock.get('http://test-server:3000/api/v1/app-conversations').mock(
        return_value=httpx.Response(200, json=[])
    )

    await api_client.get_conversation('sk-oh-mykey', 'conv-1')

    assert route.called
    request = route.calls[0].request
    assert request.headers['Authorization'] == 'Bearer sk-oh-mykey'


@pytest.mark.asyncio
async def test_get_conversation_http_error(api_client, respx_mock):
    """get_conversation raises on HTTP errors."""
    respx_mock.get('http://test-server:3000/api/v1/app-conversations').mock(
        return_value=httpx.Response(503, text='Service Unavailable')
    )

    with pytest.raises(httpx.HTTPStatusError):
        await api_client.get_conversation('sk-oh-test', 'conv-1')


# ---------------------------------------------------------------------------
# close
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_close(api_client):
    """close() shuts down the HTTP client without errors."""
    await api_client.close()
