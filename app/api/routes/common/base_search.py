#  Copyright 2025 ExxonMobil Technology and Engineering Company
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
from datetime import date
from typing import AsyncGenerator, List, NamedTuple, Optional, Tuple

import pandas as pd
import pandas._libs.json as pdujson  # noqa: WPS301, WPS436
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from loguru import logger
from starlette import status

from app.api.dependencies.request import (
    get_content_schema_version,
    get_response_mime_type,
)
from app.api.dependencies.services import (
    get_async_dataset_service,
    get_async_search_service,
    get_blob_storage_service,
)
from app.api.dependencies.validation import (
    RowPaginationParameters,
    get_orient,
    get_row_pagination_parameters,
    get_search_data_pagination_parameters,
    get_search_pagination_parameters,
    get_search_scope,
    validate_filters,
)
from app.api.routes.utils.api_description_helper import APIDescriptionHelper
from app.core.config import get_app_settings
from app.core.http_status import HTTP_422_UNPROCESSABLE
from app.dataframe.blob_parquet_loader import BlobParquetLoader
from app.dataframe.filter_processor import DFFilterProcessor
from app.dataframe.parquet_loader import DFPayload, ParquetLoader
from app.models.schemas.search_scope import SearchScope
from app.providers.dependencies.blob_storage import IBlobStorage
from app.resources.filters import DataFrameFilterValidator
from app.resources.mime_types import SupportedMimeTypes
from app.search.ddms_dataset_ids_fetcher import DDMSDatasetIdsFetcher
from app.services import dataset, search

SEARCH_READ_BATCH_SIZE = 100  # max number of parquet files retrieved
PaginationParametersType = Tuple[int, int, Optional[date], Optional[date]]


def _coerce_mixed_type_columns(df: pd.DataFrame) -> pd.DataFrame:
    # When datasets with mismatched column types are concatenated, pandas
    # produces object-dtype columns containing mixed Python types (e.g. int + str).
    # PyArrow rejects these during to_parquet(); cast such columns to str.
    for col in df.select_dtypes(include="object").columns:
        if df[col].map(type).nunique() > 1:
            df[col] = df[col].astype(str)
    return df


def _in_requested_order(signed_urls: List[Tuple[str, str]], requested_ids: List[str]) -> List[Tuple[str, str]]:
    """Order `(dataset_id, signed_url)` pairs like `requested_ids`.

    The Dataset Service answers with the datasets in an order of its own choosing. Row
    pagination treats the datasets as one logical row stream, so that order must be the
    stable one we asked for, or the same request could return different rows between
    calls. Ids the service returned that were not requested keep their relative order, last.
    """
    position = {dataset_id: index for index, dataset_id in enumerate(requested_ids)}
    return sorted(signed_urls, key=lambda pair: position.get(pair[0], len(position)))


def _row_window_fragment(
    df: pd.DataFrame,
    fragment_start: int,
    row_offset: int,
    row_window_end: Optional[int],
) -> Optional[pd.DataFrame]:
    """Slice of `df` intersecting the requested [row_offset, row_window_end) row
    window, or None if `df` falls entirely outside it.

    `df` is treated as occupying the row range [fragment_start, fragment_start +
    len(df)) within the logical row stream formed by concatenating every matching
    dataset, in stable order; `fragment_start` is the caller's running row count
    so far across that whole stream (Issue-820: no longer scoped to a dataset page).
    """
    fragment_end = fragment_start + len(df)
    if fragment_end <= row_offset:
        return None
    if row_window_end is not None and fragment_start >= row_window_end:
        return None

    local_start = max(0, row_offset - fragment_start)
    local_end = len(df) if row_window_end is None else min(len(df), row_window_end - fragment_start)
    return df.iloc[local_start:local_end]


class _RowPaginatedFragments(NamedTuple):
    """Result of streaming the row-window-intersecting fragments across every
    matching dataset (Issue-820: a global logical row stream, not a dataset page)."""

    kept_fragments: List[pd.DataFrame]
    total_rows: int
    total_size: int
    errors: List[Tuple[str, str]]


