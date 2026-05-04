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

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.responses import JSONResponse
from starlette.responses import Response

from app.api.routes.utils.ddms_datasets import (
    get_parquet_data,
    upsert_parquet_data,
)
from app.providers.dependencies.blob_storage import (
    Blob,
    BlobMetadata,
    IBlobStorage,
)
from app.resources.mime_types import SupportedMimeTypes
from app.services.storage import StorageService


@pytest.fixture
def mock_blob():
    return Blob(
        blob_data=b"parquetdata",
        blob_metadata=BlobMetadata(
            "analysis_family",
            "analysis_type",
            "1.0.0",
            "123456789",
            SupportedMimeTypes.PARQUET,
        ),
    )


@pytest.fixture
def mock_blob_metadata():
    return BlobMetadata(
        "analysis_family",
        "analysis_type",
        "1.0.0",
        "123456789",
        SupportedMimeTypes.PARQUET,
    )


@pytest.fixture
def mock_blob_storage_service():
    return AsyncMock(spec=IBlobStorage)


@pytest.fixture
def mock_storage_service():
    return AsyncMock(spec=StorageService)


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.ddms_id = "rafs"
    return settings


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "initial_ddms_datasets, expected_urn, expected_length",
    [
        # Test case 1: Existing object name
        (
            ["urn://rafs/wpc_id/analysis_family/analysis_type/1.0.0/123456789"],
            "urn://rafs/wpc_id/analysis_family/analysis_type/1.0.0/123456789",
            1,
        ),
        # Test case 2: New object name added
        (
            [
                "urn://rafs/wpc_id/analysis_family/old_type/1.0.0/123456789",
                "urn://rafs/wpc_id/analysis_family/analysis_type/2.0.0/123456789",
            ],
            "urn://rafs/wpc_id/analysis_family/analysis_type/1.0.0/123456789",
            3,
        ),
    ],
)
async def test_upsert_parquet_data(
    mock_blob,
    mock_blob_metadata,
    mock_blob_storage_service,
    mock_storage_service,
    mock_settings,
    monkeypatch,
    initial_ddms_datasets,
    expected_urn,
    expected_length,
):
    monkeypatch.setattr("app.core.config.get_app_settings", lambda: mock_settings)

    # Mock the storage service responses
    mock_record = {
        "data": {"DDMSDatasets": initial_ddms_datasets},
    }
    mock_storage_service.get_record.return_value = mock_record
    mock_storage_service.upsert_records.return_value = {"recordIdVersions": "mock_updated_id:version"}

    # Mock the blob storage service responses
    mock_blob_storage_service.create_blob.return_value = mock_blob_metadata

    # Call the function
    response = await upsert_parquet_data(
        blob=mock_blob,
        record_id="wpc_id",
        blob_storage_service=mock_blob_storage_service,
        storage_service=mock_storage_service,
    )

    # Validate the DDMSDatasets update
    updated_ddms_datasets = mock_record["data"]["DDMSDatasets"]
    assert len(updated_ddms_datasets) == expected_length
    assert expected_urn in updated_ddms_datasets

    # Validate the response
    assert isinstance(response, JSONResponse)
    response_data = response.body.decode()
    assert "ddms_urn" in response_data
    assert "updated_wpc_id" in response_data

    # Ensure correct calls
    mock_storage_service.get_record.assert_called_once_with("wpc_id")
    mock_blob_storage_service.create_blob.assert_awaited_once_with(mock_blob)
    mock_storage_service.upsert_records.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_parquet_data_success(
    mock_blob, mock_blob_metadata, mock_blob_storage_service, mock_storage_service, mock_settings, monkeypatch
):
    monkeypatch.setattr("app.core.config.get_app_settings", lambda: mock_settings)

    # Mock request and inputs
    mock_request = MagicMock()
    mock_request.headers = {"Accept": "application/x-parquet"}
    mock_record = {
        "data": {"DDMSDatasets": ["urn://rafs/wpc_id/analysis_family/analysis_type/1.0.0/123456789"]},
    }

    # Mock storage service and blob service
    mock_storage_service.get_record.return_value = mock_record
    mock_blob_storage_service.get_blob.return_value = mock_blob

    # Mock Parquet filtering
    monkeypatch.setattr(
        "app.api.routes.utils.ddms_datasets.apply_filters_from_bytes",
        lambda x, y: MagicMock(to_parquet=lambda: b"filtered_parquet_data"),
    )

    response = await get_parquet_data(
        request=mock_request,
        record_id="mock_record_id",
        blob_metadata=mock_blob_metadata,
        blob_storage_service=mock_blob_storage_service,
        storage_service=mock_storage_service,
        df_filter=MagicMock(),
    )

    # Validate the response
    assert isinstance(response, Response)
    assert response.body == b"filtered_parquet_data"
    assert response.media_type == SupportedMimeTypes.PARQUET.mime_type

    # Ensure correct calls
    mock_storage_service.get_record.assert_called_once_with("mock_record_id")
    mock_blob_storage_service.get_blob.assert_awaited_once_with(mock_blob_metadata)


@pytest.mark.asyncio
async def test_get_parquet_data_not_found(mock_blob_metadata, mock_blob_storage_service, mock_storage_service):
    # Mock request and inputs
    mock_request = MagicMock()
    mock_request.headers = {"content-type": "application/json"}
    mock_record = {
        "data": {"DDMSDatasets": []},
    }

    # Mock storage service
    mock_storage_service.get_record.return_value = mock_record

    response = await get_parquet_data(
        request=mock_request,
        record_id="mock_record_id",
        blob_metadata=mock_blob_metadata,
        blob_storage_service=mock_blob_storage_service,
        storage_service=mock_storage_service,
        df_filter=MagicMock(),
    )

    # Validate the response
    assert isinstance(response, JSONResponse)
    assert response.status_code == 404
    assert "does not exist" in response.body.decode()

    # Ensure correct calls
    mock_storage_service.get_record.assert_called_once_with("mock_record_id")
    mock_blob_storage_service.get_blob.assert_not_awaited()
