#  Copyright 2026 ExxonMobil Technology and Engineering Company
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

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from redis.exceptions import AuthenticationError, ConnectionError, ResponseError

from app.core.helpers.cache.backends.redis_cache import RedisCacheBackend
from app.core.helpers.cache.errors import CacheBackendError


@pytest.mark.parametrize("error", (AuthenticationError, ConnectionError, ResponseError))
@pytest.mark.asyncio
async def test_validate_redis_connection(error):
    redis_mock = AsyncMock()
    redis_mock.ping.side_effect = error
    with pytest.raises(CacheBackendError):
        await RedisCacheBackend()._validate_redis_connection(redis_mock)


@pytest.mark.asyncio
@patch("app.core.helpers.cache.backends.redis_cache.get_redis_factory")
async def test_get_backend(mock_get_redis_factory):
    """Test that get_backend creates a Redis client and validates the connection."""
    # Setup mocks
    mock_redis_client = AsyncMock()
    mock_factory = AsyncMock()
    mock_factory.create_client.return_value = mock_redis_client
    mock_factory.get_key_prefix = MagicMock(return_value="")
    mock_get_redis_factory.return_value = mock_factory

    # Create backend and get the fastapi-cache backend
    backend = RedisCacheBackend()
    result = await backend.get_backend()

    # Verify the factory was called correctly
    assert mock_get_redis_factory.call_count == 1
    call_args = mock_get_redis_factory.call_args
    assert call_args.kwargs["use_index_database"] is False
    mock_factory.create_client.assert_called_once()

    # Verify ping was called for validation
    mock_redis_client.ping.assert_called_once()


@pytest.mark.asyncio
@patch("app.core.helpers.cache.backends.redis_cache.get_redis_factory")
async def test_get_backend_passes_key_prefix_to_logging_backend(mock_get_redis_factory):
    """Test that get_backend wires the factory key prefix into LoggingRedisBackend."""
    mock_redis_client = AsyncMock()
    mock_factory = AsyncMock()
    mock_factory.create_client.return_value = mock_redis_client
    mock_factory.get_key_prefix = MagicMock(return_value="db13:")
    mock_get_redis_factory.return_value = mock_factory

    backend = RedisCacheBackend()
    result = await backend.get_backend()

    mock_factory.get_key_prefix.assert_called_once()
    assert result._key_prefix == "db13:"


@pytest.mark.asyncio
@patch("app.core.helpers.cache.backends.redis_cache.get_redis_factory")
async def test_get_backend_with_empty_prefix(mock_get_redis_factory):
    """Test that an empty prefix from the factory results in no prefix on the backend."""
    mock_redis_client = AsyncMock()
    mock_factory = AsyncMock()
    mock_factory.create_client.return_value = mock_redis_client
    mock_factory.get_key_prefix = MagicMock(return_value="")
    mock_get_redis_factory.return_value = mock_factory

    backend = RedisCacheBackend()
    result = await backend.get_backend()

    assert result._key_prefix == ""


@pytest.mark.asyncio
@patch("app.core.helpers.cache.backends.redis_cache.get_redis_factory")
async def test_clear_with_namespace(mock_get_redis_factory):
    """Test that clear(namespace=...) correctly applies the key prefix."""
    mock_redis_client = AsyncMock()
    mock_factory = AsyncMock()
    mock_factory.create_client.return_value = mock_redis_client
    mock_factory.get_key_prefix = MagicMock(return_value="db13:")
    mock_get_redis_factory.return_value = mock_factory

    backend = RedisCacheBackend()
    logging_backend = await backend.get_backend()

    # Mock the parent's clear method to capture what namespace it receives
    with patch("fastapi_cache.backends.redis.RedisBackend.clear", new_callable=AsyncMock) as mock_parent_clear:
        mock_parent_clear.return_value = 5

        # Clear with a namespace - should prefix the namespace
        result = await logging_backend.clear(namespace="myns")

        # Verify that the parent clear was called with the prefixed namespace "db13:myns"
        # The parent RedisBackend.clear() will convert this to the pattern "db13:myns:*"
        mock_parent_clear.assert_called_once_with("db13:myns", None)
        assert result == 5
