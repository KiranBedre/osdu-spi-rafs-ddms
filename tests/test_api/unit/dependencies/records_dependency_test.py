#  Copyright 2026 ExxonMobil Technology and Engineering Company
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

from unittest.mock import AsyncMock, patch

import pytest

from app.api.dependencies.records import get_data_file_source, get_data_file_sources
from app.resources.source_renderer import DatasetSourceFile
from app.services.dataset import DatasetService
from app.services.storage import StorageService


@pytest.fixture
def storage_service_mock():
    return AsyncMock(spec=StorageService)


@pytest.fixture
def dataset_service_mock():
    return AsyncMock(spec=DatasetService)


@pytest.mark.asyncio
async def test_get_data_file_source_resolves_version_mime_and_content(storage_service_mock, dataset_service_mock):
    dataset_full_id = "partition:dataset--File.Generic:dataset-source-id:7"
    dataset_id = "partition:dataset--File.Generic:dataset-source-id"
    dataset_record = {
        "id": dataset_id,
        "data": {"Name": "dataset-source.json"},
    }
    dataset_content = b'{"message":"ok"}'

    storage_service_mock.get_record.return_value = dataset_record
    dataset_service_mock.download_file.return_value = dataset_content

    with patch("app.api.dependencies.records.get_mime_type", return_value="application/json") as get_mime_type_mock:
        result = await get_data_file_source(dataset_full_id, storage_service_mock, dataset_service_mock)

    assert result == DatasetSourceFile(
        dataset_id=dataset_id,
        mime_type="application/json",
        content=dataset_content,
    )
    storage_service_mock.get_record.assert_awaited_once_with(dataset_id, 7)
    dataset_service_mock.download_file.assert_awaited_once_with(dataset_id)
    get_mime_type_mock.assert_called_once_with(dataset_record)


@pytest.mark.asyncio
async def test_get_data_file_sources_resolves_all_datasets(storage_service_mock, dataset_service_mock):
    parent_record = {
        "data": {
            "Datasets": [
                "partition:dataset--File.Generic:dataset-1",
                "partition:dataset--File.Generic:dataset-2",
            ],
        },
    }
    expected_sources = [
        DatasetSourceFile(dataset_id="partition:dataset--File.Generic:dataset-1", mime_type="text/csv", content=b"1"),
        DatasetSourceFile(
            dataset_id="partition:dataset--File.Generic:dataset-2", mime_type="application/json", content=b"2"
        ),
    ]

    storage_service_mock.get_record.return_value = parent_record

    with patch(
        "app.api.dependencies.records.get_data_file_source",
        new=AsyncMock(side_effect=expected_sources),
    ) as get_data_file_source_mock:
        result = await get_data_file_sources(
            record_id="partition:work-product-component--SamplesAnalysesReport:test-id",
            storage_service=storage_service_mock,
            dataset_service=dataset_service_mock,
            version=123,
        )

    assert result == expected_sources
    storage_service_mock.get_record.assert_awaited_once_with(
        "partition:work-product-component--SamplesAnalysesReport:test-id",
        123,
    )
    assert get_data_file_source_mock.await_count == 2
