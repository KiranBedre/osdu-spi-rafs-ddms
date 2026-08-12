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
from tests.integration.config import FluidModelTypes, SchemaVersions


class FluidModelPaths(object):
    VERSION = "/v2"
    POST = "/fluidmodel"
    GET = "/fluidmodel/{record_id}"
    GET_VERSIONS = "/fluidmodel/{record_id}/versions"
    GET_VERSION = "/fluidmodel/{record_id}/versions/{version}"
    DELETE = "/fluidmodel/{record_id}"
    POST_DATA = "/fluidmodel/{record_id}/data/{fluid_model_type}"
    GET_DATA = "/fluidmodel/{record_id}/data/{fluid_model_type}/{dataset_id}"
    GET_SCHEMA = "/fluidmodel/{fluid_model_type}/data/schema"
    GET_FLUID_MODEL_TYPES = "/fluidmodel/fluidmodeltypes"


class FluidModel(SchemaVersionedAPIResource):
    def __init__(self, host: str, url_prefix: str, data_partition: str, token: str):
        super().__init__(
            host,
            FluidModelPaths.VERSION,
            url_prefix,
            data_partition,
            token,
            FluidModelPaths,
        )

    def post_data(
        self,
        record_id: str,
        body: dict | bytes,
        fluid_model_type: FluidModelTypes,
        schema_version: Optional[str] = SchemaVersions.DEFAULT,
        raw: bool = False,
        **kwargs,
    ) -> dict:
        kwargs = self._merge_params(kwargs, schema_version)
        request_body = {"data": body} if isinstance(body, bytes) else {"json": body}
        response = self.post(
            path=FluidModelPaths.POST_DATA.format(
                record_id=record_id,
                fluid_model_type=fluid_model_type,
            ),
            **request_body,
            **kwargs,
        )
        return response if raw else response.json()

    def get_data(
        self,
        record_id: str,
        dataset_id: str,
        fluid_model_type: FluidModelTypes,
        schema_version: Optional[str] = SchemaVersions.DEFAULT,
        raw: bool = False,
        **kwargs,
    ) -> dict:
        kwargs = self._merge_params(kwargs, schema_version)
        response = self.get(
            path=FluidModelPaths.GET_DATA.format(
                record_id=record_id,
                fluid_model_type=fluid_model_type,
                dataset_id=dataset_id,
            ),
            **kwargs,
        )
        return response if raw else response.json()

    def get_schema(
        self,
        fluid_model_type: FluidModelTypes,
        schema_version: Optional[str] = SchemaVersions.DEFAULT,
        raw: bool = False,
        **kwargs,
    ) -> dict:
        kwargs = self._merge_params(kwargs, schema_version)
        response = self.get(
            path=FluidModelPaths.GET_SCHEMA.format(fluid_model_type=fluid_model_type),
            **kwargs,
        )
        return response if raw else response.json()

    def get_fluid_model_types(self, raw: bool = False, **kwargs) -> dict:
        """Get available types."""
        response = self.get(path=FluidModelPaths.GET_FLUID_MODEL_TYPES, **kwargs)
        return response if raw else response.json()
