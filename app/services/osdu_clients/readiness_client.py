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


import httpx
from loguru import logger

from app.core.settings.app import AppSettings
from app.services.osdu_clients.conf import TIMEOUT


class ReadinessClient(object):
    def __init__(
        self,
        settings: AppSettings,
    ) -> None:
        self.settings = settings
        self.readiness_urls = (
            [] if (self.settings.service_readiness_urls is None) else (self.settings.service_readiness_urls.split(","))
        )

    async def is_ready(
        self,
    ) -> bool:
        """Check rafs dependencies.

        :return: True if 200 on ALL readiness endpoints.
        """

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            try:
                for readiness_url in self.readiness_urls:
                    response = await client.get(readiness_url)
                    response.raise_for_status()
                return True
            except httpx.HTTPError as exc:
                raise_url = exc.request.url
                logger.error(f"SERVICE_READINESS_URLS Not ready: {raise_url} - {exc}")
                raise
