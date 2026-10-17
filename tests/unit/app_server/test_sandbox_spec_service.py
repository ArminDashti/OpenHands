"""Tests for sandbox spec service functionality.

This module tests the sandbox spec service functionality including:
- get_agent_server_image() function for determining the agent server image
- Backward compatibility with SANDBOX_RUNTIME_CONTAINER_IMAGE environment variable
"""

import os
from unittest.mock import patch

from openhands.app_server.sandbox.sandbox_spec_service import (
    AGENT_SERVER_IMAGE,
    get_agent_server_image,
)


class TestGetAgentServerImage:
    """Test cases for get_agent_server_image function."""

    def test_default_image_when_no_env_vars(self):
        """Test that default image is returned when no environment variables are set."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_agent_server_image()
            assert result == AGENT_SERVER_IMAGE

    def test_v1_style_env_vars_take_precedence(self):
        """Test that V1 style environment variables (AGENT_SERVER_IMAGE_REPOSITORY and AGENT_SERVER_IMAGE_TAG) take precedence."""
        env_vars = {
            'AGENT_SERVER_IMAGE_REPOSITORY': 'ghcr.io/openhands/agent-server',
            'AGENT_SERVER_IMAGE_TAG': 'latest',
            'SANDBOX_RUNTIME_CONTAINER_IMAGE': 'docker.openhands.dev/openhands/runtime:1.2-nikolaik',
        }

        with patch.dict(os.environ, env_vars, clear=True):
            result = get_agent_server_image()
            assert result == 'ghcr.io/openhands/agent-server:latest'

    def test_legacy_sandbox_runtime_container_image(self):
        """Test backward compatibility with SANDBOX_RUNTIME_CONTAINER_IMAGE environment variable."""
        env_vars = {
            'SANDBOX_RUNTIME_CONTAINER_IMAGE': 'docker.openhands.dev/openhands/runtime:1.2-nikolaik',
        }

        with patch.dict(os.environ, env_vars, clear=True):
            result = get_agent_server_image()
            assert result == 'docker.openhands.dev/openhands/runtime:1.2-nikolaik'

    def test_v1_style_requires_both_repository_and_tag(self):
        """Test that V1 style requires both AGENT_SERVER_IMAGE_REPOSITORY and AGENT_SERVER_IMAGE_TAG."""
        # Only repository set - should fall back to legacy or default
        env_vars = {
            'AGENT_SERVER_IMAGE_REPOSITORY': 'ghcr.io/openhands/agent-server',
            'SANDBOX_RUNTIME_CONTAINER_IMAGE': 'docker.openhands.dev/openhands/runtime:1.2-nikolaik',
        }

        with patch.dict(os.environ, env_vars, clear=True):
            result = get_agent_server_image()
            # Should fall back to SANDBOX_RUNTIME_CONTAINER_IMAGE since V1 style is incomplete
            assert result == 'docker.openhands.dev/openhands/runtime:1.2-nikolaik'

        # Only tag set - should fall back to legacy or default
        env_vars = {
            'AGENT_SERVER_IMAGE_TAG': 'latest',
            'SANDBOX_RUNTIME_CONTAINER_IMAGE': 'docker.openhands.dev/openhands/runtime:1.2-nikolaik',
        }

        with patch.dict(os.environ, env_vars, clear=True):
            result = get_agent_server_image()
            # Should fall back to SANDBOX_RUNTIME_CONTAINER_IMAGE since V1 style is incomplete
            assert result == 'docker.openhands.dev/openhands/runtime:1.2-nikolaik'

    def test_v1_style_requires_both_repository_and_tag_default_fallback(self):
        """Test that incomplete V1 style falls back to default when no legacy env var is set."""
        # Only repository set - should fall back to default
        env_vars = {
            'AGENT_SERVER_IMAGE_REPOSITORY': 'ghcr.io/openhands/agent-server',
        }

        with patch.dict(os.environ, env_vars, clear=True):
            result = get_agent_server_image()
            assert result == AGENT_SERVER_IMAGE

        # Only tag set - should fall back to default
        env_vars = {
            'AGENT_SERVER_IMAGE_TAG': 'latest',
        }

        with patch.dict(os.environ, env_vars, clear=True):
            result = get_agent_server_image()
            assert result == AGENT_SERVER_IMAGE

    def test_custom_image_with_different_registry(self):
        """Test with a custom image from a different registry."""
        env_vars = {
            'SANDBOX_RUNTIME_CONTAINER_IMAGE': 'my-registry.example.com/my-org/my-runtime:v1.0.0',
        }

        with patch.dict(os.environ, env_vars, clear=True):
            result = get_agent_server_image()
            assert result == 'my-registry.example.com/my-org/my-runtime:v1.0.0'

    def test_image_with_sha_tag(self):
        """Test with an image using a SHA tag."""
        env_vars = {
            'SANDBOX_RUNTIME_CONTAINER_IMAGE': 'ghcr.io/openhands/runtime:sha-abc123',
        }

        with patch.dict(os.environ, env_vars, clear=True):
            result = get_agent_server_image()
            assert result == 'ghcr.io/openhands/runtime:sha-abc123'

    def test_image_with_digest(self):
        """Test with an image using a digest."""
        env_vars = {
            'SANDBOX_RUNTIME_CONTAINER_IMAGE': 'ghcr.io/openhands/runtime@sha256:abc123def456',
        }

        with patch.dict(os.environ, env_vars, clear=True):
            result = get_agent_server_image()
            assert result == 'ghcr.io/openhands/runtime@sha256:abc123def456'

    def test_empty_sandbox_runtime_container_image(self):
        """Test that empty SANDBOX_RUNTIME_CONTAINER_IMAGE falls back to default."""
        env_vars = {
            'SANDBOX_RUNTIME_CONTAINER_IMAGE': '',
        }

        with patch.dict(os.environ, env_vars, clear=True):
            result = get_agent_server_image()
            # Empty string is falsy, so should fall back to default
            assert result == AGENT_SERVER_IMAGE

    def test_priority_order(self):
        """Test the priority order: V1 style > legacy > default."""
        # All three options available - V1 should win
        env_vars = {
            'AGENT_SERVER_IMAGE_REPOSITORY': 'v1-repo',
            'AGENT_SERVER_IMAGE_TAG': 'v1-tag',
            'SANDBOX_RUNTIME_CONTAINER_IMAGE': 'legacy-image:tag',
        }

        with patch.dict(os.environ, env_vars, clear=True):
            result = get_agent_server_image()
            assert result == 'v1-repo:v1-tag'

        # Only legacy available - legacy should win
        env_vars = {
            'SANDBOX_RUNTIME_CONTAINER_IMAGE': 'legacy-image:tag',
        }

        with patch.dict(os.environ, env_vars, clear=True):
            result = get_agent_server_image()
            assert result == 'legacy-image:tag'

        # Nothing available - default should be used
        with patch.dict(os.environ, {}, clear=True):
            result = get_agent_server_image()
            assert result == AGENT_SERVER_IMAGE
