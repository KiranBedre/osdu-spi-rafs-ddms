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

from unittest.mock import AsyncMock, patch

import pytest
from redis.exceptions import (
    AuthenticationError,
    ConnectionError,
    ResponseError
)

from app.core.helpers.cache.backends.redis_cache import RedisCacheBackend
from app.core.helpers.cache.errors import CacheBackendError


@pytest.mark.parametrize(
    "error", (
        AuthenticationError,
        ConnectionError,
        ResponseError
    )
)
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
