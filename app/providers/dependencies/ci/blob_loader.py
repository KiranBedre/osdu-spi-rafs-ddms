#  Copyright 2025 ExxonMobil Technology and Engineering Company
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

import httpx
from loguru import logger

from app.providers.dependencies.blob_loader import IBlobLoader

TIMEOUT = 60


class CIBlobLoader(IBlobLoader):
    """
    Blob loader implementation for CI environment.
    Uses signed URLs via plain HTTP.
    """

    async def upload_blob(self, upload_url: str, blob: bytes):
        logger.debug("CIBlobLoader: uploading blob via HTTP")
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.put(upload_url, content=blob)
            response.raise_for_status()

    async def download_blob(self, download_url: str) -> bytes:
        logger.debug("CIBlobLoader: downloading blob via HTTP")
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(download_url)
            response.raise_for_status()
            return await response.aread()
