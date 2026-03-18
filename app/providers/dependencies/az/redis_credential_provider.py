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

"""Redis credential provider for Azure Entra ID with automatic token refresh."""

from typing import Tuple

from azure.identity import DefaultAzureCredential
from loguru import logger
from redis.credentials import CredentialProvider

from app.providers.config import AzureConfig
from app.providers.dependencies.az.redis_auth import extract_oid_from_token


class AzureRedisCredentialProvider(CredentialProvider):
    """Credential provider for Azure Redis with Entra ID authentication.

    Implements redis-py's CredentialProvider interface to support automatic
    token refresh when credentials expire. Uses synchronous Azure Identity
    as required by the CredentialProvider interface.
    """

    def __init__(self, config: AzureConfig = None):
        """Initialize the Azure Redis credential provider.

        :param config: Azure configuration object, defaults to AzureConfig()
        :type config: AzureConfig, optional
        """
        self._credential = DefaultAzureCredential()
        self._config = config or AzureConfig()

    def get_credentials(self) -> Tuple[str, str]:
        """Get current credentials (username, password) for Redis authentication.

        This method is called by redis-py to get credentials initially and
        whenever re-authentication is needed (e.g., token expiration).

        NOTE: This must be synchronous as required by redis.credentials.CredentialProvider.

        :return: Tuple of (username, password) where username is the OID and password is the token
        :rtype: Tuple[str, str]
        :raises: Exception if credentials cannot be obtained
        """
        try:
            # Get token from Azure using synchronous credential
            token_response = self._credential.get_token(self._config.redis_auth_token_scope)
            token = token_response.token

            # Extract OID from JWT token using shared utility
            username = extract_oid_from_token(token)
            if not username:
                raise ValueError("No OID claim found in token")

            oid_prefix = username[:8]
            logger.debug(f"Obtained Entra credentials for Redis (OID: {oid_prefix}...)")
            return (username, token)

        except Exception as exc:  # noqa: B902
            logger.error(f"Failed to obtain Entra credentials for Redis: {exc}")
            raise RuntimeError(f"Unable to obtain Azure Entra credentials: {exc}")

    def __del__(self):  # noqa: WPS603
        """Clean up resources when provider is garbage collected."""
        if hasattr(self, "_credential") and self._credential:  # noqa: WPS421
            self._credential.close()
