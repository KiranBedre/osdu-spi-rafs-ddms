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

from unittest.mock import Mock, patch

import pytest
from httpx import AsyncClient

from app.resources import common_headers
from app.services.osdu_clients.search_client import (
    SearchServiceApiClient,
    SearchServicePaths,
)

BASE_URL = "http://test-api.com"
QUERY_DATA = {"query": "test query"}
DATA_PARTITION_ID = "partition"
TOKEN_STR = "test_token"
TEST_CORRELATION_ID = "test_id"


class TestSearchServiceApiClient:
    @pytest.mark.asyncio
    async def test_query(self):
        expected_response = {"result": "query test result"}

        # Patch the AsyncClient.post method to return a mock response
        with patch.object(
            AsyncClient, "post", return_value=Mock(status_code=200, json=Mock(return_value=expected_response))
        ) as httpx_client:
            api_client = SearchServiceApiClient(
                base_url=BASE_URL,
                data_partition_id=DATA_PARTITION_ID,
                bearer_token=TOKEN_STR,
                extra_headers={common_headers.CORRELATION_ID: TEST_CORRELATION_ID},
            )
            response = await api_client.query(QUERY_DATA)

        # Verify that the expected headers were set and the expected response was returned
        assert api_client.headers[common_headers.DATA_PARTITION_ID] == DATA_PARTITION_ID
        assert api_client.headers[common_headers.AUTHORIZATION] == f"Bearer {TOKEN_STR}"
        assert api_client.headers[common_headers.CORRELATION_ID] == TEST_CORRELATION_ID
        assert response == expected_response
        httpx_client.assert_called_once_with(
            SearchServicePaths.QUERY,
            json=QUERY_DATA,
            headers=api_client.headers,
        )

    @pytest.mark.asyncio
    async def test_query_with_cursor(self):
        expected_response = {"result": "query with cursor test result"}

        # Patch the AsyncClient.post method to return a mock response
        with patch.object(
            AsyncClient, "post", return_value=Mock(status_code=200, json=Mock(return_value=expected_response))
        ) as httpx_client:
            api_client = SearchServiceApiClient(
                base_url=BASE_URL,
                data_partition_id=DATA_PARTITION_ID,
                bearer_token=TOKEN_STR,
                extra_headers={common_headers.CORRELATION_ID: TEST_CORRELATION_ID},
            )
            response = await api_client.query_with_cursor(QUERY_DATA)

        # Verify that the expected headers were set and the expected response was returned
        assert api_client.headers[common_headers.DATA_PARTITION_ID] == DATA_PARTITION_ID
        assert api_client.headers[common_headers.AUTHORIZATION] == f"Bearer {TOKEN_STR}"
        assert api_client.headers[common_headers.CORRELATION_ID] == TEST_CORRELATION_ID
        assert response == expected_response
        httpx_client.assert_called_once_with(
            SearchServicePaths.CURSOR_QUERY,
            json=QUERY_DATA,
            headers=api_client.headers,
        )
