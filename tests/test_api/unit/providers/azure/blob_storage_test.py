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

from unittest.mock import AsyncMock, patch

import pytest

from app.exceptions.exceptions import UnprocessableContentException
from app.providers.dependencies.az.blob_storage import (
    STORAGE_ACCOUNT_NAME,
    AzureBlobStorage,
)
from app.providers.dependencies.blob_storage import (
    Blob,
    BlobMetadata,
    StoragePartitionInfo,
)
from app.resources.mime_types import SupportedMimeTypes


@pytest.fixture
def blob_metadata():
    return BlobMetadata(
        analysis_family="family",
        analysis_type="type",
        version="1",
        uuid="1234",
        content_type=SupportedMimeTypes.PARQUET,
    )


@pytest.fixture
def storage_partition_info():
    storage_account = {
        STORAGE_ACCOUNT_NAME: "accountname",
        "container_name": "test_container",
    }
    return StoragePartitionInfo(
        data_partition_id="dp1",
        storage_account_info=storage_account,
    )


@pytest.mark.asyncio
async def test_create_blob_success(blob_metadata, storage_partition_info):
    test_blob = Blob(blob_data=b"data", blob_metadata=blob_metadata)
    blob_storage = AzureBlobStorage(storage_partition_info)

    with patch.object(blob_storage, "_upload_blob", AsyncMock(return_value=blob_metadata)) as mock_upload:
        result = await blob_storage.create_blob(test_blob)
        assert result == blob_metadata
        mock_upload.assert_called_once_with(test_blob)


@pytest.mark.asyncio
async def test_update_blob_success(blob_metadata, storage_partition_info):
    test_blob = Blob(blob_data=b"data", blob_metadata=blob_metadata)
    blob_storage = AzureBlobStorage(storage_partition_info)

    with patch.object(blob_storage, "_upload_blob", AsyncMock(return_value=blob_metadata)) as mock_upload:
        result = await blob_storage.update_blob(test_blob)
        assert result == blob_metadata
        mock_upload.assert_called_once_with(test_blob, overwrite=True)


@pytest.mark.asyncio
async def test_list_blobs_success(storage_partition_info):
    blob_storage = AzureBlobStorage(storage_partition_info)

    with patch.object(blob_storage, "list_blobs", AsyncMock(return_value=["blob1", "blob2"])) as mock_list:
        result = await blob_storage.list_blobs("some_path")
        assert result == ["blob1", "blob2"]
        mock_list.assert_called_once_with("some_path")


@pytest.mark.asyncio
async def test_upload_blob_failure_due_to_azure_exception(blob_metadata, storage_partition_info):
    test_blob = Blob(blob_data=b"data", blob_metadata=blob_metadata)
    blob_storage = AzureBlobStorage(storage_partition_info)

    with patch.object(blob_storage, "_upload_blob", AsyncMock(side_effect=UnprocessableContentException())) as mock_upload:
        with pytest.raises(UnprocessableContentException):
            await blob_storage.create_blob(test_blob)
        mock_upload.assert_called_once_with(test_blob)
