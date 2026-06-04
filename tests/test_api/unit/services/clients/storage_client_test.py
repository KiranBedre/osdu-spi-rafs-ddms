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
from urllib.parse import quote

import pytest
from httpx import AsyncClient

from app.resources import common_headers
from app.services.osdu_clients.storage_client import (
    StorageServiceApiClient,
    StorageServicePaths,
)

BASE_URL = "http://test-api.com"
DATA_PARTITION_ID = "partition"
TOKEN_STR = "test_token"
TEST_CORRELATION_ID = "test_id"
TEST_RECORD_ID = "partition:entity-type--EntityName:id"
TEST_RECORD_ID_ENCODED = quote(TEST_RECORD_ID, safe="")
TEST_RECORD_ID_SPECIAL = "opendes:master-data--Sample:7%2F12-A-7%20D_Sample_249"
TEST_RECORD_ID_SPECIAL_ENCODED = quote(TEST_RECORD_ID_SPECIAL, safe="")
TEST_RESPONSE = {"result_key": "result_value"}
TEST_VERSION = 1
TEST_RECORD = {"id": "test", "data": {"key": "value"}}


class TestStorageServiceApiClient:

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
    async def test_get_latest_record(self):
        with patch.object(
            AsyncClient, "get", return_value=Mock(status_code=HTTPStatus.OK, json=Mock(return_value=TEST_RESPONSE))
        ) as httpx_client:
            api_client = StorageServiceApiClient(
                base_url=BASE_URL,
                data_partition_id=DATA_PARTITION_ID,
                bearer_token=TOKEN_STR,
                extra_headers={common_headers.CORRELATION_ID: TEST_CORRELATION_ID},
            )
            response = await api_client.get_latest_record(TEST_RECORD_ID)

        # Verify that the expected headers were set and the expected response was returned
        self.common_get_post_success_assertions(api_client, response)
        httpx_client.assert_called_once_with(
            f"{StorageServicePaths.RECORDS}/{TEST_RECORD_ID_ENCODED}",
            headers=api_client.headers,
        )

    @pytest.mark.asyncio
    async def test_get_specific_record(self):
        with patch.object(
            AsyncClient, "get", return_value=Mock(status_code=HTTPStatus.OK, json=Mock(return_value=TEST_RESPONSE))
        ) as httpx_client:
            api_client = StorageServiceApiClient(
                base_url=BASE_URL,
                data_partition_id=DATA_PARTITION_ID,
                bearer_token=TOKEN_STR,
                extra_headers={common_headers.CORRELATION_ID: TEST_CORRELATION_ID},
            )
            response = await api_client.get_specific_record(TEST_RECORD_ID, TEST_VERSION)

        # Verify that the expected headers were set and the expected response was returned
        self.common_get_post_success_assertions(api_client, response)
        httpx_client.assert_called_once_with(
            f"{StorageServicePaths.RECORDS}/{TEST_RECORD_ID_ENCODED}/{TEST_VERSION}",
            headers=api_client.headers,
        )

    @pytest.mark.asyncio
    async def test_get_record_versions(self):
        with patch.object(
            AsyncClient, "get", return_value=Mock(status_code=HTTPStatus.OK, json=Mock(return_value=TEST_RESPONSE))
        ) as httpx_client:
            api_client = StorageServiceApiClient(
                base_url=BASE_URL,
                data_partition_id=DATA_PARTITION_ID,
                bearer_token=TOKEN_STR,
                extra_headers={common_headers.CORRELATION_ID: TEST_CORRELATION_ID},
            )
            response = await api_client.get_record_versions(TEST_RECORD_ID)

        # Verify that the expected headers were set and the expected response was returned
        self.common_get_post_success_assertions(api_client, response)
        httpx_client.assert_called_once_with(
            f"{StorageServicePaths.RECORDS}/versions/{TEST_RECORD_ID_ENCODED}",
            headers=api_client.headers,
        )

    @pytest.mark.asyncio
    async def test_soft_delete_record(self):
        with patch.object(AsyncClient, "post", return_value=Mock(status_code=HTTPStatus.NO_CONTENT)) as httpx_client:
            api_client = StorageServiceApiClient(
                base_url=BASE_URL,
                data_partition_id=DATA_PARTITION_ID,
                bearer_token=TOKEN_STR,
                extra_headers={common_headers.CORRELATION_ID: TEST_CORRELATION_ID},
            )
            response = await api_client.soft_delete_record(TEST_RECORD_ID)

        # Verify that the expected headers were set and the expected response was returned
        self.common_delete_success_assertions(api_client, response)
        httpx_client.assert_called_once_with(
            f"{StorageServicePaths.RECORDS}/{TEST_RECORD_ID_ENCODED}:delete",
            headers=api_client.headers,
        )

    @pytest.mark.asyncio
    async def test_delete_record(self):
        with patch.object(AsyncClient, "delete", return_value=Mock(status_code=HTTPStatus.NO_CONTENT)) as httpx_client:
            api_client = StorageServiceApiClient(
                base_url=BASE_URL,
                data_partition_id=DATA_PARTITION_ID,
                bearer_token=TOKEN_STR,
                extra_headers={common_headers.CORRELATION_ID: TEST_CORRELATION_ID},
            )
            response = await api_client.delete_record(TEST_RECORD_ID)

        # Verify that the expected headers were set and the expected response was returned
        self.common_delete_success_assertions(api_client, response)
        httpx_client.assert_called_once_with(
            f"{StorageServicePaths.RECORDS}/{TEST_RECORD_ID_ENCODED}",
            headers=api_client.headers,
        )

    @pytest.mark.asyncio
    async def test_create_update_records(self):
        with patch.object(
            AsyncClient, "put", return_value=Mock(status_code=HTTPStatus.OK, json=Mock(return_value=TEST_RESPONSE))
        ) as httpx_client:
            api_client = StorageServiceApiClient(
                base_url=BASE_URL,
                data_partition_id=DATA_PARTITION_ID,
                bearer_token=TOKEN_STR,
                extra_headers={common_headers.CORRELATION_ID: TEST_CORRELATION_ID},
            )
            response = await api_client.create_update_records([TEST_RECORD])

        # Verify that the expected headers were set and the expected response was returned
        self.common_get_post_success_assertions(api_client, response)
        httpx_client.assert_called_once_with(
            f"{StorageServicePaths.RECORDS}",
            json=[TEST_RECORD],
            headers=api_client.headers,
        )

    @pytest.mark.asyncio
    async def test_query_records(self):
        with patch.object(
            AsyncClient, "post", return_value=Mock(status_code=HTTPStatus.OK, json=Mock(return_value=TEST_RESPONSE))
        ) as httpx_client:
            api_client = StorageServiceApiClient(
                base_url=BASE_URL,
                data_partition_id=DATA_PARTITION_ID,
                bearer_token=TOKEN_STR,
                extra_headers={common_headers.CORRELATION_ID: TEST_CORRELATION_ID},
            )
            response = await api_client.query_records([TEST_RECORD_ID])

        # Verify that the expected headers were set and the expected response was returned
        self.common_get_post_success_assertions(api_client, response)
        httpx_client.assert_called_once_with(
            f"{StorageServicePaths.QUERY}",
            json={"records": [TEST_RECORD_ID]},
            headers=api_client.headers,
        )

    @pytest.mark.asyncio
    async def test_get_latest_record_with_special_characters(self):
        """Test that record IDs with special characters are properly URL-encoded.

        Record IDs like 'opendes:master-data--Sample:7%2F12-A-7%20D_Sample_249'
        must be URL-encoded to prevent 424 errors from Storage service.
        """
        with patch.object(
            AsyncClient, "get", return_value=Mock(status_code=HTTPStatus.OK, json=Mock(return_value=TEST_RESPONSE))
        ) as httpx_client:
            api_client = StorageServiceApiClient(
                base_url=BASE_URL,
                data_partition_id=DATA_PARTITION_ID,
                bearer_token=TOKEN_STR,
                extra_headers={common_headers.CORRELATION_ID: TEST_CORRELATION_ID},
            )
            response = await api_client.get_latest_record(TEST_RECORD_ID_SPECIAL)

        self.common_get_post_success_assertions(api_client, response)
        httpx_client.assert_called_once_with(
            f"{StorageServicePaths.RECORDS}/{TEST_RECORD_ID_SPECIAL_ENCODED}",
            headers=api_client.headers,
        )
