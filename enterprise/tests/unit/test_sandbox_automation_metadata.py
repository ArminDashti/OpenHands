"""Tests for sandbox automation metadata service endpoints and store."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi import HTTPException


class TestSetSandboxAutomationMetadataRequest:
    """Tests for the SetSandboxAutomationMetadataRequest model validation."""

    def test_valid_request_with_all_fields(self):
        """Request with all fields should be valid."""
        from enterprise.server.routes.service import SetSandboxAutomationMetadataRequest

        request = SetSandboxAutomationMetadataRequest(
            automation_id='auto-123',
            automation_name='Test Automation',
            trigger_type='cron',
            run_id='run-456',
            extra_metadata={'key': 'value'},
        )
        assert request.automation_id == 'auto-123'
        assert request.automation_name == 'Test Automation'

    def test_valid_request_with_only_automation_id(self):
        """Request with only automation_id should be valid."""
        from enterprise.server.routes.service import SetSandboxAutomationMetadataRequest

        request = SetSandboxAutomationMetadataRequest(automation_id='auto-123')
        assert request.automation_id == 'auto-123'
        assert request.automation_name is None

    def test_valid_request_with_only_run_id(self):
        """Request with only run_id should be valid."""
        from enterprise.server.routes.service import SetSandboxAutomationMetadataRequest

        request = SetSandboxAutomationMetadataRequest(run_id='run-456')
        assert request.run_id == 'run-456'

    def test_invalid_request_with_no_fields(self):
        """Request with no meaningful fields should fail validation."""
        from enterprise.server.routes.service import SetSandboxAutomationMetadataRequest

        with pytest.raises(ValueError, match='At least one of'):
            SetSandboxAutomationMetadataRequest()

    def test_invalid_request_with_only_extra_metadata(self):
        """Request with only extra_metadata should fail (not meaningful enough)."""
        from enterprise.server.routes.service import SetSandboxAutomationMetadataRequest

        with pytest.raises(ValueError, match='At least one of'):
            SetSandboxAutomationMetadataRequest(extra_metadata={'key': 'value'})


class TestValidateServiceApiKey:
    """Tests for service API key validation."""

    @pytest.mark.asyncio
    async def test_valid_service_key(self):
        """Valid service key should return service identifier."""
        from enterprise.server.routes.service import validate_service_api_key

        with patch('enterprise.server.routes.service.AUTOMATIONS_SERVICE_KEY', 'test-key'):
            result = await validate_service_api_key('test-key')
            assert result == 'automations-service'

    @pytest.mark.asyncio
    async def test_missing_service_key_header(self):
        """Missing service key header should raise 401."""
        from enterprise.server.routes.service import validate_service_api_key

        with patch('enterprise.server.routes.service.AUTOMATIONS_SERVICE_KEY', 'test-key'):
            with pytest.raises(HTTPException) as exc_info:
                await validate_service_api_key(None)
            assert exc_info.value.status_code == 401
            assert 'X-Service-API-Key header is required' in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_invalid_service_key(self):
        """Invalid service key should raise 401."""
        from enterprise.server.routes.service import validate_service_api_key

        with patch('enterprise.server.routes.service.AUTOMATIONS_SERVICE_KEY', 'correct-key'):
            with pytest.raises(HTTPException) as exc_info:
                await validate_service_api_key('wrong-key')
            assert exc_info.value.status_code == 401
            assert 'Invalid service API key' in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_service_auth_not_configured(self):
        """Missing AUTOMATIONS_SERVICE_KEY env var should raise 503."""
        from enterprise.server.routes.service import validate_service_api_key

        with patch('enterprise.server.routes.service.AUTOMATIONS_SERVICE_KEY', ''):
            with pytest.raises(HTTPException) as exc_info:
                await validate_service_api_key('some-key')
            assert exc_info.value.status_code == 503
            assert 'Service authentication not configured' in exc_info.value.detail


class TestSetSandboxAutomationMetadataEndpoint:
    """Tests for the PUT /api/service/sandboxes/{sandbox_id}/automation-metadata endpoint."""

    @pytest.mark.asyncio
    async def test_set_metadata_success(self):
        """Successful metadata set should return the stored metadata."""
        from enterprise.server.routes.service import set_sandbox_automation_metadata
        from enterprise.server.routes.service import SetSandboxAutomationMetadataRequest

        mock_metadata = MagicMock()
        mock_metadata.sandbox_id = 'sandbox-123'
        mock_metadata.automation_id = 'auto-456'
        mock_metadata.automation_name = 'Test'
        mock_metadata.trigger_type = 'cron'
        mock_metadata.run_id = 'run-789'
        mock_metadata.extra_metadata = {}

        with (
            patch('enterprise.server.routes.service.validate_service_api_key', new_callable=AsyncMock) as mock_validate,
            patch('storage.sandbox_automation_metadata_store.SandboxAutomationMetadataStore.set_metadata', new_callable=AsyncMock) as mock_set,
        ):
            mock_validate.return_value = 'automations-service'
            mock_set.return_value = mock_metadata

            request = SetSandboxAutomationMetadataRequest(
                automation_id='auto-456',
                automation_name='Test',
            )

            result = await set_sandbox_automation_metadata(
                sandbox_id='sandbox-123',
                request=request,
                x_service_api_key='valid-key',
            )

            assert result.sandbox_id == 'sandbox-123'
            assert result.automation_id == 'auto-456'
            mock_validate.assert_called_once_with('valid-key')


class TestGetSandboxAutomationMetadataEndpoint:
    """Tests for the GET /api/service/sandboxes/{sandbox_id}/automation-metadata endpoint."""

    @pytest.mark.asyncio
    async def test_get_metadata_found(self):
        """Should return metadata when found."""
        from enterprise.server.routes.service import get_sandbox_automation_metadata

        mock_metadata = MagicMock()
        mock_metadata.sandbox_id = 'sandbox-123'
        mock_metadata.automation_id = 'auto-456'
        mock_metadata.automation_name = 'Test'
        mock_metadata.trigger_type = 'cron'
        mock_metadata.run_id = 'run-789'
        mock_metadata.extra_metadata = {}

        with (
            patch('enterprise.server.routes.service.validate_service_api_key', new_callable=AsyncMock),
            patch('storage.sandbox_automation_metadata_store.SandboxAutomationMetadataStore.get_metadata', new_callable=AsyncMock) as mock_get,
        ):
            mock_get.return_value = mock_metadata

            result = await get_sandbox_automation_metadata(
                sandbox_id='sandbox-123',
                x_service_api_key='valid-key',
            )

            assert result.sandbox_id == 'sandbox-123'
            assert result.automation_id == 'auto-456'

    @pytest.mark.asyncio
    async def test_get_metadata_not_found(self):
        """Should raise 404 when metadata not found."""
        from enterprise.server.routes.service import get_sandbox_automation_metadata

        with (
            patch('enterprise.server.routes.service.validate_service_api_key', new_callable=AsyncMock),
            patch('storage.sandbox_automation_metadata_store.SandboxAutomationMetadataStore.get_metadata', new_callable=AsyncMock) as mock_get,
        ):
            mock_get.return_value = None

            with pytest.raises(HTTPException) as exc_info:
                await get_sandbox_automation_metadata(
                    sandbox_id='nonexistent',
                    x_service_api_key='valid-key',
                )

            assert exc_info.value.status_code == 404
            assert 'No automation metadata found' in exc_info.value.detail
