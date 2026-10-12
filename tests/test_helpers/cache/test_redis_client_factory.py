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

"""Tests for the base RedisClientFactory."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from redis.exceptions import ConnectionError

from app.core.helpers.cache.config import RedisCacheConfig
from app.core.helpers.cache.redis_client_factory import RedisClientFactory


def _make_config(**overrides) -> RedisCacheConfig:
    """Return a RedisCacheConfig with test-friendly defaults."""
    defaults = dict(
        redis_hostname="localhost",
        redis_port=6380,
        redis_password="secret",
        redis_database=13,
        redis_index_database=0,
        redis_ssl=False,
    )
    defaults.update(overrides)
    return RedisCacheConfig(**defaults)


def test_redis_password_uses_the_standard_environment_key(monkeypatch):
    monkeypatch.setenv("REDIS_PASSWORD", "stack-secret")

    assert RedisCacheConfig().redis_password == "stack-secret"


class TestRedisClientFactoryGetDatabase:
    """Tests for _get_database()."""

    def test_returns_main_database_when_flag_false(self):
        config = _make_config(redis_database=13, redis_index_database=0)
        factory = RedisClientFactory(config, use_index_database=False)
        assert int(factory._get_database()) == 13

    def test_returns_index_database_when_flag_true(self):
        config = _make_config(redis_database=13, redis_index_database=0)
        factory = RedisClientFactory(config, use_index_database=True)
        assert factory._get_database() == 0


class TestRedisClientFactoryGetKeyPrefix:
    """Tests for get_key_prefix()."""

    def test_always_returns_empty_string(self):
        factory = RedisClientFactory(_make_config())
        assert factory.get_key_prefix() == ""

    def test_returns_empty_string_for_index_connection(self):
        factory = RedisClientFactory(_make_config(), use_index_database=True)
        assert factory.get_key_prefix() == ""


class TestRedisClientFactoryCreateClient:
    """Tests for create_client()."""

    @pytest.mark.asyncio
    async def test_create_client_returns_redis_on_success(self):
        config = _make_config()
        factory = RedisClientFactory(config)

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)

        with patch("app.core.helpers.cache.redis_client_factory.Redis", return_value=mock_redis):
            client = await factory.create_client()

        assert client is mock_redis
        mock_redis.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_client_retries_on_connection_error(self):
        """After a ConnectionError the factory should sleep and retry."""
        config = _make_config()
        factory = RedisClientFactory(config)

        # First call raises; second call succeeds
        mock_redis_fail = AsyncMock()
        mock_redis_fail.ping = AsyncMock(side_effect=ConnectionError("timeout"))

        mock_redis_ok = AsyncMock()
        mock_redis_ok.ping = AsyncMock(return_value=True)

        redis_instances = iter([mock_redis_fail, mock_redis_ok])

        with patch(
            "app.core.helpers.cache.redis_client_factory.Redis", side_effect=lambda **_: next(redis_instances)
        ), patch("app.core.helpers.cache.redis_client_factory.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            client = await factory.create_client()

        mock_sleep.assert_called_once()
        assert client is mock_redis_ok
