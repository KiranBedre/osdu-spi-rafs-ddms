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

"""Azure-specific Redis client factory with Entra ID authentication."""

from loguru import logger
from azure.identity.aio import DefaultAzureCredential
from azure.keyvault.secrets.aio import SecretClient
from redis.asyncio import Redis
from redis.asyncio.connection import ConnectionPool, SSLConnection

from app.core.config import get_provider_config
from app.core.helpers.cache.config import RedisCacheConfig
from app.core.helpers.cache.redis_client_factory import RedisClientFactory
from app.providers.config import AzureConfig
from app.providers.dependencies.az.redis_credential_provider import AzureRedisCredentialProvider

# Azure Managed Redis uses port 10000 and only supports a single logical database (db=0).
# Azure Cache for Redis uses port 6380 and supports multiple logical databases.
AZURE_MANAGED_REDIS_PORT = 10000


class AzureRedisClientFactory(RedisClientFactory):
    """Azure-specific Redis client factory with Entra ID authentication.

    Overrides create_client() to use credential provider for automatic
    token refresh. Falls back to password authentication if Entra auth
    is disabled or fails.
    """

    def __init__(self, config: RedisCacheConfig, use_index_database: bool = False):
        """Initialize the Azure factory.

        :param RedisCacheConfig config: Redis cache configuration
        :param bool use_index_database: If True, use index database; otherwise use main database
        """
        super().__init__(config, use_index_database)
        self.azure_config = get_provider_config()

    def get_key_prefix(self) -> str:
        """Return a key prefix to simulate namespace isolation on AMR.

        When using AMR with a non-zero cache database, keys are prefixed with
        ``db{n}:`` (e.g. ``db13:``) to avoid collisions in the single shared
        key-space. The index database connection is never prefixed.

        :return: Prefix string, or empty string if not needed
        :rtype: str
        """
        if self._is_amr and not self.use_index_database:
            db_num = self.config.redis_database
            return f"db{db_num}:"
        return ""

    async def create_client(self) -> Redis:
        """Create Redis client with Entra credential provider for auto-refresh.

        Overrides base implementation to use AzureRedisCredentialProvider which
        automatically refreshes tokens before expiration.

        :return: Configured Redis client instance
        :rtype: Redis
        """
        # Check if passwordless auth is enabled
        if not (isinstance(self.azure_config, AzureConfig) and self.azure_config.redis_use_passwordless_auth):
            logger.debug("Redis passwordless auth disabled, using password authentication")
            return await super().create_client()

        try:
            # Use credential provider for auto-refresh
            credential_provider = AzureRedisCredentialProvider(self.azure_config)
            logger.info("Using Azure Entra credential provider for Redis (auto-refresh enabled)")

            # Get SSL connection configuration
            connection_class, connection_kwargs = self._get_ssl_connection_params()

            # Build pool parameters using credential provider
            # The credential_provider will be called automatically by Redis when needed.
            # No username/password needed
            pool_params = await self._build_pool_params(credential_provider, connection_class, connection_kwargs)
            pool = ConnectionPool(**pool_params)

            return Redis(connection_pool=pool)

        except Exception as exc:  # noqa: B902
            logger.error(f"Error setting up Entra auth, falling back to password: {exc}")
            return await super().create_client()

    @property
    def _is_amr(self) -> bool:
        """Return True if the configured port indicates Azure Managed Redis.

        :rtype: bool
        """
        return self.config.redis_port == AZURE_MANAGED_REDIS_PORT

    def _get_database(self) -> int:
        """Return 0 for AMR (single-database constraint), or delegate to base.

        :rtype: int
        """
        if self._is_amr:
            return 0
        return super()._get_database()

    def _get_ssl_connection_params(self):
        """Get SSL connection parameters based on configuration.

        :return: Tuple of (connection_class, connection_kwargs)
        """
        if self.config.redis_ssl:
            # Use SSLConnection class for SSL/TLS connections
            return SSLConnection, {
                "ssl_cert_reqs": "none",  # Azure Redis uses managed certificates
                "ssl_check_hostname": False,
            }
        # Use default Connection class (will be set by ConnectionPool)
        return None, {}

    async def _resolve_redis_hostname(self) -> str:
        """Return the Redis hostname, fetching it from AKV when not configured.

        Reads ``config.redis_hostname`` first.  If it is ``None`` or blank the
        method falls back to Azure Key Vault using the secret named by
        ``azure_config.redis_hostname_secret_name`` (default ``"redis-hostname"``).

        :return: Resolved Redis hostname
        :rtype: str
        :raises ValueError: if hostname is absent and AKV is not configured
        """
        try:
            return self._get_hostname()
        except ValueError:
            pass

        if not isinstance(self.azure_config, AzureConfig) or not self.azure_config.az_keyvault_url:
            raise ValueError(
                "Redis hostname is not set and az_keyvault_url is not configured for AKV fallback.",
            )

        secret_name = self.azure_config.redis_hostname_secret_name
        akv_url = self.azure_config.az_keyvault_url
        logger.info(f"Redis hostname not configured — fetching '{secret_name}' from AKV: {akv_url}")
        async with DefaultAzureCredential() as credential:
            async with SecretClient(
                vault_url=akv_url,
                credential=credential,
            ) as kv_client:
                secret = await kv_client.get_secret(secret_name)
                hostname = secret.value
                logger.info(f"Resolved Redis hostname from AKV: {hostname}")
                return hostname

    async def _build_pool_params(self, credential_provider, connection_class, connection_kwargs):
        """Build connection pool parameters.

        Resolves the Redis hostname (from config or AKV) before building the parameters.

        :param credential_provider: Azure Redis credential provider instance
        :param connection_class: Connection class to use (or None for default)
        :param connection_kwargs: Additional connection keyword arguments
        :return: Dictionary of pool parameters
        """

        hostname = await self._resolve_redis_hostname()
        pool_params = {
            "host": hostname,
            "port": self.config.redis_port,
            "db": self._get_database(),
            "credential_provider": credential_provider,
            "decode_responses": False,
            "socket_connect_timeout": self.azure_config.redis_socket_connect_timeout,
            "socket_keepalive": self.azure_config.redis_socket_keepalive,
            "health_check_interval": self.azure_config.redis_health_check_interval,
            **connection_kwargs,
        }

        if connection_class:
            pool_params["connection_class"] = connection_class

        return pool_params
