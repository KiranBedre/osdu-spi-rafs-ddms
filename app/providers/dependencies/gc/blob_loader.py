# Copyright 2023 Google LLC
# Copyright 2023 EPAM Systems
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

import aiohttp

from app.providers.dependencies.blob_loader import IBlobLoader


class GoogleBlobLoader(IBlobLoader):

    async def upload_blob(self, signed_url: str, blob: bytes):
        async with aiohttp.ClientSession(trust_env=True) as session:
            async with session.put(signed_url, data=blob, ssl=False) as resp:
                resp.raise_for_status()
                await resp.read()

    async def download_blob(self, signed_url: str) -> bytes:
        async with aiohttp.ClientSession(trust_env=True) as session:
            async with session.get(signed_url, ssl=False) as resp:
                resp.raise_for_status()
                blob = await resp.read()
        return blob
