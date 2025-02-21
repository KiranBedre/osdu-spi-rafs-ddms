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

import json
from typing import Annotated, AsyncGenerator, Dict, List, Optional, Tuple

import pandas as pd
from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi_cache.decorator import cache
from loguru import logger
from starlette import status

from app.api.dependencies.parquet import get_parquet_loader
from app.api.dependencies.request import (
    get_content_schema_version,
    validate_bulkdata_content_type,
    validate_json_content_type,
)
from app.api.dependencies.services import (
    get_async_dataset_service,
    get_async_search_service,
    get_async_storage_service,
)
from app.api.dependencies.validation import (
    get_search_data_pagination_parameters,
    get_search_pagination_parameters,
    validate_filters,
)
from app.api.routes.osdu.storage_records import BaseStorageRecordView
from app.api.routes.utils.api_description_helper import APIDescriptionHelper
from app.api.routes.utils.records import get_info_from_urn
from app.core.helpers.cache.coder import ResponseCoder
from app.core.helpers.cache.key_builder import key_builder_using_token
from app.core.helpers.cache.settings import CACHE_DEFAULT_TTL
from app.dataframe.filter_processor import DFFilterProcessor
from app.dataframe.parquet_loader import DFPayload, ParquetLoader
from app.models.data_schemas.base import (
    ALL_PATHS_TO_DATA_MODEL,
    ENDPOINT_PATTERNS,
)
from app.models.domain.osdu.base import SAMPLESANALYSIS_KIND
from app.models.schemas.osdu_storage import (
    OsduStorageRecord,
    StorageUpsertResponse,
)
from app.resources.filters import DataFrameFilterValidator
from app.resources.load_model_example import load_data_example
from app.resources.mime_types import SupportedMimeTypes
from app.resources.paths import SAMPLESANALYSIS_TYPE_MAPPING
from app.services import dataset, search, storage

SAMPLESANALYSIS_ID_REGEX_STR = r"^[\w\-\.]+:work-product-component--SamplesAnalysis:[\w\-\.\:\%]+$"
SEARCH_READ_BATCH_SIZE = 100  # max number of parquet files retrieved


class SamplesAnalysisRecordView(BaseStorageRecordView):
    def __init__(
        self,
        router: APIRouter,
        validate_records_payload: callable,
        record_type: str,
    ) -> None:
        super().__init__(
            router=router,
            id_regex_str=SAMPLESANALYSIS_ID_REGEX_STR,
            validate_records_payload=validate_records_payload,
            record_type=record_type,
        )

    async def post_records(
        self,
        request: Request,
        request_records: Annotated[List[dict], Body(example=load_data_example("samples_analysis.json"))],
        storage_service: storage.StorageService = Depends(get_async_storage_service),
    ) -> StorageUpsertResponse:
        return await super().post_records(request, request_records, storage_service)

    def _prepare_post_records_route(self) -> None:
        """Add api route for post_records without dependencies."""
        async def validate_request_records(
            request_records: List[OsduStorageRecord],
            storage_service: storage.StorageService = Depends(get_async_storage_service),
        ) -> List[dict]:
            """Validate request records.

            :param request_records: request records
            :type request_records: List[OsduStorageRecord]
            :param storage_service: storage service instance, defaults
                  to Depends(get_async_storage_service)
            :type storage_service: storage.StorageService, optional
            :return: validated records
            :rtype: List[dict]
            """
            return await self._validate_records_payload(request_records, storage_service)

        self._router.add_api_route(
            path="",
            endpoint=self.post_records,
            methods=["POST"],
            status_code=status.HTTP_200_OK,
            response_model=StorageUpsertResponse,
            response_model_by_alias=False,
            description=APIDescriptionHelper.append_manage_roles(
                f"Create or update `{self._record_type}` record(s).",
            ),
            dependencies=[
                Depends(validate_request_records),
                Depends(validate_json_content_type),
            ],
        )


