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
from app.providers.config import AzureConfig
from app.providers.dependencies.az.redis_client_factory import (
    AZURE_MANAGED_REDIS_PORT,
    AzureRedisClientFactory,
)

AMR_PORT = AZURE_MANAGED_REDIS_PORT  # 10000
ACR_PORT = 6380

def _make_config(**overrides) -> RedisCacheConfig:
    """Return a RedisCacheConfig with test-friendly defaults."""
    defaults = dict(
        redis_hostname="myredis.redis.cache.windows.net",
        redis_port=ACR_PORT,
        redis_password=None,
        redis_database=13,
        redis_index_database=0,
        redis_ssl=True,
    )
    defaults.update(overrides)
    return RedisCacheConfig(**defaults)

def _make_factory(port=ACR_PORT, use_index_database=False, redis_database=13) -> AzureRedisClientFactory:
    """Return an AzureRedisClientFactory with a mocked azure_config."""
    config = _make_config(redis_port=port, redis_database=redis_database)
    with patch("app.providers.dependencies.az.redis_client_factory.get_provider_config"):
        factory = AzureRedisClientFactory(config, use_index_database=use_index_database)
    return factory

class TestAzureRedisClientFactoryIsAmr:
    """Tests for the _is_amr property."""

    def test_is_amr_true_for_amr_port(self):
        assert _make_factory(port=AMR_PORT)._is_amr is True

    def test_is_amr_false_for_acr_port(self):
        assert _make_factory(port=ACR_PORT)._is_amr is False

    def test_is_amr_false_for_arbitrary_port(self):
        assert _make_factory(port=6379)._is_amr is False


class TestAzureRedisClientFactoryGetDatabase:
    """Tests for the _get_database() override."""

    def test_amr_cache_connection_always_returns_zero(self):
        """AMR only supports db=0, even when redis_database is non-zero."""
        factory = _make_factory(port=AMR_PORT, use_index_database=False, redis_database=13)
        assert factory._get_database() == 0

    def test_amr_index_connection_returns_zero(self):
        """AMR index connection also returns 0 (the only valid database)."""
        factory = _make_factory(port=AMR_PORT, use_index_database=True, redis_database=13)
        assert factory._get_database() == 0

    def test_acr_cache_connection_delegates_to_base(self):
        """ACR cache connection should use redis_database from config."""
        factory = _make_factory(port=ACR_PORT, use_index_database=False, redis_database=13)
        assert int(factory._get_database()) == 13

    def test_acr_index_connection_delegates_to_base(self):
        """ACR index connection should use redis_index_database from config."""
        factory = _make_factory(port=ACR_PORT, use_index_database=True)
        # redis_index_database defaults to 0
        assert factory._get_database() == 0


class TestAzureRedisClientFactoryGetKeyPrefix:
    """Tests for the get_key_prefix() override."""

    def test_amr_cache_connection_returns_db_prefix(self):
        """AMR cache connection should return 'db{n}:' prefix."""
        factory = _make_factory(port=AMR_PORT, use_index_database=False, redis_database=13)
        assert factory.get_key_prefix() == "db13:"

    def test_amr_index_connection_returns_empty_prefix(self):
        """AMR index connection must NOT be prefixed (RediSearch scans by key prefix)."""
        factory = _make_factory(port=AMR_PORT, use_index_database=True, redis_database=13)
        assert factory.get_key_prefix() == ""

    def test_acr_cache_connection_returns_empty_prefix(self):
        """ACR uses logical databases natively; no prefix needed."""
        factory = _make_factory(port=ACR_PORT, use_index_database=False, redis_database=13)
        assert factory.get_key_prefix() == ""

    def test_acr_index_connection_returns_empty_prefix(self):
        factory = _make_factory(port=ACR_PORT, use_index_database=True)
        assert factory.get_key_prefix() == ""


class TestAzureRedisClientFactory:
    """Test cases for AzureRedisClientFactory."""

    @pytest.mark.asyncio
    async def test_create_client_with_passwordless_auth_disabled_uses_password(self):
        """Test that create_client() uses password auth when passwordless disabled."""
        azure_config = AzureConfig(redis_use_passwordless_auth=False)

        with patch("app.providers.dependencies.az.redis_client_factory.get_provider_config", return_value=azure_config), \
             patch("app.providers.dependencies.az.redis_client_factory.RedisClientFactory.create_client") as mock_parent_create:

            mock_redis = AsyncMock()
            mock_parent_create.return_value = mock_redis

            config = RedisCacheConfig()
            factory = AzureRedisClientFactory(config, use_index_database=False)
            client = await factory.create_client()

            mock_parent_create.assert_called_once()
            assert client == mock_redis

    @pytest.mark.asyncio
    async def test_create_client_with_entra_auth_success(self):
        """Test that create_client() builds a connection pool when Entra auth succeeds."""
        azure_config = AzureConfig(redis_use_passwordless_auth=True)

        with patch("app.providers.dependencies.az.redis_client_factory.get_provider_config", return_value=azure_config), \
             patch("app.providers.dependencies.az.redis_client_factory.AzureRedisCredentialProvider") as mock_provider_class, \
             patch("app.providers.dependencies.az.redis_client_factory.ConnectionPool") as mock_pool_class, \
             patch("app.providers.dependencies.az.redis_client_factory.Redis") as mock_redis_class:

            mock_credential_provider = MagicMock()
            mock_provider_class.return_value = mock_credential_provider

            mock_pool = MagicMock()
            mock_pool_class.return_value = mock_pool

            mock_redis = MagicMock()
            mock_redis_class.return_value = mock_redis

            config = _make_config(redis_port=ACR_PORT, redis_ssl=False)
            factory = AzureRedisClientFactory(config, use_index_database=False)
            client = await factory.create_client()

        # Connection pool should be created with the credential provider
        mock_pool_class.assert_called_once()
        pool_kwargs = mock_pool_class.call_args.kwargs
        assert pool_kwargs["credential_provider"] is mock_credential_provider
        assert pool_kwargs["host"] == config.redis_hostname
        assert pool_kwargs["port"] == config.redis_port
        assert int(pool_kwargs["db"]) == 13

        mock_redis_class.assert_called_once_with(connection_pool=mock_pool)
        assert client is mock_redis

    @pytest.mark.asyncio
    async def test_create_client_falls_back_to_password_on_entra_exception(self):
        """Test that create_client() falls back to password when an exception is raised in the Entra path."""
        azure_config = AzureConfig(redis_use_passwordless_auth=True)

        mock_redis = AsyncMock()

        with patch("app.providers.dependencies.az.redis_client_factory.get_provider_config", return_value=azure_config), \
             patch("app.providers.dependencies.az.redis_client_factory.AzureRedisCredentialProvider", side_effect=Exception("token error")), \
             patch("app.providers.dependencies.az.redis_client_factory.RedisClientFactory.create_client", return_value=mock_redis) as mock_parent_create:

            config = _make_config(redis_port=ACR_PORT)
            factory = AzureRedisClientFactory(config, use_index_database=False)
            client = await factory.create_client()

        mock_parent_create.assert_called_once()
        assert client is mock_redis