def search_data_row_pagination_responses() -> dict:
    """OpenAPI 200-response headers for `/search/data` (Issue-820).

    Parquet responses have no JSON envelope, so `X-Total-Rows` is the only channel through
    which a Parquet consumer learns the size of the logical result set it is paging through.
    Returns a fresh dict per route so routes never share one mutable object.
    """
    return {
        status.HTTP_200_OK: {
            "headers": {
                "X-Total-Rows": {
                    "description": (
                        "Total number of rows across every dataset matching the search, after "
                        "rows_filter/columns_filter and before row_offset/row_limit slicing. "
                        "Only present on Parquet responses, and only when row_offset or row_limit "
                        "is supplied. JSON responses carry the same value as `total_rows` in the "
                        "response body."
                    ),
                    "schema": {"type": "integer"},
                },
            },
        },
    }


class GenericSearchDataView(object):  # noqa: WPS214
    def __init__(
        self,
        router: APIRouter,
        ddms_dataset_ids_fetcher_class: DDMSDatasetIdsFetcher,
        register_default_routes: bool = True,
        **kwargs,
    ) -> None:
        self._router = router
        self.description_template_search_data = APIDescriptionHelper.append_joined_roles(
            "Get the (`queried`) bulk data from every `{analysis_type}` found in search service. <br><br>\
            Use the `content_schema_version` query parameter to specify content schema version \
                (e.g. `?content_schema_version=1.0.0`). The `Accept` header versioning is deprecated.<br><br>\
            The  `columns_filter`, `rows_filter`, and  `columns_aggregation` \
                query parameters can be used to manage data in response. <br><br>\
            Use the `orient` query parameter to select the JSON output format (`split` or `records`).<br><br>\
            Use `offset`, `page_limit` query parameters (legacy dataset pagination) to control response \
                data size. The `page_limit` and `total_size (found in response)` refers to the number \
                of parquet files read.<br><br>\
            Use `row_offset`, `row_limit` query parameters (logical row pagination) to paginate rows \
                across the **entire ordered set of rows from every dataset matching the search** — not \
                a single dataset page. Rows are ordered by dataset (sorted by samples analysis id, then \
                dataset id) and, within a dataset, in stored order, so consecutive row pages neither \
                overlap nor skip rows. `total_rows` (found in response, only present when `row_offset`/ \
                `row_limit` are used) is the number of rows remaining after `rows_filter`/`columns_filter` \
                across **every** matching dataset — the full logical result set, not the returned window \
                and not a single dataset page. Computing it reads every matching dataset even after the \
                requested window is complete, so request cost grows with the number of matching \
                datasets, not with `row_limit`. `offset`/`page_limit` and `row_offset`/`row_limit` are \
                **mutually exclusive**: supplying both in the same call returns `422`. In row mode the \
                JSON response carries `row_offset`, `row_limit` and `total_rows` (and `total_size`) and \
                does not echo `offset`/`page_limit`; Parquet responses expose `total_rows` as the \
                `X-Total-Rows` header. \
                `row_limit`/`row_offset` cannot be combined with `columns_aggregation`.",
        )
        self.description_template_search = APIDescriptionHelper.append_joined_roles(
            "Get the (`samples analysis`) ids list that comply with `{query}` for given`{analysis_type}`. <br><br>\
            Use the `content_schema_version` query parameter to specify content schema version \
                (e.g. `?content_schema_version=1.0.0`). The `Accept` header versioning is deprecated.<br><br>\
            The  `columns_filter`, `rows_filter`, and  `columns_aggregation` \
                query parameters can be used to manage data in response. <br><br> \
            Use `offset`, `page_limit` query parameters to control response data size. \
            The `page_limit` and `total_size` (found in response) <br> refers to the number of parquet \
                files read.<br><br>\
            Use `indexed_start_date` and `indexed_end_date` query parameters to filter the data based on indexing \
                date. <br><br>  - `indexed_start_date`: Filter for data indexed on or after this date. <br><br>  \
            - `indexed_end_date`: Filter for data indexed on or before this date. <br><br>",
        )
        if register_default_routes:
            self._prepare_api_routes()
        self._batch_size = SEARCH_READ_BATCH_SIZE
        self._ddms_dataset_ids_fetcher_class = ddms_dataset_ids_fetcher_class
        if kwargs:
            self.__dict__.update(kwargs)

    async def get_search_data(  # noqa: CCR001, CFQ001, CFQ002, WPS210, WPS211, WPS217, WPS231
        self,
        request: Request,
        analysis_type: str,
        dataset_service: dataset.DatasetService = Depends(get_async_dataset_service),
        blob_storage_service: IBlobStorage = Depends(get_blob_storage_service),
        search_service: search.SearchService = Depends(get_async_search_service),
        df_filter: DataFrameFilterValidator = Depends(validate_filters),
        content_schema_version: str = Depends(get_content_schema_version),
        pagination_parameters: PaginationParametersType = Depends(get_search_data_pagination_parameters),
        orient: str = Depends(get_orient),
        search_scope: SearchScope = Depends(get_search_scope),
        row_pagination_parameters: RowPaginationParameters = Depends(get_row_pagination_parameters),
    ) -> Response:
        """Search Data Endpoint.

        :param request: the request object
        :type request: Request
        :param analysis_type: the analysis type
        :type analysis_type: str
        :param dataset_service: dataset service instance, defaults to
            Depends(get_async_dataset_service)
        :type dataset_service: dataset.DatasetService, optional
        :param blob_storage_service: blob storage service instance,
            defaults to Depends(get_blob_storage_service)
        :type blob_storage_service: IBlobStorage, optional
        :param search_service: search service instance, defaults to
            Depends(get_async_search_service)
        :type search_service: search.SearchService, optional
        :param df_filter: dataframe filter, defaults to
            Depends(validate_filters)
        :type df_filter: DataFrameFilterValidator, optional
        :param content_schema_version: content schema version, defaults
            to Depends(get_content_schema_version)
        :type content_schema_version: str, optional
        :param pagination_parameters: A tuple containing pagination and filtering parameters:
            - `offset` (int): The starting index for pagination.
            - `page_limit` (int): The maximum number of items to return per page.
            - `indexed_start_date` (Optional[date]): The earliest date to filter data, or `None` if not provided.
            - `indexed_end_date` (Optional[date]): The latest date to filter data, or `None` if not provided.
            This parameter is populated via FastAPI's dependency injection using
            `Depends(get_search_pagination_parameters)`.
        :type pagination_parameters: Tuple[int, int, Optional[date], Optional[date]]
        :param row_pagination_parameters: A tuple `(row_limit, row_offset)` for
            row-level pagination (Issue-820) across the entire ordered logical row
            stream from every matching dataset. Mutually exclusive with
            `pagination_parameters`' `offset`/`page_limit` (legacy dataset
            pagination) when either is explicitly supplied — see
            `_dataset_pagination_explicitly_requested`. Defaults to no row-level
            pagination.
        :type row_pagination_parameters: RowPaginationParameters
        :return: Either json or parquet response from concatenated
            dataframes from search result
        :rtype: Response
        """
        # TODO: perfomance tuning
        data_partition_id = request.headers.get("data-partition-id")
        mime_type = get_response_mime_type(request)
        # Aggregation results only make sense in split format (index holds the function name)
        orient = "split" if df_filter.valid_columns_aggregation else orient
        offset, page_limit, indexed_start_date, indexed_end_date = pagination_parameters
        row_limit, row_offset = row_pagination_parameters
        row_pagination_active = self._row_pagination_explicitly_requested(request)
        if row_pagination_active and self._dataset_pagination_explicitly_requested(request):
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE,
                detail=(
                    "row_limit/row_offset (logical row pagination) cannot be combined with "
                    "offset/page_limit (legacy dataset pagination) in the same call. "
                    "Use one pagination mode per request."
                ),
            )
        query_date_range = (indexed_start_date, indexed_end_date)

        analysis_type_ids_fetcher = self._ddms_dataset_ids_fetcher_class(
            search_service=search_service,
        )
        analysis_type_ids = await analysis_type_ids_fetcher.get_ids(
            data_partition_id,
            analysis_type,
            content_schema_version,
            query_date_range,
            wks_parameters=search_scope.to_query_dict(),
        )
        # Total order: samples-analysis id, then dataset id. Sorting on the analysis id alone
        # leaves datasets that share one in whatever order the search service returned them,
        # which can differ between calls and would let consecutive row pages overlap or skip rows.
        analysis_type_ids.sort(key=lambda analysis_type_id: (analysis_type_id[1], analysis_type_id[0]))
        logger.debug("Found analysis types and datasets: ")

        total_rows = None
        if row_pagination_active:
            # Row pagination is a global logical row window across every matching dataset
            # (Issue-820) — dataset traversal is always the full, stably-ordered id list,
            # never pre-sliced by offset/page_limit (those are the mutually exclusive
            # legacy dataset-pagination mode, rejected above). total_size therefore keeps
            # _build_result_df's existing global formula (filtered survivor count when a
            # filter is active, else the full id count) — lead feedback item 1's fix,
            # still correct now that "the page" no longer exists.
            df_triplets_gen = await self._get_search_data(
                analysis_type_ids=analysis_type_ids,
                dataset_service=dataset_service,
                blob_storage_service=blob_storage_service,
                df_filter=df_filter,
            )
            result_df, total_rows, filtered_total_size = await self._build_result_df_row_paginated(
                df_triplets_gen,
                df_filter,
                row_offset,
                row_limit,
                analysis_type_ids,
            )
            total_size = filtered_total_size if self._is_non_empty_filter(df_filter) else len(analysis_type_ids)
        elif self._is_non_empty_filter(df_filter):
            df_triplets_gen = await self._get_search_data(
                analysis_type_ids=analysis_type_ids,
                dataset_service=dataset_service,
                blob_storage_service=blob_storage_service,
                df_filter=df_filter,
            )

            result_df, total_size = await self._build_result_df(
                df_triplets_gen,
                df_filter,
                offset,
                page_limit,
                analysis_type_ids,
            )
        else:
            df_triplets_gen = await self._get_search_data(
                analysis_type_ids=analysis_type_ids[offset : offset + page_limit],
                dataset_service=dataset_service,
                blob_storage_service=blob_storage_service,
                df_filter=df_filter,
            )
            total_size = len(analysis_type_ids)
            result_df, _ = await self._build_result_df(
                df_triplets_gen,
                df_filter,
                0,
                page_limit,
                analysis_type_ids,
            )

        if mime_type == SupportedMimeTypes.PARQUET:
            content_response = _coerce_mixed_type_columns(result_df).to_parquet() if result_df.any else b""
            response = Response(
                content=content_response,
                media_type=SupportedMimeTypes.PARQUET.mime_type,
            )
            if row_pagination_active:
                response.headers["X-Total-Rows"] = str(total_rows)
        else:
            if result_df.any:
                output_df = result_df
                # For records format, include index as column if it has meaningful labels
                if orient == "records" and not isinstance(result_df.index, pd.RangeIndex):
                    output_df = result_df.reset_index()
                content_response = output_df.to_dict(orient=orient)
            else:
                content_response = json.dumps({})
            dict_response = {"result": content_response}
            if row_pagination_active:
                # Row mode: `offset`/`page_limit` did not select the returned rows (they are
                # only the untouched legacy defaults), so they are not echoed back.
                dict_response["total_size"] = total_size
                dict_response["row_offset"] = row_offset
                dict_response["row_limit"] = row_limit
                dict_response["total_rows"] = total_rows
            else:
                dict_response["offset"] = offset
                dict_response["page_limit"] = page_limit
                dict_response["total_size"] = total_size
            response = Response(
                content=pdujson.ujson_dumps(dict_response),
                media_type=SupportedMimeTypes.JSON.mime_type,
            )
        return response

    async def get_search(  # noqa: CCR001, WPS231, WPS210
        self,
        request: Request,
        analysis_type: str,
        dataset_service: dataset.DatasetService = Depends(get_async_dataset_service),
        blob_storage_service: IBlobStorage = Depends(get_blob_storage_service),
        search_service: search.SearchService = Depends(get_async_search_service),
        df_filter: DataFrameFilterValidator = Depends(validate_filters),
        content_schema_version: str = Depends(get_content_schema_version),
        pagination_parameters: PaginationParametersType = Depends(get_search_pagination_parameters),
        search_scope: SearchScope = Depends(get_search_scope),
    ) -> JSONResponse:
        """Search Endpoint.

        :param request: the request object
        :type request: Request
        :param analysis_type: the analysis type
        :type analysis_type: str
        :param dataset_service: dataset service instance, defaults to
            Depends(get_async_dataset_service)
        :type dataset_service: dataset.DatasetService, optional
        :param blob_storage_service: blob storage service instance,
            defaults to Depends(get_blob_storage_service)
        :type blob_storage_service: IBlobStorage, optional
        :param search_service: search service instance, defaults to
            Depends(get_async_search_service)
        :type search_service: search.SearchService, optional
        :param df_filter: dataframe filter, defaults to
            Depends(validate_filters)
        :type df_filter: DataFrameFilterValidator, optional
        :param content_schema_version: content schema version, defaults
            to Depends(get_content_schema_version)
        :type content_schema_version: str, optional
        :param pagination_parameters: oagination parameters, defaults to
            Depends(get_pagination_parameters)
        :param pagination_parameters: A tuple containing pagination and filtering parameters:
            - `offset` (int): The starting index for pagination.
            - `page_limit` (int): The maximum number of items to return per page.
            - `indexed_start_date` (Optional[date]): The earliest date to filter data, or `None` if not provided.
            - `indexed_end_date` (Optional[date]): The latest date to filter data, or `None` if not provided.
            This parameter is populated via FastAPI's dependency injection using
            `Depends(get_search_pagination_parameters)`.
        :type pagination_parameters: Tuple[int, int, Optional[date], Optional[date]]

        :return: The list with SamplesAnalysis ids obtained from search
        :rtype: Response
        """
        data_partition_id = request.headers.get("data-partition-id")
        get_response_mime_type(request)
        offset, page_limit, indexed_start_date, indexed_end_date = pagination_parameters
        query_date_range = (indexed_start_date, indexed_end_date)

        analysis_type_ids_fetcher = self._ddms_dataset_ids_fetcher_class(
            search_service=search_service,
        )
        analysis_type_ids = await analysis_type_ids_fetcher.get_ids(
            data_partition_id,
            analysis_type,
            content_schema_version,
            query_date_range,
            wks_parameters=search_scope.to_query_dict(),
        )
        analysis_type_ids.sort(key=lambda analysis_type_id: analysis_type_id[1])

        if self._is_non_empty_filter(df_filter):
            df_triplets_gen = await self._get_search_data(
                analysis_type_ids=analysis_type_ids,
                dataset_service=dataset_service,
                blob_storage_service=blob_storage_service,
                df_filter=df_filter,
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
            "result": result_set[offset : offset + page_limit],
            "offset": offset,
            "page_limit": page_limit,
            "total_size": len(result_set),
        }
        return JSONResponse(content=response)

    def _is_non_empty_filter(self, df_filter: DataFrameFilterValidator) -> bool:
        is_column_filter = df_filter.raw_columns_aggregation or df_filter.raw_columns_filter
        is_row_filter = df_filter.raw_rows_filter
        return is_column_filter or is_row_filter

    def _row_pagination_explicitly_requested(self, request: Request) -> bool:
        """True if the caller explicitly passed `row_offset` and/or `row_limit` on the
        query string (Issue-820). Like `_dataset_pagination_explicitly_requested`, this
        checks presence, not "differs from default": `row_offset=0` is a valid explicit
        row-pagination request (it must switch on row mode, `total_rows` and the
        mutual-exclusivity check) even though it equals the parameter's default."""
        return "row_offset" in request.query_params or "row_limit" in request.query_params

    def _dataset_pagination_explicitly_requested(self, request: Request) -> bool:
        """True if the caller explicitly passed `offset` and/or `page_limit` on the
        query string (Issue-820: legacy dataset pagination and row-level pagination
        are mutually exclusive modes — this checks presence, not "differs from
        default", since both params always carry defaults)."""
        return "offset" in request.query_params or "page_limit" in request.query_params

    def _prepare_api_routes(self) -> None:
        """Prepare and add api routes."""
        self._prepare_get_search_data_route()
        self._prepare_get_search_route()

    async def _get_search_data(  # noqa: WPS234
        self,
        analysis_type_ids: List[Tuple[str, str]],
        dataset_service: dataset.DatasetService,
        blob_storage_service: IBlobStorage,
        df_filter: DataFrameFilterValidator,
    ) -> AsyncGenerator[List[DFPayload], None]:
        """Fetches parquet files from a given result list obtained from search
        service."""
        settings = get_app_settings()
        if settings.use_blob_storage:
            df_payload_gen = self._get_search_data_for_blobs(
                analysis_type_ids=analysis_type_ids,
                blob_storage_service=blob_storage_service,
                df_filter=df_filter,
            )
        else:
            df_payload_gen = self._get_search_data_for_datasets(
                analysis_type_ids=analysis_type_ids,
                dataset_service=dataset_service,
                df_filter=df_filter,
            )
        return df_payload_gen  # noqa: ASYNC910

    async def _get_search_data_for_blobs(  # noqa: WPS234, ASYNC900, ASYNC911
        self,
        analysis_type_ids: List[Tuple[str, str]],
        blob_storage_service: IBlobStorage,
        df_filter: DataFrameFilterValidator,
    ) -> AsyncGenerator[List[DFPayload], None]:
        """Fetches parquet files from a given result list obtained from search
        service."""
        blob_ids = [result_id[0] for result_id in analysis_type_ids]
        df_filter_processor = DFFilterProcessor(df_filter=df_filter)
        parquet_loader = BlobParquetLoader()

        for n_batch in range((len(blob_ids) // self._batch_size) + 1):
            batch_offset = self._batch_size * n_batch
            blob_ids_batch = blob_ids[batch_offset : batch_offset + self._batch_size]
            df_triplets = await parquet_loader.read_parquet_files(  # noqa: WPS476
                blob_ids=blob_ids_batch,
                blob_storage_service=blob_storage_service,
                df_filter_processor=df_filter_processor,
            )
            yield df_triplets

    async def _get_search_data_for_datasets(  # noqa: WPS234, ASYNC900, ASYNC911
        self,
        analysis_type_ids: List[Tuple[str, str]],
        dataset_service: dataset.DatasetService,
        df_filter: DataFrameFilterValidator,
    ) -> AsyncGenerator[List[DFPayload], None]:
        """Fetches parquet files from a given result list obtained from search
        service."""
        dataset_ids = [result_id[0] for result_id in analysis_type_ids]
        df_filter_processor = DFFilterProcessor(df_filter=df_filter)
        parquet_loader = ParquetLoader()

        for n_batch in range((len(dataset_ids) // self._batch_size) + 1):
            batch_offset = self._batch_size * n_batch
            dataset_ids_batch = dataset_ids[batch_offset : batch_offset + self._batch_size]
            signed_urls_for_datasets = await dataset_service.get_signed_urls(dataset_ids_batch)  # noqa: WPS476
            signed_urls_for_datasets = _in_requested_order(signed_urls_for_datasets, dataset_ids_batch)
            df_triplets = await parquet_loader.read_parquet_files(  # noqa: WPS476
                signed_urls_for_datasets,
                df_filter_processor,
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
            result_df = (
                df_filter_processor.apply_filters_from_df(
                    pd.concat(paged_dfs, ignore_index=True),
                )
                if paged_dfs
                else pd.DataFrame()
            )
        else:
            paged_dfs, total_size, errors = await self._paginate_dfs(filtered_df_triplets, offset, page_limit)
            result_df = pd.concat(paged_dfs, ignore_index=True) if paged_dfs else pd.DataFrame()

        if errors:
            self._handle_errors(analysis_type_ids, errors)

        return result_df, total_size

    async def _stream_row_paginated_fragments(
        self,
        filtered_df_triplets: AsyncGenerator[DFPayload, None],
        row_offset: int,
        row_window_end: Optional[int],
    ) -> _RowPaginatedFragments:
        """Walk the filtered generator once, treating every matching dataset (in
        stable order) as one logical row stream and keeping only the fragments
        intersecting the requested [row_offset, row_window_end) window (Issue-820).

        Split out of `_build_result_df_row_paginated` to keep each function's
        cognitive complexity low — this one owns the streaming/accumulation loop,
        the caller owns validation and final assembly. A dataset/fragment entirely
        outside the window is never retained in `kept_fragments`, so memory stays
        bounded by the window size, not the full result set — exact `total_rows`
        still requires walking every matching dataset, since an exact global count
        can't be known without it.

        :return: kept fragments, total_rows (global filtered row count), total_size
            (the count of every dataset that reached this generator, i.e. the
            filtered survivor count), and any per-dataset errors
        :rtype: _RowPaginatedFragments
        """
        kept_fragments: List[pd.DataFrame] = []
        errors: List[Tuple[str, str]] = []
        dataset_index = 0
        rows_seen = 0
        total_rows = 0

        async for dataset_id, df, error_msg in filtered_df_triplets:
            if error_msg:
                errors.append((dataset_id, error_msg))
                dataset_index += 1
                continue

            fragment = _row_window_fragment(df, rows_seen, row_offset, row_window_end)
            rows_seen += len(df)
            total_rows += len(df)
            if fragment is not None:
                kept_fragments.append(fragment)

            dataset_index += 1

        return _RowPaginatedFragments(kept_fragments, total_rows, dataset_index, errors)

    async def _build_result_df_row_paginated(
        self,
        df_triplets: AsyncGenerator[DFPayload, None],
        df_filter: DataFrameFilterValidator,
        row_offset: int,
        row_limit: Optional[int],
        analysis_type_ids: List[Tuple[str, str]],
    ) -> Tuple[pd.DataFrame, int, int]:
        """Apply row-level pagination across every matching dataset as one global
        logical row stream, without materializing the full result set before
        slicing (Issue-820).

        `analysis_type_ids`/`df_triplets` are never pre-sliced by dataset offset/
        page_limit here — dataset-level pagination and row-level pagination are
        mutually exclusive modes (rejected with 422 upstream in `get_search_data`
        when both are explicitly requested), so this path always traverses the
        full, stably-ordered id list. `_stream_row_paginated_fragments` checks
        each DataFrame's row range against the requested [row_offset, row_offset +
        row_limit) window as it streams past, keeping only the (possibly trimmed)
        intersecting fragments, so a dataset entirely outside the window is never
        held in memory. No DuckDB — see `app.dataframe.pagination` for why.

        `total_size` here matches `_build_result_df`'s existing semantics
        exactly (the count of datasets that survive `_filter_dfs`, i.e. are
        non-empty after row/column filtering) — lead feedback item 1: the
        row-paginated path must preserve this, not fall back to the raw
        unfiltered `len(analysis_type_ids)`.

        :return: (result dataframe for the requested row window, total_rows —
            the global filtered row count across every matching dataset,
            total_size — the filtered survivor count)
        :rtype: Tuple[pd.DataFrame, int, int]
        :raises HTTPException: 422 if `columns_aggregation` is set —
            row-level pagination is incompatible with aggregation.
        """
        if df_filter.valid_columns_aggregation:
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE,
                detail="row_limit/row_offset cannot be combined with columns_aggregation.",
            )

        filtered_df_triplets = self._filter_dfs(df_triplets)
        row_window_end = None if row_limit is None else row_offset + row_limit

        fragments = await self._stream_row_paginated_fragments(
            filtered_df_triplets,
            row_offset,
            row_window_end,
        )

        if fragments.errors:
            self._handle_errors(analysis_type_ids, fragments.errors)

        if not fragments.kept_fragments:
            return pd.DataFrame(), fragments.total_rows, fragments.total_size

        result_df = _coerce_mixed_type_columns(pd.concat(fragments.kept_fragments, ignore_index=True))
        return result_df, fragments.total_rows, fragments.total_size

    async def _filter_dfs(  # noqa: ASYNC900
        self,
        df_triplets: AsyncGenerator[DFPayload, None],
    ) -> AsyncGenerator[DFPayload, None]:
        """Async generator of pd.DataFrames."""

        async for batch_df_triplets in df_triplets:
            for dataset_id, df, error_msg in batch_df_triplets:
                if not (df.empty and error_msg is None):
                    yield dataset_id, df, error_msg  # noqa: ASYNC911

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
            responses=search_data_row_pagination_responses(),
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
