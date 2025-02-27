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

from typing import NamedTuple

import httpx
from loguru import logger

from app.resources.common_headers import (
    AUTHORIZATION,
    CONTENT_TYPE,
    DATA_PARTITION_ID,
)
from app.services.osdu_clients.conf import DEFAULT_RETRIES, TIMEOUT


class SearchServicePaths(NamedTuple):
    QUERY = "/query"
    CURSOR_QUERY = "/query_with_cursor"


class SearchServiceApiClient(object):
    def __init__(
        self,
        base_url: str,
        *,
        data_partition_id: str = None,
        bearer_token: str = None,
        extra_headers: dict = None,
    ) -> None:
        self.base_url = base_url
        self.headers = {
            CONTENT_TYPE: "application/json",
            DATA_PARTITION_ID: data_partition_id,
            AUTHORIZATION: f"Bearer {bearer_token}",
            **(extra_headers or {}),
        }
        self.name = "SearchService"

    def add_headers(self, headers: dict) -> None:
        """Add headers.

        :param headers: headers
        :type headers: dict
        """
        self.headers = {**self.headers, **headers}

    async def query(self, query: dict) -> dict:
        """Performa query to the osdu search service.

        :param query: query
        :type query: dict
        :return: query result
        :rtype: dict
        """
        async with httpx.AsyncClient(
            base_url=self.base_url, headers=self.headers, timeout=TIMEOUT, transport=self._transport(),
        ) as client:
            response = await client.post(SearchServicePaths.QUERY, json=query, headers=self.headers)
            logger.debug(f"{self.name}: query response: {response}")
            response.raise_for_status()
            return response.json()

    async def query_with_cursor(self, query: dict) -> dict:
        """Performa query to the osdu search service.

        :param query: query
        :type query: dict
        :return: query with cursor result
        :rtype: dict
        """
        async with httpx.AsyncClient(
            base_url=self.base_url, headers=self.headers, timeout=TIMEOUT, transport=self._transport(),
        ) as client:
            response = await client.post(SearchServicePaths.CURSOR_QUERY, json=query, headers=self.headers)
            logger.debug(f"{self.name}: query with cursor response: {response}")
            response.raise_for_status()
            return response.json()

    def _transport(self, retries: int = DEFAULT_RETRIES, **kwargs) -> httpx.AsyncHTTPTransport:
        """Create a new transport object.

        :param retries: the number of retries, defaults to
            DEFAULT_RETRIES
        :type retries: int, optional
        :return: A new transport object
        :rtype: httpx.AsyncHTTPTransport
        """
        return httpx.AsyncHTTPTransport(retries=retries, **kwargs)