class SamplesAnalysisTypesView:
    def __init__(
        self,
        router: APIRouter,
    ) -> None:
        self._router = router
        self._prepare_types_route()

    async def get_types(self) -> JSONResponse:
        """Get available data types and their supported versions."""
        analysis_types_versions_map = {
            path.strip("/").split("/")[-1]: list(versions.keys())
            for path, versions in ALL_PATHS_TO_DATA_MODEL.items()
        }
        return JSONResponse(content=analysis_types_versions_map)

    def _prepare_types_route(self) -> None:
        """Add API route for getting available data types and versions."""
        self._router.add_api_route(
            path="/analysistypes",
            endpoint=self.get_types,
            methods=["GET"],
            status_code=status.HTTP_200_OK,
            response_model=Dict[str, list],
            description="Get available types.",
        )


class SamplesAnalysisSchemasView:
    def __init__(
        self,
        router: APIRouter,
    ) -> None:
        self._router = router
        self._prepare_content_schema_route()

    async def get_content_schema(
        self,
        analysistype: str,
        content_schema_version: str = Depends(get_content_schema_version),
    ) -> JSONResponse:
        """Get the schema of the given analysis type and version."""
        model_versions = None
        for pattern in ENDPOINT_PATTERNS:
            model_versions = ALL_PATHS_TO_DATA_MODEL.get(pattern.format(analysistype=analysistype))
            if model_versions:
                break
        if model_versions and (model := model_versions.get(content_schema_version)):  # noqa: WPS332
            return JSONResponse(
                content=model.schema(),
            )
        return JSONResponse(
            {"message": f"Schema not found for {analysistype} and version {content_schema_version}"},
            status_code=status.HTTP_404_NOT_FOUND,
        )

    def _prepare_content_schema_route(self) -> None:
        """Add API route for getting content schema."""
        self._router.add_api_route(
            path="/{analysistype}/data/schema",
            endpoint=self.get_content_schema,
            methods=["GET"],
            status_code=status.HTTP_200_OK,
            response_model=Dict[str, list],
            description=APIDescriptionHelper.append_joined_roles(
                "Get the (`content schema`) for a given `{analysistype}`. <br><br>\
                Use the `Accept` request header to specify content schema version \
                    (example header `Accept: application/json;version=1.0.0` is supported).",
            ),
        )


