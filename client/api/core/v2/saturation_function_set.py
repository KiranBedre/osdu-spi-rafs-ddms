from collections import defaultdict
from typing import Optional

from client.api.core.api_source import APIResource
from tests.integration.config import ACCEPT_HEADERS, SCHEMA_VERSION


class SaturationFunctionSetPaths(object):
    VERSION = "/v2"
    POST = "/saturationfunctionset"
    GET = "/saturationfunctionset/{record_id}"
    GET_VERSIONS = "/saturationfunctionset/{record_id}/versions"
    GET_VERSION = "/saturationfunctionset/{record_id}/versions/{version}"
    DELETE = "/saturationfunctionset/{record_id}"
    POST_DATA = "/saturationfunctionset/{record_id}/data"
    GET_DATA = "/saturationfunctionset/{record_id}/data/{dataset_id}"
    GET_SCHEMA = "/saturationfunctionset/data/schema"
    SEARCH = "/saturationfunctionset/search"
    SEARCH_DATA = "/saturationfunctionset/search/data"


class SaturationFunctionSet(APIResource):
    def __init__(self, host: str, url_prefix: str, data_partition: str, token: str):
        super().__init__(
            host,
            SaturationFunctionSetPaths.VERSION,
            url_prefix,
            data_partition,
            token,
            SaturationFunctionSetPaths,
        )

    def post_data(
        self,
        record_id: str,
        body: dict,
        schema_version_header: Optional[str] = ACCEPT_HEADERS.format(version=SCHEMA_VERSION),
        raw: bool = False,
        **kwargs,
    ) -> dict:
        self._apply_schema_version_header(kwargs, schema_version_header)
        response = self.post(
            path=SaturationFunctionSetPaths.POST_DATA.format(record_id=record_id),
            json=body,
            **kwargs,
        )
        return response if raw else response.json()

    def get_data(
        self,
        record_id: str,
        dataset_id: str,
        schema_version_header: Optional[str] = ACCEPT_HEADERS.format(version=SCHEMA_VERSION),
        raw: bool = False,
        **kwargs,
    ):
        self._apply_schema_version_header(kwargs, schema_version_header)
        response = self.get(
            path=SaturationFunctionSetPaths.GET_DATA.format(
                record_id=record_id,
                dataset_id=dataset_id,
            ),
            **kwargs,
        )
        return response if raw else response.json()

    def get_schema(
        self,
        schema_version_header: Optional[str] = ACCEPT_HEADERS.format(version=SCHEMA_VERSION),
        raw: bool = False,
        **kwargs,
    ) -> dict:
        self._apply_schema_version_header(kwargs, schema_version_header)
        response = self.get(path=SaturationFunctionSetPaths.GET_SCHEMA, **kwargs)
        return response if raw else response.json()

    def search_records(
        self,
        schema_version_header: Optional[str] = ACCEPT_HEADERS.format(version=SCHEMA_VERSION),
        raw: bool = False,
        **kwargs,
    ) -> dict:
        self._apply_schema_version_header(kwargs, schema_version_header)
        response = self.get(path=SaturationFunctionSetPaths.SEARCH, **kwargs)
        return response if raw else response.json()

    def search_data(
        self,
        schema_version_header: Optional[str] = ACCEPT_HEADERS.format(version=SCHEMA_VERSION),
        raw: bool = False,
        **kwargs,
    ) -> dict:
        self._apply_schema_version_header(kwargs, schema_version_header)
        response = self.get(path=SaturationFunctionSetPaths.SEARCH_DATA, **kwargs)
        return response if raw else response.json()

    def _apply_schema_version_header(self, kwargs, header_value: Optional[str]):
        if not header_value:
            return
        headers = defaultdict(dict, kwargs.get("headers", {}))
        headers.update({"Accept": header_value})
        kwargs["headers"] = headers
