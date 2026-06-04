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

from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.providers.dependencies.az.blob_loader import (
    TIMEOUT,
    AzureBlobLoader,
    BlobClient,
)

TEST_BLOB_URL = "https://somedomain.blob.core.windows.net/staging-area/user"
TEST_BLOB = b"blob"


class TestBlobLoader:
    @pytest.mark.asyncio
    async def test_upload_blob(self):
        # Patch the BlobClient.upload_blob method to return a mock response
        with patch.object(BlobClient, "upload_blob", return_value=Mock()) as blob_client:
            blob_loader = AzureBlobLoader()
            response = await blob_loader.upload_blob(TEST_BLOB_URL, TEST_BLOB)
        # Verify response and blob client called
        assert response is None
        blob_client.assert_called_once_with(blob_type="BlockBlob", data=TEST_BLOB, overwrite=True, timeout=TIMEOUT)

    @pytest.mark.asyncio
    async def test_download_blob(self):
        # Patch the BlobClient.download_blob method to return a mock response
        with patch.object(
            BlobClient, "download_blob", return_value=AsyncMock(readall=AsyncMock(return_value=TEST_BLOB))
        ) as blob_client:
            blob_loader = AzureBlobLoader()
            response = await blob_loader.download_blob(TEST_BLOB_URL)
        # Verify response and blob client called
        assert response == TEST_BLOB
        blob_client.assert_called_once_with(timeout=TIMEOUT)
