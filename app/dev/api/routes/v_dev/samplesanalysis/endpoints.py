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
from typing import AsyncGenerator, List, Optional, Tuple

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi_cache.decorator import cache
from loguru import logger
from starlette import status

from app.api.dependencies.parquet import get_parquet_loader
from app.api.dependencies.request import (
    get_content_schema_version,
    validate_bulkdata_content_type,
)
from app.api.dependencies.services import get_async_dataset_service
from app.api.dependencies.validation import (
    get_search_data_pagination_parameters,
    get_search_pagination_parameters,
)
from app.api.routes.utils.api_description_helper import APIDescriptionHelper
from app.core.helpers.cache.coder import ResponseCoder
from app.core.helpers.cache.key_builder import key_builder_using_token
from app.core.helpers.cache.settings import CACHE_DEFAULT_TTL
from app.dataframe.parquet_loader import DFPayload
from app.dev.api.dependencies.search import (
    AnalysisTypeIdsFetcher,
    get_analysis_type_ids_fetcher,
)
from app.dev.api.dependencies.validation import (
    get_search_wks_parameters,
    validate_multiple_nested_filters,
)
from app.dev.dataframe.multiple_nested_filter_processor import (
    DFMultipleNestedFilterProcessor,
)
from app.dev.resources.multiple_nested_filters import (
    DFMultipleNestedFilterValidator,
)
from app.resources.mime_types import SupportedMimeTypes
from app.services import dataset

