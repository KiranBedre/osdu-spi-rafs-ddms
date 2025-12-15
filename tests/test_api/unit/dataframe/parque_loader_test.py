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

import io
import json
from http import HTTPStatus
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pandas as pd
import pytest
from httpx import AsyncClient

from app.dataframe.filter_processor import DFFilterProcessor
from app.dataframe.parquet_filter import DataFrameFilterValidator
from app.dataframe.parquet_loader import ParquetLoader
from app.models.data_schemas.sample_analysis_api_v2.base import (
    RoutineCoreAnalysisModel100,
)

ORIENT_SPLIT_TEST = {
    "columns": [
        "SamplesAnalysisID",
        "SampleID",
        "Test",
    ],
    "index": [
        0,
    ],
    "data": [
        [
            "opendes:work-product-component--SamplesAnalysis:SamplesAnalysisTest:",
            "opendes:master-data--Sample:Sample:",
            {
                "ExampleKey": "Example",
            },
        ],
    ],
}


class MockResponse:
    def __init__(self, content=b"", status_code=HTTPStatus.OK):
        self.content = content
        self.status_code = status_code

    async def aread(self):
        return self.content

    def raise_for_status(self):
        pass


class AsyncContextManager:

    def __init__(self, content=b""):
        self.content = content

    async def __aenter__(self):
        return MockResponse(self.content)

    async def __aexit__(self, exc_type, exc, traceback):
        pass


@pytest.fixture
def parquet_loader():
    return ParquetLoader()


@pytest.mark.asyncio
async def test_read_parquet_files_successful(parquet_loader):
    signed_urls = [("dataset_id1", "http://example.com/parquet1"), ("dataset_id2", "http://example.com/parquet2")]
    mock_content = pd.read_json(io.StringIO(json.dumps(ORIENT_SPLIT_TEST)), orient="split").to_parquet()

    with patch.object(AsyncClient, "stream", return_value=AsyncContextManager(mock_content)):
        result = await parquet_loader.read_parquet_files(signed_urls)

    assert len(result) == 2
    assert isinstance(result[0], tuple)
    assert isinstance(result[0][0], str)  # Dataset ID
    assert isinstance(result[0][1], pd.DataFrame)  # Pandas DataFrame


@pytest.mark.asyncio
async def test_read_parquet_files_with_filter_successful(parquet_loader):
    signed_urls = [("dataset_id1", "http://example.com/parquet1"), ("dataset_id2", "http://example.com/parquet2")]
    mock_content = pd.read_json(io.StringIO(json.dumps(ORIENT_SPLIT_TEST)), orient="split").to_parquet()
    df_filter = DataFrameFilterValidator(RoutineCoreAnalysisModel100)
    df_filter_processor = DFFilterProcessor(df_filter)

    with patch.object(AsyncClient, "stream", return_value=AsyncContextManager(mock_content)):
        result = await parquet_loader.read_parquet_files(signed_urls, df_filter_processor)

    assert len(result) == 2
    assert isinstance(result[0], tuple)
    assert isinstance(result[0][0], str)  # Dataset ID
    assert isinstance(result[0][1], pd.DataFrame)  # Pandas DataFrame


@pytest.mark.asyncio
async def test_read_parquet_from_url_with_failed_response(parquet_loader):
    async_client_mock = AsyncMock(spec=httpx.AsyncClient)
    async_client_mock.stream.side_effect = httpx.HTTPStatusError(
        message="", request=None, response=Mock(status_code=HTTPStatus.NOT_FOUND),
    )

    dataset_id, df, error_msg = await parquet_loader._read_parquet_from_url(
        "dataset_id", "http://example.com/parquet", client=async_client_mock,
    )

    assert dataset_id == "dataset_id"
    assert df.empty
    assert error_msg == "HTTP status error 404 for URL: http://example.com/parquet"
    async_client_mock.stream.assert_called_once_with("GET", "http://example.com/parquet")