class SamplesAnalysisSearchDataView:

    def __init__(
        self,
        router: APIRouter,
        **kwargs,
    ) -> None:
        self._router = router
        self.description_template_search_data = APIDescriptionHelper.append_joined_roles(
            "Get the (`queried`) bulk data from every `{analysis_type}` found in search service. <br><br>\
            Use the `Accept` request header to specify content schema version \
                (example header `Accept: */*;version=1.0.0` is supported).<br><br>\
            The  `columns_filter`, `rows_filter`, and  `columns_aggregation` \
                query parameters can be used to manage data in response. <br><br>\
            Use `offset`, `page_limit` query parameters to control response data size. \
                The `page_limit` and `total_size (found in response)` refers to the number of parquet files read.",
        )
        self.description_template_search = APIDescriptionHelper.append_joined_roles(
            "Get the (`samples analysis`) ids list that comply with `{query}` for given`{analysis_type}`. <br><br>\
            Use the `Accept` request header to specify content schema version \
                (example header `Accept: */*;version=1.0.0` is supported).<br><br>\
            The  `columns_filter`, `rows_filter`, and  `columns_aggregation` \
                query parameters can be used to manage data in response. <br><br> \
            Use `offset`, `page_limit` query parameters to control response data size. \
                The `page_limit` and `total_size (found in response)` refers to the number of parquet files read.",
        )
        self._prepare_api_routes()
        self._batch_size = SEARCH_READ_BATCH_SIZE
        if kwargs:
            self.__dict__.update(kwargs)

    @cache(expire=CACHE_DEFAULT_TTL, coder=ResponseCoder, key_builder=key_builder_using_token)
    async def get_search_data(
        self,
        request: Request,
        analysis_type: str,
        dataset_service: dataset.DatasetService = Depends(get_async_dataset_service),
        search_service: search.SearchService = Depends(get_async_search_service),
        df_filter: DataFrameFilterValidator = Depends(validate_filters),
        content_schema_version: str = Depends(get_content_schema_version),
        parquet_loader: ParquetLoader = Depends(get_parquet_loader),
        pagination_parameters: Tuple[int, int] = Depends(get_search_data_pagination_parameters),
    ) -> Response:
        """Search Data Endpoint.

        :param request: the request object
        :type request: Request
        :param analysis_type: the analysis type
        :type analysis_type: str
        :param dataset_service: dataset service instance, defaults to
            Depends(get_async_dataset_service)
        :type dataset_service: dataset.DatasetService, optional
        :param search_service: search service instance, defaults to
            Depends(get_async_search_service)
        :type search_service: search.SearchService, optional
        :param df_filter: dataframe filter, defaults to
            Depends(validate_filters)
        :type df_filter: DataFrameFilterValidator, optional
        :param content_schema_version: content schema version, defaults
            to Depends(get_content_schema_version)
        :type content_schema_version: str, optional
        :param parquet_loader: parquet loader instance, defaults to
            Depends(get_parquet_loader)
        :type parquet_loader: ParquetLoader, optional
        :param pagination_parameters: oagination parameters, defaults to
            Depends(get_pagination_parameters)
        :type pagination_parameters: Tuple[int, int], optional
        :return: Either json or parquet response from concatenated
            dataframes from search result
        :rtype: Response
        """
        data_partition_id = request.headers.get("data-partition-id")
        mime_type = SupportedMimeTypes.find_by_mime_type(request.headers["content-type"])
        offset, page_limit = pagination_parameters

        analysis_type_ids = await self._find_analysis_type_ids(
            data_partition_id, analysis_type, content_schema_version, search_service,
        )
        logger.debug("Found analysis types and datasets: ")
        logger.debug(analysis_type_ids)

        df_triplets_gen = self._get_search_data(
            analysis_type_ids,
            dataset_service,
            df_filter,
            parquet_loader,
        )

        result_df, total_size = await self._build_result_df(
            df_triplets_gen, df_filter, offset, page_limit, analysis_type_ids,
        )

        if mime_type == SupportedMimeTypes.PARQUET:
            content_response = result_df.astype(str).to_parquet() if result_df.any else b""
            response = Response(
                content=content_response,
                media_type=SupportedMimeTypes.PARQUET.mime_type,
            )
        else:
            content_response = result_df.to_json(orient="split") if result_df.any else json.dumps({})
            dict_response = {
                "result": json.loads(content_response),
                "offset": offset,
                "page_limit": page_limit,
                "total_size": total_size,
            }
            response = Response(
                content=json.dumps(dict_response),
                media_type=SupportedMimeTypes.JSON.mime_type,
            )

        return response

    @cache(expire=CACHE_DEFAULT_TTL, coder=ResponseCoder, key_builder=key_builder_using_token)
    async def get_search(
        self,
        request: Request,
        analysis_type: str,
        dataset_service: dataset.DatasetService = Depends(get_async_dataset_service),
        search_service: search.SearchService = Depends(get_async_search_service),
        df_filter: DataFrameFilterValidator = Depends(validate_filters),
        content_schema_version: str = Depends(get_content_schema_version),
        parquet_loader: ParquetLoader = Depends(get_parquet_loader),
        pagination_parameters: Tuple[int, int] = Depends(get_search_pagination_parameters),
    ) -> JSONResponse:
        """Search Endpoint.

        :param request: the request object
        :type request: Request
        :param analysis_type: the analysis type
        :type analysis_type: str
        :param dataset_service: dataset service instance, defaults to
            Depends(get_async_dataset_service)
        :type dataset_service: dataset.DatasetService, optional
        :param search_service: search service instance, defaults to
            Depends(get_async_search_service)
        :type search_service: search.SearchService, optional
        :param df_filter: dataframe filter, defaults to
            Depends(validate_filters)
        :type df_filter: DataFrameFilterValidator, optional
        :param content_schema_version: content schema version, defaults
            to Depends(get_content_schema_version)
        :type content_schema_version: str, optional
        :param parquet_loader: parquet loader instance, defaults to
            Depends(get_parquet_loader)
        :type parquet_loader: ParquetLoader, optional
        :param pagination_parameters: oagination parameters, defaults to
            Depends(get_pagination_parameters)
        :type pagination_parameters: Tuple[int, int], optional
        :return: The list with SamplesAnalysis ids obtained from search
        :rtype: Response
        """
        data_partition_id = request.headers.get("data-partition-id")
        offset, page_limit = pagination_parameters

        analysis_type_ids = await self._find_analysis_type_ids(
            data_partition_id, analysis_type, content_schema_version, search_service,
        )

        df_triplets_gen = self._get_search_data(
            analysis_type_ids,
            dataset_service,
            df_filter,
            parquet_loader,
        )

        result_set = []
        errors = []
        analysis_type_ids = dict(analysis_type_ids)
        async for batch_df_triplets in df_triplets_gen:
            for dataset_id, df, error_msg in batch_df_triplets:
                if not df.empty:
                    result_set.append(analysis_type_ids[dataset_id])
                if error_msg:
                    errors.append((dataset_id, error_msg))

        if errors:
            self._handle_errors(analysis_type_ids, errors)

        response = {
            "result": result_set[offset:offset + page_limit],
            "offset": offset,
            "page_limit": page_limit,
            "total_size": len(result_set),
        }
        return JSONResponse(content=response)

    def _prepare_api_routes(self) -> None:
        """Prepare and add api routes."""
        self._prepare_get_search_data_route()
        self._prepare_get_search_route()

    async def _get_search_data(  # noqa: WPS234
        self,
        analysis_type_ids: List[Tuple[str, str]],
        dataset_service: dataset.DatasetService,
        df_filter: DataFrameFilterValidator,
        parquet_loader: ParquetLoader,
    ) -> AsyncGenerator[List[DFPayload], None]:
        """Fetches parquet files from a given result list obtained from search
        service."""
        analysis_type_ids.sort(key=lambda analysis_type_id: analysis_type_id[1])
        dataset_ids = [result_id[0] for result_id in analysis_type_ids]
        df_filter_processor = DFFilterProcessor(df_filter=df_filter)

        for n_batch in range((len(dataset_ids) // self._batch_size) + 1):
            batch_offset = self._batch_size * n_batch
            dataset_ids_batch = dataset_ids[batch_offset:batch_offset + self._batch_size]
            signed_urls_for_datasets = await dataset_service.get_signed_urls(dataset_ids_batch)
            df_triplets = await parquet_loader.read_parquet_files(
                signed_urls_for_datasets, df_filter_processor,
            )
            yield df_triplets

    async def _find_analysis_type_ids(
        self,
        data_partition_id: str,
        analysis_type: str,
        target_schema_version: str,
        search_service: search.SearchService,
    ) -> List[Tuple[str, str]]:
        """Performs a query to search service to build a list of tuples
        dataset_id, samples_analysis_id."""
        query = self._build_sampleanalysistype_query(data_partition_id, SAMPLESANALYSIS_TYPE_MAPPING[analysis_type])

        result_records = []
        cursor = None
        while True:
            search_response = await search_service.find_records(
                kind=SAMPLESANALYSIS_KIND,
                query=query,
                limit=search.QUERY_LIMIT,
                cursor=cursor,
            )
            records = search_response.get("results", [])
            cursor = search_response.get("cursor", None)
            if not records:
                break
            result_records.extend(records)

        return self._build_result_ids(result_records, target_schema_version, analysis_type)

    async def _paginate_dfs(  # noqa: WPS234
        self,
        df_triplets: AsyncGenerator[DFPayload, None],
        offset: int,
        page_limit: Optional[int] = None,
        select_all: Optional[bool] = False,
    ) -> Tuple[List[pd.DataFrame], int, List[Tuple[str, str]]]:
        """Paginate the list of pd.DataFrame."""
        paged_dfs = []
        errors = []
        df_i = 0
        async for dataset_id, df, error_msg in df_triplets:
            if error_msg:
                logger.error(error_msg)
                errors.append((dataset_id, error_msg))
            elif select_all or (df_i >= offset and df_i < offset + page_limit):  # noqa: WPS333
                paged_dfs.append(df)
            df_i += 1

        return paged_dfs, df_i, errors

    async def _build_result_df(
        self,
        df_triplets: AsyncGenerator[DFPayload, None],
        df_filter: DataFrameFilterValidator,
        offset: int,
        page_limit: int,
        analysis_type_ids: List[Tuple[str, str]],
    ) -> Tuple[pd.DataFrame, int]:
        """Build a concatenated or aggregated pd.DataFrame."""

        filtered_df_triplets = self._filter_dfs(df_triplets)

        if df_filter.valid_columns_aggregation:
            df_filter_processor = DFFilterProcessor(df_filter=df_filter)
            paged_dfs, total_size, errors = await self._paginate_dfs(filtered_df_triplets, offset=0, select_all=True)
            result_df = df_filter_processor.apply_filters_from_df(
                pd.concat(paged_dfs, ignore_index=True),
            ) if paged_dfs else pd.DataFrame()
        else:
            paged_dfs, total_size, errors = await self._paginate_dfs(filtered_df_triplets, offset, page_limit)
            result_df = pd.concat(paged_dfs, ignore_index=True) if paged_dfs else pd.DataFrame()

        if errors:
            self._handle_errors(analysis_type_ids, errors)

        return result_df, total_size

    async def _filter_dfs(
        self,
        df_triplets: AsyncGenerator[DFPayload, None],
    ) -> AsyncGenerator[DFPayload, None]:
        """Async generator of pd.DataFrames."""

        async for batch_df_triplets in df_triplets:
            for dataset_id, df, error_msg in batch_df_triplets:
                if not (df.empty and error_msg is None):
                    yield dataset_id, df, error_msg

    def _verify_target_schema(
        self,
        dataset_id: str,
        analysis_type: str,
        current_schema: str,
        target_schema: str,
    ) -> bool:
        """Verify the dataset matches the correct target schema."""

        schema_match = False
        if current_schema == target_schema:
            schema_match = True

        dataset_type_match = False
        if f":{analysis_type}-" in dataset_id:
            dataset_type_match = True

        return schema_match and dataset_type_match

    def _build_result_ids(  # noqa: CCR001
        self,
        result_records: list,
        target_schema_version: str,
        analysis_type: str,
    ) -> List[Tuple[str, str]]:
        """Build a list of tuples dataset_id, samples_analysis_id."""

        result_ids = []
        for record in result_records:
            if ddms_datasets := record.get("data", {}).get("DDMSDatasets"):  # noqa: WPS332
                for urn in ddms_datasets:
                    urn_info = get_info_from_urn(urn)
                    if self._verify_target_schema(  # noqa: WPS337
                        dataset_id=urn_info["dataset_id"],
                        analysis_type=analysis_type,
                        current_schema=urn_info["content_schema_version"],
                        target_schema=target_schema_version,
                    ):
                        result_ids.append((urn_info["dataset_id"], urn_info["samples_analysis_id"]))  # noqa: WPS220

        return result_ids

    def _build_sampleanalysistype_query(self, data_partition_id: str, analysis_types: List[str]) -> str:
        """Build a query to be used within search service for
        SamplesAnalysisType."""

        analysis_types = [
            f'"{data_partition_id}:reference-data--SampleAnalysisType:{analysis_type}"'
            for analysis_type in analysis_types
        ]
        analysis_types_str = " OR ".join(analysis_types)
        return f"data.SampleAnalysisTypeIDs:({analysis_types_str})"

    def _handle_errors(self, analysis_type_ids: List[Tuple[str, str]], errors: List[Tuple[str, str]]):
        """Handle errors."""

        logger.error("Errors in datasets: ")
        logger.error(errors)
        analysis_type_ids = dict(analysis_type_ids)
        formatted_errors = {}
        for dataset_id, error_detail in errors:
            formatted_errors[analysis_type_ids[dataset_id]] = error_detail

        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"errors": formatted_errors})

    def _prepare_get_search_data_route(self) -> None:
        """Add api route for get_search_data."""

        self._router.add_api_route(
            path="/{analysis_type}/search/data",
            endpoint=self.get_search_data,
            methods=["GET"],
            status_code=status.HTTP_200_OK,
            description=self.description_template_search_data,
            dependencies=[
                Depends(validate_bulkdata_content_type),
            ],
        )

    def _prepare_get_search_route(self) -> None:
        """Add api route for get_search."""

        self._router.add_api_route(
            path="/{analysis_type}/search",
            endpoint=self.get_search,
            methods=["GET"],
            status_code=status.HTTP_200_OK,
            description=self.description_template_search,
        )
