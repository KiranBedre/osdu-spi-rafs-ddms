#  Copyright 2023 ExxonMobil Technology and Engineering Company
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
    ResponseError,
)

from app.core.helpers.cache.backends.redis_cache import RedisCacheBackend
from app.core.helpers.cache.errors import CacheBackendError


@pytest.mark.parametrize(
    "error", (
        AuthenticationError,
        ConnectionError,
        ResponseError,
    ),
)
@pytest.mark.asyncio
async def test_validate_redis_settings(error):
    redis_mock = AsyncMock()
    redis_mock.ping.side_effect = error
    with pytest.raises(CacheBackendError):
        await RedisCacheBackend()._validate_redis_settings(redis_mock)


@pytest.mark.asyncio
@patch.object(RedisCacheBackend, "_validate_redis_settings")
@patch("app.core.helpers.cache.backends.redis_cache.Redis")
async def test_get_backend(redis_class_mock, mock_validate_redis_settings):
    redis_instance_mock = AsyncMock()
    redis_class_mock.return_value = redis_instance_mock

    backend_instance = RedisCacheBackend()
    await backend_instance.get_backend()

    mock_validate_redis_settings.assert_called_once_with(redis_instance_mock)