SEARCH_READ_BATCH_SIZE = 100  # max number of parquet files retrieved


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
        df_filter: DFMultipleNestedFilterValidator = Depends(validate_multiple_nested_filters),
        content_schema_version: str = Depends(get_content_schema_version),
        pagination_parameters: Tuple[int, int] = Depends(get_search_data_pagination_parameters),
        wks_parameters: Optional[dict] = Depends(get_search_wks_parameters),
        analysis_type_ids_fetcher: AnalysisTypeIdsFetcher = Depends(get_analysis_type_ids_fetcher),
    ) -> Response:
        """Search Data Endpoint.

        :param request: the request object
        :type request: Request
        :param analysis_type: the analysis type
        :type analysis_type: str
        :param dataset_service: dataset service instance, defaults to
            Depends(get_async_dataset_service)
        :type dataset_service: dataset.DatasetService, optional
        :param df_filter: dataframe filter, defaults to
            Depends(validate_multiple_nested_filters)
        :type df_filter: DFMultipleNestedFilterValidator, optional
        :param content_schema_version: content schema version, defaults
            to Depends(get_content_schema_version)
        :type content_schema_version: str, optional
        :param pagination_parameters: pagination parameters, defaults to
            Depends(get_pagination_parameters)
        :type pagination_parameters: Tuple[int, int], optional
        :param wks_parameters: wks search parameters, defaults to
            Depends(get_search_wks_parameters)
        :type wks_parameters: Optiona[dict], optional
        :return: Either json or parquet response from concatenated
            dataframes from search result
        :rtype: Response
        """
        data_partition_id = request.headers.get("data-partition-id")
        mime_type = SupportedMimeTypes.find_by_mime_type(request.headers["content-type"])
        offset, page_limit = pagination_parameters

        analysis_type_ids = await analysis_type_ids_fetcher.get_ids(
            data_partition_id, analysis_type, content_schema_version, wks_parameters,
        )
        analysis_type_ids.sort(key=lambda analysis_type_id: analysis_type_id[1])

        if self._is_non_empty_filter(df_filter):
            df_triplets_gen = self._get_search_data(
                analysis_type_ids,
                dataset_service,
                df_filter,
            )

            result_df, total_size = await self._build_result_df(
                df_triplets_gen, df_filter, offset, page_limit, analysis_type_ids,
            )
        else:
            df_triplets_gen = self._get_search_data(
                analysis_type_ids[offset:offset + page_limit],
                dataset_service,
                df_filter,
            )
            total_size = len(analysis_type_ids)
            result_df, _ = await self._build_result_df(
                df_triplets_gen, df_filter, 0, page_limit, analysis_type_ids,
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
    async def get_search(  # noqa: CCR001
        self,
        request: Request,
        analysis_type: str,
        dataset_service: dataset.DatasetService = Depends(get_async_dataset_service),
        df_filter: DFMultipleNestedFilterValidator = Depends(validate_multiple_nested_filters),
        content_schema_version: str = Depends(get_content_schema_version),
        pagination_parameters: Tuple[int, int] = Depends(get_search_pagination_parameters),
        wks_parameters: Optional[dict] = Depends(get_search_wks_parameters),
        analysis_type_ids_fetcher: AnalysisTypeIdsFetcher = Depends(get_analysis_type_ids_fetcher),
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
            Depends(validate_multiple_nested_filters)
        :type df_filter: DFMultipleNestedFilterValidator, optional
        :param content_schema_version: content schema version, defaults
            to Depends(get_content_schema_version)
        :type content_schema_version: str, optional
        :param pagination_parameters: pagination parameters, defaults to
            Depends(get_pagination_parameters)
        :type pagination_parameters: Tuple[int, int], optional
        :param wks_parameters: wks search parameters, defaults to
            Depends(get_search_wks_parameters)
        :type wks_parameters: Optiona[dict], optional
        :return: The list with SamplesAnalysis ids obtained from search
        :rtype: Response
        """
        data_partition_id = request.headers.get("data-partition-id")
        offset, page_limit = pagination_parameters

        analysis_type_ids = await analysis_type_ids_fetcher.get_ids(
            data_partition_id, analysis_type, content_schema_version, wks_parameters,
        )
        analysis_type_ids.sort(key=lambda analysis_type_id: analysis_type_id[1])

        if self._is_non_empty_filter(df_filter):
            df_triplets_gen = self._get_search_data(
                analysis_type_ids,
                dataset_service,
                df_filter,
            )

            result_set = []
            errors = []
            analysis_type_ids = dict(analysis_type_ids)
            async for batch_df_triplets in df_triplets_gen:
                for dataset_id, df, error_msg in batch_df_triplets:
                    if not df.empty:
                        result_set.append(analysis_type_ids[dataset_id])  # noqa: WPS220
                    if error_msg:
                        errors.append((dataset_id, error_msg))  # noqa: WPS220

            if errors:
                self._handle_errors(analysis_type_ids, errors)
        else:
            result_set = [samplesanalysis_ids for _, samplesanalysis_ids in analysis_type_ids]

        response = {
            "result": result_set[offset:offset + page_limit],
            "offset": offset,
            "page_limit": page_limit,
            "total_size": len(result_set),
        }
        return JSONResponse(content=response)

    async def _get_search_data(  # noqa: WPS234
        self,
        analysis_type_ids: List[Tuple[str, str]],
        dataset_service: dataset.DatasetService,
        df_filter: DFMultipleNestedFilterValidator,
    ) -> AsyncGenerator[List[DFPayload], None]:
        """Fetches parquet files from a given result list obtained from search
        service."""
        dataset_ids = [result_id[0] for result_id in analysis_type_ids]
        df_filter_processor = DFMultipleNestedFilterProcessor(df_filter=df_filter)
        parquet_loader = await get_parquet_loader()

        for n_batch in range((len(dataset_ids) // self._batch_size) + 1):
            batch_offset = self._batch_size * n_batch
            dataset_ids_batch = dataset_ids[batch_offset:batch_offset + self._batch_size]
            signed_urls_for_datasets = await dataset_service.get_signed_urls(dataset_ids_batch)
            df_triplets = await parquet_loader.read_parquet_files(
                signed_urls_for_datasets, df_filter_processor,
            )
            yield df_triplets

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
        df_filter: DFMultipleNestedFilterValidator,
        offset: int,
        page_limit: int,
        analysis_type_ids: List[Tuple[str, str]],
    ) -> Tuple[pd.DataFrame, int]:
        """Build a concatenated or aggregated pd.DataFrame."""

        filtered_df_triplets = self._filter_dfs(df_triplets)

        if df_filter.valid_columns_aggregation:
            df_filter_processor = DFMultipleNestedFilterProcessor(df_filter=df_filter)
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

    def _is_non_empty_filter(self, df_filter: DFMultipleNestedFilterValidator) -> bool:
        is_column_filter = df_filter.raw_columns_aggregation or df_filter.raw_columns_filter
        is_row_filter = df_filter.raw_rows_filter or df_filter.raw_rows_multiple_filter
        return is_column_filter or is_row_filter

    def _prepare_api_routes(self) -> None:
        """Prepare and add api routes."""
        self._prepare_get_search_data_route()
        self._prepare_get_search_route()

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
