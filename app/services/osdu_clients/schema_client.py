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

import dataclasses
from enum import StrEnum
from typing import Union

import httpx

from app.resources.common_headers import (
    AUTHORIZATION,
    CONTENT_TYPE,
    DATA_PARTITION_ID,
)
from app.services.osdu_clients.conf import DEFAULT_RETRIES, TIMEOUT


@dataclasses.dataclass
class SchemaIdentity:
    id: str
    _auth_index: int = 0
    _source_index: int = 1
    _entity_type_index: int = 2
    _version_index: int = 3
    _major_v_index: int = 0
    _minor_v_index: int = 1
    _patch_v_index: int = 2

    def __post_init__(self):
        splitted_id = self.id.split(":")
        splitted_version = splitted_id[self._version_index].split(".")
        id_parts = 4
        version_parts = 3

        if len(splitted_id) != id_parts or len(splitted_version) != version_parts:
            raise ValueError(
                f"Wrong id {self.id}, expected format: authority:source:entity_type:major_v.minor_v.patch_v",
            )

    @property
    def authority(self):
        return self.id.split(":")[self._auth_index]

    @property
    def source(self):
        return self.id.split(":")[self._source_index]

    @property
    def entity_type(self):
        return self.id.split(":")[self._entity_type_index]

    @property
    def major_version(self):
        return self.id.split(":")[self._version_index].split(".")[self._major_v_index]

    @property
    def minor_version(self):
        return self.id.split(":")[self._version_index].split(".")[self._minor_v_index]

    @property
    def patch_version(self):
        return self.id.split(":")[self._version_index].split(".")[self._patch_v_index]


class SchemaScope(StrEnum):
    SHARED = "SHARED"
    INTERNAL = "INTERNAL"


class SchemaStatus(StrEnum):
    DEVELOPMENT = "DEVELOPMENT"
    PUBLISHED = "PUBLISHED"
    OBSOLETE = "OBSOLETE"


class SchemaServicePaths(StrEnum):
    SCHEMA = "/schema"


class SchemaServiceApiClient(object):
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
        self.name = "SchemaService"

    def add_headers(self, headers: dict) -> None:
        """Add headers.

        :param headers: headers
        :type headers: dict
        """
        self.headers = {**self.headers, **headers}

    async def upsert_schema(
        self,
        schema_identity: SchemaIdentity,
        created_by: str,
        scope: Union[SchemaScope.SHARED, SchemaScope.INTERNAL],
        status: Union[SchemaStatus.DEVELOPMENT, SchemaStatus.OBSOLETE, SchemaStatus.PUBLISHED],
        schema_content: dict,
    ) -> dict:
        """Upserts the schema.

        :param schema_identity: schema identity
        :type schema_identity: SchemaIdentity
        :param created_by: created by description
        :type created_by: str
        :param scope: One of [SHARED, INTERNAL]
        :type scope: Union[SchemaScope.SHARED, SchemaScope.INTERNAL]
        :param status: One of [DEVELOPMENT, OBSOLETE, PUBLISHED]
        :type status: Union[SchemaStatus.DEVELOPMENT,
            SchemaStatus.OBSOLETE, SchemaStatus.PUBLISHED]
        :param schema_content: the dictionary containing the schema
        :type schema_content: dict
        :return: response from schema service
        :rtype: dict
        """
        payload = {
            "schemaInfo": {
                "schemaIdentity": {
                    "authority": schema_identity.authority,
                    "source": schema_identity.source,
                    "entityType": schema_identity.entity_type,
                    "schemaVersionMajor": schema_identity.major_version,
                    "schemaVersionMinor": schema_identity.minor_version,
                    "schemaVersionPatch": schema_identity.patch_version,
                    "id": schema_identity.id,
                },
                "createdBy": created_by,
                "scope": f"{scope}",
                "status": f"{status}",
            },
            "schema": schema_content,
        }
        async with httpx.AsyncClient(
            base_url=self.base_url, headers=self.headers, timeout=TIMEOUT, transport=self._transport(),
        ) as client:
            response = await client.put(SchemaServicePaths.SCHEMA, json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()

    # @cache(expire=CACHE_DEFAULT_TTL)
    async def get_schema(self, schema_id: str) -> dict:
        """Get the schema from schema service.

        :param schema_id: schema id
        :type schema_id: str
        :return: the schema
        :rtype: dict
        """
        async with httpx.AsyncClient(
            base_url=self.base_url, headers=self.headers, timeout=TIMEOUT, transport=self._transport(),
        ) as client:
            response = await client.get(f"{SchemaServicePaths.SCHEMA}/{schema_id}", headers=self.headers)
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
