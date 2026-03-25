#  Copyright 2026 Microsoft Corporation
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""Tests for AzureRedisClientFactory."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.helpers.cache.config import RedisCacheConfig
from app.providers.dependencies.az.redis_client_factory import AzureRedisClientFactory


class TestAzureRedisClientFactory:
    """Test cases for AzureRedisClientFactory."""

    @pytest.mark.asyncio
    async def test_create_client_with_passwordless_auth_disabled_uses_password(self):
        """Test that create_client() uses password auth when passwordless disabled."""
        with patch("app.providers.dependencies.az.redis_client_factory.get_provider_config") as mock_get_provider, \
             patch("app.providers.dependencies.az.redis_client_factory.RedisClientFactory.create_client") as mock_parent_create:

            # Setup Azure config with passwordless disabled
            mock_azure_config = MagicMock()
            mock_azure_config.redis_use_passwordless_auth = False
            mock_get_provider.return_value = mock_azure_config

            mock_redis = AsyncMock()
            mock_parent_create.return_value = mock_redis

            config = RedisCacheConfig()
            factory = AzureRedisClientFactory(config, use_index_database=False)
            client = await factory.create_client()

            # Should fall back to parent password-based implementation
            mock_parent_create.assert_called_once()
            assert client == mock_redis

    @pytest.mark.asyncio
    async def test_create_client_with_credential_failure_falls_back_to_password(self):
        """Test that create_client() falls back to password when credentials fail."""
        with patch("app.providers.dependencies.az.redis_client_factory.get_provider_config") as mock_get_provider, \
             patch("app.providers.dependencies.az.redis_client_factory.AzureRedisCredentialProvider") as mock_provider_class, \
             patch("app.providers.dependencies.az.redis_client_factory.RedisClientFactory.create_client") as mock_parent_create:

            # Setup Azure config with passwordless enabled
            mock_azure_config = MagicMock()
            mock_azure_config.redis_use_passwordless_auth = True
            mock_get_provider.return_value = mock_azure_config

            # Mock credential provider that fails
            mock_provider = AsyncMock()
            mock_provider.get_credentials = AsyncMock(return_value=None)
            mock_provider_class.return_value = mock_provider

            mock_redis = AsyncMock()
            mock_parent_create.return_value = mock_redis

            config = RedisCacheConfig()
            factory = AzureRedisClientFactory(config, use_index_database=False)
            client = await factory.create_client()

            # Should fall back to parent implementation
            mock_parent_create.assert_called_once()
            assert client == mock_redis