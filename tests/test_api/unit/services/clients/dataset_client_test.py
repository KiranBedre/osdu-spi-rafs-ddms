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

from http import HTTPStatus
from unittest.mock import Mock, patch

import pytest
from httpx import AsyncClient

from app.resources import common_headers
from app.services.osdu_clients.dataset_client import (
    DatasetServiceApiClient,
    DatasetServicePaths,
)

BASE_URL = "http://test-api.com"
DATA_PARTITION_ID = "partition"
TOKEN_STR = "test_token"
TEST_CORRELATION_ID = "test_id"
TEST_REGISTRY_ID = "partition:entity-type--EntityName:id"
TEST_RESPONSE = {"result_key": "result_value"}
TEST_VERSION = 1
TEST_RECORD = {"id": "test", "data": {"key": "value"}}
KIND_SUBTYPE = "kindsubtype"


class TestDatasetServiceApiClient:

    def common_assertions(self, api_client):
        assert api_client.headers[common_headers.DATA_PARTITION_ID] == DATA_PARTITION_ID
        assert api_client.headers[common_headers.AUTHORIZATION] == f"Bearer {TOKEN_STR}"
        assert api_client.headers[common_headers.CORRELATION_ID] == TEST_CORRELATION_ID

    def common_get_post_success_assertions(self, api_client, response):
        self.common_assertions(api_client)
        assert response == TEST_RESPONSE

    def common_delete_success_assertions(self, api_client, response):
        self.common_assertions(api_client)
        assert response is None

    @pytest.mark.asyncio
    async def test_get_storage_instructions(self):
        with patch.object(
            AsyncClient, "get", return_value=Mock(status_code=HTTPStatus.OK, json=Mock(return_value=TEST_RESPONSE))
        ) as httpx_client:
            api_client = DatasetServiceApiClient(
                base_url=BASE_URL,
                data_partition_id=DATA_PARTITION_ID,
                bearer_token=TOKEN_STR,
                extra_headers={common_headers.CORRELATION_ID: TEST_CORRELATION_ID},
            )
            response = await api_client.get_storage_instructions(KIND_SUBTYPE)

        # Verify that the expected headers were set and the expected response was returned
        self.common_get_post_success_assertions(api_client, response)
        httpx_client.assert_called_once_with(
            f"{DatasetServicePaths.GET_STORAGE_INSTRUCTIONS}",
            headers=api_client.headers,
            params={"kindSubType": KIND_SUBTYPE},
        )

    @pytest.mark.asyncio
    async def test_storage_instructions(self):
        with patch.object(
            AsyncClient, "post", return_value=Mock(status_code=HTTPStatus.OK, json=Mock(return_value=TEST_RESPONSE))
        ) as httpx_client:
            api_client = DatasetServiceApiClient(
                base_url=BASE_URL,
                data_partition_id=DATA_PARTITION_ID,
                bearer_token=TOKEN_STR,
                extra_headers={common_headers.CORRELATION_ID: TEST_CORRELATION_ID},
            )
            response = await api_client.storage_instructions(KIND_SUBTYPE)

        # Verify that the expected headers were set and the expected response was returned
        self.common_get_post_success_assertions(api_client, response)
        httpx_client.assert_called_once_with(
            f"{DatasetServicePaths.STORAGE_INSTRUCTIONS}",
            headers=api_client.headers,
            params={"kindSubType": KIND_SUBTYPE},
        )

    @pytest.mark.asyncio
    async def test_retrieval_instructions(self):
        with patch.object(
            AsyncClient, "post", return_value=Mock(status_code=HTTPStatus.OK, json=Mock(return_value=TEST_RESPONSE))
        ) as httpx_client:
            api_client = DatasetServiceApiClient(
                base_url=BASE_URL,
                data_partition_id=DATA_PARTITION_ID,
                bearer_token=TOKEN_STR,
                extra_headers={common_headers.CORRELATION_ID: TEST_CORRELATION_ID},
            )
            response = await api_client.retrieval_instructions([TEST_REGISTRY_ID])

        # Verify that the expected headers were set and the expected response was returned
        self.common_get_post_success_assertions(api_client, response)
        httpx_client.assert_called_once_with(
            f"{DatasetServicePaths.RETRIEVAL_INSTRUCTIONS}",
            json={"datasetRegistryIds": [TEST_REGISTRY_ID]},
            headers=api_client.headers,
        )

    @pytest.mark.asyncio
    async def test_get_retrieval_instructions(self):
        with patch.object(
            AsyncClient, "get", return_value=Mock(status_code=HTTPStatus.OK, json=Mock(return_value=TEST_RESPONSE))
        ) as httpx_client:
            api_client = DatasetServiceApiClient(
                base_url=BASE_URL,
                data_partition_id=DATA_PARTITION_ID,
                bearer_token=TOKEN_STR,
                extra_headers={common_headers.CORRELATION_ID: TEST_CORRELATION_ID},
            )
            response = await api_client.get_retrieval_instructions(TEST_REGISTRY_ID)

        # Verify that the expected headers were set and the expected response was returned
        self.common_get_post_success_assertions(api_client, response)
        httpx_client.assert_called_once_with(
            f"{DatasetServicePaths.RETRIEVAL_INSTRUCTIONS}",
            headers=api_client.headers,
            params={"id": TEST_REGISTRY_ID},
        )

    @pytest.mark.asyncio
    async def test_create_or_update_dataset_registry(self):
        with patch.object(
            AsyncClient, "put", return_value=Mock(status_code=HTTPStatus.OK, json=Mock(return_value=TEST_RESPONSE))
        ) as httpx_client:
            api_client = DatasetServiceApiClient(
                base_url=BASE_URL,
                data_partition_id=DATA_PARTITION_ID,
                bearer_token=TOKEN_STR,
                extra_headers={common_headers.CORRELATION_ID: TEST_CORRELATION_ID},
            )
            response = await api_client.create_or_update_dataset_registry([TEST_RECORD])

        # Verify that the expected headers were set and the expected response was returned
        self.common_get_post_success_assertions(api_client, response)
        httpx_client.assert_called_once_with(
            f"{DatasetServicePaths.REGISTER_DATASET}",
            json={"datasetRegistries": [TEST_RECORD]},
            headers=api_client.headers,
        )

    @pytest.mark.asyncio
    async def test_get_dataset_registry(self):
        with patch.object(
            AsyncClient, "get", return_value=Mock(status_code=HTTPStatus.OK, json=Mock(return_value=TEST_RESPONSE))
        ) as httpx_client:
            api_client = DatasetServiceApiClient(
                base_url=BASE_URL,
                data_partition_id=DATA_PARTITION_ID,
                bearer_token=TOKEN_STR,
                extra_headers={common_headers.CORRELATION_ID: TEST_CORRELATION_ID},
            )
            response = await api_client.get_dataset_registry(TEST_REGISTRY_ID)

        # Verify that the expected headers were set and the expected response was returned
        self.common_get_post_success_assertions(api_client, response)
        httpx_client.assert_called_once_with(
            f"{DatasetServicePaths.GET_DATASET_REGISTRY}",
            headers=api_client.headers,
            params={"id": TEST_REGISTRY_ID},
        )

    @pytest.mark.asyncio
    async def test_get_dataset_registries(self):
        with patch.object(
            AsyncClient, "post", return_value=Mock(status_code=HTTPStatus.OK, json=Mock(return_value=TEST_RESPONSE))
        ) as httpx_client:
            api_client = DatasetServiceApiClient(
                base_url=BASE_URL,
                data_partition_id=DATA_PARTITION_ID,
                bearer_token=TOKEN_STR,
                extra_headers={common_headers.CORRELATION_ID: TEST_CORRELATION_ID},
            )
            response = await api_client.get_dataset_registries([TEST_REGISTRY_ID])

        # Verify that the expected headers were set and the expected response was returned
        self.common_get_post_success_assertions(api_client, response)
        httpx_client.assert_called_once_with(
            f"{DatasetServicePaths.GET_DATASET_REGISTRY}",
            json={"datasetRegistryIds": [TEST_REGISTRY_ID]},
            headers=api_client.headers,
        )
