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

from typing import List, NamedTuple

import httpx
from loguru import logger

from app.resources.common_headers import (
    AUTHORIZATION,
    CONTENT_TYPE,
    DATA_PARTITION_ID,
)
from app.services.osdu_clients.conf import DEFAULT_RETRIES, TIMEOUT


class StorageServicePaths(NamedTuple):
    RECORDS = "/records"
    QUERY = "/query/records"


class StorageServiceApiClient(object):
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
        self.name = "StorageService"

    def add_headers(self, headers: dict) -> None:
        """Add headers.

        :param headers: headers
        :type headers: dict
        """
        self.headers = {**self.headers, **headers}

    async def create_update_records(self, records: List[dict]) -> dict:
        """Create or update existing records.

        :param records: records
        :type records: List[dict]
        :return: created or updated records ids
        :rtype: dict
        """
        async with httpx.AsyncClient(
            base_url=self.base_url, headers=self.headers, timeout=TIMEOUT, transport=self._transport(),
        ) as client:
            response = await client.put(StorageServicePaths.RECORDS, json=records, headers=self.headers)
            logger.debug(f"{self.name}: upsert records response: {response}")
            response.raise_for_status()
            return response.json()

    async def get_latest_record(self, record_id: str) -> dict:
        """Get latest version of record.

        :param record_id: record id
        :type record_id: str
        :return: record
        :rtype: dict
        """
        async with httpx.AsyncClient(
            base_url=self.base_url, headers=self.headers, timeout=TIMEOUT, transport=self._transport(),
        ) as client:
            response = await client.get(f"{StorageServicePaths.RECORDS}/{record_id}", headers=self.headers)
            logger.debug(f"{self.name}: get latest version of record response: {response}")
            response.raise_for_status()
            return response.json()

    async def get_specific_record(self, record_id: str, version: int) -> dict:
        """Get record by version.

        :param record_id: record id
        :type record_id: str
        :param version: record version
        :type version: int
        :return: versioned record
        :rtype: dict
        """
        async with httpx.AsyncClient(
            base_url=self.base_url, headers=self.headers, timeout=TIMEOUT, transport=self._transport(),
        ) as client:
            response = await client.get(f"{StorageServicePaths.RECORDS}/{record_id}/{version}", headers=self.headers)
            logger.debug(f"{self.name}: get specific record response: {response}")
            response.raise_for_status()
            return response.json()

    async def get_record_versions(self, record_id: str) -> dict:
        """Get record versions.

        :param record_id: record id
        :type record_id: str
        :return: record versions
        :rtype: dict
        """
        async with httpx.AsyncClient(
            base_url=self.base_url, headers=self.headers, timeout=TIMEOUT, transport=self._transport(),
        ) as client:
            response = await client.get(f"{StorageServicePaths.RECORDS}/versions/{record_id}", headers=self.headers)
            logger.debug(f"{self.name}: get record versions response: {response}")
            response.raise_for_status()
            return response.json()

    async def soft_delete_record(self, record_id: str) -> None:
        """Mark record as deleted.

        :param record_id: record id
        :type record_id: str
        """
        async with httpx.AsyncClient(
            base_url=self.base_url, headers=self.headers, timeout=TIMEOUT, transport=self._transport(),
        ) as client:
            response = await client.post(f"{StorageServicePaths.RECORDS}/{record_id}:delete", headers=self.headers)
            logger.debug(f"{self.name}: soft delete record response: {response}")
            response.raise_for_status()

    async def delete_record(self, record_id: str) -> None:
        """Delete (purge) record.

        :param record_id: record id
        :type record_id: str
        :return: deleted record id
        :rtype: dict
        """
        async with httpx.AsyncClient(
            base_url=self.base_url, headers=self.headers, timeout=TIMEOUT, transport=self._transport(),
        ) as client:
            response = await client.delete(f"{StorageServicePaths.RECORDS}/{record_id}", headers=self.headers)
            logger.debug(f"{self.name}: delete record response: {response}")
            response.raise_for_status()

    async def query_records(self, records: List[str]) -> dict:
        """Query records.

        :param records: records ids
        :type records: List[str]
        :return: records details
        :rtype: dict
        """
        async with httpx.AsyncClient(
            base_url=self.base_url, headers=self.headers, timeout=TIMEOUT, transport=self._transport(),
        ) as client:
            query_records_request = {"records": records}
            response = await client.post(
                f"{StorageServicePaths.QUERY}", json=query_records_request, headers=self.headers,
            )
            logger.debug(f"{self.name}: query records response: {response}")
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
