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

# Pylint cannot always resolve Azure namespace packages in static analysis.
# pylint: disable=no-name-in-module

from azure.storage.blob.aio import BlobClient
from loguru import logger

from app.providers.dependencies.blob_loader import IBlobLoader

TIMEOUT = 60


class AzureBlobLoader(IBlobLoader):

    async def upload_blob(self, upload_url: str, blob: bytes):
        async with BlobClient.from_blob_url(upload_url) as blob_client:
            response = await blob_client.upload_blob(data=blob, blob_type="BlockBlob", overwrite=True, timeout=TIMEOUT)
            logger.debug(f"Blob upload response {response}")

    async def download_blob(self, download_url: str) -> bytes:
        async with BlobClient.from_blob_url(download_url) as blob_client:
            stream = await blob_client.download_blob(timeout=TIMEOUT)
            return await stream.readall()
