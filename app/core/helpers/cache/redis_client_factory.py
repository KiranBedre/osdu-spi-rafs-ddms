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

"""Base Redis client factory with default implementation."""

import asyncio

from loguru import logger
from redis.asyncio.client import Redis
from redis.exceptions import (
    AuthenticationError,
    ConnectionError,
    ResponseError,
    TimeoutError,
)

from app.core.helpers.cache.config import RedisCacheConfig

WAIT_FOR_REDIS = 5  # in seconds


class RedisClientFactory(object):
    """Base Redis client factory with default password authentication.

    This class provides the base implementation using password authentication.
    Provider-specific subclasses can override create_client() to implement
    custom authentication methods.
    """

    def __init__(self, config: RedisCacheConfig, use_index_database: bool = False):
        """Initialize the factory.

        :param RedisCacheConfig config: Redis cache configuration
        :param bool use_index_database: If True, use index database; otherwise use main database
        """
        self.config = config
        self.use_index_database = use_index_database

    def get_key_prefix(self) -> str:
        """Return key prefix for namespace isolation.

        Base implementation returns an empty string (no prefix).
        Subclasses may override this when the server does not support
        multiple logical databases.

        :return: Key prefix string, empty means no prefix applied
        :rtype: str
        """
        return ""

    async def create_client(self) -> Redis:
        """Create Redis client with password authentication.

        Uses password from settings for authentication.
        Retries on connection failures with a fixed delay.

        :return: Connected Redis client
        :rtype: Redis
        """
        while True:
            try:
                hostname = self._get_hostname()
                redis_client = Redis(
                    host=hostname,
                    port=self.config.redis_port,
                    password=self.config.redis_password,
                    db=self._get_database(),
                    ssl=self.config.redis_ssl,
                )
                await redis_client.ping()
                logger.debug("Redis client connected successfully")
                return redis_client
            except (AuthenticationError, ConnectionError, ResponseError, TimeoutError) as exc:  # noqa: WPS239
                exc_msg = str(exc)
                error_msg = f"Redis client error: {exc_msg}"
                logger.error(error_msg)
                await asyncio.sleep(WAIT_FOR_REDIS)

    def _get_hostname(self) -> str:
        """Return the configured Redis hostname.

        :return: Stripped hostname string
        :rtype: str
        :raises ValueError: if ``redis_hostname`` is not set or blank
        """
        hostname = self.config.redis_hostname.strip() if self.config.redis_hostname else ""
        if not hostname:
            raise ValueError("Redis hostname is not configured, can't create Redis client.")
        return hostname

    def _get_database(self) -> int:
        """Determine the Redis database number to use.

        :return: Database number based on use_index_database flag
        :rtype: int
        """
        return self.config.redis_index_database if self.use_index_database else self.config.redis_database
