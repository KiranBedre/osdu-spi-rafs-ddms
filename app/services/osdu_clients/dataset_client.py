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

from typing import List, NamedTuple

import httpx
from loguru import logger

from app.resources.common_headers import (
    AUTHORIZATION,
    CONTENT_TYPE,
    DATA_PARTITION_ID,
)
from app.services.osdu_clients.conf import DEFAULT_RETRIES, TIMEOUT


class DatasetServicePaths(NamedTuple):
    REGISTER_DATASET = "/registerDataset"
    GET_STORAGE_INSTRUCTIONS = "/getStorageInstructions"
    STORAGE_INSTRUCTIONS = "/storageInstructions"
    RETRIEVAL_INSTRUCTIONS = "/retrievalInstructions"
    GET_DATASET_REGISTRY = "/getDatasetRegistry"


class DatasetServiceApiClient(object):

    def __init__(
        self,
        base_url: str,
        *,
        data_partition_id: str = None,
        bearer_token: str = None,
        extra_headers: dict = None,
    ) -> None:
        self.base_url = base_url
        self.headers = {
            CONTENT_TYPE: "application/json",
            DATA_PARTITION_ID: data_partition_id,
            AUTHORIZATION: f"Bearer {bearer_token}",
            **(extra_headers or {}),
        }
        self.name = "DatasetService"

    def add_headers(self, headers: dict) -> None:
        """Add headers.

        :param headers: headers
        :type headers: dict
        """
        self.headers = {**self.headers, **headers}

    async def storage_instructions(self, kind_subtype: str) -> dict:
        """Get storage instructions for file uploading.

        :param kind_subtype: kind subtype
        :type kind_subtype: str
        :return: instructions with unsigned and signed URL for the
            uploading file
        :rtype: dict
        """
        async with httpx.AsyncClient(
            base_url=self.base_url, headers=self.headers, timeout=TIMEOUT, transport=self._transport(),
        ) as client:
            q_params = {"kindSubType": kind_subtype}
            response = await client.post(
                DatasetServicePaths.STORAGE_INSTRUCTIONS, headers=self.headers, params=q_params,
            )
            logger.debug(f"{self.name}: storage instructions response: {response}")
            response.raise_for_status()
            return response.json()

    async def get_storage_instructions(self, kind_subtype: str) -> dict:
        """Get storage instructions for file uploading.

        :param kind_subtype: kind subtype
        :type kind_subtype: str
        :return: instructions with unsigned and signed URL for the
            uploading file
        :rtype: dict
        """
        async with httpx.AsyncClient(
            base_url=self.base_url, headers=self.headers, timeout=TIMEOUT, transport=self._transport(),
        ) as client:
            q_params = {"kindSubType": kind_subtype}
            response = await client.get(
                DatasetServicePaths.GET_STORAGE_INSTRUCTIONS, headers=self.headers, params=q_params,
            )
            logger.debug(f"{self.name}: get storage instructions response: {response}")
            response.raise_for_status()
            return response.json()

    async def retrieval_instructions(self, dataset_ids: List[str]) -> dict:
        """Get retrieval instructions for a list of datasets to download.

        :param dataset_ids: the list of dataset ids to get the retrieval
            instructions for
        :type dataset_ids: List[str]
        :return: instructions with unsigned and signed URL to download
            the dataset file sources
        :rtype: dict
        """
        async with httpx.AsyncClient(
            base_url=self.base_url, headers=self.headers, timeout=TIMEOUT, transport=self._transport(),
        ) as client:
            request_body = {
                "datasetRegistryIds": dataset_ids,
            }

            response = await client.post(
                DatasetServicePaths.RETRIEVAL_INSTRUCTIONS,
                headers=self.headers,
                json=request_body,
            )
            logger.debug(f"{self.name}: retrieval instructions response: {response}")
            response.raise_for_status()
        return response.json()

    async def get_retrieval_instructions(self, dataset_id: str) -> dict:
        """Get retrieval instructions for a dataset to download.

        :param dataset_id: the dataset id to get the retrieval
            instructions for
        :type dataset_ids: str
        :return: instructions with unsigned and signed URL to download
            the dataset file source
        :rtype: dict
        """
        async with httpx.AsyncClient(
            base_url=self.base_url, headers=self.headers, timeout=TIMEOUT, transport=self._transport(),
        ) as client:
            q_params = {"id": dataset_id}

            response = await client.get(
                DatasetServicePaths.RETRIEVAL_INSTRUCTIONS,
                headers=self.headers,
                params=q_params,
            )
            logger.debug(f"{self.name}: get retrieval instructions response: {response}")
            response.raise_for_status()
            return response.json()

    async def create_or_update_dataset_registry(self, dataset_registries: List[dict]) -> dict:
        """Create or update dataset registry.

        :param dataset_registries: The list of dataset registry records.
        :type dataset_registries: List[dict]
        :return: response
        :rtype: dict
        """
        async with httpx.AsyncClient(
            base_url=self.base_url, headers=self.headers, timeout=TIMEOUT, transport=self._transport(),
        ) as client:
            request_body = {
                "datasetRegistries": dataset_registries,
            }
            response = await client.put(DatasetServicePaths.REGISTER_DATASET, headers=self.headers, json=request_body)
            logger.debug(f"{self.name}: put dataset registry response: {response}")
            response.raise_for_status()
            return response.json()

    async def get_dataset_registry(self, dataset_id: str) -> dict:
        """Get dataset registry.

        :param dataset_id: the dataset_id to retrieve
        :type request_body: str
        :return: the dataset registry
        :rtype: dict
        """
        async with httpx.AsyncClient(
            base_url=self.base_url, headers=self.headers, timeout=TIMEOUT, transport=self._transport(),
        ) as client:
            q_params = {"id": dataset_id}

            response = await client.get(
                DatasetServicePaths.GET_DATASET_REGISTRY, headers=self.headers, params=q_params,
            )
            logger.debug(f"{self.name}: get dataset registry response: {response}")
            response.raise_for_status()
            return response.json()

    async def get_dataset_registries(self, dataset_ids: List[str]) -> dict:
        """Get dataset registries.

        :param dataset_ids: the lits of dataset_id's to retrieve
        :type dataset_ids: List[str]
        :return: the dataset registries
        :rtype: dict
        """
        async with httpx.AsyncClient(
            base_url=self.base_url, headers=self.headers, timeout=TIMEOUT, transport=self._transport(),
        ) as client:
            request_body = {
                "datasetRegistryIds": dataset_ids,
            }

            response = await client.post(
                DatasetServicePaths.GET_DATASET_REGISTRY, headers=self.headers, json=request_body,
            )
            logger.debug(f"{self.name}: get dataset registries response: {response}")
            response.raise_for_status()
            return response.json()

    def _transport(self, retries: int = DEFAULT_RETRIES, **kwargs) -> httpx.AsyncHTTPTransport:
        """Create a new transport object.

        :param retries: the number of retries, defaults to
            DEFAULT_RETRIES
        :type retries: int, optional
        :return: A new transport object
        :rtype: httpx.AsyncHTTPTransport
        """
        return httpx.AsyncHTTPTransport(retries=retries, **kwargs)
