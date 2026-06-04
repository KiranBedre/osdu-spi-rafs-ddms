from typing import Optional

from client.api.core.schema_versioned_resource import SchemaVersionedAPIResource
from tests.integration.config import SchemaVersions


class SimulationRockPhysicsPaths(object):
    VERSION = "/v2"
    POST = "/reservoirsimulationrockphysicsmodel"
    GET = "/reservoirsimulationrockphysicsmodel/{record_id}"
    GET_VERSIONS = "/reservoirsimulationrockphysicsmodel/{record_id}/versions"
    GET_VERSION = "/reservoirsimulationrockphysicsmodel/{record_id}/versions/{version}"
    DELETE = "/reservoirsimulationrockphysicsmodel/{record_id}"
    POST_DATA = "/reservoirsimulationrockphysicsmodel/{record_id}/data"
    GET_DATA = "/reservoirsimulationrockphysicsmodel/{record_id}/data/{dataset_id}"
    GET_SCHEMA = "/reservoirsimulationrockphysicsmodel/data/schema"
    SEARCH = "/reservoirsimulationrockphysicsmodel/search"
    SEARCH_DATA = "/reservoirsimulationrockphysicsmodel/search/data"


class SimulationRockPhysics(SchemaVersionedAPIResource):

    def __init__(self, host: str, url_prefix: str, data_partition: str, token: str):
        super().__init__(
            host,
            SimulationRockPhysicsPaths.VERSION,
            url_prefix,
            data_partition,
            token,
            SimulationRockPhysicsPaths,
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
            path=SimulationRockPhysicsPaths.POST_DATA.format(record_id=record_id),
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
            path=SimulationRockPhysicsPaths.GET_DATA.format(
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
        response = self.get(path=SimulationRockPhysicsPaths.GET_SCHEMA, **kwargs)
        return response if raw else response.json()

    def search_records(
        self,
        schema_version: Optional[str] = SchemaVersions.DEFAULT,
        raw: bool = False,
        **kwargs,
    ) -> dict:
        kwargs = self._merge_params(kwargs, schema_version)
        response = self.get(path=SimulationRockPhysicsPaths.SEARCH, **kwargs)
        return response if raw else response.json()

    def search_data(
        self,
        schema_version: Optional[str] = SchemaVersions.DEFAULT,
        raw: bool = False,
        **kwargs,
    ) -> dict:
        kwargs = self._merge_params(kwargs, schema_version)
        response = self.get(path=SimulationRockPhysicsPaths.SEARCH_DATA, **kwargs)
        return response if raw else response.json()
