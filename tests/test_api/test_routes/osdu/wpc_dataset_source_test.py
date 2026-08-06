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

from contextlib import contextmanager
from unittest.mock import create_autospec, patch

import pytest
from httpx import AsyncClient
from starlette import status

from app.api.dependencies.services import (
    get_async_dataset_service,
    get_async_storage_service,
)
from app.main import app
from app.services.dataset import DatasetService
from app.services.storage import StorageService
from tests.test_api.test_routes import dependencies
from tests.test_api.test_routes.osdu.storage_mock_objects import (
    TEST_HEADERS,
    TEST_SAMPLESANALYSESREPORT_ID,
    TEST_SERVER,
)

storage_service_mock = create_autospec(StorageService, spec_set=True, instance=True)
dataset_service_mock = create_autospec(DatasetService, spec_set=True, instance=True)


async def mock_get_async_storage_service():
    yield storage_service_mock


async def mock_get_async_dataset_service():
    yield dataset_service_mock


@contextmanager
def source_route_override():
    overrides = {
        get_async_storage_service: mock_get_async_storage_service,
        get_async_dataset_service: mock_get_async_dataset_service,
    }
    with dependencies.DependencyOverrider(app, overrides) as mock_dependencies:
        yield mock_dependencies


@pytest.mark.asyncio
async def test_get_source_route_returns_single_dataset_file():
    dataset_id = "partition:dataset--File.Generic:dataset-source-id"
    parent_record = {
        "data": {
            "Datasets": [dataset_id],
        },
    }
    dataset_record = {
        "id": dataset_id,
        "data": {
            "Name": "dataset-source.json",
        },
    }

    with patch.object(storage_service_mock, "get_record", side_effect=[parent_record, dataset_record]):
        with patch.object(dataset_service_mock, "download_file", return_value=b'{"source":"ok"}'):
            with source_route_override():
                async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
                    response = await client.get(
                        f"/api/os-rafs-ddms/v2/samplesanalysesreport/{TEST_SAMPLESANALYSESREPORT_ID}/source",
                        headers=TEST_HEADERS,
                    )

    assert response.status_code == status.HTTP_200_OK
    assert response.content == b'{"source":"ok"}'
    assert response.headers["content-type"].startswith("application/json")
    assert response.headers["content-disposition"] == (f'attachment;filename="{dataset_id}.json"')
