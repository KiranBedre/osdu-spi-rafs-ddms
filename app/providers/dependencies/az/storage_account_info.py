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

from async_lru import alru_cache
from azure.identity.aio import DefaultAzureCredential
from azure.keyvault.secrets.aio import SecretClient
from fastapi_cache.decorator import cache
from pydantic import BaseSettings

from app.core.config import AppSettings
from app.core.helpers.cache.key_builder import key_builder_for_service_methods
from app.core.helpers.cache.settings import (
    STORAGE_ACCOUNT_INFO_CACHE_DEFAULT_TTL,
)
from app.services.osdu_clients.partition_client import (
    PartitionServiceApiClient,
)

STORAGE_ACCOUNT_NAME = "storage-account-name"


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

    async def __aenter__(self):
        self._credential = DefaultAzureCredential()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._credential.close()

    @alru_cache
    @cache(expire=STORAGE_ACCOUNT_INFO_CACHE_DEFAULT_TTL, key_builder=key_builder_for_service_methods)
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
                STORAGE_ACCOUNT_NAME: {
                    "value": f"{self._data_partition_id}-storage",
                },
            }

        async with SecretClient(self._cloud_provider_config.az_keyvault_url, self._credential) as kv_client:
            account_name = await kv_client.get_secret(partition_info[STORAGE_ACCOUNT_NAME]["value"])

        return {
            STORAGE_ACCOUNT_NAME: account_name.value,
            "container_name": self._cloud_provider_config.az_container_name,
        }
