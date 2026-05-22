#  Copyright 2024 ExxonMobil Technology and Engineering Company
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

import hashlib
from typing import Callable, Optional

from async_lru import alru_cache

# Pylint cannot always resolve Azure namespace packages in static analysis.
# pylint: disable=no-name-in-module
from azure.identity.aio import DefaultAzureCredential
from azure.keyvault.secrets.aio import SecretClient
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache
from pydantic import BaseSettings

from app.core.config import AppSettings
from app.core.helpers.cache.settings import (
    STORAGE_ACCOUNT_INFO_CACHE_DEFAULT_TTL,
)
from app.services.osdu_clients.partition_client import (
    PartitionServiceApiClient,
)

STORAGE_ACCOUNT_BLOB_ENDPOINT = "storage-account-blob-endpoint"


def storage_account_key_builder(
    func: Callable,
    namespace: Optional[str] = "",
    request=None,
    response=None,
    args: Optional[tuple] = None,
    kwargs: Optional[dict] = None,
) -> str:
    """Custom key builder that includes data_partition_id from instance."""
    func_meta = f"{func.__module__}:{func.__name__}"
    prefix = f"{FastAPICache.get_prefix()}:{namespace}"

    # Extract partition_id from self (args[0])
    partition_id = ""
    if args:
        partition_id = getattr(args[0], "_data_partition_id", "")

    cache_meta = f"partition:{partition_id}"
    hash_key = hashlib.sha256(f"{func_meta}:{cache_meta}".encode()).hexdigest()

    return f"{prefix}:{hash_key}"


class AzureStorageAccountInfo(object):

    def __init__(
        self,
        data_partition_id: str,
        settings: AppSettings,
        cloud_provider_config: BaseSettings,
    ):
        self._credential = None
        self._data_partition_id = data_partition_id
        self._settings = settings
        self._cloud_provider_config = cloud_provider_config

    async def __aenter__(self):  # noqa: ASYNC910
        self._credential = DefaultAzureCredential()
        return self  # noqa: ASYNC910

    async def __aexit__(self, exc_type, exc_val, exc_tb):  # noqa: ASYNC102
        await self._credential.close()  # noqa: ASYNC102

    @alru_cache
    @cache(expire=STORAGE_ACCOUNT_INFO_CACHE_DEFAULT_TTL, key_builder=storage_account_key_builder)
    async def get_info(self) -> dict:

        if self._cloud_provider_config.az_use_partition_service:
            async with SecretClient(self._cloud_provider_config.az_keyvault_url, self._credential) as sc_client:
                aad_client_id = await sc_client.get_secret(self._cloud_provider_config.az_aad_client_id_key)
                access_token = await self._credential.get_token(f"{aad_client_id.value}/.default")
                partition_client = PartitionServiceApiClient(
                    base_url=self._settings.service_host_partition,
                    data_partition_id=self._data_partition_id,
                    bearer_token=access_token.token,
                )
                partition_info = await partition_client.get_partition_info(self._data_partition_id)
        else:
            partition_info = {
                STORAGE_ACCOUNT_BLOB_ENDPOINT: {
                    "value": f"{self._data_partition_id}-{STORAGE_ACCOUNT_BLOB_ENDPOINT}",
                },
            }

        async with SecretClient(self._cloud_provider_config.az_keyvault_url, self._credential) as kv_client:
            blob_endpoint = await kv_client.get_secret(partition_info[STORAGE_ACCOUNT_BLOB_ENDPOINT]["value"])

        return {
            "container_name": self._cloud_provider_config.az_container_name,
            STORAGE_ACCOUNT_BLOB_ENDPOINT: blob_endpoint.value,
        }
