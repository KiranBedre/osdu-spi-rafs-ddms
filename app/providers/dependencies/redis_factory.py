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

"""Provider-specific Redis factory resolver."""

from app.core.helpers.cache.config import RedisCacheConfig
from app.core.helpers.cache.redis_client_factory import RedisClientFactory
from app.core.settings.app import AppSettings
from app.providers.dependencies.az.redis_client_factory import AzureRedisClientFactory


def get_redis_factory(
    settings: AppSettings,
    use_index_database: bool = False,
) -> RedisClientFactory:
    """Get the appropriate Redis client factory based on cloud provider.

    This function returns provider-specific factories that can implement
    custom authentication.

    :param AppSettings settings: Application settings containing cloud_provider
    :param bool use_index_database: If True, use index database; otherwise use main database
    :return: Redis client factory instance
    :rtype: RedisClientFactory
    """
    config = RedisCacheConfig()

    if settings.cloud_provider == "azure":
        return AzureRedisClientFactory(config, use_index_database)
    # Default to base factory for other providers
    return RedisClientFactory(config, use_index_database)
