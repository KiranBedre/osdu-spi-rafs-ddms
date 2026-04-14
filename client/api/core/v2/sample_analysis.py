from collections import defaultdict

from client.api.core.api_source import APIResource
from client.api_client import APIClient
from tests.integration.config import (
    ACCEPT_HEADERS,
    SchemaVersions,
    SamplesAnalysisTypes,
)


class SamplesAnalysisPaths(object):
    VERSION = "/v2"
    POST = "/samplesanalysis"
    GET = "/samplesanalysis/{record_id}"
    GET_VERSIONS = "/samplesanalysis/{record_id}/versions"
    GET_VERSION = "/samplesanalysis/{record_id}/versions/{version}"
    DELETE = "/samplesanalysis/{record_id}"
    POST_DATA = "/samplesanalysis/{record_id}/data/{analysis_type}"
    GET_DATA = "/samplesanalysis/{record_id}/data/{analysis_type}/{dataset_id}"
    GET_ANALYSIS_TYPES = "/samplesanalysis/analysistypes"
    GET_SCHEMA = "/samplesanalysis/{analysistypes}/data/schema"
    SEARCH = "/samplesanalysis/{analysis_type}/search"
    SEARCH_DATA = "/samplesanalysis/{analysis_type}/search/data"


class SamplesAnalysis(APIResource, APIClient):
    def __init__(self, host: str, url_prefix: str, data_partition: str, token: str):
        super().__init__(host, SamplesAnalysisPaths.VERSION, url_prefix, data_partition, token, SamplesAnalysisPaths)

    def post_measurements(
        self,
        record_id: str,
        body: dict,
        analysis_type: SamplesAnalysisTypes,
        schema_version: str = SchemaVersions.DEFAULT,
        raw: bool = False,
        **kwargs,
    ) -> dict:
        """
        :param record_id: created record_id
        :param analysis_type: necessary analysis_type
        :param body: measurements data
        :param schema_version_header: version of the dataset schema
        :return: created data
        """
        self._add_version_header(kwargs, schema_version)
        response = self.post(
            path=SamplesAnalysisPaths.POST_DATA.format(record_id=record_id, analysis_type=analysis_type),
            json=body,
            **kwargs,
        )
        return response if raw else response.json()

    def get_measurements(
        self,
        record_id: str,
        dataset_id: str,
        analysis_type: SamplesAnalysisTypes,
        schema_version: str = SchemaVersions.DEFAULT,
        raw: bool = False,
        **kwargs,
    ) -> dict:
        """
        :param record_id: created record id
        :param analysis_type: necessary analysis_type
        :param dataset_id: created dataset id
        :param schema_version_header: version of the dataset schema
        :param json: is response json or not
        :return: measurements data
        """
        self._add_version_header(kwargs, schema_version)
        path = SamplesAnalysisPaths.GET_DATA.format(
            record_id=record_id,
            analysis_type=analysis_type,
            dataset_id=dataset_id,
        )
        response = self.get(path=path, **kwargs)
        return response if raw else response.json()

    def get_analysis_types(self, raw: bool = False, **kwargs) -> dict:
        """Get available types."""
        response = self.get(path=SamplesAnalysisPaths.GET_ANALYSIS_TYPES, **kwargs)
        return response if raw else response.json()

    def get_schema(
        self,
        analysis_type: SamplesAnalysisTypes,
        schema_version: str = SchemaVersions.DEFAULT,
        raw: bool = False,
        **kwargs,
    ) -> dict:
        """Get actual schema for provided analysis_type."""
        self._add_version_header(kwargs, schema_version)
        response = self.get(
            path=SamplesAnalysisPaths.GET_SCHEMA.format(analysistypes=analysis_type),
            **kwargs,
        )
        return response if raw else response.json()

    def search(
        self,
        analysis_type: SamplesAnalysisTypes,
        schema_version: str = SchemaVersions.DEFAULT,
        raw: bool = False,
        **kwargs,
    ) -> dict:
        """Search for analysis type ids."""
        self._add_version_header(kwargs, schema_version)
        response = self.get(
            path=SamplesAnalysisPaths.SEARCH.format(analysis_type=analysis_type),
            **kwargs,
        )
        return response if raw else response.json()

    def search_data(
        self,
        analysis_type: SamplesAnalysisTypes,
        schema_version: str = SchemaVersions.DEFAULT,
        raw: bool = False,
        **kwargs,
    ) -> dict:
        """Search for bulk data given analysis type."""
        self._add_version_header(kwargs, schema_version)
        response = self.get(
            path=SamplesAnalysisPaths.SEARCH_DATA.format(analysis_type=analysis_type),
            **kwargs,
        )
        return response if raw else response.json()

    def _add_version_header(self, kwargs: dict, schema_version: str) -> None:
        """ Helper to construct and inject the Accept header. """

        accept_header = ACCEPT_HEADERS.format(version=schema_version)

        headers = defaultdict(dict, kwargs.get("headers", {}))
        headers.update({"Accept": accept_header})
        kwargs["headers"] = headers
