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

from typing import Optional

from fastapi_cache.backends.redis import RedisBackend
from loguru import logger
from redis.asyncio.client import Redis
from redis.exceptions import (
    AuthenticationError,
    ConnectionError,
    ResponseError,
)

from app.core.config import get_app_settings
from app.core.helpers.cache.backends.base_cache import BaseCacheBackend
from app.core.helpers.cache.errors import CacheBackendError
from app.providers.dependencies.redis_factory import get_redis_factory


class LoggingRedisBackend(RedisBackend):
    """Redis backend with logging for cache hits and misses."""

    async def get(self, key: str) -> Optional[bytes]:
        """Get value from cache with logging.

        :param str key: cache key
        :return Optional[bytes]: cached value or None
        """
        cached_data = await super().get(key)
        if cached_data is not None:
            logger.debug(f"Cache HIT for key: {key}")
        else:
            logger.debug(f"Cache MISS for key: {key}")
        return cached_data

    async def get_with_ttl(self, key: str) -> tuple:
        """Get value and TTL from cache with logging.

        :param str key: cache key
        :return tuple: (ttl, value) where ttl is time-to-live in seconds and value is cached data
        """
        ttl, cached_data = await super().get_with_ttl(key)

        if cached_data is not None:
            logger.debug(f"Cache HIT for key: {key}, TTL: {ttl}s")
        else:
            logger.debug(f"Cache MISS for key: {key}")

        return ttl, cached_data

    async def set(self, key: str, value: bytes, expire: Optional[int] = None) -> None:  # noqa: WPS110
        """Set value in cache with logging.

        :param str key: cache key
        :param bytes value: value to cache
        :param Optional[int] expire: expiration time in seconds
        """
        await super().set(key, value, expire)
        logger.debug(f"Cache SET for key: {key}, expire: {expire}s")

    async def clear(self, namespace: Optional[str] = None, key: Optional[str] = None) -> int:
        """Clear cache entries with logging.

        :param Optional[str] namespace: namespace to clear
        :param Optional[str] key: specific key to clear
        :return int: number of keys deleted
        """
        deleted_count = await super().clear(namespace, key)
        logger.debug(f"Cache CLEAR: deleted {deleted_count} keys (namespace={namespace}, key={key})")
        return deleted_count


class RedisCacheBackend(BaseCacheBackend):
    """Redis cache backend that uses the provider-specific Redis client factory.

    This backend integrates with the Redis client factory system, allowing
    provider-specific authentication to be used transparently with fastapi-cache2.
    """

    async def get_backend(self) -> LoggingRedisBackend:
        """Init and return instance of LoggingRedisBackend with cache hit/miss logging.

        Uses the provider-specific Redis client factory to create a client with appropriate authentication.

        :return LoggingRedisBackend: instance of LoggingRedisBackend with provider-specific client
        """
        # Get app settings
        settings = get_app_settings()

        # Get the provider-specific factory
        factory = get_redis_factory(settings, use_index_database=False)

        # Create the Redis client (with provider-specific auth)
        redis_client = await factory.create_client()

        # Validate the connection
        await self._validate_redis_connection(redis_client)

        logger.info("Redis cache backend initialized with provider-specific client")
        return LoggingRedisBackend(redis_client)

    async def _validate_redis_connection(self, redis_client: Redis) -> None:
        """Validate Redis connection by pinging the server.

        :param Redis redis_client: redis instance
        :raises:
          AuthenticationError: for wrong password
          ConnectionError: for wrong host or port
          ResponseError: for wrong db
        """
        try:
            logger.debug("Validating Redis connection...")
            await redis_client.ping()
        except (AuthenticationError, ConnectionError, ResponseError):
            raise CacheBackendError("Redis client can't be init. Redis host, port, password or db are wrong")
