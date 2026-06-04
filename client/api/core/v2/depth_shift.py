#  Copyright 2026 ExxonMobil Technology and Engineering Company
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

from typing import Optional

from client.api.core.schema_versioned_resource import SchemaVersionedAPIResource
from tests.integration.config import SchemaVersions


class DepthShiftPaths(object):
    VERSION = "/v2"
    POST = "/depthshift"
    GET = "/depthshift/{record_id}"
    GET_VERSIONS = "/depthshift/{record_id}/versions"
    GET_VERSION = "/depthshift/{record_id}/versions/{version}"
    DELETE = "/depthshift/{record_id}"
    POST_DATA = "/depthshift/{record_id}/data"
    GET_DATA = "/depthshift/{record_id}/data/{dataset_id}"
    GET_SCHEMA = "/depthshift/data/schema"
    SEARCH = "/depthshift/search"
    SEARCH_DATA = "/depthshift/search/data"


class DepthShift(SchemaVersionedAPIResource):

    def __init__(self, host: str, url_prefix: str, data_partition: str, token: str):
        super().__init__(
            host,
            DepthShiftPaths.VERSION,
            url_prefix,
            data_partition,
            token,
            DepthShiftPaths,
        )

    def post_data(
        self,
        record_id: str,
        body: dict,
        schema_version: Optional[str] = SchemaVersions.DEFAULT,
        raw: bool = False,
        **kwargs,
    ) -> dict:
        kwargs = self._merge_params(kwargs, schema_version)
        response = self.post(
            path=DepthShiftPaths.POST_DATA.format(record_id=record_id),
            json=body,
            **kwargs,
        )
        return response if raw else response.json()

    def get_data(
        self,
        record_id: str,
        dataset_id: str,
        schema_version: Optional[str] = SchemaVersions.DEFAULT,
        raw: bool = False,
        **kwargs,
    ):
        kwargs = self._merge_params(kwargs, schema_version)
        response = self.get(
            path=DepthShiftPaths.GET_DATA.format(
                record_id=record_id,
                dataset_id=dataset_id,
            ),
            **kwargs,
        )
        return response if raw else response.json()

    def get_schema(
        self,
        schema_version: Optional[str] = SchemaVersions.DEFAULT,
        raw: bool = False,
        **kwargs,
    ) -> dict:
        kwargs = self._merge_params(kwargs, schema_version)
        response = self.get(path=DepthShiftPaths.GET_SCHEMA, **kwargs)
        return response if raw else response.json()

    def search_records(
        self,
        schema_version: Optional[str] = SchemaVersions.DEFAULT,
        raw: bool = False,
        **kwargs,
    ) -> dict:
        kwargs = self._merge_params(kwargs, schema_version)
        response = self.get(path=DepthShiftPaths.SEARCH, **kwargs)
        return response if raw else response.json()

    def search_data(
        self,
        schema_version: Optional[str] = SchemaVersions.DEFAULT,
        raw: bool = False,
        **kwargs,
    ) -> dict:
        kwargs = self._merge_params(kwargs, schema_version)
        response = self.get(path=DepthShiftPaths.SEARCH_DATA, **kwargs)
        return response if raw else response.json()
